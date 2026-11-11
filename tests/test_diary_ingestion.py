"""Neural adapter errors must not invent metadata or erase originals."""

import hashlib
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.ingestion import classify_record
from agents.copilot.storage import DiaryStore


def diary():
    return DiaryRecord(
        record_id="d1",
        patient_id="alice",
        recorded_at=datetime(2026, 11, 5, tzinfo=UTC),
        original_text="Fiquei preocupada com a minha avó.",
    )


class StubPredictor:
    def predict_text(self, text):
        assert text == diary().original_text
        return SimpleNamespace(
            primary_theme="familia",
            candidate_theme="familia",
            confidence=0.7,
            abstention_reason=None,
        )


def test_not_requested_is_explicit_and_preserved_when_saved(tmp_path):
    item = diary()
    assert item.classification.status == "not_requested"
    store = DiaryStore(tmp_path / "dados.sqlite3")
    store.save(item)
    assert store.list_records(Query(patient_id="alice", question="avó"))[0] == item


def test_maps_predictor_output_without_changing_original():
    item = diary()
    classified = classify_record(item, predictor=StubPredictor())
    assert classified.original_text == item.original_text
    assert classified.record_id == item.record_id
    assert classified.recorded_at == item.recorded_at
    assert item.classification.status == "not_requested"
    assert classified.classification.status == "ok"
    assert classified.classification.primary_theme == "familia"
    assert classified.classification.candidate_score == 0.7
    assert classified.classification.model_version is None


def test_abstention_keeps_candidate_and_score_distinct():
    class Abstaining:
        def predict_text(self, text):
            return SimpleNamespace(
                primary_theme="outros_indeterminado",
                candidate_theme="familia",
                confidence=0.2,
                abstention_reason="below_threshold",
            )

    classification = classify_record(diary(), predictor=Abstaining()).classification
    assert classification.status == "ok"
    assert classification.primary_theme == "outros_indeterminado"
    assert classification.candidate_theme == "familia"
    assert classification.abstention_reason == "below_threshold"


def test_versions_both_artifacts_by_content(tmp_path):
    weights, vector = tmp_path / "pesos.pt", tmp_path / "vetor.joblib"
    weights.write_bytes(b"weights")
    vector.write_bytes(b"vectorizer")
    expected = hashlib.sha256(
        hashlib.sha256(b"weights").digest() + hashlib.sha256(b"vectorizer").digest()
    ).hexdigest()
    result = classify_record(
        diary(), predictor=StubPredictor(), model_path=weights, vectorizer_path=vector
    )
    assert result.classification.model_version == "sha256:" + expected


def test_missing_weights_is_recorded_as_error_and_original_remains_searchable(tmp_path):
    item = classify_record(
        diary(), model_path=tmp_path / "missing.pt", vectorizer_path=tmp_path / "missing.joblib"
    )
    assert item.classification.status == "error"
    assert item.classification.primary_theme is None
    assert item.classification.error_code == "classification_model_unavailable"
    store = DiaryStore(tmp_path / "dados.sqlite3")
    store.save(item)
    assert (
        store.list_records(Query(patient_id="alice", question="avó"))[0].original_text
        == diary().original_text
    )


@pytest.mark.parametrize(
    "exception,code",
    [
        (RuntimeError("texto ou caminho privado"), "classification_failed"),
        (ValueError("saída inválida"), "classification_invalid_output"),
    ],
)
def test_failures_are_sanitized(exception, code):
    class Broken:
        def predict_text(self, text):
            raise exception

    result = classify_record(diary(), predictor=Broken())
    assert result.classification.error_code == code
    assert result.classification.primary_theme is None
    assert "privado" not in result.classification.model_dump_json()
    assert result.original_text == diary().original_text


def test_invalid_category_is_not_accepted():
    class Invalid:
        def predict_text(self, text):
            return SimpleNamespace(
                primary_theme="diagnostico",
                candidate_theme="diagnostico",
                confidence=0.9,
                abstention_reason=None,
            )

    assert classify_record(diary(), predictor=Invalid()).classification.status == "error"


def test_real_predictor_loads_temporary_artifacts_and_records_version(tmp_path):
    import joblib
    import torch
    from sklearn.feature_extraction.text import TfidfVectorizer

    from models.torch_mlp import ClinicalThemeMLP

    vectorizer = TfidfVectorizer().fit(["avó família cuidado", "trabalho empresa"])
    model = ClinicalThemeMLP(input_dim=len(vectorizer.vocabulary_))
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
        model.fc3.bias[0] = 10.0  # Controlled output: adapter integration, not a quality benchmark.
    weights = tmp_path / "pesos locais.pt"
    vector = tmp_path / "vocabulário.joblib"
    torch.save(model.state_dict(), weights)
    joblib.dump(vectorizer, vector)
    result = classify_record(diary(), model_path=weights, vectorizer_path=vector)
    assert result.classification.status == "ok"
    assert result.classification.primary_theme == "familia"
    assert result.classification.model_version.startswith("sha256:")
    assert result.original_text == diary().original_text


def test_corrupt_checkpoint_becomes_operational_error(tmp_path):
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer

    weights = tmp_path / "corrupt.pt"
    vector = tmp_path / "vector.joblib"
    weights.write_bytes(b"")
    joblib.dump(TfidfVectorizer().fit(["família cuidado"]), vector)
    result = classify_record(diary(), model_path=weights, vectorizer_path=vector)
    assert result.classification.status == "error"
    assert result.classification.error_code == "classification_failed"
    assert result.classification.primary_theme is None
    assert result.original_text == diary().original_text
