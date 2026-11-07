"""Persistência local apenas para execuções com textos sintéticos."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .contracts import ProcessingResult

DB_VERSION = 2


class StorageError(Exception):
    """Erro sanitizado de persistência, sem detalhes do relato ou caminho."""


def save_result(
    db_path: str | Path,
    text: str,
    result: ProcessingResult,
    *,
    encrypt: bool | None = None,
) -> None:
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
        should_encrypt = (
            encrypt
            if encrypt is not None
            else os.environ.get("ENABLE_DIARY_ENCRYPTION", "").lower() in ("1", "true", "yes")
        )
        if should_encrypt:
            from security.encryption import encrypt_diary_text

            stored_text = encrypt_diary_text(text)
        else:
            stored_text = text

        with sqlite3.connect(path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, DB_VERSION):
                raise StorageError("Versão do banco incompatível.")
            if version == 0:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if tables:
                    raise StorageError("Esquema do banco desconhecido.")
            connection.execute("BEGIN IMMEDIATE")
            if version == 0:
                connection.execute("""CREATE TABLE runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    synthetic INTEGER NOT NULL CHECK(synthetic = 1),
                    input_text TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    model TEXT NOT NULL,
                    model_digest TEXT,
                    prompt_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('ok', 'error')),
                    nlp_polaridade TEXT,
                    nlp_score REAL,
                    discrepancia_detectada INTEGER,
                    distancia_polaridade REAL
                )""")
            elif version == 1:
                connection.execute("ALTER TABLE runs ADD COLUMN nlp_polaridade TEXT")
                connection.execute("ALTER TABLE runs ADD COLUMN nlp_score REAL")
                connection.execute("ALTER TABLE runs ADD COLUMN discrepancia_detectada INTEGER")
                connection.execute("ALTER TABLE runs ADD COLUMN distancia_polaridade REAL")
            connection.execute(f"PRAGMA user_version = {DB_VERSION}")
            connection.execute(
                """INSERT INTO runs (
                    id, created_at, synthetic, input_text, result_json, model, model_digest,
                    prompt_version, schema_version, status, nlp_polaridade, nlp_score,
                    discrepancia_detectada, distancia_polaridade
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.id,
                    result.created_at.isoformat(),
                    1,
                    stored_text,
                    result.model_dump_json(),
                    result.metadata.model,
                    result.metadata.model_digest,
                    result.metadata.prompt_version,
                    result.metadata.schema_version,
                    result.status,
                    result.validation.nlp_polaridade if result.validation else None,
                    result.validation.nlp_score if result.validation else None,
                    int(result.validation.discrepancia_detectada) if result.validation else None,
                    result.validation.distancia_polaridade if result.validation else None,
                ),
            )
    except StorageError:
        raise
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as from_error:
        raise StorageError("Não foi possível salvar a execução no banco local.") from from_error


def read_result_text(db_path: str | Path, run_id: str) -> str | None:
    """Recupera e descriptografa transparentemente o relato de uma execução (LGPD)."""
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        return None
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT input_text FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if not row or row[0] is None:
                return None
            from security.encryption import decrypt_diary_text

            return decrypt_diary_text(row[0])
    except (sqlite3.Error, OSError, ValueError):
        return None


def delete_result(db_path: str | Path, run_id: str) -> bool:
    """Remove permanentemente os registros de uma execução do banco SQLite (LGPD Art. 18, VI).

    Retorna True se o registro foi localizado e excluído, ou False caso não exista.
    """
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        return False
    try:
        with sqlite3.connect(path) as connection:
            cursor = connection.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            connection.commit()
            return cursor.rowcount > 0
    except (sqlite3.Error, OSError) as e:
        raise StorageError("Não foi possível excluir o registro do banco local.") from e


def purge_records(db_path: str | Path, *, older_than_days: int) -> int:
    """Expurga registros antigos com base na política de retenção de dados (LGPD Art. 16).

    Retorna o número de registros removidos permanentemente.
    """
    if older_than_days < 0:
        raise StorageError("O período de retenção deve ser maior ou igual a zero dias.")
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        return 0
    from datetime import UTC, datetime, timedelta

    cutoff = (datetime.now(UTC) - timedelta(days=older_than_days)).isoformat()
    try:
        with sqlite3.connect(path) as connection:
            cursor = connection.execute("DELETE FROM runs WHERE created_at < ?", (cutoff,))
            connection.commit()
            return cursor.rowcount
    except (sqlite3.Error, OSError) as e:
        raise StorageError("Falha ao expurgar registros do banco local.") from e
