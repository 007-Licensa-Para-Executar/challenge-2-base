"""Pipeline automatizado e reproduzível de MLOps: dados, treino, baseline, avaliação e tracking."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from mlops.config import MLOpsConfig
from mlops.tracker import MLOpsTracker
from models.baseline import SentimentBaselineClassifier
from models.neural_net import SentimentNeuralNetClassifier

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "synthetic"


def compute_file_sha256(filepath: Path) -> str:
    """Calcula o digest SHA-256 do arquivo para rastreamento de linhagem de dados."""
    hasher = hashlib.sha256()
    with filepath.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_dataset(split: str = "dev", directory: Path = DATA_DIR) -> tuple[list[str], list[str], str]:
    """Carrega relatos e sentimentos sintéticos, retornando textos, rótulos e hash do dataset."""
    file_path = directory / f"{split}.jsonl"
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {file_path}")

    dataset_hash = compute_file_sha256(file_path)
    texts: list[str] = []
    labels: list[str] = []

    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        texts.append(item["text"])
        labels.append(item["expected"]["sentimento"])

    return texts, labels, dataset_hash


def plot_confusion_matrix(cm: list[list[int]], classes: list[str]) -> plt.Figure:
    """Gera figura de matriz de confusão para registro em artefatos de MLOps."""
    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.matshow(cm, cmap=plt.cm.Blues)
    fig.colorbar(cax)

    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=45, ha="left")
    ax.set_yticklabels(classes)

    for i in range(len(classes)):
        for j in range(len(classes)):
            val = cm[i][j]
            ax.text(j, i, str(val), ha="center", va="center", color="black" if val < 5 else "white")

    ax.set_xlabel("Predição do Modelo")
    ax.set_ylabel("Rótulo Real (Esperado)")
    ax.set_title("Matriz de Confusão - Classificação de Sentimentos", pad=20)
    plt.tight_layout()
    return fig


def run_mlops_pipeline(config: MLOpsConfig) -> dict[str, Any]:
    """Executa o ciclo completo de MLOps com rastreabilidade, baseline e modelo neural."""
    texts, labels, dataset_hash = load_dataset(split=config.split)

    # Divisão estratificada com fallback defensivo para conjuntos pequenos
    try:
        x_train, x_val, y_train, y_val = train_test_split(
            texts,
            labels,
            test_size=config.test_size,
            random_state=config.random_seed,
            stratify=labels,
        )
    except ValueError:
        x_train, x_val, y_train, y_val = train_test_split(
            texts,
            labels,
            test_size=config.test_size,
            random_state=config.random_seed,
        )

    unique_classes = sorted(set(labels))

    tracker = MLOpsTracker(
        tracking_uri=config.tracking_uri,
        experiment_name=config.experiment_name,
    )

    with tracker:
        tracker.start_run(
            run_name=f"run-{config.model_name}-seed{config.random_seed}",
            tags={
                "project": "challenge-2-diario-emocional",
                "framework": "scikit-learn-mlp",
                "dataset_split": config.split,
            },
        )

        # 1. Rastrear Linhagem e Metadados do Dataset
        tracker.log_params(
            {
                "dataset_split": config.split,
                "dataset_hash": dataset_hash,
                "total_samples": len(texts),
                "train_samples": len(x_train),
                "val_samples": len(x_val),
                "num_classes": len(unique_classes),
                "random_seed": config.random_seed,
                "test_size": config.test_size,
            }
        )

        # 2. Treinar e Avaliar Modelo Baseline
        baseline = SentimentBaselineClassifier(random_state=config.random_seed)
        baseline.fit(x_train, y_train)
        baseline_metrics = baseline.evaluate(x_val, y_val)

        tracker.log_metrics(
            {
                "baseline_val_accuracy": baseline_metrics["accuracy"],
                "baseline_val_f1_macro": baseline_metrics["f1_macro"],
            }
        )

        # 3. Treinar e Avaliar Rede Neural MLP
        tracker.log_params(
            {
                "model_type": "MLPClassifier",
                "hidden_layer_sizes": config.hidden_layer_sizes,
                "alpha": config.alpha,
                "learning_rate_init": config.learning_rate_init,
                "max_iter": config.max_iter,
                "max_features": config.max_features,
            }
        )

        nn_model = SentimentNeuralNetClassifier(
            hidden_layer_sizes=tuple(config.hidden_layer_sizes),
            alpha=config.alpha,
            learning_rate_init=config.learning_rate_init,
            max_iter=config.max_iter,
            random_state=config.random_seed,
            max_features=config.max_features,
        )
        nn_model.fit(x_train, y_train)

        # Registrar evolução da perda (loss curve) por época no MLflow
        for step, loss_val in enumerate(nn_model.loss_curve_):
            tracker.log_metrics({"training_loss": float(loss_val)}, step=step)

        # Avaliação no conjunto de validação
        val_metrics = nn_model.evaluate(x_val, y_val)
        tracker.log_metrics(
            {
                "val_accuracy": val_metrics["accuracy"],
                "val_f1_macro": val_metrics["f1_macro"],
                "val_precision_macro": val_metrics["precision_macro"],
                "val_recall_macro": val_metrics["recall_macro"],
            }
        )

        # 4. Artefatos de Diagnóstico e Explicabilidade
        cm_fig = plot_confusion_matrix(val_metrics["confusion_matrix"], val_metrics["classes"])
        tracker.log_figure(cm_fig, "confusion_matrix.png")
        plt.close(cm_fig)

        tracker.log_dict(val_metrics["report"], "classification_report.json")

        # 5. Critério de Aceite / Gate de Promoção
        is_promoted = bool(
            val_metrics["accuracy"] >= baseline_metrics["accuracy"]
            and val_metrics["accuracy"] >= config.min_accuracy_threshold
        )

        tracker.log_params({"model_promoted": is_promoted})
        tracker.log_model(nn_model.pipeline, artifact_path="model")

        # 6. Avaliação Final em Holdout (opcional)
        holdout_metrics: dict[str, Any] | None = None
        if config.evaluate_holdout:
            h_texts, h_labels, h_hash = load_dataset(split="holdout")
            holdout_metrics = nn_model.evaluate(h_texts, h_labels)
            tracker.log_metrics(
                {
                    "holdout_accuracy": holdout_metrics["accuracy"],
                    "holdout_f1_macro": holdout_metrics["f1_macro"],
                }
            )
            tracker.log_params({"holdout_dataset_hash": h_hash})

        run_id = tracker.active_run.info.run_id if tracker.active_run else "unknown"

    return {
        "status": "ok",
        "run_id": run_id,
        "dataset_hash": dataset_hash,
        "baseline_val_accuracy": baseline_metrics["accuracy"],
        "val_accuracy": val_metrics["accuracy"],
        "val_f1_macro": val_metrics["f1_macro"],
        "promoted": is_promoted,
        "holdout": holdout_metrics,
    }


def main() -> None:
    """Interface CLI para execução do pipeline de MLOps."""
    parser = argparse.ArgumentParser(
        description="Executa o pipeline reproduzível de MLOps do Diário Emocional."
    )
    parser.add_argument("--split", default="dev", choices=["dev"], help="Split base de treino")
    parser.add_argument(
        "--holdout",
        action="store_true",
        help="Executar avaliação cega no conjunto holdout",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatória para reprodutibilidade")
    parser.add_argument("--max-iter", type=int, default=200, help="Épocas máximas de treino do MLP")
    parser.add_argument(
        "--tracking-uri",
        default="sqlite:///mlflow.db",
        help="URI de rastreamento do MLflow (ex: sqlite:///mlflow.db)",
    )
    parser.add_argument("--output", type=str, help="Caminho para salvar o sumário JSON do pipeline")

    args = parser.parse_args()

    config = MLOpsConfig(
        split=args.split,
        random_seed=args.seed,
        max_iter=args.max_iter,
        tracking_uri=args.tracking_uri,
        evaluate_holdout=args.holdout,
    )

    print("=" * 60)
    print(" INICIANDO PIPELINE DE MLOPS - BEM-ESTAR")
    print(f" Experimento: {config.experiment_name}")
    print(f" Tracking URI: {config.tracking_uri}")
    print(f" Semente: {config.random_seed} | Max Iter: {config.max_iter}")
    print("=" * 60)

    result = run_mlops_pipeline(config)

    print(f"Run ID: {result['run_id']}")
    print(f"Dataset Hash: {result['dataset_hash'][:12]}...")
    print(f"Baseline Accuracy: {result['baseline_val_accuracy']:.2%}")
    print(f"Rede Neural Val Accuracy: {result['val_accuracy']:.2%}")
    print(f"Rede Neural Val F1-Macro: {result['val_f1_macro']:.4f}")
    print(f"Modelo Promovido no Gate?: {'SIM' if result['promoted'] else 'NÃO'}")

    if result.get("holdout"):
        print(f"Holdout Accuracy: {result['holdout']['accuracy']:.2%}")
        print(f"Holdout F1-Macro: {result['holdout']['f1_macro']:.4f}")
    print("=" * 60)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Sumário salvo em: {out_path}")


if __name__ == "__main__":
    main()
