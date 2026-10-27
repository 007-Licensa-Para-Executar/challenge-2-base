import json
import os
import sqlite3

import pytest

from agents.extractor.contracts import Extraction, ProcessingResult, RunMetadata
from agents.extractor.storage import StorageError, save_result


def result():
    return ProcessingResult(
        status="ok",
        extraction=Extraction(
            tema="familia", sentimento="alegria", indicio_textual_risco="nao_identificado"
        ),
        metadata=RunMetadata(model="fake", model_digest="sha256:test"),
    )


def test_roundtrip_unicode_and_metadata(tmp_path):
    path = tmp_path / "private" / "runs.db"
    item = result()
    save_result(path, "Família fictícia, coração feliz.", item)
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT input_text, result_json, model_digest, synthetic FROM runs"
        ).fetchone()
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
    assert row[0] == "Família fictícia, coração feliz."
    assert json.loads(row[1]) == json.loads(item.model_dump_json())
    assert row[2:] == ("sha256:test", 1)
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


@pytest.mark.parametrize("version", [0, 2])
def test_unknown_schema_untouched(tmp_path, version):
    path = tmp_path / "runs.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (value TEXT)")
        db.execute(f"PRAGMA user_version = {version}")
    with pytest.raises(StorageError):
        save_result(path, "Texto inventado.", result())
    with sqlite3.connect(path) as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='runs'").fetchall()


def test_storage_failure_sanitized(tmp_path):
    with pytest.raises(StorageError) as error:
        save_result(tmp_path, "SEGREDO DE TESTE", result())
    assert "SEGREDO" not in str(error.value)


def test_unknown_home_user_is_sanitized():
    with pytest.raises(StorageError) as error:
        save_result("~usuario_inexistente_extractor_725ef3/db.sqlite", "SINTETICO", result())
    assert "usuario_inexistente" not in str(error.value)
