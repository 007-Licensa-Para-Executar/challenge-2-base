"""Fila de transcrição com áudio e texto sintéticos."""

import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.patient_diary import (
    AccessDeniedError,
    Actor,
    FakeTranscriber,
    FasterWhisperTranscriber,
    PatientDiaryStore,
    StoreIsolationError,
    TranscriptionError,
    TranscriptionWorker,
    parse_entry,
)
from agents.patient_diary.contracts import Segment, TranscriptResult


def actor(user_id="alice", role="patient"):
    return Actor(user_id=user_id, role=role)


def tone(seconds: float) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "tone.wav"
        subprocess.run(
            [
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
                "-c:a",
                "pcm_s16le",
                str(target),
            ],
            check=True,
            shell=False,
            timeout=30,
        )
        return target.read_bytes()


def diary_with(*clips, tmp_path, patient="alice"):
    diary = PatientDiaryStore(tmp_path / "patient_diary.sqlite3", tmp_path / "audio")
    when = datetime(2026, 11, 5, 12, tzinfo=UTC)
    ids = []
    for index, audio in enumerate(clips, start=1):
        entry_id = f"a{index}"
        diary.create_audio(
            entry_id=entry_id,
            created_at=when,
            consent_id="consent-1",
            audio=audio,
            actor=actor(patient),
            patient_id=patient,
            author_user_id=patient,
        )
        ids.append(entry_id)
    return diary, ids


def test_transcribes_one_queued_audio_and_keeps_the_written_entry(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    text = "Relato escrito que a transcrição não altera."
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
    phrase = "Nota sintética azul."
    worker = TranscriptionWorker(diary, FakeTranscriber(phrase), "worker-a")
    assert worker.run_once() == "a1"
    assert worker.run_once() is None
    saved = diary.get("a1", actor())
    assert saved.processing_status == "ready"
    assert saved.original_text is None
    assert saved.error_code is None
    transcript = diary.read_transcript("a1", actor())
    assert transcript.text == phrase
    assert transcript.language == "pt"
    assert transcript.model_name == "fake"
    assert transcript.segments[0].start_sec == 0
    assert diary.get("t1", actor()).original_text == text
    audio_dir = tmp_path / "audio"
    assert any(audio_dir.iterdir())
    with sqlite3.connect(diary.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM transcripts").fetchone() == (1,)


def test_empty_queue_missing_file_bad_hash_and_empty_transcript(tmp_path):
    diary = PatientDiaryStore(tmp_path / "db.sqlite3", tmp_path / "audio")
    idle = TranscriptionWorker(diary, FakeTranscriber(), "worker-a")
    assert idle.run_once() is None

    diary, _ids = diary_with(tone(0.3), tone(0.4), tone(0.5), tmp_path=tmp_path)
    missing = tmp_path / "audio"
    only = next(missing.iterdir())
    gone = diary.queued_audio("a1", actor()).audio_path
    (missing / gone).unlink()
    worker = TranscriptionWorker(diary, FakeTranscriber(), "worker-a", max_attempts=1)
    worker.run_once()
    assert diary.get("a1", actor()).error_code == "audio_missing"

    hashed = diary.queued_audio("a2", actor()).audio_path
    (missing / hashed).write_bytes(b"conteudo trocado")
    worker.run_once()
    changed = diary.get("a2", actor())
    assert changed.error_code == "hash_mismatch"
    assert changed.audio_sha256 != __import__("hashlib").sha256(b"conteudo trocado").hexdigest()

    empty = TranscriptionWorker(diary, FakeTranscriber(empty=True), "worker-b", max_attempts=1)
    empty.run_once()
    assert diary.get("a3", actor()).error_code == "empty_transcript"
    with sqlite3.connect(diary.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM transcripts").fetchone() == (0,)
    assert only.name


def test_failure_retries_then_stops(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    worker = TranscriptionWorker(
        diary, FakeTranscriber(fail=True), "worker-a", max_attempts=2
    )
    assert worker.run_once() == "a1"
    assert diary.get("a1", actor()).processing_status == "queued"
    assert worker.run_once() == "a1"
    failed = diary.get("a1", actor())
    assert failed.processing_status == "failed"
    assert failed.error_code == "transcriber_failed"
    assert worker.run_once() is None
    with sqlite3.connect(diary.db_path) as conn:
        assert conn.execute("SELECT attempt_count FROM patient_entries").fetchone() == (2,)
        assert conn.execute("SELECT COUNT(*) FROM transcripts").fetchone() == (0,)


def test_interrupted_claim_is_recovered(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    with sqlite3.connect(diary.db_path) as conn:
        conn.execute(
            "UPDATE patient_entries SET processing_status = 'processing', attempt_count = 1, "
            "claimed_by = 'dead', claimed_at = '2020-01-01T00:00:00.000000+00:00'"
        )
    worker = TranscriptionWorker(diary, FakeTranscriber("Retomada sintética."), "worker-a")
    assert worker.run_once() == "a1"
    assert diary.get("a1", actor()).processing_status == "ready"
    assert diary.read_transcript("a1", actor()).text == "Retomada sintética."


def test_stale_claim_at_the_attempt_limit_is_not_retried(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    with sqlite3.connect(diary.db_path) as conn:
        conn.execute(
            "UPDATE patient_entries SET processing_status = 'processing', attempt_count = 3, "
            "claimed_by = 'dead', claimed_at = '2020-01-01T00:00:00.000000+00:00'"
        )
    fake = FakeTranscriber()
    worker = TranscriptionWorker(diary, fake, "worker-a", max_attempts=3)
    assert worker.run_once() is None
    assert fake.paths == []
    assert diary.get("a1", actor()).error_code == "attempts_exhausted"


def test_two_workers_take_different_entries(tmp_path):
    diary, ids = diary_with(tone(0.3), tone(0.4), tmp_path=tmp_path)

    class Gate:
        def __init__(self):
            self.barrier = threading.Barrier(2)
            self.paths: list[str] = []

        def transcribe(self, path: Path) -> TranscriptResult:
            self.paths.append(path.name)
            self.barrier.wait(timeout=5)
            return TranscriptResult(
                text="Fila sintética.",
                language="pt",
                segments=(Segment(start_sec=0.0, end_sec=0.2, text="Fila sintética."),),
                model_name="fake",
                status="ok",
            )

    gate = Gate()
    found: list[str | None] = []

    def run(name: str) -> None:
        found.append(TranscriptionWorker(diary, gate, name).run_once())

    threads = [threading.Thread(target=run, args=(name,)) for name in ("worker-a", "worker-b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert sorted(found) == sorted(ids)
    assert len(set(gate.paths)) == 2
    assert {diary.get(entry_id, actor()).processing_status for entry_id in ids} == {"ready"}


def test_other_patient_cannot_read_the_transcript(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    phrase = "Segredo sintético da Alice."
    TranscriptionWorker(diary, FakeTranscriber(phrase), "worker-a").run_once()
    with pytest.raises(AccessDeniedError) as denied:
        diary.read_transcript("a1", actor("bob"))
    assert phrase not in str(denied.value)
    assert phrase not in repr(denied.value)


def test_faster_whisper_stays_local_and_optional(tmp_path, monkeypatch):
    missing = FasterWhisperTranscriber(tmp_path / "ausente", model_name="small")
    with pytest.raises(TranscriptionError) as unavailable:
        missing.transcribe(tmp_path / "audio.wav")
    assert unavailable.value.code == "model_unavailable"

    model_dir = tmp_path / "modelo"
    model_dir.mkdir()
    created: list[tuple] = []

    class FakeModel:
        def __init__(self, path, device, compute_type, local_files_only):
            created.append((path, device, compute_type, local_files_only))

        def transcribe(self, audio, language, initial_prompt=None):
            assert language == "pt"
            assert "Brasil" in initial_prompt
            segment = SimpleNamespace(start=0.0, end=0.4, text=" olá sintético ")
            return iter([segment]), SimpleNamespace(language="pt")

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))
    adapter = FasterWhisperTranscriber(model_dir, model_name="small")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"sintetico")
    first = adapter.transcribe(audio)
    second = adapter.transcribe(audio)
    assert created == [(str(model_dir), "cpu", "int8", True)]
    assert first.text == second.text == "olá sintético"
    assert first.language == "pt"
    assert first.model_name == "small"

    real_import = __import__("builtins").__import__

    def block(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "faster_whisper", raising=False)
    monkeypatch.setattr("builtins.__import__", block)
    fresh = FasterWhisperTranscriber(model_dir, model_name="small")
    with pytest.raises(TranscriptionError) as blocked:
        fresh.transcribe(audio)
    assert blocked.value.code == "transcriber_unavailable"


def _result(text: str) -> TranscriptResult:
    return TranscriptResult(
        text=text,
        language="pt",
        segments=(Segment(start_sec=0.0, end_sec=0.2, text=text),),
        model_name="fake",
        status="ok",
    )


def test_long_task_keeps_the_lease(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    started = threading.Event()

    class Slow:
        def transcribe(self, path: Path) -> TranscriptResult:
            started.set()
            time.sleep(1.2)
            return _result("Demorou e manteve a reserva.")

    box: dict[str, str | None] = {}

    def run() -> None:
        box["id"] = TranscriptionWorker(diary, Slow(), "worker-a", lease_seconds=0.4).run_once()

    thread = threading.Thread(target=run)
    thread.start()
    assert started.wait(timeout=5)
    time.sleep(0.7)
    assert (
        TranscriptionWorker(diary, FakeTranscriber("intruso"), "worker-b", lease_seconds=0.4).run_once()
        is None
    )
    thread.join(timeout=5)
    assert box["id"] == "a1"
    assert diary.read_transcript("a1", actor()).text == "Demorou e manteve a reserva."


def test_old_attempt_cannot_overwrite_a_newer_transcript(tmp_path):
    diary, _ids = diary_with(tone(0.3), tmp_path=tmp_path)
    first = diary.claim_next("worker-a", lease_seconds=60, max_attempts=3)
    with sqlite3.connect(diary.db_path) as conn:
        conn.execute("UPDATE patient_entries SET claimed_at = '2020-01-01T00:00:00.000000+00:00'")
    second = diary.claim_next("worker-b", lease_seconds=60, max_attempts=3)
    assert first is not None and second is not None
    assert second.claim_token != first.claim_token
    diary.save_transcript(second, "worker-b", _result("Frase nova."))
    with pytest.raises(StoreIsolationError) as lost:
        diary.save_transcript(first, "worker-a", _result("Frase velha."))
    assert lost.value.code == "claim_lost"
    with pytest.raises(StoreIsolationError):
        diary.fail_audio("a1", "worker-a", first.claim_token, "transcriber_failed", 3)
    assert diary.read_transcript("a1", actor()).text == "Frase nova."


def test_rag_sources_do_not_reference_transcription():
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
        assert "transcripts" not in source
        assert "FasterWhisper" not in source
        checked += 1
    assert checked >= 1


def test_version_two_entries_survive_the_transcript_migration(tmp_path):
    path = tmp_path / "v2.sqlite3"
    text = "Texto da versão 2 com ã."
    digest = "a" * 64
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version = 2")
        conn.execute(
            "CREATE TABLE patient_entries ("
            "entry_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
            "author_user_id TEXT NOT NULL, created_at TEXT NOT NULL, "
            "input_type TEXT NOT NULL, original_text TEXT, processing_status TEXT NOT NULL, "
            "consent_id TEXT NOT NULL, audio_path TEXT, audio_sha256 TEXT, duration_sec REAL)"
        )
        conn.execute(
            "INSERT INTO patient_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "t1",
                "alice",
                "alice",
                "2026-11-05T12:00:00.000000+00:00",
                "text",
                text,
                "ready",
                "consent-1",
                None,
                None,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO patient_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "a1",
                "alice",
                "alice",
                "2026-11-05T12:00:01.000000+00:00",
                "audio",
                None,
                "queued",
                "consent-1",
                f"{'b' * 32}.wav",
                digest,
                0.3,
            ),
        )
    diary = PatientDiaryStore(path, tmp_path / "audio")
    entries = diary.list_entries("alice", actor())
    assert entries[0].original_text == text
    assert entries[1].audio_sha256 == digest
    assert entries[1].processing_status == "queued"
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transcripts'"
        ).fetchone()
