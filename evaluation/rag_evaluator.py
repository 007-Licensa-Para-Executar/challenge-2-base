"""Avaliador reproduzível da qualidade de recuperação e abstenção do RAG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agents.copilot.config import CopilotSettings
from agents.copilot.retriever import HybridRetriever


def evaluate_rag(
    benchmark_path: Path,
    corpus_path: Path,
    top_k: int = 4,
    abstention_threshold: float = 0.12,
) -> dict[str, Any]:
    retriever = HybridRetriever(corpus_path=corpus_path, abstention_threshold=abstention_threshold)

    total_queries = 0
    in_scope_queries = 0
    out_of_scope_queries = 0

    hits_recall = 0
    abstention_hits = 0
    details = []

    with benchmark_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            total_queries += 1

            query = item["query"]
            expected_chunks = set(item.get("expected_chunk_ids", []))
            expected_abstention = item.get("expected_abstention", False)

            evidences, status = retriever.retrieve(query=query, top_k=top_k)
            retrieved_ids = [ev.chunk_id for ev in evidences]

            if expected_abstention:
                out_of_scope_queries += 1
                is_correct = (status == "evidencia_insuficiente") or len(evidences) == 0
                if is_correct:
                    abstention_hits += 1
            else:
                in_scope_queries += 1
                # Recall: o chunk esperado está entre os recuperados?
                hit = any(cid in retrieved_ids for cid in expected_chunks)
                if hit:
                    hits_recall += 1
                is_correct = hit

            details.append({
                "query_id": item.get("query_id"),
                "query": query,
                "expected_abstention": expected_abstention,
                "status": status,
                "retrieved_chunk_ids": retrieved_ids,
                "is_correct": is_correct,
            })

    recall_at_k = (hits_recall / in_scope_queries) if in_scope_queries > 0 else 1.0
    abstention_rate = (abstention_hits / out_of_scope_queries) if out_of_scope_queries > 0 else 1.0
    overall_accuracy = ((hits_recall + abstention_hits) / total_queries) if total_queries > 0 else 1.0

    return {
        "total_queries": total_queries,
        "in_scope_queries": in_scope_queries,
        "out_of_scope_queries": out_of_scope_queries,
        "recall_at_k": round(recall_at_k, 4),
        "abstention_rate": round(abstention_rate, 4),
        "overall_accuracy": round(overall_accuracy, 4),
        "top_k": top_k,
        "abstention_threshold": abstention_threshold,
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avaliação automatizada do RAG para o Agente 2.")
    parser.add_argument(
        "--benchmarks",
        type=Path,
        default=Path("evaluation/rag_benchmarks.jsonl"),
        help="Caminho do arquivo com casos de teste.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("knowledge_base/corpus.jsonl"),
        help="Caminho da base de conhecimento.",
    )
    parser.add_argument("--top-k", type=int, default=4, help="Número de trechos a recuperar.")
    parser.add_argument("--output", type=Path, help="Caminho para salvar relatório JSON.")

    args = parser.parse_args(argv)
    settings = CopilotSettings.from_env()

    results = evaluate_rag(
        benchmark_path=args.benchmarks,
        corpus_path=args.corpus or settings.corpus_path,
        top_k=args.top_k,
        abstention_threshold=settings.abstention_threshold,
    )

    report_json = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report_json, encoding="utf-8")
        print(f"Relatório de avaliação salvo em {args.output}")
    else:
        print(report_json)

    # Verifica se os critérios mínimos de qualidade foram atendidos
    if results["recall_at_k"] < 0.80 or results["abstention_rate"] < 0.80:
        print("ALERTA: Desempenho do RAG abaixo dos critérios mínimos de aceite!", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
