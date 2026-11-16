"""Métricas de classificação compartilhadas pelos modelos do projeto."""

from __future__ import annotations

from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)


def score_predictions(labels: list[str], predictions: list[str]) -> dict[str, Any]:
    """Calcula acurácia, F1 macro, precisão, recall e o relatório por classe."""
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "f1_macro": float(f1_score(labels, predictions, average="macro", zero_division=0)),
        "precision_macro": float(
            precision_score(labels, predictions, average="macro", zero_division=0)
        ),
        "recall_macro": float(recall_score(labels, predictions, average="macro", zero_division=0)),
        "report": classification_report(labels, predictions, output_dict=True, zero_division=0),
    }
