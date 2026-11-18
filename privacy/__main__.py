"""Operação local do protótipo #27, apenas com dados sintéticos."""

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet

from .client import PrivacyClient, PrivacyError
from .contracts import DEMO_DIR


def create_secret(path: Path, value: str):
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        stream.write(value + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEMO_DIR)
    parser.add_argument("--port", type=int, default=8001)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    serve = commands.add_parser("serve")
    serve.add_argument("--model-path", type=Path, required=True)
    commands.add_parser("register-demo")
    name = commands.add_parser("name")
    name.add_argument("patient_id", type=UUID)
    original = commands.add_parser("original")
    original.add_argument("patient_id", type=UUID)
    original.add_argument("record_id")
    args = parser.parse_args(argv)
    directory = args.directory
    try:
        if args.command == "init":
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            create_secret(directory / "analysis.token", secrets.token_urlsafe(32))
            create_secret(directory / "identity.token", secrets.token_urlsafe(32))
            create_secret(directory / "vault.key", Fernet.generate_key().decode("ascii"))
            return 0
        if args.command == "serve":
            import uvicorn

            from .detector import build_detector
            from .server import create_app
            from .vault import Vault

            keys = (directory / "vault.key").read_text(encoding="ascii").split()
            app = create_app(
                Vault(directory / "vault.sqlite3", keys),
                build_detector(args.model_path),
                analysis_token=(directory / "analysis.token").read_text(encoding="ascii").strip(),
                identity_token=(directory / "identity.token").read_text(encoding="ascii").strip(),
            )
            uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
            return 0
        client = PrivacyClient(directory / "identity.token", f"http://127.0.0.1:{args.port}")
        if args.command == "register-demo":
            mapping = {}
            for alias, name in {"patient_ana": "Ana de Exemplo", "patient_bruno": "Bruno de Exemplo"}.items():
                result = client.request("POST", "/v1/identity/patients", {
                    "patient_key": alias, "display_name": name, "synthetic": True,
                })
                mapping[alias] = str(UUID(result["patient_id"]))
            path = directory / "demo-patients.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(mapping), encoding="utf-8")
            temporary.replace(path)
            print(json.dumps(mapping))
        else:
            path = f"/v1/identity/patients/{args.patient_id}"
            if args.command == "original":
                from pydantic import TypeAdapter

                from .contracts import RecordId

                path += "/records/" + TypeAdapter(RecordId).validate_python(args.record_id)
            print(json.dumps(client.request("GET", path), ensure_ascii=True))
        return 0
    except (PrivacyError, ValueError, OSError, RuntimeError, ImportError, KeyError):
        print("Operação local indisponível. Confira serviço, modelo e configuração.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
