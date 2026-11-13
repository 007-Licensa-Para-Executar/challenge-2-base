"""Áudio sintético do diário. Sem gravação de paciente e sem transcrição."""

import sqlite3
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agents.patient_diary import (
    AccessDeniedError,
    Actor,
    DuplicateAudioError,
    EntryConflictError,
    InvalidEntryError,
    PatientDiaryStore,
    StoreIsolationError,
    parse_entry,
)


def actor(user_id="alice", role="patient"):
    return Actor(user_id=user_id, role=role)


def store(tmp_path):
    return PatientDiaryStore(tmp_path / "patient_diary.sqlite3", tmp_path / "audio")


def tone(kind: str, seconds: float) -> bytes:
    suffix = {"wav": ".wav", "ogg": ".ogg", "webm": ".webm", "m4a": ".m4a", "mp3": ".mp3"}[kind]
    with tempfile.TemporaryDirectory() as directory:
        return _render(Path(directory), suffix, kind, seconds)


def _render(directory: Path, suffix: str, kind: str, seconds: float) -> bytes:
    target = directory / f"tone{suffix}"
    command = [
        "/usr/bin/ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={seconds}",
        "-ar",
        "8000",
        "-ac",
        "1",
    ]
    command += {
        "wav": ["-c:a", "pcm_s16le"],
        "ogg": ["-c:a", "libvorbis"],
        "webm": ["-c:a", "libopus", "-f", "webm"],
        "m4a": ["-c:a", "aac"],
        "mp3": ["-c:a", "libmp3lame"],
    }[kind]
    command.append(str(target))
    subprocess.run(command, check=True, shell=False, timeout=60)
    return target.read_bytes()


def save(diary, audio, entry_id="a1", user="alice", **overrides):
    values = {
        "entry_id": entry_id,
        "created_at": datetime(2026, 11, 5, 12, tzinfo=UTC),
        "consent_id": "consent-1",
        "audio": audio,
        "actor": actor(user),
        "patient_id": user,
        "author_user_id": user,
    }
    values.update(overrides)
    return diary.create_audio(**values)


def test_stores_wav_outside_sqlite_without_exposing_the_path(tmp_path):
    diary = store(tmp_path)
    text = "Relato escrito que permanece."
    diary.create(
        parse_entry(
            entry_id="t1",
            patient_id="alice",
            author_user_id="alice",
            created_at=datetime(2026, 11, 5, 11, tzinfo=UTC),
            original_text=text,
            consent_id="consent-1",
        ),
        actor(),
    )
    saved = save(diary, tone("wav", 0.3))
    assert saved.input_type == "audio"
    assert saved.processing_status == "queued"
    assert saved.original_text is None
    assert saved.duration_sec > 0
    assert "audio_path" not in saved.model_dump()
    job = diary.queued_audio("a1", actor())
    audio_file = tmp_path / "audio" / job.audio_path
    assert audio_file.is_file()
    assert stat.S_IMODE(audio_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(audio_file.parent.stat().st_mode) == 0o700
    assert job.audio_sha256 == saved.audio_sha256
    assert "/" not in job.audio_path and ".." not in job.audio_path
    with sqlite3.connect(diary.db_path) as conn:
        rows = conn.execute(
            "SELECT entry_id, original_text, audio_path FROM patient_entries ORDER BY entry_id"
        ).fetchall()
    assert rows[0] == ("a1", None, job.audio_path)
    assert rows[1] == ("t1", text, None)


@pytest.mark.parametrize("kind", ["wav", "ogg", "webm", "m4a", "mp3"])
def test_accepts_probed_formats(tmp_path, kind):
    saved = save(store(tmp_path), tone(kind, 0.3), entry_id=kind)
    assert saved.input_type == "audio"
    assert saved.audio_sha256


def test_rejects_empty_corrupt_disguised_and_limits(tmp_path):
    diary = store(tmp_path)
    secret = b"RIFF" + b"\x00" * 64
    with pytest.raises(InvalidEntryError) as empty:
        save(diary, b"")
    with pytest.raises(InvalidEntryError) as corrupt:
        save(diary, secret)
    with pytest.raises(InvalidEntryError) as disguised:
        save(diary, b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    with pytest.raises(InvalidEntryError) as huge:
        save(diary, b"\x00" * (25 * 1024 * 1024 + 1))
    with pytest.raises(InvalidEntryError) as long_audio:
        save(diary, tone("wav", 601))
    assert empty.value.code == "empty_audio"
    assert corrupt.value.code == disguised.value.code == "invalid_audio"
    assert huge.value.code == "audio_too_large"
    assert long_audio.value.code == "audio_too_long"
    assert "RIFF" not in str(corrupt.value) and "RIFF" not in repr(corrupt.value)
    assert not diary.db_path.exists()
    audio_dir = tmp_path / "audio"
    assert not audio_dir.exists() or list(audio_dir.iterdir()) == []


def test_duplicate_hash_conflict_and_idempotent_retry(tmp_path):
    diary = store(tmp_path)
    audio = tone("wav", 0.3)
    first = save(diary, audio)
    again = save(diary, audio)
    assert again == first
    assert len(list((tmp_path / "audio").iterdir())) == 1
    with pytest.raises(DuplicateAudioError) as duplicate:
        save(diary, audio, entry_id="a2")
    with pytest.raises(EntryConflictError) as conflict:
        save(diary, tone("wav", 0.5))
    other = save(diary, audio, entry_id="b1", user="bob")
    assert duplicate.value.code == "duplicate_audio"
    assert conflict.value.code == "entry_conflict"
    assert "440" not in str(conflict.value)
    assert other.patient_id == "bob"
    assert other.audio_sha256 == first.audio_sha256
    assert len(list((tmp_path / "audio").iterdir())) == 2
    with sqlite3.connect(diary.db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM patient_entries WHERE patient_id = 'alice'"
        ).fetchone()
    assert count == (1,)


def test_write_and_transaction_failures_remove_the_new_file(tmp_path, monkeypatch):
    diary = store(tmp_path)
    audio = tone("wav", 0.3)
    real_open = os_open = __import__("os").open

    def fail_audio(path, flags, mode=0o777, **kwargs):
        if str(path).endswith(".partial"):
            raise OSError("sem espaço")
        return real_open(path, flags, mode, **kwargs)

    monkeypatch.setattr("os.open", fail_audio)
    with pytest.raises(InvalidEntryError) as write_failed:
        save(diary, audio)
    assert write_failed.value.code == "audio_write_failed"
    assert "sem espaço" not in str(write_failed.value)
    monkeypatch.setattr("os.open", os_open)

    def fail_insert(self, entry, audio_path=None):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(PatientDiaryStore, "_insert", fail_insert)
    with pytest.raises(StoreIsolationError) as transaction_failed:
        save(diary, audio)
    assert transaction_failed.value.code == "write_failed"
    assert "locked" not in str(transaction_failed.value)
    assert list((tmp_path / "audio").iterdir()) == []
    assert not diary.db_path.exists() or _count(diary) == 0


def test_rejects_path_traversal_and_other_patients(tmp_path):
    diary = store(tmp_path)
    save(diary, tone("wav", 0.3))
    job = diary.queued_audio("a1", actor())
    audio_file = tmp_path / "audio" / job.audio_path
    before = audio_file.read_bytes()
    with sqlite3.connect(diary.db_path) as conn:
        conn.execute("UPDATE patient_entries SET audio_path = ?", ("../fora.wav",))
    with pytest.raises(StoreIsolationError) as escaped:
        diary.queued_audio("a1", actor())
    assert escaped.value.code == "invalid_audio_path"
    assert "fora" not in str(escaped.value)
    with sqlite3.connect(diary.db_path) as conn:
        conn.execute("UPDATE patient_entries SET audio_path = ?", (job.audio_path,))
    audio_file.unlink()
    audio_file.symlink_to("/etc/passwd")
    with pytest.raises(StoreIsolationError):
        diary.queued_audio("a1", actor())
    audio_file.unlink()
    audio_file.write_bytes(before)
    bob = actor("bob")
    with pytest.raises(AccessDeniedError) as denied:
        diary.get("a1", bob)
    with pytest.raises(AccessDeniedError):
        diary.queued_audio("a1", bob)
    with pytest.raises(AccessDeniedError):
        diary.list_entries("alice", bob)
    clinician = actor("psi-1", role="clinician")
    with pytest.raises(AccessDeniedError):
        save(diary, tone("wav", 0.4), entry_id="a9", user="alice", actor=clinician)
    diary.link_clinician("psi-1", "alice")
    visible = diary.get("a1", clinician)
    assert "audio_path" not in visible.model_dump()
    with pytest.raises(AccessDeniedError):
        diary.queued_audio("a1", clinician)
    assert denied.value.code == "access_denied"
    assert job.audio_sha256 not in str(denied.value)


def test_migrates_written_entries_and_refuses_rag_databases(tmp_path):
    legacy = tmp_path / "legacy.sqlite3"
    text = "Texto sintético com ã e coração."
    with sqlite3.connect(legacy) as conn:
        conn.execute("PRAGMA user_version = 1")
        conn.execute(
            "CREATE TABLE patient_entries ("
            "entry_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
            "author_user_id TEXT NOT NULL, created_at TEXT NOT NULL, "
            "input_type TEXT NOT NULL CHECK(input_type = 'text'), "
            "original_text TEXT NOT NULL CHECK(length(original_text) BETWEEN 1 AND 20000), "
            "processing_status TEXT NOT NULL CHECK(processing_status = 'ready'), "
            "consent_id TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO patient_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "t1",
                "alice",
                "alice",
                "2026-11-05T12:00:00.000000+00:00",
                "text",
                text,
                "ready",
                "consent-1",
            ),
        )
    diary = PatientDiaryStore(legacy, tmp_path / "audio")
    assert diary.list_entries("alice", actor())[0].original_text == text
    save(diary, tone("wav", 0.3))
    entries = diary.list_entries("alice", actor())
    assert [item.entry_id for item in entries] == ["a1", "t1"]
    assert entries[1].original_text == text
    with sqlite3.connect(legacy) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM patient_entries").fetchone() == (2,)

    foreign = tmp_path / "rag.sqlite3"
    with sqlite3.connect(foreign) as conn:
        conn.execute("CREATE TABLE literature_documents (id TEXT)")
        conn.execute("INSERT INTO literature_documents VALUES ('ficar')")
    before = foreign.read_bytes()
    with pytest.raises(StoreIsolationError) as blocked:
        PatientDiaryStore(foreign, tmp_path / "outro").create_audio(
            entry_id="a1",
            created_at=datetime(2026, 11, 5, 12, tzinfo=UTC),
            consent_id="consent-1",
            audio=tone("wav", 0.3),
            actor=actor(),
        )
    assert blocked.value.code == "foreign_database"
    assert foreign.read_bytes() == before
    assert list((tmp_path / "outro").glob("*")) == []


def _count(diary) -> int:
    if not diary.db_path.exists():
        return 0
    with sqlite3.connect(diary.db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'patient_entries'"
        ).fetchone()
        if row[0] == 0:
            return 0
        return conn.execute("SELECT COUNT(*) FROM patient_entries").fetchone()[0]
