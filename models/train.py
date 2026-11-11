"""Compare Torch, from-scratch NumPy and majority baseline on disjoint source families.

Synthetic reference labels are unreviewed. Results are preliminary agreement,
not clinical validation or evidence of performance on real diaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import torch
from sklearn.dummy import DummyClassifier
from sklearn.metrics import classification_report, f1_score
from torch import nn

from data.split import stratified_split_dataset
from data.synthetic_generator import infer_template_group
from mlops.tracker import MLFlowTracker
from models.embedder import PORTUGUESE_STOPWORDS, ClinicalTextEmbedder
from models.numpy_mlp import NumpyClinicalMLP
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP, compute_ece

logger = logging.getLogger(__name__)
THEME_TO_IDX = {theme: idx for idx, theme in enumerate(THEME_CLASSES)}
IDX_TO_THEME = dict(enumerate(THEME_CLASSES))


def load_dataset_rows(data_path: str | Path) -> list[dict[str, Any]]:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}; generate it explicitly first")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Dataset must be a nonempty list")
    result = []
    for i, row in enumerate(rows):
        text = row.get("texto") or row.get("text", "")
        label = row.get("macro_tema") or row.get("expected", {}).get("tema")
        if not isinstance(text, str) or not text.strip() or label not in THEME_TO_IDX:
            raise ValueError(f"Invalid text or unknown label at row {i}")
        result.append({**row, "texto": text, "macro_tema": label})
    return result


def load_dataset_records(data_path: str | Path) -> tuple[list[str], list[int]]:
    """Compatibility helper; the CLI also preserves groups and IDs via load_dataset_rows."""
    rows = load_dataset_rows(data_path)
    return [row["texto"] for row in rows], [THEME_TO_IDX[row["macro_tema"]] for row in rows]


def _metrics(y_true, predictions) -> dict[str, Any]:
    return {
        "accuracy": float(np.mean(np.asarray(y_true) == predictions)),
        "macro_f1": float(
            f1_score(
                y_true,
                predictions,
                labels=list(range(len(THEME_CLASSES))),
                average="macro",
                zero_division=0,
            )
        ),
        "classification_report": classification_report(
            y_true,
            predictions,
            labels=list(range(len(THEME_CLASSES))),
            target_names=THEME_CLASSES,
            output_dict=True,
            zero_division=0,
        ),
    }


def _policy(probs: np.ndarray, threshold: float):
    preds = probs.argmax(axis=1)
    abstained = probs.max(axis=1) < threshold
    preds[abstained] = len(THEME_CLASSES) - 1
    return preds, abstained


def _evaluate(probs, labels, threshold):
    predictions, abstained = _policy(probs, threshold)
    return {
        "threshold_policy": {
            **_metrics(labels, predictions),
            "abstention_count": int(abstained.sum()),
            "determined_coverage": float(1 - abstained.mean()),
        },
        "argmax_only": _metrics(labels, probs.argmax(axis=1)),
    }


def train_theme_classifier(
    texts: list[str],
    labels: list[int],
    epochs: int = 35,
    batch_size: int = 32,
    lr: float = 0.005,
    weight_decay: float = 1e-3,
    random_state: int = 42,
    experiment_name: str = "Theme_MLP_Preliminary",
    dist_dir: str | Path = "dist",
    tracking_uri: str | None = None,
    groups: list[str] | None = None,
    record_ids: list[str] | None = None,
    threshold: float = 0.50,
    numpy_lr: float = 0.05,
    max_features: int = 3000,
    init_strategy: str = "svd",
) -> dict[str, Any]:
    """Select both neural checkpoints on validation; inspect test only afterwards.

    Legacy calls infer known template families and exact duplicates. External
    paraphrases require explicit source-family groups from the caller.
    """
    n = len(texts)
    if n != len(labels) or not n or epochs < 1 or batch_size < 1:
        raise ValueError("Nonempty aligned data and positive epochs/batch_size required")
    if groups is not None and len(groups) != n or record_ids is not None and len(record_ids) != n:
        raise ValueError("Group and record IDs must align with texts")
    if not 0 <= threshold <= 1 or lr <= 0 or numpy_lr <= 0:
        raise ValueError("Invalid threshold or learning rate")
    if any(label not in IDX_TO_THEME for label in labels):
        raise ValueError("Unknown class index")
    rows = [
        {
            "id": record_ids[i] if record_ids else f"row_{i}",
            "texto": text,
            "macro_tema": IDX_TO_THEME[labels[i]],
            "group_id": groups[i] if groups else infer_template_group(text),
            "row_index": i,
        }
        for i, text in enumerate(texts)
    ]
    if len({row["id"] for row in rows}) != n:
        raise ValueError("Record IDs must be unique")
    splits = stratified_split_dataset(rows, random_state=random_state)
    indexes = [[row["row_index"] for row in split] for split in splits]
    y_train, y_val, y_test = [np.asarray(labels)[idx] for idx in indexes]
    vectorizer = ClinicalTextEmbedder(
        embedding_dim=128,
        max_features=max_features,
        stop_words=PORTUGUESE_STOPWORDS,
        random_state=random_state,
        init_strategy=init_strategy,
        use_idf_weighting=True,
    )
    vectorizer.fit([texts[i] for i in indexes[0]])
    x_train = vectorizer.transform([texts[i] for i in indexes[0]], normalize=True)
    x_val, x_test = [
        vectorizer.transform([texts[i] for i in idx], normalize=True) for idx in indexes[1:]
    ]

    x_train_t = torch.tensor(x_train, dtype=torch.float32)
    x_val_t = torch.tensor(x_val, dtype=torch.float32)
    x_test_t = torch.tensor(x_test, dtype=torch.float32)

    torch.manual_seed(random_state)
    model = ClinicalThemeMLP(
        input_dim=vectorizer.embedding_dim,
        hidden_dim1=128,
        hidden_dim2=64,
        num_classes=len(THEME_CLASSES),
        vocab_size=None,
    )

    numpy_model = NumpyClinicalMLP(
        in_dim=x_train.shape[1],
        h1=64,
        out_dim=len(THEME_CLASSES),
        lr=numpy_lr,
        random_state=random_state,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.CrossEntropyLoss()
    target_t = torch.tensor(y_train, dtype=torch.long)
    val_target_t = torch.tensor(y_val, dtype=torch.long)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(x_train_t, target_t),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(random_state),
    )
    dist = Path(dist_dir)
    dist.mkdir(parents=True, exist_ok=True)
    tracker = MLFlowTracker(experiment_name=experiment_name, tracking_uri=tracking_uri)
    baseline = DummyClassifier(strategy="most_frequent").fit(x_train, y_train)
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    manifest = {
        "dataset_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "code_commit": commit,
        "source_sha256": {
            str(path.relative_to(Path(__file__).resolve().parent.parent)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (
                Path(__file__).resolve(),
                Path(__file__).resolve().with_name("embedder.py"),
                Path(__file__).resolve().with_name("numpy_mlp.py"),
                Path(__file__).resolve().with_name("torch_mlp.py"),
                Path(__file__).resolve().parent.parent / "data" / "split.py",
                Path(__file__).resolve().parent.parent / "data" / "synthetic_generator.py",
            )
        },
        "seed": random_state,
        "classes": THEME_CLASSES,
        "split_policy": "class-aware source/template groups; approximate 70/15/15",
        "reference_status": "experimental reference labels; held-out split is not independent annotation or clinical validation",
        "grouping_limit": "known templates and exact duplicates; external paraphrases need groups",
        "threshold": threshold,
        "numpy_lr": numpy_lr,
        "splits": {
            name: [{k: row[k] for k in ("id", "group_id", "macro_tema")} for row in split]
            for name, split in zip(("train", "validation", "test"), splits, strict=True)
        },
        "vectorizer": vectorizer.get_params(),
    }
    with mlflow.start_run(run_name="Grouped_Comparison") as run:
        tracker.log_params(
            {
                "seed": random_state,
                "dataset_sha256": manifest["dataset_sha256"],
                "input_dim": x_train.shape[1],
                "hidden_layers": [128, 64],
                "numpy_hidden_units": 64,
                "threshold": threshold,
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": lr,
                "numpy_lr": numpy_lr,
                "weight_decay": weight_decay,
                "train_samples": len(y_train),
                "val_samples": len(y_val),
                "test_samples": len(y_test),
            }
        )
        best_torch, best_numpy = None, None
        best_scores = [-1.0, -1.0]
        best_epochs = [0, 0]
        history = []
        for epoch in range(1, epochs + 1):
            model.train()
            train_loss = 0.0
            for bx, by in loader:
                optimizer.zero_grad()
                loss = criterion(model(bx), by)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                train_loss += loss.item() * len(bx)
            numpy_loss = numpy_model.fit(x_train, y_train, epochs=1, batch_size=batch_size)[0]
            model.eval()
            with torch.no_grad():
                logits = model(x_val_t)
                val_loss = criterion(logits, val_target_t).item()
                torch_probs = torch.softmax(logits, dim=1).numpy()
            numpy_probs = numpy_model.predict_proba(x_val)
            numpy_val_loss = numpy_model.compute_loss(
                numpy_probs, np.eye(len(THEME_CLASSES))[y_val]
            )
            scores = [
                _metrics(y_val, p.argmax(axis=1))["macro_f1"]
                for p in (torch_probs, numpy_probs)
            ]
            metrics = {
                "train_loss": train_loss / len(y_train),
                "val_loss": val_loss,
                "val_macro_f1": scores[0],
                "numpy_train_loss": numpy_loss,
                "numpy_val_loss": numpy_val_loss,
                "numpy_val_macro_f1": scores[1],
            }
            tracker.log_metrics(metrics, step=epoch)
            history.append({"epoch": epoch, **metrics})
            if scores[0] > best_scores[0]:
                best_scores[0], best_epochs[0] = scores[0], epoch
                best_torch = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            if scores[1] > best_scores[1]:
                best_scores[1], best_epochs[1] = scores[1], epoch
                best_numpy = {k: getattr(numpy_model, k).copy() for k in ("W1", "b1", "W2", "b2")}
        model.load_state_dict(best_torch)
        for key, value in best_numpy.items():
            setattr(numpy_model, key, value)

        # Calibração de Probabilidades via Temperature Scaling (Guo et al., 2017)
        optimal_temp = 1.0
        try:
            with torch.no_grad():
                val_raw_logits = model(x_val_t)
            optimal_temp = model.calibrate_temperature(val_raw_logits, val_target_t)
        except (RuntimeError, ValueError):
            optimal_temp = 1.0

        with torch.no_grad():
            test_logits = model(x_test_t)
            uncalibrated_test_probs = torch.softmax(test_logits, dim=1).numpy()
            torch_probs = model.predict_proba(x_test_t, apply_temperature=True).numpy()
            test_loss = criterion(test_logits, torch.tensor(y_test, dtype=torch.long)).item()

        ece_uncalibrated = compute_ece(uncalibrated_test_probs, y_test)
        ece_calibrated = compute_ece(torch_probs, y_test)

        comparison = {
            "reference_status": manifest["reference_status"],
            "torch": _evaluate(torch_probs, y_test, threshold),
            "numpy": _evaluate(numpy_model.predict_proba(x_test), y_test, threshold),
            "majority_baseline": _metrics(y_test, baseline.predict(x_test)),
            "calibration": {
                "temperature": optimal_temp,
                "ece_before": ece_uncalibrated,
                "ece_after": ece_calibrated,
            },
        }
        final = comparison["torch"]["threshold_policy"]
        manifest["calibration"] = comparison["calibration"]
        manifest["best_checkpoint_epochs"] = dict(zip(("torch", "numpy"), best_epochs, strict=True))

        tracker.log_metrics(
            {
                "final_test_macro_f1": final["macro_f1"],
                "final_test_acc": final["accuracy"],
                "final_test_loss": test_loss,
                "torch_test_argmax_macro_f1": comparison["torch"]["argmax_only"]["macro_f1"],
                "numpy_test_macro_f1": comparison["numpy"]["threshold_policy"]["macro_f1"],
                "majority_test_macro_f1": comparison["majority_baseline"]["macro_f1"],
                "temperature": optimal_temp,
                "ece_uncalibrated": ece_uncalibrated,
                "ece_calibrated": ece_calibrated,
            }
        )
        tracker.log_confusion_matrix(
            y_test, _policy(torch_probs, threshold)[0], THEME_CLASSES, dist
        )
        tracker.log_metrics(
            {"best_val_macro_f1": best_scores[0], "best_numpy_val_macro_f1": best_scores[1]}
        )
        documents = {
            "split_manifest.json": manifest,
            "comparison_report.json": comparison,
            "learning_curves.json": history,
            "classification_report.json": final["classification_report"],
            "theme_classes.json": THEME_CLASSES,
        }
        for name, obj in documents.items():
            path = dist / name
            path.write_text(
                json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )
            tracker.log_artifact(path)
        torch.save(model.state_dict(), dist / "best_theme_mlp.pt")
        joblib.dump(vectorizer, dist / "theme_embedder.joblib")
        joblib.dump(vectorizer, dist / "tfidf_vectorizer.joblib")
        np.savez(dist / "best_numpy_mlp.npz", **best_numpy)
        for name in (
            "best_theme_mlp.pt",
            "theme_embedder.joblib",
            "tfidf_vectorizer.joblib",
            "best_numpy_mlp.npz",
        ):
            tracker.log_artifact(dist / name)
        return {
            "run_id": run.info.run_id,
            "final_test_macro_f1": final["macro_f1"],
            "final_test_acc": final["accuracy"],
            "final_test_loss": test_loss,
            "torch_argmax_macro_f1": comparison["torch"]["argmax_only"]["macro_f1"],
            "temperature": optimal_temp,
            "ece_calibrated": ece_calibrated,
            "model_path": str(dist / "best_theme_mlp.pt"),
            "vectorizer_path": str(dist / "theme_embedder.joblib"),
            "comparison": comparison,
            "manifest_path": str(dist / "split_manifest.json"),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_data_path = (
        "data/real_diaries.json"
        if Path("data/real_diaries.json").exists()
        else "data/synthetic/synthetic_diaries.json"
    )
    parser.add_argument("--data-path", default=default_data_path)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.005)
    parser.add_argument("--numpy-lr", type=float, default=0.05)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--max-features", type=int, default=3000)
    parser.add_argument("--init-strategy", default="svd", choices=["gaussian", "svd"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--experiment-name", default="Theme_MLP_Preliminary")
    args = parser.parse_args()
    rows = load_dataset_rows(args.data_path)
    result = train_theme_classifier(
        [r["texto"] for r in rows],
        [THEME_TO_IDX[r["macro_tema"]] for r in rows],
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        numpy_lr=args.numpy_lr,
        threshold=args.threshold,
        max_features=args.max_features,
        init_strategy=args.init_strategy,
        random_state=args.seed,
        experiment_name=args.experiment_name,
        dist_dir=args.dist_dir,
        groups=[r.get("group_id") or infer_template_group(r["texto"]) for r in rows],
        record_ids=[r.get("id", f"row_{i}") for i, r in enumerate(rows)],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
