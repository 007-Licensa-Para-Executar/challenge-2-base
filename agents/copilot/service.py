"""Consultar registros com contexto verificado e fontes materializadas pelo código."""

import sqlite3
from collections import Counter
from typing import Literal

from .contracts import CopilotAnswer, Evidence, Query


class CopilotService:
    def __init__(self, store, retriever, generator=None):
        self.store = store
        self.retriever = retriever
        self.generator = generator

    def answer(
        self,
        query: Query,
        generation_mode: Literal["ollama", "extractive"] = "ollama",
        top_k: int = 3,
    ) -> CopilotAnswer:
        if generation_mode not in ("ollama", "extractive") or not 1 <= top_k <= 5:
            raise ValueError("Modo ou quantidade de trechos inválidos")
        backend = self.retriever.backend
        model = getattr(self.generator, "model", None) if generation_mode == "ollama" else None
        common = {
            "patient_id": query.patient_id,
            "question": query.question,
            "start_at": query.start_at,
            "end_at": query.end_at,
            "generation_mode": generation_mode,
            "retriever": backend,
            "model": model,
        }

        def failure(code):
            return CopilotAnswer(
                status="error",
                answer="Falha operacional; nenhuma síntese foi gerada.",
                error_code=code,
                **common,
            )

        try:
            records = self.store.list_records(query)
        except (OSError, sqlite3.Error, ValueError):
            return failure("storage_error")
        for record in records:
            if (
                record.patient_id != query.patient_id
                or query.start_at
                and record.recorded_at < query.start_at
                or query.end_at
                and record.recorded_at > query.end_at
            ):
                return failure("context_mismatch")
        counts = dict(
            Counter(
                r.classification.primary_theme for r in records if r.classification.status == "ok"
            )
        )
        common.update(eligible_records=len(records), theme_counts=counts)
        if not records:
            return CopilotAnswer(
                status="insufficient_evidence",
                answer="Nenhum registro desta pessoa no período solicitado.",
                **common,
            )
        from .retriever import RetrievalError

        try:
            evidence = self.retriever.search(records, query.question, top_k=top_k)
        except RetrievalError as error:
            return failure(error.code)
        if not evidence:
            return CopilotAnswer(
                status="insufficient_evidence",
                answer="Não foram encontrados trechos suficientes para responder.",
                **common,
            )
        originals = {r.record_id: r for r in records}
        if not all(self._valid_evidence(ev, originals, query) for ev in evidence):
            return failure("invalid_evidence")
        if generation_mode == "extractive":
            answer = "Trechos recuperados (sem síntese por LLM):\n" + "\n".join(
                f"[{ev.chunk_id}] {ev.quote}" for ev in evidence
            )
            return CopilotAnswer(status="ok", answer=answer, evidence=evidence, **common)
        if self.generator is None:
            return failure("generator_unavailable")
        from .model import GenerationError

        try:
            draft = self.generator.generate(query, evidence)
        except GenerationError as error:
            if error.code == "insufficient_evidence":
                return CopilotAnswer(
                    status="insufficient_evidence",
                    answer="Os trechos encontrados não sustentaram uma resposta.",
                    **common,
                )
            return failure(error.code)
        allowed = {ev.chunk_id: ev for ev in evidence}
        if not draft.statements:
            return CopilotAnswer(
                status="insufficient_evidence",
                answer="Os trechos encontrados não sustentaram uma resposta.",
                **common,
            )
        if any(
            ref not in allowed for statement in draft.statements for ref in statement.evidence_ids
        ):
            return failure("invalid_citation")
        used = {ref for statement in draft.statements for ref in statement.evidence_ids}
        answer = "\n".join(
            statement.text + " " + " ".join(f"[{ref}]" for ref in statement.evidence_ids)
            for statement in draft.statements
        )
        return CopilotAnswer(
            status="ok",
            answer=answer,
            evidence=[ev for ev in evidence if ev.chunk_id in used],
            **common,
        )

    @staticmethod
    def _valid_evidence(ev: Evidence, records, query: Query) -> bool:
        record = records.get(ev.record_id)
        return bool(
            record is not None
            and ev.patient_id == query.patient_id
            and ev.recorded_at == record.recorded_at
            and ev.source_title == record.source_title
            and ev.end_char <= len(record.original_text)
            and ev.quote == record.original_text[ev.start_char : ev.end_char]
            and ev.chunk_id == f"{ev.record_id}:{ev.start_char}:{ev.end_char}"
        )
