"""Leakage checks independent from model classification quality."""

import json
from pathlib import Path

import pytest

from data.split import stratified_split_dataset
from data.synthetic_generator import infer_template_group


def test_versioned_dataset_has_disjoint_template_families():
    rows = json.loads(Path("data/synthetic/synthetic_diaries.json").read_text(encoding="utf-8"))
    splits = stratified_split_dataset(rows)
    assert splits == stratified_split_dataset(rows)
    groups = [{infer_template_group(r["texto"]) for r in split} for split in splits]
    texts = [{r["texto"] for r in split} for split in splits]
    for i in range(3):
        for j in range(i + 1, 3):
            assert groups[i].isdisjoint(groups[j])
            assert texts[i].isdisjoint(texts[j])
    assert sum(map(len, splits)) == len(rows)
    expected = {r["macro_tema"] for r in rows}
    assert all({r["macro_tema"] for r in split} == expected for split in splits)


def test_legacy_known_variants_are_not_split_apart():
    from data.synthetic_generator import _OFFLINE_TEMPLATES

    bases = _OFFLINE_TEMPLATES["persona_universitario"]["estudos"]
    rows = [
        {"id": str(i), "macro_tema": "estudos", "texto": prefix + base}
        for i, (base, prefix) in enumerate((b, p) for b in bases for p in ("", "Introdução "))
    ]
    splits = stratified_split_dataset(rows)
    assert all(len(s) == 2 for s in splits)


def test_rejects_insufficient_source_families_and_conflicting_labels():
    with pytest.raises(ValueError, match="3 independent"):
        stratified_split_dataset([{"texto": "same text", "macro_tema": "a"}] * 10)
    with pytest.raises(ValueError, match="conflicting"):
        stratified_split_dataset(
            [{"texto": "same text", "macro_tema": "a"}, {"texto": "same text", "macro_tema": "b"}]
        )


def test_explicit_family_links_and_identical_texts_are_both_respected():
    rows = [
        {"texto": f"Family number {g} variation {v}", "macro_tema": "a", "group_id": str(g)}
        for g in range(6)
        for v in range(2)
    ]
    rows.append({**rows[0], "group_id": "separate_metadata"})
    splits = stratified_split_dataset(rows)
    assert sum(any(r["texto"] == rows[0]["texto"] for r in s) for s in splits) == 1
    groups = [{r["group_id"] for r in s} for s in splits]
    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])
