"""Deterministic Portuguese polarity analysis using VADER's scoring algorithm."""

from dataclasses import dataclass

from vaderSentiment import vaderSentiment
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .contracts import Sentimento, ValidationMetrics

PORTUGUESE_LEXICON = {
    "feliz": 2.5,
    "felizes": 2.5,
    "felicidade": 2.5,
    "alegre": 2.4,
    "alegria": 2.4,
    "contente": 2.3,
    "satisfeito": 2.4,
    "satisfeita": 2.4,
    "orgulhoso": 2.5,
    "orgulhosa": 2.5,
    "aliviado": 2.2,
    "aliviada": 2.2,
    "celebrar": 2.2,
    "aprovação": 1.9,
    "aprovacao": 1.9,
    "esperançoso": 2.0,
    "esperancoso": 2.0,
    "ótimo": 3.1,
    "otimo": 3.1,
    "ótima": 3.1,
    "otima": 3.1,
    "excelente": 3.4,
    "maravilhoso": 3.4,
    "maravilhosa": 3.4,
    "bom": 1.9,
    "boa": 1.9,
    "bem": 1.7,
    "gosto": 1.9,
    "adoro": 3.0,
    "adorei": 3.0,
    "triste": -2.2,
    "tristeza": -2.0,
    "raiva": -2.2,
    "irritado": -2.0,
    "irritada": -2.0,
    "furioso": -3.0,
    "furiosa": -3.0,
    "medo": -2.0,
    "assustado": -2.0,
    "assustada": -2.0,
    "preocupado": -1.8,
    "preocupada": -1.8,
    "frustrado": -2.3,
    "frustrada": -2.3,
    "frustrante": -2.0,
    "frustra": -2.0,
    "chateado": -1.8,
    "chateada": -1.8,
    "preocupa": -1.8,
    "péssimo": -3.4,
    "pessimo": -3.4,
    "péssima": -3.4,
    "pessima": -3.4,
    "horrível": -3.4,
    "horrivel": -3.4,
    "terrível": -3.2,
    "terrivel": -3.2,
    "odeio": -3.0,
    "odiei": -3.0,
    "desanimado": -2.0,
    "desanimada": -2.0,
    "decepcionado": -2.2,
    "decepcionada": -2.2,
    "calma": 0.0,
    "calmo": 0.0,
    "calmos": 0.0,
    "calmas": 0.0,
    "tranquilo": 0.0,
    "tranquila": 0.0,
    "tranquilos": 0.0,
    "tranquilas": 0.0,
    "paz": 0.0,
    "tranquilidade": 0.0,
}

_PORTUGUESE_NEGATIONS = {
    "não",
    "nao",
    "nunca",
    "jamais",
    "nem",
    "nenhum",
    "nenhuma",
    "nada",
    "ninguém",
    "ninguem",
    "sem",
    "tampouco",
}
_PORTUGUESE_BOOSTERS = {
    "muito": 0.293,
    "muita": 0.293,
    "muitos": 0.293,
    "muitas": 0.293,
    "tão": 0.293,
    "tao": 0.293,
    "extremamente": 0.293,
    "bastante": 0.293,
    "super": 0.293,
    "totalmente": 0.293,
    "pouco": -0.293,
    "pouca": -0.293,
    "quase": -0.293,
}
_POLARITY_ANCHORS = {
    Sentimento.ALEGRIA: 1.0,
    Sentimento.TRISTEZA: -1.0,
    Sentimento.RAIVA: -1.0,
    Sentimento.MEDO: -1.0,
    Sentimento.PREOCUPACAO: -1.0,
    Sentimento.FRUSTRACAO: -1.0,
    Sentimento.CALMA: 0.0,
    Sentimento.NAO_IDENTIFICADO: 0.0,
}
_LABEL_THRESHOLD = 0.05
_EXTREME_SCORE_THRESHOLD = 0.7


class PortugueseVader(SentimentIntensityAnalyzer):
    @staticmethod
    def _but_check(words_and_emoticons, sentiments):
        words = [str(word).lower() for word in words_and_emoticons]
        conjunction = next((word for word in ("but", "mas") if word in words), None)
        if conjunction is None:
            return sentiments
        boundary = words.index(conjunction)
        return [
            score * (0.5 if index < boundary else 1.5 if index > boundary else 1.0)
            for index, score in enumerate(sentiments)
        ]


@dataclass(frozen=True)
class Polarity:
    label: str
    score: float


vaderSentiment.NEGATE = [
    *vaderSentiment.NEGATE,
    *sorted(_PORTUGUESE_NEGATIONS.difference(vaderSentiment.NEGATE)),
]
vaderSentiment.BOOSTER_DICT.update(_PORTUGUESE_BOOSTERS)
_ANALYZER = PortugueseVader()
_ANALYZER.lexicon = PORTUGUESE_LEXICON


def analyze_polarity(text: str) -> Polarity:
    score = _ANALYZER.polarity_scores(text)["compound"]
    if score >= _LABEL_THRESHOLD:
        label = "POSITIVO"
    elif score <= -_LABEL_THRESHOLD:
        label = "NEGATIVO"
    else:
        label = "NEUTRO"
    return Polarity(label=label, score=score)


def validate_polarity(sentiment: Sentimento, polarity: Polarity) -> ValidationMetrics:
    anchor = _POLARITY_ANCHORS[sentiment]
    distance = abs(anchor - polarity.score)
    discrepancy = (
        anchor >= 0.6 and polarity.score <= -_EXTREME_SCORE_THRESHOLD
    ) or (
        anchor <= -0.6 and polarity.score >= _EXTREME_SCORE_THRESHOLD
    )
    return ValidationMetrics(
        nlp_polaridade=polarity.label,
        nlp_score=polarity.score,
        discrepancia_detectada=discrepancy,
        distancia_polaridade=distance,
    )
