import json

import pytest

from evaluation.runner import DATA_DIR, load_cases, summarize


def make_row(case_id, expected, predicted=None, repetition=1):
    return {
        "case_id": case_id,
        "expected": expected,
        "predicted": predicted,
        "status": "ok" if predicted else "error",
        "error_code": None if predicted else "unavailable",
        "repetition": repetition,
        "latency_ms": 10,
        "ollama_size_vram_bytes": None,
    }


def test_dataset_has_disjoint_splits_and_required_scenarios():
    dev, holdout = load_cases("dev"), load_cases("holdout")
    assert (len(dev), len(holdout)) == (60, 40)
    assert not {c["id"] for c in dev} & {c["id"] for c in holdout}
    assert not {c["text"] for c in dev} & {c["text"] for c in holdout}
    for split in (dev, holdout):
        tags = {tag for case in split for tag in case["scenario_tags"]}
        assert {
            "claro",
            "misto",
            "curto",
            "negacao",
            "historico",
            "terceiros",
            "figurado",
            "injecao",
            "dano_explicito",
            "ambiguo",
        } <= tags
        assert all(c["synthetic"] and c["annotation_status"] == "unreviewed" for c in split)


def test_failed_attempt_counts_as_error_false_negative_and_reduces_accuracy():
    expected = {"tema": "trabalho", "sentimento": "medo", "indicio_textual_risco": "presente"}
    rows = [make_row("a", expected, expected), make_row("b", expected)]
    report = summarize(rows)
    assert report["success_rate"] == 0.5
    assert report["classification"]["tema"]["accuracy"] == 0.5
    assert report["classification"]["tema"]["macro_f1"] == pytest.approx(2 / 3)
    assert report["risk_signal"]["false_negatives_including_errors"] == 1
    assert report["risk_signal"]["false_positives"] == 0
    assert (
        report["classification"]["indicio_textual_risco"]["confusion"]["presente"]["__error__"] == 1
    )


def test_stability_requires_three_successful_equal_predictions():
    expected = {
        "tema": "familia",
        "sentimento": "calma",
        "indicio_textual_risco": "nao_identificado",
    }
    rows = [make_row("a", expected, expected, r) for r in (1, 2, 3)]
    rows += [make_row("b", expected, expected, r) for r in (1, 2)] + [
        make_row("b", expected, repetition=3)
    ]
    report = summarize(rows)
    assert report["stability"] == {
        "eligible_cases_at_least_3_runs": 2,
        "stable_cases": 1,
        "rate": 0.5,
    }
    assert report["risk_signal"]["determinate_coverage"] == pytest.approx(5 / 6)


def test_false_positive_and_indeterminate_are_distinct():
    expected = {
        "tema": "outros",
        "sentimento": "tristeza",
        "indicio_textual_risco": "nao_identificado",
    }
    present = {**expected, "indicio_textual_risco": "presente"}
    uncertain = {**expected, "indicio_textual_risco": "indeterminado"}
    report = summarize([make_row("a", expected, present), make_row("b", expected, uncertain)])
    assert report["risk_signal"]["false_positives"] == 1
    assert report["risk_signal"]["indeterminate_predictions"] == 1
    assert report["risk_signal"]["determinate_coverage"] == 0.5


def test_empty_report_is_explicit_about_missing_measurements():
    report = summarize([])
    assert report["success_rate"] is None
    assert report["latency_ms"]["median"] is None
    assert report["memory"]["max_reported_ollama_size_vram_bytes"] is None


def test_duplicate_dataset_is_rejected(tmp_path):
    for name in ("dev", "holdout"):
        (tmp_path / f"{name}.jsonl").write_text((DATA_DIR / f"{name}.jsonl").read_text())
    case = load_cases("dev")[0]
    case["split"] = "holdout"
    with (tmp_path / "holdout.jsonl").open("a") as file:
        file.write(json.dumps(case) + "\n")
    with pytest.raises(ValueError):
        load_cases("all", tmp_path)


def test_runner_resume_and_changed_configuration_are_safe(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    import ollama

    import agents.extractor.model as model_module
    from agents.extractor.contracts import (
        Extraction,
        ProcessingResult,
        RunMetadata,
        ValidationMetrics,
    )
    from evaluation.runner import main

    class Client:
        def __init__(self, **kwargs):
            pass

        def list(self):
            return SimpleNamespace(models=[SimpleNamespace(model="fake:1", digest="digest-1")])

        def generate(self, **kwargs):
            return None

    calls = []

    class Extractor:
        def __init__(self, settings):
            self.settings = settings

        def extract(self, text):
            calls.append(text)
            return ProcessingResult(
                status="ok",
                extraction=Extraction.model_validate(load_cases("dev")[0]["expected"]),
                validation=ValidationMetrics(
                    nlp_polaridade="NEUTRO",
                    nlp_score=0.0,
                    discrepancia_detectada=False,
                    distancia_polaridade=0.0,
                ),
                metadata=RunMetadata(
                    model=self.settings.model, model_digest="digest-1", latency_ms=12
                ),
            )

    monkeypatch.setattr(ollama, "Client", Client)
    monkeypatch.setattr(model_module, "OllamaExtractor", Extractor)
    monkeypatch.setattr("evaluation.runner.memory_allocation", lambda host, model: None)
    output = tmp_path / "summary.json"
    args = ["--models", "fake:1", "--limit", "1", "--repetitions", "1", "--output", str(output)]
    assert main(args) == 0
    assert main(args + ["--resume"]) == 0
    assert len(calls) == 1
    assert main(args) == 2
    assert main(args + ["--resume", "--repetitions", "3"]) == 2
    assert len(calls) == 1
    assert load_cases("dev")[0]["text"] not in output.with_suffix(".jsonl").read_text()
    assert json.loads(output.read_text())["complete"] is True
    capsys.readouterr()


def test_runner_circuit_breaker_keeps_checkpoint(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    import ollama

    import agents.extractor.model as model_module
    from agents.extractor.contracts import ErrorInfo, ProcessingResult, RunMetadata
    from evaluation.runner import main

    class Client:
        def __init__(self, **kwargs):
            pass

        def list(self):
            return SimpleNamespace(models=[SimpleNamespace(model="fake:1", digest="digest-1")])

        def generate(self, **kwargs):
            return None

    class Extractor:
        def __init__(self, settings):
            self.settings = settings

        def extract(self, text):
            return ProcessingResult(
                status="error",
                error=ErrorInfo(code="service_unavailable", message="Serviço indisponível"),
                metadata=RunMetadata(model=self.settings.model, latency_ms=1),
            )

    monkeypatch.setattr(ollama, "Client", Client)
    monkeypatch.setattr(model_module, "OllamaExtractor", Extractor)
    monkeypatch.setattr("evaluation.runner.memory_allocation", lambda host, model: None)
    output = tmp_path / "partial.json"
    assert (
        main(["--models", "fake:1", "--limit", "5", "--repetitions", "1", "--output", str(output)])
        == 1
    )
    report = json.loads(output.read_text())
    assert not report["complete"]
    assert report["models"]["fake:1"]["attempts"] == 3
    assert report["models"]["fake:1"]["success_rate"] == 0
    assert len(output.with_suffix(".jsonl").read_text().splitlines()) == 4
    capsys.readouterr()
