"""Persistência de originais sintéticos, separada da tabela legada de extrações."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .contracts import DiaryRecord, Query


class DuplicateRecordError(ValueError):
    """O identificador já existe; o original não foi sobrescrito."""


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


class DiaryStore:
    """Armazena registros e consulta um único paciente por intervalo inclusivo.

    ``patient_id`` é contexto de consulta, não um mecanismo de autenticação.
    A autorização da profissional deve ser estabelecida pela aplicação.
    """

    table = "diary_records"
    version = "1.0.0"
    primary_key = "record_id"

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()

    def save(self, record: DiaryRecord) -> None:
        if record.schema_version != self.version:
            raise ValueError("Representação incompatível com a base")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(sqlite3.connect(self.db_path)) as conn, conn:
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {self.table} ("
                    "record_id TEXT NOT NULL, patient_id TEXT NOT NULL, "
                    "recorded_at TEXT NOT NULL, record_json TEXT NOT NULL, "
                    f"PRIMARY KEY ({self.primary_key}))"
                )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table}_patient_time "
                    f"ON {self.table}(patient_id, recorded_at, record_id)"
                )
                conn.execute(
                    f"INSERT INTO {self.table} VALUES (?, ?, ?, ?)",
                    (
                        record.record_id,
                        record.patient_id,
                        _timestamp(record.recorded_at),
                        record.model_dump_json(exclude=
                            {"treated_text", "representation_id", "detector_version"}
                            if self.version == "1.0.0" else {"original_text"}
                        ),
                    ),
                )
        except sqlite3.IntegrityError:
            raise DuplicateRecordError("record_id já existe; registro não alterado") from None

    def list_records(self, query: Query) -> list[DiaryRecord]:
        if not self.db_path.exists():
            return []
        # URI keeps paths containing spaces/accents portable and prevents creation/writes.
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            if not conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (self.table,)
            ).fetchone():
                return []
            clauses = ["patient_id = ?"]
            params = [query.patient_id]
            if query.start_at is not None:
                clauses.append("recorded_at >= ?")
                params.append(_timestamp(query.start_at))
            if query.end_at is not None:
                clauses.append("recorded_at <= ?")
                params.append(_timestamp(query.end_at))
            rows = conn.execute(
                f"SELECT record_id, recorded_at, record_json FROM {self.table} WHERE "
                + " AND ".join(clauses)
                + " ORDER BY recorded_at, record_id",
                params,
            ).fetchall()
        result = []
        for record_id, recorded_at, payload in rows:
            record = DiaryRecord.model_validate_json(payload)
            if (
                record.schema_version != self.version
                or record.patient_id != query.patient_id
                or record.record_id != record_id
                or _timestamp(record.recorded_at) != recorded_at
            ):
                raise ValueError("Metadados persistidos inconsistentes")
            result.append(record)
        return result


class ProtectedDiaryStore(DiaryStore):
    """Consulta somente a tabela da representação tratada, mesmo numa base legada."""

    table = "protected_diary_records"
    version = "2.0.0"
    primary_key = "patient_id, record_id"
