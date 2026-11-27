"""Evaluate exact entity spans on a small synthetic Portuguese fixture set.

The benchmark uses invented people and organizations, public place names, and
non-working contact details and CPF examples to exercise identifier shapes.
It measures detection and candidate substitutions on these cases only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ENTITY_KINDS = ("PERSON", "ORG", "LOCATION", "CPF", "PHONE", "EMAIL")
FIXTURE_PATH = Path(__file__).with_name("privacy_cases.jsonl")


class DetectedSpan(Protocol):
    @property
    def start(self) -> int: ...

    @property
    def end(self) -> int: ...

    @property
    def kind(self) -> str: ...


class Detector(Protocol):
    @property
    def version(self) -> str: ...

    def detect(self, text: str) -> Iterable[DetectedSpan]: ...


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str


@dataclass(frozen=True)
class Case:
    case_id: str
    text: str
    expected: tuple[Span, ...]


def _validate_span(span: Span, text_length: int, case_id: str) -> None:
    if (
        type(span.start) is not int
        or type(span.end) is not int
        or not 0 <= span.start < span.end <= text_length
        or span.kind not in ENTITY_KINDS
    ):
        raise ValueError(f"Invalid entity span or kind in {case_id}")


def load_cases(path: Path = FIXTURE_PATH) -> list[Case]:
    cases = []
    seen_ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        case = Case(row["case_id"], row["text"], tuple(Span(**span) for span in row["expected"]))
        if case.case_id in seen_ids:
            raise ValueError(f"Duplicate benchmark case ID: {case.case_id}")
        seen_ids.add(case.case_id)
        previous_end = 0
        for span in sorted(case.expected, key=lambda span: span.start):
            _validate_span(span, len(case.text), case.case_id)
            if span.start < previous_end:
                raise ValueError(f"Overlapping gold annotations in {case.case_id}")
            previous_end = span.end
        cases.append(case)
    if not cases:
        raise ValueError("Benchmark requires at least one case")
    return cases


def _metrics(tp: int, fp: int, fn: int) -> dict[str, int | float | None]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "support": tp + fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


def evaluate_privacy(cases: Iterable[Case], detector: Detector) -> dict:
    """Score exact (start, end, kind) matches with exclusive end offsets.

    Duplicate detections are false positives. Each wrong-kind detection at the
    exact boundaries of a missed entity counts once as a label substitution,
    a false positive for the predicted kind, and a false negative for the gold kind.
    Planned substitutions count all detections, including false positives.
    Precision and recall with a zero denominator are null in the report.
    """
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    details = []
    for case in cases:
        gold = Counter(case.expected)
        predicted: Counter[Span] = Counter()
        for detection in detector.detect(case.text):
            span = Span(detection.start, detection.end, detection.kind)
            _validate_span(span, len(case.text), case.case_id)
            predicted[span] += 1
        matches = gold & predicted
        extras = predicted - gold
        misses = gold - predicted
        tp.update(span.kind for span in matches.elements())
        fp.update(span.kind for span in extras.elements())
        fn.update(span.kind for span in misses.elements())

        extra_bounds = Counter((span.start, span.end) for span in extras.elements())
        missed_bounds = Counter((span.start, span.end) for span in misses.elements())
        details.append(
            {
                "case_id": case.case_id,
                "tp": matches.total(),
                "fp": extras.total(),
                "fn": misses.total(),
                "planned_substitutions": predicted.total(),
                "label_substitutions": (extra_bounds & missed_bounds).total(),
            }
        )
    if not details:
        raise ValueError("Benchmark requires at least one case")
    return {
        "scope": "synthetic Portuguese cases with exact span and kind matching",
        "detector_version": detector.version,
        "case_count": len(details),
        "per_entity": {kind: _metrics(tp[kind], fp[kind], fn[kind]) for kind in ENTITY_KINDS},
        "micro": _metrics(tp.total(), fp.total(), fn.total()),
        "planned_substitutions": sum(case["planned_substitutions"] for case in details),
        "label_substitutions": sum(case["label_substitutions"] for case in details),
        "cases": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True, help="Local detector model path")
    args = parser.parse_args(argv)

    from privacy.detector import build_detector

    result = evaluate_privacy(load_cases(), build_detector(args.model_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
