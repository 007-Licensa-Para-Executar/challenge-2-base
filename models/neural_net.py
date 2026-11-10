"""Rede neural simples (Multi-Layer Perceptron) para classificação de texto."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from models.metrics import score_predictions


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
        predictions = self.predict(texts)
        classes = self.classes_
        metrics = score_predictions(labels, predictions)
        metrics["confusion_matrix"] = confusion_matrix(labels, predictions, labels=classes).tolist()
        metrics["classes"] = classes
        return metrics

    def save(self, filepath: Path | str) -> None:
        """Serializa o pipeline treinado."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, filepath: Path | str) -> SentimentNeuralNetClassifier:
        """Carrega um modelo serializado e recupera os hiperparâmetros do pipeline."""
        pipeline = joblib.load(filepath)
        tfidf: TfidfVectorizer = pipeline.named_steps["tfidf"]
        mlp: MLPClassifier = pipeline.named_steps["mlp"]
        instance = cls(
            hidden_layer_sizes=tuple(mlp.hidden_layer_sizes),
            alpha=float(mlp.alpha),
            learning_rate_init=float(mlp.learning_rate_init),
            max_iter=int(mlp.max_iter),
            random_state=int(mlp.random_state),
            max_features=int(tfidf.max_features),
            ngram_range=tuple(tfidf.ngram_range),
        )
        instance.pipeline = pipeline
        return instance
