"""Relatos escritos sintéticos em SQLite próprio, sem o RAG."""

import sqlite3
import stat
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from agents.patient_diary import (
    AccessDeniedError,
    Actor,
    EntryConflictError,
    EntryNotFoundError,
    InvalidEntryError,
    PatientDiaryStore,
    PatientEntry,
    StoreIsolationError,
    parse_entry,
)


def entry(**overrides):
    values = {
        "entry_id": "e1",
        "patient_id": "alice",
        "author_user_id": "alice",
        "created_at": datetime(2026, 11, 5, 12, tzinfo=UTC),
        "original_text": "Fiquei feliz com minha família.",
        "consent_id": "consent-1",
    }
    values.update(overrides)
    return parse_entry(**values)


def actor(user_id="alice", role="patient"):
    return Actor(user_id=user_id, role=role)


def test_stores_text_preserves_accents_and_normalizes_timezone(tmp_path):
    path = tmp_path / "área" / "patient_diary.sqlite3"
    store = PatientDiaryStore(path)
    when = datetime(2026, 11, 5, 9, tzinfo=timezone(timedelta(hours=-3)))
    text = "Ávó: coração e cuidado.\r\nSegundo parágrafo."
    stored = store.create(entry(created_at=when, original_text=text), actor())
    assert stored.original_text == text
    assert stored.processing_status == "ready"
    assert stored.input_type == "text"
    assert stored.created_at == datetime(2026, 11, 5, 12, tzinfo=UTC)
    with sqlite3.connect(path) as conn:
        raw = conn.execute("SELECT created_at, original_text FROM patient_entries").fetchone()
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert raw == ("2026-11-05T12:00:00.000000+00:00", text)
    assert tables == {"patient_entries", "care_links", "transcripts"}
    assert version == 4
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_rejects_empty_long_and_non_text_without_echoing_the_text():
    long_text = "á" * 20_001
    with pytest.raises(InvalidEntryError) as empty:
        entry(original_text=" \n\t ")
    with pytest.raises(InvalidEntryError) as blank:
        entry(original_text="")
    with pytest.raises(InvalidEntryError) as too_long:
        entry(original_text=long_text)
    with pytest.raises(InvalidEntryError) as audio:
        entry(input_type="foto")
    with pytest.raises(InvalidEntryError) as naive:
        entry(created_at=datetime(2026, 11, 5, 12))
    with pytest.raises(InvalidEntryError) as injected:
        entry(entry_id="alice' OR 1=1 --")
    assert empty.value.code == "empty_text"
    assert blank.value.code == "empty_text"
    assert too_long.value.code == "text_too_long"
    assert audio.value.code == "invalid_input_type"
    assert naive.value.code == "timezone_required"
    assert injected.value.code == "invalid_identifier"
    assert long_text not in str(too_long.value)
    assert "Fiquei feliz" not in str(audio.value)


def test_same_id_and_content_is_idempotent_and_difference_conflicts(tmp_path):
    store = PatientDiaryStore(tmp_path / "patient_diary.sqlite3")
    first = entry()
    assert store.create(first, actor()) == store.create(first, actor())
    with pytest.raises(EntryConflictError) as conflict:
        store.create(entry(original_text="Outro relato sintético."), actor())
    assert conflict.value.code == "entry_conflict"
    assert "Outro relato" not in str(conflict.value)
    assert store.get("e1", actor()).original_text == first.original_text
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM patient_entries").fetchone() == (1,)


def test_isolates_patients_and_denies_unlinked_readers(tmp_path):
    store = PatientDiaryStore(tmp_path / "patient_diary.sqlite3")
    secret = "Relato sintético só da Alice, com ã."
    store.create(entry(original_text=secret), actor())
    store.create(
        entry(
            entry_id="e2",
            patient_id="bob",
            author_user_id="bob",
            original_text="Dia do Bob.",
        ),
        actor("bob"),
    )
    store.link_clinician("psi-1", "alice")
    store.link_clinician("psi-2", "bob")
    clinician = actor("psi-1", role="clinician")
    assert [item.entry_id for item in store.list_entries("alice", actor())] == ["e1"]
    assert store.get("e1", clinician).original_text == secret
    with pytest.raises(AccessDeniedError) as denied_list:
        store.list_entries("alice", actor("psi-2", role="clinician"))
    with pytest.raises(AccessDeniedError) as denied_get:
        store.get("e1", actor("bob"))
    with pytest.raises(AccessDeniedError):
        store.create(entry(entry_id="e3", original_text="Psicólogo não escreve o diário."), clinician)
    assert denied_list.value.code == "access_denied"
    assert secret not in str(denied_get.value)
    assert store.list_entries("bob", actor("bob"))[0].entry_id == "e2"


def test_denied_create_does_not_create_the_database(tmp_path):
    path = tmp_path / "novo" / "patient_diary.sqlite3"
    clinician = actor("psi-1", role="clinician")
    with pytest.raises(AccessDeniedError):
        PatientDiaryStore(path).create(entry(), clinician)
    assert not path.exists()


def test_missing_entry_and_read_do_not_create_the_database(tmp_path):
    path = tmp_path / "ausente" / "patient_diary.sqlite3"
    store = PatientDiaryStore(path)
    assert store.list_entries("alice", actor()) == []
    with pytest.raises(EntryNotFoundError) as missing:
        store.get("e1", actor())
    assert missing.value.code == "entry_not_found"
    assert not path.parent.exists()


def test_refuses_diary_and_literature_databases_without_writing(tmp_path):
    for table in ("diary_records", "literature_documents"):
        path = tmp_path / f"{table}.sqlite3"
        with sqlite3.connect(path) as conn:
            conn.execute(f"CREATE TABLE {table} (id TEXT)")
            conn.execute(f"INSERT INTO {table} VALUES ('ficar')")
        before = path.read_bytes()
        with pytest.raises(StoreIsolationError) as blocked:
            PatientDiaryStore(path).create(entry(), actor())
        assert blocked.value.code == "foreign_database"
        assert path.read_bytes() == before


def test_read_uses_a_read_only_uri(tmp_path, monkeypatch):
    path = tmp_path / "patient_diary.sqlite3"
    store = PatientDiaryStore(path)
    store.create(entry(), actor())
    connect = sqlite3.connect
    calls = []

    def spy(database, *args, **kwargs):
        calls.append((database, kwargs))
        return connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)
    assert store.get("e1", actor()).entry_id == "e1"
    assert calls[0][0].endswith("?mode=ro")
    assert calls[0][1]["uri"] is True
    assert list(tmp_path.iterdir()) == [path]


def test_create_does_not_log_the_report(tmp_path, caplog):
    text = "Texto sintético que não pode ir para o log."
    PatientDiaryStore(tmp_path / "patient_diary.sqlite3").create(entry(original_text=text), actor())
    assert text not in caplog.text
    assert caplog.records == []


def test_client_cannot_grant_itself_another_patient(tmp_path):
    path = tmp_path / "patient_diary.sqlite3"
    store = PatientDiaryStore(path)
    secret = "Relato sintético da Alice, com acento ã."
    store.create(entry(original_text=secret), actor())
    before = path.read_bytes()
    bob = actor("bob")
    with pytest.raises(AccessDeniedError) as other_get:
        store.get("e1", bob)
    with pytest.raises(AccessDeniedError) as other_list:
        store.list_entries("alice", bob)
    with pytest.raises(AccessDeniedError):
        store.create(
            entry(entry_id="e9", patient_id="alice", author_user_id="bob"),
            bob,
        )
    with pytest.raises(InvalidEntryError) as claimed:
        Actor(user_id="bob", role="patient", patient_ids=("alice",))
    with pytest.raises(InvalidEntryError) as injected:
        store.list_entries("alice' OR 1=1 --", actor())
    with pytest.raises(AccessDeniedError) as unlinked:
        store.get("e1", actor("psi-9", role="clinician"))
    forged = Actor.model_construct(user_id="bob", role="clinician")
    with pytest.raises(AccessDeniedError):
        store.get("e1", forged)
    assert other_get.value.code == other_list.value.code == unlinked.value.code == "access_denied"
    assert claimed.value.code == "untrusted_actor"
    assert injected.value.code == "invalid_identifier"
    for error in (other_get.value, other_list.value, claimed.value, injected.value, unlinked.value):
        assert secret not in str(error)
        assert secret not in repr(error)
        assert error.__cause__ is None
        assert error.__context__ is None
    assert path.read_bytes() == before
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM patient_entries").fetchone() == (1,)
        assert conn.execute("SELECT COUNT(*) FROM care_links").fetchone() == (0,)


def test_validation_errors_do_not_carry_the_report(tmp_path):
    secret = "relato sintético sigiloso " + ("á" * 20_001)
    with pytest.raises(InvalidEntryError) as direct:
        PatientEntry(
            entry_id="e1",
            patient_id="alice",
            author_user_id="alice",
            created_at=datetime(2026, 11, 5, 12, tzinfo=UTC),
            original_text=secret,
            consent_id="consent-1",
        )
    bypassed = PatientEntry.model_construct(
        entry_id="e1",
        patient_id="alice",
        author_user_id="alice",
        created_at=datetime(2026, 11, 5, 12, tzinfo=UTC),
        input_type="text",
        original_text=secret,
        processing_status="ready",
        consent_id="consent-1",
    )
    path = tmp_path / "patient_diary.sqlite3"
    with pytest.raises(InvalidEntryError) as stored:
        PatientDiaryStore(path).create(bypassed, actor())
    assert direct.value.code == stored.value.code == "text_too_long"
    for error in (direct.value, stored.value):
        assert secret not in str(error)
        assert secret not in repr(error)
        assert error.__cause__ is None
        assert error.__context__ is None
    assert not path.exists()


def test_copilot_and_literature_do_not_reference_the_patient_diary():
    root = Path(__file__).parents[1]
    checked = 0
    for relative in (
        "app/shell.py",
        "agents/copilot/service.py",
        "agents/copilot/storage.py",
        "agents/copilot/literature.py",
    ):
        path = root / relative
        if not path.is_file():
            continue
        source = path.read_text()
        assert "patient_diary" not in source
        assert "patient_entries" not in source
        checked += 1
    assert checked >= 1
