"""Métricas do benchmark científico. Não abre a base experimental."""

from evaluation.literature_bm25 import load_questions, score_run

POSITIVE = {
    "query_id": "q-pos",
    "category": ["exemplo"],
    "question": "Pergunta fictícia com gabarito.",
    "expected_abstention": False,
    "relevant_documents": ["PT-001"],
    "passages": [
        {"chunk_id": "PT-001_texto:0:10", "document_id": "PT-001", "label": "direta", "group": "resumo", "why": "Trecho direto."},
        {"chunk_id": "PT-001_texto:10:20", "document_id": "PT-001", "label": "parcial", "why": "Trecho parcial."},
        {"chunk_id": "PT-001_texto:20:30", "document_id": "PT-001", "label": "redundante", "group": "resumo", "why": "Tradução."},
    ],
}
NEGATIVE = {
    "query_id": "q-neg",
    "category": ["sem_evidencia"],
    "question": "Pergunta fictícia sem resposta.",
    "expected_abstention": True,
    "relevant_documents": [],
    "passages": [],
}


def _hit(chunk_id):
    return {"chunk_id": chunk_id, "document_id": chunk_id.split("_", 1)[0]}


def test_gold_file_separates_abstention_from_support():
    questions = load_questions()
    assert 15 <= len(questions) <= 20
    assert any(item["expected_abstention"] for item in questions)
    assert any(item["relevant_documents"] == ["PT-001"] for item in questions)
    assert any(item["relevant_documents"] == ["PT-002"] for item in questions)
    assert any(set(item["relevant_documents"]) == {"PT-001", "PT-002"} for item in questions)


def test_strict_precision_and_annotated_recall_ignore_the_duplicate():
    retrieved = {
        "q-pos": {
            "ranked": [_hit("PT-001_texto:20:30"), _hit("PT-001_texto:0:10"), _hit("PT-009_texto:0:10")],
            "kept": {1: ["PT-001_texto:20:30"], 3: ["PT-001_texto:20:30", "PT-001_texto:0:10"], 5: []},
        },
        "q-neg": {"ranked": [_hit("PT-001_texto:0:10")], "kept": {1: ["PT-001_texto:0:10"], 3: [], 5: []}},
    }
    result = score_run([POSITIVE, NEGATIVE], retrieved)
    top = result["details"][0]["cutoffs"]["3"]
    assert top["precision_at_k"] == 1 / 3
    assert top["annotated_recall_at_k"] == 1 / 2
    assert top["hit_at_k"] is True
    assert top["mrr_at_k"] == 1
    assert top["redundancy_at_k"] == 1 / 3
    assert top["unannotated_at_k"] == 1 / 3
    assert result["metrics"]["3"]["precision_at_k"] == 1 / 3
    assert result["metrics"]["3"]["false_positives"] == 0
    assert result["metrics"]["1"]["false_positives"] == 1
    assert "corpus" in result["gold_scope"]
