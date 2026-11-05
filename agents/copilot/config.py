"""Configuração do Agente 2 e do mecanismo RAG."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CopilotSettings:
    db_path: Path = Path("data/comparacao.sqlite3")
    corpus_path: Path = Path("knowledge_base/corpus.jsonl")
    model: str = "qwen3:4b"
    top_k: int = 4
    abstention_threshold: float = 0.12
    ollama_host: str = "http://127.0.0.1:11434"
    mock_mode: bool = False

    @classmethod
    def from_env(cls) -> CopilotSettings:
        db_path = Path(os.getenv("BEM_ESTAR_DB_PATH", "data/comparacao.sqlite3"))
        corpus_path = Path(os.getenv("BEM_ESTAR_CORPUS_PATH", "knowledge_base/corpus.jsonl"))
        model = os.getenv("BEM_ESTAR_COPILOT_MODEL", os.getenv("BEM_ESTAR_MODEL", "qwen3:4b"))
        top_k = int(os.getenv("BEM_ESTAR_TOP_K", "4"))
        abstention_threshold = float(os.getenv("BEM_ESTAR_ABSTENTION_THRESHOLD", "0.12"))
        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        mock_mode = os.getenv("BEM_ESTAR_MOCK", "0").lower() in ("1", "true", "yes")

        return cls(
            db_path=db_path,
            corpus_path=corpus_path,
            model=model,
            top_k=top_k,
            abstention_threshold=abstention_threshold,
            ollama_host=ollama_host,
            mock_mode=mock_mode,
        )
