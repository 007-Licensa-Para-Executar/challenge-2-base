"""CLI do fluxo temático + consulta de diários fictícios com fontes."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from privacy.client import PrivacyClient, PrivacyError
from privacy.contracts import DEFAULT_URL, DEMO_DIR

from .contracts import DiaryRecord, Query
from .ingestion import classify_record
from .model import OllamaGenerator
from .privacy_flow import map_patient, protect_diary, protect_query
from .retriever import RetrievalError, Retriever
from .service import CopilotService
from .storage import DiaryStore, DuplicateRecordError, ProtectedDiaryStore

DEMO = Path(__file__).resolve().parents[2] / "knowledge_base" / "patient_demo" / "diaries.jsonl"


def _emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _classify(record, args):
    if not args.classify:
        return record
    return classify_record(record, model_path=args.model_path, vectorizer_path=args.vectorizer_path)


def _matching_record(store, record):
    for existing in store.list_records(Query(patient_id=record.patient_id, question="listar")):
        if existing.record_id != record.record_id:
            continue
        if any(
            getattr(existing, field) != getattr(record, field)
            for field in ("analysis_text", "recorded_at", "source_title", "representation_id")
        ):
            raise ValueError("Identificador existente com outro conteúdo")
        return existing
    return None


def main(argv: list[str] | None = None) -> int:
    # JSON text remains UTF-8 when redirected from CMD or a legacy-codepage console.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed", help="Importar os dois pacientes inteiramente fictícios")
    seed.add_argument("--fixtures", type=Path, default=DEMO)
    ingest = sub.add_parser("ingest", help="Salvar um relato sintético e opcionalmente classificar")
    ingest.add_argument("--patient-id", required=True)
    ingest.add_argument("--record-id")
    ingest.add_argument(
        "--at", required=True, help="Data ISO-8601 com fuso, por exemplo 2026-11-09T12:00:00Z"
    )
    ingest.add_argument("--title", default="Diário sintético")
    source = ingest.add_mutually_exclusive_group()
    source.add_argument("--text")
    source.add_argument("--file", type=Path)
    for command in (seed, ingest):
        command.add_argument(
            "--synthetic",
            action="store_true",
            required=True,
            help="Confirma que todos os relatos são inteiramente fictícios",
        )
        command.add_argument("--classify", action="store_true")
        command.add_argument("--model-path", type=Path)
        command.add_argument("--vectorizer-path", type=Path)
    listing = sub.add_parser("list", help="Listar registros sintéticos da pessoa e período")
    ask = sub.add_parser("ask", help="Consultar trechos e gerar resposta com referências")
    ask.add_argument("question", nargs="?")
    ask.add_argument("--question-stdin", action="store_true")
    ask.add_argument("--generation", choices=["extractive", "ollama"], default="ollama")
    ask.add_argument("--backend", choices=["bm25", "e5"], default="bm25")
    ask.add_argument("--embedding-model-path", type=Path)
    ask.add_argument("--min-score", type=float)
    ask.add_argument("--top-k", type=int, choices=range(1, 6), default=3)
    ask.add_argument("--model", default="qwen3:4b")
    ask.add_argument("--ollama-host", default="http://localhost:11434")
    ask.add_argument("--timeout", type=float, default=60)
    for command in (listing, ask):
        command.add_argument("--patient-id", required=True)
        command.add_argument("--from", dest="start_at", help="Início inclusivo ISO-8601 com fuso")
        command.add_argument("--to", dest="end_at", help="Fim inclusivo ISO-8601 com fuso")
    for command in (seed, ingest, listing, ask):
        command.add_argument("--db", type=Path)
        command.add_argument("--privacy", action="store_true", help="Usar API local e base tratada")
        command.add_argument("--privacy-dir", type=Path, default=DEMO_DIR)
        command.add_argument("--privacy-url", default=DEFAULT_URL)
    args = parser.parse_args(argv)
    try:
        directory = args.privacy_dir
        store = (
            ProtectedDiaryStore(args.db or directory / "analytics.sqlite3") if args.privacy
            else DiaryStore(args.db or Path("data/copilot_demo.sqlite3"))
        )
        privacy = (
            PrivacyClient(directory / "analysis.token", args.privacy_url)
            if args.privacy and args.command != "list" else None
        )
        if args.command == "seed":
            records = [
                DiaryRecord.model_validate_json(line)
                for line in args.fixtures.read_text(encoding="utf-8-sig").splitlines()
                if line.strip()
            ]
            if len({record.record_id for record in records}) != len(records):
                raise ValueError("Identificadores duplicados no arquivo de importação")
            if privacy:
                records = [protect_diary(record, privacy, directory) for record in records]
            saved, skipped, errors = 0, 0, 0
            for record in records:
                if _matching_record(store, record) is not None:
                    skipped += 1
                    continue
                record = _classify(record, args)
                store.save(record)
                saved += 1
                errors += record.classification.status == "error"
            _emit(
                {
                    "status": "ok" if not errors else "classification_error",
                    "saved": saved,
                    "skipped": skipped,
                    "classification_errors": errors,
                    "synthetic": True,
                }
            )
            return 1 if errors else 0
        if args.command == "ingest":
            text = args.text
            if args.file:
                with args.file.open("r", encoding="utf-8-sig", newline="") as source:
                    text = source.read(20001)
            if text is None:
                if hasattr(sys.stdin, "reconfigure"):
                    sys.stdin.reconfigure(encoding="utf-8", newline="")
                text = sys.stdin.read(20001)
            fields = {
                "patient_id": args.patient_id,
                "recorded_at": args.at,
                "original_text": text,
                "source_title": args.title,
            }
            if args.record_id:
                fields["record_id"] = args.record_id
            record = DiaryRecord.model_validate(fields)
            if privacy:
                record = protect_diary(record, privacy, directory)
            previous = _matching_record(store, record) if privacy else None
            if previous is not None:
                record = previous
            else:
                record = _classify(record, args)
                try:
                    store.save(record)
                except DuplicateRecordError:
                    previous = _matching_record(store, record) if privacy else None
                    if previous is None:
                        raise
                    record = previous
            excluded = {"original_text"} if privacy else {
                "treated_text", "representation_id", "detector_version",
            }
            _emit(record.model_dump(mode="json", exclude=excluded))
            return 1 if record.classification.status == "error" else 0
        question = "listar"
        if args.command == "ask":
            if args.question_stdin:
                if args.question is not None:
                    raise ValueError("Escolha uma entrada de pergunta")
                if hasattr(sys.stdin, "reconfigure"):
                    sys.stdin.reconfigure(encoding="utf-8")
                question = sys.stdin.read(2001)
            else:
                question = args.question
            if not question or len(question) > 2000:
                raise ValueError("Pergunta inválida")
        query = Query(
            patient_id=map_patient(args.patient_id, directory) if args.privacy else args.patient_id,
            question=question,
            start_at=args.start_at,
            end_at=args.end_at,
        )
        if args.command == "list":
            excluded = {"original_text"} if args.privacy else {
                "treated_text", "representation_id", "detector_version",
            }
            _emit([r.model_dump(mode="json", exclude=excluded) for r in store.list_records(query)])
            return 0
        if privacy:
            query = protect_query(query, privacy, directory)
        if args.timeout <= 0:
            raise ValueError("Timeout precisa ser positivo")
        retriever = Retriever(
            backend=args.backend, model_path=args.embedding_model_path, min_score=args.min_score
        )
        if args.privacy and args.generation == "ollama":
            from agents.extractor.config import Settings

            Settings(host=args.ollama_host, model=args.model, timeout_seconds=args.timeout)
        generator = (
            OllamaGenerator(model=args.model, host=args.ollama_host, timeout=args.timeout)
            if args.generation == "ollama"
            else None
        )
        result = CopilotService(store, retriever, generator).answer(
            query, generation_mode=args.generation, top_k=args.top_k
        )
        _emit(result.model_dump(mode="json"))
        return 1 if result.status == "error" else 0
    except PrivacyError as error:
        print(f"Pseudonimização interrompida ({error}).", file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error, ValueError, ValidationError, RetrievalError):
        print(
            "Falha de entrada, armazenamento ou configuração; nenhum resultado foi inventado.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
