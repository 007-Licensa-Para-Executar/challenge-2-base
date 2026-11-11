"""Suficiência por maioria de termos, separada do score BM25."""

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.retriever import Retriever, supported_evidence
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore
from evaluation.patient_rag import DEMO_ROOT, evaluate_patient_rag, load_jsonl

ROOT = DEMO_ROOT / "sufficiency"


def corpus():
    return [DiaryRecord.model_validate(row) for row in load_jsonl(ROOT / "diaries.jsonl")]


def report(split):
    questions = [row for row in load_jsonl(ROOT / "questions.jsonl") if row["split"] == split]
    return evaluate_patient_rag(corpus(), questions, Retriever())


def test_majority_rejects_a_single_shared_term_and_keeps_a_covering_quote():
    records = corpus()
    retriever = Retriever()
    card = retriever.search(records, "Qual é a senha do cartão bancário?")
    assert card
    assert supported_evidence("Qual é a senha do cartão bancário?", card, "patient_clara") == []
    work = retriever.search(records, "O que foi registrado sobre trabalho e reunião?")
    kept = supported_evidence(
        "O que foi registrado sobre trabalho e reunião?", work, "patient_clara"
    )
    assert [item.record_id for item in kept] == ["clara_06"]
    original = next(row for row in records if row.record_id == "clara_06").original_text
    assert kept[0].quote == original[kept[0].start_char : kept[0].end_char]
    assert kept[0].chunk_id == f"clara_06:{kept[0].start_char}:{kept[0].end_char}"


def test_development_gate_removes_false_positives_without_losing_gold():
    result = report("dev")
    assert result["retrieval_false_positives"] == 2
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["recall_at_k"] == 1
    assert result["hit_rate_at_k"] == 1
    assert result["correct_abstention_rate"] == 1
    bike = next(item for item in result["details"] if item["query_id"] == "dev_bike")
    assert bike["retrieved_record_ids"] == ["clara_07", "clara_08"]


def test_held_out_cases_keep_context_and_record_lexical_limits(tmp_path):
    result = report("test")
    by_id = {item["query_id"]: item for item in result["details"]}
    assert by_id["test_synonym"]["false_negative"] is True
    assert by_id["test_synonym"]["retrieved_record_ids"] == []
    assert by_id["test_split"]["abstained"] is True
    assert by_id["test_split"]["retrieval_false_positive"] is True
    assert by_id["test_partial"]["false_positive"] is False
    assert by_id["test_credit"]["false_positive"] is False
    assert by_id["test_multi"]["abstained"] is True
    assert by_id["test_who"]["retrieved_record_ids"] == ["clara_04", "clara_05"]
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 1
    assert result["recall_at_k"] == 0.5
    store = DiaryStore(tmp_path / "clara.sqlite3")
    for record in corpus():
        store.save(record)
    other = DiaryRecord(
        record_id="ana_99",
        patient_id="patient_ana",
        recorded_at="2026-11-04T12:00:00Z",
        original_text="Cozinhei para os avós e dividi os cuidados com a minha irmã.",
    )
    store.save(other)
    answer = CopilotService(store, Retriever()).answer(
        Query(patient_id="patient_clara", question="Quem ajudou nos cuidados com os avós?"),
        "extractive",
    )
    assert answer.status == "ok"
    assert {item.record_id for item in answer.evidence} == {"clara_04", "clara_05"}
    assert all(item.patient_id == "patient_clara" for item in answer.evidence)
    denied = CopilotService(store, Retriever()).answer(
        Query(patient_id="patient_clara", question="Qual é a senha do cartão de crédito?"),
        "extractive",
    )
    assert denied.status == "insufficient_evidence"
    assert denied.evidence == []
