"""Rastreamento de experimentos, métricas e artefatos via MLflow."""

from __future__ import annotations

import os
import types
from typing import Any, Self

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from mlops.store import sqlite_artifact_uri


class MLOpsTracker:
    """Gerenciador de rastreamento de experimentos com MLflow."""

    def __init__(
        self,
        tracking_uri: str = "sqlite:///mlflow.db",
        experiment_name: str = "diario-emocional-sentimentos",
    ) -> None:
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        mlflow.set_tracking_uri(self.tracking_uri)
        self.artifact_uri = self._ensure_experiment()
        self.active_run: mlflow.ActiveRun | None = None

    def _ensure_experiment(self) -> str | None:
        """Cria o experimento com artefatos ao lado do SQLite, se ainda não existir."""
        client = MlflowClient(tracking_uri=self.tracking_uri)
        artifact_uri = sqlite_artifact_uri(self.tracking_uri)
        existing = client.get_experiment_by_name(self.experiment_name)
        if existing is None:
            client.create_experiment(self.experiment_name, artifact_location=artifact_uri)
        mlflow.set_experiment(self.experiment_name)
        return artifact_uri

    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> mlflow.ActiveRun:
        """Inicia uma execução rastreada no MLflow."""
        self.active_run = mlflow.start_run(run_name=run_name, tags=tags)
        return self.active_run

    def log_params(self, params: dict[str, Any]) -> None:
        """Registra parâmetros e hiperparâmetros sanitizados."""
        flat_params = {
            key: str(value) if isinstance(value, (list, tuple, dict)) else value
            for key, value in params.items()
        }
        mlflow.log_params(flat_params)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Registra métricas escalares no MLflow."""
        mlflow.log_metrics(metrics, step=step)

    def set_tag(self, key: str, value: str) -> None:
        """Registra um rótulo da execução, como o resultado do gate."""
        mlflow.set_tag(key, value)

    def log_dict(self, data: dict[str, Any], artifact_file: str) -> None:
        """Registra dicionário estruturado como artefato JSON."""
        mlflow.log_dict(data, artifact_file)

    def log_figure(self, fig: Any, artifact_file: str) -> None:
        """Registra figura matplotlib gerada como imagem."""
        mlflow.log_figure(fig, artifact_file)

    def log_model(
        self,
        sk_model: Any,
        name: str = "sentiment-mlp",
        registered_model_name: str | None = None,
    ) -> mlflow.models.model.ModelInfo:
        """Registra o pipeline scikit-learn e, se pedido, publica no Model Registry."""
        return mlflow.sklearn.log_model(
            sk_model=sk_model,
            name=name,
            registered_model_name=registered_model_name,
            serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_SKOPS,
            skops_trusted_types=[
                "sklearn.neural_network._stochastic_optimizers.AdamOptimizer",
            ],
        )

    def end_run(self, status: str = "FINISHED") -> None:
        """Encerra a execução ativa com o status informado."""
        if self.active_run:
            mlflow.end_run(status=status)
            self.active_run = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.end_run(status="FAILED" if exc_type else "FINISHED")
