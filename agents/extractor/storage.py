"""Persistência local apenas para execuções com textos sintéticos."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .contracts import ProcessingResult

DB_VERSION = 1


class StorageError(Exception):
    """Erro sanitizado de persistência, sem detalhes do relato ou caminho."""


def save_result(db_path: str | Path, text: str, result: ProcessingResult) -> None:
    """Salva uma execução de forma atômica; nunca registra resultado parcial."""
    try:
        path = Path(db_path).expanduser()
        if str(path) == ":memory:":
            raise StorageError("Use um arquivo local para persistência.")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        with sqlite3.connect(path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, DB_VERSION):
                raise StorageError("Versão do banco incompatível.")
            if version == 0:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if tables:
                    raise StorageError("Esquema do banco desconhecido.")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                synthetic INTEGER NOT NULL CHECK(synthetic = 1),
                input_text TEXT NOT NULL,
                result_json TEXT NOT NULL,
                model TEXT NOT NULL,
                model_digest TEXT,
                prompt_version TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ok', 'error'))
            )""")
            connection.execute(f"PRAGMA user_version = {DB_VERSION}")
            connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    result.id,
                    result.created_at.isoformat(),
                    1,
                    text,
                    result.model_dump_json(),
                    result.metadata.model,
                    result.metadata.model_digest,
                    result.metadata.prompt_version,
                    result.metadata.schema_version,
                    result.status,
                ),
            )
    except StorageError:
        raise
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as from_error:
        raise StorageError("Não foi possível salvar a execução no banco local.") from from_error
