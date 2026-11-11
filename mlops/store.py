"""Local dos artefatos de tracking em relação ao banco SQLite."""

from __future__ import annotations

from pathlib import Path

_SQLITE_PREFIX = "sqlite:///"


def sqlite_db_path(tracking_uri: str) -> Path | None:
    """Resolve o arquivo do banco quando o tracking usa SQLite em disco."""
    if not tracking_uri.startswith(_SQLITE_PREFIX):
        return None
    raw = tracking_uri.removeprefix(_SQLITE_PREFIX)
    if not raw or raw == ":memory:":
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def sqlite_artifact_uri(tracking_uri: str) -> str | None:
    """Cria o diretório irmão `<banco>-artifacts` e devolve a URI file:// dele."""
    db_path = sqlite_db_path(tracking_uri)
    if db_path is None:
        return None
    artifact_dir = db_path.parent / f"{db_path.stem}-artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir.resolve().as_uri()
