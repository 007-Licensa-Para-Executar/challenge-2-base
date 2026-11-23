"""Revisão interna da transcrição. Não abre rota HTTP nem banco do RAG."""

import math
import sqlite3
import struct
import wave
from datetime import UTC, datetime
from io import BytesIO

import pytest

from agents.patient_diary.contracts import Actor, Segment, TranscriptResult, parse_entry
from agents.patient_diary.store import (
    AccessDeniedError,
    InvalidEntryError,
    PatientDiaryStore,
    StoreIsolationError,
)


def test_revision_keeps_the_automatic_text_and_returns_the_latest(tmp_path):
    store = _ready(tmp_path)
    original = store.read_transcript("a1", _patient()).text
    audio_path = _column(store, "audio_path")
    digest = _column(store, "audio_sha256")
    pending = store.theme_source("a1", _clinician())
    assert pending.review_status == "unreviewed"
    assert pending.text is None
    assert original not in (pending.text or "")
    assert store.latest_revision("a1", _clinician()) is None
    first = store.add_revision("a1", "  Não tomou o remédio. ", _clinician())
    second = store.add_revision("a1", "Não tomou o remédio e não relatou falta de ar.", _clinician())
    assert store.read_transcript("a1", _patient()).text == original
    assert _column(store, "audio_path") == audio_path
    assert _column(store, "audio_sha256") == digest
    assert _column(store, "original_text") is None
    history = store.list_revisions("a1", _patient())
    assert [item.revision_number for item in history] == [1, 2]
    assert history[0].revised_text == "Não tomou o remédio."
    assert history[0].reviewer_user_id == "psi-1"
    assert history[1] == second
    assert first.reviewer_user_id == "psi-1"
    latest = store.latest_revision("a1", _clinician())
    assert latest is not None
    assert latest.revision_id == second.revision_id
    source = store.theme_source("a1", _clinician())
    assert source.text == second.revised_text
    assert source.text_source == "reviewed_transcript"
    assert source.review_status == "reviewed"
    assert source.patient_id == "alice"
    assert source.input_type == "audio"
    assert source.text != original


def test_revision_rejects_empty_forged_author_and_another_patient(tmp_path):
    store = _ready(tmp_path)
    with pytest.raises(InvalidEntryError) as empty:
        store.add_revision("a1", "   ", _clinician())
    assert empty.value.code == "empty_text"
    with pytest.raises(InvalidEntryError) as forged:
        store.add_revision("a1", "Correção.", _clinician(), reviewer_user_id="outra-pessoa")
    assert forged.value.code == "untrusted_actor"
    with pytest.raises(AccessDeniedError):
        store.add_revision("a1", "Correção.", _patient())
    with pytest.raises(AccessDeniedError):
        store.add_revision("a1", "Correção.", Actor(user_id="psi-2", role="clinician"))
    store.create_audio(
        entry_id="b1",
        created_at=datetime(2026, 11, 18, 2, tzinfo=UTC),
        consent_id="consent-1",
        audio=_wav(0.3),
        actor=Actor(user_id="bob", role="patient"),
    )
    store.link_clinician("psi-2", "bob")
    with pytest.raises(AccessDeniedError):
        store.add_revision("b1", "Correção.", _clinician())
    assert store.list_revisions("a1", _clinician()) == []


def test_written_entry_and_rag_database_stay_untouched(tmp_path):
    store = _ready(tmp_path)
    written = "Relato fictício que não é transcrição."
    store.create(
        parse_entry(
            entry_id="t1",
            patient_id="alice",
            author_user_id="alice",
            created_at=datetime(2026, 11, 18, 1, tzinfo=UTC),
            original_text=written,
            consent_id="consent-1",
        ),
        _patient(),
    )
    with pytest.raises(InvalidEntryError) as rejected:
        store.add_revision("t1", "Texto trocado.", _clinician())
    assert rejected.value.code == "invalid_entry"
    assert store.get("t1", _patient()).original_text == written
    source = store.theme_source("t1", _patient())
    assert source.text == written
    assert source.text_source == "written"
    assert source.review_status == "not_required"
    foreign = tmp_path / "rag.sqlite3"
    with sqlite3.connect(foreign) as conn:
        conn.execute("CREATE TABLE literature_documents (id TEXT)")
        conn.execute("INSERT INTO literature_documents VALUES ('ficar')")
        conn.execute("CREATE TABLE diary_records (id TEXT)")
    before = foreign.read_bytes()
    with pytest.raises(StoreIsolationError):
        PatientDiaryStore(foreign).create(
            parse_entry(
                entry_id="x",
                patient_id="alice",
                author_user_id="alice",
                created_at=datetime(2026, 11, 18, tzinfo=UTC),
                original_text="não entra",
                consent_id="consent-1",
            ),
            _patient(),
        )
    assert foreign.read_bytes() == before


def _ready(tmp_path):
    store = PatientDiaryStore(tmp_path / "diary.sqlite3", tmp_path / "audio")
    store.create_audio(
        entry_id="a1",
        created_at=datetime(2026, 11, 18, tzinfo=UTC),
        consent_id="consent-1",
        audio=_wav(0.2),
        actor=_patient(),
    )
    job = store.claim_next("worker-local", lease_seconds=30, max_attempts=3)
    store.save_transcript(
        job,
        "worker-local",
        TranscriptResult(
            text="nao tomou o remedio",
            language="pt",
            segments=(Segment(start_sec=0.0, end_sec=0.2, text="nao tomou o remedio"),),
            model_name="fake",
        ),
    )
    store.link_clinician("psi-1", "alice")
    return store


def _patient() -> Actor:
    return Actor(user_id="alice", role="patient")


def _clinician() -> Actor:
    return Actor(user_id="psi-1", role="clinician")


def _column(store: PatientDiaryStore, name: str):
    with sqlite3.connect(store.db_path) as conn:
        return conn.execute(f"SELECT {name} FROM patient_entries WHERE entry_id = 'a1'").fetchone()[0]


def _wav(seconds: float) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        frames = (
            struct.pack("<h", int(8000 * math.sin(index / 8))) for index in range(int(8000 * seconds))
        )
        handle.writeframes(b"".join(frames))
    return buffer.getvalue()
