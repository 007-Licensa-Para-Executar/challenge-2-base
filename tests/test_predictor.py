"""Testes unitários para o inferenciador e decompositor temático ClinicalThemePredictor."""

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from models.predictor import (
    ClinicalThemePredictor,
    DiaryTopicBreakdown,
    TopicDistribution,
)
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP


@pytest.fixture(scope="module")
def predictor():
    """Instância compartilhada do preditor carregando os artefatos de dist/."""
    return ClinicalThemePredictor()


def test_predictor_initialization_with_defaults(predictor):
    """Valida inicialização padrão carregando os artefatos persistidos."""
    assert predictor.model is not None
    assert predictor.vectorizer is not None
    assert isinstance(predictor.model, ClinicalThemeMLP)
    assert isinstance(predictor.vectorizer, TfidfVectorizer)
    assert not predictor.model.training


def test_predictor_predict_text_theme_separation(predictor):
    """Valida a separação de temas com percentuais claros (ex: alto trabalho, baixo familia)."""
    text = (
        "Acabei de sair de uma reuniao com a diretoria da empresa e a pressao "
        "por metas no trabalho esta insuportavel."
    )
    result = predictor.predict_text(text)

    assert isinstance(result, TopicDistribution)
    assert result.primary_theme == "trabalho"
    assert result.confidence > 0.50
    assert not result.is_fallback

    # Percentuais devem somar ~100.0%
    total_pct = sum(result.percentages.values())
    assert abs(total_pct - 100.0) < 0.2

    # Probabilidades devem somar ~1.0
    total_prob = sum(result.probabilities.values())
    assert abs(total_prob - 1.0) < 0.01

    # O tema principal deve ter o maior percentual
    assert result.percentages["trabalho"] > 50.0
    # Outros temas devem ter percentuais baixos ou próximos de zero
    assert result.percentages["familia"] < 10.0
    assert result.percentages["estudos"] < 10.0

    # Validação do ranking ordenado decrescente
    assert result.ranking[0]["tema"] == "trabalho"
    for i in range(len(result.ranking) - 1):
        assert result.ranking[i]["percentual"] >= result.ranking[i + 1]["percentual"]


def test_predictor_destrinchar_diario_multi_topic(predictor):
    """Valida o destrinchamento de diário contendo múltiplos tópicos e evidências literais.

    Demonstra que o diário é decomposto em tópicos com pesos proporcionais (ex: 60% tema_1,
    15% tema_3, 0% tema_2) e citações literais ancoradas com fidelidade estrita.
    """
    text = (
        "Acabei de sair de uma reuniao com a diretoria da empresa e a pressao por metas no trabalho esta insuportavel. "
        "Ao mesmo tempo meu casamento esta em crise e meu marido reclama que estamos distantes. "
        "Para piorar tive uma insonia horrivel e dor no corpo a noite toda."
    )

    breakdown = predictor.destrinchar_diario(text, min_segment_chars=15)

    assert isinstance(breakdown, DiaryTopicBreakdown)
    assert len(breakdown.segments) == 3

    # Segmento 1: Trabalho
    seg1 = breakdown.segments[0]
    assert seg1.theme == "trabalho"
    assert "trabalho" in seg1.quote.lower() or "empresa" in seg1.quote.lower()

    # Segmento 2: Relacionamentos
    seg2 = breakdown.segments[1]
    assert seg2.theme == "relacionamentos"
    assert "casamento" in seg2.quote.lower() or "marido" in seg2.quote.lower()

    # Segmento 3: Saúde & Sono
    seg3 = breakdown.segments[2]
    assert seg3.theme == "saude_sono"
    assert "insonia" in seg3.quote.lower() or "corpo" in seg3.quote.lower()

    # Validação de ancoragem literal de citações (Span Fidelity):
    # O trecho extraído deve coincidir rigorosamente com o texto original
    for seg in breakdown.segments:
        assert text[seg.start_char : seg.end_char] == seg.quote

    # Validação de pesos proporcionais por tópico no diário
    assert breakdown.topic_weights["trabalho"] > 0.0
    assert breakdown.topic_weights["relacionamentos"] > 0.0
    assert breakdown.topic_weights["saude_sono"] > 0.0
    # Temas não abordados devem ter 0.0%
    assert breakdown.topic_weights["familia"] == 0.0
    assert breakdown.topic_weights["estudos"] == 0.0
    assert breakdown.topic_weights["financas"] == 0.0
    assert breakdown.topic_weights["luto"] == 0.0

    # Tópicos detectados
    assert "trabalho" in breakdown.detected_topics
    assert "relacionamentos" in breakdown.detected_topics
    assert "saude_sono" in breakdown.detected_topics
    assert "familia" not in breakdown.detected_topics

    # Resumo descritivo presente
    assert isinstance(breakdown.summary, str)
    assert "trabalho" in breakdown.summary


def test_predictor_empty_and_neutral_fallback(predictor):
    """Valida salvaguarda em textos vazios ou sem conteúdo clínico claro."""
    # 1. Texto vazio
    empty_res = predictor.predict_text("")
    assert empty_res.primary_theme == "outros_indeterminado"
    assert empty_res.is_fallback is True

    empty_breakdown = predictor.destrinchar_diario("")
    assert empty_breakdown.global_theme == "outros_indeterminado"
    assert len(empty_breakdown.segments) == 0

    # 2. Texto neutro cotidiano
    neutral_text = "Hoje fui na padaria comprar pao e voltei ouvindo o barulho da chuva."
    neutral_res = predictor.predict_text(neutral_text)
    assert isinstance(neutral_res, TopicDistribution)
    # Deve recair em outros_indeterminado
    assert neutral_res.primary_theme == "outros_indeterminado"


def test_predictor_batch_prediction(predictor):
    """Valida inferência vetorizada em lote."""
    texts = [
        "Reuniao com meu chefe sobre metas de trabalho.",
        "Meu casamento esta em crise e discutimos.",
        "Nao durmo faz tres dias com insonia e cansaco.",
    ]
    results = predictor.predict_batch(texts)
    assert len(results) == 3
    for res in results:
        assert isinstance(res, TopicDistribution)
        assert res.primary_theme in THEME_CLASSES
        assert abs(sum(res.percentages.values()) - 100.0) < 0.2


def test_predictor_custom_instances():
    """Valida construção injetando modelos e vetorizadores customizados em memória."""
    vectorizer = TfidfVectorizer(max_features=32)
    corpus = [
        "trabalho empresa chefe",
        "familia pai mae irmao",
        "dia neutro padaria chuva",
    ]
    vectorizer.fit(corpus)

    model = ClinicalThemeMLP(input_dim=len(vectorizer.vocabulary_), num_classes=9)
    custom_predictor = ClinicalThemePredictor(model=model, vectorizer=vectorizer)

    res = custom_predictor.predict_text("trabalho empresa")
    assert isinstance(res, TopicDistribution)
    assert len(res.percentages) == 9
