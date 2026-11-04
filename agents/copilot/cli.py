"""Interface de linha de comando para o Agente 2 (Copiloto com RAG)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import CopilotSettings
from .contracts import ErrorInfo, ProcessingResult, RunMetadata
from .service import CopilotService


class ArgumentError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentError(f"Argumentos inválidos: {message}. Consulte --help.")


def _emit_error(code: str, message: str, model: str = "unconfigured") -> None:
    res = ProcessingResult(
        status="error",
        error=ErrorInfo(code=code, message=message),
        metadata=RunMetadata(model=model),
    )
    print(res.model_dump_json())
    print(f"{code}: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = Parser(description="Agente 2: Copiloto de síntese longitudinal e RAG para psicólogos.")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Confirma que os dados são estritamente sintéticos.",
    )
    parser.add_argument("--db", type=Path, help="Caminho do SQLite local com os dados do Agente 1.")
    parser.add_argument("--days", type=int, default=7, help="Janela de dias para análise (padrão: 7).")
    parser.add_argument("--file", type=Path, help="Arquivo JSON ou JSONL alternativo contendo extrações.")
    parser.add_argument("--model", type=str, help="Modelo Ollama a ser utilizado.")
    parser.add_argument("--mock", action="store_true", help="Executa em modo determinístico sem requisições ao Ollama.")
    parser.add_argument("--output", type=Path, help="Caminho para salvar o Dossiê JSON (padrão: stdout).")
    parser.add_argument("--report-md", type=Path, help="Caminho opcional para exportar relatório Markdown.")

    try:
        args = parser.parse_args(argv)
        if not args.synthetic:
            raise ArgumentError("O uso da flag --synthetic é obrigatório para garantir dados de teste.")

        settings = CopilotSettings.from_env()
        overrides = {}
        if args.db:
            overrides["db_path"] = args.db
        if args.model:
            overrides["model"] = args.model
        if args.mock:
            overrides["mock_mode"] = True

        if overrides:
            settings = CopilotSettings(
                db_path=overrides.get("db_path", settings.db_path),
                corpus_path=settings.corpus_path,
                model=overrides.get("model", settings.model),
                top_k=settings.top_k,
                abstention_threshold=settings.abstention_threshold,
                ollama_host=settings.ollama_host,
                mock_mode=overrides.get("mock_mode", settings.mock_mode),
            )
    except ArgumentError as e:
        _emit_error("invalid_arguments", str(e))
        return 2

    service = CopilotService(settings)

    # Obtenção das extrações: via arquivo ou SQLite
    extractions = []
    if args.file:
        try:
            with args.file.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("["):
                    extractions = json.loads(content)
                else:
                    for line in content.splitlines():
                        if line.strip():
                            extractions.append(json.loads(line))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
            _emit_error("file_read_error", f"Não foi possível ler o arquivo de entrada: {e}", settings.model)
            return 2
    else:
        extractions = service.load_extractions_from_db(db_path=settings.db_path, days_window=args.days)

    if not extractions:
        _emit_error(
            "no_data",
            f"Nenhum relato encontrado no banco '{settings.db_path}' para o período de {args.days} dias.",
            settings.model,
        )
        return 2

    result = service.analyze(extractions, days_window=args.days)

    if result.status == "error":
        _emit_error(result.error.code, result.error.message, settings.model)
        return 3

    # Exportações
    if args.report_md and result.dossier:
        try:
            args.report_md.parent.mkdir(parents=True, exist_ok=True)
            md_content = service.export_markdown_report(result.dossier)
            args.report_md.write_text(md_content, encoding="utf-8")
        except OSError as e:
            print(f"Aviso: Não foi possível salvar o relatório Markdown: {e}", file=sys.stderr)

    json_str = result.model_dump_json(indent=2)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json_str, encoding="utf-8")
        except OSError as e:
            _emit_error("output_write_error", f"Falha ao salvar saída: {e}", settings.model)
            return 3
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
