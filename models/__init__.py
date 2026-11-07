"""Módulo de modelos de Deep Learning para classificação clínica de macrotemas."""

from typing import TYPE_CHECKING

from models.numpy_mlp import NumpyClinicalMLP
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP

if TYPE_CHECKING:
    from models.predictor import (
        ClinicalThemePredictor,
        DiaryTopicBreakdown,
        DiaryTopicSegment,
        TopicDistribution,
    )


def __getattr__(name: str):
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
    "THEME_CLASSES",
    "ClinicalThemeMLP",
    "ClinicalThemePredictor",
    "DiaryTopicBreakdown",
    "DiaryTopicSegment",
    "NumpyClinicalMLP",
    "TopicDistribution",
]
