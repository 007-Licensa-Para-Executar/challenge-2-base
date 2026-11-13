"""Diário do paciente, fora do RAG de relatos sintéticos e da literatura."""

from .contracts import Actor, InvalidEntryError, PatientEntry, QueuedAudio, Transcript, parse_entry
from .store import (
    AccessDeniedError,
    DuplicateAudioError,
    EntryConflictError,
    EntryNotFoundError,
    PatientDiaryStore,
    StoreIsolationError,
)
from .transcribe import FakeTranscriber, FasterWhisperTranscriber, TranscriptionError
from .worker import TranscriptionWorker

__all__ = [
    "AccessDeniedError",
    "Actor",
    "DuplicateAudioError",
    "EntryConflictError",
    "EntryNotFoundError",
    "FakeTranscriber",
    "FasterWhisperTranscriber",
    "InvalidEntryError",
    "PatientDiaryStore",
    "PatientEntry",
    "QueuedAudio",
    "StoreIsolationError",
    "Transcript",
    "TranscriptionError",
    "TranscriptionWorker",
    "parse_entry",
]
