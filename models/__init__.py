"""Módulo de modelos de Deep Learning para classificação clínica de temas e emoções."""

from typing import TYPE_CHECKING

from models.emotion_net import EKMAN_LABELS, EmotionNeuralNetwork, EmotionPipeline
from models.emotion_predictor import EmotionDiaryPredictor, EmotionDiaryResult
from models.emotion_taxonomy import (
    DIVERTIDAMENTE_CORE_EMOTIONS,
    DIVERTIDAMENTE_EMOTIONS,
    EmotionDivertidamente,
    SubEmotion,
    canonicalize_emotion_id,
    get_all_divertidamente_taxonomy,
    get_divertidamente_emotion,
    resolve_sub_emotion,
)
from models.numpy_mlp import NumpyClinicalMLP
from models.sbert_embedder import SBERTEmbedder

if TYPE_CHECKING:
    from models.predictor import (
        ClinicalThemePredictor,
        DiaryTopicBreakdown,
        DiaryTopicSegment,
        TopicDistribution,
    )


def __getattr__(name: str):
    if name == "ClinicalTextEmbedder":
        from models.embedder import ClinicalTextEmbedder

        return ClinicalTextEmbedder
    if name in {"THEME_CLASSES", "ClinicalThemeMLP"}:
        from models import torch_mlp

        return getattr(torch_mlp, name)
    if name in {
        "ClinicalThemePredictor",
        "DiaryTopicBreakdown",
        "DiaryTopicSegment",
        "TopicDistribution",
    }:
        import models.predictor as _predictor

        return getattr(_predictor, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "DIVERTIDAMENTE_CORE_EMOTIONS",
    "DIVERTIDAMENTE_EMOTIONS",
    "EKMAN_LABELS",
    "THEME_CLASSES",
    "ClinicalTextEmbedder",
    "ClinicalThemeMLP",
    "ClinicalThemePredictor",
    "DiaryTopicBreakdown",
    "DiaryTopicSegment",
    "EmotionDiaryPredictor",
    "EmotionDiaryResult",
    "EmotionDivertidamente",
    "EmotionNeuralNetwork",
    "EmotionPipeline",
    "NumpyClinicalMLP",
    "SBERTEmbedder",
    "SubEmotion",
    "TopicDistribution",
    "canonicalize_emotion_id",
    "get_all_divertidamente_taxonomy",
    "get_divertidamente_emotion",
    "resolve_sub_emotion",
]
