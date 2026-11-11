"""Contract, scope and failure tests without downloading any model."""

import math

import numpy as np
import pytest

from agents.copilot.contracts import DiaryRecord
from agents.copilot.retriever import RetrievalError, Retriever, chunk_record


def record(text="Cuidei dos avós e acompanhei uma consulta.", **kwargs):
    return DiaryRecord(
        record_id="r1",
        patient_id="p1",
        recorded_at="2026-11-01T12:00:00Z",
        original_text=text,
        **kwargs,
    )


def test_bm25_returns_literal_ranked_evidence():
    first = record()
    second = first.model_copy(update={"record_id": "r2", "original_text": "Estudei matemática."})
    result = Retriever().search([second, first], "consulta avós")
    assert [e.record_id for e in result] == ["r1"]
    evidence = result[0]
    assert first.original_text[evidence.start_char : evidence.end_char] == evidence.quote
    assert evidence.patient_id == first.patient_id
    assert evidence.score > 0


def test_hyphenated_compound_is_not_a_fragment_of_the_question():
    diary = record("Comprei um cartão-postal para guardar como lembrança.")
    assert Retriever().search([diary], "Qual é a senha do cartão bancário?") == []
    found = Retriever().search([diary], "O que aparece sobre o cartão-postal?")
    assert [item.record_id for item in found] == ["r1"]
    assert diary.original_text[found[0].start_char : found[0].end_char] == found[0].quote
    assert found[0].chunk_id == f"r1:{found[0].start_char}:{found[0].end_char}"


def test_no_overlap_empty_records_and_blank_query_return_no_evidence():
    retriever = Retriever()
    assert retriever.search([record()], "vulcão satélite") == []
    assert retriever.search([], "avós") == []
    assert retriever.search([record()], "  ") == []


def test_bm25_is_not_normalized_by_best_result_and_threshold_can_abstain():
    retriever = Retriever(min_score=2)
    # With one short document the score is below 2, not normalized to 1.
    assert retriever.search([record()], "avós") == []
    score = Retriever().search([record()], "avós")[0].score
    assert math.isclose(score, math.log(1 + 0.5 / 1.5))


def test_literal_chunks_preserve_unicode_crlf_and_every_character():
    text = "Avós e família 🙂.\r\n" * 30
    diary = record(text)
    chunks = chunk_record(diary, 45)
    assert "".join(c.quote for c in chunks) == text
    assert all(len(c.quote) <= 45 for c in chunks)
    for c in chunks:
        assert text[c.start_char : c.end_char] == c.quote
        assert c.chunk_id == f"r1:{c.start_char}:{c.end_char}"


def test_mixed_patient_and_duplicate_record_input_rejected():
    diary = record()
    with pytest.raises(RetrievalError, match="mixed_patient_scope"):
        Retriever().search([diary, diary.model_copy(update={"patient_id": "p2"})], "avós")
    with pytest.raises(RetrievalError, match="duplicate_record_id"):
        Retriever().search([diary, diary], "avós")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"backend": "arbitrary"},
        {"min_score": -1},
        {"min_score": float("nan")},
        {"chunk_chars": 0},
        {"backend": "e5", "min_score": 1.1},
    ],
)
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        Retriever(**kwargs)


def test_e5_requires_existing_explicit_local_model(tmp_path):
    with pytest.raises(RetrievalError, match="embedding_model_missing"):
        Retriever("e5", tmp_path / "missing").search([record()], "avós")


class Encoder:
    max_seq_length = 512

    def __init__(self):
        self.inputs = None

    def tokenizer(self, inputs, **kwargs):
        assert kwargs == {"truncation": False, "add_special_tokens": True, "padding": False}
        return {"input_ids": [[1] * (len(text) + 2) for text in inputs]}

    def encode(self, inputs, **kwargs):
        self.inputs = inputs
        assert kwargs["normalize_embeddings"] is True
        assert kwargs["convert_to_numpy"] is True
        return np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])


def test_e5_prefix_normalization_cosine_and_threshold_without_model_download():
    encoder = Encoder()
    retriever = Retriever("e5", min_score=0.6)
    retriever._encoder = encoder
    first = record()
    second = first.model_copy(update={"record_id": "r2", "original_text": "Matemática."})
    results = retriever.search([first, second], "avós")
    assert [e.record_id for e in results] == ["r1"]
    assert encoder.inputs[0] == "query: avós"
    assert encoder.inputs[1] == "passage: " + first.original_text


def test_e5_rejects_token_overflow_before_encoding():
    encoder = Encoder()
    retriever = Retriever("e5")
    retriever._encoder = encoder
    with pytest.raises(RetrievalError, match="embedding_input_too_long"):
        retriever.search([record()], "x" * 600)
    assert encoder.inputs is None


def test_e5_failure_is_sanitized():
    class Broken(Encoder):
        def encode(self, *args, **kwargs):
            raise RuntimeError("Private raw model error")

    retriever = Retriever("e5")
    retriever._encoder = Broken()
    with pytest.raises(RetrievalError, match="^embedding_failed$"):
        retriever.search([record()], "avós")
