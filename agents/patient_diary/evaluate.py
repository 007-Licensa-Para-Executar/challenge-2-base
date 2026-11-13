"""Avalia uma transcrição fictícia, em português, sem sair da máquina.

Exemplo, a partir da raiz do repositório:

    .venv/bin/python -m agents.patient_diary.evaluate \\
        --audio gravacao-ficticia.wav \\
        --reference-file referencia.txt \\
        --name Marina \\
        --symptom dor \\
        --medication remédio

O modelo padrão é data/models/faster-whisper-small. A execução define
HF_HUB_OFFLINE e recusa conexão externa. WER e CER não medem segurança
clínica. O texto gravado é o do transcritor, sem correção.
"""

from __future__ import annotations

import argparse
import os
import socket
import sqlite3
import tempfile
import threading
import time
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .audio import probe_audio
from .contracts import Actor, InvalidEntryError, PatientDiaryError, TranscriptResult, parse_entry
from .store import PatientDiaryStore
from .transcribe import FasterWhisperTranscriber, SpeechTranscriber
from .worker import TranscriptionWorker

CLINICAL_LIMIT = "WER e CER não medem segurança clínica. O texto gravado não é corrigido."
NEGATIONS = ("não", "nao", "nem", "nunca", "jamais", "nenhum", "nenhuma", "tampouco", "sem")
_ACTOR = Actor(user_id="voz-ficticia", role="patient")


@dataclass(frozen=True)
class TermNote:
    kind: str
    term: str
    status: str


@dataclass(frozen=True)
class Score:
    reference: str
    hypothesis: str
    wer: float
    cer: float
    changes: tuple[tuple[str, str, str], ...]
    terms: tuple[TermNote, ...]


@dataclass(frozen=True)
class Evaluation:
    score: Score
    audio_sec: float
    wall_sec: float
    peak_rss_mib: float
    written_text: str
    transcript_text: str
    separated: bool


def normalize(text: str) -> str:
    """Minúsculas e sem pontuação. Os acentos permanecem, para o WER não esconder troca de palavra."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    chars = [char if char.isalnum() or char.isspace() else " " for char in folded]
    return " ".join("".join(chars).split())


def score_pair(
    reference: str,
    hypothesis: str,
    *,
    names: Sequence[str] = (),
    medications: Sequence[str] = (),
    symptoms: Sequence[str] = (),
) -> Score:
    ref_words = _words(reference)
    hyp_words = _words(hypothesis)
    if not ref_words:
        raise InvalidEntryError("empty_reference")
    ref_chars = list(normalize(reference))
    changes = tuple(item for item in _align(ref_words, hyp_words) if item[0] != "equal")
    return Score(
        reference=reference,
        hypothesis=hypothesis,
        wer=_distance(ref_words, hyp_words) / len(ref_words),
        cer=_distance(ref_chars, list(normalize(hypothesis))) / len(ref_chars),
        changes=changes,
        terms=tuple(_terms(ref_words, hyp_words, names, medications, symptoms)),
    )


def evaluate_audio(
    audio: Path,
    reference: str,
    transcriber: SpeechTranscriber,
    work_dir: Path,
    *,
    names: Sequence[str] = (),
    medications: Sequence[str] = (),
    symptoms: Sequence[str] = (),
    written_text: str = "Relato escrito separado da transcrição.",
) -> Evaluation:
    """Transcreve, mede e grava num SQLite novo. Recusa um diretório que já tenha banco."""
    if not audio.is_file():
        raise InvalidEntryError("invalid_audio")
    if not _words(reference):
        raise InvalidEntryError("empty_reference")
    database = work_dir / "diary.sqlite3"
    if database.exists() or any(work_dir.glob("*.db")):
        raise InvalidEntryError("existing_database")
    _suffix, audio_sec = probe_audio(audio)
    peak = _Peak()
    started = time.perf_counter()
    peak.start()
    try:
        result = transcriber.transcribe(audio)
    finally:
        peak.stop()
    wall = time.perf_counter() - started
    scored = score_pair(
        reference,
        result.text,
        names=names,
        medications=medications,
        symptoms=symptoms,
    )
    stored = _store_apart(work_dir, audio.read_bytes(), written_text, result)
    return Evaluation(
        score=scored,
        audio_sec=audio_sec,
        wall_sec=wall,
        peak_rss_mib=peak.mib,
        written_text=stored[0],
        transcript_text=stored[1],
        separated=stored[2],
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.audio is None or not args.audio.is_file():
        print("invalid_audio")
        return 2
    try:
        reference = _reference_text(args)
    except InvalidEntryError as exc:
        print(exc.code)
        return 2
    except OSError:
        print("invalid_reference")
        return 2
    if not _words(reference):
        print("empty_reference")
        return 2
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    _refuse_remote_network()
    work = args.work_dir
    if work is None:
        with tempfile.TemporaryDirectory(prefix="diario-asr-") as directory:
            return _run_cli(args, reference, Path(directory))
    work.mkdir(parents=True, exist_ok=True)
    return _run_cli(args, reference, work)


def _run_cli(args, reference: str, work: Path) -> int:
    try:
        report = evaluate_audio(
            args.audio,
            reference,
            FasterWhisperTranscriber(args.model, model_name="small"),
            work,
            names=args.name,
            medications=args.medication,
            symptoms=args.symptom,
        )
    except PatientDiaryError as exc:
        print(exc.code)
        return 1
    _print_report(report)
    return 0


def _print_report(report: Evaluation) -> None:
    score = report.score
    print(f"audio_s {report.audio_sec:.3f}")
    print(f"wall_s {report.wall_sec:.2f}")
    print(f"peak_rss_mib {report.peak_rss_mib:.1f}")
    print(f"wer {score.wer:.4f}")
    print(f"cer {score.cer:.4f}")
    print("transcricao", score.hypothesis)
    print("referencia", score.reference)
    for kind, left, right in score.changes:
        print(f"diff {kind} {left} -> {right}".rstrip())
    for note in score.terms:
        print(f"termo {note.kind} {note.term} {note.status}")
    print(
        "sqlite",
        "separado" if report.separated else "misturado",
        "escrito=" + report.written_text,
        "transcricao=" + report.transcript_text,
    )
    print(CLINICAL_LIMIT)


def _store_apart(
    work_dir: Path, audio: bytes, written_text: str, result: TranscriptResult
) -> tuple[str, str, bool]:
    """Grava o relato e a transcrição em tabelas diferentes, sem reescrever o texto."""
    work_dir.mkdir(parents=True, exist_ok=True)
    diary = PatientDiaryStore(work_dir / "diary.sqlite3", work_dir / "audio")
    when = datetime(2026, 11, 13, 15, tzinfo=UTC)
    diary.create(
        parse_entry(
            entry_id="escrito-1",
            patient_id=_ACTOR.user_id,
            author_user_id=_ACTOR.user_id,
            created_at=when,
            original_text=written_text,
            consent_id="consent-eval",
        ),
        _ACTOR,
    )
    diary.create_audio(
        entry_id="audio-1",
        created_at=when,
        consent_id="consent-eval",
        audio=audio,
        actor=_ACTOR,
    )
    finished = TranscriptionWorker(diary, _Replay(result), "worker-eval").run_once()
    if finished != "audio-1":
        raise InvalidEntryError("store_failed")
    written = diary.get("escrito-1", _ACTOR)
    transcript = diary.read_transcript("audio-1", _ACTOR)
    with sqlite3.connect(diary.db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    separated = (
        written.original_text == written_text
        and transcript.text == result.text
        and diary.get("audio-1", _ACTOR).original_text is None
        and {"patient_entries", "transcripts"} <= tables
    )
    return written.original_text or "", transcript.text, separated


class _Replay:
    """Devolve a transcrição já medida, para o SQLite guardar o original e não uma segunda passagem."""

    def __init__(self, result: TranscriptResult):
        self.result = result

    def transcribe(self, path: Path) -> TranscriptResult:
        return self.result


class _Peak:
    def __init__(self):
        self.mib = _rss_mib()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
        self.mib = max(self.mib, _rss_mib())

    def _sample(self) -> None:
        while not self._stop.wait(0.05):
            self.mib = max(self.mib, _rss_mib())


def _rss_mib() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return 0.0


def _words(text: str) -> list[str]:
    normalized = normalize(text)
    return normalized.split() if normalized else []


def _distance(left: Sequence[str], right: Sequence[str]) -> int:
    if not left:
        return len(right)
    previous = list(range(len(right) + 1))
    for i, item in enumerate(left, start=1):
        current = [i]
        for j, other in enumerate(right, start=1):
            cost = 0 if item == other else 1
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


def _align(ref: list[str], hyp: list[str]) -> list[tuple[str, str, str]]:
    rows = len(ref) + 1
    cols = len(hyp) + 1
    cost = [[0] * cols for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0] = i
    for j in range(1, cols):
        cost[0][j] = j
    for i, left in enumerate(ref, start=1):
        for j, right in enumerate(hyp, start=1):
            step = 0 if left == right else 1
            cost[i][j] = min(cost[i - 1][j] + 1, cost[i][j - 1] + 1, cost[i - 1][j - 1] + step)
    ops: list[tuple[str, str, str]] = []
    i, j = len(ref), len(hyp)
    while i or j:
        if i and j and cost[i][j] == cost[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            kind = "equal" if ref[i - 1] == hyp[j - 1] else "replace"
            ops.append((kind, ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i and cost[i][j] == cost[i - 1][j] + 1:
            ops.append(("delete", ref[i - 1], ""))
            i -= 1
        else:
            ops.append(("insert", "", hyp[j - 1]))
            j -= 1
    ops.reverse()
    return ops


def _terms(ref: list[str], hyp: list[str], names, medications, symptoms) -> list[TermNote]:
    notes = []
    for term in NEGATIONS:
        status = _phrase_status(ref, hyp, term)
        if status != "absent":
            notes.append(TermNote("negation", term, status))
    groups = (("name", names), ("medication", medications), ("symptom", symptoms))
    for kind, terms in groups:
        for term in terms:
            notes.append(TermNote(kind, term, _phrase_status(ref, hyp, term)))
    return notes


def _phrase_status(ref: list[str], hyp: list[str], phrase: str) -> str:
    needle = _words(phrase)
    if not needle:
        return "absent"
    found_ref = _count(ref, needle)
    found_hyp = _count(hyp, needle)
    if found_ref == found_hyp == 0:
        return "absent"
    if found_ref == found_hyp:
        return "preserved"
    if found_hyp < found_ref:
        return "missed"
    return "added"


def _count(words: list[str], needle: list[str]) -> int:
    span = len(needle)
    found = range(len(words) - span + 1)
    return sum(1 for index in found if words[index : index + span] == needle)


def _reference_text(args) -> str:
    if args.reference and args.reference_file:
        raise InvalidEntryError("invalid_reference")
    if args.reference_file is not None:
        return args.reference_file.read_text(encoding="utf-8")
    return args.reference or ""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Avalia uma transcrição fictícia local.")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--reference")
    parser.add_argument("--reference-file", type=Path)
    parser.add_argument("--model", type=Path, default=Path("data/models/faster-whisper-small"))
    parser.add_argument("--name", action="append", default=[])
    parser.add_argument("--medication", action="append", default=[])
    parser.add_argument("--symptom", action="append", default=[])
    parser.add_argument("--work-dir", type=Path)
    return parser


def _refuse_remote_network() -> None:
    connect = socket.socket.connect
    lookup = socket.getaddrinfo

    def guarded(self, address):
        # Socket de arquivo é texto. Endereço de rede é tupla e fica bloqueado.
        if type(address) is not str and type(address) is not bytes:
            raise OSError(101, "rede bloqueada")
        return connect(self, address)

    def local_only(host, *args, **kwargs):
        if host not in (None, "", "localhost", "127.0.0.1", "::1"):
            raise RuntimeError("dns bloqueado")
        return lookup(host, *args, **kwargs)

    socket.socket.connect = guarded
    socket.getaddrinfo = local_only


if __name__ == "__main__":
    raise SystemExit(main())
