"""Integration checks of context, citations and clean-checkout CLI behaviour."""

import json
import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

from agents.copilot.cli import main
from agents.copilot.contracts import DiaryRecord, DraftAnswer, Query, Statement, ThemePrediction
from agents.copilot.model import GenerationError
from agents.copilot.retriever import Retriever
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore


def test_utf8_file_crlf_and_redirected_legacy_console(tmp_path):
    original = "Texto fictício: avós e família.\r\nAnotação com emoji 📝."
    source = tmp_path / "anotação com espaço.txt"
    source.write_bytes(original.encode("utf-8"))
    db = tmp_path / "arquivo.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agents.copilot",
            "ingest",
            "--synthetic",
            "--patient-id",
            "ana",
            "--at",
            "2026-11-09T12:00:00Z",
            "--file",
            str(source),
            "--db",
            str(db),
        ],
        env={**os.environ, "PYTHONIOENCODING": "ascii"},
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    assert json.loads(result.stdout)["original_text"] == original
    assert (
        DiaryStore(db).list_records(Query(patient_id="ana", question="avós"))[0].original_text
        == original
    )


@pytest.fixture
def store(tmp_path):
    value = DiaryStore(tmp_path / "pasta com espaços" / "diários.sqlite3")
    for patient, record_id, date in [
        ("ana", "a1", "2026-11-02T12:00:00Z"),
        ("ana", "a_old", "2026-01-02T12:00:00Z"),
        ("bruno", "b1", "2026-11-02T12:00:00Z"),
    ]:
        value.save(
            DiaryRecord(
                record_id=record_id,
                patient_id=patient,
                recorded_at=date,
                original_text="Levei meus avós à consulta e preparei almoço.",
                classification=ThemePrediction(status="error", error_code="missing_model"),
            )
        )
    return value


def test_extractive_uses_raw_text_despite_failed_classifier(store):
    query = Query(patient_id="ana", question="avós consulta", start_at="2026-11-01T00:00:00Z")
    result = CopilotService(store, Retriever()).answer(query, "extractive")
    assert result.status == "ok"
    assert result.eligible_records == 1
    assert result.theme_counts == {}
    assert {ev.record_id for ev in result.evidence} == {"a1"}
    assert "sem síntese por LLM" in result.answer


def test_extractive_rejects_ranked_text_that_shares_no_whole_term(store):
    query = Query(patient_id="ana", question="Qual é a senha do cartão bancário?")
    ranked = Retriever().search(
        store.list_records(Query(patient_id="ana", question="avós")), "avós"
    )
    retriever = Mock(backend="bm25")
    retriever.search.return_value = ranked
    generator = Mock(model="fake")
    result = CopilotService(store, retriever, generator).answer(query, "extractive")
    assert result.status == "insufficient_evidence"
    assert result.evidence == []
    generator.generate.assert_not_called()


def test_extractive_demo_keeps_supported_quotes_and_abstains_without_them(tmp_path):
    from evaluation.patient_rag import DEMO_ROOT, load_jsonl

    store = DiaryStore(tmp_path / "demo.sqlite3")
    for row in load_jsonl(DEMO_ROOT / "diaries.jsonl"):
        store.save(DiaryRecord.model_validate(row))
    service = CopilotService(store, Retriever())
    denied = service.answer(
        Query(patient_id="patient_bruno", question="Qual é a senha do cartão bancário?"),
        "extractive",
    )
    assert denied.status == "insufficient_evidence"
    assert denied.evidence == []
    kept = service.answer(
        Query(patient_id="patient_ana", question="Quais cuidados dos avós foram descritos?"),
        "extractive",
    )
    assert kept.status == "ok"
    assert {item.record_id for item in kept.evidence} == {"ana_01", "ana_03", "ana_05"}
    saved = {
        item.record_id: item
        for item in store.list_records(Query(patient_id="patient_ana", question="avós"))
    }
    for item in kept.evidence:
        assert item.quote == saved[item.record_id].original_text[item.start_char : item.end_char]
        assert item.chunk_id == f"{item.record_id}:{item.start_char}:{item.end_char}"


def test_empty_window_skips_retrieval_and_generation(store):
    retriever = Mock(backend="bm25")
    generator = Mock(model="fake")
    result = CopilotService(store, retriever, generator).answer(
        Query(patient_id="ana", question="avós", start_at="2027-01-01T00:00:00Z")
    )
    assert result.status == "insufficient_evidence"
    assert result.eligible_records == 0
    retriever.search.assert_not_called()
    generator.generate.assert_not_called()


def test_wrong_scope_from_store_is_rejected_before_retrieval():
    store = Mock()
    store.list_records.return_value = [
        DiaryRecord(
            patient_id="other",
            recorded_at="2026-11-01T00:00:00Z",
            original_text="texto de outra pessoa",
        )
    ]
    retriever = Mock(backend="bm25")
    result = CopilotService(store, retriever).answer(Query(patient_id="ana", question="texto"))
    assert result.error_code == "context_mismatch"
    retriever.search.assert_not_called()


def test_invalid_evidence_never_reaches_generator(store):
    query = Query(patient_id="ana", question="avós")
    ev = Retriever().search(store.list_records(query), query.question)[0]
    retriever = Mock(backend="bm25")
    retriever.search.return_value = [ev.model_copy(update={"quote": "trecho fabricado"})]
    generator = Mock(model="fake")
    result = CopilotService(store, retriever, generator).answer(query)
    assert result.error_code == "invalid_evidence"
    generator.generate.assert_not_called()


def test_generation_preserves_backend_counts_and_sources(store):
    query = Query(patient_id="ana", question="avós", start_at="2026-11-01T00:00:00Z")
    generator = Mock(model="fake")
    generator.generate.side_effect = lambda q, ev: DraftAnswer(
        statements=[
            Statement(
                text="O relato menciona uma consulta dos avós.", evidence_ids=[ev[0].chunk_id]
            )
        ]
    )
    result = CopilotService(store, Retriever(), generator).answer(query)
    assert result.status == "ok"
    assert result.eligible_records == 1
    assert result.evidence[0].quote == store.list_records(query)[0].original_text
    assert result.evidence[0].chunk_id in result.answer


@pytest.mark.parametrize(
    "code,status",
    [
        ("service_unavailable", "error"),
        ("invalid_response", "error"),
        ("insufficient_evidence", "insufficient_evidence"),
    ],
)
def test_generation_failure_is_not_replaced_with_a_fake_dossier(store, code, status):
    generator = Mock(model="fake")
    generator.generate.side_effect = GenerationError(code)
    result = CopilotService(store, Retriever(), generator).answer(
        Query(patient_id="ana", question="avós")
    )
    assert result.status == status
    assert result.evidence == []
    assert result.error_code == (code if status == "error" else None)


def test_unknown_citation_rejected_even_for_custom_generator(store):
    generator = Mock(model="fake")
    generator.generate.return_value = DraftAnswer(
        statements=[Statement(text="afirmação", evidence_ids=["fake"])]
    )
    result = CopilotService(store, Retriever(), generator).answer(
        Query(patient_id="ana", question="avós")
    )
    assert result.error_code == "invalid_citation"


def test_structured_schema_and_service_allow_generator_abstention(store):
    assert DraftAnswer.model_validate({"statements": []}).statements == []
    assert DraftAnswer.model_json_schema()["properties"]["statements"].get("minItems", 0) == 0
    generator = Mock(model="fake")
    generator.generate.return_value = DraftAnswer(statements=[])
    result = CopilotService(store, Retriever(), generator).answer(
        Query(patient_id="ana", question="avós")
    )
    assert result.status == "insufficient_evidence"
    assert result.evidence == []


def test_seed_query_list_and_idempotent_seed_from_clean_checkout(tmp_path, capsys):
    db = str(tmp_path / "espaço" / "diários.sqlite3")
    assert main(["seed", "--db", db, "--synthetic"]) == 0
    assert json.loads(capsys.readouterr().out)["saved"] == 20
    assert main(["seed", "--db", db, "--synthetic"]) == 0
    assert json.loads(capsys.readouterr().out)["skipped"] == 20
    assert (
        main(
            [
                "ask",
                "avós",
                "--patient-id",
                "patient_ana",
                "--db",
                db,
                "--generation",
                "extractive",
                "--from",
                "2026-11-01T00:00:00Z",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert all(e["patient_id"] == "patient_ana" for e in result["evidence"])
    assert main(["list", "--patient-id", "patient_bruno", "--db", db]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 10


def test_cli_invalid_window_and_missing_database_do_not_create_it(tmp_path, capsys):
    db = str(tmp_path / "absent.sqlite3")
    assert (
        main(
            [
                "ask",
                "avós",
                "--patient-id",
                "ana",
                "--db",
                db,
                "--from",
                "2026-12-01T00:00:00Z",
                "--to",
                "2026-01-01T00:00:00Z",
            ]
        )
        == 2
    )
    assert capsys.readouterr().out == ""
    assert not (tmp_path / "absent.sqlite3").exists()
    assert main(["list", "--patient-id", "ana", "--db", db]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert not (tmp_path / "absent.sqlite3").exists()


def test_cli_records_explicit_classification_error_without_losing_original(tmp_path, capsys):
    db = str(tmp_path / "new.sqlite3")
    assert (
        main(
            [
                "ingest",
                "--patient-id",
                "ana",
                "--at",
                "2026-11-09T12:00:00Z",
                "--text",
                "Relato fictício sobre os avós.",
                "--record-id",
                "new1",
                "--db",
                db,
                "--synthetic",
                "--classify",
                "--model-path",
                str(tmp_path / "missing.pt"),
            ]
        )
        == 1
    )
    result = json.loads(capsys.readouterr().out)
    assert result["classification"]["status"] == "error"
    assert result["classification"]["primary_theme"] is None
    assert (
        DiaryStore(db).list_records(Query(patient_id="ana", question="avós"))[0].original_text
        == result["original_text"]
    )
