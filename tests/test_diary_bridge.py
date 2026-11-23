"""Ponte do diário fictício. O preditor falso não mede acurácia da rede.

Não abre a rede real, não baixa peso e não mistura os bancos.
"""

import math
import sqlite3
import struct
import wave
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace

import pytest

from agents.copilot.contracts import DiaryRecord
from agents.copilot.storage import DiaryStore
from agents.diary_bridge.project import SYNTHETIC_FIXTURES, consult, project_entry
from agents.patient_diary.contracts import Actor, Segment, TranscriptResult, parse_entry
from agents.patient_diary.local_app import LOCAL_USER
from agents.patient_diary.store import PatientDiaryStore

WRITTEN = "Relato fictício sobre sono curto."
AUTOMATIC = "transcricao-automatica-nao-confirmada"
REVISED_OLD = "jardim antigo alfa"
REVISED_NEW = "jardim novo beta"
WHEN = datetime(2026, 11, 18, 12, tzinfo=UTC)
assert {WRITTEN, REVISED_OLD, REVISED_NEW} <= SYNTHETIC_FIXTURES


@pytest.fixture(autouse=True)
def _demo_switch(monkeypatch):
    monkeypatch.setenv("DIARY_BRIDGE_DEMO", "1")


def test_written_synthetic_text_is_projected_and_retrieved(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    projected = project_entry(diary, rag, "t1", _patient(), predictor=_theme(seen))
    assert projected.status == "stored"
    assert projected.code == "projected"
    assert projected.primary_theme == "saude_sono"
    assert projected.version == "w"
    assert projected.recorded_at == WHEN
    assert projected.record_id == "e2xt1vw"
    assert seen == [WRITTEN]
    answer = consult(diary, rag, _patient(), "sono")
    assert answer.clinical_use is False
    assert answer.status == "ok"
    assert WRITTEN in answer.evidence_quotes
    assert _rows(rag) == 1
    assert not _has_table(diary, "diary_records")


def test_reviewed_audio_uses_the_revision_not_the_automatic_transcript(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _revise(diary, REVISED_OLD)
    projected = project_entry(diary, rag, "a1", _patient(), predictor=_theme(seen))
    assert projected.status == "stored"
    assert projected.text_source == "reviewed_transcript"
    assert projected.version == "r1"
    assert projected.recorded_at == WHEN
    assert seen == [REVISED_OLD]
    assert AUTOMATIC.encode() not in rag.db_path.read_bytes()
    assert b"audio_path" not in rag.db_path.read_bytes()


def test_unreviewed_audio_is_blocked_before_classification_or_storage(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _audio(diary)
    projected = project_entry(diary, rag, "a1", _patient(), predictor=_theme(seen))
    assert projected.status == "blocked"
    assert projected.code == "unreviewed"
    assert seen == []
    assert not rag.db_path.exists()
    assert _rows(diary, "transcripts") == 1


def test_new_revision_selects_the_latest_text_and_keeps_the_previous_row(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _revise(diary, REVISED_OLD)
    project_entry(diary, rag, "a1", _patient(), predictor=_theme(seen))
    diary.add_revision("a1", REVISED_NEW, _clinician())
    again = project_entry(diary, rag, "a1", _patient(), predictor=_theme(seen))
    assert again.version == "r2"
    assert again.recorded_at == WHEN
    assert again.recorded_at != diary.latest_revision("a1", _patient()).created_at
    assert _rows(rag) == 2
    assert [item.revision_number for item in diary.list_revisions("a1", _patient())] == [1, 2]
    answer = consult(diary, rag, _patient(), "jardim")
    assert any("beta" in quote for quote in answer.evidence_quotes)
    assert all("alfa" not in quote for quote in answer.evidence_quotes)
    assert "alfa" not in answer.answer


def test_missing_classifier_stores_the_existing_error_without_a_theme(tmp_path):
    diary, rag, _seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    projected = project_entry(diary, rag, "t1", _patient(), predictor=_missing())
    assert projected.status == "stored"
    assert projected.code == "classification_model_unavailable"
    assert projected.primary_theme is None
    assert projected.classification_status == "error"
    assert _rows(rag) == 1


def test_unauthorized_actor_is_blocked_and_nothing_is_written(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    stranger = Actor(user_id="outra-pessoa", role="patient")
    projected = project_entry(diary, rag, "t1", stranger, predictor=_theme(seen))
    assert projected.status == "blocked"
    assert projected.code == "access_denied"
    assert seen == []
    assert not rag.db_path.exists()


def test_projecting_the_same_version_again_does_not_duplicate(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    predictor = _theme(seen)
    first = project_entry(diary, rag, "t1", _patient(), predictor=predictor)
    second = project_entry(diary, rag, "t1", _patient(), predictor=predictor)
    assert first.status == "stored"
    assert second.status == "unchanged"
    assert second.record_id == first.record_id
    assert seen == [WRITTEN]
    assert _rows(rag) == 1


def test_diary_database_is_not_reused_as_the_rag_database(tmp_path):
    diary, _rag, seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    shared = DiaryStore(diary.db_path)
    projected = project_entry(diary, shared, "t1", _patient(), predictor=_theme(seen))
    assert projected.status == "blocked"
    assert projected.code == "shared_database"
    assert seen == []
    assert not _has_table(diary, "diary_records")
    assert _rows(diary, "patient_entries") == 1


def test_demo_identity_with_unknown_text_is_not_treated_as_synthetic(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _write(diary, "t9", "Texto fora do catálogo, mesmo no paciente de demonstração.")
    projected = project_entry(diary, rag, "t9", _patient(), predictor=_theme(seen))
    assert projected.status == "blocked"
    assert projected.code == "unproven_synthetic"
    assert seen == []
    assert not rag.db_path.exists()


def test_known_fixture_stays_blocked_when_the_demo_switch_is_off(tmp_path, monkeypatch):
    monkeypatch.delenv("DIARY_BRIDGE_DEMO", raising=False)
    diary, rag, seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    projected = project_entry(diary, rag, "t1", _patient(), predictor=_theme(seen))
    answer = consult(diary, rag, _patient(), "sono")
    assert projected.code == "demo_disabled"
    assert answer.code == "demo_disabled"
    assert seen == []
    assert not rag.db_path.exists()


def test_synthetic_flag_alone_does_not_publish_an_unknown_sentence(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    _write(diary, "t1", WRITTEN)
    project_entry(diary, rag, "t1", _patient(), predictor=_theme(seen))
    rag.save(
        DiaryRecord(
            record_id="e2xz9vw",
            patient_id=LOCAL_USER,
            recorded_at=WHEN,
            original_text="Frase ausente do catálogo de demonstração.",
            source_title="patient_diary:z9:w",
        )
    )
    answer = consult(diary, rag, _patient(), "catalogo")
    assert answer.evidence_quotes == ()
    assert "ausente" not in answer.answer


def test_other_patient_cannot_be_promoted_by_the_synthetic_flag(tmp_path):
    diary, rag, seen = _pair(tmp_path)
    other = Actor(user_id="alice", role="patient")
    diary.create(
        parse_entry(
            entry_id="t1",
            patient_id="alice",
            author_user_id="alice",
            created_at=WHEN,
            original_text=WRITTEN,
            consent_id="consent-1",
        ),
        other,
    )
    projected = project_entry(diary, rag, "t1", other, predictor=_theme(seen))
    assert projected.status == "blocked"
    assert projected.code == "unproven_synthetic"
    assert seen == []
    assert not rag.db_path.exists()


def _pair(tmp_path):
    diary = PatientDiaryStore(tmp_path / "diary.sqlite3", tmp_path / "audio")
    return diary, DiaryStore(tmp_path / "rag.sqlite3"), []


def _patient() -> Actor:
    return Actor(user_id=LOCAL_USER, role="patient")


def _clinician() -> Actor:
    return Actor(user_id="psi-1", role="clinician")


def _write(diary: PatientDiaryStore, entry_id: str, text: str) -> None:
    diary.create(
        parse_entry(
            entry_id=entry_id,
            patient_id=LOCAL_USER,
            author_user_id=LOCAL_USER,
            created_at=WHEN,
            original_text=text,
            consent_id="consent-1",
        ),
        _patient(),
    )


def _audio(diary: PatientDiaryStore) -> None:
    diary.create_audio(
        entry_id="a1",
        created_at=WHEN,
        consent_id="consent-1",
        audio=_wav(),
        actor=_patient(),
    )
    job = diary.claim_next("worker-local", lease_seconds=30, max_attempts=3)
    diary.save_transcript(
        job,
        "worker-local",
        TranscriptResult(
            text=AUTOMATIC,
            language="pt",
            segments=(Segment(start_sec=0.0, end_sec=0.2, text=AUTOMATIC),),
            model_name="fake",
        ),
    )
    diary.link_clinician("psi-1", LOCAL_USER)


def _revise(diary: PatientDiaryStore, text: str) -> None:
    _audio(diary)
    diary.add_revision("a1", text, _clinician())


def _theme(seen: list[str]):
    class Predictor:
        def predict_text(self, text, threshold=0.50):
            seen.append(text)
            return SimpleNamespace(
                primary_theme="saude_sono",
                candidate_theme="saude_sono",
                confidence=0.8,
                abstention_reason=None,
            )

    return Predictor()


def _missing():
    class Predictor:
        def predict_text(self, text, threshold=0.50):
            raise FileNotFoundError("modelo ausente")

    return Predictor()


def _rows(store, table="diary_records") -> int:
    path = store.db_path
    if not path.is_file() or not _has_table(store, table):
        return 0
    with sqlite3.connect(path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _has_table(store, table: str) -> bool:
    if not store.db_path.is_file():
        return False
    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
    return row is not None


def _wav() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        frames = (
            struct.pack("<h", int(8000 * math.sin(index / 8))) for index in range(1600)
        )
        handle.writeframes(b"".join(frames))
    return buffer.getvalue()
