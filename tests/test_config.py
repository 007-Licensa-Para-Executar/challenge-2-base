import pytest

from agents.extractor.config import Settings


def test_defaults(monkeypatch):
    for name in [
        "EXTRACTOR_MODEL",
        "OLLAMA_HOST",
        "EXTRACTOR_CONTEXT_TOKENS",
        "EXTRACTOR_TIMEOUT_SECONDS",
        "EXTRACTOR_DB_PATH",
    ]:
        monkeypatch.delenv(name, raising=False)
    assert Settings.from_env() == Settings()


def test_environment(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_MODEL", "gemma3:4b")
    monkeypatch.setenv("EXTRACTOR_CONTEXT_TOKENS", "2048")
    monkeypatch.setenv("EXTRACTOR_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("EXTRACTOR_DB_PATH", "custom.sqlite3")
    settings = Settings.from_env()
    assert settings.model == "gemma3:4b"
    assert settings.context_tokens == 2048
    assert settings.timeout_seconds == 15
    assert settings.db_path == "custom.sqlite3"


@pytest.mark.parametrize(
    "host",
    [
        "https://example.com",
        "http://10.0.0.1:11434",
        "http://localhost.evil",
        "http://user:secret@localhost",
        "http://localhost/path",
        "http://localhost?x=1",
        "http://localhost:bad",
        "http://127.0.0.2",
    ],
)
def test_non_local_hosts_rejected(host):
    with pytest.raises(ValueError):
        Settings(host=host)


@pytest.mark.parametrize(
    "host", ["http://localhost:11434", "http://127.0.0.1:11434", "http://[::1]:11434"]
)
def test_loopback_hosts_allowed(host):
    assert Settings(host=host).host == host


@pytest.mark.parametrize(
    "changes",
    [
        {"context_tokens": 512},
        {"context_tokens": 5000},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": float("inf")},
        {"model": ""},
        {"model": "qwen:cloud"},
        {"db_path": " "},
    ],
)
def test_invalid_settings(changes):
    with pytest.raises(ValueError):
        Settings(**changes)


def test_bad_numeric_environment_sanitized(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_TIMEOUT_SECONDS", "secret")
    with pytest.raises(ValueError) as exc:
        Settings.from_env()
    assert "secret" not in str(exc.value)
