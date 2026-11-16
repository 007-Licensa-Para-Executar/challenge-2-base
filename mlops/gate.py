"""Critério de promoção do modelo de sentimento."""

from __future__ import annotations


def should_promote(candidate_f1: float, baseline_f1: float, min_f1_macro: float) -> bool:
    """Promove quando o F1 macro da validação cobre o limiar e o baseline."""
    return candidate_f1 >= baseline_f1 and candidate_f1 >= min_f1_macro
