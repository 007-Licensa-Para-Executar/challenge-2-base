"""Integração da representação tratada ao copiloto, sem acesso ao cofre."""

import json
from pathlib import Path
from uuid import UUID

from privacy.client import PrivacyClient, PrivacyError

from .contracts import DiaryRecord, Query


def map_patient(value: str, directory: Path) -> str:
    """Aceita UUID ou alias das fixtures de demonstração."""
    try:
        patient = UUID(value)
    except ValueError:
        try:
            mapping = json.loads((directory / "demo-patients.json").read_text(encoding="utf-8"))
            patient = UUID(mapping[value])
        except (KeyError, OSError, TypeError, ValueError):
            raise PrivacyError("privacy_patient_not_registered") from None
    if patient.version != 4:
        raise PrivacyError("privacy_patient_not_registered")
    return str(patient)


def protect_diary(record: DiaryRecord, client: PrivacyClient, directory: Path) -> DiaryRecord:
    result = client.protect(
        patient_id=map_patient(record.patient_id, directory), record_id=record.record_id,
        text=record.original_text, title=record.source_title,
    )
    return DiaryRecord(
        record_id=record.record_id, patient_id=str(result.patient_id),
        recorded_at=record.recorded_at, source_title=result.title,
        treated_text=result.text, representation_id=result.representation_id,
        detector_version=result.detector_version, schema_version="2.0.0",
    )


def protect_query(query: Query, client: PrivacyClient, directory: Path) -> Query:
    result = client.protect(
        patient_id=map_patient(query.patient_id, directory), text=query.question,
    )
    return Query(
        patient_id=str(result.patient_id), question=result.text, treated=True,
        start_at=query.start_at, end_at=query.end_at,
    )
