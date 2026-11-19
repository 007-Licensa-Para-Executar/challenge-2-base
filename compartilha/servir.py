"""Sobe a API do diário fictício e retoma a fila já existente.

Não baixa modelo. Não altera o módulo do diário: a fila usa transcribe_next.
"""

from __future__ import annotations

import os
import signal
import threading
from pathlib import Path

from agents.patient_diary.local_app import LocalDiary, serve

_ROOT = Path(os.environ.get("DIARY_ROOT", "/data"))
_MODEL = Path(os.environ.get("DIARY_MODEL_DIR", "/models/faster-whisper-small"))
_PORT = 8765
_PAUSE_SECONDS = 30.0


def _drain(diary: LocalDiary, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            worked = diary.transcribe_next()
        except Exception:  # noqa: BLE001 — o texto pode citar o caminho do áudio
            print("recuperacao_falhou", flush=True)
            return
        if not worked:
            return


def main() -> int:
    if not (_MODEL / "model.bin").is_file():
        print("Modelo local ausente. O processo não baixa pesos.", flush=True)
        return 1
    _ROOT.mkdir(parents=True, exist_ok=True)
    (_ROOT / "audio").mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    diary = LocalDiary(_ROOT, model_path=_MODEL)
    server = serve(diary, _PORT)
    stop = threading.Event()

    def recover() -> None:
        while not stop.is_set():
            _drain(diary, stop)
            stop.wait(_PAUSE_SECONDS)

    threading.Thread(target=recover, name="diary-recover", daemon=True).start()

    def _stop(_signum: int, _frame: object) -> None:
        print("sigterm", flush=True)
        stop.set()
        # shutdown espera o serve_forever; chamado da thread principal, trava.
        threading.Thread(target=server.shutdown, name="diary-shutdown", daemon=True).start()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    print("api_pronta", flush=True)
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
