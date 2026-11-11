"""Retrieval over already scoped synthetic records: lexical BM25 or local E5.

No model is downloaded by this module. Scores are ranking values, not confidence
or evidence sufficiency guarantees. Application authorization precedes retrieval.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from .contracts import DiaryRecord, Evidence


class RetrievalError(RuntimeError):
    """Sanitized operational error, without patient text or library exceptions."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "essa",
    "esse",
    "esta",
    "este",
    "foi",
    "foram",
    "ha",
    "me",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "pela",
    "pelo",
    "por",
    "qual",
    "quais",
    "que",
    "se",
    "sua",
    "suas",
    "seu",
    "seus",
    "um",
    "uma",
    "sobre",
    "como",
    "quando",
    "relatou",
    "diarios",
    "relatos",
    "mostre",
    "diga",
    "paciente",
}


def _tokens(text: str) -> list[str]:
    """Content terms. A hyphenated compound is one term, not its fragments."""
    normalized = "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )
    terms = []
    for token in re.findall(r"\w+(?:-\w+)*", normalized):
        if "-" in token:
            parts = token.split("-")
            if all(len(part) <= 1 or part in _STOPWORDS for part in parts):
                continue
            terms.append(token)
            continue
        if len(token) > 1 and token not in _STOPWORDS:
            terms.append(token)
    return terms


def shares_content_term(question: str, quote: str) -> bool:
    """Lexical overlap of whole terms. This is not a relevance probability."""
    asked = set(_tokens(question))
    return bool(asked and asked & set(_tokens(quote)))


# Reporting words of a question, not the subject being asked about.
_QUESTION_WORDS = {
    "aconteceu",
    "aparece",
    "apareceu",
    "aparecer",
    "descrita",
    "descritas",
    "descrito",
    "descritos",
    "descreveu",
    "dita",
    "dito",
    "escreveu",
    "escrito",
    "experiencia",
    "falado",
    "falou",
    "houve",
    "mencionada",
    "mencionado",
    "mencionados",
    "onde",
    "porque",
    "quem",
    "registrada",
    "registrado",
    "registrados",
    "registrou",
    "relatada",
    "relatado",
    "relatados",
    "relatou",
}


def _question_terms(question: str, patient_id: str = "") -> set[str]:
    labels = {token for token in _tokens(patient_id.replace("_", " ")) if token != "patient"}
    return set(_tokens(question)) - _QUESTION_WORDS - labels


def supported_evidence(
    question: str, evidence: list[Evidence], patient_id: str = ""
) -> list[Evidence]:
    """Keep quotes only when one of them covers a strict majority of the question.

    shortcut: synonyms and a split with no covering quote stay unanswered, add a
    tested local embedding check when that model exists.
    """
    required = _question_terms(question, patient_id)
    if not required or not evidence:
        return []
    needed = len(required) // 2 + 1
    found = [(item, required & set(_tokens(item.quote))) for item in evidence]
    anchor: set[str] = set()
    for _item, have in found:
        if len(have) >= needed:
            anchor |= have
    if len(anchor) < needed:
        return []
    return [item for item, have in found if have & anchor]


def chunk_record(record: DiaryRecord, chunk_chars: int) -> list[Evidence]:
    """Nonoverlapping literal spans; prefer a whitespace boundary near the limit."""
    result = []
    start = 0
    text = record.original_text
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        if end < len(text):
            boundary = max(
                text.rfind(" ", start + chunk_chars // 2, end),
                text.rfind("\n", start + chunk_chars // 2, end),
            )
            if boundary > start:
                end = boundary + 1
        quote = text[start:end]
        if quote.strip():
            result.append(
                Evidence(
                    chunk_id=f"{record.record_id}:{start}:{end}",
                    record_id=record.record_id,
                    patient_id=record.patient_id,
                    recorded_at=record.recorded_at,
                    source_title=record.source_title,
                    quote=quote,
                    start_char=start,
                    end_char=end,
                    score=0.0,
                )
            )
        start = end
    return result


class Retriever:
    """Ranking of candidate chunks, never a clinical or factuality assessment."""

    def __init__(
        self,
        backend: Literal["bm25", "e5"] = "bm25",
        model_path: str | Path | None = None,
        min_score: float | None = None,
        chunk_chars: int = 600,
    ):
        if backend not in {"bm25", "e5"}:
            raise ValueError("Unknown retrieval backend")
        if not isinstance(chunk_chars, int) or chunk_chars < 20 or chunk_chars > 20000:
            raise ValueError("chunk_chars must be between 20 and 20000")
        threshold = (0.0 if backend == "bm25" else 0.55) if min_score is None else min_score
        if not math.isfinite(threshold) or threshold < 0 or (backend == "e5" and threshold > 1):
            raise ValueError("Invalid retrieval threshold")
        self.backend = backend
        self.model_path = Path(model_path).expanduser() if model_path is not None else None
        self.min_score = threshold
        self.chunk_chars = chunk_chars
        self._encoder: Any = None

    def _load_encoder(self):
        if self._encoder is not None:
            return self._encoder
        if self.model_path is None or not self.model_path.is_dir():
            raise RetrievalError("embedding_model_missing")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RetrievalError("embedding_dependency_missing") from exc
        try:
            self._encoder = SentenceTransformer(str(self.model_path), local_files_only=True)
        except Exception as exc:
            raise RetrievalError("embedding_model_unavailable") from exc
        return self._encoder

    @staticmethod
    def _bm25(chunks: list[Evidence], question: str) -> list[float]:
        docs = [_tokens(c.quote) for c in chunks]
        counts = [Counter(tokens) for tokens in docs]
        query = set(_tokens(question))
        n_docs = len(docs)
        average = sum(map(len, docs)) / max(n_docs, 1)
        if not average or not query:
            return [0.0] * n_docs
        scores = []
        for tokens, frequencies in zip(docs, counts, strict=True):
            score = 0.0
            for token in query:
                df = sum(token in doc for doc in counts)
                tf = frequencies[token]
                if not tf:
                    continue
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * len(tokens) / average))
            scores.append(score)
        return scores

    def _e5(self, chunks: list[Evidence], question: str) -> list[float]:
        encoder = self._load_encoder()
        inputs = [f"query: {question}", *[f"passage: {c.quote}" for c in chunks]]
        try:
            budget = min(512, int(encoder.max_seq_length))
            lengths = encoder.tokenizer(
                inputs,
                truncation=False,
                add_special_tokens=True,
                padding=False,
            )["input_ids"]
            if any(len(tokens) > budget for tokens in lengths):
                raise RetrievalError("embedding_input_too_long")
            vectors = encoder.encode(
                inputs,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            scores = [float(vectors[0] @ vector) for vector in vectors[1:]]
            if not all(math.isfinite(s) for s in scores):
                raise RetrievalError("embedding_invalid_response")
            return scores
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError("embedding_failed") from exc

    def search(self, records: list[DiaryRecord], question: str, top_k: int = 3) -> list[Evidence]:
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")
        if not question.strip():
            return []
        if len({r.patient_id for r in records}) > 1:
            raise RetrievalError("mixed_patient_scope")
        if len({r.record_id for r in records}) != len(records):
            raise RetrievalError("duplicate_record_id")
        chunks = [c for record in records for c in chunk_record(record, self.chunk_chars)]
        if not chunks:
            return []
        scores = (
            self._bm25(chunks, question) if self.backend == "bm25" else self._e5(chunks, question)
        )
        ranked = sorted(
            zip(scores, chunks, strict=True), key=lambda item: (-item[0], item[1].chunk_id)
        )
        return [
            chunk.model_copy(update={"score": max(0.0, score)})
            for score, chunk in ranked
            if score > 0 and score >= self.min_score
        ][:top_k]
