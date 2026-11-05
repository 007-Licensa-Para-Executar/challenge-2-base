"""Classificador baseline de referência para comparação de modelos."""

from __future__ import annotations

from typing import Any

from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)


class SentimentBaselineClassifier:
    """Baseline estocástico/frequencial para classificar sentimentos."""

    def __init__(self, strategy: str = "most_frequent", random_state: int = 42) -> None:
        self.strategy = strategy
        self.random_state = random_state
        self.model = DummyClassifier(strategy=strategy, random_state=random_state)
        self.classes_: list[str] = []

    def fit(self, texts: list[str], labels: list[str]) -> SentimentBaselineClassifier:
        self.model.fit(texts, labels)
        self.classes_ = list(self.model.classes_)
        return self

    def predict(self, texts: list[str]) -> list[str]:
        return list(self.model.predict(texts))

    def evaluate(self, texts: list[str], labels: list[str]) -> dict[str, Any]:
        """Calcula métricas padronizadas para o baseline."""
        preds = self.predict(texts)
        return {
            "accuracy": float(accuracy_score(labels, preds)),
            "f1_macro": float(f1_score(labels, preds, average="macro", zero_division=0)),
            "precision_macro": float(precision_score(labels, preds, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(labels, preds, average="macro", zero_division=0)),
            "report": classification_report(labels, preds, output_dict=True, zero_division=0),
        }
