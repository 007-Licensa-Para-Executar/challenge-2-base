"""A validação direcionada fica congelada e não abre a base experimental."""

import hashlib

from evaluation.literature_bm25 import load_questions
from evaluation.literature_hybrid_protocol import (
    STRATEGIES,
    VALIDATION,
    VALIDATION_SHA256,
    assert_token_budget,
    embedding_cache_key,
    reciprocal_rank_fusion,
)
from evaluation.literature_hybrid_run import recovered_outside

BENCHMARK = VALIDATION.parent / "questions.jsonl"


def test_directed_validation_is_frozen_and_separate():
    digest = hashlib.sha256(VALIDATION.read_bytes()).hexdigest()
    assert digest == VALIDATION_SHA256
    questions = load_questions(VALIDATION)
    benchmark = {item["query_id"] for item in load_questions(BENCHMARK)}
    assert {item["query_id"] for item in questions}.isdisjoint(benchmark)
    categories = {name for item in questions for name in item["category"]}
    assert {"validacao_direcionada", "sinonimos", "sem_evidencia", "negacao", "ingles", "controle_lexical"} <= categories
    assert sum(item["expected_abstention"] for item in questions) == 2
    negation = next(item for item in questions if "negacao" in item["category"])
    assert negation["expected_abstention"] is False
    assert negation["expected_answer"].startswith("Não.")
    assert all(item["frozen_on"] == "2026-11-24" for item in questions)
    assert STRATEGIES == ("bm25", "e5", "hybrid_rrf", "hybrid_rrf_gated")


def test_hybrid_can_count_a_passage_the_lexical_top_missed():
    outside, reached = recovered_outside(["a", "b", "c"], ["a", "z"], ["b", "y"])
    assert outside == ["b", "c"]
    assert reached == ["b"]


def test_fusion_keeps_equal_weights_and_cache_identity():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    assert fused[0] == "b"
    assert fused.index("a") < fused.index("c")
    assert_token_budget([("PT-001_texto:0:10", 512)])
    try:
        assert_token_budget([("PT-001_texto:0:10", 513)])
    except ValueError as error:
        assert "PT-001_texto:0:10" in str(error)
    else:
        raise AssertionError("trecho longo foi aceito")
    base = embedding_cache_key("PT-001", "abc", "PT-001_texto:0:10", "rev")
    assert base != embedding_cache_key("PT-001", "def", "PT-001_texto:0:10", "rev")
    assert base != embedding_cache_key("PT-001", "abc", "PT-001_texto:0:10", "outra")
