"""Processamento e leitura compartilhados pelo diário, roda e chat."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agents.extractor.contracts import Agent1Output

from .contracts import DiaryRecord, Evidence, Query
from .storage import ProtectedDiaryStore

DISPLAY_THEMES = {
    "autoestima": "autopercepcao",
    "familia": "vinculos",
    "relacionamentos": "vinculos",
    "trabalho": "desempenho",
    "estudos": "desempenho",
    "financas": "desempenho",
    "saude_sono": "fisico",
    "luto": "rupturas",
    "outros_indeterminado": "outros",
}


class StoredAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["1.0.0"] = "1.0.0"
    source: Literal["ollama"] = "ollama"
    record_id: str
    representation_id: str
    output: Agent1Output


def validate_analysis(record: DiaryRecord, analysis: StoredAnalysis) -> None:
    if (
        record.schema_version != "2.0.0"
        or record.record_id != analysis.record_id
        or record.representation_id != analysis.representation_id
        or record.patient_id != analysis.output.patient_id
        or record.classification.primary_theme != analysis.output.macro_tema_validado
    ):
        raise ValueError("Vínculo da análise inválido")
    for topic in analysis.output.subtemas:
        for span in topic.evidencias:
            if (
                not 0 <= span.start_char < span.end_char <= len(record.analysis_text)
                or record.analysis_text[span.start_char:span.end_char] != span.quote_text
            ):
                raise ValueError("Citação da análise inválida")


class IntegratedStore(ProtectedDiaryStore):
    def publish(self, record: DiaryRecord, output: Agent1Output) -> StoredAnalysis:
        analysis = StoredAnalysis(
            record_id=record.record_id, representation_id=record.representation_id, output=output,
        )
        validate_analysis(record, analysis)
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS diary_analyses ("
                "patient_id TEXT NOT NULL, record_id TEXT NOT NULL, entry_id TEXT NOT NULL, "
                "analysis_json TEXT NOT NULL, PRIMARY KEY(patient_id, record_id, entry_id))"
            )
            db.execute(
                "INSERT INTO diary_analyses VALUES (?, ?, ?, ?)",
                (record.patient_id, record.record_id, str(output.entry_id),
                 analysis.model_dump_json()),
            )
        return analysis

    def save_classification(self, record: DiaryRecord) -> None:
        with closing(sqlite3.connect(self.db_path)) as db, db:
            changed = db.execute(
                "UPDATE protected_diary_records SET record_json = ? "
                "WHERE patient_id = ? AND record_id = ? "
                "AND json_extract(record_json, '$.representation_id') = ?",
                (record.model_dump_json(exclude={"original_text"}), record.patient_id,
                 record.record_id, record.representation_id),
            ).rowcount
            if changed != 1:
                raise ValueError("Representação indisponível durante o reprocessamento")

    def analyses(self, query: Query) -> list[tuple[DiaryRecord, StoredAnalysis | None]]:
        records = self.list_records(query)
        if not records:
            return []
        with closing(sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='diary_analyses'"
            ).fetchone()
            rows = db.execute(
                "SELECT record_id, entry_id, analysis_json FROM diary_analyses "
                "WHERE patient_id = ? ORDER BY rowid", (query.patient_id,),
            ).fetchall() if exists else []
        latest = {record_id: (entry_id, raw) for record_id, entry_id, raw in rows}
        result = []
        for record in records:
            saved = None
            if row := latest.get(record.record_id):
                entry_id, raw = row
                saved = StoredAnalysis.model_validate_json(raw)
                if str(saved.output.entry_id) != entry_id:
                    raise ValueError("Identificador de análise inconsistente")
                validate_analysis(record, saved)
            result.append((record, saved))
        return result


def topic_evidence(
    record: DiaryRecord, analysis: StoredAnalysis, topic: str,
) -> list[Evidence]:
    return [
        Evidence(
            chunk_id=f"{record.evidence_key}:{span.start_char}:{span.end_char}",
            record_id=record.record_id, patient_id=record.patient_id,
            representation_id=record.representation_id, recorded_at=record.recorded_at,
            source_title=record.source_title, quote=span.quote_text,
            start_char=span.start_char, end_char=span.end_char, score=0,
            entry_id=analysis.output.entry_id,
        )
        for item in analysis.output.subtemas if item.nome.casefold() == topic.casefold()
        for span in item.evidencias
    ]
