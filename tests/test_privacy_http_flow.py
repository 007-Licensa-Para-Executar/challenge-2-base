"""Exercita a fronteira HTTP, o fluxo analítico e a consulta autorizada ao original."""

import json
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from cryptography.fernet import Fernet

from agents.copilot import cli
from agents.copilot.contracts import DraftAnswer, Statement, ThemePrediction
from privacy.client import PrivacyClient, PrivacyError
from privacy.detector import FixtureDetector
from privacy.server import create_app
from privacy.vault import Vault

ANALYSIS = "A" * 48
IDENTITY = "B" * 48
NAME = "Úrsula de Exemplo"


@pytest.fixture
def service(tmp_path):
    for filename, value in (("analysis.token", ANALYSIS), ("identity.token", IDENTITY)):
        (tmp_path / filename).write_text(value, encoding="ascii")
    vault = Vault(tmp_path / "vault.sqlite3", [Fernet.generate_key().decode()])
    app = create_app(vault, FixtureDetector({NAME: "PERSON"}),
                     analysis_token=ANALYSIS, identity_token=IDENTITY)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            for _ in range(150):
                if server.started:
                    break
                if not thread.is_alive():
                    break
                time.sleep(.02)
            assert server.started
            yield url
        finally:
            server.should_exit = True
            thread.join(timeout=5)


def test_real_http_ingestion_query_and_identity(tmp_path, service, monkeypatch, capsys):
    operator = PrivacyClient(tmp_path / "identity.token", service)
    client = PrivacyClient(tmp_path / "analysis.token", service)
    patient = operator.request("POST", "/v1/identity/patients", {
        "patient_key": "demo", "display_name": NAME, "synthetic": True,
    })["patient_id"]
    path = f"/v1/identity/patients/{patient}"
    assert operator.request("GET", path) == {"display_name": NAME}
    with pytest.raises(PrivacyError, match="privacy_http_401"):
        client.request("GET", path)
    with pytest.raises(PrivacyError, match="privacy_http_401"):
        operator.protect(patient_id=patient, text=NAME)
    text = f"Minha avó {NAME} recebeu a mensagem em pessoa@example.invalid."
    time_args = ["--at", "2026-11-18T12:00:00Z"]
    flags = ["--privacy", "--privacy-dir", str(tmp_path), "--privacy-url", service,
             "--patient-id", patient]
    received = []

    def classify(record, **_kwargs):
        received.append(record.analysis_text)
        assert record.original_text is None
        return record.model_copy(update={
            "classification": ThemePrediction(status="ok", primary_theme="familia",
                                              candidate_score=0.8),
        })

    agent1_calls = []
    post = httpx.Client.post

    def ollama_post(client, url, **kwargs):
        if not url.endswith("/api/chat"):
            return post(client, url, **kwargs)
        prompt = kwargs["json"]["messages"][-1]["content"]
        assert NAME not in prompt and "example.invalid" not in prompt
        assert "Minha avó [PERSON_" in prompt and "[EMAIL]" in prompt
        agent1_calls.append(prompt)
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "message": {"content": json.dumps({
                "subtemas": [{
                    "nome": "Avó", "descricao": "Relato sobre a avó",
                    "evidencias": [{"quote_text": "Minha avó", "start_char": 0, "end_char": 9}],
                }],
                "sentimento_predominante": "nao_identificado", "score_polaridade": 0.0,
                "indicio_textual_risco": "nao_identificado",
            })},
        })

    monkeypatch.setattr(httpx.Client, "post", ollama_post)
    monkeypatch.setattr(cli, "classify_record", classify)
    assert cli.main(["ingest", "--synthetic", "--classify", "--subtopics", "--record-id", "demo1",
                     "--text", text, "--title", NAME, *time_args, *flags]) == 0
    saved = json.loads(capsys.readouterr().out)
    assert len(agent1_calls) == 1
    assert saved["agent1"]["patient_id"] == patient
    span = saved["agent1"]["subtemas"][0]["evidencias"][0]
    assert saved["treated_text"][span["start_char"]:span["end_char"]] == span["quote_text"]
    assert cli.main(["ingest", "--synthetic", "--classify", "--record-id", "demo1",
                     "--text", text, "--title", NAME, *time_args, *flags]) == 0
    assert json.loads(capsys.readouterr().out)["representation_id"] == saved["representation_id"]
    assert len(received) == 1
    assert NAME not in received[0] and "example.invalid" not in received[0]
    assert "[PERSON_" in received[0] and "[EMAIL]" in received[0]
    assert NAME not in saved["source_title"]
    assert operator.request("GET", path + "/records/demo1") == {"text": text, "title": NAME}

    class Generator:
        def __init__(self, **_):
            pass

        def generate(self, query, evidence):
            assert NAME not in query.question
            assert query.patient_id == patient
            assert evidence[0].quote == received[0]
            assert evidence[0].representation_id == saved["representation_id"]
            return DraftAnswer(statements=[
                Statement(text="Houve uma mensagem.", evidence_ids=[evidence[0].chunk_id]),
            ])

    monkeypatch.setattr(cli, "OllamaGenerator", Generator)
    assert cli.main(["ask", f"O que ocorreu com {NAME}?", *flags]) == 0
    reply = json.loads(capsys.readouterr().out)
    assert NAME not in json.dumps(reply, ensure_ascii=False)
    assert reply["status"] == "ok"
    assert all(NAME.encode() not in p.read_bytes() for p in tmp_path.glob("*.sqlite3"))
    assert text.encode() not in (tmp_path / "vault.sqlite3").read_bytes()


def test_failure_prevents_classification_and_analytics(tmp_path, service, monkeypatch, capsys):
    (tmp_path / "analysis.token").write_text("Z" * 48, encoding="ascii")
    from uuid import uuid4

    def unexpected(*_args, **_kwargs):
        pytest.fail("classificação executada depois de falhar a API")

    monkeypatch.setattr(cli, "classify_record", unexpected)
    args = ["ingest", "--synthetic", "--classify", "--subtopics", "--privacy-dir", str(tmp_path),
            "--privacy",
            "--privacy-url", service, "--patient-id", str(uuid4()), "--text", NAME,
            "--at", "2026-11-18T12:00:00Z"]
    assert cli.main(args) == 2
    out = capsys.readouterr()
    assert NAME not in out.err and "privacy_http_401" in out.err
    assert not (tmp_path / "analytics.sqlite3").exists()


def test_client_timeout_and_untrusted_targets(tmp_path, monkeypatch):
    token = tmp_path / "analysis.token"
    token.write_text(ANALYSIS, encoding="ascii")

    def timeout(*_args, **_kwargs):
        raise httpx.ReadTimeout(NAME)

    with pytest.raises(PrivacyError, match="invalid_privacy_url"):
        PrivacyClient(token, "http://example.invalid:8001")
    monkeypatch.setattr(httpx.Client, "request", timeout)
    with pytest.raises(PrivacyError, match="^privacy_timeout$"):
        PrivacyClient(token).request("POST", "/v1/pseudonymize", {})


def test_client_rejects_response_for_another_patient(tmp_path, monkeypatch):
    from uuid import uuid4

    token = tmp_path / "analysis.token"
    token.write_text(ANALYSIS, encoding="ascii")
    monkeypatch.setattr(PrivacyClient, "request", lambda *_args: {
        "patient_id": str(uuid4()), "record_id": None, "text": "tratado", "title": None,
        "representation_id": "fake", "detector_version": "fixture", "schema_version": "1",
    })
    with pytest.raises(PrivacyError, match="^invalid_privacy_contract$"):
        PrivacyClient(token).protect(patient_id=uuid4(), text="relato fictício")


def test_protected_store_never_lists_legacy_records(tmp_path):
    from datetime import UTC, datetime
    from uuid import uuid4

    from agents.copilot.contracts import DiaryRecord, Query
    from agents.copilot.storage import DiaryStore, ProtectedDiaryStore

    patient = str(uuid4())
    path = tmp_path / "diaries.sqlite3"
    raw = DiaryRecord(patient_id=patient, recorded_at=datetime.now(UTC), original_text=NAME)
    DiaryStore(path).save(raw)
    protected = ProtectedDiaryStore(path)
    assert protected.list_records(Query(patient_id=patient, question="listar")) == []
    with pytest.raises(ValueError, match="Representação incompatível"):
        protected.save(raw)
