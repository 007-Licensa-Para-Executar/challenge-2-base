"""Testes automatizados para os modelos e pipeline de MLOps."""

from __future__ import annotations

from pathlib import Path

import pytest
from mlflow.tracking import MlflowClient

from mlops.config import MLOpsConfig
from mlops.data import compute_file_sha256, load_dataset
from mlops.gate import should_promote
from mlops.pipeline import run_mlops_pipeline
from mlops.store import sqlite_artifact_uri
from mlops.tracker import MLOpsTracker
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

    model_file = tmp_path / "model.joblib"
    model.save(model_file)
    assert model_file.exists()

    loaded_model = SentimentNeuralNetClassifier.load(model_file)
    assert loaded_model.hidden_layer_sizes == (16, 8)
    assert loaded_model.max_iter == 150
    assert loaded_model.predict(["Alegria e festa"]) == preds


def test_compute_file_sha256(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("conteúdo de teste para hash", encoding="utf-8")
    hash_1 = compute_file_sha256(sample_file)
    assert len(hash_1) == 64

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


def test_should_promote_requires_f1_above_baseline_and_threshold():
    assert should_promote(0.40, 0.10, 0.25) is True
    assert should_promote(0.20, 0.10, 0.25) is False
    assert should_promote(0.40, 0.45, 0.25) is False
    assert should_promote(0.25, 0.25, 0.25) is True


def test_sqlite_artifact_uri_uses_sibling_directory(tmp_path: Path):
    db_file = tmp_path / "experimento.db"
    location = sqlite_artifact_uri(f"sqlite:///{db_file.as_posix()}")
    artifact_dir = tmp_path / "experimento-artifacts"
    assert artifact_dir.is_dir()
    assert location == artifact_dir.resolve().as_uri()


def test_holdout_cannot_train_and_evaluate_the_same_split():
    config = MLOpsConfig(split="holdout", evaluate_holdout=True, tracking_uri="sqlite:///unused.db")
    with pytest.raises(ValueError, match="holdout"):
        run_mlops_pipeline(config)


def test_tracker_marks_failed_run(tmp_path: Path):
    db_file = tmp_path / "failed.db"
    tracking_uri = f"sqlite:///{db_file.as_posix()}"
    tracker = MLOpsTracker(tracking_uri=tracking_uri, experiment_name="falha-de-treino")

    with pytest.raises(RuntimeError, match="falha de treino"), tracker:
        tracker.start_run(run_name="boom")
        raise RuntimeError("falha de treino")

    client = MlflowClient(tracking_uri)
    experiment = client.get_experiment_by_name("falha-de-treino")
    assert experiment is not None
    runs = client.search_runs([experiment.experiment_id])
    assert len(runs) == 1
    assert runs[0].info.status == "FAILED"


def _pipeline_config(tmp_path: Path, name: str, **overrides: object) -> MLOpsConfig:
    db_file = tmp_path / f"{name}.db"
    values: dict[str, object] = {
        "split": "dev",
        "random_seed": 42,
        "max_iter": 30,
        "hidden_layer_sizes": [16, 8],
        "tracking_uri": f"sqlite:///{db_file.as_posix()}",
        "experiment_name": name,
        "evaluate_holdout": False,
    }
    values.update(overrides)
    return MLOpsConfig(**values)


def test_mlops_pipeline_end_to_end(tmp_path: Path):
    config = _pipeline_config(tmp_path, "e2e", evaluate_holdout=True)
    result = run_mlops_pipeline(config)

    assert result["status"] == "ok"
    assert result["run_id"] != "unknown"
    assert len(result["dataset_hash"]) == 64
    assert 0.0 <= result["baseline_val_accuracy"] <= 1.0
    assert 0.0 <= result["baseline_val_f1_macro"] <= 1.0
    assert 0.0 <= result["val_accuracy"] <= 1.0
    assert 0.0 <= result["val_f1_macro"] <= 1.0
    assert result["promoted"] is should_promote(
        result["val_f1_macro"],
        result["baseline_val_f1_macro"],
        config.min_f1_macro,
    )
    assert result["holdout"] is not None
    assert 0.0 <= result["holdout"]["accuracy"] <= 1.0
    assert 0.0 <= result["holdout"]["f1_macro"] <= 1.0


def test_rejected_model_is_not_registered_and_artifacts_stay_beside_db(tmp_path: Path):
    config = _pipeline_config(tmp_path, "gate-rejeita", min_f1_macro=0.99, max_iter=15)
    result = run_mlops_pipeline(config)

    assert result["promoted"] is False
    assert result["registered_model"] is None

    client = MlflowClient(config.tracking_uri)
    assert client.search_registered_models() == []
    artifact_dir = tmp_path / "gate-rejeita-artifacts"
    assert list(artifact_dir.rglob("confusion_matrix.png"))
    assert list(artifact_dir.rglob("classification_report.json"))

    experiment = client.get_experiment_by_name(config.experiment_name)
    assert experiment is not None
    run = client.get_run(result["run_id"])
    assert run.data.tags["promoted"] == "false"
    assert "model_promoted" not in run.data.params


def test_promoted_model_is_registered(tmp_path: Path):
    config = _pipeline_config(
        tmp_path,
        "gate-promove",
        min_f1_macro=0.0,
        model_name="mlp-teste-promocao",
    )
    result = run_mlops_pipeline(config)

    assert result["promoted"] is True
    assert result["registered_model"] == "mlp-teste-promocao"
    client = MlflowClient(config.tracking_uri)
    registered = client.search_registered_models(filter_string="name='mlp-teste-promocao'")
    assert len(registered) == 1


def test_same_seed_reproduces_validation_f1(tmp_path: Path):
    first = run_mlops_pipeline(_pipeline_config(tmp_path, "repro-a", max_iter=20))
    second = run_mlops_pipeline(_pipeline_config(tmp_path, "repro-b", max_iter=20))
    assert first["val_f1_macro"] == second["val_f1_macro"]
    assert first["val_accuracy"] == second["val_accuracy"]
    assert first["dataset_hash"] == second["dataset_hash"]
