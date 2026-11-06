"""Gerenciador de rastreamento de experimentos e artefatos de MLOps com MLflow."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import mlflow
import numpy as np

logger = logging.getLogger(__name__)


class MLFlowTracker:
    """Encapsula operações do MLflow para rastreabilidade de experimentos e modelos."""

    def __init__(
        self,
        experiment_name: str = "Clinical_Theme_MLP",
        db_uri: str = "sqlite:///mlflow.db",
        tracking_uri: str | None = None,
    ) -> None:
        self.experiment_name = experiment_name
        self.db_uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI") or db_uri
        self.tracking_uri = self.db_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)

    def log_params(self, params: dict[str, Any]) -> None:
        """Registra dicionário de hiperparâmetros na run ativa."""
        mlflow.log_params(params)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Registra métricas escalares com step opcional."""
        mlflow.log_metrics(metrics, step=step)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Registra uma métrica individual."""
        mlflow.log_metric(key, value, step=step)

    def log_artifact(self, artifact_path: str | Path) -> None:
        """Registra um arquivo como artefato da run ativa."""
        p = Path(artifact_path)
        if p.exists():
            mlflow.log_artifact(str(p))
            logger.info("Artefato registrado no MLflow: %s", p)
        else:
            logger.warning("Artefato não encontrado para registro: %s", p)

    def log_confusion_matrix(
        self,
        y_true: list[int] | np.ndarray,
        y_pred: list[int] | np.ndarray,
        labels: list[str],
        output_dir: str | Path = "dist",
    ) -> tuple[Path, Path | None]:
        """Calcula matriz de confusão, gera JSON e imagem PNG, e os registra no MLflow."""
        from sklearn.metrics import confusion_matrix

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
        cm_data = {
            "labels": labels,
            "matrix": cm.tolist(),
        }

        json_path = out_path / "confusion_matrix.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cm_data, f, ensure_ascii=False, indent=2)

        self.log_artifact(json_path)

        png_path: Path | None = None
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
            ax.figure.colorbar(im, ax=ax)

            ax.set(
                xticks=np.arange(cm.shape[1]),
                yticks=np.arange(cm.shape[0]),
                xticklabels=labels,
                yticklabels=labels,
                title="Matriz de Confusão - Macrotemas Clínicos",
                ylabel="Rótulo Real",
                xlabel="Rótulo Predito",
            )
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

            thresh = cm.max() / 2.0
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(
                        j,
                        i,
                        format(cm[i, j], "d"),
                        ha="center",
                        va="center",
                        color="white" if cm[i, j] > thresh else "black",
                    )
            fig.tight_layout()

            png_path = out_path / "confusion_matrix.png"
            fig.savefig(png_path, dpi=150)
            plt.close(fig)
            self.log_artifact(png_path)
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("Não foi possível gerar gráfico PNG da matriz de confusão: %s", e)

        return json_path, png_path

    def log_training_session(
        self,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts_paths: list[str | Path] | None = None,
        run_name: str = "training_run",
    ) -> str:
        """Executa um ciclo completo de registro com context manager."""
        with mlflow.start_run(run_name=run_name) as run:
            self.log_params(params)
            self.log_metrics(metrics)
            if artifacts_paths:
                for path in artifacts_paths:
                    self.log_artifact(path)
            return run.info.run_id

    @staticmethod
    def get_best_model_run(
        experiment_name: str = "Clinical_Theme_MLP",
        metric_name: str = "final_test_macro_f1",
    ) -> Any:
        """Busca o melhor run registrado no MLflow ordenado por uma métrica."""
        exp = mlflow.get_experiment_by_name(experiment_name)
        if not exp:
            return None
        runs = mlflow.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=[f"metrics.{metric_name} DESC"],
            max_results=1,
        )
        return runs.iloc[0] if not runs.empty else None
