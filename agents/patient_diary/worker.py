"""Fila de transcrição. Não registra o texto nem os bytes do áudio."""

from __future__ import annotations

import hashlib
import re
import threading

from .contracts import InvalidEntryError
from .store import PatientDiaryStore, StoreIsolationError
from .transcribe import SpeechTranscriber, TranscriptionError

_SAFE = re.compile(r"^[a-z_]{1,40}$")


class TranscriptionWorker:
    def __init__(
        self,
        store: PatientDiaryStore,
        transcriber: SpeechTranscriber,
        worker_id: str,
        *,
        max_attempts: int = 3,
        lease_seconds: float = 900,
    ):
        self.store = store
        self.transcriber = transcriber
        self.worker_id = worker_id
        self.max_attempts = max_attempts
        self.lease_seconds = lease_seconds

    def run_once(self) -> str | None:
        job = self.store.claim_next(
            self.worker_id,
            lease_seconds=self.lease_seconds,
            max_attempts=self.max_attempts,
        )
        if job is None:
            return None
        outcome = self._finish(job)
        if outcome == "claim_lost":
            return None
        if outcome != "ready":
            try:
                self.store.fail_audio(
                    job.entry_id, self.worker_id, job.claim_token, outcome, self.max_attempts
                )
            except StoreIsolationError:
                return None
        return job.entry_id

    def _finish(self, job) -> str:
        path = self.store.audio_file(job.audio_path)
        if path is None:
            return "audio_missing"
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return "audio_missing"
        if digest != job.audio_sha256:
            return "hash_mismatch"
        try:
            result = self._transcribe_while_held(job, path)
            if not self.store.renew_claim(job, self.worker_id):
                return "claim_lost"
            self.store.save_transcript(job, self.worker_id, result)
        except StoreIsolationError as exc:
            if exc.code == "claim_lost":
                return "claim_lost"
            return "transcriber_failed"
        except (TranscriptionError, InvalidEntryError) as exc:
            return exc.code if _SAFE.fullmatch(exc.code) else "transcriber_failed"
        except Exception:  # noqa: BLE001 — o texto da exceção não pode ir para o status
            return "transcriber_failed"
        return "ready"

    def _transcribe_while_held(self, job, path):
        stop = threading.Event()

        def beat() -> None:
            # Renova antes do prazo para outro worker não tomar a tarefa no meio.
            interval = max(self.lease_seconds / 3, 0.05)
            while not stop.wait(interval):
                if not self.store.renew_claim(job, self.worker_id):
                    return

        thread = threading.Thread(target=beat, name="diary-lease", daemon=True)
        thread.start()
        try:
            return self.transcriber.transcribe(path)
        finally:
            stop.set()
            thread.join(timeout=1)
