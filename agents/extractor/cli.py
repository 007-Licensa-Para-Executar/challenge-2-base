"""Interface de terminal: um JSON por execução, sem relatos nos diagnósticos."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .config import Settings
from .contracts import MAX_INPUT_BYTES, MAX_INPUT_CHARS, ErrorInfo, ProcessingResult, RunMetadata
from .model import OllamaExtractor
from .storage import StorageError, save_result


class ArgumentError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentError("Argumentos inválidos. Consulte --help.")


def _error(code: str, message: str, settings=None) -> ProcessingResult:
    return ProcessingResult(
        status="error",
        error=ErrorInfo(code=code, message=message),
        metadata=RunMetadata(
            model=settings.model if settings else "unconfigured",
            context_tokens=settings.context_tokens if settings else 2048,
        ),
    )


def _emit(result: ProcessingResult) -> None:
    print(result.model_dump_json())
    if result.error:
        print(f"{result.error.code}: {result.error.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = Parser(description="Extrai metadados experimentais somente de textos sintéticos.")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Confirma que a entrada foi inteiramente inventada para testes.",
    )
    parser.add_argument("--file", type=Path, help="Arquivo de entrada UTF-8; padrão: stdin.")
    parser.add_argument("--db", help="Caminho do SQLite local.")
    parser.add_argument("--model", help="Modelo instalado no Ollama local.")
    parser.add_argument(
        "--encrypt",
        dest="encrypt",
        action="store_true",
        default=None,
        help="Força criptografia do relato no banco SQLite (LGPD Art. 46).",
    )
    parser.add_argument(
        "--no-encrypt",
        dest="encrypt",
        action="store_false",
        help="Desativa explicitamente a criptografia em repouso.",
    )
    settings = None
    try:
        args = parser.parse_args(argv)
        if not args.synthetic:
            raise ArgumentError("Use --synthetic somente para entradas inteiramente inventadas.")
        settings = Settings.from_env()
        overrides = {}
        if args.db:
            overrides["db_path"] = args.db
        if args.model:
            overrides["model"] = args.model
        settings = replace(settings, **overrides)
    except ArgumentError as error:
        _emit(_error("invalid_input", str(error), settings))
        return 2
    except (ValueError, TypeError, OSError):
        _emit(_error("invalid_config", "Configuração inválida; revise as variáveis de ambiente."))
        return 2
    try:
        if args.file:
            with args.file.open(encoding="utf-8") as stream:
                text = stream.read(MAX_INPUT_CHARS + 1)
        else:
            text = sys.stdin.read(MAX_INPUT_CHARS + 1)
        if (
            not text.strip()
            or len(text) > MAX_INPUT_CHARS
            or len(text.encode("utf-8")) > MAX_INPUT_BYTES
        ):
            raise ArgumentError(
                f"Use entrada não vazia com até {MAX_INPUT_CHARS} caracteres e {MAX_INPUT_BYTES} bytes UTF-8."
            )
    except (OSError, UnicodeError):
        _emit(_error("input_read_error", "Não foi possível ler a entrada UTF-8.", settings))
        return 2
    except ArgumentError as error:
        _emit(_error("invalid_input", str(error), settings))
        return 2
    try:
        result = OllamaExtractor(settings).extract(text)
    except Exception:  # noqa: BLE001 - sanitize unexpected third-party failures
        # Última barreira: bibliotecas externas podem incluir o relato na exceção.
        result = _error("model_error", "Falha inesperada ao executar o modelo local.", settings)
    try:
        save_result(settings.db_path, text, result, encrypt=args.encrypt)
    except StorageError:
        _emit(_error("storage_error", "A execução não foi salva no banco local.", settings))
        return 3
    _emit(result)
    return 0 if result.status == "ok" else 2
