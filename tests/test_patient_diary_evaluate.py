"""Métricas da transcrição fictícia. Não carregam o modelo nem abrem o banco do projeto."""

import wave
from pathlib import Path

import pytest

from agents.patient_diary.contracts import InvalidEntryError
from agents.patient_diary.evaluate import (
    CLINICAL_LIMIT,
    evaluate_audio,
    main,
    normalize,
    score_pair,
)
from agents.patient_diary.transcribe import FakeTranscriber

REFERENCE = "A paciente fictícia Marina não relatou dor. E não tomou o remédio ontem."
HEARD = "A paciente fictícia madina não relatou por e não tomou o remédio ontem."


def test_normalize_keeps_accents_and_drops_punctuation():
    assert normalize("Não,  Dor!") == "não dor"
    assert normalize("Remédio.") == "remédio"


def test_wer_and_cer_of_the_espeak_sample():
    score = score_pair(REFERENCE, HEARD, names=("Marina",), symptoms=("dor",), medications=("remédio",))
    assert score.hypothesis == HEARD
    assert score.wer == pytest.approx(2 / 13)
    assert score.changes == (("replace", "marina", "madina"), ("replace", "dor", "por"))
    assert score.cer == pytest.approx(2 / len(normalize(REFERENCE)))
    notes = {(note.kind, note.term, note.status) for note in score.terms}
    assert ("negation", "não", "preserved") in notes
    assert ("name", "Marina", "missed") in notes
    assert ("symptom", "dor", "missed") in notes
    assert ("medication", "remédio", "preserved") in notes


def test_empty_reference_is_rejected():
    with pytest.raises(InvalidEntryError) as error:
        score_pair("...", "alguma fala")
    assert error.value.code == "empty_reference"


def test_missing_audio_does_not_call_the_transcriber(tmp_path):
    class Boom:
        def transcribe(self, path: Path):
            raise AssertionError(path)

    with pytest.raises(InvalidEntryError) as error:
        evaluate_audio(tmp_path / "ausente.wav", "fala fictícia", Boom(), tmp_path / "novo")
    assert error.value.code == "invalid_audio"


def test_cli_without_audio_stops_before_the_model():
    assert main(["--reference", "fala fictícia"]) == 2


def test_sqlite_keeps_the_written_entry_apart_from_the_raw_transcript(tmp_path):
    audio = tmp_path / "silencio.wav"
    _silence(audio)
    phrase = "Nota sintética, sem correção."
    report = evaluate_audio(
        audio,
        "nota sintética sem correção",
        FakeTranscriber(phrase),
        tmp_path / "diario",
        names=("Marina",),
    )
    assert report.separated
    assert report.transcript_text == phrase
    assert report.written_text == "Relato escrito separado da transcrição."
    assert report.transcript_text != report.written_text
    assert report.score.hypothesis == phrase
    assert report.audio_sec > 0
    assert report.wall_sec >= 0
    assert report.peak_rss_mib > 0
    assert "não medem segurança clínica" in CLINICAL_LIMIT
    database = tmp_path / "diario" / "diary.sqlite3"
    with pytest.raises(InvalidEntryError) as error:
        evaluate_audio(audio, "outra fala", FakeTranscriber(phrase), tmp_path / "diario")
    assert error.value.code == "existing_database"
    assert database.exists()


def _silence(path: Path) -> None:
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 2400)
