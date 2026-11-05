"""Mecanismo de Recuperação Híbrida (BM25 + Semântica) para a Base de Conhecimento."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

from .contracts import KnowledgeChunk, RetrievedEvidence


def _normalize(text: str) -> list[str]:
    """Normaliza texto: remove acentos, pontuação e converte para minúsculas."""
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
    words = re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())
    # Stopwords básicas em português/inglês para refinar relevância
    stopwords = {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma", "os",
        "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "ao", "ele", "das", "sua",
        "the", "and", "of", "to", "in", "for", "with", "is", "that", "on", "by", "this",
    }
    return [w for w in words if w not in stopwords]


class HybridRetriever:
    """Recuperador híbrido combinando busca esparsa BM25 e similaridade de cosseno."""

    def __init__(self, corpus_path: str | Path, abstention_threshold: float = 0.12):
        self.corpus_path = Path(corpus_path)
        self.abstention_threshold = abstention_threshold
        self.chunks: list[KnowledgeChunk] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_freq: dict[str, int] = {}
        self._avg_doc_len: float = 0.0
        self._load_corpus()

    def _load_corpus(self) -> None:
        if not self.corpus_path.exists():
            raise FileNotFoundError(f"Arquivo da base de conhecimento não encontrado: {self.corpus_path}")

        self.chunks.clear()
        self._doc_tokens.clear()
        self._doc_freq.clear()

        total_length = 0
        with self.corpus_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                chunk = KnowledgeChunk.model_validate(data)
                self.chunks.append(chunk)

                # Conteúdo indexável composto
                indexable_content = (
                    f"{chunk.title} {chunk.institution} {' '.join(chunk.dimension_tags)} "
                    f"{chunk.methodology} {chunk.text} {chunk.limitations}"
                )
                tokens = _normalize(indexable_content)
                self._doc_tokens.append(tokens)
                total_length += len(tokens)

                unique_tokens = set(tokens)
                for t in unique_tokens:
                    self._doc_freq[t] = self._doc_freq.get(t, 0) + 1

        self._avg_doc_len = total_length / max(len(self.chunks), 1)

    def _score_bm25(self, query_tokens: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
        n_docs = len(self.chunks)
        scores = [0.0] * n_docs

        for token in query_tokens:
            df = self._doc_freq.get(token, 0)
            if df == 0:
                continue
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

            for idx, doc in enumerate(self._doc_tokens):
                tf = doc.count(token)
                if tf == 0:
                    continue
                doc_len = len(doc)
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (doc_len / self._avg_doc_len))
                scores[idx] += idf * (numerator / denominator)

        # Normalização linear para [0, 1]
        max_s = max(scores) if scores else 0.0
        if max_s > 0:
            return [s / max_s for s in scores]
        return scores

    def _score_dense_cosine(self, query_tokens: list[str]) -> list[float]:
        """Calcula similaridade de cosseno com vetorização TF-IDF leve em memória."""
        n_docs = len(self.chunks)
        query_set = set(query_tokens)
        scores = [0.0] * n_docs

        if not query_tokens:
            return scores

        query_counts = {t: query_tokens.count(t) for t in query_set}
        query_norm = math.sqrt(sum(c * c for c in query_counts.values()))
        if query_norm == 0:
            return scores

        for idx, doc in enumerate(self._doc_tokens):
            dot_product = 0.0
            doc_norm_sq = 0.0
            doc_counts = {t: doc.count(t) for t in set(doc)}
            for t, count in doc_counts.items():
                doc_norm_sq += count * count
                if t in query_counts:
                    dot_product += count * query_counts[t]

            doc_norm = math.sqrt(doc_norm_sq)
            if doc_norm > 0:
                scores[idx] = dot_product / (doc_norm * query_norm)

        return scores

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        collection_filter: str | None = None,
        alpha: float = 0.5,
    ) -> tuple[list[RetrievedEvidence], str]:
        """Recupera evidências relevantes combinando BM25 e similaridade de cosseno."""
        query_tokens = _normalize(query)
        if not query_tokens:
            return [], "evidencia_insuficiente"

        bm25_scores = self._score_bm25(query_tokens)
        dense_scores = self._score_dense_cosine(query_tokens)

        combined_scores: list[tuple[float, int]] = []
        for idx in range(len(self.chunks)):
            chunk = self.chunks[idx]
            if collection_filter and chunk.collection != collection_filter:
                continue

            hybrid_score = (alpha * bm25_scores[idx]) + ((1.0 - alpha) * dense_scores[idx])
            combined_scores.append((hybrid_score, idx))

        combined_scores.sort(key=lambda x: x[0], reverse=True)

        # Verificação do limiar de abstenção
        best_score = combined_scores[0][0] if combined_scores else 0.0
        if best_score < self.abstention_threshold:
            return [], "evidencia_insuficiente"

        results: list[RetrievedEvidence] = []
        for score, idx in combined_scores[:top_k]:
            if score < (self.abstention_threshold * 0.75):
                continue
            c = self.chunks[idx]
            results.append(
                RetrievedEvidence(
                    chunk_id=c.chunk_id,
                    title=c.title,
                    institution=c.institution,
                    year=c.year,
                    evidence_tier=c.evidence_tier,
                    doi_or_url=c.doi_or_url,
                    claim_ou_trecho=c.text,
                    limitacoes=c.limitations,
                )
            )

        status = "evidencia_suficiente" if len(results) >= 2 else "evidencia_parcial"
        return results, status
