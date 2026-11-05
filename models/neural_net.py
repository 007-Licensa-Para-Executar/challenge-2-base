"""Rede neural simples (Multi-Layer Perceptron) para classificação de texto."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline


class SentimentNeuralNetClassifier:
    """Classificador baseado em Rede Neural MLP com extração TF-IDF."""

    def __init__(
        self,
        hidden_layer_sizes: tuple[int, ...] = (32, 16),
        alpha: float = 0.01,
        learning_rate_init: float = 0.001,
        max_iter: int = 200,
        random_state: int = 42,
        max_features: int = 300,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> None:
        self.hidden_layer_sizes = hidden_layer_sizes
        self.alpha = alpha
        self.learning_rate_init = learning_rate_init
        self.max_iter = max_iter
        self.random_state = random_state
        self.max_features = max_features
        self.ngram_range = ngram_range

        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        max_features=self.max_features,
                        ngram_range=self.ngram_range,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=self.hidden_layer_sizes,
                        activation="relu",
                        solver="adam",
                        alpha=self.alpha,
                        learning_rate_init=self.learning_rate_init,
                        max_iter=self.max_iter,
                        random_state=self.random_state,
                        early_stopping=False,
                    ),
                ),
            ]
        )

    def fit(self, texts: list[str], labels: list[str]) -> SentimentNeuralNetClassifier:
        self.pipeline.fit(texts, labels)
        return self

    def predict(self, texts: list[str]) -> list[str]:
        return list(self.pipeline.predict(texts))

    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        probs = self.pipeline.predict_proba(texts)
        return probs.tolist()

    @property
    def classes_(self) -> list[str]:
        mlp: MLPClassifier = self.pipeline.named_steps["mlp"]
        return list(mlp.classes_)

    @property
    def loss_curve_(self) -> list[float]:
        mlp: MLPClassifier = self.pipeline.named_steps["mlp"]
        return list(getattr(mlp, "loss_curve_", []))

    def evaluate(self, texts: list[str], labels: list[str]) -> dict[str, Any]:
        """Calcula métricas de desempenho e matriz de confusão."""
        preds = self.predict(texts)
        classes = self.classes_
        cm = confusion_matrix(labels, preds, labels=classes).tolist()
        return {
            "accuracy": float(accuracy_score(labels, preds)),
            "f1_macro": float(f1_score(labels, preds, average="macro", zero_division=0)),
            "precision_macro": float(precision_score(labels, preds, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(labels, preds, average="macro", zero_division=0)),
            "confusion_matrix": cm,
            "classes": classes,
            "report": classification_report(labels, preds, output_dict=True, zero_division=0),
        }

    def save(self, filepath: Path | str) -> None:
        """Serializa o pipeline treinado."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, filepath: Path | str) -> SentimentNeuralNetClassifier:
        """Carrega um modelo serializado."""
        instance = cls()
        instance.pipeline = joblib.load(filepath)
        return instance
