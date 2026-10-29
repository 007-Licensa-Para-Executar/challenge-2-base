"""Leitura SQLite sem criar banco nem alterar o arquivo consultado."""

import json
import sqlite3
from pathlib import Path

PAGE_SIZE = 10


def read_history(path: str | Path, page: int = 1) -> tuple[list[dict], bool]:
    if page < 1:
        raise ValueError("Página deve ser positiva")
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        return [], False
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        rows = connection.execute(
            "SELECT result_json FROM runs ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (PAGE_SIZE + 1, (page - 1) * PAGE_SIZE),
        ).fetchall()
    return [json.loads(row[0]) for row in rows[:PAGE_SIZE]], len(rows) > PAGE_SIZE
