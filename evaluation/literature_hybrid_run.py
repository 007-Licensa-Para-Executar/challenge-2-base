"""Ensaio isolado BM25, E5 e fusão. Não grava vetor nem altera o produto.

A coluna E5 e a fusão crua só ordenam. A resposta sai do BM25 atual e da
fusão que passa pela diversificação e pela suficiência já existentes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

from agents.copilot.literature import (
    RETRIEVAL_POOL,
    LiteratureStore,
    literature_evidence,
    select_literature_passages,
)
from agents.copilot.retriever import Retriever, chunk_record
from evaluation.literature_bm25 import (
    CUTOFFS,
    EXPECTED_HASHES,
    GOLD,
    SUPPORT,
    _body_records,
    _stored_hashes,
    load_questions,
    run_benchmark,
    score_run,
)
from evaluation.literature_hybrid_protocol import (
    MODEL_DIR,
    MODEL_REVISION,
    TOKEN_BUDGET,
    VALIDATION,
    VALIDATION_SHA256,
    assert_token_budget,
    embedding_cache_key,
    reciprocal_rank_fusion,
)

RANKING = (
    "precision_at_k",
    "annotated_recall_at_k",
    "passage_mrr_at_k",
    "redundancy_at_k",
)


def recovered_outside(
    support: list[str], lexical_top: list[str], other_top: list[str]
) -> tuple[list[str], list[str]]:
    """Passagens anotadas ausentes do top lexical e as que o outro ranking alcança."""
    blocked = set(lexical_top)
    outside = [chunk_id for chunk_id in support if chunk_id not in blocked]
    reached = [chunk_id for chunk_id in outside if chunk_id in set(other_top)]
    return outside, reached


def _rss_kb() -> int:
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def _preview(quote: str) -> str:
    return " ".join(quote.split())[:180]


def _support(item: dict[str, Any]) -> list[str]:
    return [passage["chunk_id"] for passage in item["passages"] if passage["label"] in SUPPORT]


def _as_rows(chunks: list[Any]) -> list[dict[str, str]]:
    return [
        {"chunk_id": chunk.chunk_id, "document_id": chunk.chunk_id.split("_", 1)[0]}
        for chunk in chunks
    ]


def _pack(ranked: list[Any], kept: dict[int, list[str]]) -> dict[str, Any]:
    return {"ranked": _as_rows(ranked), "kept": {k: kept.get(k, []) for k in CUTOFFS}}


def _latency(values: list[float]) -> dict[str, float]:
    return {"mean": sum(values) / len(values), "median": statistics.median(values), "max": max(values)}


def _ranking(result: dict[str, Any]) -> dict[str, Any]:
    return {k: {name: result["metrics"][k][name] for name in RANKING} for k in result["metrics"]}


def _answers(questions: list[dict[str, Any]], retrieved: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    missed = [
        item["query_id"]
        for item in questions
        if not item["expected_abstention"] and not retrieved[item["query_id"]]["kept"][5]
    ]
    point = result["metrics"]["5"]
    return {
        "correct_abstention_rate": point["correct_abstention_rate"],
        "false_positives": point["false_positives"],
        "false_abstentions": missed,
        "answer_hit_rate_at_5": point["answer_hit_rate_at_k"],
    }


def _same_ranking(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _ranking(left) == _ranking(right) and left["metrics"]["5"]["false_positives"] == right["metrics"]["5"]["false_positives"]


def _load_encoder(model_dir: Path):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer

    started = time.perf_counter()
    encoder = SentenceTransformer(
        str(model_dir), local_files_only=True, trust_remote_code=False, device="cpu"
    )
    encoder.eval()
    return encoder, (time.perf_counter() - started) * 1000


def _token_lengths(tokenizer, texts: list[str]) -> list[int]:
    encoded = tokenizer(texts, truncation=False, add_special_tokens=True, padding=False)
    return [len(tokens) for tokens in encoded["input_ids"]]


def _evaluate(db_path: Path, items: list[dict[str, Any]], records, chunks, vectors, encoder) -> dict[str, Any]:
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    retriever = Retriever(backend="bm25")
    retrieved = {name: {} for name in ("bm25", "e5", "hybrid_rrf", "hybrid_rrf_gated")}
    timings = {name: [] for name in retrieved}
    cases = {}
    for item in items:
        question = item["question"]
        started = time.perf_counter()
        pool = retriever.search(records, question, top_k=RETRIEVAL_POOL)
        chosen = select_literature_passages(question, pool, 5, quantity=True)
        kept = {
            k: [chunk.chunk_id for chunk in literature_evidence(question, chosen[:k], quantity=True)]
            for k in CUTOFFS
        }
        timings["bm25"].append((time.perf_counter() - started) * 1000)
        retrieved["bm25"][item["query_id"]] = _pack(chosen, kept)
        started = time.perf_counter()
        query_vector = encoder.encode(
            [f"query: {question}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        semantic = sorted(
            zip((vectors @ query_vector).tolist(), chunks, strict=True),
            key=lambda pair: (-pair[0], pair[1].chunk_id),
        )
        timings["e5"].append((time.perf_counter() - started) * 1000)
        lexical_full = sorted(
            (
                (score, chunk)
                for score, chunk in zip(Retriever._bm25(chunks, question), chunks, strict=True)
                if score > 0
            ),
            key=lambda pair: (-pair[0], pair[1].chunk_id),
        )
        fused_ids = reciprocal_rank_fusion([
            [chunk.chunk_id for _, chunk in lexical_full],
            [chunk.chunk_id for _, chunk in semantic],
        ])
        fused = [by_id[chunk_id] for chunk_id in fused_ids]
        timings["hybrid_rrf"].append((time.perf_counter() - started) * 1000)
        gated = select_literature_passages(question, fused[:RETRIEVAL_POOL], 5, quantity=True)
        gated_kept = {
            k: [chunk.chunk_id for chunk in literature_evidence(question, gated[:k], quantity=True)]
            for k in CUTOFFS
        }
        timings["hybrid_rrf_gated"].append((time.perf_counter() - started) * 1000)
        semantic_chunks = [chunk for _, chunk in semantic]
        retrieved["e5"][item["query_id"]] = _pack(semantic_chunks, {})
        retrieved["hybrid_rrf"][item["query_id"]] = _pack(fused, {})
        retrieved["hybrid_rrf_gated"][item["query_id"]] = _pack(gated, gated_kept)
        support = _support(item)
        lexical_ids = [chunk.chunk_id for chunk in pool]
        e5_top = [chunk.chunk_id for chunk in semantic_chunks[:5]]
        hybrid_top = fused_ids[:5]
        outside, entered = recovered_outside(support, lexical_ids, hybrid_top)
        _, entered_e5 = recovered_outside(support, lexical_ids, e5_top)
        gated_ids = [chunk.chunk_id for chunk in gated]
        cases[item["query_id"]] = {
            "bm25_top_id": chosen[0].chunk_id if chosen else "",
            "bm25_top": _preview(chosen[0].quote) if chosen else "",
            "e5_top_id": semantic_chunks[0].chunk_id,
            "e5_top": _preview(semantic_chunks[0].quote),
            "hybrid_top_id": fused_ids[0],
            "hybrid_top": _preview(fused[0].quote),
            "gated_ids": gated_ids,
            "kept_ids": gated_kept[5],
            "support_at_5": {
                "bm25": [chunk_id for chunk_id in lexical_ids[:5] if chunk_id in support],
                "e5": [chunk_id for chunk_id in e5_top if chunk_id in support],
                "hybrid": [chunk_id for chunk_id in hybrid_top if chunk_id in support],
                "gated": [chunk_id for chunk_id in gated_kept[5] if chunk_id in support],
            },
            "outside_lexical_top20": outside,
            "outside_reached_by_hybrid_top5": entered,
            "outside_reached_by_e5_top5": entered_e5,
            "support_blocked_by_gate": [
                chunk_id for chunk_id in gated_ids if chunk_id in support and chunk_id not in gated_kept[5]
            ],
            "e5_support_blocked": [
                chunk_id for chunk_id in e5_top if chunk_id in support and chunk_id not in gated_kept[5]
            ],
        }
    scored = {name: score_run(items, retrieved[name]) for name in retrieved}
    official = run_benchmark(db_path, items, diversify=True, quantity=True)
    if not _same_ranking(scored["bm25"], official):
        raise RuntimeError("O BM25 deste ensaio divergiu do benchmark oficial")
    return {
        "bm25": {
            "ranking": _ranking(scored["bm25"]),
            "answers": _answers(items, retrieved["bm25"], scored["bm25"]),
            "latency_ms": _latency(timings["bm25"]),
        },
        "e5": {"ranking": _ranking(scored["e5"]), "latency_ms": _latency(timings["e5"])},
        "hybrid_rrf": {
            "ranking": _ranking(scored["hybrid_rrf"]),
            "latency_ms": _latency(timings["hybrid_rrf"]),
        },
        "hybrid_rrf_gated": {
            "ranking": _ranking(scored["hybrid_rrf_gated"]),
            "answers": _answers(items, retrieved["hybrid_rrf_gated"], scored["hybrid_rrf_gated"]),
            "latency_ms": _latency(timings["hybrid_rrf_gated"]),
        },
        "cases": cases,
    }


def run_experiment(db_path: Path, model_dir: Path) -> dict[str, Any]:
    before = db_path.stat()
    if hashlib.sha256(VALIDATION.read_bytes()).hexdigest() != VALIDATION_SHA256:
        raise RuntimeError("O conjunto direcionado mudou depois do congelamento")
    hashes = _stored_hashes(db_path)
    if hashes != EXPECTED_HASHES:
        raise RuntimeError("A base experimental não é a coleção validada de PT-001 e PT-002")
    documents = LiteratureStore(db_path).list_documents()
    records = _body_records(documents)
    chunks = [chunk for record in records for chunk in chunk_record(record, 600)]
    if len(chunks) != 136:
        raise RuntimeError(f"Esperados 136 trechos de corpo, encontrados {len(chunks)}")
    questions = load_questions(GOLD)
    directed = load_questions(VALIDATION)
    memory_before = _rss_kb()
    encoder, load_ms = _load_encoder(model_dir)
    dimension = encoder.get_embedding_dimension()
    if dimension != 384 or int(encoder.max_seq_length) != TOKEN_BUDGET:
        raise RuntimeError("O modelo carregado não é o E5 small de 384 dimensões e 512 tokens")
    passage_inputs = [f"passage: {chunk.quote}" for chunk in chunks]
    query_items = questions + directed
    query_inputs = [f"query: {item['question']}" for item in query_items]
    lengths = _token_lengths(encoder.tokenizer, passage_inputs + query_inputs)
    named = list(zip((chunk.chunk_id for chunk in chunks), lengths[: len(chunks)], strict=True))
    query_lengths = list(zip((item["query_id"] for item in query_items), lengths[len(chunks) :], strict=True))
    overflow = [chunk_id for chunk_id, length in named + query_lengths if length > TOKEN_BUDGET]
    if overflow:
        raise RuntimeError("Texto acima de 512 tokens: " + ", ".join(overflow))
    assert_token_budget(named)
    import numpy as np

    started = time.perf_counter()
    vectors = encoder.encode(
        passage_inputs,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    encode_ms = (time.perf_counter() - started) * 1000
    norms = np.linalg.norm(vectors, axis=1)
    if vectors.shape != (136, 384) or float(np.max(np.abs(norms - 1))) > 1e-3:
        raise RuntimeError("Os embeddings não vieram normalizados em 384 dimensões")
    probe = {"normalize_embeddings": True, "convert_to_numpy": True, "show_progress_bar": False}
    if not np.array_equal(
        encoder.encode(["query: sigilo clínico"], **probe),
        encoder.encode(["query: sigilo clínico"], **probe),
    ):
        raise RuntimeError("A inferência em CPU não repetiu o mesmo vetor")
    cache = {
        embedding_cache_key(
            chunk.chunk_id.split("_", 1)[0],
            hashes[chunk.chunk_id.split("_", 1)[0]],
            chunk.chunk_id,
            MODEL_REVISION,
        ): vector
        for chunk, vector in zip(chunks, vectors, strict=True)
    }
    if len(cache) != 136:
        raise RuntimeError("O cache em memória não cobre os 136 trechos")
    memory_after = _rss_kb()
    report = {
        "model_id": "intfloat/multilingual-e5-small",
        "model_revision": MODEL_REVISION,
        "embedding_dim": 384,
        "token_budget": TOKEN_BUDGET,
        "max_passage_tokens": max(length for _, length in named),
        "max_query_tokens": max(length for _, length in query_lengths),
        "body_chunks": 136,
        "normalized": True,
        "deterministic_cpu": True,
        "offline_queries": True,
        "load_ms": load_ms,
        "encode_ms": encode_ms,
        "rss_kb_before": memory_before,
        "rss_kb_after_index": memory_after,
        "benchmark": _evaluate(db_path, questions, records, chunks, vectors, encoder),
        "directed": _evaluate(db_path, directed, records, chunks, vectors, encoder),
    }
    after = db_path.stat()
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise RuntimeError("A base experimental foi modificada durante o ensaio")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=MODEL_DIR)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run_experiment(args.db, args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
