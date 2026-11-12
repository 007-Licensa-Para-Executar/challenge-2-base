"""Contract tests with controlled weights, independent of local trained artefacts."""

import joblib
import pytest
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

from models.predictor import ClinicalThemePredictor, DiaryTopicBreakdown, TopicDistribution
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP


@pytest.mark.parametrize("flags", [[], ["--destrinchar"]])
def test_cli_distinguishes_abstention_from_candidate_score(predictor, monkeypatch, capsys, flags):
    import models.predictor as module

    monkeypatch.setattr(module, "ClinicalThemePredictor", lambda: predictor)
    monkeypatch.setattr("sys.argv", ["predictor", "--text", "palavras desconhecidas aqui.", *flags])
    module.main()
    output = capsys.readouterr().out
    assert "outros_indeterminado" in output
    assert "below_threshold" in output
    assert "Candidato" in output
    assert "não calibrado" in output


@pytest.fixture
def components():
    """A real MLP wired to controlled features; these are not quality benchmarks."""
    vectorizer = TfidfVectorizer().fit(THEME_CLASSES)
    model = ClinicalThemeMLP(input_dim=len(vectorizer.vocabulary_))
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
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
    assert loaded.predict_text("trabalho").primary_theme == "trabalho"


def test_missing_artefacts_are_explicit(tmp_path):
    with pytest.raises(FileNotFoundError, match="TF-IDF"):
        ClinicalThemePredictor(vectorizer_path=tmp_path / "missing.joblib")


def test_missing_weights_are_explicit(components, tmp_path):
    _, vectorizer = components
    with pytest.raises(FileNotFoundError, match="Pesos"):
        ClinicalThemePredictor(vectorizer=vectorizer, model_path=tmp_path / "missing.pt")


def test_scores_do_not_claim_multiple_topics(predictor):
    result = predictor.predict_text("trabalho")
    assert isinstance(result, TopicDistribution)
    assert result.primary_theme == "trabalho"
    assert result.candidate_theme == "trabalho"
    assert not result.is_fallback
    assert result.abstention_reason is None
    assert result.score_semantics == "uncalibrated_softmax"
    assert sum(result.probabilities.values()) == pytest.approx(1, abs=0.001)
    assert sum(result.percentages.values()) == pytest.approx(100, abs=0.1)
    assert len(result.top_topics) == 1
    assert result.ranking[0]["tema"] == "trabalho"
    assert result.to_dict()["score_semantics"] == "uncalibrated_softmax"


def test_low_score_abstention_keeps_candidate_score(predictor):
    result = predictor.predict_text("vocabulário desconhecido")
    assert result.is_fallback
    assert result.primary_theme == "outros_indeterminado"
    assert result.candidate_theme in THEME_CLASSES
    assert result.confidence == pytest.approx(1 / len(THEME_CLASSES), abs=0.0001)
    assert result.abstention_reason == "below_threshold"
    assert result.top_topics == []


def test_empty_input_does_not_fabricate_confidence(predictor, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Empty input must not invoke the model")

    monkeypatch.setattr(predictor.model, "predict_proba", forbidden)
    result = predictor.predict_text(" \r\n ")
    assert result.confidence == 0
    assert result.candidate_theme is None
    assert result.abstention_reason == "empty_input"
    assert sum(result.probabilities.values()) == 0
    assert result.ranking == []


def test_segment_weights_are_measured_character_shares(predictor):
    text = "trabalho trabalho. familia familia familia. saude_sono saude_sono."
    result = predictor.destrinchar_diario(text, min_segment_chars=3)
    assert isinstance(result, DiaryTopicBreakdown)
    assert len(result.segments) == 3
    assert [s.theme for s in result.segments] == ["trabalho", "familia", "saude_sono"]
    count = sum(len(s.quote) for s in result.segments)
    assert result.analyzed_chars == count
    assert result.total_chars == len(text)
    assert result.omitted_chars == len(text) - count
    assert result.coverage_ratio == pytest.approx(count / len(text))
    assert result.weight_basis == "analyzed_characters"
    assert result.topic_weights["familia"] == pytest.approx(
        100 * len(result.segments[1].quote) / count, abs=0.01
    )
    assert sum(result.topic_weights.values()) == pytest.approx(100, abs=0.1)
    assert result.topic_weights["estudos"] == 0
    for segment in result.segments:
        assert text[segment.start_char : segment.end_char] == segment.quote


def test_unicode_crlf_and_short_segment_coverage(predictor):
    text = "Oi!\r\n  família 🧡 trabalho trabalho!\r\nSim."
    result = predictor.destrinchar_diario(text, min_segment_chars=15)
    assert len(result.segments) == 1
    segment = result.segments[0]
    assert text[segment.start_char : segment.end_char] == segment.quote
    assert segment.quote == "família 🧡 trabalho trabalho!"
    assert result.omitted_chars == len(text) - len(segment.quote)
    assert 0 < result.coverage_ratio < 1


def test_no_segments_has_no_textual_distribution(predictor):
    result = predictor.destrinchar_diario("trabalho", min_segment_chars=15)
    assert result.global_theme == "trabalho"
    assert sum(result.theme_percentages.values()) == pytest.approx(100, abs=0.1)
    assert sum(result.topic_weights.values()) == 0
    assert result.detected_topics == []
    assert result.analyzed_chars == 0
    assert result.omitted_chars == len("trabalho")
    assert result.coverage_ratio == 0


def test_empty_breakdown_has_zero_coverage(predictor):
    result = predictor.destrinchar_diario("")
    assert result.global_confidence == 0
    assert result.total_chars == result.analyzed_chars == result.omitted_chars == 0
    assert result.coverage_ratio == 0
    assert result.detected_topics == []
    assert sum(result.topic_weights.values()) == 0


def test_batch_preserves_order_and_abstention(predictor):
    results = predictor.predict_batch(["trabalho", "familia", ""])
    assert [r.primary_theme for r in results] == ["trabalho", "familia", "outros_indeterminado"]


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_invalid_threshold_rejected(predictor, threshold):
    with pytest.raises(ValueError, match="threshold"):
        predictor.predict_text("trabalho", threshold=threshold)


def test_invalid_segment_configuration_rejected(predictor):
    with pytest.raises(ValueError, match="positivo"):
        predictor.destrinchar_diario("trabalho", min_segment_chars=0)
    with pytest.raises(ValueError, match="segment_threshold"):
        predictor.destrinchar_diario("trabalho", segment_threshold=2)
