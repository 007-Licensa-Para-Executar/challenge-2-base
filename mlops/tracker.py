"""Rastreamento de experimentos, métricas e artefatos via MLflow."""

from __future__ import annotations

import os
import types
from typing import Any, Self

# Garante compatibilidade caso o usuário opte por tracking local em arquivos
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import mlflow
import mlflow.sklearn


class MLOpsTracker:
    """Gerenciador de rastreamento de experimentos com MLflow."""

    def __init__(self, tracking_uri: str = "mlruns", experiment_name: str = "diario-emocional") -> None:
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        self.active_run: mlflow.ActiveRun | None = None

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
            k: str(v) if isinstance(v, (list, tuple, dict)) else v
            for k, v in params.items()
        }
        mlflow.log_params(flat_params)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Registra métricas escalares no MLflow."""
        mlflow.log_metrics(metrics, step=step)

    def log_dict(self, data: dict[str, Any], artifact_file: str) -> None:
        """Registra dicionário estruturado como artefato JSON."""
        mlflow.log_dict(data, artifact_file)

    def log_text(self, text: str, artifact_file: str) -> None:
        """Registra relatório de texto como artefato."""
        mlflow.log_text(text, artifact_file)

    def log_figure(self, fig: Any, artifact_file: str) -> None:
        """Registra figura matplotlib gerada como imagem."""
        mlflow.log_figure(fig, artifact_file)

    def log_model(self, sk_model: Any, artifact_path: str = "model") -> None:
        """Registra o pipeline treinado do scikit-learn como artefato MLmodel."""
        mlflow.sklearn.log_model(
            sk_model=sk_model,
            artifact_path=artifact_path,
            serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
        )

    def end_run(self) -> None:
        """Encerra a execução ativa."""
        if self.active_run:
            mlflow.end_run()
            self.active_run = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.end_run()
