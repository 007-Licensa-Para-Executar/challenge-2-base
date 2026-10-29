from threading import Event
from types import SimpleNamespace

import httpx
import pytest
from ollama import ListResponse, ResponseError

from agents.extractor.config import Settings
from agents.extractor.contracts import MAX_INPUT_CHARS, Extraction
from agents.extractor.model import OllamaExtractor, fetch_model_metadata
from agents.extractor.sentiment import Polarity

VALID = '{"tema":"trabalho","sentimento":"tristeza","indicio_textual_risco":"nao_identificado"}'


class FakeClient:
    def __init__(self, content=VALID, exception=None):
        self.content = content
        self.exception = exception
        self.calls = []
        self.models = [{"model": "qwen3:4b", "digest": "sha256:test"}]

    def fetch_metadata(self, settings):
        if self.exception:
            raise self.exception
        return {"models": self.models}

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=self.content))


def make_extractor(client):
    return OllamaExtractor(Settings(), client, client.fetch_metadata)


def test_structured_local_request_and_metadata():
    client = FakeClient()
    result = OllamaExtractor(Settings(), client, client.fetch_metadata).extract(
        "Hoje fiquei triste no trabalho."
    )
    assert result.status == "ok"
    assert result.extraction.tema == "trabalho"
    assert result.validation.nlp_polaridade == "NEGATIVO"
    assert result.validation.nlp_score < 0
    assert not result.validation.discrepancia_detectada
    assert result.metadata.model_digest == "sha256:test"
    assert result.metadata.latency_ms >= 0
    assert result.metadata.synthetic
    call = client.calls[0]
    assert call["format"] == Extraction.model_json_schema()
    assert call["options"] == {"temperature": 0, "num_ctx": 2048, "num_predict": 160}
    assert call["think"] is False
    assert call["stream"] is False
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["content"] == "Hoje fiquei triste no trabalho."


@pytest.mark.parametrize(
    "sentiment,text,expected",
    [
        ("tristeza", "Estou feliz, ótimo e maravilhoso.", True),
        ("alegria", "Estou muito feliz com essa notícia.", False),
        ("tristeza", "Estou muito triste, péssimo e horrível.", False),
    ],
)
def test_vader_cross_validation_flags_only_extreme_opposite_polarity(sentiment, text, expected):
    content = VALID.replace('"tristeza"', f'"{sentiment}"')
    result = make_extractor(FakeClient(content)).extract(text)
    assert result.status == "ok"
    assert result.validation.discrepancia_detectada is expected
    assert 0 <= result.validation.distancia_polaridade <= 2


def test_portuguese_negation_is_handled():
    result = make_extractor(FakeClient()).extract("Não estou feliz.")
    assert result.validation.nlp_score < 0


def test_vader_analysis_runs_while_model_request_is_in_flight(monkeypatch):
    analysis_started = Event()
    release_analysis = Event()

    def analyze(text):
        analysis_started.set()
        assert release_analysis.wait(timeout=1)
        return Polarity("POSITIVO", 0.8)

    client = FakeClient()

    def chat(**kwargs):
        assert analysis_started.wait(timeout=1)
        release_analysis.set()
        return SimpleNamespace(message=SimpleNamespace(content=VALID))

    client.chat = chat
    monkeypatch.setattr("agents.extractor.model.analyze_polarity", analyze)
    result = make_extractor(client).extract("Relato sintético de teste.")
    assert result.status == "ok"


@pytest.mark.parametrize("text", ["", "  ", None, "x" * (MAX_INPUT_CHARS + 1)])
def test_invalid_input_never_calls_model(text):
    client = FakeClient()
    result = OllamaExtractor(Settings(), client, client.fetch_metadata).extract(text)
    assert result.status == "error"
    assert result.extraction is None
    assert not client.calls


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "{}",
        "[]",
        VALID[:-1] + ',"extra":true}',
        VALID.replace('"tristeza"', '"diagnostico"'),
    ],
)
def test_invalid_response_never_fabricates_extraction(content):
    result = make_extractor(FakeClient(content)).extract("relato sintético")
    assert result.error.code == "invalid_response"
    assert result.extraction is None
    assert content not in result.model_dump_json()


@pytest.mark.parametrize(
    "exception,code",
    [
        (ConnectionError("secret relato"), "service_unavailable"),
        (httpx.ConnectError("secret relato"), "service_unavailable"),
        (httpx.ReadTimeout("secret relato"), "model_timeout"),
        (ResponseError("secret relato", status_code=404), "model_not_found"),
        (ResponseError("secret relato", status_code=500), "provider_error"),
        (RuntimeError("secret relato"), "provider_error"),
    ],
)
def test_provider_errors_are_sanitized(exception, code):
    result = make_extractor(FakeClient(exception=exception)).extract("relato sintético")
    assert result.error.code == code
    assert result.extraction is None
    assert "secret relato" not in result.model_dump_json()


def test_missing_model():
    client = FakeClient()
    client.models = []
    result = OllamaExtractor(Settings(), client, client.fetch_metadata).extract("relato sintético")
    assert result.error.code == "model_not_found"
    assert not client.calls


def test_missing_digest():
    client = FakeClient()
    client.models[0]["digest"] = None
    result = OllamaExtractor(Settings(), client, client.fetch_metadata).extract("relato sintético")
    assert result.error.code == "model_metadata_error"
    assert not client.calls


def test_empty_response():
    result = make_extractor(FakeClient("")).extract("relato sintético")
    assert result.error.code == "empty_response"


def test_refusal():
    client = FakeClient()
    client.chat = lambda **kwargs: {"message": {"content": "", "refusal": "sensitive"}}
    result = OllamaExtractor(Settings(), client, client.fetch_metadata).extract("relato sintético")
    assert result.error.code == "model_refusal"
    assert "sensitive" not in result.model_dump_json()


def test_client_disables_proxy_and_redirects(monkeypatch):
    calls = []
    monkeypatch.setattr("agents.extractor.model.Client", lambda **kw: calls.append(kw))
    OllamaExtractor(Settings())
    assert calls == [
        {
            "host": "http://127.0.0.1:11434",
            "timeout": 60,
            "trust_env": False,
            "follow_redirects": False,
        }
    ]


def test_remote_model_metadata_rejected():
    client = FakeClient()
    client.models[0]["remote_host"] = "https://remote.invalid"
    result = OllamaExtractor(Settings(), client, client.fetch_metadata).extract("relato sintético")
    assert result.error.code == "remote_model_forbidden"
    assert not client.calls


def test_sdk_typed_tags_discard_remote_metadata():
    payload = {
        "models": [
            {
                "model": "qwen3:4b",
                "digest": "test",
                "remote_host": "https://remote.invalid",
                "remote_model": "remote",
            }
        ]
    }
    parsed = ListResponse.model_validate(payload)
    assert not hasattr(parsed.models[0], "remote_host")
    assert not hasattr(parsed.models[0], "remote_model")
    client = FakeClient()
    extractor = OllamaExtractor(Settings(), client, lambda settings: payload)
    assert extractor.extract("relato sintético").error.code == "remote_model_forbidden"
    assert not client.calls


def test_raw_metadata_request_preserves_remote_fields(monkeypatch):
    payload = {
        "models": [{"model": "qwen3:4b", "digest": "test", "remote_host": "https://remote.invalid"}]
    }
    options = []
    requests = []
    original_client = httpx.Client

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    def factory(**kwargs):
        options.append(kwargs)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("agents.extractor.model.httpx.Client", factory)
    assert fetch_model_metadata(Settings()) == payload
    assert str(requests[0].url) == "http://127.0.0.1:11434/api/tags"
    assert options == [{"trust_env": False, "follow_redirects": False, "timeout": 60}]


def test_utf8_byte_limit_rejected_before_model_request():
    client = FakeClient()
    result = make_extractor(client).extract("🙂" * 601)
    assert result.error.code == "input_too_long"
    assert not client.calls


@pytest.mark.parametrize("counter,expected", [(1887, "ok"), (1888, "error"), (2048, "error")])
def test_context_margin_rejects_high_prompt_counter(counter, expected):
    client = FakeClient()
    client.chat = lambda **kwargs: {"prompt_eval_count": counter, "message": {"content": VALID}}
    result = make_extractor(client).extract("relato sintético")
    assert result.status == expected
    if expected == "error":
        assert result.error.code == "context_limit"
        assert result.extraction is None
