"""SQLite do diário do paciente. Não abre diary_records nem literature_documents."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .audio import MAX_BYTES, probe_audio
from .contracts import (
    ID_PATTERN,
    Actor,
    ClaimedAudio,
    InvalidEntryError,
    PatientDiaryError,
    PatientEntry,
    QueuedAudio,
    Segment,
    Transcript,
    TranscriptResult,
    parse_actor,
    parse_entry,
)

_ID = re.compile(ID_PATTERN)
_AUDIO_NAME = re.compile(r"^[0-9a-f]{32}\.(wav|webm|m4a|mp3|ogg)$")
# shortcut: version 4 adds a claim token; human correction of transcripts is a later migration
SCHEMA_VERSION = 4
_FORBIDDEN = frozenset({"diary_records", "literature_documents"})
_ALLOWED = frozenset({"patient_entries", "care_links", "transcripts"})
_COLUMNS = (
    "entry_id, patient_id, author_user_id, created_at, input_type, "
    "original_text, processing_status, consent_id, audio_sha256, duration_sec, error_code"
)
_SAFE_CODE = re.compile(r"^[a-z_]{1,40}$")


class AccessDeniedError(PatientDiaryError):
    def __init__(self):
        super().__init__("access_denied")


class EntryConflictError(PatientDiaryError):
    def __init__(self):
        super().__init__("entry_conflict")


class EntryNotFoundError(PatientDiaryError):
    def __init__(self):
        super().__init__("entry_not_found")


class StoreIsolationError(PatientDiaryError):
    def __init__(self, code: str = "foreign_database"):
        super().__init__(code)


class DuplicateAudioError(PatientDiaryError):
    def __init__(self):
        super().__init__("duplicate_audio")


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _same(stored: PatientEntry, entry: PatientEntry) -> bool:
    return (
        stored.entry_id == entry.entry_id
        and stored.patient_id == entry.patient_id
        and stored.author_user_id == entry.author_user_id
        and _timestamp(stored.created_at) == _timestamp(entry.created_at)
        and stored.input_type == entry.input_type
        and stored.original_text == entry.original_text
        and stored.processing_status == entry.processing_status
        and stored.consent_id == entry.consent_id
        and stored.audio_sha256 == entry.audio_sha256
        and stored.duration_sec == entry.duration_sec
        and stored.error_code == entry.error_code
    )


class PatientDiaryStore:
    """Grava relatos escritos. O caminho vem de quem chama; o menu do copiloto não usa este store.

    O acesso usa o user_id da sessão. patient_id do relato não concede permissão.
    O vínculo do psicólogo fica em care_links e não vem do cliente.
    Este módulo não autentica: trocar o user_id da sessão está fora daqui.
    """

    def __init__(self, db_path: str | Path, audio_dir: str | Path | None = None):
        self.db_path = Path(db_path).expanduser()
        self.audio_dir = None if audio_dir is None else Path(audio_dir).expanduser()

    def create(self, entry: PatientEntry, actor: Actor) -> PatientEntry:
        if type(entry) is not PatientEntry:
            raise InvalidEntryError("invalid_entry")
        entry = parse_entry(**entry.model_dump())
        actor = parse_actor(actor)
        names, version = self._inspect()
        self._reject_foreign(names, version)
        existing = self._fetch(entry.entry_id) if "patient_entries" in names else None
        if existing is not None:
            return self._replay(existing, entry, actor)
        self._authorize_create(entry, actor)
        self._ensure_schema()
        try:
            self._insert(entry)
        except sqlite3.IntegrityError:
            existing = self._fetch(entry.entry_id)
            if existing is None:
                raise StoreIsolationError("write_failed") from None
            return self._replay(existing, entry, actor)
        stored = self._fetch(entry.entry_id)
        if stored is None or not _same(stored, entry):
            raise StoreIsolationError("write_failed")
        return stored

    def create_audio(
        self,
        *,
        entry_id: str,
        created_at: datetime,
        consent_id: str,
        audio: bytes,
        actor: Actor,
        patient_id: str | None = None,
        author_user_id: str | None = None,
    ) -> PatientEntry:
        """Grava áudio fora do SQLite. O caminho é gerado aqui e não vem do cliente."""
        actor = parse_actor(actor)
        self._identifier(entry_id)
        self._identifier(consent_id)
        patient_id = actor.user_id if patient_id is None else patient_id
        author_user_id = actor.user_id if author_user_id is None else author_user_id
        self._identifier(patient_id)
        self._identifier(author_user_id)
        if (
            actor.role != "patient"
            or patient_id != actor.user_id
            or author_user_id != actor.user_id
        ):
            raise AccessDeniedError()
        if not isinstance(created_at, datetime) or created_at.tzinfo is None:
            raise InvalidEntryError("timezone_required")
        if not isinstance(audio, bytes):
            raise InvalidEntryError("invalid_audio")
        if len(audio) == 0:
            raise InvalidEntryError("empty_audio")
        if len(audio) > MAX_BYTES:
            raise InvalidEntryError("audio_too_large")
        if self.audio_dir is None:
            raise InvalidEntryError("audio_directory_required")
        digest = hashlib.sha256(audio).hexdigest()
        names, _version = self._inspect()
        self._reject_foreign(names, _version)
        if names:
            self._migrate_if_needed()
            existing = self._fetch(entry_id)
            if existing is not None:
                return self._replay_audio(existing, actor, digest, created_at, consent_id)
            if self._hash_owner(actor.user_id, digest) is not None:
                raise DuplicateAudioError()
        relative, duration = self._store_file(audio)
        try:
            entry = parse_entry(
                entry_id=entry_id,
                patient_id=actor.user_id,
                author_user_id=actor.user_id,
                created_at=created_at,
                input_type="audio",
                processing_status="queued",
                consent_id=consent_id,
                audio_sha256=digest,
                duration_sec=duration,
            )
            self._ensure_schema()
            self._insert(entry, audio_path=relative)
        except sqlite3.IntegrityError:
            self._unlink_audio(relative)
            existing = self._fetch(entry_id)
            if existing is not None:
                return self._replay_audio(existing, actor, digest, created_at, consent_id)
            raise DuplicateAudioError() from None
        except sqlite3.Error:
            self._unlink_audio(relative)
            raise StoreIsolationError("write_failed") from None
        except Exception:
            self._unlink_audio(relative)
            raise
        stored = self._fetch(entry_id)
        if stored is None or not _same(stored, entry):
            raise StoreIsolationError("write_failed")
        return stored

    def queued_audio(self, entry_id: str, actor: Actor) -> QueuedAudio:
        """Contrato interno do worker. A leitura pública continua em get e list_entries."""
        actor = parse_actor(actor)
        entry = self.get(entry_id, actor)
        if (
            entry.input_type != "audio"
            or entry.processing_status != "queued"
            or actor.role != "patient"
            or actor.user_id != entry.author_user_id
        ):
            raise AccessDeniedError()
        relative = self._stored_audio_path(entry_id)
        if not self._safe_audio_file(relative):
            raise StoreIsolationError("invalid_audio_path")
        return QueuedAudio(
            entry_id=entry.entry_id,
            patient_id=entry.patient_id,
            input_type="audio",
            audio_path=relative,
            audio_sha256=entry.audio_sha256,
            duration_sec=entry.duration_sec,
            processing_status="queued",
        )

    def claim_next(
        self, worker_id: str, *, lease_seconds: float, max_attempts: int
    ) -> ClaimedAudio | None:
        """Reserva um áudio queued. Recolhe processamento interrompido fora da janela."""
        self._identifier(worker_id)
        if not 1 <= max_attempts <= 5 or lease_seconds < 0:
            raise InvalidEntryError("invalid_entry")
        if not self.db_path.exists():
            return None
        self._migrate_if_needed()
        now = datetime.now(UTC)
        cutoff = _timestamp(now - timedelta(seconds=lease_seconds))
        with closing(self._connect_write()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "UPDATE patient_entries SET processing_status = 'failed', "
                    "error_code = 'attempts_exhausted', claimed_by = NULL, claimed_at = NULL, "
                    "claim_token = NULL WHERE input_type = 'audio' AND processing_status = 'processing' "
                    "AND claimed_at < ? AND attempt_count >= ?",
                    (cutoff, max_attempts),
                )
                conn.execute(
                    "UPDATE patient_entries SET processing_status = 'queued', "
                    "claimed_by = NULL, claimed_at = NULL, claim_token = NULL "
                    "WHERE input_type = 'audio' AND processing_status = 'processing' "
                    "AND claimed_at < ? AND attempt_count < ?",
                    (cutoff, max_attempts),
                )
                row = conn.execute(
                    "SELECT entry_id, patient_id, audio_path, audio_sha256, attempt_count "
                    "FROM patient_entries WHERE input_type = 'audio' "
                    "AND processing_status = 'queued' ORDER BY created_at, entry_id LIMIT 1"
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return None
                token = secrets.token_hex(16)
                updated = conn.execute(
                    "UPDATE patient_entries SET processing_status = 'processing', "
                    "claimed_by = ?, claimed_at = ?, claim_token = ?, "
                    "attempt_count = attempt_count + 1, error_code = NULL "
                    "WHERE entry_id = ? AND processing_status = 'queued'",
                    (worker_id, _timestamp(now), token, row[0]),
                )
                if updated.rowcount != 1:
                    conn.execute("ROLLBACK")
                    return None
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return ClaimedAudio(
            entry_id=row[0],
            patient_id=row[1],
            audio_path=row[2],
            audio_sha256=row[3],
            attempt_count=row[4] + 1,
            claim_token=token,
        )

    def audio_file(self, relative: str) -> Path | None:
        if not self._safe_audio_file(relative):
            return None
        return self.audio_dir / relative

    def save_transcript(self, job: ClaimedAudio, worker_id: str, result: TranscriptResult) -> None:
        self._identifier(worker_id)
        if type(result) is not TranscriptResult or not result.text.strip():
            raise InvalidEntryError("empty_transcript")
        segments = json.dumps(
            [
                {"start_sec": item.start_sec, "end_sec": item.end_sec, "text": item.text}
                for item in result.segments
            ],
            ensure_ascii=False,
        )
        with closing(self._connect_write()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                updated = conn.execute(
                    "UPDATE patient_entries SET processing_status = 'ready', "
                    "error_code = NULL, claimed_by = NULL, claimed_at = NULL, claim_token = NULL "
                    "WHERE entry_id = ? AND processing_status = 'processing' "
                    "AND claimed_by = ? AND claim_token = ?",
                    (job.entry_id, worker_id, job.claim_token),
                )
                if updated.rowcount != 1:
                    raise StoreIsolationError("claim_lost")
                conn.execute(
                    "INSERT INTO transcripts ("
                    "transcript_id, entry_id, language, text, segments_json, model_name, "
                    "created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready')",
                    (
                        secrets.token_hex(16),
                        job.entry_id,
                        result.language,
                        result.text,
                        segments,
                        result.model_name,
                        _timestamp(datetime.now(UTC)),
                    ),
                )
                conn.execute("COMMIT")
            except StoreIsolationError:
                conn.execute("ROLLBACK")
                raise
            except sqlite3.Error:
                conn.execute("ROLLBACK")
                raise StoreIsolationError("write_failed") from None

    def renew_claim(self, job: ClaimedAudio, worker_id: str) -> bool:
        """Estende o prazo só se esta tentativa ainda for a dona da reserva."""
        self._identifier(worker_id)
        with closing(self._connect_write()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                updated = conn.execute(
                    "UPDATE patient_entries SET claimed_at = ? "
                    "WHERE entry_id = ? AND processing_status = 'processing' "
                    "AND claimed_by = ? AND claim_token = ?",
                    (_timestamp(datetime.now(UTC)), job.entry_id, worker_id, job.claim_token),
                )
                conn.execute("COMMIT")
            except sqlite3.Error:
                # Um bloqueio não é reserva perdida; o próximo batimento tenta de novo.
                conn.execute("ROLLBACK")
                return True
        return updated.rowcount == 1

    def fail_audio(
        self, entry_id: str, worker_id: str, claim_token: str, code: str, max_attempts: int
    ) -> None:
        self._identifier(entry_id)
        self._identifier(worker_id)
        if _SAFE_CODE.fullmatch(code) is None or not 1 <= max_attempts <= 5:
            raise InvalidEntryError("invalid_entry")
        if len(claim_token) != 32:
            raise InvalidEntryError("invalid_entry")
        with closing(self._connect_write()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT attempt_count FROM patient_entries "
                    "WHERE entry_id = ? AND processing_status = 'processing' "
                    "AND claimed_by = ? AND claim_token = ?",
                    (entry_id, worker_id, claim_token),
                ).fetchone()
                if row is None:
                    raise StoreIsolationError("claim_lost")
                status = "failed" if row[0] >= max_attempts else "queued"
                conn.execute(
                    "UPDATE patient_entries SET processing_status = ?, error_code = ?, "
                    "claimed_by = NULL, claimed_at = NULL, claim_token = NULL "
                    "WHERE entry_id = ? AND claimed_by = ? AND claim_token = ?",
                    (status, code, entry_id, worker_id, claim_token),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def read_transcript(self, entry_id: str, actor: Actor) -> Transcript:
        entry = self.get(entry_id, actor)
        if entry.input_type != "audio" or entry.processing_status != "ready":
            raise EntryNotFoundError()
        with closing(self._connect_ro()) as conn:
            row = conn.execute(
                "SELECT transcript_id, entry_id, language, text, segments_json, "
                "model_name, created_at, status FROM transcripts WHERE entry_id = ?",
                (entry_id,),
            ).fetchone()
        if row is None:
            raise EntryNotFoundError()
        try:
            segments = tuple(Segment.model_validate(item) for item in json.loads(row[4]))
            return Transcript(
                transcript_id=row[0],
                entry_id=row[1],
                language=row[2],
                text=row[3],
                segments=segments,
                model_name=row[5],
                created_at=datetime.fromisoformat(row[6]),
                status=row[7],
            )
        except (TypeError, ValueError, PatientDiaryError):
            raise StoreIsolationError("corrupt_entry") from None

    def get(self, entry_id: str, actor: Actor) -> PatientEntry:
        actor = parse_actor(actor)
        self._identifier(entry_id)
        row = self._fetch(entry_id)
        if row is None:
            raise EntryNotFoundError()
        if not self._can_read(actor, row):
            raise AccessDeniedError()
        return row

    def list_entries(self, patient_id: str, actor: Actor) -> list[PatientEntry]:
        actor = parse_actor(actor)
        self._identifier(patient_id)
        scope_id = self._scope(actor, patient_id)
        if not self.db_path.exists():
            return []
        self._migrate_if_needed()
        params: list[str] = [scope_id]
        author = ""
        if actor.role == "patient":
            author = " AND author_user_id = ?"
            params.append(actor.user_id)
        with closing(self._connect_ro()) as conn:
            if not self._has_table(conn):
                return []
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM patient_entries WHERE patient_id = ?{author} "
                "ORDER BY created_at, entry_id",
                params,
            ).fetchall()
        return [_entry(row) for row in rows]

    def link_clinician(self, clinician_user_id: str, patient_id: str) -> None:
        """Grava o vínculo local do psicólogo. Não autentica e não lê o relato."""
        self._identifier(clinician_user_id)
        self._identifier(patient_id)
        names, version = self._inspect()
        self._reject_foreign(names, version)
        self._ensure_schema()
        with closing(sqlite3.connect(self.db_path, isolation_level=None)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO care_links (clinician_user_id, patient_id) "
                    "VALUES (?, ?)",
                    (clinician_user_id, patient_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def _scope(self, actor: Actor, patient_id: str) -> str:
        if actor.role == "patient":
            if patient_id != actor.user_id:
                raise AccessDeniedError()
            return actor.user_id
        if not self._linked(actor.user_id, patient_id):
            raise AccessDeniedError()
        return patient_id

    def _can_read(self, actor: Actor, entry: PatientEntry) -> bool:
        if actor.role == "patient":
            return entry.patient_id == actor.user_id and entry.author_user_id == actor.user_id
        return self._linked(actor.user_id, entry.patient_id)

    def _linked(self, clinician_user_id: str, patient_id: str) -> bool:
        if not self.db_path.exists():
            return False
        with closing(self._connect_ro()) as conn:
            if (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'care_links'"
                ).fetchone()
                is None
            ):
                return False
            row = conn.execute(
                "SELECT 1 FROM care_links WHERE clinician_user_id = ? AND patient_id = ?",
                (clinician_user_id, patient_id),
            ).fetchone()
        return row is not None

    def _replay(self, existing: PatientEntry, entry: PatientEntry, actor: Actor) -> PatientEntry:
        if not self._can_read(actor, existing):
            raise AccessDeniedError()
        if not _same(existing, entry):
            raise EntryConflictError()
        if actor.role != "patient" or actor.user_id != existing.author_user_id:
            raise AccessDeniedError()
        return existing

    def _replay_audio(
        self,
        existing: PatientEntry,
        actor: Actor,
        digest: str,
        created_at: datetime,
        consent_id: str,
    ) -> PatientEntry:
        if not self._can_read(actor, existing):
            raise AccessDeniedError()
        same = (
            existing.input_type == "audio"
            and existing.audio_sha256 == digest
            and existing.consent_id == consent_id
            and existing.author_user_id == actor.user_id
            and _timestamp(existing.created_at) == _timestamp(created_at)
        )
        if not same:
            raise EntryConflictError()
        if actor.role != "patient":
            raise AccessDeniedError()
        return existing

    def _hash_owner(self, patient_id: str, digest: str) -> str | None:
        if not self.db_path.exists():
            return None
        with closing(self._connect_ro()) as conn:
            if not self._has_column(conn, "audio_sha256"):
                return None
            row = conn.execute(
                "SELECT entry_id FROM patient_entries WHERE patient_id = ? AND audio_sha256 = ?",
                (patient_id, digest),
            ).fetchone()
        return None if row is None else row[0]

    def _store_file(self, audio: bytes) -> tuple[str, float]:
        directory = self._prepare_audio_dir()
        token = secrets.token_hex(16)
        partial = directory / f".{token}.partial"
        final: Path | None = None
        try:
            fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        except OSError:
            raise InvalidEntryError("audio_write_failed") from None
        try:
            view = memoryview(audio)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError
                view = view[written:]
        except OSError:
            os.close(fd)
            partial.unlink(missing_ok=True)
            raise InvalidEntryError("audio_write_failed") from None
        os.close(fd)
        try:
            suffix, duration = probe_audio(partial)
            final = directory / f"{token}{suffix}"
            os.replace(partial, final)
            os.chmod(final, 0o600)
        except Exception:
            partial.unlink(missing_ok=True)
            if final is not None and final.exists() and not final.is_symlink():
                final.unlink()
            raise
        return final.name, duration

    def _prepare_audio_dir(self) -> Path:
        if self.audio_dir is None:
            raise InvalidEntryError("audio_directory_required")
        directory = self.audio_dir
        if directory.is_symlink():
            raise StoreIsolationError("invalid_audio_path")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        if directory.is_symlink() or not directory.is_dir():
            raise StoreIsolationError("invalid_audio_path")
        return directory

    def _unlink_audio(self, relative: str | None) -> None:
        if not relative or self.audio_dir is None or _AUDIO_NAME.fullmatch(relative) is None:
            return
        path = self.audio_dir / relative
        if path.is_symlink() or path.resolve().parent != self.audio_dir.resolve():
            return
        path.unlink(missing_ok=True)

    def _stored_audio_path(self, entry_id: str) -> str | None:
        if not self.db_path.exists():
            return None
        with closing(self._connect_ro()) as conn:
            row = conn.execute(
                "SELECT audio_path FROM patient_entries WHERE entry_id = ?",
                (entry_id,),
            ).fetchone()
        return None if row is None else row[0]

    def _safe_audio_file(self, relative: str | None) -> bool:
        if self.audio_dir is None or not relative or _AUDIO_NAME.fullmatch(relative) is None:
            return False
        root = self.audio_dir.resolve()
        candidate = self.audio_dir / relative
        if candidate.is_symlink():
            return False
        resolved = candidate.resolve()
        return resolved.parent == root and resolved.is_file()

    def _authorize_create(self, entry: PatientEntry, actor: Actor) -> None:
        if (
            actor.role != "patient"
            or entry.patient_id != actor.user_id
            or entry.author_user_id != actor.user_id
        ):
            raise AccessDeniedError()

    def _reject_foreign(self, names: set[str], version: int) -> None:
        if names & _FORBIDDEN or not names <= _ALLOWED:
            raise StoreIsolationError("foreign_database")
        if names and version not in (1, 2, 3, SCHEMA_VERSION):
            raise StoreIsolationError("unknown_schema")

    def _migrate_if_needed(self) -> None:
        if not self.db_path.exists():
            return
        names, version = self._inspect()
        if not names or version == SCHEMA_VERSION:
            return
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        names, version = self._inspect()
        self._reject_foreign(names, version)
        parent = self.db_path.parent
        parent_existed = parent.exists()
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not parent_existed:
            parent.chmod(0o700)
        if not self.db_path.exists():
            fd = os.open(self.db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            if version == 1 and "patient_entries" in names:
                _migrate_legacy(conn, audio_columns=False)
            elif version == 2 and "patient_entries" in names:
                _migrate_legacy(conn, audio_columns=True)
            elif version == 3 and "patient_entries" in names:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(patient_entries)")}
                if "claim_token" not in columns:
                    conn.execute("ALTER TABLE patient_entries ADD COLUMN claim_token TEXT")
            elif "patient_entries" not in names:
                conn.execute(_ENTRIES_V3)
                _entry_indexes(conn)
            conn.execute(_CARE_LINKS)
            conn.execute(_TRANSCRIPTS)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        os.chmod(self.db_path, 0o600)

    def _insert(self, entry: PatientEntry, audio_path: str | None = None) -> None:
        with closing(sqlite3.connect(self.db_path, isolation_level=None)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO patient_entries ("
                    "entry_id, patient_id, author_user_id, created_at, input_type, "
                    "original_text, processing_status, consent_id, audio_path, "
                    "audio_sha256, duration_sec) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.entry_id,
                        entry.patient_id,
                        entry.author_user_id,
                        _timestamp(entry.created_at),
                        entry.input_type,
                        entry.original_text,
                        entry.processing_status,
                        entry.consent_id,
                        audio_path,
                        entry.audio_sha256,
                        entry.duration_sec,
                    ),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def _fetch(self, entry_id: str) -> PatientEntry | None:
        if not self.db_path.exists():
            return None
        self._migrate_if_needed()
        with closing(self._connect_ro()) as conn:
            if not self._has_table(conn):
                return None
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM patient_entries WHERE entry_id = ?",
                (entry_id,),
            ).fetchone()
        return _entry(row) if row is not None else None

    def _inspect(self) -> tuple[set[str], int]:
        if not self.db_path.exists():
            return set(), 0
        with closing(self._connect_ro()) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
            }
        return names, version

    def _connect_ro(self) -> sqlite3.Connection:
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        return sqlite3.connect(uri, uri=True)

    def _connect_write(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None, timeout=5)
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    @staticmethod
    def _has_table(conn: sqlite3.Connection) -> bool:
        return (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'patient_entries'"
            ).fetchone()
            is not None
        )

    @staticmethod
    def _has_column(conn: sqlite3.Connection, column: str) -> bool:
        rows = conn.execute("PRAGMA table_info(patient_entries)").fetchall()
        return any(row[1] == column for row in rows)

    @staticmethod
    def _identifier(value: str) -> None:
        if _ID.fullmatch(value) is None:
            raise InvalidEntryError("invalid_identifier")


_CARE_LINKS = (
    "CREATE TABLE IF NOT EXISTS care_links ("
    "clinician_user_id TEXT NOT NULL, patient_id TEXT NOT NULL, "
    "PRIMARY KEY (clinician_user_id, patient_id))"
)
_TRANSCRIPTS = (
    "CREATE TABLE IF NOT EXISTS transcripts ("
    "transcript_id TEXT PRIMARY KEY, entry_id TEXT NOT NULL UNIQUE, "
    "language TEXT NOT NULL CHECK(language = 'pt'), "
    "text TEXT NOT NULL CHECK(length(trim(text)) >= 1 AND length(text) <= 20000), "
    "segments_json TEXT NOT NULL, "
    "model_name TEXT NOT NULL CHECK(length(model_name) BETWEEN 1 AND 80), "
    "created_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status = 'ready'))"
)
_ENTRIES_V3 = (
    "CREATE TABLE patient_entries ("
    "entry_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
    "author_user_id TEXT NOT NULL, created_at TEXT NOT NULL, "
    "input_type TEXT NOT NULL CHECK(input_type IN ('text', 'audio')), "
    "original_text TEXT CHECK(original_text IS NULL OR length(original_text) BETWEEN 1 AND 20000), "
    "processing_status TEXT NOT NULL CHECK(processing_status IN "
    "('ready', 'queued', 'processing', 'failed')), "
    "consent_id TEXT NOT NULL, audio_path TEXT, audio_sha256 TEXT, duration_sec REAL, "
    "attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count BETWEEN 0 AND 5), "
    "error_code TEXT, claimed_by TEXT, claimed_at TEXT, claim_token TEXT, "
    "CHECK ((input_type = 'text' AND processing_status = 'ready' AND original_text IS NOT NULL "
    "AND audio_path IS NULL AND audio_sha256 IS NULL AND duration_sec IS NULL "
    "AND attempt_count = 0 AND error_code IS NULL AND claimed_by IS NULL "
    "AND claimed_at IS NULL AND claim_token IS NULL) "
    "OR (input_type = 'audio' AND processing_status IN ('queued', 'processing', 'ready', 'failed') "
    "AND original_text IS NULL AND audio_path IS NOT NULL AND audio_sha256 IS NOT NULL "
    "AND duration_sec > 0 AND duration_sec <= 600)))"
)


def _entry_indexes(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS patient_entry_time "
        "ON patient_entries(patient_id, created_at, entry_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS patient_audio_hash "
        "ON patient_entries(patient_id, audio_sha256) WHERE audio_sha256 IS NOT NULL"
    )


def _migrate_legacy(conn: sqlite3.Connection, *, audio_columns: bool) -> None:
    """Copia os relatos para o esquema atual e só então remove a tabela antiga."""
    conn.execute(
        _ENTRIES_V3.replace("CREATE TABLE patient_entries (", "CREATE TABLE patient_entries_v3 (", 1)
    )
    audio = (
        "audio_path, audio_sha256, duration_sec"
        if audio_columns
        else "NULL, NULL, NULL"
    )
    conn.execute(
        "INSERT INTO patient_entries_v3 ("
        "entry_id, patient_id, author_user_id, created_at, input_type, original_text, "
        "processing_status, consent_id, audio_path, audio_sha256, duration_sec, "
        "attempt_count, error_code, claimed_by, claimed_at, claim_token) "
        "SELECT entry_id, patient_id, author_user_id, created_at, input_type, original_text, "
        f"processing_status, consent_id, {audio}, 0, NULL, NULL, NULL, NULL FROM patient_entries"
    )
    conn.execute("DROP TABLE patient_entries")
    conn.execute("ALTER TABLE patient_entries_v3 RENAME TO patient_entries")
    _entry_indexes(conn)


def _entry(row: tuple) -> PatientEntry:
    try:
        return parse_entry(
            entry_id=row[0],
            patient_id=row[1],
            author_user_id=row[2],
            created_at=datetime.fromisoformat(row[3]),
            input_type=row[4],
            original_text=row[5],
            processing_status=row[6],
            consent_id=row[7],
            audio_sha256=row[8],
            duration_sec=row[9],
            error_code=row[10],
        )
    except PatientDiaryError:
        raise StoreIsolationError("corrupt_entry") from None
