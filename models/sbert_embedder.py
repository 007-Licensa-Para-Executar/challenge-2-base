"""Embeddings de sentença (SBERT) para diários clínicos.

Encoder pré-treinado e CONGELADO: ele só transforma texto em vetor. Quem aprende
as fronteiras de decisão é o MLP em PyTorch (models/torch_mlp.py), treinado em cima
desses vetores. Como o encoder não é ajustado com os dados do projeto, não existe
vazamento de informação entre treino/validação/teste por causa dele.

Interface compatível com `ClinicalTextEmbedder` (fit / transform / embedding_dim /
get_params), então train.py e predictor.py usam os dois do mesmo jeito.
"""

from __future__ import annotations

from typing import Any

import numpy as np

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class SBERTEmbedder:
    """Gera embeddings densos de sentença com sentence-transformers.

    Modelos testados na proposta do grupo (ambos 384 dimensões):
      - "paraphrase-multilingual-MiniLM-L12-v2"  (SBERT clássico; max_seq_length=128)
      - "intfloat/multilingual-e5-small"          (exige prefixo "query: "; 512 tokens)
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        batch_size: int = 64,
        text_prefix: str | None = None,
        max_seq_length: int | None = None,
        device: str | None = None,
        normalize_default: bool = True,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        # Modelos E5 foram treinados com prefixo; sem ele a qualidade cai.
        if text_prefix is None and "e5" in model_name.lower():
            text_prefix = "query: "
        self.text_prefix = text_prefix or ""
        self.max_seq_length = max_seq_length
        self.device = device
        self.normalize_default = normalize_default
        self._model: Any = None
        self._embedding_dim: int | None = None

    # ------------------------------------------------------------------ modelo
    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "sentence-transformers não instalado. Rode: uv sync"
                ) from exc
            self._model = SentenceTransformer(self.model_name, device=self.device)
            if self.max_seq_length:
                self._model.max_seq_length = self.max_seq_length
            self._embedding_dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    @property
    def embedding_dim(self) -> int:
        if self._embedding_dim is None:
            self._load()
        assert self._embedding_dim is not None
        return self._embedding_dim

    # --------------------------------------------------------------- interface
    def fit(self, texts: list[str] | None = None) -> SBERTEmbedder:
        """No-op: o encoder é pré-treinado. Existe só por compatibilidade com train.py."""
        self._load()
        return self

    def transform(self, texts: list[str], normalize: bool | None = None) -> np.ndarray:
        """Retorna array float32 (n_textos, embedding_dim)."""
        model = self._load()
        do_norm = self.normalize_default if normalize is None else normalize
        cleaned = [
            self.text_prefix + (t.strip() if isinstance(t, str) else "") for t in texts
        ]
        if not cleaned:
            return np.zeros((0, self.embedding_dim), dtype=np.float32)
        vectors = model.encode(
            cleaned,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=do_norm,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        return self.fit(texts).transform(texts)

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        return {
            "embedder": "sbert",
            "model_name": self.model_name,
            "embedding_dim": self._embedding_dim,
            "text_prefix": self.text_prefix,
            "max_seq_length": self.max_seq_length,
            "normalize_default": self.normalize_default,
        }

    # ------------------------------------------------- serialização (joblib)
    def __getstate__(self) -> dict[str, Any]:
        """Não serializa os pesos do SBERT (~470 MB): salva só a configuração."""
        state = self.__dict__.copy()
        state["_model"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._model = None  # recarregado sob demanda no primeiro transform()