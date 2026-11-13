"""Validação de áudio com ffprobe. O processo não usa shell e não devolve o conteúdo."""

from __future__ import annotations

import json
import math
import resource
import subprocess
from pathlib import Path

from .contracts import InvalidEntryError

FFPROBE = "/usr/bin/ffprobe"
MAX_BYTES = 25 * 1024 * 1024
MAX_SECONDS = 600.0
_PROBE_TIMEOUT = 10
_SUFFIXES = {
    "wav": ".wav",
    "ogg": ".ogg",
    "webm": ".webm",
    "mov": ".m4a",
    "mp4": ".m4a",
    "m4a": ".m4a",
    "mp3": ".mp3",
    "3gp": ".m4a",
    "3g2": ".m4a",
}


def _limit_child() -> None:
    cpu = _PROBE_TIMEOUT
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def probe_audio(path: Path) -> tuple[str, float]:
    """Devolve o sufixo e a duração. A exceção só tem o código."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise InvalidEntryError("invalid_audio")
    if path.stat().st_size > MAX_BYTES:
        raise InvalidEntryError("audio_too_large")
    try:
        completed = subprocess.run(
            [
                FFPROBE,
                "-v",
                "error",
                "-show_entries",
                "format=format_name,duration:stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            shell=False,
            check=False,
            capture_output=True,
            timeout=_PROBE_TIMEOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            preexec_fn=_limit_child,
        )
    except subprocess.TimeoutExpired:
        raise InvalidEntryError("invalid_audio") from None
    except FileNotFoundError:
        raise InvalidEntryError("audio_probe_unavailable") from None
    except OSError:
        raise InvalidEntryError("invalid_audio") from None
    if completed.returncode != 0 or not completed.stdout:
        raise InvalidEntryError("invalid_audio")
    try:
        payload = json.loads(completed.stdout)
        names = set(str(payload["format"]["format_name"]).split(","))
        streams = payload.get("streams") or []
        kinds = {stream.get("codec_type") for stream in streams}
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise InvalidEntryError("invalid_audio") from None
    if "audio" not in kinds or "video" in kinds:
        raise InvalidEntryError("invalid_audio")
    suffix = next((ext for name, ext in _SUFFIXES.items() if name in names), None)
    if suffix is None or not math.isfinite(duration) or duration <= 0:
        raise InvalidEntryError("invalid_audio")
    if duration > MAX_SECONDS:
        raise InvalidEntryError("audio_too_long")
    return suffix, round(duration, 3)
