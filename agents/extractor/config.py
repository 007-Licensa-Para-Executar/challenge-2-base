"""Configuração local explícita; nenhum serviço externo ou fallback implícito."""

import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    model: str = "qwen3:4b"
    host: str = "http://127.0.0.1:11434"
    context_tokens: int = 2048
    timeout_seconds: float = 60
    db_path: str = "data/extractions.sqlite3"

    def __post_init__(self):
        try:
            url = urlsplit(self.host)
            valid_host = (
                url.scheme == "http"
                and url.hostname in {"127.0.0.1", "localhost", "::1"}
                and url.username is None
                and url.password is None
                and url.path in {"", "/"}
                and not url.query
                and not url.fragment
                and (url.port is None or 1 <= url.port <= 65535)
            )
        except (ValueError, TypeError):
            valid_host = False
        if not valid_host:
            raise ValueError("OLLAMA_HOST deve apontar para HTTP em loopback local.")
        if not self.model.strip() or "cloud" in self.model.lower() or "/" in self.model:
            raise ValueError("EXTRACTOR_MODEL deve identificar um modelo local.")
        if not 2048 <= self.context_tokens <= 4096:
            raise ValueError("EXTRACTOR_CONTEXT_TOKENS deve estar entre 2048 e 4096.")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("EXTRACTOR_TIMEOUT_SECONDS deve ser positivo e finito.")
        if not self.db_path.strip():
            raise ValueError("EXTRACTOR_DB_PATH não pode ser vazio.")

    @classmethod
    def from_env(cls):
        try:
            context = int(os.environ.get("EXTRACTOR_CONTEXT_TOKENS", "2048"))
            timeout = float(os.environ.get("EXTRACTOR_TIMEOUT_SECONDS", "60"))
        except ValueError:
            raise ValueError("Configuração numérica do extrator inválida.") from None
        return cls(
            model=os.environ.get("EXTRACTOR_MODEL", "qwen3:4b"),
            host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
            context_tokens=context,
            timeout_seconds=timeout,
            db_path=os.environ.get("EXTRACTOR_DB_PATH", "data/extractions.sqlite3"),
        )
