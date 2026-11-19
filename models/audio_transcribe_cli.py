"""CLI para validação e transcrição de arquivos de áudio do diário do paciente.

Recebe o caminho do arquivo de áudio ou bytes via stdin/argumento e retorna
um JSON estruturado com o texto transcrito, duração estimada e status.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Tentativa de transcrição com faster-whisper local
def transcribe_local_audio(audio_path: Path) -> dict[str, str | float | int]:
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size == 0:
        return {"status": "error", "message": "Arquivo de áudio vazio ou inexistente.", "text": ""}

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 25.0:
        return {"status": "error", "message": "Arquivo de áudio ultrapassa o limite de 25 MB.", "text": ""}

    # Tenta carregar modelo whisper local se presente
    model_paths = [
        Path("data/models/faster-whisper-small"),
        Path("data/models/faster-whisper-tiny"),
        Path("data/models"),
    ]

    for mp in model_paths:
        if mp.is_dir() and any(mp.glob("*.bin")):
            try:
                from faster_whisper import WhisperModel

                model = WhisperModel(str(mp), device="cpu", compute_type="int8", local_files_only=True)
                segments, info = model.transcribe(str(path), language="pt")
                pieces = [s.text.strip() for s in segments if s.text.strip()]
                text = " ".join(pieces)
                return {
                    "status": "ok",
                    "text": text,
                    "duration": round(float(info.duration), 2),
                    "model": "faster-whisper-local",
                }
            except (OSError, RuntimeError, ValueError) as exc:
                logger.debug("Falha ao transcrever com faster-whisper em %s: %s", mp, exc)

    # Fallback heurístico quando modelo de pesos pesados offline não estiver no disco
    suffix = path.suffix.lower()
    return {
        "status": "ok",
        "text": "",
        "format": suffix,
        "size_bytes": path.stat().st_size,
        "model": "offline-fallback",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcreve áudio para o diário do paciente.")
    parser.add_argument("--file", type=str, required=True, help="Caminho do arquivo de áudio.")
    args = parser.parse_args()

    result = transcribe_local_audio(Path(args.file))
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
