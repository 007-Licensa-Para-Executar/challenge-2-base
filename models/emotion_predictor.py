"""Inferenciador emocional para relatos de diários de pacientes.

Utiliza a rede neural treinada (GoEmotions PT-BR) e a taxonomia inspirada no filme
Divertidamente (Inside Out) e na plataforma How We Feel para extrair a emoção
predominante, suas cores associadas e o sub-sentimento mais granular com seu símbolo.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents.patient_diary.contracts import EmotionCheckin

from models.emotion_net import EKMAN_LABELS, EmotionPipeline
from models.emotion_taxonomy import (
    NEUTRO_DEF,
    SubEmotion,
    get_divertidamente_emotion,
    resolve_sub_emotion,
)

logger = logging.getLogger(__name__)

DEFAULT_EMOTION_MODEL_PATH = Path("dist/emotion_classifier.joblib")


@dataclass
class EmotionDiaryResult:
    """Resultado da análise emocional do diário de um paciente com Divertidamente e How We Feel."""

    primary_emotion: str
    confidence: float
    relative_score: float
    detected_emotions: list[str]
    probabilities: dict[str, float]
    thresholds: dict[str, float]
    is_risk_emotion: bool
    character: str = ""
    color_name: str = ""
    color_hex: str = ""
    color_secondary_hex: str = ""
    active_sub_emotion: SubEmotion | None = None
    all_sub_emotions: list[SubEmotion] = field(default_factory=list)
    ekman_emotion: str = ""
    score_semantics: str = "threshold_relative_ratio"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.active_sub_emotion is not None:
            data["active_sub_emotion"] = self.active_sub_emotion.to_dict()
        data["all_sub_emotions"] = [
            s.to_dict() if hasattr(s, "to_dict") else s for s in self.all_sub_emotions
        ]
        return data

    def to_checkin(self, entry_id: str) -> EmotionCheckin:
        """Converte o resultado emocional no contrato EmotionCheckin do diário do paciente."""
        from agents.patient_diary.contracts import parse_emotion_checkin

        sub_name = self.active_sub_emotion.nome if self.active_sub_emotion else self.character
        sub_symbol = self.active_sub_emotion.simbolo if self.active_sub_emotion else "⚖️"
        clamped_conf = min(1.0, max(0.0, float(round(self.confidence, 4))))
        return parse_emotion_checkin(
            entry_id=entry_id,
            primary_emotion=self.primary_emotion.lower(),
            character=self.character,
            color_name=self.color_name,
            color_hex=self.color_hex,
            sub_emotion_name=sub_name,
            sub_emotion_symbol=sub_symbol,
            confidence=clamped_conf,
            is_risk_emotion=self.is_risk_emotion,
        )


class EmotionDiaryPredictor:
    """Preditor de emoções clínicas alimentado pela rede neural NumPy e taxonomia Divertidamente."""

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

    def predict(self, diary_text: str | None) -> EmotionDiaryResult:
        """Extrai a emoção mais condizente com o relato do paciente e seus atributos visuais."""
        if not self.is_ready():
            raise RuntimeError(
                f"Modelo de emoções não carregado. Execute 'python -m models.train_emotion' para gerar {self.model_path}."
            )

        assert self.pipeline is not None
        clean_text = (diary_text or "").strip()
        if not clean_text:
            neutro_sub = NEUTRO_DEF.sub_sentimentos[0]
            return EmotionDiaryResult(
                primary_emotion=NEUTRO_DEF.id,
                character=NEUTRO_DEF.personagem,
                color_name=NEUTRO_DEF.cor_nome,
                color_hex=NEUTRO_DEF.cor_hex,
                color_secondary_hex=NEUTRO_DEF.cor_secundaria_hex,
                active_sub_emotion=neutro_sub,
                all_sub_emotions=list(NEUTRO_DEF.sub_sentimentos),
                ekman_emotion="neutro",
                confidence=1.0,
                relative_score=1.0,
                detected_emotions=["neutro"],
                probabilities={lbl: (1.0 if lbl == "neutro" else 0.0) for lbl in EKMAN_LABELS},
                thresholds=dict(
                    zip(EKMAN_LABELS, self.pipeline.thresholds_.tolist(), strict=False)
                ),
                is_risk_emotion=False,
            )

        res = self.pipeline.predict_primary_emotion(clean_text)
        raw_primary = res["primary_emotion"]
        profile = get_divertidamente_emotion(raw_primary)
        active_sub = resolve_sub_emotion(profile.id, clean_text)

        return EmotionDiaryResult(
            primary_emotion=profile.id,
            character=profile.personagem,
            color_name=profile.cor_nome,
            color_hex=profile.cor_hex,
            color_secondary_hex=profile.cor_secundaria_hex,
            active_sub_emotion=active_sub,
            all_sub_emotions=list(profile.sub_sentimentos),
            ekman_emotion=raw_primary,
            confidence=res["confidence"],
            relative_score=res["relative_score"],
            detected_emotions=res["detected_emotions"],
            probabilities=res["probabilities"],
            thresholds=res["thresholds"],
            is_risk_emotion=res["is_risk_emotion"],
        )

    def analyze_entry(self, entry: Any, text: str | None = None) -> EmotionCheckin:
        """Processa um PatientEntry (ou similar) e retorna seu EmotionCheckin enriquecido."""
        raw_text = text if text is not None else getattr(entry, "original_text", "")
        result = self.predict(raw_text)
        entry_id = getattr(entry, "entry_id", "entry_unspecified")
        return result.to_checkin(entry_id=entry_id)

    def predict_batch(self, diary_texts: list[str]) -> list[EmotionDiaryResult]:
        return [self.predict(t) for t in diary_texts]
