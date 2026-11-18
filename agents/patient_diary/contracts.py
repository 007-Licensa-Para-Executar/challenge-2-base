"""Contrato do diário do paciente.

Separado de DiaryRecord: aquele modelo só aceita texto sintético do RAG.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

ID_PATTERN = r"^[A-Za-z0-9_-]{1,80}$"
TEXT_LIMIT = 20_000


class PatientDiaryError(Exception):
    """Falha do diário. A mensagem é só o código, nunca o relato."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class InvalidEntryError(PatientDiaryError):
    """Entrada rejeitada antes de gravar."""


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as exc:
            code = _invalid_code(exc)
        else:
            return
        # Fora do except para não manter o ValidationError, que carrega o relato.
        raise InvalidEntryError(code)


class PatientEntry(Contract):
    """Resposta de leitura. Não inclui o caminho do áudio."""

    entry_id: str = Field(pattern=ID_PATTERN)
    patient_id: str = Field(pattern=ID_PATTERN)
    author_user_id: str = Field(pattern=ID_PATTERN)
    created_at: AwareDatetime
    input_type: Literal["text", "audio"] = "text"
    original_text: str | None = Field(default=None, min_length=1, max_length=TEXT_LIMIT)
    processing_status: Literal["ready", "queued", "processing", "failed"] = "ready"
    consent_id: str = Field(pattern=ID_PATTERN)
    audio_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    duration_sec: float | None = Field(default=None, gt=0, le=600)
    error_code: str | None = Field(default=None, pattern=r"^[a-z_]{1,40}$")

    @model_validator(mode="after")
    def consistent(self):
        if self.input_type == "text":
            if self.processing_status != "ready" or self.error_code is not None:
                raise ValueError("invalid_status")
            if self.original_text is None or not self.original_text.strip():
                raise ValueError("empty_text")
            if self.audio_sha256 is not None or self.duration_sec is not None:
                raise ValueError("invalid_entry")
            return self
        if self.original_text is not None or self.audio_sha256 is None or self.duration_sec is None:
            raise ValueError("invalid_audio")
        return self


class ClaimedAudio(Contract):
    """Reserva interna de um áudio. Não é resposta de leitura."""

    entry_id: str = Field(pattern=ID_PATTERN)
    patient_id: str = Field(pattern=ID_PATTERN)
    audio_path: str = Field(pattern=r"^[0-9a-f]{32}\.(wav|webm|m4a|mp3|ogg)$")
    audio_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_count: int = Field(ge=1, le=5)
    claim_token: str = Field(pattern=r"^[0-9a-f]{32}$")


class QueuedAudio(Contract):
    """Pedido interno do futuro transcritor. Não é resposta pública."""

    entry_id: str = Field(pattern=ID_PATTERN)
    patient_id: str = Field(pattern=ID_PATTERN)
    input_type: Literal["audio"]
    audio_path: str = Field(pattern=r"^[0-9a-f]{32}\.(wav|webm|m4a|mp3|ogg)$")
    audio_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_sec: float = Field(gt=0, le=600)
    processing_status: Literal["queued"]


class Segment(Contract):
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0, le=600)
    text: str = Field(min_length=1, max_length=TEXT_LIMIT)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_sec <= self.start_sec or not self.text.strip():
            raise ValueError("invalid_transcript")
        return self


class TranscriptResult(Contract):
    """Saída de um transcritor. O texto não entra na mensagem de erro."""

    text: str = Field(min_length=1, max_length=TEXT_LIMIT)
    language: Literal["pt"] = "pt"
    segments: tuple[Segment, ...] = Field(min_length=1, max_length=200)
    model_name: str = Field(pattern=r"^[A-Za-z0-9._-]{1,80}$")
    status: Literal["ok"] = "ok"

    @model_validator(mode="after")
    def nonempty(self):
        if not self.text.strip():
            raise ValueError("empty_transcript")
        return self


class Transcript(Contract):
    """Transcrição gravada. Fica fora do relato e do caminho do áudio."""

    transcript_id: str = Field(pattern=ID_PATTERN)
    entry_id: str = Field(pattern=ID_PATTERN)
    language: Literal["pt"]
    text: str = Field(min_length=1, max_length=TEXT_LIMIT)
    segments: tuple[Segment, ...] = Field(min_length=1, max_length=200)
    model_name: str = Field(pattern=r"^[A-Za-z0-9._-]{1,80}$")
    created_at: AwareDatetime
    status: Literal["ready"]

    @model_validator(mode="after")
    def nonempty(self):
        if not self.text.strip():
            raise ValueError("empty_transcript")
        return self


class Actor(Contract):
    """Identidade da sessão. Não autentica e não carrega permissões declaradas pelo cliente."""

    user_id: str = Field(pattern=ID_PATTERN)
    role: Literal["patient", "clinician"]


def _invalid_code(exc: ValidationError) -> str:
    errors = exc.errors()
    if len(errors) != 1:
        return "invalid_entry"
    err = errors[0]
    loc = err["loc"]
    kind = err["type"]
    if kind == "missing":
        return "invalid_entry"
    if kind == "value_error" and err["msg"].rsplit(" ", 1)[-1] in {
        "empty_text",
        "invalid_audio",
        "invalid_status",
        "invalid_entry",
        "invalid_transcript",
        "empty_transcript",
        "audio_too_long",
    }:
        return err["msg"].rsplit(" ", 1)[-1]
    if loc == ("duration_sec",):
        return "audio_too_long"
    if loc == ("original_text",) and kind == "string_too_short":
        return "empty_text"
    if loc == ("original_text",) and kind == "string_too_long":
        return "text_too_long"
    if kind == "extra_forbidden" and loc == ("patient_ids",):
        return "untrusted_actor"
    if kind == "string_pattern_mismatch" or (
        kind == "value_error" and err["msg"].endswith("invalid_identifier")
    ):
        return "invalid_identifier"
    if loc == ("created_at",):
        return "timezone_required"
    if loc == ("input_type",):
        return "invalid_input_type"
    if loc == ("processing_status",):
        return "invalid_status"
    if loc == ("role",) or kind == "invalid_actor":
        return "invalid_actor"
    return "invalid_entry"


def parse_entry(**kwargs: object) -> PatientEntry:
    """Valida texto não confiável. A exceção resultante só contém o código."""
    if "patient_ids" in kwargs:
        raise InvalidEntryError("untrusted_actor")
    return PatientEntry(**kwargs)  # type: ignore[arg-type]


def parse_actor(actor: Actor) -> Actor:
    if type(actor) is not Actor:
        raise InvalidEntryError("invalid_actor")
    return Actor(user_id=actor.user_id, role=actor.role)
