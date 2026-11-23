import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from evaluation.privacy import ENTITY_KINDS, Case, Span, evaluate_privacy, load_cases, main


class FakeDetector:
    version = "test-detector-v1"

    def __init__(self, detections: dict[str, list[Span]]) -> None:
        self.detections = detections

    def detect(self, text: str) -> list[Span]:
        return self.detections.get(text, [])


def test_fixture_annotations_use_character_offsets_and_cover_all_entity_kinds():
    cases = load_cases()
    by_id = {case.case_id: case for case in cases}
    assert {span.kind for case in cases for span in case.expected} == set(ENTITY_KINDS)
    assert sum(not case.expected for case in cases) >= 3

    unicode = by_id["person-decomposed-unicode"]
    (span,) = unicode.expected
    assert unicode.text[span.start : span.end] == "Andre\u0301 Solivaz"
    repeated = by_id["person-repeated"]
    assert [repeated.text[span.start : span.end] for span in repeated.expected] == [
        "Téo Solivaz",
        "Téo Solivaz",
        "Téo",
    ]


def test_exact_scoring_counts_duplicates_partial_spans_label_errors_and_negatives():
    text = "Érica Ventoluz escreveu a caixa@exemplo.invalid."
    person = Span(0, len("Érica Ventoluz"), "PERSON")
    email = Span(text.index("caixa"), len(text) - 1, "EMAIL")
    location = Span(0, len("Recife"), "LOCATION")
    negative = "Sem detalhes."
    cases = [
        Case("mixed", text, (person, email)),
        Case("location", "Recife", (location,)),
        Case("negative", negative, ()),
    ]
    detector = FakeDetector(
        {
            text: [person, person, Span(email.start, email.end, "ORG")],
            "Recife": [Span(0, 5, "LOCATION")],
            negative: [Span(0, 3, "PERSON")],
        }
    )

    report = evaluate_privacy(cases, detector)

    assert report["micro"] == {
        "tp": 1,
        "fp": 4,
        "fn": 2,
        "support": 3,
        "precision": 1 / 5,
        "recall": 1 / 3,
    }
    assert report["per_entity"]["PERSON"] == {
        "tp": 1,
        "fp": 2,
        "fn": 0,
        "support": 1,
        "precision": 1 / 3,
        "recall": 1,
    }
    assert report["per_entity"]["EMAIL"] == {
        "tp": 0,
        "fp": 0,
        "fn": 1,
        "support": 1,
        "precision": None,
        "recall": 0,
    }
    assert report["planned_substitutions"] == 5
    assert report["label_substitutions"] == 1
    assert report["cases"][-1] == {
        "case_id": "negative",
        "tp": 0,
        "fp": 1,
        "fn": 0,
        "planned_substitutions": 1,
        "label_substitutions": 0,
    }
    encoded = json.dumps(report, ensure_ascii=False)
    assert "Érica Ventoluz" not in encoded
    assert "caixa@exemplo.invalid" not in encoded


def test_invalid_detection_errors_omit_case_text():
    case = Case("invalid-span", "Texto sintético.", ())
    detector = FakeDetector({case.text: [Span(0, 99, "PERSON")]})

    with pytest.raises(ValueError, match="^Invalid entity span or kind in invalid-span$"):
        evaluate_privacy([case], detector)


def test_cli_uses_local_model_path_and_prints_metrics(monkeypatch, capsys):
    model_path = Path("fixture-model")
    detector_module = ModuleType("privacy.detector")

    def build_detector(path):
        assert path == model_path
        return FakeDetector({})

    detector_module.build_detector = build_detector
    monkeypatch.setitem(sys.modules, "privacy.detector", detector_module)

    assert main(["--model-path", str(model_path)]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["detector_version"] == FakeDetector.version
    assert report["case_count"] == len(load_cases())
    assert report["planned_substitutions"] == 0
    assert report["micro"]["fn"] == sum(len(case.expected) for case in load_cases())
    assert report["micro"]["recall"] == 0
