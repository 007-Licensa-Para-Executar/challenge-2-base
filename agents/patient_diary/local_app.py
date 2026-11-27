"""Página local do diário fictício. Não autentica e não chama a rede neural.

Uso, na raiz do repositório:

    .venv/bin/python -m agents.patient_diary.local_app

Abre somente em 127.0.0.1:8765. O paciente é sempre ``paciente-ficticio``.
Um campo de identidade vindo do navegador é ignorado. Ainda não há
autenticação adequada para relatos reais.

JSON, além da página: ``POST /api/texto`` com ``{"text": "..."}`` responde
``id``, ``created_at``, ``kind=written`` e ``status=ready``. ``POST /api/audio``
recebe o campo ``audio`` e responde sempre JSON. ``GET /api/historico`` devolve
no máximo 100 registros, do mais antigo ao mais novo, com desempate pelo id.
A interface reordena para mostrar o mais recente primeiro.

``POST /worker`` e ``POST /transcrever`` não atendem o navegador. Não são
autenticação: só respondem a um processo preso em loopback, sem cabeçalho
de browser.

O banco fica em data/patient_diary_local/, separado dos bancos já existentes.
A transcrição usa o Faster-Whisper small local e não envia áudio para fora.

Contrato futuro da rede temática, ainda sem implementação: a entrada é o
entry_id, a origem ``written`` ou ``transcript`` e o texto daquela origem.
A saída é status, tema, score e motivo de abstenção. Ela não substitui o
relato escrito nem a transcrição bruta.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import secrets
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse

from .contracts import Actor, InvalidEntryError, PatientDiaryError, parse_entry
from .store import PatientDiaryStore
from .transcribe import FasterWhisperTranscriber, SpeechTranscriber
from .worker import TranscriptionWorker

LOCAL_USER = "paciente-ficticio"
DEFAULT_ROOT = Path("data/patient_diary_local")
DEFAULT_MODEL = Path("data/models/faster-whisper-small")
_HOST = "127.0.0.1"
_MAX_BODY = 26 * 1024 * 1024
# 20 mil caracteres em UTF-8, mais o envelope JSON. Acima disso o corpo é recusado.
_TEXT_BODY = 96 * 1024
# Os mais recentes. A resposta continua do mais antigo ao mais novo; a paginação fica para depois.
_HISTORY_LIMIT = 100
_LOOPBACK_ORIGIN = re.compile(r"http://(127\.0\.0\.1|localhost)(:[0-9]{1,5})?\Z")
_STATUS = {
    "queued": "aguardando",
    "processing": "processando",
    "ready": "concluído",
    "failed": "erro",
}
_NOTICES = {
    "texto_gravado": "Relato escrito gravado.",
    "audio_gravado": "Áudio gravado e colocado na fila.",
    "transcrito": "O worker concluiu uma passagem.",
    "fila_vazia": "Não há áudio aguardando.",
    "empty_text": "O relato está vazio.",
    "text_too_long": "O relato passa de 20 mil caracteres.",
    "invalid_audio": "O arquivo não é um WAV, MP3 ou M4A válido.",
    "empty_audio": "O arquivo está vazio.",
    "audio_too_large": "O arquivo passa de 25 MB.",
    "audio_too_long": "O áudio passa de 10 minutos.",
    "duplicate_audio": "Este áudio já foi registrado.",
    "model_unavailable": "O modelo local não está disponível.",
    "transcriber_unavailable": "O transcritor local não está instalado.",
    "transcriber_failed": "A transcrição falhou.",
    "empty_transcript": "A transcrição veio vazia.",
    "audio_missing": "O arquivo de áudio não foi encontrado.",
    "hash_mismatch": "O áudio não confere com o que foi gravado.",
}


@dataclass(frozen=True)
class FutureThemeInput:
    """Pedido futuro para a rede de temas. Este módulo não o envia."""

    entry_id: str
    source: Literal["written", "transcript"]
    text: str


@dataclass(frozen=True)
class FutureThemeOutput:
    """Resposta futura. Não é diagnóstico e não apaga o texto de origem."""

    status: Literal["ok", "unavailable", "error"]
    primary_theme: str | None = None
    candidate_score: float | None = None
    abstention_reason: str | None = None


class LocalDiary:
    """Operações do MVP. A identidade é a constante local, não a do pedido."""

    def __init__(
        self,
        root: Path,
        transcriber: SpeechTranscriber | None = None,
        model_path: Path = DEFAULT_MODEL,
    ):
        self.root = root
        self.model_path = model_path
        self.store = PatientDiaryStore(root / "diary.sqlite3", root / "audio")
        self._transcriber = transcriber

    def add_text(self, text: str) -> str:
        entry_id = secrets.token_hex(8)
        self.store.create(
            parse_entry(
                entry_id=entry_id,
                patient_id=LOCAL_USER,
                author_user_id=LOCAL_USER,
                created_at=datetime.now(UTC),
                original_text=text,
                consent_id="consent-local",
            ),
            _actor(),
        )
        return entry_id

    def add_audio(self, payload: bytes) -> str:
        entry_id = secrets.token_hex(8)
        self.store.create_audio(
            entry_id=entry_id,
            created_at=datetime.now(UTC),
            consent_id="consent-local",
            audio=payload,
            actor=_actor(),
        )
        return entry_id

    def add_audio_part(self, content_type: str, body: bytes) -> str:
        return self.add_audio(_audio_part(content_type, body))

    def transcribe_next(self) -> str | None:
        return TranscriptionWorker(self.store, self._load_transcriber(), "worker-local").run_once()

    def preview_audio(self, payload: bytes, suffix: str) -> str:
        """Transcreve o arquivo sem criar registro."""
        if suffix not in {".wav", ".mp3", ".m4a", ".webm"}:
            raise InvalidEntryError("invalid_audio")
        if not payload:
            raise InvalidEntryError("empty_audio")
        if len(payload) > 25 * 1024 * 1024:
            raise InvalidEntryError("audio_too_large")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            path = Path(handle.name)
        try:
            path.write_bytes(payload)
            return self._load_transcriber().transcribe(path).text
        finally:
            path.unlink(missing_ok=True)

    def api_history(self) -> tuple[list[dict[str, object]], bool]:
        """Histórico JSON do paciente fixo.

        A ordem é a do banco: created_at crescente e, na mesma data, entry_id
        crescente. No máximo os 100 mais recentes. Sem caminho, hash ou reserva.
        """
        actor = _actor()
        rows = self.store.list_entries(LOCAL_USER, actor)
        truncated = len(rows) > _HISTORY_LIMIT
        if truncated:
            rows = rows[-_HISTORY_LIMIT:]
        documents: list[dict[str, object]] = []
        for entry in rows:
            item: dict[str, object] = {
                "id": entry.entry_id,
                "created_at": entry.created_at.isoformat(),
                "kind": "written" if entry.input_type == "text" else "audio",
                "status": entry.processing_status,
                "text": entry.original_text or "",
                "transcript": "",
            }
            if entry.input_type == "audio":
                item["duration_seconds"] = entry.duration_sec
                if entry.processing_status == "ready":
                    item["transcript"] = self.store.read_transcript(entry.entry_id, actor).text
            documents.append(item)
        return documents, truncated

    def history(self) -> list[dict[str, str]]:
        rows = []
        actor = _actor()
        for entry in self.store.list_entries(LOCAL_USER, actor):
            transcript = ""
            if entry.input_type == "audio" and entry.processing_status == "ready":
                transcript = self.store.read_transcript(entry.entry_id, actor).text
            rows.append(
                {
                    "created_at": entry.created_at.isoformat(),
                    "kind": "escrito" if entry.input_type == "text" else "áudio",
                    "status": entry.processing_status,
                    "label": _STATUS.get(entry.processing_status, entry.processing_status),
                    "text": entry.original_text or "",
                    "transcript": transcript,
                    "error": entry.error_code or "",
                }
            )
        return rows

    def _load_transcriber(self) -> SpeechTranscriber:
        if self._transcriber is not None:
            return self._transcriber
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        return FasterWhisperTranscriber(self.model_path, model_name="small")


def serve(diary: LocalDiary, port: int = 8765) -> ThreadingHTTPServer:
    """Escuta em 127.0.0.1, salvo se DIARY_BIND estiver definido para o container."""
    handler = _handler(diary)
    return ThreadingHTTPServer((_bind_host(), port), handler)


def _bind_host() -> str:
    return os.environ.get("DIARY_BIND") or _HOST


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diário local fictício, só em 127.0.0.1.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    diary = LocalDiary(args.root, model_path=args.model)
    server = serve(diary, args.port)
    print(f"http://{_bind_host()}:{args.port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
    return 0


def _actor() -> Actor:
    return Actor(user_id=LOCAL_USER, role="patient")


def _loopback_origin(origin: str) -> bool:
    """Origem explícita de loopback. Não aceita curinga, https nem outro host."""
    if not _LOOPBACK_ORIGIN.fullmatch(origin):
        return False
    parsed = urlparse(origin)
    if parsed.username or parsed.password or parsed.hostname not in {"127.0.0.1", "localhost"}:
        return False
    return parsed.port is None or 1 <= parsed.port <= 65535


def _handler(diary: LocalDiary):
    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:
            path = urlparse(self.path).path
            if not self._host_ok():
                self._json(421, {"error": "invalid_host"})
                return
            if path in {"/api/texto", "/api/historico", "/api/audio"}:
                if not _loopback_origin(self.headers.get("Origin", "")):
                    self._json(403, {"error": "forbidden"})
                    return
                self._empty(204, cors=True)
                return
            if path != "/transcrever":
                self._send(404, "não encontrado")
                return
            if not self._loopback_operator():
                self._json(403, {"error": "operator_only"})
                return
            self._empty(204, cors=True)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if not self._host_ok():
                self._json(421, {"error": "invalid_host"})
                return
            if parsed.path == "/api/historico":
                if not self._browser_allowed():
                    self._json(403, {"error": "forbidden"})
                    return
                entries, truncated = diary.api_history()
                self._json(
                    200,
                    {
                        "entries": entries,
                        "order": "oldest_first",
                        "limit": _HISTORY_LIMIT,
                        "truncated": truncated,
                    },
                )
                return
            if parsed.path != "/":
                self._json(404, {"error": "not_found"})
                return
            query = parse_qs(parsed.query)
            notice = _NOTICES.get(_one(query.get("aviso")), "")
            error = _NOTICES.get(_one(query.get("erro")), "")
            self._send(200, _page(diary.history(), notice, error), html_page=True)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if not self._host_ok():
                self._json(421, {"error": "invalid_host"})
                return
            if not self._browser_allowed():
                self._json(403, {"error": "forbidden"})
                return
            if parsed.path in {"/worker", "/transcrever"} and not self._loopback_operator():
                self._json(403, {"error": "operator_only"})
                return
            if parsed.path == "/api/texto":
                self._post_text()
                return
            if parsed.path == "/api/audio":
                self._post_api_audio()
                return
            try:
                body = self._body()
                if parsed.path == "/texto":
                    fields = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
                    diary.add_text(fields.get("texto", [""])[0])
                    self._redirect("aviso", "texto_gravado")
                elif parsed.path == "/audio":
                    entry_id = diary.add_audio_part(self.headers.get("Content-Type", ""), body)
                    if self._wants_json():
                        self._queue_saved_audio(entry_id)
                    else:
                        self._redirect("aviso", "audio_gravado")
                elif parsed.path == "/worker":
                    result = diary.transcribe_next()
                    self._redirect("aviso", "transcrito" if result else "fila_vazia")
                elif parsed.path == "/transcrever":
                    suffix = _one(parse_qs(parsed.query).get("ext"))
                    if suffix and not suffix.startswith("."):
                        suffix = f".{suffix}"
                    text = diary.preview_audio(body, suffix.lower())
                    self._send(200, text, cors=True)
                else:
                    self._json(404, {"error": "not_found"})
            except PatientDiaryError as exc:
                code = exc.code if exc.code in _NOTICES else "invalid_audio"
                path = urlparse(self.path).path
                if path == "/transcrever":
                    self._send(400, _NOTICES[code], cors=True)
                elif path == "/audio" and self._wants_json():
                    self._json(400, {"error": code})
                else:
                    self._redirect("erro", code)

        def log_message(self, fmt: str, *args) -> None:
            code = args[1] if len(args) > 1 else ""
            sys.stderr.write(f"{code}\n")

        def _post_api_audio(self) -> None:
            kind = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if kind != "multipart/form-data":
                self._json(415, {"error": "unsupported_type"})
                return
            try:
                entry_id = diary.add_audio_part(self.headers.get("Content-Type", ""), self._body())
            except PatientDiaryError as exc:
                code = exc.code if exc.code in _NOTICES else "invalid_audio"
                self._json(400, {"error": code})
                return
            self._queue_saved_audio(entry_id)

        def _loopback_operator(self) -> bool:
            """Não autentica. O navegador não dispara worker nem prévia."""
            if _bind_host() not in {"127.0.0.1", "localhost"}:
                return False
            browser = ("Origin", "Sec-Fetch-Site", "Sec-Fetch-Mode")
            return not any(self.headers.get(name) for name in browser)

        def _post_text(self) -> None:
            kind = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if kind != "application/json":
                self._json(415, {"error": "unsupported_type"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._json(400, {"error": "invalid_json"})
                return
            if length < 0 or length > _TEXT_BODY:
                self._json(413, {"error": "payload_too_large"})
                return
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json(400, {"error": "invalid_json"})
                return
            if type(payload) is not dict or type(payload.get("text")) is not str:
                self._json(400, {"error": "invalid_text"})
                return
            text = payload["text"].strip()
            if not text:
                self._json(400, {"error": "empty_text"})
                return
            if len(text) > 20_000:
                self._json(400, {"error": "text_too_long"})
                return
            try:
                entry_id = diary.add_text(text)
                entry = diary.store.get(entry_id, _actor())
            except PatientDiaryError as exc:
                code = exc.code if exc.code in {"empty_text", "text_too_long"} else "invalid_text"
                self._json(400, {"error": code})
                return
            self._json(
                201,
                {
                    "id": entry.entry_id,
                    "created_at": entry.created_at.isoformat(),
                    "kind": "written",
                    "status": entry.processing_status,
                },
            )

        def _queue_saved_audio(self, entry_id: str) -> None:
            """A resposta sai na fila. O worker local roda depois, fora do pedido."""
            entry = diary.store.get(entry_id, _actor())
            self._json(
                201,
                {
                    "id": entry.entry_id,
                    "created_at": entry.created_at.isoformat(),
                    "kind": "audio",
                    "status": "queued",
                    "duration_seconds": entry.duration_sec,
                },
            )

            def run() -> None:
                try:
                    while diary.transcribe_next():
                        pass
                except Exception:  # noqa: BLE001 — a mensagem pode citar o áudio
                    return

            threading.Thread(target=run, name="diary-worker", daemon=True).start()

        def _wants_json(self) -> bool:
            return "application/json" in self.headers.get("Accept", "").lower()

        def _host_ok(self) -> bool:
            host = self.headers.get("Host", "")
            if host.count(":") != 1:
                return False
            name, port = host.split(":", 1)
            return name in {"127.0.0.1", "localhost"} and port == str(self.server.server_address[1])

        def _browser_allowed(self) -> bool:
            """CORS não autentica. Bloqueia site externo e Host já foi checado."""
            origin = self.headers.get("Origin", "")
            if origin and not _loopback_origin(origin):
                return False
            site = self.headers.get("Sec-Fetch-Site", "")
            return not (site == "cross-site" and not origin)

        def _body(self) -> bytes:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise InvalidEntryError("invalid_audio") from None
            if length < 0 or length > _MAX_BODY:
                raise InvalidEntryError("audio_too_large")
            return self.rfile.read(length)

        def _empty(self, status: int, cors: bool) -> None:
            self.send_response(status)
            if cors:
                self._allow_local_browser()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _json(self, status: int, payload: dict[str, object]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            origin = self.headers.get("Origin", "")
            if _loopback_origin(origin):
                self._cors(origin)
            self.end_headers()
            self.wfile.write(data)

        def _cors(self, origin: str) -> None:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def _redirect(self, key: str, code: str) -> None:
            body = b""
            self.send_response(303)
            self.send_header("Location", f"/?{key}={code}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.wfile.write(body)

        def _allow_local_browser(self) -> None:
            origin = self.headers.get("Origin", "")
            if _loopback_origin(origin):
                self._cors(origin)

        def _send(self, status: int, content: str, html_page: bool = False, cors: bool = False) -> None:
            data = content.encode("utf-8")
            kind = "text/html; charset=utf-8" if html_page else "text/plain; charset=utf-8"
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            if cors:
                self._allow_local_browser()
            self.end_headers()
            self.wfile.write(data)

    return Handler


def _audio_part(content_type: str, body: bytes) -> bytes:
    marker = "boundary="
    if marker not in content_type:
        raise InvalidEntryError("invalid_audio")
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    if not boundary:
        raise InvalidEntryError("invalid_audio")
    for chunk in body.split(b"--" + boundary.encode("latin-1", "ignore")):
        if b"\r\n\r\n" not in chunk:
            continue
        header, data = chunk.split(b"\r\n\r\n", 1)
        text = header.decode("latin-1", "replace")
        if 'name="audio"' not in text and "name=audio" not in text:
            continue
        return data.removesuffix(b"\r\n").removesuffix(b"--").removesuffix(b"\r\n")
    raise InvalidEntryError("invalid_audio")


def _one(values: list[str] | None) -> str:
    return values[0] if values else ""


def _page(rows: list[dict[str, str]], notice: str, error: str) -> str:
    items = "\n".join(_row(item) for item in rows) or "<p>Nenhum registro ainda.</p>"
    banner = ""
    if notice:
        banner += f"<p>{html.escape(notice)}</p>"
    if error:
        banner += f"<p>{html.escape(error)}</p>"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Diário local fictício</title>
<style>
body {{ font-family: sans-serif; max-width: 46rem; margin: 2rem auto; line-height: 1.4; }}
form {{ margin: 1rem 0; }}
article {{ border-top: 1px solid #ccc; padding: 0.5rem 0; }}
</style>
</head>
<body>
<h1>Diário local fictício</h1>
<p>Paciente fixo deste processo: {LOCAL_USER}. Não há autenticação para uso com pacientes reais. Um identificador enviado pelo navegador é ignorado. A rede neural não está ligada.</p>
{banner}
<h2>Relato escrito</h2>
<form method="post" action="/texto">
<textarea name="texto" rows="5" maxlength="20000" required></textarea>
<p><button type="submit">Gravar relato</button></p>
</form>
<h2>Áudio</h2>
<form method="post" action="/audio" enctype="multipart/form-data">
<input type="file" name="audio" accept=".wav,.mp3,.m4a,audio/*" required>
<p><button type="submit">Enviar áudio</button></p>
</form>
<p>O envio por esta página só entra na fila. A transcrição parte na rota JSON, não daqui.</p>
<h2>Histórico</h2>
{items}
</body>
</html>"""


def _row(item: dict[str, str]) -> str:
    heading = (
        f"<p>{html.escape(item['created_at'])} · {html.escape(item['kind'])} · "
        f"{html.escape(item['label'])} ({html.escape(item['status'])})</p>"
    )
    parts = [heading]
    if item["text"]:
        parts.append(f"<p>{html.escape(item['text'])}</p>")
    if item["transcript"]:
        parts.append(f"<p>Transcrição bruta: {html.escape(item['transcript'])}</p>")
    if item["error"]:
        parts.append(f"<p>Falha: {html.escape(item['error'])}</p>")
    return "<article>" + "".join(parts) + "</article>"


if __name__ == "__main__":
    raise SystemExit(main())
