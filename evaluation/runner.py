"""Avaliação offline: exemplos sintéticos e artefatos sem os textos de entrada."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from agents.extractor.contracts import PROMPT_VERSION, SCHEMA_VERSION, Extraction

FIELDS = ("tema", "sentimento", "indicio_textual_risco")
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def load_cases(split: str, directory: Path = DATA_DIR) -> list[dict]:
    cases = []
    ids: set[str] = set()
    texts: set[str] = set()
    for name in ("dev", "holdout"):
        for line in (directory / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            if (
                case["id"] in ids
                or case["text"] in texts
                or case["synthetic"] is not True
                or case["split"] != name
                or not case["text"].strip()
                or case["annotation_status"] not in ("unreviewed", "reviewed")
            ):
                raise ValueError("Dataset inválido, duplicado ou split inconsistente")
            Extraction.model_validate(case["expected"])
            ids.add(case["id"])
            texts.add(case["text"])
            if split == "all" or split == name:
                cases.append(case)
    return cases


def summarize(rows: list[dict]) -> dict:
    """Denominador inclui erros; ausência de previsão nunca é acerto."""
    total = len(rows)
    success = [row for row in rows if row["status"] == "ok" and row.get("predicted")]
    summary: dict[str, Any] = {
        "attempts": total,
        "success": len(success),
        "errors": total - len(success),
        "success_rate": len(success) / total if total else None,
        "refusals": sum(row.get("error_code") == "model_refusal" for row in rows),
        "error_codes": dict(
            Counter(row.get("error_code") or "unknown" for row in rows if row not in success)
        ),
        "classification": {},
    }
    for field in FIELDS:
        labels = sorted(
            {row["expected"][field] for row in rows} | {row["predicted"][field] for row in success}
        )
        confusion = Counter(
            (row["expected"][field], row["predicted"][field] if row in success else "__error__")
            for row in rows
        )
        f1 = []
        for label in labels:
            tp = confusion[label, label]
            fp = sum(
                count
                for (actual, predicted), count in confusion.items()
                if predicted == label and actual != label
            )
            fn = sum(
                count
                for (actual, predicted), count in confusion.items()
                if actual == label and predicted != label
            )
            f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
        summary["classification"][field] = {
            "accuracy": sum(confusion[label, label] for label in labels) / total if total else None,
            "macro_f1": statistics.mean(f1) if f1 else None,
            "macro_f1_labels": labels,
            "confusion": {
                actual: {
                    predicted: count for (a, predicted), count in confusion.items() if a == actual
                }
                for actual in labels
            },
        }
    risk = summary["classification"]["indicio_textual_risco"]["confusion"]
    summary["risk_signal"] = {
        "false_negatives_including_errors": sum(
            count
            for predicted, count in risk.get("presente", {}).items()
            if predicted != "presente"
        ),
        "false_positives": sum(
            values.get("presente", 0) for actual, values in risk.items() if actual != "presente"
        ),
        "indeterminate_predictions": sum(
            row["predicted"]["indicio_textual_risco"] == "indeterminado" for row in success
        ),
        "determinate_coverage": sum(
            row["predicted"]["indicio_textual_risco"] != "indeterminado" for row in success
        )
        / total
        if total
        else None,
    }
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row["case_id"]].append(row)
    eligible = [values for values in grouped.values() if len(values) >= 3]
    stable = sum(
        all(
            row["status"] == "ok" and row.get("predicted") == values[0].get("predicted")
            for row in values
        )
        for values in eligible
    )
    summary["stability"] = {
        "eligible_cases_at_least_3_runs": len(eligible),
        "stable_cases": stable,
        "rate": stable / len(eligible) if eligible else None,
    }
    latency = sorted(row["latency_ms"] for row in rows)
    summary["latency_ms"] = {
        "median": statistics.median(latency) if latency else None,
        "p95": latency[max(0, math.ceil(0.95 * len(latency)) - 1)] if latency else None,
    }
    memory = [
        row["ollama_size_vram_bytes"]
        for row in rows
        if row.get("ollama_size_vram_bytes") is not None
    ]
    summary["memory"] = {
        "max_reported_ollama_size_vram_bytes": max(memory) if memory else None,
        "measurement": "Ollama /api/ps allocation; not peak RAM/RSS, shared-memory pressure or system total",
    }
    return summary


def memory_allocation(host: str, model: str) -> int | None:
    import httpx

    try:
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=3) as client:
            response = client.get(host.rstrip("/") + "/api/ps")
            response.raise_for_status()
            for entry in response.json().get("models", []):
                if entry.get("name") == model or entry.get("model") == model:
                    return entry.get("size_vram")
    except Exception:  # noqa: BLE001 — optional measurement must not expose service messages
        return None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen3:4b", "gemma3:4b"])
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="dev")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=Path("results/evaluation.json"))
    parser.add_argument("--runs-file", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if (
        args.repetitions < 1
        or args.limit is not None
        and args.limit < 1
        or len(set(args.models)) != len(args.models)
    ):
        parser.error("Repetições, limite e modelos devem ser positivos/únicos")
    import ollama

    from agents.extractor.config import Settings
    from agents.extractor.model import OllamaExtractor

    try:
        cases = load_cases(args.split)
        if args.limit:
            cases = cases[: args.limit]
        base_settings = Settings.from_env()
        manifest = {
            "dataset_sha256": hashlib.sha256(
                json.dumps(cases, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            "models": args.models,
            "split": args.split,
            "limit": args.limit,
            "repetitions": args.repetitions,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "context_tokens": base_settings.context_tokens,
            "timeout_seconds": base_settings.timeout_seconds,
            "host": base_settings.host,
            "annotation_status": "unreviewed; two human reviewers required",
        }
        client = ollama.Client(
            host=base_settings.host,
            timeout=base_settings.timeout_seconds,
            trust_env=False,
            follow_redirects=False,
        )
        # A tag pode mudar. Digest faz parte da identidade do benchmark e do resume.
        installed = {item.model: item.digest for item in client.list().models}
        manifest["model_digests"] = {model: installed.get(model) for model in args.models}
        if any(value is None for value in manifest["model_digests"].values()):
            raise ValueError("Baixe todos os modelos solicitados antes da avaliação")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        runs_file = args.runs_file or args.output.with_suffix(".jsonl")
        runs_file.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        if args.resume and runs_file.exists():
            lines = runs_file.read_text(encoding="utf-8").splitlines()
            if not lines or json.loads(lines[0]) != {"manifest": manifest}:
                raise ValueError("Resume incompatível: configuração, dataset ou digest mudou")
            rows = [json.loads(line) for line in lines[1:]]
        elif runs_file.exists():
            raise ValueError("Artefato existente: use --resume ou outro nome de saída")
        else:
            runs_file.write_text(
                json.dumps({"manifest": manifest}, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        done = {(row["model"], row["case_id"], row["repetition"]) for row in rows}
        interrupted = False
        with runs_file.open("a", encoding="utf-8") as stream:
            for model in args.models:
                settings = replace(base_settings, model=model)
                extractor = OllamaExtractor(settings)
                consecutive_errors = 0
                try:
                    for case in cases:
                        for repetition in range(1, args.repetitions + 1):
                            key = (model, case["id"], repetition)
                            if key in done:
                                continue
                            result = extractor.extract(case["text"])
                            row = {
                                "model": model,
                                "model_digest": manifest["model_digests"][model],
                                "case_id": case["id"],
                                "repetition": repetition,
                                "expected": case["expected"],
                                "status": result.status,
                                "predicted": result.extraction.model_dump(mode="json")
                                if result.extraction
                                else None,
                                "error_code": result.error.code if result.error else None,
                                "latency_ms": result.metadata.latency_ms,
                                "ollama_size_vram_bytes": memory_allocation(settings.host, model),
                                "prompt_version": result.metadata.prompt_version,
                                "schema_version": result.metadata.schema_version,
                            }
                            rows.append(row)
                            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                            stream.flush()
                            consecutive_errors = (
                                consecutive_errors + 1 if result.status == "error" else 0
                            )
                            print(
                                f"{model}: {case['id']} repetição {repetition}: {result.status}",
                                file=sys.stderr,
                            )
                            if consecutive_errors >= 3:
                                raise RuntimeError(
                                    "Três falhas consecutivas: avaliação interrompida; retome após corrigir o serviço"
                                )
                except (RuntimeError, KeyboardInterrupt):
                    interrupted = True
                    break
                finally:
                    try:
                        client.generate(model=model, prompt="", keep_alive=0)
                    except Exception:  # noqa: BLE001 — sanitize service messages
                        print(
                            "Não foi possível confirmar descarregamento do modelo.", file=sys.stderr
                        )
        report = {
            "manifest": manifest,
            "complete": len(rows) == len(cases) * len(args.models) * args.repetitions,
            "models": {
                model: summarize([row for row in rows if row["model"] == model])
                for model in args.models
            },
            "limitations": [
                "Referências sintéticas preliminares, não revisadas por humanos",
                "Sem validação clínica; risco é sinal textual, não diagnóstico",
                "size_vram é alocação reportada pelo serviço, não pico de RAM",
            ],
        }
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "report": str(args.output),
                    "runs": str(runs_file),
                    "complete": report["complete"],
                },
                ensure_ascii=False,
            )
        )
        return 1 if interrupted else 0
    except Exception:  # noqa: BLE001 — artifact boundary sanitizes unexpected errors
        print(
            json.dumps(
                {
                    "error": "evaluation_failed",
                    "message": "Verifique serviço/modelos, dataset e compatibilidade dos artefatos.",
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
