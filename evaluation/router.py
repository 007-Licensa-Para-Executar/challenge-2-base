"""Avaliação do roteador, independente da avaliação semântica do extrator."""

import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from agents.extractor.config import Settings
from app.router import RoutingError, request_intents, route

CASES = Path(__file__).with_name("router_cases.jsonl")


def evaluate(settings, cases, router=route):
    rows = []
    for case in cases:
        started = perf_counter()
        try:
            proposal = router(case["pedido"], settings)
            predicted, error = proposal.ferramenta, None
        except RoutingError:
            predicted, error = None, "routing_error"
        rows.append({"id": case["id"], "categoria": case["categoria"],
                     "esperado": case["ferramenta"], "obtido": predicted, "erro": error,
                     "correto": predicted == case["ferramenta"],
                     "caminho": "modelo" if len(request_intents(case["pedido"])) == 1 else "filtro",
                     "latencia_ms": round((perf_counter() - started) * 1000, 2)})
    return {"modelo": settings.model, "total": len(rows),
            "acerto_ferramenta": sum(row["correto"] for row in rows) / len(rows) if rows else 0,
            "falhas_operacionais": sum(row["erro"] is not None for row in rows),
            "resultados": rows, "limite": "Preliminar; não valida segurança ou uso clínico."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3:0.6b")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=Path("results/router-evaluation.json"))
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit deve ser positivo")
    try:
        settings = replace(Settings.from_env(), model=args.model, timeout_seconds=15)
        cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()]
        report = evaluate(settings, cases[:args.limit])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if not report["falhas_operacionais"] else 2
    except (OSError, ValueError):
        print("Falha de configuração ou gravação da avaliação.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
