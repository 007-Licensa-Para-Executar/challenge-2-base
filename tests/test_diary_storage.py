"""Patient/time boundaries and original-preserving SQLite operations."""

import sqlite3
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.storage import DiaryStore, DuplicateRecordError


def record(identifier="d1", patient="alice", when=None, text="Fiquei feliz com minha família."):
    return DiaryRecord(
        record_id=identifier,
        patient_id=patient,
        original_text=text,
        recorded_at=when or datetime(2026, 11, 5, 12, tzinfo=UTC),
    )


def test_query_does_not_create_missing_database_or_directory(tmp_path):
    path = tmp_path / "não existe" / "dados.sqlite3"
    assert DiaryStore(path).list_records(Query(patient_id="alice", question="família")) == []
    assert not path.parent.exists()


def test_separates_patients_and_keeps_stable_time_id_order(tmp_path):
    store = DiaryStore(tmp_path / "dados.sqlite3")
    for item in [record("z"), record("x", "bob"), record("a")]:
        store.save(item)
    items = store.list_records(Query(patient_id="alice", question="família"))
    assert [item.record_id for item in items] == ["a", "z"]
    assert all(item.patient_id == "alice" for item in items)


def test_inclusive_window_normalizes_offsets_and_preserves_original(tmp_path):
    store = DiaryStore(tmp_path / "área com espaços" / "diários.sqlite3")
    utc = datetime(2026, 11, 5, 12, tzinfo=UTC)
    offset = timezone(timedelta(hours=-3))
    same_instant = utc.astimezone(offset)
    item = record(when=same_instant, text="Ávó: coração e cuidado.\r\nSegundo parágrafo.")
    store.save(item)
    store.save(record("old", when=utc - timedelta(microseconds=1)))
    store.save(record("new", when=utc + timedelta(microseconds=1)))
    found = store.list_records(Query(patient_id="alice", question="avó", start_at=utc, end_at=utc))
    assert found == [item]
    assert found[0].original_text == item.original_text


def test_empty_window_does_not_borrow_older_records(tmp_path):
    store = DiaryStore(tmp_path / "dados.sqlite3")
    store.save(record())
    assert (
        store.list_records(
            Query(
                patient_id="alice", question="família", start_at=datetime(2026, 12, 1, tzinfo=UTC)
            )
        )
        == []
    )


def test_preserves_legacy_table_and_does_not_migrate_on_read(tmp_path):
    path = tmp_path / "dados.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE runs (id TEXT)")
        conn.execute("INSERT INTO runs VALUES ('legacy')")
    store = DiaryStore(path)
    original_bytes = path.read_bytes()
    assert store.list_records(Query(patient_id="alice", question="família")) == []
    assert path.read_bytes() == original_bytes
    store.save(record())
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT id FROM runs").fetchall() == [("legacy",)]


def test_duplicate_identifier_never_overwrites_even_across_patients(tmp_path):
    store = DiaryStore(tmp_path / "dados.sqlite3")
    item = record()
    store.save(item)
    with pytest.raises(DuplicateRecordError):
        store.save(record(patient="bob", text="Outro conteúdo"))
    assert store.list_records(Query(patient_id="alice", question="família")) == [item]
    assert store.list_records(Query(patient_id="bob", question="família")) == []


def test_read_connection_is_read_only_and_does_not_create_sidecars(tmp_path, monkeypatch):
    path = tmp_path / "dados.sqlite3"
    store = DiaryStore(path)
    store.save(record())
    connect = sqlite3.connect
    calls = []

    def spy(database, *args, **kwargs):
        calls.append((database, kwargs))
        return connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)
    assert len(store.list_records(Query(patient_id="alice", question="família"))) == 1
    assert calls[0][0].endswith("?mode=ro")
    assert calls[0][1]["uri"] is True
    assert list(tmp_path.iterdir()) == [path]


def test_sql_uses_parameters_even_if_a_caller_bypasses_validation(tmp_path):
    store = DiaryStore(tmp_path / "dados.sqlite3")
    store.save(record())
    query = Query.model_construct(patient_id="alice' OR 1=1 --", question="família")
    assert store.list_records(query) == []


def test_rejects_naive_or_inverted_dates_and_unsafe_identifier():
    with pytest.raises(ValidationError):
        record(when=datetime(2026, 11, 1))
    with pytest.raises(ValidationError):
        Query(patient_id="alice' OR 1=1 --", question="família")
    with pytest.raises(ValidationError):
        Query(
            patient_id="alice",
            question="família",
            start_at=datetime(2026, 11, 2, tzinfo=UTC),
            end_at=datetime(2026, 11, 1, tzinfo=UTC),
        )


def test_corrupted_payload_cannot_escape_patient_scope(tmp_path):
    path = tmp_path / "dados.sqlite3"
    store = DiaryStore(path)
    store.save(record())
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE diary_records SET record_json = ?", (record(patient="bob").model_dump_json(),)
        )
    with pytest.raises(ValueError, match="inconsistentes"):
        store.list_records(Query(patient_id="alice", question="família"))
