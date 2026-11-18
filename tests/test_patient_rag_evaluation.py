"""Independent definitions of recall, hit rate, negatives and scoped fixtures."""

import pytest

from agents.copilot.contracts import DiaryRecord
from agents.copilot.retriever import Retriever, chunk_record
from evaluation.patient_rag import DEMO_ROOT, evaluate_patient_rag, load_jsonl, main


def diaries():
    return [DiaryRecord.model_validate(r) for r in load_jsonl(DEMO_ROOT / "diaries.jsonl")]


def test_demo_has_two_fictitious_people_and_no_unknown_gold():
    rows = diaries()
    assert len(rows) == 20
    assert {r.patient_id for r in rows} == {"patient_ana", "patient_bruno"}
    questions = load_jsonl(DEMO_ROOT / "questions.jsonl")
    report = evaluate_patient_rag(rows, questions, Retriever())
    assert report["questions"] == 12
    assert report["positive_questions"] == 8
    assert report["negative_questions"] == 4
    assert report["recall_at_k"] == 1
    assert report["hit_rate_at_k"] == 1
    # "cartão bancário" overlaps "cartão-postal": measure the known lexical
    # false positive rather than asserting that word overlap proves relevance.
    assert report["correct_abstention_rate"] == 0.75
    negative = next(d for d in report["details"] if d["query_id"] == "test_05")
    assert negative["retrieved_record_ids"] == ["bruno_10"]


def test_recall_counts_fraction_of_gold_not_any_hit():
    rows = diaries()[:3]

    class Partial(Retriever):
        def search(self, records, question, top_k=3):
            return chunk_record(records[0], 600)

    question = {
        "query_id": "one",
        "patient_id": "patient_ana",
        "question": "avós",
        "expected_record_ids": [r.record_id for r in rows],
        "expected_abstention": False,
    }
    result = evaluate_patient_rag(rows, [question], Partial())
    assert result["recall_at_k"] == 1 / 3
    assert result["hit_rate_at_k"] == 1
    assert result["correct_abstention_rate"] is None


def test_empty_benchmark_not_perfect_score_and_incorrect_gold_rejected():
    with pytest.raises(ValueError, match="at least one"):
        evaluate_patient_rag(diaries(), [], Retriever())
    question = {
        "query_id": "bad",
        "patient_id": "patient_ana",
        "question": "avós",
        "expected_record_ids": ["bruno_01"],
        "expected_abstention": False,
    }
    with pytest.raises(ValueError, match="authorized patient"):
        evaluate_patient_rag(diaries(), [question], Retriever())


def test_period_and_patient_scoped_before_retrieval():
    questions = [
        {
            "query_id": "empty",
            "patient_id": "patient_ana",
            "question": "avós",
            "start_at": "2026-12-01T00:00:00Z",
            "expected_record_ids": [],
            "expected_abstention": True,
        },
        {
            "query_id": "other_person",
            "patient_id": "patient_ana",
            "question": "astronomia telescópio",
            "expected_record_ids": [],
            "expected_abstention": True,
        },
    ]
    report = evaluate_patient_rag(diaries(), questions, Retriever())
    assert report["recall_at_k"] is None
    assert report["hit_rate_at_k"] is None
    assert report["correct_abstention_rate"] == 1
    assert report["details"][0]["eligible_records"] == 0


def test_evaluation_cli_writes_report(tmp_path, capsys):
    output = tmp_path / "pasta com espaços" / "results.json"
    assert main(["--split", "test", "--output", str(output)]) == 0
    import json

    report = json.loads(output.read_text())
    assert report["split"] == "test"
    assert report["questions"] == 6
    assert json.loads(capsys.readouterr().out) == report
