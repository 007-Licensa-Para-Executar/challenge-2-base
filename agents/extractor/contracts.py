"""Contrato compartilhado entre modelo, CLI, persistência e avaliação."""

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"
PROMPT_VERSION = "1.0.0"
MAX_INPUT_CHARS = 2400
MAX_INPUT_BYTES = 2400


class Tema(str, Enum):
    TRABALHO = "trabalho"
    FAMILIA = "familia"
    RELACIONAMENTOS = "relacionamentos"
    ESTUDOS = "estudos"
    SAUDE = "saude"
    FINANCAS = "financas"
    LUTO = "luto"
    OUTROS = "outros"
    NAO_IDENTIFICADO = "nao_identificado"


class Sentimento(str, Enum):
    ALEGRIA = "alegria"
    TRISTEZA = "tristeza"
    RAIVA = "raiva"
    MEDO = "medo"
    PREOCUPACAO = "preocupacao"
    FRUSTRACAO = "frustracao"
    CALMA = "calma"
    NAO_IDENTIFICADO = "nao_identificado"


class IndicioRisco(str, Enum):
    PRESENTE = "presente"
    NAO_IDENTIFICADO = "nao_identificado"
    INDETERMINADO = "indeterminado"


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tema: Tema
    sentimento: Sentimento
    indicio_textual_risco: IndicioRisco


class RunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    model_digest: str | None = None
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION
    context_tokens: int = Field(default=2048, ge=2048, le=4096)
    latency_ms: float = Field(default=0, ge=0)
    synthetic: Literal[True] = True


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str  # Mensagem sanitizada, sem texto do relato nem exceção bruta.


class ProcessingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["ok", "error"]
    extraction: Extraction | None = None
    error: ErrorInfo | None = None
    metadata: RunMetadata

    @model_validator(mode="after")
    def consistent_result(self):
        if self.status == "ok" and (self.extraction is None or self.error is not None):
            raise ValueError("Successful results require extraction and no error")
        if self.status == "error" and (self.extraction is not None or self.error is None):
            raise ValueError("Error results must not contain an extraction")
        return self
