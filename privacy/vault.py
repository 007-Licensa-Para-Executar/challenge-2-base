"""Local encrypted storage for identities, originals, and pseudonym mappings."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import sqlite3
import unicodedata
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from itertools import pairwise
from pathlib import Path
from typing import Any, Protocol, TypedDict
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

_DIRECT_IDENTIFIERS = frozenset({"CPF", "PHONE", "EMAIL"})
_LINKABLE_ENTITIES = frozenset({"PERSON", "ORG", "LOCATION"})
_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS vault_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        cipher_lookup_key BLOB NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        source_key BLOB NOT NULL UNIQUE,
        cipher_name BLOB NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS records (
        patient_id TEXT NOT NULL REFERENCES patients(patient_id),
        record_key BLOB NOT NULL,
        cipher_record BLOB NOT NULL,
        PRIMARY KEY (patient_id, record_key)
    )""",
    """CREATE TABLE IF NOT EXISTS entities (
        patient_id TEXT NOT NULL REFERENCES patients(patient_id),
        entity_key BLOB NOT NULL,
        cipher_entity BLOB NOT NULL,
        PRIMARY KEY (patient_id, entity_key)
    )""",
)


class VaultError(RuntimeError):
    """The vault could not safely open its encrypted data."""


class SpanLike(Protocol):
    @property
    def start(self) -> int: ...

    @property
    def end(self) -> int: ...

    @property
    def kind(self) -> str: ...


class OriginalRecord(TypedDict):
    text: str
    title: str | None


def _validated_key(key: str) -> bytes:
    try:
        encoded = key.encode("ascii")
        decoded = base64.b64decode(encoded, altchars=b"-_", validate=True)
        if len(decoded) == 32 and base64.urlsafe_b64encode(decoded) == encoded:
            return encoded
    except (AttributeError, ValueError, binascii.Error):
        pass
    raise ValueError("Vault keys must be URL-safe base64-encoded Fernet keys.")


def _checked_spans(text: str | None, spans: Iterable[SpanLike]) -> list[SpanLike]:
    spans = list(spans)
    length = len(text) if text is not None else 0
    for span in spans:
        if type(span.start) is not int or type(span.end) is not int:
            raise ValueError("Invalid entity span offsets.")
        if not 0 <= span.start < span.end <= length:
            raise ValueError("Entity span is outside its input.")
        if span.kind not in _DIRECT_IDENTIFIERS and span.kind not in _LINKABLE_ENTITIES:
            raise ValueError("Unsupported entity kind.")
    ordered = sorted(spans, key=lambda span: span.start)
    if any(left.end > right.start for left, right in pairwise(ordered)):
        raise ValueError("Entity spans overlap.")
    return ordered


class Vault:
    """Persist only opaque identifiers and authenticated ciphertext in a dedicated database."""

    def __init__(self, path: Path | str, keys: list[str]) -> None:
        if not keys:
            raise ValueError("At least one vault key is required.")
        self._cipher = MultiFernet([Fernet(_validated_key(key)) for key in keys])
        self._path = Path(path).absolute()
        try:
            fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)

        with self._transaction(write=True) as conn:
            for statement in _SCHEMA:
                conn.execute(statement)
            row = conn.execute("SELECT cipher_lookup_key FROM vault_config WHERE id = 1").fetchone()
            if row is None:
                if conn.execute("SELECT 1 FROM patients LIMIT 1").fetchone() is not None:
                    raise VaultError("Vault configuration is missing.")
                self._lookup_key = os.urandom(32)
                conn.execute(
                    "INSERT INTO vault_config VALUES (1, ?)",
                    (self._cipher.encrypt(self._lookup_key),),
                )
            else:
                self._lookup_key = self._decrypt(row[0])
                if len(self._lookup_key) != 32:
                    raise VaultError("Vault configuration is invalid.")

    @contextmanager
    def _transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        try:
            with closing(sqlite3.connect(self._path)) as conn, conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield conn
        except sqlite3.Error:
            raise VaultError("Vault storage is unavailable.") from None

    def _lookup(self, namespace: str, *values: str) -> bytes:
        message = json.dumps((namespace, *values), ensure_ascii=False).encode("utf-8")
        return hmac.digest(self._lookup_key, message, "sha256")

    def _decrypt(self, ciphertext: bytes) -> bytes:
        try:
            return self._cipher.decrypt(ciphertext)
        except (InvalidToken, TypeError):
            raise VaultError("Vault data could not be decrypted.") from None

    def _seal(self, context: str, value: Any) -> bytes:
        return self._cipher.encrypt(json.dumps((context, value), ensure_ascii=False).encode())

    def _open(self, context: str, ciphertext: bytes) -> Any:
        try:
            bound_context, value = json.loads(self._decrypt(ciphertext))
        except (UnicodeError, ValueError, TypeError):
            raise VaultError("Vault data is invalid.") from None
        if bound_context != context:
            raise VaultError("Vault data failed its scope check.")
        return value

    def register(self, patient_key: str, display_name: str) -> str:
        """Register a source patient key and return its persistent UUID."""
        if not patient_key.strip() or not display_name.strip():
            raise ValueError("Patient key and display name are required.")
        source_key = self._lookup("patient", patient_key)
        with self._transaction(write=True) as conn:
            row = conn.execute(
                "SELECT patient_id, cipher_name FROM patients WHERE source_key = ?", (source_key,)
            ).fetchone()
            if row is not None:
                patient_id, cipher_name = row
                if self._open(patient_id, cipher_name) != display_name:
                    raise ValueError("Patient key is already registered with a different name.")
                return patient_id
            patient_id = str(uuid4())
            conn.execute(
                "INSERT INTO patients VALUES (?, ?, ?)",
                (patient_id, source_key, self._seal(patient_id, display_name)),
            )
            return patient_id

    def display_name(self, patient_id: str) -> str:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT cipher_name FROM patients WHERE patient_id = ?", (patient_id,)
            ).fetchone()
            if row is None:
                raise KeyError("Unknown patient.")
            return self._open(patient_id, row[0])

    def protect(
        self,
        patient_id: str,
        record_id: str | None,
        text: str,
        title: str | None,
        spans: Iterable[SpanLike],
        title_spans: Iterable[SpanLike],
        detector_version: str,
    ) -> tuple[str, str | None, str]:
        """Return the treated fields and representation ID, saving originals for records."""
        checked_spans = _checked_spans(text, spans)
        checked_title_spans = _checked_spans(title, title_spans)
        if not detector_version.strip() or (record_id is not None and not record_id.strip()):
            raise ValueError("Detector version and any supplied record ID must be nonempty.")

        ingest = record_id is not None
        with self._transaction(write=ingest) as conn:
            if (
                conn.execute(
                    "SELECT 1 FROM patients WHERE patient_id = ?", (patient_id,)
                ).fetchone()
                is None
            ):
                raise KeyError("Unknown patient.")

            original = {"text": text, "title": title}
            if record_id is not None:
                record_key = self._lookup("record", patient_id, record_id)
                existing = self._read_record(conn, patient_id, record_key)
                if existing is not None:
                    if existing["original"] != original or existing["version"] != detector_version:
                        raise ValueError(
                            "Record ID is already used for different content or version."
                        )
                    return existing["text"], existing["title"], existing["representation_id"]

            treated_text = self._replace(conn, patient_id, text, checked_spans, ingest=ingest)
            treated_title = (
                self._replace(conn, patient_id, title, checked_title_spans, ingest=ingest)
                if title is not None
                else None
            )
            representation_id = str(uuid4())
            if record_id is not None:
                data = {
                    "original": original,
                    "version": detector_version,
                    "text": treated_text,
                    "title": treated_title,
                    "representation_id": representation_id,
                }
                conn.execute(
                    "INSERT INTO records VALUES (?, ?, ?)",
                    (patient_id, record_key, self._seal(record_key.hex(), data)),
                )
            return treated_text, treated_title, representation_id

    def original(self, patient_id: str, record_id: str) -> OriginalRecord:
        """Read the original fields for an application-authorized patient and record."""
        record_key = self._lookup("record", patient_id, record_id)
        with self._transaction() as conn:
            record = self._read_record(conn, patient_id, record_key)
            if record is None:
                raise KeyError("Unknown record.")
            return record["original"]

    def _read_record(
        self, conn: sqlite3.Connection, patient_id: str, record_key: bytes
    ) -> dict[str, Any] | None:
        row = conn.execute(
            "SELECT cipher_record FROM records WHERE patient_id = ? AND record_key = ?",
            (patient_id, record_key),
        ).fetchone()
        return self._open(record_key.hex(), row[0]) if row is not None else None

    def _replace(
        self,
        conn: sqlite3.Connection,
        patient_id: str,
        text: str,
        spans: list[SpanLike],
        *,
        ingest: bool,
    ) -> str:
        parts = []
        cursor = 0
        for span in spans:
            parts.append(text[cursor : span.start])
            token = f"[{span.kind}]"
            if span.kind in _LINKABLE_ENTITIES:
                source = text[span.start : span.end]
                normalized = " ".join(unicodedata.normalize("NFKC", source).casefold().split())
                # A first name alone is not enough to link mentions across entries.
                if span.kind == "PERSON" and len(normalized.split()) == 1:
                    parts.append(token)
                    cursor = span.end
                    continue
                entity_key = self._lookup("entity", patient_id, span.kind, normalized)
                row = conn.execute(
                    "SELECT cipher_entity FROM entities WHERE patient_id = ? AND entity_key = ?",
                    (patient_id, entity_key),
                ).fetchone()
                if row is not None:
                    token = self._open(entity_key.hex(), row[0])["token"]
                elif ingest:
                    token = f"[{span.kind}_{uuid4().hex}]"
                    conn.execute(
                        "INSERT INTO entities VALUES (?, ?, ?)",
                        (
                            patient_id,
                            entity_key,
                            self._seal(
                                entity_key.hex(),
                                {"kind": span.kind, "source": source, "token": token},
                            ),
                        ),
                    )
            parts.append(token)
            cursor = span.end
        parts.append(text[cursor:])
        return "".join(parts)
