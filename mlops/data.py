"""Leitura dos relatos sintéticos e hash de linhagem do arquivo."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "synthetic"


def compute_file_sha256(filepath: Path) -> str:
    """Calcula o digest SHA-256 do arquivo para rastreamento de linhagem."""
    hasher = hashlib.sha256()
    with filepath.open("rb") as file:
        while chunk := file.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_dataset(
    split: str = "dev",
    directory: Path = DATA_DIR,
) -> tuple[list[str], list[str], str]:
    """Carrega textos, rótulos de sentimento e o hash do JSONL do split."""
    file_path = directory / f"{split}.jsonl"
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {file_path}")

    dataset_hash = compute_file_sha256(file_path)
    texts: list[str] = []
    labels: list[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        texts.append(item["text"])
        labels.append(item["expected"]["sentimento"])
    return texts, labels, dataset_hash
