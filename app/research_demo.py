"""Treino demonstrativo explícito, local e exclusivamente sintético."""

import argparse
import json

from app.processes import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["train"])
    parser.parse_args()
    import torch

    from data.synthetic_generator import infer_template_group
    from models.train import THEME_TO_IDX, load_dataset_rows, train_theme_classifier

    torch.set_num_threads(2)
    rows = load_dataset_rows(ROOT / "data/synthetic/synthetic_diaries.json")
    result = train_theme_classifier(
        [r["texto"] for r in rows], [THEME_TO_IDX[r["macro_tema"]] for r in rows],
        epochs=35, random_state=42, init_strategy="gaussian",
        dist_dir=ROOT / "dist/rag-demo",
        tracking_uri="sqlite:///" + (ROOT / "dist/rag-demo/mlflow.db").as_posix(),
        experiment_name="RAG_Synthetic_Demo",
        groups=[r.get("group_id") or infer_template_group(r["texto"]) for r in rows],
        record_ids=[r.get("id", f"row_{i}") for i, r in enumerate(rows)],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
