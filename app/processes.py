"""Processos Python internos e canceláveis, sem shell nem argumentos vindos do LLM."""

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from agents.extractor.config import Settings

ROOT = Path(__file__).resolve().parent.parent
MODULES = {"agents.extractor", "app.router", "evaluation.runner", "pytest"}


@dataclass(frozen=True)
class ProcessResult:
    code: int
    stdout: str
    stderr: str


def child_environment(settings: Settings) -> dict[str, str]:
    # Não herdar tokens, chaves ou variáveis de ferramentas de desenvolvimento.
    allowed = {
        "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR",
        "HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "LANG", "LC_ALL",
        "VIRTUAL_ENV", "UV_CACHE_DIR",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(
        PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
        OLLAMA_HOST=settings.host, EXTRACTOR_MODEL=settings.model,
        EXTRACTOR_CONTEXT_TOKENS=str(settings.context_tokens),
        EXTRACTOR_TIMEOUT_SECONDS=str(settings.timeout_seconds),
        EXTRACTOR_DB_PATH=settings.db_path,
    )
    return env


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGINT)
        process.wait(timeout=3)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    if os.name == "nt":
        # taskkill é parte do Windows; /T encerra também os descendentes.
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def run_module(
    module: str, arguments: list[str], settings: Settings, *, text: str | None = None,
    timeout: float | None = None, progress=lambda: None,
) -> ProcessResult:
    if module not in MODULES:
        raise ValueError("Módulo não permitido")
    options = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt" else {"start_new_session": True}
    )
    process = subprocess.Popen(
        [sys.executable, "-m", module, *arguments], cwd=ROOT,
        env=child_environment(settings), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", **options,
    )
    started = time.monotonic()
    first = True
    try:
        while True:
            try:
                out, err = process.communicate(input=text if first else None, timeout=0.15)
                return ProcessResult(process.returncode, out, err)
            except subprocess.TimeoutExpired:
                first = False
                if timeout is not None and time.monotonic() - started >= timeout:
                    raise TimeoutError("Tempo limite excedido; operação cancelada.")
                progress()
    finally:
        stop_process(process)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()
