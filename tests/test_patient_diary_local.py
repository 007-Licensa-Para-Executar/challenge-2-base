"""MVP local do diário fictício. O servidor de teste escuta só em 127.0.0.1."""

import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from agents.patient_diary import AccessDeniedError, Actor
from agents.patient_diary.local_app import (
    LOCAL_USER,
    FutureThemeInput,
    FutureThemeOutput,
    LocalDiary,
    serve,
)
from agents.patient_diary.transcribe import FakeTranscriber

PHRASE = "Relato fictício que permanece escrito."


def test_text_survives_a_new_process_and_blocks_another_actor(tmp_path):
    first = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    entry_id = first.add_text(PHRASE)
    second = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    saved = second.store.get(entry_id, Actor(user_id=LOCAL_USER, role="patient"))
    assert saved.original_text == PHRASE
    assert saved.processing_status == "ready"
    with pytest.raises(AccessDeniedError):
        second.store.get(entry_id, Actor(user_id="outra-pessoa", role="patient"))


def test_page_ignores_browser_identity_and_rejects_invalid_audio(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber("Nota sintética local."))
    page = _client(diary)
    body = urlencode({"texto": PHRASE, "patient_id": "alice"}).encode()
    page("/texto", body, "application/x-www-form-urlencoded")
    history = page("/")
    assert PHRASE in history
    assert "alice" not in history
    assert LOCAL_USER in history
    refused = page(
        "/audio",
        _multipart({"patient_id": b"alice", "audio": b"nao-e-audio"}),
        'multipart/form-data; boundary=bound',
    )
    assert "não é um WAV, MP3 ou M4A válido" in refused
    assert diary.store.list_entries(LOCAL_USER, Actor(user_id=LOCAL_USER, role="patient"))[0].input_type == "text"


def test_audio_transcript_stays_apart_from_the_written_entry(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber("Nota sintética local."))
    written = diary.add_text(PHRASE)
    diary.add_audio(_wav())
    assert diary.transcribe_next()
    assert diary.transcribe_next() is None
    rows = diary.history()
    assert rows[0]["text"] == PHRASE
    assert rows[0]["transcript"] == ""
    assert rows[1]["status"] == "ready"
    assert rows[1]["transcript"] == "Nota sintética local."
    assert rows[1]["text"] == ""
    assert diary.store.list_entries(LOCAL_USER, _patient())[1].original_text is None
    assert diary.store.get(written, _patient()).original_text == PHRASE


def test_offline_small_model_transcribes_without_replacing_the_written_text(tmp_path, monkeypatch):
    model = Path("data/models/faster-whisper-small")
    if not (model / "model.bin").is_file():
        pytest.skip("modelo local ausente")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    _block_network(monkeypatch)
    diary = LocalDiary(tmp_path, model_path=model)
    diary.add_text(PHRASE)
    diary.add_audio(_speech())
    assert diary.transcribe_next()
    rows = diary.history()
    assert rows[0]["text"] == PHRASE
    assert rows[1]["status"] == "ready"
    assert rows[1]["text"] == ""
    assert rows[1]["transcript"]


def test_local_page_has_no_remote_address_or_neural_call():
    source = Path("agents/patient_diary/local_app.py").read_text()
    assert "0.0.0.0" not in source
    assert "ClinicalTheme" not in source
    assert "huggingface.co" not in source
    assert "HF_HUB_OFFLINE" in source
    FutureThemeInput(entry_id="a1", source="transcript", text="texto fictício")
    FutureThemeOutput(status="unavailable")
    ignored = Path(".gitignore").read_text()
    assert "/data/*" in ignored
    assert "*.sqlite3" in ignored


def _block_network(monkeypatch) -> None:
    import socket

    connect = socket.socket.connect
    lookup = socket.getaddrinfo

    def guarded(self, address):
        if type(address) is not str and type(address) is not bytes:
            raise OSError(101, "rede bloqueada")
        return connect(self, address)

    def local_only(host, *args, **kwargs):
        if host not in (None, "", "localhost", "127.0.0.1", "::1"):
            raise OSError(101, "dns bloqueado")
        return lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "getaddrinfo", local_only)


def _speech() -> bytes:
    import ctypes
    import wave
    from io import BytesIO

    lib = ctypes.CDLL("libespeak-ng.so.1")
    samples: list[int] = []
    callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

    def collect(wav, count, _events):
        if count > 0 and wav:
            samples.extend(int(wav[index]) for index in range(count))
        return 0

    holder = callback(collect)
    lib.espeak_Initialize.restype = ctypes.c_int
    rate = lib.espeak_Initialize(1, 0, None, 0)
    lib.espeak_SetSynthCallback(holder)
    lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
    lib.espeak_SetVoiceByName.restype = ctypes.c_int
    lib.espeak_SetVoiceByName(b"pt-br")
    lib.espeak_SetParameter.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.espeak_SetParameter(1, 120, 0)
    text = "A paciente fictícia Marina não relatou dor."
    raw = text.encode()
    lib.espeak_Synth.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.c_void_p,
    ]
    uid = ctypes.c_uint(0)
    lib.espeak_Synth(raw, len(raw) + 1, 0, 0, 0, 1, ctypes.byref(uid), None)
    lib.espeak_Synchronize()
    buffer = BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"".join(int(sample).to_bytes(2, "little", signed=True) for sample in samples))
    return buffer.getvalue()


def _patient() -> Actor:
    return Actor(user_id=LOCAL_USER, role="patient")


def _wav() -> bytes:
    import math
    import struct
    import wave
    from io import BytesIO

    buffer = BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(index / 8))) for index in range(1600)
        )
        handle.writeframes(frames)
    return buffer.getvalue()


def _multipart(fields: dict[str, bytes]) -> bytes:
    chunks = []
    for name, payload in fields.items():
        chunks.append(
            b'--bound\r\nContent-Disposition: form-data; name="'
            + name.encode()
            + b'"\r\n\r\n'
            + payload
            + b"\r\n"
        )
    chunks.append(b"--bound--\r\n")
    return b"".join(chunks)


def _client(diary: LocalDiary):
    server = serve(diary, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    def request(path: str, body: bytes | None = None, content_type: str | None = None) -> str:
        target = f"http://127.0.0.1:{port}{path}"
        headers = {"Content-Type": content_type} if content_type else {}
        call = Request(target, data=body, headers=headers, method="POST" if body is not None else "GET")
        try:
            with urlopen(call, timeout=10) as response:
                return response.read().decode()
        except HTTPError as exc:
            return exc.read().decode()

    request.server = server  # type: ignore[attr-defined]
    return request


@pytest.fixture(autouse=True)
def _close_servers():
    servers: list[ThreadingHTTPServer] = []
    original = serve

    def tracked(diary: LocalDiary, port: int = 8765):
        server = original(diary, port)
        servers.append(server)
        return server

    globals()["serve"] = tracked
    yield
    globals()["serve"] = original
    for server in servers:
        server.shutdown()
        server.server_close()
