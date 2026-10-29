import json
import os
import sqlite3
from pathlib import Path

import pytest

from agents.extractor.contracts import (
    Extraction,
    ProcessingResult,
    RunMetadata,
    ValidationMetrics,
)
from agents.extractor.storage import StorageError, save_result


def result():
    return ProcessingResult(
        status="ok",
        extraction=Extraction(
            tema="familia", sentimento="alegria", indicio_textual_risco="nao_identificado"
        ),
        validation=ValidationMetrics(
            nlp_polaridade="POSITIVO",
            nlp_score=0.8,
            discrepancia_detectada=False,
            distancia_polaridade=0.2,
        ),
        metadata=RunMetadata(model="fake", model_digest="sha256:test"),
    )


def test_roundtrip_unicode_and_metadata(tmp_path):
    path = tmp_path / "private" / "runs.db"
    item = result()
    save_result(path, "Família fictícia, coração feliz.", item)
    with sqlite3.connect(path) as db:
        row = db.execute(
            """SELECT input_text, result_json, model_digest, synthetic, nlp_polaridade,
                      nlp_score, discrepancia_detectada, distancia_polaridade FROM runs"""
        ).fetchone()
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    assert row[0] == "Família fictícia, coração feliz."
    assert json.loads(row[1]) == json.loads(item.model_dump_json())
    assert row[2:] == ("sha256:test", 1, "POSITIVO", 0.8, 0, 0.2)
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600


def test_duplicate_rolls_back(tmp_path):
    path = tmp_path / "runs.db"
    item = result()
    save_result(path, "Texto sintético.", item)
    with pytest.raises(StorageError):
        save_result(path, "Outro texto sintético.", item)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1


@pytest.mark.parametrize("version", [0, 3])
def test_unknown_schema_untouched(tmp_path, version):
    path = tmp_path / "runs.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (value TEXT)")
        db.execute(f"PRAGMA user_version = {version}")
    with pytest.raises(StorageError):
        save_result(path, "Texto inventado.", result())
    with sqlite3.connect(path) as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='runs'").fetchall()


def test_existing_v1_database_is_migrated_without_losing_records(tmp_path):
    path = tmp_path / "runs.db"
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE runs (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, synthetic INTEGER NOT NULL,
            input_text TEXT NOT NULL, result_json TEXT NOT NULL, model TEXT NOT NULL,
            model_digest TEXT, prompt_version TEXT NOT NULL, schema_version TEXT NOT NULL,
            status TEXT NOT NULL
        )""")
        db.execute(
            "INSERT INTO runs VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)",
            ("existing", "2026-01-01T00:00:00+00:00", "texto sintético", "{}", "fake",
             None, "1.0.0", "1.0.0", "ok"),
        )
        db.execute("PRAGMA user_version = 1")
    item = result()
    save_result(path, "Novo relato sintético.", item)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("SELECT input_text FROM runs WHERE id='existing'").fetchone()[0] == (
            "texto sintético"
        )
        old_fields = db.execute(
            """SELECT nlp_polaridade, nlp_score, discrepancia_detectada, distancia_polaridade
               FROM runs WHERE id='existing'"""
        ).fetchone()
        assert old_fields == (None, None, None, None)
        new_fields = db.execute(
            """SELECT nlp_polaridade, nlp_score, discrepancia_detectada, distancia_polaridade
               FROM runs WHERE id=?""",
            (item.id,),
        ).fetchone()
        assert new_fields == ("POSITIVO", 0.8, 0, 0.2)


def test_storage_failure_sanitized(tmp_path):
    with pytest.raises(StorageError) as error:
        save_result(tmp_path, "SEGREDO DE TESTE", result())
    assert "SEGREDO" not in str(error.value)


def test_home_expansion_failure_is_sanitized(tmp_path, monkeypatch):
    path = tmp_path / "private_user" / "db.sqlite"

    def fail_expanduser(self):
        assert self == path
        raise RuntimeError(f"Cannot expand home directory: {self}")

    monkeypatch.setattr(Path, "expanduser", fail_expanduser)
    with pytest.raises(StorageError) as error:
        save_result(path, "SINTETICO", result())
    assert str(error.value) == "Não foi possível salvar a execução no banco local."
    assert isinstance(error.value.__cause__, RuntimeError)
    assert not path.parent.exists()
