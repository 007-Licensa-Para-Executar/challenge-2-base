"""Deterministic class-aware split of source families, not individual rows.

Ratios are approximate because entire families stay together. Known template
variants and exact duplicates are grouped even when their row IDs differ.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from data.synthetic_generator import infer_template_group


def stratified_split_dataset(
    records: list[dict[str, Any]],
    label_key: str = "macro_tema",
    train_size: float = 0.70,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep source groups and known template/exact-text duplicates disjoint.

    Each source-family group must have one label. At least three independent
    families per observed class are required; no silent unstratified fallback.
    """
    ratios = (train_size, val_size, test_size)
    if min(ratios) <= 0 or abs(sum(ratios) - 1) > 1e-6:
        raise ValueError("Positive split proportions must sum to 1")
    if not records:
        raise ValueError("Dataset is empty")
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(records):
        text = row.get("texto") or row.get("text", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Each record requires non-empty text")
        keys = [("family", infer_template_group(text))]
        explicit = row.get("group_id") or row.get("template_id")
        if explicit:
            keys.append(("source", str(explicit)))
        for key in keys:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    families = defaultdict(list)
    for i, row in enumerate(records):
        families[find(i)].append(row)
    by_class = defaultdict(list)
    for rows in families.values():
        labels = {row[label_key] for row in rows}
        if len(labels) != 1:
            raise ValueError("A source/template family has conflicting labels")
        by_class[next(iter(labels))].append(rows)
    result = [[], [], []]
    rng = random.Random(random_state)
    for label in sorted(by_class, key=str):
        groups = by_class[label]
        if len(groups) < 3:
            raise ValueError(f"Class {label!r} requires at least 3 independent source families")
        rng.shuffle(groups)
        n_val = max(1, round(len(groups) * val_size))
        n_test = max(1, round(len(groups) * test_size))
        if n_val + n_test >= len(groups):
            raise ValueError("Not enough groups for requested proportions")
        ranges = (groups[n_val + n_test :], groups[:n_val], groups[n_val : n_val + n_test])
        for dest, subset in zip(result, ranges, strict=True):
            dest.extend(row for group in subset for row in group)
    return tuple(result)


def save_split_files(train_data, val_data, test_data, output_dir="data/synthetic") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in zip(
        ("train", "val", "holdout"), (train_data, val_data, test_data), strict=True
    ):
        (out / f"{name}_split.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "-i", default="data/synthetic/synthetic_diaries.json")
    parser.add_argument("--output-dir", "-o", default="data/synthetic")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    save_split_files(
        *stratified_split_dataset(records, random_state=args.seed), output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
