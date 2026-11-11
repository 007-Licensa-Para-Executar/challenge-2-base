"""Contrato compartilhado entre modelo, CLI, persistência e avaliação."""

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.1.0"
PROMPT_VERSION = "1.0.0"
MAX_INPUT_CHARS = 2400
MAX_INPUT_BYTES = 2400


class MacroTema(str, Enum):
    TRABALHO = "trabalho"
    FAMILIA = "familia"
    RELACIONAMENTOS = "relacionamentos"
    ESTUDOS = "estudos"
    SAUDE_SONO = "saude_sono"
    FINANCAS = "financas"
    LUTO = "luto"
    AUTOESTIMA = "autoestima"
    OUTROS = "outros"
    NAO_IDENTIFICADO = "nao_identificado"
    OUTROS_INDETERMINADO = "outros_indeterminado"
    SAUDE = "saude"


class Tema(str, Enum):
    TRABALHO = "trabalho"
    FAMILIA = "familia"
    RELACIONAMENTOS = "relacionamentos"
    ESTUDOS = "estudos"
    SAUDE = "saude"
    SAUDE_SONO = "saude_sono"
    FINANCAS = "financas"
    LUTO = "luto"
    AUTOESTIMA = "autoestima"
    OUTROS = "outros"
    NAO_IDENTIFICADO = "nao_identificado"
    OUTROS_INDETERMINADO = "outros_indeterminado"


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


class ValidationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nlp_polaridade: Literal["POSITIVO", "NEGATIVO", "NEUTRO"]
    nlp_score: float = Field(ge=-1, le=1)
    discrepancia_detectada: bool
    distancia_polaridade: float = Field(ge=0, le=2)


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
    validation: ValidationMetrics | None = None
    error: ErrorInfo | None = None
    metadata: RunMetadata

    @model_validator(mode="after")
    def consistent_result(self):
        if self.status == "ok" and (
            self.extraction is None or self.validation is None or self.error is not None
        ):
            raise ValueError("Successful results require extraction and validation, with no error")
        if self.status == "error" and (
            self.extraction is not None or self.validation is not None or self.error is None
        ):
            raise ValueError("Error results must not contain an extraction")
        return self


class EvidenceSpan(BaseModel):
    """Trecho literal e exato extraído do relato clínico com posições de caractere."""

    model_config = ConfigDict(extra="ignore")
    quote_text: str = Field(description="Citação textual literal e exata proferida pelo paciente")
    start_char: int = Field(default=0, ge=0, description="Índice inicial do caractere no relato")
    end_char: int = Field(default=0, ge=0, description="Índice final do caractere no relato")
    audio_start_sec: float | None = Field(
        default=None, ge=0.0, description="Início do trecho no áudio em segundos"
    )
    audio_end_sec: float | None = Field(
        default=None, ge=0.0, description="Fim do trecho no áudio em segundos"
    )


class SubTemaItem(BaseModel):
    """Subtema clínico específico decomposto a partir do relato e referenciado por evidências."""

    model_config = ConfigDict(extra="ignore")
    nome: str = Field(
        min_length=2,
        max_length=100,
        description="Nome conciso do subtema clínico (ex: 'Irmão', 'Pai', 'Carga Horária')",
    )
    descricao: str = Field(
        min_length=5,
        max_length=500,
        description="Contextualização clínica descritiva do subtema observado",
    )
    evidencias: list[EvidenceSpan] = Field(
        min_length=1,
        description="Lista de trechos literais comprovando a ocorrência do subtema",
    )


class Agent1LLMExtraction(BaseModel):
    """Esquema estrito de saída gerado pelo LLM local (Ollama Structured Outputs)."""

    model_config = ConfigDict(extra="ignore")
    subtemas: list[SubTemaItem] = Field(
        min_length=1,
        max_length=8,
        description="Lista de subtemas específicos encontrados no relato clínico",
    )
    sentimento_predominante: Sentimento = Field(
        description="Sentimento clínico predominante expresso no relato"
    )
    score_polaridade: float = Field(
        ge=-1.0,
        le=1.0,
        description="Valência afetiva contínua de -1.0 (sofrimento severo) a +1.0 (afeto positivo)",
    )
    indicio_textual_risco: IndicioRisco = Field(
        default=IndicioRisco.NAO_IDENTIFICADO,
        description="Sinalizador de risco textual de autolesão/ideação",
    )


class Agent1Output(BaseModel):
    """Saída completa do Agente 1 (Decompositor Temático e Extrator de Evidências)."""

    model_config = ConfigDict(extra="ignore")
    entry_id: UUID = Field(default_factory=uuid4)
    patient_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    macro_tema_validado: MacroTema
    confianca_macro_tema: float = Field(ge=0.0, le=1.0)
    subtemas: list[SubTemaItem] = Field(min_length=1, max_length=8)
    sentimento_predominante: Sentimento
    score_polaridade: float = Field(
        ge=-1.0, le=1.0, description="Valência afetiva contínua de -1.0 a +1.0"
    )
    indicio_textual_risco: IndicioRisco
    modalidade: Literal["texto", "audio", "foto"] = "texto"
    validation: ValidationMetrics | None = None

