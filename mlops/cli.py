"""Interface de linha de comando do pipeline de MLOps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mlops.config import MLOpsConfig
from mlops.pipeline import run_mlops_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Monta os argumentos do comando bem-estar-mlops."""
    parser = argparse.ArgumentParser(
        description="Executa o pipeline reproduzível de MLOps do Diário Emocional."
    )
    parser.add_argument("--split", default="dev", choices=["dev"], help="Split base de treino")
    parser.add_argument(
        "--holdout",
        action="store_true",
        help="Executar avaliação cega no conjunto holdout",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Semente aleatória para reprodutibilidade"
    )
    parser.add_argument(
        "--max-iter", type=int, default=200, help="Iterações máximas de treino do MLP"
    )
    parser.add_argument(
        "--min-f1",
        type=float,
        default=0.25,
        help="F1 macro mínimo na validação para promover o modelo",
    )
    parser.add_argument(
        "--tracking-uri",
        default="sqlite:///mlflow.db",
        help="URI de rastreamento do MLflow (ex: sqlite:///mlflow.db)",
    )
    parser.add_argument("--output", type=str, help="Caminho para salvar o sumário JSON do pipeline")
    return parser


def main() -> None:
    """Executa o pipeline e imprime o sumário da rodada."""
    args = build_parser().parse_args()
    config = MLOpsConfig(
        split=args.split,
        random_seed=args.seed,
        max_iter=args.max_iter,
        min_f1_macro=args.min_f1,
        tracking_uri=args.tracking_uri,
        evaluate_holdout=args.holdout,
    )

    print("=" * 60)
    print(" INICIANDO PIPELINE DE MLOPS - BEM-ESTAR")
    print(f" Experimento: {config.experiment_name}")
    print(f" Tracking URI: {config.tracking_uri}")
    print(f" Semente: {config.random_seed} | Max Iter: {config.max_iter}")
    print(f" F1 macro mínimo: {config.min_f1_macro:.2f}")
    print("=" * 60)

    result = run_mlops_pipeline(config)

    print(f"Run ID: {result['run_id']}")
    print(f"Dataset Hash: {result['dataset_hash'][:12]}...")
    print(f"Baseline Accuracy: {result['baseline_val_accuracy']:.2%}")
    print(f"Baseline F1-Macro: {result['baseline_val_f1_macro']:.4f}")
    print(f"Rede Neural Val Accuracy: {result['val_accuracy']:.2%}")
    print(f"Rede Neural Val F1-Macro: {result['val_f1_macro']:.4f}")
    if result["promoted"]:
        print(f"Modelo promovido no registry: {result['registered_model']}")
    else:
        print("Modelo promovido no registry: não")

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
