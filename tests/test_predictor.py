"""Contract tests with controlled weights, independent of local trained artefacts."""

import joblib
import numpy as np
import pytest
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

from models.embedder import ClinicalTextEmbedder
from models.predictor import ClinicalThemePredictor, DiaryTopicBreakdown, TopicDistribution
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP


@pytest.mark.parametrize("flags", [[], ["--destrinchar"]])
def test_cli_distinguishes_abstention_from_candidate_score(predictor, monkeypatch, capsys, flags):
    import models.predictor as module

    monkeypatch.setattr(module, "ClinicalThemePredictor", lambda: predictor)
    monkeypatch.setattr("sys.argv", ["predictor", "--text", "palavras desconhecidas aqui.", *flags])
    module.main()
    output = capsys.readouterr().out
    assert "outros" in output
    assert "below_threshold" in output
    assert "Candidato" in output
    assert "não calibrado" in output


@pytest.fixture
def components():
    """A real MLP wired to controlled features; these are not quality benchmarks."""
    vectorizer = TfidfVectorizer().fit(THEME_CLASSES)
    model = ClinicalThemeMLP(input_dim=len(vectorizer.vocabulary_), num_classes=len(THEME_CLASSES))
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
        model.temperature.fill_(1.0)
        model.bn1.weight.fill_(1.0)
        model.bn1.running_mean.zero_()
        model.bn1.running_var.fill_(1.0)
        for idx, theme in enumerate(THEME_CLASSES):
            model.fc1.weight[idx, vectorizer.vocabulary_[theme]] = 1.0
            model.fc2.weight[idx, idx] = 1.0
            model.fc3.weight[idx, idx] = 20.0
    return model, vectorizer


@pytest.fixture
def predictor(components):
    model, vectorizer = components
    return ClinicalThemePredictor(model=model, vectorizer=vectorizer)


def test_initialization_from_injected_components(predictor):
    assert isinstance(predictor.model, ClinicalThemeMLP)
    assert not predictor.model.training


def test_load_artefacts_created_in_temporary_directory(components, tmp_path):
    model, vectorizer = components
    model_path = tmp_path / "pesos.pt"
    vectorizer_path = tmp_path / "vetorizador.joblib"
    torch.save(model.state_dict(), model_path)
    joblib.dump(vectorizer, vectorizer_path)
    loaded = ClinicalThemePredictor(model_path=model_path, vectorizer_path=vectorizer_path)
    assert loaded.predict_text("desempenho").primary_theme == "desempenho"


def test_load_embedder_checkpoint_without_phantom_embedding_bag(tmp_path):
    """Garante carregamento sem EmbeddingBag fantasma e com normalização L2 na inferência."""
    embedder = ClinicalTextEmbedder(embedding_dim=16, max_features=50, init_strategy="gaussian")
    embedder.fit(["desempenho trabalho", "vinculos familia", "fisico sono"])
    model = ClinicalThemeMLP(input_dim=16, num_classes=len(THEME_CLASSES), norm_type="layer_norm")
    with torch.no_grad():
        model.temperature.copy_(torch.tensor([1.35]))

    model_path = tmp_path / "mlp.pt"
    emb_path = tmp_path / "embedder.joblib"
    torch.save(model.state_dict(), model_path)
    joblib.dump(embedder, emb_path)

    loaded = ClinicalThemePredictor(model_path=model_path, vectorizer_path=emb_path)
    assert loaded.model.embedding_bag is None
    assert loaded.score_semantics == "temperature_scaled_softmax"
    encoded = loaded._encode_text("desempenho trabalho")
    np.testing.assert_allclose(np.linalg.norm(encoded, axis=1), np.ones(1), atol=1e-5)


def test_missing_artefacts_are_explicit(tmp_path):
    with pytest.raises(FileNotFoundError, match="Vetorizador/Embedder"):
        ClinicalThemePredictor(vectorizer_path=tmp_path / "missing.joblib")


def test_missing_weights_are_explicit(components, tmp_path):
    _, vectorizer = components
    with pytest.raises(FileNotFoundError, match="Pesos"):
        ClinicalThemePredictor(vectorizer=vectorizer, model_path=tmp_path / "missing.pt")


def test_scores_do_not_claim_multiple_topics(predictor):
    result = predictor.predict_text("desempenho")
    assert isinstance(result, TopicDistribution)
    assert result.primary_theme == "desempenho"
    assert result.candidate_theme == "desempenho"
    assert not result.is_fallback
    assert result.abstention_reason is None
    assert result.score_semantics == "uncalibrated_softmax"
    assert sum(result.probabilities.values()) == pytest.approx(1, abs=0.001)
    assert sum(result.percentages.values()) == pytest.approx(100, abs=0.1)
    assert len(result.top_topics) == 1
    assert result.ranking[0]["tema"] == "desempenho"
    assert result.to_dict()["score_semantics"] == "uncalibrated_softmax"


def test_low_score_abstention_keeps_candidate_score(predictor):
    result = predictor.predict_text("vocabulário desconhecido")
    assert result.is_fallback
    assert result.primary_theme == "outros"
    assert result.candidate_theme in THEME_CLASSES
    assert result.confidence == pytest.approx(1 / len(THEME_CLASSES), abs=0.0001)
    assert result.abstention_reason == "below_threshold"
    assert result.top_topics == []


def test_empty_input_does_not_fabricate_confidence(predictor, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Empty input must not invoke the model")

    monkeypatch.setattr(predictor.model, "predict_proba", forbidden)
    result = predictor.predict_text(" \r\n ")
    assert result.primary_theme == "outros"
    assert result.confidence == 0
    assert result.candidate_theme is None
    assert result.abstention_reason == "empty_input"
    assert sum(result.probabilities.values()) == 0
    assert result.ranking == []

    num_result = predictor.predict_text("12345 67890 !@#")
    assert num_result.primary_theme == "outros"
    assert num_result.confidence == 0
    assert num_result.candidate_theme is None
    assert num_result.abstention_reason == "non_textual_input"
    assert num_result.is_fallback


def test_segment_weights_are_measured_character_shares(predictor):
    text = "desempenho desempenho. vinculos vinculos vinculos. fisico fisico."
    result = predictor.destrinchar_diario(text, min_segment_chars=3)
    assert isinstance(result, DiaryTopicBreakdown)
    assert len(result.segments) == 3
    assert [s.theme for s in result.segments] == ["desempenho", "vinculos", "fisico"]
    count = sum(len(s.quote) for s in result.segments)
    assert result.analyzed_chars == count
    assert result.total_chars == len(text)
    assert result.omitted_chars == len(text) - count
    assert result.coverage_ratio == pytest.approx(count / len(text))
    assert result.weight_basis == "analyzed_characters"
    assert result.topic_weights["vinculos"] == pytest.approx(
        100 * len(result.segments[1].quote) / count, abs=0.01
    )
    assert sum(result.topic_weights.values()) == pytest.approx(100, abs=0.1)
    assert result.topic_weights["autopercepcao"] == 0
    for segment in result.segments:
        assert text[segment.start_char : segment.end_char] == segment.quote


def test_unicode_crlf_and_short_segment_coverage(predictor):
    text = "Oi!\r\n  vinculos 🧡 desempenho desempenho!\r\nSim."
    result = predictor.destrinchar_diario(text, min_segment_chars=15)
    assert len(result.segments) == 1
    segment = result.segments[0]
    assert text[segment.start_char : segment.end_char] == segment.quote
    assert segment.quote == "vinculos 🧡 desempenho desempenho!"
    assert result.omitted_chars == len(text) - len(segment.quote)
    assert 0 < result.coverage_ratio < 1


def test_no_segments_has_no_textual_distribution(predictor):
    result = predictor.destrinchar_diario("desempenho", min_segment_chars=15)
    assert result.global_theme == "desempenho"
    assert sum(result.theme_percentages.values()) == pytest.approx(100, abs=0.1)
    assert sum(result.topic_weights.values()) == 0
    assert result.detected_topics == []
    assert result.analyzed_chars == 0
    assert result.omitted_chars == len("desempenho")
    assert result.coverage_ratio == 0


def test_empty_breakdown_has_zero_coverage(predictor):
    result = predictor.destrinchar_diario("")
    assert result.global_confidence == 0
    assert result.total_chars == result.analyzed_chars == result.omitted_chars == 0
    assert result.coverage_ratio == 0
    assert result.detected_topics == []
    assert sum(result.topic_weights.values()) == 0


def test_batch_preserves_order_and_abstention(predictor):
    results = predictor.predict_batch(["desempenho", "vinculos", ""])
    assert [r.primary_theme for r in results] == ["desempenho", "vinculos", "outros"]


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_invalid_threshold_rejected(predictor, threshold):
    with pytest.raises(ValueError, match="threshold"):
        predictor.predict_text("desempenho", threshold=threshold)


def test_invalid_segment_configuration_rejected(predictor):
    with pytest.raises(ValueError, match="positivo"):
        predictor.destrinchar_diario("desempenho", min_segment_chars=0)
    with pytest.raises(ValueError, match="segment_threshold"):
        predictor.destrinchar_diario("desempenho", segment_threshold=2)
