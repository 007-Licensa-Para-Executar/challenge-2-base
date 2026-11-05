"""Testes unitários para o Recuperador Híbrido (BM25 + Cosseno) do RAG."""

from pathlib import Path

from agents.copilot.retriever import HybridRetriever, _normalize


def test_normalize_text():
    tokens = _normalize("Olá, mundo! Como vai a depressão e o bem-estar?")
    assert "depressao" in tokens
    assert "bem" in tokens
    assert "estar" in tokens
    # Stopwords devem ser filtradas
    assert "como" not in tokens
    assert "e" not in tokens


def test_retriever_load_corpus():
    corpus_path = Path("knowledge_base/corpus.jsonl")
    assert corpus_path.exists(), "O corpus.jsonl deve existir."

    retriever = HybridRetriever(corpus_path=corpus_path, abstention_threshold=0.12)
    assert len(retriever.chunks) >= 10
    assert retriever._avg_doc_len > 0


def test_retriever_query_in_scope():
    retriever = HybridRetriever(corpus_path="knowledge_base/corpus.jsonl", abstention_threshold=0.10)
    evidences, status = retriever.retrieve("sycophancy bajulação algorítmica validação negativa", top_k=2)

    assert len(evidences) > 0
    assert status in ("evidencia_suficiente", "evidencia_parcial")
    chunk_ids = [ev.chunk_id for ev in evidences]
    assert "mit_risk_simulation_01_sycophancy" in chunk_ids


def test_retriever_abstention_out_of_scope():
    retriever = HybridRetriever(corpus_path="knowledge_base/corpus.jsonl", abstention_threshold=0.15)
    evidences, status = retriever.retrieve("conserto de cambio automatico e suspensao automotiva", top_k=3)

    assert status == "evidencia_insuficiente"
    assert len(evidences) == 0


def test_retriever_collection_filter():
    retriever = HybridRetriever(corpus_path="knowledge_base/corpus.jsonl", abstention_threshold=0.05)
    evidences, _ = retriever.retrieve(
        query="psicologia ética regulamentação",
        top_k=5,
        collection_filter="etica_governanca_cfp",
    )
    for ev in evidences:
        assert "CFP" in ev.institution or "Brasil" in ev.institution
