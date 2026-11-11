"""Orquestração do ciclo de dados, treino, avaliação e tracking."""

from __future__ import annotations

from collections import Counter
from typing import Any

import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from mlops.config import MLOpsConfig
from mlops.data import load_dataset
from mlops.gate import should_promote
from mlops.plots import plot_confusion_matrix
from mlops.tracker import MLOpsTracker
from models.baseline import SentimentBaselineClassifier
from models.neural_net import SentimentNeuralNetClassifier


def split_train_validation(
    texts: list[str],
    labels: list[str],
    test_size: float,
    random_seed: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Divide treino e validação, estratificando quando toda classe tem ao menos dois exemplos."""
    counts = Counter(labels)
    stratify = labels if counts and min(counts.values()) >= 2 else None
    x_train, x_val, y_train, y_val = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=random_seed,
        stratify=stratify,
    )
    return list(x_train), list(x_val), list(y_train), list(y_val)


def run_mlops_pipeline(config: MLOpsConfig) -> dict[str, Any]:
    """Executa o ciclo de MLOps com baseline, rede neural e gate por F1 macro."""
    if config.evaluate_holdout and config.split == "holdout":
        raise ValueError(
            "O split de treino não pode ser o holdout quando a avaliação cega está ativa."
        )

    texts, labels, dataset_hash = load_dataset(split=config.split)
    x_train, x_val, y_train, y_val = split_train_validation(
        texts,
        labels,
        test_size=config.test_size,
        random_seed=config.random_seed,
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
                "model_type": "MLPClassifier",
                "hidden_layer_sizes": config.hidden_layer_sizes,
                "alpha": config.alpha,
                "learning_rate_init": config.learning_rate_init,
                "max_iter": config.max_iter,
                "max_features": config.max_features,
                "min_f1_macro": config.min_f1_macro,
            }
        )

        baseline = SentimentBaselineClassifier(random_state=config.random_seed)
        baseline.fit(x_train, y_train)
        baseline_metrics = baseline.evaluate(x_val, y_val)
        tracker.log_metrics(
            {
                "baseline_val_accuracy": baseline_metrics["accuracy"],
                "baseline_val_f1_macro": baseline_metrics["f1_macro"],
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
        for step, loss_val in enumerate(nn_model.loss_curve_):
            tracker.log_metrics({"training_loss": float(loss_val)}, step=step)

        val_metrics = nn_model.evaluate(x_val, y_val)
        tracker.log_metrics(
            {
                "val_accuracy": val_metrics["accuracy"],
                "val_f1_macro": val_metrics["f1_macro"],
                "val_precision_macro": val_metrics["precision_macro"],
                "val_recall_macro": val_metrics["recall_macro"],
            }
        )

        cm_fig = plot_confusion_matrix(val_metrics["confusion_matrix"], val_metrics["classes"])
        tracker.log_figure(cm_fig, "confusion_matrix.png")
        plt.close(cm_fig)
        tracker.log_dict(val_metrics["report"], "classification_report.json")

        is_promoted = should_promote(
            val_metrics["f1_macro"],
            baseline_metrics["f1_macro"],
            config.min_f1_macro,
        )
        tracker.set_tag("promoted", "true" if is_promoted else "false")
        tracker.log_metrics({"promoted": 1.0 if is_promoted else 0.0})
        registered_model = None
        if is_promoted:
            tracker.log_model(
                nn_model.pipeline,
                registered_model_name=config.model_name,
            )
            registered_model = config.model_name

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
        "baseline_val_f1_macro": baseline_metrics["f1_macro"],
        "val_accuracy": val_metrics["accuracy"],
        "val_f1_macro": val_metrics["f1_macro"],
        "promoted": is_promoted,
        "registered_model": registered_model,
        "holdout": holdout_metrics,
    }
