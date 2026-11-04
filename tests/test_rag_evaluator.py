"""Testes automatizados para o script de avaliação do RAG."""

from pathlib import Path

from evaluation.rag_evaluator import evaluate_rag


def test_evaluate_rag_benchmarks():
    benchmark_path = Path("evaluation/rag_benchmarks.jsonl")
    corpus_path = Path("knowledge_base/corpus.jsonl")

    assert benchmark_path.exists()
    assert corpus_path.exists()

    metrics = evaluate_rag(
        benchmark_path=benchmark_path,
        corpus_path=corpus_path,
        top_k=4,
        abstention_threshold=0.10,
    )

    assert metrics["total_queries"] == 10
    assert metrics["in_scope_queries"] == 7
    assert metrics["out_of_scope_queries"] == 3

    # Critérios de qualidade exigidos
    assert metrics["recall_at_k"] >= 0.85, f"Recall@k abaixo do limiar: {metrics['recall_at_k']}"
    assert metrics["abstention_rate"] >= 0.80, f"Taxa de abstenção abaixo do limiar: {metrics['abstention_rate']}"
    assert metrics["overall_accuracy"] >= 0.85
