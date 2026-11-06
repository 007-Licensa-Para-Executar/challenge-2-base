"""Divisão determinística estratificada de dataset sintético em Treino (70%),

Validação (15%) e Holdout Cego (15%).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


def stratified_split_dataset(
    records: list[dict[str, Any]],
    label_key: str = "macro_tema",
    train_size: float = 0.70,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Divide registros em treino, validação e teste de forma estratificada."""
    total = train_size + val_size + test_size
    if abs(total - 1.0) > 1e-4:
        raise ValueError(f"Soma das proporções deve ser 1.0, obteve {total:.4f}")

    labels = [r[label_key] for r in records]

    # Primeira divisão: Treino vs Resto (Validação + Teste)
    temp_size = val_size + test_size
    train_data, temp_data, _, temp_labels = train_test_split(
        records,
        labels,
        test_size=temp_size,
        stratify=labels,
        random_state=random_state,
    )

    # Segunda divisão: Validação vs Teste (50% do Resto se val_size == test_size)
    relative_test_size = test_size / temp_size
    val_data, test_data = train_test_split(
        temp_data,
        test_size=relative_test_size,
        stratify=temp_labels,
        random_state=random_state,
    )

    return train_data, val_data, test_data


def save_split_files(
    train_data: list[dict[str, Any]],
    val_data: list[dict[str, Any]],
    test_data: list[dict[str, Any]],
    output_dir: str | Path = "data/synthetic",
) -> None:
    """Salva as divisões em arquivos JSON separados."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "train_split.json", "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)

    with open(out_dir / "val_split.json", "w", encoding="utf-8") as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)

    with open(out_dir / "holdout_split.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    logger.info(
        "Divisão concluída! Treino: %d, Validação: %d, Holdout: %d salvos em %s",
        len(train_data),
        len(val_data),
        len(test_data),
        out_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Script de divisão estratificada do dataset")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="data/synthetic/synthetic_diaries.json",
        help="Caminho do dataset sintético de entrada",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="data/synthetic",
        help="Diretório para salvar as divisões",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente aleatória para reprodutibilidade",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    train, val, test = stratified_split_dataset(records, random_state=args.seed)
    save_split_files(train, val, test, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
