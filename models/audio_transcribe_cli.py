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


def transcribe_local_audio(audio_path: Path) -> dict[str, str | float | int]:
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size == 0:
        return {"status": "error", "message": "Arquivo de áudio vazio ou inexistente.", "text": ""}

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 25.0:
        return {"status": "error", "message": "Arquivo de áudio ultrapassa o limite de 25 MB.", "text": ""}

    cache_dir = Path("data/models")
    model_paths = [
        Path("data/models/faster-whisper-small"),
        Path("data/models/faster-whisper-base"),
        Path("data/models/faster-whisper-tiny"),
    ]
    model_path = next(
        (candidate for candidate in model_paths if (candidate / "model.bin").is_file()),
        None,
    )

    try:
        from faster_whisper import WhisperModel

        cache_dir.mkdir(parents=True, exist_ok=True)
        model = WhisperModel(
            str(model_path) if model_path else "base",
            device="cpu",
            compute_type="int8",
            download_root=str(cache_dir),
            local_files_only=bool(model_path),
        )
        segments, info = model.transcribe(str(path), language="pt")
        pieces = [segment.text.strip() for segment in segments if segment.text.strip()]
        text = " ".join(pieces)
        if not text:
            return {
                "status": "empty",
                "message": "Não identificamos fala no áudio. Confira o microfone e tente novamente.",
                "text": "",
            }
        return {
            "status": "ok",
            "text": text,
            "duration": round(float(info.duration), 2),
            "model": model_path.name if model_path else "faster-whisper-base",
        }
    except Exception:
        logger.exception("Falha ao preparar ou executar a transcrição local.")
        return {
            "status": "error",
            "message": "Não foi possível preparar a transcrição local. Verifique a conexão e tente novamente.",
            "text": "",
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
