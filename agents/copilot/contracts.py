"""Contrato independente entre classificação temática, armazenamento e recuperação."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ThemePrediction(Contract):
    status: Literal["ok", "error", "not_requested"]
    primary_theme: str | None = None
    candidate_theme: str | None = None
    candidate_score: float | None = Field(default=None, ge=0, le=1)
    abstention_reason: str | None = None
    error_code: str | None = None
    model_version: str | None = None
    score_semantics: Literal["uncalibrated_softmax"] = "uncalibrated_softmax"

    @model_validator(mode="after")
    def consistent(self):
        if self.status == "ok" and (not self.primary_theme or self.error_code):
            raise ValueError("Classificação válida exige tema e nenhum erro")
        if self.status == "error" and (not self.error_code or self.primary_theme is not None):
            raise ValueError("Falha exige código de erro e nenhum tema inventado")
        if self.status == "not_requested" and any(
            v is not None
            for v in (
                self.primary_theme,
                self.candidate_theme,
                self.candidate_score,
                self.abstention_reason,
                self.error_code,
                self.model_version,
            )
        ):
            raise ValueError("Classificação não solicitada não contém previsões")
        return self


class DiaryRecord(Contract):
    record_id: str = Field(default_factory=lambda: uuid4().hex, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    patient_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    recorded_at: AwareDatetime
    original_text: str = Field(min_length=1, max_length=20000)
    source_title: str = Field(default="Diário sintético", min_length=1, max_length=200)
    classification: ThemePrediction = Field(
        default_factory=lambda: ThemePrediction(status="not_requested")
    )
    synthetic: Literal[True] = True
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION

    @model_validator(mode="after")
    def nonempty_text(self):
        if not self.original_text.strip():
            raise ValueError("Texto não pode ser composto apenas por espaços")
        return self


class Query(Contract):
    patient_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    question: str = Field(min_length=1, max_length=2000)
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def valid_window(self):
        if not self.question.strip():
            raise ValueError("Pergunta vazia")
        if self.start_at and self.end_at and self.start_at > self.end_at:
            raise ValueError("Início do período posterior ao fim")
        return self


class Evidence(Contract):
    chunk_id: str
    record_id: str
    patient_id: str
    recorded_at: AwareDatetime
    source_title: str
    quote: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=1)
    score: float = Field(ge=0)

    @model_validator(mode="after")
    def valid_span(self):
        if self.end_char <= self.start_char or len(self.quote) != self.end_char - self.start_char:
            raise ValueError("Intervalo da evidência inválido")
        return self


class Statement(Contract):
    text: str = Field(min_length=1, max_length=1200)
    evidence_ids: list[str] = Field(min_length=1, max_length=5)


class DraftAnswer(Contract):
    # Empty is a valid model-level abstention; service must not label it a response.
    statements: list[Statement] = Field(max_length=5)


class CopilotAnswer(Contract):
    status: Literal["ok", "insufficient_evidence", "error"]
    patient_id: str
    question: str
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    answer: str
    evidence: list[Evidence] = Field(default_factory=list)
    eligible_records: int = Field(default=0, ge=0)
    theme_counts: dict[str, int] = Field(default_factory=dict)
    generation_mode: Literal["extractive", "ollama"]
    retriever: Literal["bm25", "e5"]
    model: str | None = None
    error_code: str | None = None
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    synthetic: Literal[True] = True
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION

    @model_validator(mode="after")
    def consistent(self):
        if self.status == "ok" and (not self.evidence or self.error_code):
            raise ValueError("Resposta exige evidências e nenhum erro")
        if self.status == "error" and not self.error_code:
            raise ValueError("Erro exige código operacional")
        if self.status != "error" and self.error_code:
            raise ValueError("Código operacional reservado a falhas")
        if self.status == "insufficient_evidence" and self.evidence:
            raise ValueError("Insuficiência não deve apresentar evidência como resposta")
        return self
