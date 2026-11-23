"""Contratos e caminhos compartilhados na integração HTTP local."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "privacy"
DEFAULT_URL = "http://127.0.0.1:8001"
RecordId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")]


class Wire(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProtectRequest(Wire):
    patient_id: UUID4
    record_id: RecordId | None = None
    text: str = Field(min_length=1, max_length=20000)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    synthetic: Literal[True]

    @field_validator("text", "title")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("empty_text")
        return value


class ProtectedText(Wire):
    patient_id: UUID4
    record_id: RecordId | None
    text: str = Field(min_length=1, max_length=200000)
    title: str | None = Field(default=None, min_length=1, max_length=4096)
    representation_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    detector_version: str = Field(min_length=1, max_length=512)
    schema_version: Literal["1"]


class PatientRegistration(Wire):
    patient_key: RecordId
    display_name: str = Field(min_length=1, max_length=200)
    synthetic: Literal[True]
