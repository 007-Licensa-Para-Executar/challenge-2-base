"""HTTP local com credencial limitada à pseudonimização."""

from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .contracts import DEFAULT_URL, ProtectedText, ProtectRequest


class PrivacyError(Exception):
    """Código operacional público, sem conteúdo do relato."""


class PrivacyClient:
    def __init__(self, token_file: Path, url: str = DEFAULT_URL, *, timeout=10):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or parsed.port is None or parsed.port == 0
        ):
            raise PrivacyError("invalid_privacy_url")
        try:
            token = token_file.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            raise PrivacyError("privacy_credentials_unavailable") from None
        if len(token) < 32 or not token.isascii() or not token.isprintable() or " " in token:
            raise PrivacyError("invalid_privacy_credentials")
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.token = token

    def request(self, method, path, payload=None):
        try:
            with httpx.Client(
                timeout=self.timeout, trust_env=False, follow_redirects=False,
                headers={"Authorization": f"Bearer {self.token}"},
            ) as client:
                response = client.request(method, self.url + path, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise PrivacyError("privacy_timeout") from None
        except httpx.HTTPStatusError as error:
            raise PrivacyError(f"privacy_http_{error.response.status_code}") from None
        except httpx.RequestError:
            raise PrivacyError("privacy_unavailable") from None
        except ValueError:
            raise PrivacyError("invalid_privacy_response") from None

    def protect(self, **fields):
        try:
            request = ProtectRequest(synthetic=True, **fields)
            result = ProtectedText.model_validate(self.request(
                "POST", "/v1/pseudonymize", request.model_dump(mode="json"),
            ))
            if (
                result.patient_id != request.patient_id or result.record_id != request.record_id
                or (result.title is None) != (request.title is None)
                or not result.text.strip()
            ):
                raise ValueError("scope")
            return result
        except ValueError:
            raise PrivacyError("invalid_privacy_contract") from None
