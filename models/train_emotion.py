"""Script de treinamento e avaliação da rede neural de emoções em português.

Treina o modelo baseado no dataset GoEmotions PT-BR mapeado para as 7 emoções
de Ekman, calibra os limiares na validação e avalia o desempenho no conjunto de teste.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from models.emotion_net import EKMAN_LABELS, EmotionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def evaluate_test_set(
    pipeline: EmotionPipeline,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    """Calcula métricas multirrótulo e de emoção única no conjunto de teste."""
    texts_test = test_df["text"].tolist()
    Y_test = test_df[EKMAN_LABELS].to_numpy()

    P_test = pipeline.predict_proba(texts_test)
    thresholds = pipeline.thresholds_
    Y_pred = (P_test >= thresholds).astype(int)

    # 1. Métricas multirrótulo
    roc_macro = float(roc_auc_score(Y_test, P_test, average="macro"))
    f1_macro = float(f1_score(Y_test, Y_pred, average="macro", zero_division=0))
    f1_micro = float(f1_score(Y_test, Y_pred, average="micro", zero_division=0))

    per_class: dict[str, dict[str, float]] = {}
    for j, label in enumerate(EKMAN_LABELS):
        p = float(precision_score(Y_test[:, j], Y_pred[:, j], zero_division=0))
        r = float(recall_score(Y_test[:, j], Y_pred[:, j], zero_division=0))
        f = float(f1_score(Y_test[:, j], Y_pred[:, j], zero_division=0))
        per_class[label] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
            "threshold": round(float(thresholds[j]), 4),
            "support": int(Y_test[:, j].sum()),
        }

    # 2. Métricas de Emoção Principal (Single-label)
    primary_predictions = [
        pipeline.predict_primary_emotion(t)["primary_emotion"] for t in texts_test
    ]
    y_true_primary = test_df["primary_emotion"].tolist()

    single_acc = float(accuracy_score(y_true_primary, primary_predictions))
    single_f1_macro = float(f1_score(y_true_primary, primary_predictions, average="macro", zero_division=0))

    report = classification_report(
        y_true_primary, primary_predictions, labels=EKMAN_LABELS, output_dict=True, zero_division=0
    )

    return {
        "multilabel": {
            "roc_auc_macro": round(roc_macro, 4),
            "f1_macro": round(f1_macro, 4),
            "f1_micro": round(f1_micro, 4),
            "per_class": per_class,
        },
        "primary_emotion": {
            "accuracy": round(single_acc, 4),
            "f1_macro": round(single_f1_macro, 4),
            "classification_report": report,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina a rede neural de emoções.")
    parser.add_argument("--data-dir", type=str, default="data/goemotions", help="Pasta com train, validation e test CSVs.")
    parser.add_argument("--output-model", type=str, default="dist/emotion_classifier.joblib", help="Caminho do artefato final.")
    parser.add_argument("--output-metrics", type=str, default="dist/emotion_metrics.json", help="Caminho do relatório de métricas.")
    parser.add_argument("--features", type=int, default=5000, help="Número de features TF-IDF.")
    parser.add_argument("--hidden", type=int, default=64, help="Número de neurônios na camada oculta.")
    parser.add_argument("--epochs", type=int, default=15, help="Número de épocas de treino.")
    parser.add_argument("--lr", type=float, default=0.5, help="Taxa de aprendizado inicial.")
    parser.add_argument("--batch-size", type=int, default=64, help="Tamanho do mini-batch.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    train_df = pd.read_csv(data_dir / "train.csv")
    val_df = pd.read_csv(data_dir / "validation.csv")
    test_df = pd.read_csv(data_dir / "test.csv")

    logger.info(
        "Carregados conjuntos: Treino=%d, Val=%d, Teste=%d",
        len(train_df), len(val_df), len(test_df),
    )

    texts_train = train_df["text"].fillna("").tolist()
    Y_train = train_df[EKMAN_LABELS].to_numpy()

    texts_val = val_df["text"].fillna("").tolist()
    Y_val = val_df[EKMAN_LABELS].to_numpy()

    pipeline = EmotionPipeline(
        n_features=args.features,
        hidden_units=[args.hidden],
        activation="relu",
    )

    pipeline.fit(
        texts_train=texts_train,
        Y_train=Y_train,
        texts_val=texts_val,
        Y_val=Y_val,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
    )

    logger.info("Avaliando modelo no conjunto de teste (%d amostras)...", len(test_df))
    metrics = evaluate_test_set(pipeline, test_df)

    out_model_path = Path(args.output_model)
    pipeline.save(out_model_path)

    out_metrics_path = Path(args.output_metrics)
    out_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    logger.info("Métricas salvas em %s", out_metrics_path)

    print("\n=================== RESULTADOS NO TESTE ===================")
    print(f"ROC-AUC Macro:            {metrics['multilabel']['roc_auc_macro']:.4f}")
    print(f"F1 Macro (multirrótulo):  {metrics['multilabel']['f1_macro']:.4f}")
    print(f"F1 Micro (multirrótulo):  {metrics['multilabel']['f1_micro']:.4f}")
    print(f"Acurácia Emoção Principal:{metrics['primary_emotion']['accuracy']:.4f}")
    print(f"F1 Macro Emoção Principal:{metrics['primary_emotion']['f1_macro']:.4f}")
    print("-----------------------------------------------------------")
    print(f"{'Emoção':<12} | {'Precisão':<8} | {'Recall':<8} | {'F1':<8} | {'Limiar':<8}")
    for label, d in metrics["multilabel"]["per_class"].items():
        print(f"{label:<12} | {d['precision']:<8.4f} | {d['recall']:<8.4f} | {d['f1']:<8.4f} | {d['threshold']:<8.4f}")
    print("===========================================================")


if __name__ == "__main__":
    main()
