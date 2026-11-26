import io
import json

from agents.copilot.literature import LiteratureStore, ingest_file, literature_test_scope
from agents.copilot.literature_http import main, parse_request


def test_request_rejects_a_browser_database_and_bad_limits():
    assert parse_request({"query": "  ", "top_k": 5}) == "empty_query"
    assert parse_request({"query": "x" * 2001}) == "query_too_long"
    assert parse_request({"query": "ética", "top_k": True}) == "invalid_top_k"
    assert parse_request({"query": "ética", "top_k": 0}) == "invalid_top_k"
    assert parse_request({"query": "ética", "db_path": "/tmp/outro.sqlite3"}) == "db_path_forbidden"
    assert parse_request([]) == "invalid_body"
    assert parse_request({"query": " ética da IA "}) == ("ética da IA", 5)


def test_bridge_reports_an_inaccessible_database(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LITERATURE_DB_PATH", str(tmp_path / "ausente.sqlite3"))
    monkeypatch.setattr("sys.stdin", io.StringIO('{"query": "ética"}'))
    assert main() == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "configuration_error"
    assert body["error_code"] == "database_unavailable"
    assert "ausente.sqlite3" not in json.dumps(body)


def test_bridge_reports_a_missing_database(monkeypatch, capsys):
    monkeypatch.delenv("LITERATURE_DB_PATH", raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO('{"query": "ética"}'))
    assert main() == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "configuration_error"
    assert body["error_code"] == "database_unconfigured"
    assert body["evidence_sufficient"] is False


def test_bridge_reports_an_unreadable_database(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "ruim.sqlite3"
    bad.write_bytes(b"nao e sqlite")
    monkeypatch.setenv("LITERATURE_DB_PATH", str(bad))
    monkeypatch.setattr("sys.stdin", io.StringIO('{"query": "ética"}'))
    assert main() == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "error"
    assert body["error_code"] == "storage_error"
    assert "ruim.sqlite3" not in json.dumps(body)


def test_bridge_keeps_citations_and_abstains_without_a_count(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    note = tmp_path / "nota.txt"
    note.write_text(
        "A discussão conclui que a psicoterapia mantém o cuidado humano.\n",
        encoding="utf-8",
    )
    db = tmp_path / "literatura.sqlite3"
    with literature_test_scope():
        ingest_file(
            LiteratureStore(db), note, document_id="nota_doi",
            title="Cuidado humano na psicoterapia", authors=["Autora Demo"],
            year=2024, doi="10.0000/cuidado",
        )
    monkeypatch.setenv("LITERATURE_DB_PATH", str(db))
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            '{"query": "O que a discussão conclui sobre o cuidado humano na psicoterapia?", '
            '"top_k": 5, "patient_id": "ana"}'
        ),
    )
    assert main() == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "evidence"
    assert body["retrieval_backend"] == "bm25"
    assert body["sources"][0]["doi"] == "10.0000/cuidado"
    assert "cuidado humano" in body["sources"][0]["quote_text"]
    assert "ana" not in json.dumps(body)

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"query": "Quantos autores a nota registra?"}'),
    )
    assert main() == 0
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "insufficient_evidence"
    assert missing["sources"] == []


def test_bridge_rejects_bad_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{"))
    assert main() == 2
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_json"


def test_bridge_cli_rejects_forbidden_database(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"query": "ética", "db_path": "/tmp/outro.sqlite3"}'),
    )
    assert main() == 2
    assert json.loads(capsys.readouterr().out)["error"] == "db_path_forbidden"
