"""Configuração tipada para experimentos e pipelines de MLOps."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MLOpsConfig(BaseModel):
    """Parâmetros de execução do pipeline de MLOps e treinamento da rede neural."""

    experiment_name: str = Field(
        default="diario-emocional-sentimentos",
        description="Nome do experimento no MLflow",
    )
    model_name: str = Field(
        default="mlp-sentiment-classifier",
        description="Identificador do modelo no Model Registry",
    )
    split: str = Field(
        default="dev",
        description="Divisão do dataset para treino/validação ('dev' ou 'all')",
    )
    test_size: float = Field(
        default=0.25,
        ge=0.1,
        le=0.5,
        description="Proporção da divisão de validação",
    )
    random_seed: int = Field(
        default=42,
        description="Semente aleatória para reprodutibilidade estrita",
    )
    hidden_layer_sizes: list[int] = Field(
        default=[32, 16],
        description="Topologia das camadas ocultas do MLP",
    )
    alpha: float = Field(
        default=0.01,
        ge=0.0,
        description="Termo de regularização L2 da rede neural",
    )
    learning_rate_init: float = Field(
        default=0.001,
        gt=0.0,
        description="Taxa inicial de aprendizado",
    )
    max_iter: int = Field(
        default=200,
        ge=10,
        description="Número máximo de épocas/iterações",
    )
    max_features: int = Field(
        default=300,
        ge=50,
        description="Vocabulário máximo do TF-IDF",
    )
    tracking_uri: str = Field(
        default="sqlite:///mlflow.db",
        description="URI de tracking do MLflow (SQLite local ou servidor remoto)",
    )
    evaluate_holdout: bool = Field(
        default=False,
        description="Se verdadeiro, realiza teste cego final no split holdout",
    )
    min_accuracy_threshold: float = Field(
        default=0.20,
        description="Acurácia mínima exigida para aprovação do modelo",
    )
