"""Testes automatizados para os modelos e pipeline de MLOps."""

from __future__ import annotations

from pathlib import Path

import pytest

from mlops.config import MLOpsConfig
from mlops.pipeline import compute_file_sha256, load_dataset, run_mlops_pipeline
from models.baseline import SentimentBaselineClassifier
from models.neural_net import SentimentNeuralNetClassifier


def test_baseline_classifier_training_and_evaluation():
    texts = [
        "Estou muito feliz e animado com o projeto",
        "Que dia maravilhoso e alegre",
        "Sinto muita tristeza e desânimo hoje",
        "Tudo deu errado e fiquei frustrado",
    ]
    labels = ["alegria", "alegria", "tristeza", "frustracao"]

    baseline = SentimentBaselineClassifier(random_state=42)
    baseline.fit(texts, labels)

    preds = baseline.predict(["Outro texto qualquer"])
    assert len(preds) == 1
    assert preds[0] in labels

    metrics = baseline.evaluate(texts, labels)
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["f1_macro"] <= 1.0
    assert "report" in metrics


def test_neural_net_classifier_lifecycle(tmp_path: Path):
    texts = [
        "Estou radiante de tanta felicidade e alegria",
        "Felicidade pura e comemoração",
        "Me sinto desamparado, muito triste e chorando",
        "Tristeza profunda e solidão",
    ]
    labels = ["alegria", "alegria", "tristeza", "tristeza"]

    model = SentimentNeuralNetClassifier(
        hidden_layer_sizes=(16, 8),
        max_iter=150,
        random_state=42,
    )
    model.fit(texts, labels)

    preds = model.predict(["Alegria e festa"])
    assert len(preds) == 1
    assert preds[0] in labels

    probs = model.predict_proba(["Alegria e festa"])
    assert len(probs[0]) == len(model.classes_)
    assert pytest.approx(sum(probs[0]), abs=1e-3) == 1.0

    eval_results = model.evaluate(texts, labels)
    assert 0.0 <= eval_results["accuracy"] <= 1.0
    assert "confusion_matrix" in eval_results
    assert len(model.loss_curve_) > 0

    # Teste de persistência (save e load)
    model_file = tmp_path / "model.joblib"
    model.save(model_file)
    assert model_file.exists()

    loaded_model = SentimentNeuralNetClassifier.load(model_file)
    loaded_preds = loaded_model.predict(["Alegria e festa"])
    assert loaded_preds == preds


def test_compute_file_sha256(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("conteúdo de teste para hash", encoding="utf-8")
    hash_1 = compute_file_sha256(sample_file)
    assert len(hash_1) == 64

    # Mesmo conteúdo gera mesmo hash
    sample_file_2 = tmp_path / "sample2.txt"
    sample_file_2.write_text("conteúdo de teste para hash", encoding="utf-8")
    assert compute_file_sha256(sample_file_2) == hash_1


def test_load_dataset_dev():
    texts, labels, dataset_hash = load_dataset(split="dev")
    assert len(texts) == 60
    assert len(labels) == 60
    assert len(dataset_hash) == 64
    assert "alegria" in labels
    assert "tristeza" in labels


def test_mlops_pipeline_end_to_end(tmp_path: Path):
    db_file = tmp_path / "test_mlflow.db"
    config = MLOpsConfig(
        split="dev",
        random_seed=42,
        max_iter=30,
        hidden_layer_sizes=[16, 8],
        tracking_uri=f"sqlite:///{db_file.as_posix()}",
        evaluate_holdout=True,
    )

    result = run_mlops_pipeline(config)

    assert result["status"] == "ok"
    assert result["run_id"] != "unknown"
    assert len(result["dataset_hash"]) == 64
    assert 0.0 <= result["baseline_val_accuracy"] <= 1.0
    assert 0.0 <= result["val_accuracy"] <= 1.0
    assert 0.0 <= result["val_f1_macro"] <= 1.0
    assert isinstance(result["promoted"], bool)
    assert result["holdout"] is not None
    assert 0.0 <= result["holdout"]["accuracy"] <= 1.0
