"""Testes unitários para o pipeline de treinamento MLOps e rastreamento."""

import json

from mlops.tracker import MLFlowTracker
from models.torch_mlp import THEME_CLASSES
from models.train import (
    IDX_TO_THEME,
    THEME_TO_IDX,
    load_dataset_records,
    train_theme_classifier,
)


def test_theme_mappings():
    """Valida mapeamentos biunívocos entre índices inteiros e nomes de classes."""
    assert len(THEME_TO_IDX) == len(THEME_CLASSES)
    assert len(IDX_TO_THEME) == len(THEME_CLASSES)
    for idx, name in enumerate(THEME_CLASSES):
        assert THEME_TO_IDX[name] == idx
        assert IDX_TO_THEME[idx] == name


def test_load_dataset_records_from_file(tmp_path):
    """Valida leitura e conversão de registros de dataset JSON."""
    data_file = tmp_path / "sample_data.json"
    sample = [
        {"texto": "Meu trabalho está cansativo.", "macro_tema": "trabalho"},
        {"texto": "Minha mãe está doente.", "macro_tema": "familia"},
        {"texto": "Apenas um dia neutro.", "macro_tema": "outros_indeterminado"},
    ]
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(sample, f)

    texts, labels = load_dataset_records(data_file)
    assert len(texts) == 3
    assert len(labels) == 3
    assert labels[0] == THEME_TO_IDX["trabalho"]
    assert labels[1] == THEME_TO_IDX["familia"]
    assert labels[2] == THEME_TO_IDX["outros_indeterminado"]


def test_mlflow_tracker_operations(tmp_path):
    """Valida operações básicas do MLFlowTracker."""
    db_file = tmp_path / "test_mlflow.db"
    tracker = MLFlowTracker(
        experiment_name="Test_Tracker_Experiment",
        tracking_uri=f"sqlite:///{db_file}",
    )

    dummy_artifact = tmp_path / "test_artifact.txt"
    dummy_artifact.write_text("conteúdo de teste", encoding="utf-8")

    run_id = tracker.log_training_session(
        params={"test_param": 42},
        metrics={"test_metric": 0.95},
        artifacts_paths=[dummy_artifact],
        run_name="Unit_Test_Run",
    )
    assert isinstance(run_id, str)
    assert len(run_id) > 0


def test_train_theme_classifier_e2e(tmp_path):
    """Executa o pipeline de ponta a ponta com dataset reduzido e verifica os artefatos gerados."""
    # Gera dataset mínimo: 9 classes x 10 amostras = 90 amostras
    texts = []
    labels = []
    for cls_idx, cls_name in enumerate(THEME_CLASSES):
        for i in range(10):
            texts.append(f"Relato sintético sobre {cls_name} exemplo {i} com vocabulário clínico.")
            labels.append(cls_idx)

    dist_dir = tmp_path / "dist_test"
    db_file = tmp_path / "test_e2e.db"

    result = train_theme_classifier(
        texts=texts,
        labels=labels,
        epochs=2,
        batch_size=8,
        lr=0.005,
        random_state=42,
        experiment_name="Test_Theme_Classifier_E2E",
        dist_dir=dist_dir,
        tracking_uri=f"sqlite:///{db_file}",
    )

    assert "run_id" in result
    assert "final_test_macro_f1" in result
    assert "final_test_acc" in result
    assert 0.0 <= result["final_test_acc"] <= 1.0

    # Verifica que todos os artefatos esperados foram gerados no disco
    assert (dist_dir / "best_theme_mlp.pt").exists()
    assert (dist_dir / "tfidf_vectorizer.joblib").exists()
    assert (dist_dir / "confusion_matrix.json").exists()
    assert (dist_dir / "classification_report.json").exists()
    assert (dist_dir / "theme_classes.json").exists()
