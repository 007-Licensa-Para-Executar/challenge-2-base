"""Geração local com referências validadas, sem fallback silencioso ou fontes inventadas."""

from __future__ import annotations

import json
import math

import httpx
import ollama
from pydantic import ValidationError

from .contracts import DraftAnswer, Evidence, Query
from .prompt import SYSTEM_PROMPT, build_prompt


class GenerationError(Exception):
    """Código público sanitizado; nunca incorpora relato nem exceção do fornecedor."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class OllamaGenerator:
    def __init__(self, model="qwen3:4b", host="http://localhost:11434", timeout=60):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Modelo não pode ser vazio")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout deve ser positivo e finito")
        self.model = model
        self.client = ollama.Client(host=host, timeout=timeout)

    def generate(self, query: Query, evidence: list[Evidence]) -> DraftAnswer:
        """Valida escopo e referências. Isso não comprova suporte semântico da paráfrase."""
        try:
            query = Query.model_validate(query.model_dump(warnings=False))
            evidence = [
                Evidence.model_validate(item.model_dump(warnings=False)) for item in evidence
            ]
        except (ValidationError, AttributeError, TypeError):
            raise GenerationError("invalid_context") from None
        if not evidence:
            raise GenerationError("insufficient_evidence")
        if len(evidence) > 5 or sum(len(e.quote) for e in evidence) > 6000:
            raise GenerationError("context_too_large")
        ids = {e.chunk_id for e in evidence}
        if len(ids) != len(evidence):
            raise GenerationError("invalid_context")
        if any(
            e.patient_id != query.patient_id
            or (query.start_at is not None and e.recorded_at < query.start_at)
            or (query.end_at is not None and e.recorded_at > query.end_at)
            for e in evidence
        ):
            raise GenerationError("invalid_context")
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(query, evidence)},
                ],
                format=DraftAnswer.model_json_schema(),
                options={"temperature": 0, "num_ctx": 4096, "num_predict": 512},
                think=False,
                stream=False,
            )
        except httpx.TimeoutException:
            raise GenerationError("generation_timeout") from None
        except (httpx.ConnectError, ConnectionError, OSError):
            raise GenerationError("service_unavailable") from None
        except ollama.ResponseError as error:
            code = "model_unavailable" if error.status_code == 404 else "generation_service_error"
            raise GenerationError(code) from None
        except httpx.HTTPError:
            raise GenerationError("generation_service_error") from None
        try:
            message = response["message"]
            if message.get("refusal"):
                raise GenerationError("model_refusal")
            content = message["content"]
            if not isinstance(content, str):
                raise GenerationError("invalid_response")
            data = json.loads(content)
            if (
                isinstance(data, dict)
                and data.get("statements") == []
                and set(data) == {"statements"}
            ):
                raise GenerationError("insufficient_evidence")
            result = DraftAnswer.model_validate(data)
        except (KeyError, TypeError, AttributeError, ValueError, ValidationError):
            raise GenerationError("invalid_response") from None
        if any(
            not statement.text.strip()
            or len(set(statement.evidence_ids)) != len(statement.evidence_ids)
            or not set(statement.evidence_ids).issubset(ids)
            for statement in result.statements
        ):
            raise GenerationError("invalid_references")
        return result
