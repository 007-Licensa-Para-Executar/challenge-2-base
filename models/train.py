"""Pipeline de treinamento da Rede Neural MLP para classificação dos 8 macrotemas clínicos.

Inclui divisão estratificada (70/15/15), vetorização TF-IDF, rastreamento
de métricas e artefatos no MLflow e avaliação no conjunto de teste holdout cego.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from torch import nn

from mlops.tracker import MLFlowTracker
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP

logger = logging.getLogger(__name__)

THEME_TO_IDX: dict[str, int] = {theme: idx for idx, theme in enumerate(THEME_CLASSES)}
IDX_TO_THEME: dict[int, str] = {idx: theme for idx, theme in enumerate(THEME_CLASSES)}


def load_dataset_records(data_path: str | Path) -> tuple[list[str], list[int]]:
    """Carrega relatos e converte os macrotemas em índices de classe."""
    path = Path(data_path)
    if not path.exists():
        # Gera dataset automaticamente se não existir
        from data.synthetic_generator import generate_synthetic_dataset

        logger.info("Dataset não encontrado em %s. Gerando dataset sintético inicial...", path)
        generate_synthetic_dataset(output_path=str(path), samples_per_theme=40)

    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    texts: list[str] = []
    labels: list[int] = []

    fallback_idx = THEME_TO_IDX["outros_indeterminado"]

    for item in records:
        text = item.get("texto") or item.get("text", "")
        theme = item.get("macro_tema") or item.get("expected", {}).get(
            "tema", "outros_indeterminado"
        )
        label_idx = THEME_TO_IDX.get(theme, fallback_idx)

        if text.strip():
            texts.append(text)
            labels.append(label_idx)

    return texts, labels


def train_theme_classifier(
    texts: list[str],
    labels: list[int],
    epochs: int = 40,
    batch_size: int = 32,
    lr: float = 0.001,
    weight_decay: float = 1e-4,
    random_state: int = 42,
    experiment_name: str = "Clinical_Theme_MLP",
    dist_dir: str | Path = "dist",
    tracking_uri: str | None = None,
) -> dict[str, Any]:
    """Executa o ciclo completo de treinamento, validação e teste com rastreamento no MLflow."""
    torch.manual_seed(random_state)
    np.random.seed(random_state)

    dist_path = Path(dist_dir)
    dist_path.mkdir(parents=True, exist_ok=True)

    tracker = MLFlowTracker(experiment_name=experiment_name, tracking_uri=tracking_uri)

    # 1. Divisão Estratificada: 70% Treino, 15% Validação, 15% Holdout Cego
    X_train_raw, X_temp, y_train_raw, y_temp = train_test_split(
        texts,
        labels,
        test_size=0.30,
        random_state=random_state,
        stratify=labels,
    )
    try:
        X_val_raw, X_test_raw, y_val_raw, y_test_raw = train_test_split(
            X_temp,
            y_temp,
            test_size=0.50,
            random_state=random_state,
            stratify=y_temp,
        )
    except ValueError:
        # Fallback sem estratificação caso classes raras tenham < 2 membros no conjunto temporário
        X_val_raw, X_test_raw, y_val_raw, y_test_raw = train_test_split(
            X_temp,
            y_temp,
            test_size=0.50,
            random_state=random_state,
        )

    logger.info(
        "Divisão dos dados: Treino=%d, Validação=%d, Teste Holdout=%d",
        len(X_train_raw),
        len(X_val_raw),
        len(X_test_raw),
    )

    # 2. Vetorização TF-IDF
    vectorizer = TfidfVectorizer(max_features=1024, ngram_range=(1, 2), lowercase=True)
    X_train = vectorizer.fit_transform(X_train_raw).toarray()
    X_val = vectorizer.transform(X_val_raw).toarray()
    X_test = vectorizer.transform(X_test_raw).toarray()

    # Conversão para tensores PyTorch
    t_X_train = torch.tensor(X_train, dtype=torch.float32)
    t_y_train = torch.tensor(y_train_raw, dtype=torch.long)
    t_X_val = torch.tensor(X_val, dtype=torch.float32)
    t_y_val = torch.tensor(y_val_raw, dtype=torch.long)
    t_X_test = torch.tensor(X_test, dtype=torch.float32)
    t_y_test = torch.tensor(y_test_raw, dtype=torch.long)

    # 3. Inicialização da Rede Neural e Otimizador AdamW
    input_dim = t_X_train.shape[1]
    num_classes = len(THEME_CLASSES)
    model = ClinicalThemeMLP(input_dim=input_dim, num_classes=num_classes)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.CrossEntropyLoss()

    dataset = torch.utils.data.TensorDataset(t_X_train, t_y_train)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    with mlflow.start_run(run_name="MLP_Training_Run") as run:
        # Registro de hiperparâmetros
        tracker.log_params(
            {
                "model_architecture": "ClinicalThemeMLP",
                "input_dim": input_dim,
                "hidden_layers": [128, 64],
                "num_classes": num_classes,
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": lr,
                "weight_decay": weight_decay,
                "train_samples": len(X_train_raw),
                "val_samples": len(X_val_raw),
                "test_samples": len(X_test_raw),
            }
        )

        best_val_f1 = -1.0
        best_model_weights = None

        # 4. Loop de Treinamento e Validação
        for epoch in range(1, epochs + 1):
            model.train()
            epoch_loss = 0.0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * batch_x.size(0)

            epoch_loss /= len(dataset)

            # Validação
            model.eval()
            with torch.no_grad():
                val_logits = model(t_X_val)
                val_loss = criterion(val_logits, t_y_val).item()
                val_preds = torch.argmax(val_logits, dim=-1).cpu().numpy()
                val_f1 = float(f1_score(y_val_raw, val_preds, average="macro", zero_division=0))

            tracker.log_metric("train_loss", epoch_loss, step=epoch)
            tracker.log_metric("val_loss", val_loss, step=epoch)
            tracker.log_metric("val_macro_f1", val_f1, step=epoch)

            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                best_model_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        # 5. Avaliação Final no Conjunto de Teste Holdout Cego
        if best_model_weights is not None:
            model.load_state_dict(best_model_weights)
        model.eval()

        with torch.no_grad():
            test_logits = model(t_X_test)
            test_loss = criterion(test_logits, t_y_test).item()
            test_preds = torch.argmax(test_logits, dim=-1).cpu().numpy()
            test_f1 = float(f1_score(y_test_raw, test_preds, average="macro", zero_division=0))
            test_acc = float((test_preds == np.array(y_test_raw)).mean())

        tracker.log_metrics(
            {
                "final_test_loss": test_loss,
                "final_test_macro_f1": test_f1,
                "final_test_acc": test_acc,
            }
        )

        report_dict = classification_report(
            y_test_raw,
            test_preds,
            target_names=[THEME_CLASSES[i] for i in sorted(set(y_test_raw + list(test_preds)))],
            output_dict=True,
            zero_division=0,
        )

        # 6. Registro de Matriz de Confusão e Relatórios
        _cm_json, _cm_png = tracker.log_confusion_matrix(
            y_true=y_test_raw,
            y_pred=test_preds,
            labels=THEME_CLASSES,
            output_dir=dist_path,
        )

        report_path = dist_path / "classification_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        tracker.log_artifact(report_path)

        classes_path = dist_path / "theme_classes.json"
        with open(classes_path, "w", encoding="utf-8") as f:
            json.dump(THEME_CLASSES, f, ensure_ascii=False, indent=2)
        tracker.log_artifact(classes_path)

        # 7. Salvamento e Registro dos Pesos e Vetorizador
        model_weights_path = dist_path / "best_theme_mlp.pt"
        vectorizer_path = dist_path / "tfidf_vectorizer.joblib"

        torch.save(model.state_dict(), model_weights_path)
        joblib.dump(vectorizer, vectorizer_path)

        tracker.log_artifact(model_weights_path)
        tracker.log_artifact(vectorizer_path)

        logger.info(
            "Treinamento Concluído! Test Macro-F1: %.4f | Test Acc: %.4f | Run ID: %s",
            test_f1,
            test_acc,
            run.info.run_id,
        )

        return {
            "run_id": run.info.run_id,
            "final_test_macro_f1": test_f1,
            "final_test_acc": test_acc,
            "final_test_loss": test_loss,
            "model_path": str(model_weights_path),
            "vectorizer_path": str(vectorizer_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline de Treino do Classificador MLP de Macrotemas"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/synthetic/synthetic_diaries.json",
        help="Caminho do arquivo de dados sintéticos",
    )
    parser.add_argument("--epochs", type=int, default=40, help="Número de épocas de treinamento")
    parser.add_argument("--batch-size", type=int, default=32, help="Tamanho do lote")
    parser.add_argument("--lr", type=float, default=0.001, help="Taxa de aprendizado")
    parser.add_argument("--seed", type=int, default=42, help="Semente pseudoaleatória")
    parser.add_argument(
        "--dist-dir", type=str, default="dist", help="Diretório de saída de artefatos"
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default="Clinical_Theme_MLP",
        help="Nome do experimento no MLflow",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    texts, labels = load_dataset_records(args.data_path)
    train_theme_classifier(
        texts=texts,
        labels=labels,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        random_state=args.seed,
        experiment_name=args.experiment_name,
        dist_dir=args.dist_dir,
    )


if __name__ == "__main__":
    main()
