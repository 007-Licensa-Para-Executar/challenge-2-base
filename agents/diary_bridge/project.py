"""Liga um relato já autorizado do diário ao classificador e ao RAG sintético.

O identificador `paciente-ficticio` não prova que o texto seja fictício. A ponte
só roda com `DIARY_BRIDGE_DEMO=1` e só aceita as frases de `SYNTHETIC_FIXTURES`.
`synthetic=true` é gravado depois desse filtro. Não há rota HTTP.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from agents.copilot.contracts import CopilotAnswer, DiaryRecord, Query
from agents.copilot.ingestion import classify_record
from agents.copilot.retriever import Retriever
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore, DuplicateRecordError
from agents.patient_diary.contracts import Actor
from agents.patient_diary.local_app import LOCAL_USER
from agents.patient_diary.store import AccessDeniedError, PatientDiaryStore

_TITLE = re.compile(r"^patient_diary:([^:]+):(w|r[1-9][0-9]*)$")
_VERSION = re.compile(r"^(w|r[1-9][0-9]*)$")
# Catálogo fechado. Incluir uma frase aqui é mudança de código, não um argumento do cliente.
SYNTHETIC_FIXTURES = frozenset({
    "Relato fictício sobre sono curto.",
    "jardim antigo alfa",
    "jardim novo beta",
})


@dataclass(frozen=True)
class Projection:
    """Resultado da ponte. Não é aconselhamento nem conclusão clínica."""

    status: Literal["stored", "unchanged", "blocked"]
    code: str
    entry_id: str
    patient_id: str | None = None
    record_id: str | None = None
    text_source: str | None = None
    review_status: str | None = None
    recorded_at: datetime | None = None
    version: str | None = None
    classification_status: str | None = None
    primary_theme: str | None = None
    classification_error: str | None = None


@dataclass(frozen=True)
class Consultation:
    """Trechos recuperados. O campo clínico permanece falso."""

    status: Literal["ok", "insufficient_evidence", "error", "blocked"]
    code: str
    answer: str
    patient_id: str | None = None
    evidence_quotes: tuple[str, ...] = ()
    clinical_use: Literal[False] = False


def project_entry(
    diary: PatientDiaryStore,
    rag: DiaryStore,
    entry_id: str,
    actor: Actor,
    predictor=None,
) -> Projection:
    """Projeta o texto confirmado. Não aceita texto enviado direto pelo cliente."""
    refused = _separate(diary, rag)
    if refused is not None:
        return Projection(status="blocked", code=refused, entry_id=entry_id)
    if not _demo_enabled():
        return Projection(status="blocked", code="demo_disabled", entry_id=entry_id)
    try:
        source = diary.theme_source(entry_id, actor)
    except AccessDeniedError:
        return Projection(status="blocked", code="access_denied", entry_id=entry_id)
    if source.review_status == "unreviewed" or source.text is None:
        return Projection(
            status="blocked",
            code="unreviewed",
            entry_id=entry_id,
            patient_id=source.patient_id,
            text_source=source.text_source,
            review_status=source.review_status,
        )
    if source.patient_id != LOCAL_USER or source.text not in SYNTHETIC_FIXTURES:
        return Projection(
            status="blocked",
            code="unproven_synthetic",
            entry_id=entry_id,
            patient_id=source.patient_id,
            review_status=source.review_status,
        )
    version = _version(diary, entry_id, actor, source.input_type)
    if version is None:
        return Projection(status="blocked", code="unreviewed", entry_id=entry_id)
    record_id = _record_id(entry_id, version)
    if record_id is None:
        return Projection(status="blocked", code="identifier_too_long", entry_id=entry_id)
    stored = _stored(rag, source.patient_id, record_id)
    if stored is not None:
        return _from_record(stored, status="unchanged", code="unchanged")
    record = DiaryRecord(
        record_id=record_id,
        patient_id=source.patient_id,
        recorded_at=source.created_at,
        original_text=source.text,
        source_title=f"patient_diary:{entry_id}:{version}",
    )
    classified = classify_record(record, predictor=predictor)
    try:
        rag.save(classified)
    except DuplicateRecordError:
        stored = _stored(rag, source.patient_id, record_id)
        if stored is None or stored.original_text != classified.original_text:
            return Projection(status="blocked", code="record_conflict", entry_id=entry_id)
        return _from_record(stored, status="unchanged", code="unchanged")
    code = classified.classification.error_code or "projected"
    return _from_record(classified, status="stored", code=code)


def consult(
    diary: PatientDiaryStore,
    rag: DiaryStore,
    actor: Actor,
    question: str,
    *,
    patient_id: str | None = None,
) -> Consultation:
    """Consulta só a versão selecionada de cada relato, em modo extrativo e BM25."""
    scope = actor.user_id if patient_id is None else patient_id
    refused = _separate(diary, rag)
    if refused is not None:
        return Consultation(status="blocked", code=refused, answer="", patient_id=scope)
    if not _demo_enabled():
        return Consultation(status="blocked", code="demo_disabled", answer="", patient_id=scope)
    if scope != LOCAL_USER:
        return Consultation(status="blocked", code="unproven_synthetic", answer="", patient_id=scope)
    try:
        diary.list_entries(scope, actor)
    except AccessDeniedError:
        return Consultation(status="blocked", code="access_denied", answer="", patient_id=scope)
    service = CopilotService(_Selected(rag), Retriever(backend="bm25"))
    answer = service.answer(
        Query(patient_id=scope, question=question),
        generation_mode="extractive",
    )
    return _consultation(answer)


def _demo_enabled() -> bool:
    return os.environ.get("DIARY_BRIDGE_DEMO") == "1"


def _version(diary: PatientDiaryStore, entry_id: str, actor: Actor, input_type: str) -> str | None:
    if input_type == "text":
        return "w"
    latest = diary.latest_revision(entry_id, actor)
    if latest is None:
        return None
    return f"r{latest.revision_number}"


def _record_id(entry_id: str, version: str) -> str | None:
    if _VERSION.fullmatch(version) is None:
        return None
    body = f"e{len(entry_id)}x{entry_id}v{version}"
    if len(body) > 80 or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", body) is None:
        return None
    return body


def _separate(diary: PatientDiaryStore, rag: DiaryStore) -> str | None:
    diary_path = diary.db_path.expanduser().resolve()
    rag_path = rag.db_path.expanduser().resolve()
    if diary_path == rag_path or _has_patient_entries(rag_path):
        return "shared_database"
    return None


def _has_patient_entries(path) -> bool:
    if not path.is_file():
        return False
    with closing(sqlite3.connect(path)) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'patient_entries'"
        ).fetchone()
    return row is not None


def _stored(rag: DiaryStore, patient_id: str, record_id: str) -> DiaryRecord | None:
    if not rag.db_path.exists():
        return None
    rows = rag.list_records(Query(patient_id=patient_id, question="versao"))
    for record in rows:
        if record.record_id == record_id:
            return record
    return None


def _from_record(
    record: DiaryRecord, *, status: Literal["stored", "unchanged"], code: str
) -> Projection:
    parsed = _TITLE.fullmatch(record.source_title)
    entry_id = parsed.group(1) if parsed else ""
    version = parsed.group(2) if parsed else None
    classification = record.classification
    theme = classification.primary_theme if classification.status == "ok" else None
    return Projection(
        status=status,
        code=code,
        entry_id=entry_id,
        patient_id=record.patient_id,
        record_id=record.record_id,
        text_source="written" if version == "w" else "reviewed_transcript",
        review_status="not_required" if version == "w" else "reviewed",
        recorded_at=record.recorded_at,
        version=version,
        classification_status=classification.status,
        primary_theme=theme,
        classification_error=classification.error_code,
    )


class _Selected:
    """Entrega ao RAG a versão mais nova de cada relato. As antigas ficam no banco."""

    def __init__(self, store: DiaryStore):
        self._store = store

    def list_records(self, query: Query) -> list[DiaryRecord]:
        chosen: dict[str, tuple[tuple[int, int], DiaryRecord]] = {}
        for record in self._store.list_records(query):
            parsed = _TITLE.fullmatch(record.source_title)
            if parsed is None:
                continue
            if record.original_text not in SYNTHETIC_FIXTURES:
                continue
            entry_id, version = parsed.group(1), parsed.group(2)
            rank = (0, 0) if version == "w" else (1, int(version[1:]))
            current = chosen.get(entry_id)
            if current is None or rank > current[0]:
                chosen[entry_id] = (rank, record)
        return [item[1] for item in chosen.values()]


def _consultation(answer: CopilotAnswer) -> Consultation:
    return Consultation(
        status=answer.status,
        code=answer.error_code or answer.status,
        answer=answer.answer,
        patient_id=answer.patient_id,
        evidence_quotes=tuple(item.quote for item in answer.evidence),
    )
