"""JSON local de relato e histórico. O banco do teste é um diretório vazio."""

import json
import sqlite3
import threading
import time
from datetime import UTC, datetime
from http.client import HTTPConnection

import pytest

from agents.patient_diary import AccessDeniedError, Actor
from agents.patient_diary.contracts import parse_entry
from agents.patient_diary.local_app import _HISTORY_LIMIT, LOCAL_USER, LocalDiary, serve
from agents.patient_diary.transcribe import FakeTranscriber

PHRASE = "Relato fictício gravado pela API."


def test_text_is_saved_and_survives_a_new_store(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    server = _serve(diary)
    created = _json(
        server,
        "POST",
        "/api/texto",
        {"text": f"  {PHRASE}  ", "patient_id": "alice", "mood": "triste"},
        {"Origin": "http://127.0.0.1:5000"},
    )
    assert created["status"] == 201
    assert created["headers"]["access-control-allow-origin"] == "http://127.0.0.1:5000"
    assert "*" not in created["headers"].get("access-control-allow-origin", "")
    body = created["json"]
    assert body["kind"] == "written"
    assert body["status"] == "ready"
    assert body["created_at"].endswith("+00:00")
    assert "patient_id" not in body
    again = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    saved = again.store.get(body["id"], Actor(user_id=LOCAL_USER, role="patient"))
    assert saved.original_text == PHRASE
    assert saved.patient_id == LOCAL_USER
    row = sqlite3.connect(tmp_path / "diary.sqlite3").execute(
        "SELECT patient_id, original_text, audio_path, claim_token FROM patient_entries"
    ).fetchone()
    assert row == (LOCAL_USER, PHRASE, None, None)
    with pytest.raises(AccessDeniedError):
        again.store.get(body["id"], Actor(user_id="alice", role="patient"))


def test_text_rejects_empty_invalid_and_oversized_bodies(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    server = _serve(diary)
    assert _json(server, "POST", "/api/texto", {"text": "   "})["json"]["error"] == "empty_text"
    invalid = _send(server, "POST", "/api/texto", b"{", {"Content-Type": "application/json"})
    assert invalid["status"] == 400
    assert invalid["json"]["error"] == "invalid_json"
    assert "Traceback" not in invalid["body"]
    assert _json(server, "POST", "/api/texto", {"text": 1})["json"]["error"] == "invalid_text"
    long = _json(server, "POST", "/api/texto", {"text": "a" * 20_001})
    assert long["status"] == 400
    assert long["json"]["error"] == "text_too_long"
    huge = _send(
        server,
        "POST",
        "/api/texto",
        b"{}",
        {"Content-Type": "application/json", "Content-Length": str(_HISTORY_LIMIT * 2000)},
    )
    assert huge["status"] == 413
    assert diary.store.list_entries(LOCAL_USER, _patient()) == []


def test_history_is_oldest_first_and_keeps_a_legacy_audio(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    when = datetime(2020, 1, 1, 12, tzinfo=UTC)
    for entry_id in ("b", "a"):
        diary.store.create(
            parse_entry(
                entry_id=entry_id,
                patient_id=LOCAL_USER,
                author_user_id=LOCAL_USER,
                created_at=when,
                original_text=f"texto {entry_id}",
                consent_id="consent-local",
            ),
            _patient(),
        )
    audio = diary.add_audio(_wav())
    before = diary.store.get(audio, _patient())
    server = _serve(diary)
    empty = LocalDiary(tmp_path / "vazio", transcriber=FakeTranscriber())
    assert _json(_serve(empty), "GET", "/api/historico")["json"]["entries"] == []
    history = _json(server, "GET", "/api/historico?patient_id=alice")
    assert history["json"]["order"] == "oldest_first"
    assert [item["id"] for item in history["json"]["entries"][:2]] == ["a", "b"]
    legacy = history["json"]["entries"][2]
    assert legacy["kind"] == "audio"
    assert legacy["status"] == "queued"
    assert legacy["text"] == ""
    assert legacy["transcript"] == ""
    assert legacy["duration_seconds"] > 0
    raw = history["body"]
    for hidden in ("patient_id", "audio_path", "claim_token", "sha256", "consent"):
        assert hidden not in raw
    after = diary.store.get(audio, _patient())
    assert after.processing_status == before.processing_status
    assert after.audio_sha256 == before.audio_sha256


def test_history_returns_only_the_newest_hundred(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    when = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(_HISTORY_LIMIT + 1):
        diary.store.create(
            parse_entry(
                entry_id=f"e{index:03d}",
                patient_id=LOCAL_USER,
                author_user_id=LOCAL_USER,
                created_at=when.replace(minute=index % 60, hour=index // 60),
                original_text=f"texto {index}",
                consent_id="consent-local",
            ),
            _patient(),
        )
    body = _json(_serve(diary), "GET", "/api/historico")["json"]
    assert body["truncated"] is True
    assert body["limit"] == _HISTORY_LIMIT
    assert len(body["entries"]) == _HISTORY_LIMIT
    assert body["entries"][0]["id"] == "e001"
    assert body["entries"][-1]["id"] == "e100"


def test_cross_origin_writes_and_foreign_hosts_are_refused(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber())
    server = _serve(diary)
    evil = {"Origin": "https://evil.example", "Content-Type": "text/plain", "Sec-Fetch-Site": "cross-site"}
    refused = _send(server, "POST", "/api/texto", b'{"text":"invasao"}', evil)
    assert refused["status"] == 403
    assert "access-control-allow-origin" not in refused["headers"]
    form = _send(
        server,
        "POST",
        "/texto",
        b"texto=invasao",
        {"Origin": "http://evil.example", "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert form["status"] == 403
    plain = _send(
        server,
        "POST",
        "/api/texto",
        b'{"text":"invasao"}',
        {"Origin": "http://127.0.0.1:5000", "Content-Type": "text/plain"},
    )
    assert plain["status"] == 415
    host = _send(server, "GET", "/api/historico", None, {"Host": "evil.example"})
    assert host["status"] == 421
    assert host["json"]["error"] == "invalid_host"
    preflight = _send(
        server,
        "OPTIONS",
        "/api/texto",
        None,
        {"Origin": "http://localhost:1234", "Access-Control-Request-Method": "POST"},
    )
    assert preflight["status"] == 204
    assert preflight["headers"]["access-control-allow-origin"] == "http://localhost:1234"
    blocked = _send(server, "OPTIONS", "/api/historico", None, {"Origin": "http://evil.example"})
    assert blocked["status"] == 403
    assert "access-control-allow-origin" not in blocked["headers"]
    assert diary.history() == []


def test_json_audio_is_queued_and_the_worker_saves_its_transcript(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber("Fala fictícia do arquivo."))
    server = _serve(diary)
    written = _json(server, "POST", "/api/texto", {"text": PHRASE})
    created = _send(
        server,
        "POST",
        "/audio",
        _multipart({"audio": _wav(), "patient_id": b"alice"}),
        {
            "Content-Type": "multipart/form-data; boundary=bound",
            "Accept": "application/json",
        },
    )
    assert created["status"] == 201
    assert created["json"]["kind"] == "audio"
    assert created["json"]["status"] == "queued"
    for hidden in ("patient_id", "audio_path", "claim_token", "sha256"):
        assert hidden not in created["body"]
    audio_id = created["json"]["id"]
    saved = _wait_audio(server, audio_id)
    assert saved["status"] == "ready"
    assert saved["transcript"] == "Fala fictícia do arquivo."
    assert saved["text"] == ""
    history = _json(server, "GET", "/api/historico")["json"]["entries"]
    assert [item["id"] for item in history] == [written["json"]["id"], audio_id]
    assert history[0]["text"] == PHRASE
    row = sqlite3.connect(tmp_path / "diary.sqlite3").execute(
        "SELECT entry_id FROM transcripts"
    ).fetchone()
    assert row == (audio_id,)


def test_failed_transcription_does_not_invent_text(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber(fail=True))
    server = _serve(diary)
    created = _send(
        server,
        "POST",
        "/audio",
        _multipart({"audio": _wav()}),
        {
            "Content-Type": "multipart/form-data; boundary=bound",
            "Accept": "application/json",
        },
    )
    saved = _wait_audio(server, created["json"]["id"])
    assert saved["status"] == "failed"
    assert saved["transcript"] == ""
    assert "audio_path" not in _json(server, "GET", "/api/historico")["body"]


def test_api_audio_is_json_and_the_browser_cannot_run_the_worker(tmp_path, monkeypatch):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber("Fala da rota nova."))
    server = _serve(diary)
    created = _send(
        server,
        "POST",
        "/api/audio",
        _multipart({"audio": _wav(), "patient_id": b"alice"}),
        {"Content-Type": "multipart/form-data; boundary=bound"},
    )
    assert created["status"] == 201
    assert created["json"]["status"] == "queued"
    assert "Accept" not in created["body"]
    audio_id = created["json"]["id"]
    saved = _wait_audio(server, audio_id)
    assert saved["status"] == "ready"
    assert saved["transcript"] == "Fala da rota nova."
    row = sqlite3.connect(tmp_path / "diary.sqlite3").execute(
        "SELECT patient_id FROM patient_entries WHERE entry_id = ?",
        (audio_id,),
    ).fetchone()
    assert row == (LOCAL_USER,)
    with pytest.raises(AccessDeniedError):
        diary.store.get(audio_id, Actor(user_id="alice", role="patient"))
    again = _serve(LocalDiary(tmp_path, transcriber=FakeTranscriber()))
    restarted = _json(again, "GET", "/api/historico")["json"]["entries"]
    assert restarted[-1]["id"] == audio_id
    assert restarted[-1]["transcript"] == "Fala da rota nova."
    time.sleep(0.4)
    refused_type = _send(
        server,
        "POST",
        "/api/audio",
        b"{}",
        {"Content-Type": "application/json"},
    )
    assert refused_type["status"] == 415
    assert refused_type["json"]["error"] == "unsupported_type"
    invalid = _send(
        server,
        "POST",
        "/api/audio",
        _multipart({"audio": b"nao-e-audio"}),
        {"Content-Type": "multipart/form-data; boundary=bound"},
    )
    assert invalid["status"] == 400
    assert invalid["json"]["error"] == "invalid_audio"
    legacy = _send(
        server,
        "POST",
        "/audio",
        _multipart({"audio": _wav(800)}),
        {"Content-Type": "multipart/form-data; boundary=bound"},
    )
    assert legacy["status"] == 303
    assert legacy["headers"]["location"].endswith("audio_gravado")
    time.sleep(0.2)
    assert diary.history()[-1]["status"] == "queued"
    browser = {
        "Origin": "http://localhost:3000",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "cors",
    }
    blocked = _send(server, "POST", "/worker", b"", browser)
    preview = _send(server, "POST", "/transcrever?ext=wav", _wav(), browser)
    assert blocked["status"] == preview["status"] == 403
    assert blocked["json"]["error"] == preview["json"]["error"] == "operator_only"
    assert diary.history()[-1]["status"] == "queued"
    monkeypatch.setenv("DIARY_BIND", "0.0.0.0")
    public = _send(server, "POST", "/worker", b"", {})
    assert public["status"] == 403
    assert diary.history()[-1]["transcript"] == ""
    monkeypatch.setenv("DIARY_BIND", "127.0.0.1")
    done = _send(server, "POST", "/worker", b"", {})
    assert done["status"] == 303
    assert done["headers"]["location"].endswith("transcrito")
    assert diary.history()[-1]["status"] == "ready"
    preflight = _send(
        server,
        "OPTIONS",
        "/api/audio",
        None,
        {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert preflight["status"] == 204


def test_html_audio_stays_queued_until_the_existing_worker_button(tmp_path):
    diary = LocalDiary(tmp_path, transcriber=FakeTranscriber("não deve rodar"))
    server = _serve(diary)
    response = _send(
        server,
        "POST",
        "/audio",
        _multipart({"audio": _wav()}),
        {"Content-Type": "multipart/form-data; boundary=bound"},
    )
    assert response["status"] == 303
    time.sleep(0.2)
    assert diary.history()[0]["status"] == "queued"
    assert diary.history()[0]["transcript"] == ""


def _wait_audio(server, entry_id: str) -> dict:
    last = {}
    for _ in range(50):
        rows = _json(server, "GET", "/api/historico")["json"]["entries"]
        last = next(item for item in rows if item["id"] == entry_id)
        if last["status"] in {"ready", "failed"}:
            return last
        time.sleep(0.05)
    return last


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


def _patient() -> Actor:
    return Actor(user_id=LOCAL_USER, role="patient")


def _serve(diary: LocalDiary):
    server = serve(diary, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _json(server, method: str, path: str, payload: dict | None = None, headers: dict | None = None):
    body = None if payload is None else json.dumps(payload).encode()
    sent = {"Content-Type": "application/json"} if payload is not None else {}
    sent.update(headers or {})
    response = _send(server, method, path, body, sent)
    return response


def _send(server, method: str, path: str, body: bytes | None, headers: dict[str, str]):
    connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    parsed = {
        "status": response.status,
        "headers": {key.lower(): value for key, value in response.getheaders()},
    }
    text = raw.decode()
    parsed["body"] = text
    if text.startswith(("{", "[")):
        parsed["json"] = json.loads(text)
    connection.close()
    return parsed


def _wav(samples: int = 1600) -> bytes:
    import math
    import struct
    import wave
    from io import BytesIO

    buffer = BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        frames = (struct.pack("<h", int(8000 * math.sin(index / 8))) for index in range(samples))
        handle.writeframes(b"".join(frames))
    return buffer.getvalue()
