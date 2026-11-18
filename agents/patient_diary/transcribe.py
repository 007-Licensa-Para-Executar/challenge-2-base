"""Transcrição de áudio. O adaptador local não baixa modelo e não é importado à toa."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .contracts import PatientDiaryError, Segment, TranscriptResult


class TranscriptionError(PatientDiaryError):
    """Falha do transcritor. A mensagem é só o código."""


class SpeechTranscriber(Protocol):
    def transcribe(self, path: Path) -> TranscriptResult:
        """Lê um arquivo já validado e devolve texto, idioma, segmentos e modelo."""


class FakeTranscriber:
    """Transcritor fixo para testes. Não lê o áudio como fala."""

    def __init__(
        self,
        text: str = "Nota sintética de teste.",
        *,
        fail: bool = False,
        empty: bool = False,
    ):
        self.text = text
        self.fail = fail
        self.empty = empty
        self.paths: list[Path] = []

    def transcribe(self, path: Path) -> TranscriptResult:
        self.paths.append(path)
        if self.fail:
            raise TranscriptionError("transcriber_failed")
        if self.empty:
            raise TranscriptionError("empty_transcript")
        return TranscriptResult(
            text=self.text,
            language="pt",
            segments=(Segment(start_sec=0.0, end_sec=0.2, text=self.text),),
            model_name="fake",
            status="ok",
        )


class FasterWhisperTranscriber:
    """Faster-Whisper local, em CPU, com modelo já presente no disco.

    Não baixa pesos. A biblioteca precisa ser instalada à parte.
    """

    def __init__(self, model_path: str | Path, model_name: str = "local"):
        self.model_path = Path(model_path)
        self.model_name = model_name
        self._model = None

    def transcribe(self, path: Path) -> TranscriptResult:
        model = self._load()
        try:
            segments, _info = model.transcribe(
                str(path),
                language="pt",
                initial_prompt="Transcrição em português do Brasil.",
            )
            pieces = [
                Segment(start_sec=float(item.start), end_sec=float(item.end), text=item.text.strip())
                for item in segments
                if getattr(item, "text", "").strip()
            ]
        except TranscriptionError:
            raise
        except Exception:  # noqa: BLE001 — a mensagem da biblioteca pode conter a fala
            raise TranscriptionError("transcriber_failed") from None
        if not pieces:
            raise TranscriptionError("empty_transcript")
        text = " ".join(piece.text for piece in pieces)
        return TranscriptResult(
            text=text,
            language="pt",
            segments=tuple(pieces),
            model_name=self.model_name,
            status="ok",
        )

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.model_path.is_dir():
            raise TranscriptionError("model_unavailable")
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError("transcriber_unavailable") from None
        try:
            self._model = WhisperModel(
                str(self.model_path),
                device="cpu",
                compute_type="int8",
                local_files_only=True,
            )
        except Exception:  # noqa: BLE001 — a mensagem pode citar o caminho do modelo
            raise TranscriptionError("model_unavailable") from None
        return self._model
