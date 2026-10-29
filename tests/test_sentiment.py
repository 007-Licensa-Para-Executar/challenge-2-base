import pytest

from agents.extractor.contracts import Sentimento
from agents.extractor.sentiment import Polarity, analyze_polarity, validate_polarity


@pytest.mark.parametrize(
    "text,label",
    [
        ("Estou feliz e muito contente com o resultado.", "POSITIVO"),
        ("Minha irmã chegou de viagem; fiquei tão feliz de poder abraçá-la de novo",
         "POSITIVO"),
        (("Ganhei uma bolsa e estou feliz, embora as despesas em casa ainda preocupem; "
          "hoje quero celebrar a aprovação."), "POSITIVO"),
        ("Hoje consegui descansar depois da consulta; estou calmo.", "NEUTRO"),
        ("Passei a tarde olhando o mar e finalmente me senti em paz.", "NEUTRO"),
        ("A fisioterapia avança devagar e me frustra não conseguir voltar a correr.",
         "NEGATIVO"),
        ("Estou apenas chateado com o barulho do vizinho.", "NEGATIVO"),
        ("Foi péssimo, horrível e frustrante.", "NEGATIVO"),
        ("Hoje fui ao trabalho.", "NEUTRO"),
    ],
)
def test_portuguese_polarity_labels(text, label):
    assert analyze_polarity(text).label == label


def test_extreme_opposite_polarity_is_flagged_with_absolute_distance():
    validation = validate_polarity(Sentimento.ALEGRIA, Polarity("NEGATIVO", -0.8))
    assert validation.discrepancia_detectada
    assert validation.distancia_polaridade == pytest.approx(1.8)


def test_non_extreme_opposite_polarity_is_not_flagged():
    validation = validate_polarity(Sentimento.ALEGRIA, Polarity("NEGATIVO", -0.4))
    assert not validation.discrepancia_detectada
    assert validation.distancia_polaridade == pytest.approx(1.4)


def test_portuguese_degree_intensifier_increases_positive_score():
    base_score = analyze_polarity("Fiquei feliz.").score
    intensified_score = analyze_polarity("Fiquei tão feliz.").score
    assert intensified_score > base_score
