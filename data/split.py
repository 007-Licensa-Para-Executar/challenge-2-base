"""Split determinístico por famílias de origem (não por linha), estratificado por classe.

As proporções são aproximadas porque famílias inteiras ficam juntas. Variantes conhecidas
de template e textos exatamente repetidos são agrupados mesmo quando os IDs diferem.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from data.synthetic_generator import infer_template_group
from data.taxonomy import CLASSES

MIN_FAMILIES_PER_CLASS = 3
SPLIT_NAMES: tuple[str, str, str] = ("train", "val", "holdout")


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        self.parent[self.find(a)] = self.find(b)


def _row_keys(row: dict[str, Any]) -> set[tuple[str, str]]:
    """Chaves que identificam a família de origem de um registro."""
    text = row.get("texto") or row.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Registro {row.get('id', '?')} sem texto não vazio")
    keys = {("family", infer_template_group(text))}
    explicit = row.get("group_id") or row.get("template_id")
    if explicit:
        keys.add(("source", str(explicit)))
    return keys


def _build_families(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Une registros que compartilham qualquer chave de família (união-busca)."""
    uf = _UnionFind(len(records))
    owner: dict[tuple[str, str], int] = {}
    for i, row in enumerate(records):
        for key in _row_keys(row):
            if key in owner:
                uf.union(i, owner[key])
            else:
                owner[key] = i
    families: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for i, row in enumerate(records):
        families[uf.find(i)].append(row)
    return list(families.values())


def stratified_split_dataset(
    records: list[dict[str, Any]],
    label_key: str = "macro_tema",
    train_size: float = 0.70,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
    strict_labels: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Mantém famílias de origem disjuntas entre treino, validação e teste.

    Cada família precisa ter um único rótulo. Cada classe precisa de pelo menos
    MIN_FAMILIES_PER_CLASS famílias independentes; não há fallback sem estratificação.
    """
    ratios = (train_size, val_size, test_size)
    if min(ratios) <= 0 or abs(sum(ratios) - 1) > 1e-6:
        raise ValueError("As proporções positivas devem somar 1")
    if not records:
        raise ValueError("Dataset vazio")

    by_class: dict[str, list[list[dict[str, Any]]]] = defaultdict(list)
    for rows in _build_families(records):
        labels = {row[label_key] for row in rows}
        if len(labels) != 1:
            raise ValueError(f"Família com rótulos conflitantes: {sorted(map(str, labels))}")
        label = labels.pop()
        if strict_labels and label not in CLASSES:
            raise ValueError(f"Rótulo fora da taxonomia: {label!r}")
        by_class[label].append(rows)

    too_few = {c: len(g) for c, g in by_class.items() if len(g) < MIN_FAMILIES_PER_CLASS}
    if too_few:
        raise ValueError(
            f"Famílias insuficientes por classe (mínimo {MIN_FAMILIES_PER_CLASS}): {too_few}"
        )

    rng = random.Random(random_state)
    result: tuple[list[dict[str, Any]], ...] = ([], [], [])
    order = sorted(by_class, key=lambda c: CLASSES.index(c) if c in CLASSES else len(CLASSES))
    for label in order:
        groups = by_class[label]
        rng.shuffle(groups)
        n_val = max(1, round(len(groups) * val_size))
        n_test = max(1, round(len(groups) * test_size))
        if n_val + n_test >= len(groups):
            raise ValueError(f"Famílias insuficientes para as proporções pedidas na classe {label!r}")
        subsets = (groups[n_val + n_test :], groups[:n_val], groups[n_val : n_val + n_test])
        for dest, subset in zip(result, subsets, strict=True):
            dest.extend(row for group in subset for row in group)

    train, val, test = result
    return train, val, test


def assert_disjoint(*splits: list[dict[str, Any]]) -> None:
    """Garante que nenhuma família de origem aparece em mais de um conjunto."""
    owner: dict[tuple[str, str], int] = {}
    for idx, rows in enumerate(splits):
        for row in rows:
            for key in _row_keys(row):
                prev = owner.setdefault(key, idx)
                if prev != idx:
                    raise AssertionError(f"Vazamento: família {key[1]} aparece em mais de um conjunto")


def class_distribution(
    *splits: list[dict[str, Any]], label_key: str = "macro_tema"
) -> dict[str, dict[str, int]]:
    """Contagem por conjunto e classe, para conferência visual."""
    return {
        name: dict(Counter(row[label_key] for row in rows))
        for name, rows in zip(SPLIT_NAMES, splits, strict=True)
    }


def save_split_files(
    train_data: list[dict[str, Any]],
    val_data: list[dict[str, Any]],
    test_data: list[dict[str, Any]],
    output_dir: str = "data/synthetic",
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in zip(SPLIT_NAMES, (train_data, val_data, test_data), strict=True):
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
    train, val, test = stratified_split_dataset(records, random_state=args.seed)
    assert_disjoint(train, val, test)

    print(json.dumps(class_distribution(train, val, test), ensure_ascii=False, indent=2))
    save_split_files(train, val, test, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
