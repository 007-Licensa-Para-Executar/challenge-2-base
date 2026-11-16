"""Small synthetic retrieval benchmark; record-level relevance and explicit negatives.

This evaluates retrieval only. It does not evaluate generated answer faithfulness,
clinical performance, user benefit, or classifier quality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.retriever import Retriever

DEMO_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base" / "patient_demo"


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def scoped_records(records: list[DiaryRecord], query: Query) -> list[DiaryRecord]:
    return [
        r
        for r in records
        if r.patient_id == query.patient_id
        and (query.start_at is None or r.recorded_at >= query.start_at)
        and (query.end_at is None or r.recorded_at <= query.end_at)
    ]


def evaluate_patient_rag(
    records: list[DiaryRecord],
    questions: list[dict[str, Any]],
    retriever: Retriever,
    top_k: int = 3,
) -> dict[str, Any]:
    if not questions:
        raise ValueError("Benchmark requires at least one question")
    if len({q["query_id"] for q in questions}) != len(questions):
        raise ValueError("Benchmark query IDs must be unique")
    recalls, hits, abstentions, details = [], [], [], []
    for item in questions:
        query = Query.model_validate(
            {key: item.get(key) for key in ("patient_id", "question", "start_at", "end_at")}
        )
        eligible = scoped_records(records, query)
        gold = set(item["expected_record_ids"])
        negative = item["expected_abstention"]
        if not isinstance(negative, bool) or negative == bool(gold):
            raise ValueError("Negative questions need no gold; positive questions need gold")
        if not gold.issubset({r.record_id for r in eligible}):
            raise ValueError("Gold records must belong to the authorized patient and period")
        evidence = retriever.search(eligible, query.question, top_k=top_k)
        returned = {e.record_id for e in evidence}
        if not returned.issubset({r.record_id for r in eligible}):
            raise ValueError("Retriever returned records outside its scope")
        recall = len(gold & returned) / len(gold) if gold else None
        hit = bool(gold & returned) if gold else None
        if negative:
            abstentions.append(not evidence)
        else:
            recalls.append(recall)
            hits.append(hit)
        details.append(
            {
                "query_id": item["query_id"],
                "split": item.get("split"),
                "patient_id": query.patient_id,
                "eligible_records": len(eligible),
                "expected_record_ids": sorted(gold),
                "retrieved_record_ids": sorted(returned),
                "retrieved_chunk_ids": [e.chunk_id for e in evidence],
                "expected_abstention": negative,
                "abstained": not evidence,
                "recall_at_k": recall,
                "hit_at_k": hit,
            }
        )
    return {
        "scope": "synthetic record-level retrieval; not generated-answer evaluation",
        "backend": retriever.backend,
        "top_k_chunks": top_k,
        "min_score": retriever.min_score,
        "chunk_chars": retriever.chunk_chars,
        "questions": len(questions),
        "positive_questions": len(recalls),
        "negative_questions": len(abstentions),
        "recall_at_k": sum(recalls) / len(recalls) if recalls else None,
        "hit_rate_at_k": sum(hits) / len(hits) if hits else None,
        "correct_abstention_rate": sum(abstentions) / len(abstentions) if abstentions else None,
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEMO_ROOT)
    parser.add_argument("--db", type=Path, help="Evaluate records already saved in a demo database")
    parser.add_argument("--backend", choices=["bm25", "e5"], default="bm25")
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--min-score", type=float)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    questions = load_jsonl(args.fixtures / "questions.jsonl")
    if args.split != "all":
        questions = [q for q in questions if q["split"] == args.split]
    if args.db:
        from agents.copilot.storage import DiaryStore

        store = DiaryStore(args.db)
        # Store exposes one explicitly scoped read, never an all-patients query.
        records = []
        for patient in sorted({q["patient_id"] for q in questions}):
            records.extend(store.list_records(Query(patient_id=patient, question="benchmark")))
    else:
        records = [
            DiaryRecord.model_validate(r) for r in load_jsonl(args.fixtures / "diaries.jsonl")
        ]
    retriever = Retriever(args.backend, args.model_path, min_score=args.min_score)
    result = evaluate_patient_rag(records, questions, retriever, args.top_k)
    result["split"] = args.split
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
