"""Inferenciador emocional para relatos de diários de pacientes.

Utiliza a rede neural treinada para extrair a emoção predominante (Single Label)
e o perfil multirrótulo de sentimentos do paciente a partir do texto de seu diário.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from models.emotion_net import EKMAN_LABELS, EmotionPipeline

logger = logging.getLogger(__name__)

DEFAULT_EMOTION_MODEL_PATH = Path("dist/emotion_classifier.joblib")


@dataclass
class EmotionDiaryResult:
    """Resultado da análise emocional do diário de um paciente."""

    primary_emotion: str
    confidence: float
    relative_score: float
    detected_emotions: list[str]
    probabilities: dict[str, float]
    thresholds: dict[str, float]
    is_risk_emotion: bool
    score_semantics: str = "threshold_relative_ratio"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EmotionDiaryPredictor:
    """Preditor de emoções clínicas alimentado pela rede neural NumPy."""

    def __init__(self, model_path: Path | str = DEFAULT_EMOTION_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.pipeline: EmotionPipeline | None = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            logger.warning(
                "Arquivo do modelo de emoções não encontrado em %s. Modo de inferência aguardando treino.",
                self.model_path,
            )
            return
        try:
            self.pipeline = EmotionPipeline.load(self.model_path)
            logger.info("Modelo de emoções carregado com sucesso de %s", self.model_path)
        except (OSError, TypeError, ValueError, KeyError) as exc:
            logger.error("Falha ao carregar modelo de emoções de %s: %s", self.model_path, exc)
            self.pipeline = None

    def is_ready(self) -> bool:
        return self.pipeline is not None

    def predict(self, diary_text: str) -> EmotionDiaryResult:
        """Extrai a emoção mais condizente com o relato do paciente."""
        if not self.is_ready():
            raise RuntimeError(
                f"Modelo de emoções não carregado. Execute 'python -m models.train_emotion' para gerar {self.model_path}."
            )

        assert self.pipeline is not None
        clean_text = diary_text.strip()
        if not clean_text:
            return EmotionDiaryResult(
                primary_emotion="neutro",
                confidence=1.0,
                relative_score=1.0,
                detected_emotions=["neutro"],
                probabilities={lbl: (1.0 if lbl == "neutro" else 0.0) for lbl in EKMAN_LABELS},
                thresholds=dict(zip(EKMAN_LABELS, self.pipeline.thresholds_.tolist())),
                is_risk_emotion=False,
            )

        res = self.pipeline.predict_primary_emotion(clean_text)
        return EmotionDiaryResult(
            primary_emotion=res["primary_emotion"],
            confidence=res["confidence"],
            relative_score=res["relative_score"],
            detected_emotions=res["detected_emotions"],
            probabilities=res["probabilities"],
            thresholds=res["thresholds"],
            is_risk_emotion=res["is_risk_emotion"],
        )

    def predict_batch(self, diary_texts: list[str]) -> list[EmotionDiaryResult]:
        return [self.predict(t) for t in diary_texts]
