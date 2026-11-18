"""Serviço experimental em loopback. A rota analítica nunca revela identidades."""

import json
import secrets
import sqlite3
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import UUID4, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from .contracts import PatientRegistration, ProtectedText, ProtectRequest, RecordId
from .vault import VaultError

MAX_BODY_BYTES = 256_000


def create_app(vault, detector, *, analysis_token: str, identity_token: str):
    tokens = (analysis_token, identity_token)
    if (
        any(len(t) < 32 or not t.isascii() or not t.isprintable() or " " in t for t in tokens)
        or secrets.compare_digest(*tokens)
    ):
        raise ValueError("Configure credenciais locais distintas.")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def authorize(header, token):
        if not header or not secrets.compare_digest(
            header.encode("utf-8"), f"Bearer {token}".encode("ascii")
        ):
            raise HTTPException(401, "unauthorized")

    async def read_body(request, schema):
        body = bytearray()
        try:
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise HTTPException(413, "payload_too_large")
                body.extend(chunk)
            return schema.model_validate(json.loads(body))
        except (ValueError, UnicodeError):
            raise HTTPException(422, "invalid_payload") from None

    @app.exception_handler(RequestValidationError)
    async def invalid_route(_request, _error):
        return JSONResponse(status_code=422, content={"detail": "invalid_payload"})

    @app.middleware("http")
    async def prevent_caching(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValidationError)
    async def invalid_output(_request, _error):
        return JSONResponse(status_code=503, content={"detail": "privacy_unavailable"})

    @app.exception_handler(Exception)
    async def internal_error(_request, _error):
        # Wrap model/storage operations below so the server never logs exception input.
        return JSONResponse(status_code=503, content={"detail": "privacy_unavailable"})

    def protect(payload):
        spans = detector.detect(payload.text)
        title_spans = detector.detect(payload.title) if payload.title else []
        treated, title, representation = vault.protect(
            str(payload.patient_id), payload.record_id, payload.text, payload.title,
            spans, title_spans, detector.version,
        )
        return ProtectedText(
            patient_id=payload.patient_id, record_id=payload.record_id, text=treated, title=title,
            representation_id=representation, detector_version=detector.version, schema_version="1",
        )

    @app.post("/v1/pseudonymize")
    async def pseudonymize(request: Request, authorization: Annotated[str | None, Header()] = None):
        authorize(authorization, analysis_token)
        payload = await read_body(request, ProtectRequest)
        try:
            return await run_in_threadpool(protect, payload)
        except KeyError:
            raise HTTPException(404, "patient_not_found") from None
        except (VaultError, sqlite3.Error, ValidationError):
            raise HTTPException(503, "privacy_unavailable") from None
        except ValueError:
            raise HTTPException(409, "privacy_conflict") from None
        except Exception:  # noqa: BLE001 -- redact third-party detector errors
            raise HTTPException(503, "privacy_unavailable") from None

    @app.post("/v1/identity/patients")
    async def register(request: Request, authorization: Annotated[str | None, Header()] = None):
        authorize(authorization, identity_token)
        payload = await read_body(request, PatientRegistration)
        try:
            patient_id = await run_in_threadpool(
                vault.register, payload.patient_key, payload.display_name,
            )
            return {"patient_id": patient_id}
        except ValueError:
            raise HTTPException(409, "identity_conflict") from None
        except (VaultError, sqlite3.Error):
            raise HTTPException(503, "identity_unavailable") from None

    @app.get("/v1/identity/patients/{patient_id}")
    def display_name(patient_id: UUID4, authorization: Annotated[str | None, Header()] = None):
        authorize(authorization, identity_token)
        try:
            return {"display_name": vault.display_name(str(patient_id))}
        except KeyError:
            raise HTTPException(404, "patient_not_found") from None
        except (VaultError, sqlite3.Error):
            raise HTTPException(503, "identity_unavailable") from None

    @app.get("/v1/identity/patients/{patient_id}/records/{record_id}")
    def original(
        patient_id: UUID4, record_id: RecordId, authorization: Annotated[str | None, Header()] = None
    ):
        authorize(authorization, identity_token)
        try:
            return vault.original(str(patient_id), record_id)
        except KeyError:
            raise HTTPException(404, "record_not_found") from None
        except (VaultError, sqlite3.Error):
            raise HTTPException(503, "identity_unavailable") from None

    return app
