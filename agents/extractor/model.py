"""Adaptador síncrono do SDK oficial Ollama, com validação e erros sanitizados."""

from collections.abc import Mapping
from threading import Lock
from time import perf_counter

import httpx
from ollama import Client, ResponseError
from pydantic import ValidationError

from .config import Settings
from .contracts import (
    MAX_INPUT_BYTES,
    MAX_INPUT_CHARS,
    ErrorInfo,
    Extraction,
    ProcessingResult,
    RunMetadata,
)
from .prompt import SYSTEM_PROMPT

# Serializa inclusive instâncias diferentes no processo para limitar uso de memória.
_MODEL_LOCK = Lock()


def _field(value, name, default=None):
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def fetch_model_metadata(settings: Settings) -> dict:
    """Read raw tags: the SDK typed models discard cloud-routing metadata."""
    with httpx.Client(
        trust_env=False, follow_redirects=False, timeout=settings.timeout_seconds
    ) as client:
        response = client.get(settings.host.rstrip("/") + "/api/tags")
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise TypeError("Invalid local model metadata")
    return payload


class OllamaExtractor:
    def __init__(self, settings: Settings, client=None, metadata_fetcher=None):
        self.settings = settings
        self.metadata_fetcher = metadata_fetcher or fetch_model_metadata
        self.client = (
            client
            if client is not None
            else Client(
                host=settings.host,
                timeout=settings.timeout_seconds,
                trust_env=False,
                follow_redirects=False,
            )
        )

    def extract(self, text: str) -> ProcessingResult:
        started = perf_counter()
        metadata = RunMetadata(
            model=self.settings.model, context_tokens=self.settings.context_tokens
        )

        def error(code, message):
            metadata.latency_ms = (perf_counter() - started) * 1000
            return ProcessingResult(
                status="error", error=ErrorInfo(code=code, message=message), metadata=metadata
            )

        if not isinstance(text, str) or not text.strip():
            return error("invalid_input", "Informe um relato sintético não vazio.")
        if len(text) > MAX_INPUT_CHARS:
            return error("input_too_long", "O relato excede o limite de caracteres.")
        try:
            input_bytes = len(text.encode("utf-8"))
        except UnicodeError:
            return error("invalid_input", "O relato deve conter texto UTF-8 válido.")
        if input_bytes > MAX_INPUT_BYTES:
            return error("input_too_long", "O relato excede o limite de bytes UTF-8.")
        try:
            with _MODEL_LOCK:
                models = self.metadata_fetcher(self.settings)["models"]
                model = next((m for m in models if _field(m, "model") == self.settings.model), None)
                if model is None:
                    return error("model_not_found", "Modelo não instalado no Ollama local.")
                if _field(model, "remote_host") or _field(model, "remote_model"):
                    return error("remote_model_forbidden", "Use somente um modelo local instalado.")
                digest = _field(model, "digest")
                if not isinstance(digest, str) or not digest.strip():
                    return error("model_metadata_error", "Digest do modelo local indisponível.")
                metadata.model_digest = digest
                response = self.client.chat(
                    model=self.settings.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    format=Extraction.model_json_schema(),
                    stream=False,
                    think=False,
                    keep_alive="30s",
                    options={
                        "temperature": 0,
                        "num_ctx": self.settings.context_tokens,
                        "num_predict": 160,
                    },
                )
            prompt_tokens = _field(response, "prompt_eval_count")
            if (
                isinstance(prompt_tokens, int)
                and prompt_tokens >= self.settings.context_tokens - 160
            ):
                return error("context_limit", "O relato excedeu a margem de contexto do modelo.")
            message = _field(response, "message")
            if _field(message, "refusal"):
                return error("model_refusal", "O modelo recusou o processamento.")
            content = _field(message, "content")
            if not isinstance(content, str) or not content.strip():
                return error("empty_response", "O modelo não retornou uma extração.")
            extraction = Extraction.model_validate_json(content)
        except (httpx.TimeoutException, TimeoutError):
            return error("model_timeout", "Tempo limite do Ollama local excedido.")
        except (httpx.ConnectError, ConnectionError):
            return error("service_unavailable", "Ollama local indisponível.")
        except ResponseError as exc:
            code = "model_not_found" if exc.status_code == 404 else "provider_error"
            return error(code, "O Ollama local não concluiu o processamento.")
        except ValidationError:
            return error("invalid_response", "Resposta incompatível com o esquema de extração.")
        except Exception:  # noqa: BLE001 — sanitize any provider failure at this boundary.
            # Nunca propaga mensagens que possam conter o relato ou dados do provedor.
            return error("provider_error", "Não foi possível concluir a extração local.")
        metadata.latency_ms = (perf_counter() - started) * 1000
        return ProcessingResult(status="ok", extraction=extraction, metadata=metadata)
