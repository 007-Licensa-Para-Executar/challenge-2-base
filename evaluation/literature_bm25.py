"""Baseline BM25 dos dois artigos reais. Não altera o ranking.

O gabarito de passagens foi lido no texto e não é exaustivo. Recall@k é a
cobertura desse conjunto anotado, não o recall do corpus. A nota do BM25
ordena trechos; não é probabilidade de acerto.

Perguntas sem evidência ficam fora de precisão, recall, MRR e hit rate.
Elas entram só na abstenção e no falso positivo, medidos depois do filtro
de dois termos no mesmo trecho. Um trecho recuperado que não está no
gabarito fica como não anotado: isso não prova que ele seja irrelevante.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents.copilot.contracts import DiaryRecord
from agents.copilot.literature import (
    RETRIEVAL_POOL,
    LiteratureStore,
    literature_evidence,
    select_literature_passages,
)
from agents.copilot.retriever import Retriever

GOLD = Path(__file__).resolve().parent.parent / "knowledge_base/literature/benchmark/questions.jsonl"
EXPECTED_HASHES = {
    "PT-001": "0acc0a84132ca8118ed0427464239e9471a44b9b1e99ddd33006bbc7eb8992b6",
    "PT-002": "0567fe58f3c3ca13c0b553a4dd16aada862394fdcbe48399ce3414cbc0183a92",
}
SUPPORT = {"direta", "parcial"}
LABELS = SUPPORT | {"redundante"}
CUTOFFS = (1, 3, 5)


def load_questions(path: Path = GOLD) -> list[dict[str, Any]]:
    questions = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    validate_questions(questions)
    return questions


def validate_questions(questions: list[dict[str, Any]]) -> None:
    if not questions:
        raise ValueError("O benchmark precisa de perguntas")
    if len({item["query_id"] for item in questions}) != len(questions):
        raise ValueError("Identificadores de pergunta repetidos")
    for item in questions:
        passages = item["passages"]
        negative = item["expected_abstention"]
        documents = set(item["relevant_documents"])
        if negative != (not passages):
            raise ValueError(f"{item['query_id']}: abstenção e passagens divergem")
        if negative != (not documents):
            raise ValueError(f"{item['query_id']}: abstenção e documentos divergem")
        ids = [passage["chunk_id"] for passage in passages]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{item['query_id']}: passagem repetida")
        if not negative and not any(passage["label"] == "direta" for passage in passages):
            raise ValueError(f"{item['query_id']}: falta passagem direta")
        for passage in passages:
            if passage["label"] not in LABELS:
                raise ValueError(f"{item['query_id']}: rótulo inválido")
            if passage["document_id"] not in documents:
                raise ValueError(f"{item['query_id']}: documento fora do gabarito")
            if not passage["chunk_id"].startswith(passage["document_id"] + "_"):
                raise ValueError(f"{item['query_id']}: chunk de outro documento")


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _cutoff(rows: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    return rows[:k]


def score_run(
    questions: list[dict[str, Any]],
    retrieved: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """retrieved[id] = {ranked: [{chunk_id, document_id}], kept: {1|3|5: [chunk_id]}}."""
    validate_questions(questions)
    metrics = {k: [] for k in CUTOFFS}
    details = []
    for item in questions:
        query_id = item["query_id"]
        found = retrieved[query_id]
        ranked = found["ranked"]
        support = {p["chunk_id"] for p in item["passages"] if p["label"] in SUPPORT}
        groups = {p["chunk_id"]: p["group"] for p in item["passages"] if p.get("group")}
        documents = set(item["relevant_documents"])
        row = {"query_id": query_id, "category": item["category"], "cutoffs": {}}
        for k in CUTOFFS:
            top = _cutoff(ranked, k)
            ids = [chunk["chunk_id"] for chunk in top]
            docs = [chunk["document_id"] for chunk in top]
            kept = found["kept"][k]
            if item["expected_abstention"]:
                point = {
                    "abstained": not kept,
                    "false_positive": bool(kept),
                    "ranked_nonempty": bool(top),
                }
            else:
                hits = [index for index, doc in enumerate(docs, start=1) if doc in documents]
                support_ranks = [index for index, chunk_id in enumerate(ids, start=1) if chunk_id in support]
                support_hits = [chunk_id for chunk_id in ids if chunk_id in support]
                seen: set[str] = set()
                redundant = 0
                for chunk_id in ids:
                    group = groups.get(chunk_id)
                    if group and group in seen:
                        redundant += 1
                    if group:
                        seen.add(group)
                point = {
                    "precision_at_k": len(support_hits) / k,
                    "annotated_recall_at_k": len(support_hits) / len(support),
                    "hit_at_k": bool(hits),
                    "mrr_at_k": (1 / hits[0]) if hits else 0.0,
                    "passage_mrr_at_k": (1 / support_ranks[0]) if support_ranks else 0.0,
                    "redundancy_at_k": redundant / k,
                    "unannotated_at_k": len([chunk for chunk in ids if chunk not in groups and chunk not in support]) / k,
                    "answer_hit_at_k": any(chunk.split("_", 1)[0] in documents for chunk in kept),
                }
            row["cutoffs"][str(k)] = point
            metrics[k].append(point)
        details.append(row)
    summary = {}
    for k, points in metrics.items():
        positive = [point for point in points if "precision_at_k" in point]
        negative = [point for point in points if "abstained" in point]
        summary[str(k)] = {
            "precision_at_k": _mean([point["precision_at_k"] for point in positive]),
            "annotated_recall_at_k": _mean([point["annotated_recall_at_k"] for point in positive]),
            "hit_rate_at_k": _mean([float(point["hit_at_k"]) for point in positive]),
            "mrr_at_k": _mean([point["mrr_at_k"] for point in positive]),
            "passage_mrr_at_k": _mean([point["passage_mrr_at_k"] for point in positive]),
            "redundancy_at_k": _mean([point["redundancy_at_k"] for point in positive]),
            "unannotated_at_k": _mean([point["unannotated_at_k"] for point in positive]),
            "answer_hit_rate_at_k": _mean([float(point["answer_hit_at_k"]) for point in positive]),
            "correct_abstention_rate": _mean([float(point["abstained"]) for point in negative]),
            "false_positives": sum(point["false_positive"] for point in negative),
            "ranking_nonempty_on_abstention": sum(point["ranked_nonempty"] for point in negative),
        }
    return {
        "gold_scope": "passagens lidas e anotadas; recall não é o do corpus",
        "bm25_score_is": "ranking, não probabilidade",
        "negative_questions_excluded_from": ["precision", "recall", "mrr", "hit_rate"],
        "questions": len(questions),
        "positive_questions": sum(not item["expected_abstention"] for item in questions),
        "negative_questions": sum(item["expected_abstention"] for item in questions),
        "categories": dict(Counter(name for item in questions for name in item["category"])),
        "metrics": summary,
        "details": details,
    }


def _body_records(documents) -> list[DiaryRecord]:
    records = []
    for document in documents:
        when = datetime(document.year or 2026, 1, 1, tzinfo=UTC)
        for section in document.sections:
            if section.role != "body":
                continue
            records.append(
                DiaryRecord(
                    record_id=section.record_id,
                    patient_id="literature",
                    recorded_at=when,
                    original_text=section.text,
                    source_title=document.title[:200],
                )
            )
    return records


def _stored_hashes(path: Path) -> dict[str, str]:
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        rows = conn.execute(
            "SELECT document_id, text_hash FROM literature_documents ORDER BY document_id"
        ).fetchall()
    return dict(rows)


def run_benchmark(
    db_path: Path,
    questions: list[dict[str, Any]],
    *,
    diversify: bool = False,
    quantity: bool = False,
) -> dict[str, Any]:
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    hashes = _stored_hashes(db_path)
    if hashes != EXPECTED_HASHES:
        raise RuntimeError("A base experimental não é a coleção validada de PT-001 e PT-002")
    documents = LiteratureStore(db_path).list_documents()
    records = _body_records(documents)
    known = {chunk_id for document in documents for chunk_id in document.chunk_ids}
    missing = [
        passage["chunk_id"]
        for item in questions
        for passage in item["passages"]
        if passage["chunk_id"] not in known
    ]
    if missing:
        raise RuntimeError(f"Gabarito cita chunk ausente: {missing[0]}")
    retriever = Retriever(backend="bm25")
    retrieved = {}
    latencies = []
    previews = {}
    pool = RETRIEVAL_POOL if diversify else 5
    for item in questions:
        started = time.perf_counter()
        ranked_pool = retriever.search(records, item["question"], top_k=pool)
        ranked = (
            select_literature_passages(item["question"], ranked_pool, 5, quantity=quantity)
            if diversify else ranked_pool
        )
        latencies.append((time.perf_counter() - started) * 1000)
        packed = [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.chunk_id.split("_", 1)[0],
                "score": chunk.score,
            }
            for chunk in ranked
        ]
        retrieved[item["query_id"]] = {
            "ranked": packed,
            "kept": {
                k: [
                    chunk.chunk_id
                    for chunk in literature_evidence(item["question"], ranked[:k], quantity=quantity)
                ]
                for k in CUTOFFS
            },
        }
        previews[item["query_id"]] = [
            {"chunk_id": chunk.chunk_id, "quote": " ".join(chunk.quote.split())[:180]}
            for chunk in ranked
        ]
    result = score_run(questions, retrieved)
    result["database"] = str(db_path)
    result["diversify"] = diversify
    result["quantity"] = quantity
    result["candidate_pool"] = pool
    result["documents"] = [
        {
            "document_id": document.document_id,
            "text_sha256": hashes[document.document_id],
            "chunks": len(document.chunk_ids),
            "body_chunks": sum(len(section.chunk_ids) for section in document.sections if section.role == "body"),
        }
        for document in documents
    ]
    result["latency_ms"] = {
        "mean": _mean(latencies),
        "max": max(latencies) if latencies else None,
    }
    result["previews"] = previews
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=GOLD)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--diversify", action="store_true")
    parser.add_argument("--quantity", action="store_true")
    args = parser.parse_args(argv)
    if not args.db.is_file():
        print("Base experimental ausente. Esta fase não recria o arquivo.", file=sys.stderr)
        return 2
    result = run_benchmark(
        args.db, load_questions(args.questions), diversify=args.diversify, quantity=args.quantity
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
