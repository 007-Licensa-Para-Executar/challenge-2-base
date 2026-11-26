"""Ponte local da consulta científica. O banco vem do ambiente, nunca do pedido."""

from __future__ import annotations

import json
import sys

from agents.copilot.literature import search_literature

MAX_QUERY = 2000


def parse_request(payload: object) -> tuple[str, int] | str:
    if not isinstance(payload, dict):
        return "invalid_body"
    if "db_path" in payload:
        return "db_path_forbidden"
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        return "empty_query"
    if len(query.strip()) > MAX_QUERY:
        return "query_too_long"
    top_k = payload.get("top_k", 5)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 5:
        return "invalid_top_k"
    return query.strip(), top_k


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "invalid_json"}, ensure_ascii=False))
        return 2
    parsed = parse_request(payload)
    if isinstance(parsed, str):
        print(json.dumps({"error": parsed}, ensure_ascii=False))
        return 2
    query, top_k = parsed
    print(search_literature(query, top_k).model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
