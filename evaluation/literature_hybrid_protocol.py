"""Protocolo do ensaio semântico. Congelado em 2026-11-24, antes de qualquer E5.

Não baixa modelo nem grava vetor. Os pesos da fusão ficam iguais e o k do RRF
fica em 60. Mexer nisso depois de ver a validação invalida o ensaio.
"""

from __future__ import annotations

from pathlib import Path

VALIDATION = (
    Path(__file__).resolve().parent.parent
    / "knowledge_base/literature/benchmark/validation_directed.jsonl"
)
VALIDATION_SHA256 = "6faaaaf48c5e028fb201fe1063f3ae76ee40401caa3d7bbceb71b7f31d732cca"
MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_DIR = Path("tmp/models/multilingual-e5-small")
TOKEN_BUDGET = 512
# shortcut: k do Cormack e peso igual; recalibrar só com outro conjunto, não com este.
RRF_K = 60
STRATEGIES = ("bm25", "e5", "hybrid_rrf", "hybrid_rrf_gated")


def embedding_cache_key(
    document_id: str,
    text_hash: str,
    chunk_id: str,
    model_revision: str,
) -> tuple[str, str, str, str]:
    """Identidade em memória. Outro hash ou outra revisão não reaproveita o vetor."""
    if not all((document_id, text_hash, chunk_id, model_revision)):
        raise ValueError("cache de embedding incompleto")
    return (document_id, text_hash, chunk_id, model_revision)


def assert_token_budget(lengths: list[tuple[str, int]], budget: int = TOKEN_BUDGET) -> None:
    """Recusa o ensaio se algum trecho não cabe. Não corta o texto."""
    overflow = [chunk_id for chunk_id, length in lengths if length > budget]
    if overflow:
        raise ValueError(f"trecho acima de {budget} tokens: {overflow[0]}")


def reciprocal_rank_fusion(rankings: list[list[str]], *, k: int = RRF_K) -> list[str]:
    """Junta listas já ordenadas. Cada lista pesa um. Não usa a nota bruta."""
    if k < 1:
        raise ValueError("k do RRF inválido")
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(chunk_id, len(first_seen))
    return sorted(scores, key=lambda chunk_id: (-scores[chunk_id], first_seen[chunk_id]))
