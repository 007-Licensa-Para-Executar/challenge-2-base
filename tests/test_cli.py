import io
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from agents.extractor import cli
from agents.extractor.contracts import (
    ErrorInfo,
    Extraction,
    ProcessingResult,
    RunMetadata,
    ValidationMetrics,
)


@pytest.fixture
def success(monkeypatch):
    class FakeExtractor:
        def __init__(self, settings):
            self.settings = settings

        def extract(self, text):
            assert "família" in text
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
                metadata=RunMetadata(model=self.settings.model),
            )

    monkeypatch.setattr(cli, "OllamaExtractor", FakeExtractor)


@pytest.mark.parametrize("file_input", [False, True])
def test_unicode_input_saved(tmp_path, monkeypatch, capsys, success, file_input):
    db_path = tmp_path / "runs.db"
    args = ["--synthetic", "--db", str(db_path), "--model", "fake:1b"]
    text = "Minha família fictícia está feliz."
    if file_input:
        path = tmp_path / "example.txt"
        path.write_text(text, encoding="utf-8")
        args += ["--file", str(path)]
    else:
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["extraction"]["tema"] == "familia"
    assert json.loads(captured.out)["validation"]["nlp_polaridade"] == "POSITIVO"
    assert not captured.err
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT input_text FROM runs").fetchone()[0] == text


def test_no_synthetic_does_not_read_or_store(tmp_path, capsys):
    path = tmp_path / "runs.db"
    assert cli.main(["--db", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert not path.exists()


def test_invalid_unicode_file(tmp_path, capsys):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff")
    assert cli.main(["--synthetic", "--file", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "input_read_error"


def test_model_failure_persisted_without_extraction(tmp_path, monkeypatch, capsys):
    class Broken:
        def __init__(self, settings):
            pass

        def extract(self, text):
            return ProcessingResult(
                status="error",
                error=ErrorInfo(code="model_unavailable", message="Modelo indisponível."),
                metadata=RunMetadata(model="fake"),
            )

    monkeypatch.setattr(cli, "OllamaExtractor", Broken)
    monkeypatch.setattr(sys, "stdin", io.StringIO("RELATO SINTÉTICO PRIVADO"))
    path = tmp_path / "runs.db"
    assert cli.main(["--synthetic", "--db", str(path)]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["extraction"] is None
    assert "PRIVADO" not in captured.err
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT status FROM runs").fetchone()[0] == "error"


def test_storage_failure_removes_extraction(tmp_path, monkeypatch, capsys, success):
    monkeypatch.setattr(sys, "stdin", io.StringIO("Minha família fictícia."))
    assert cli.main(["--synthetic", "--db", str(tmp_path)]) == 3
    output = json.loads(capsys.readouterr().out)
    assert output["extraction"] is None
    assert output["error"]["code"] == "storage_error"


@pytest.mark.parametrize("arguments", [["--unknown", "PRIVATE"], ["--synthetic"]])
def test_subprocess_error_output_json(arguments):
    completed = subprocess.run(
        [sys.executable, "-m", "agents.extractor", *arguments],
        input="",
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["extraction"] is None
    assert "PRIVATE" not in completed.stderr


def test_unexpected_provider_exception_is_sanitized(tmp_path, monkeypatch, capsys):
    class Broken:
        def __init__(self, settings):
            pass

        def extract(self, text):
            raise RuntimeError(text)

    monkeypatch.setattr(cli, "OllamaExtractor", Broken)
    monkeypatch.setattr(sys, "stdin", io.StringIO("PRIVATE SYNTHETIC EXAMPLE"))
    assert cli.main(["--synthetic", "--db", str(tmp_path / "runs.db")]) == 2
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err
    assert json.loads(captured.out)["extraction"] is None


@pytest.mark.parametrize("text", ["", "   ", "a" * 2401, "😀" * 601])
def test_invalid_input_never_persisted(text, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    path = tmp_path / "runs.db"
    assert cli.main(["--synthetic", "--db", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "invalid_input"
    assert not path.exists()


def test_home_expansion_failure_returns_storage_error(tmp_path, monkeypatch, capsys, success):
    def fail_expanduser(self):
        raise RuntimeError("usuario_inexistente")

    db_path = tmp_path / "runs.db"
    monkeypatch.setattr(Path, "expanduser", fail_expanduser)
    monkeypatch.setattr(sys, "stdin", io.StringIO("Minha família fictícia."))
    assert cli.main(["--synthetic", "--db", str(db_path)]) == 3
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["error"]["code"] == "storage_error"
    assert output["extraction"] is None
    assert "Traceback" not in captured.out + captured.err
    assert "usuario_inexistente" not in captured.out + captured.err
    assert not db_path.exists()
