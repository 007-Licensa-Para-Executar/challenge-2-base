"""Vetorizador de Embeddings Neurais Densos para Diários Clínicos.

Substitui a abordagem esparsa TF-IDF por representações vetoriais contínuas (Embeddings),
aplicando boas práticas consagradas de Deep Learning e Redes Neurais:
- Tokenização clínica robusta (limpeza, pontuação, acentuação e suporte a português);
- Gerenciamento de vocabulário com tokens reservados:
    * <PAD> (índice 0): preenchimento para sequências de comprimento variável;
    * <UNK> (índice 1): salvaguarda para palavras fora do vocabulário (Out-Of-Vocabulary / OOV);
- Inicialização paramétrica dos pesos de embedding segundo He/Xavier Normal;
- Agregação vetorial por Mean Pooling mascarado (desconsiderando tokens <PAD>);
- Normalização L2 na hiperesfera unitária (garante geometria consistente de similaridade de cosseno);
- Ajuste e atualização de pesos de embedding end-to-end via retropropagação (PyTorch);
- Serialização padronizada com joblib e compatibilidade scikit-learn.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

import numpy as np
import torch
from sklearn.decomposition import TruncatedSVD

PORTUGUESE_STOPWORDS: list[str] = [
    "de",
    "a",
    "o",
    "que",
    "e",
    "do",
    "da",
    "em",
    "um",
    "para",
    "com",
    "nao",
    "não",
    "uma",
    "os",
    "no",
    "se",
    "na",
    "por",
    "mais",
    "as",
    "dos",
    "como",
    "mas",
    "foi",
    "ao",
    "ele",
    "das",
    "tem",
    "seu",
    "sua",
    "ou",
    "ser",
    "quando",
    "muito",
    "nos",
    "já",
    "ja",
    "eu",
    "também",
    "tambem",
    "só",
    "so",
    "pelo",
    "pela",
    "até",
    "ate",
    "isso",
    "ela",
    "entre",
    "era",
    "depois",
    "sem",
    "mesmo",
    "aos",
    "ter",
    "seus",
    "quem",
    "nas",
    "me",
    "esse",
    "eles",
    "estão",
    "estao",
    "você",
    "voce",
    "tinha",
    "foram",
    "essa",
    "num",
    "nem",
    "suas",
    "meu",
    "minha",
    "numa",
    "pelos",
    "elas",
    "havia",
    "seja",
    "qual",
    "será",
    "sera",
    "tenho",
    "lhe",
    "deles",
    "essas",
    "esses",
    "pelas",
    "este",
    "fosse",
    "dele",
    "tu",
    "te",
    "vocês",
    "voces",
    "lhes",
    "meus",
    "minhas",
    "teu",
    "tua",
    "teus",
    "tuas",
    "nosso",
    "nossa",
    "nossos",
    "nossas",
    "dela",
    "delas",
    "esta",
    "está",
    "estava",
    "estou",
    "estive",
    "estivemos",
    "estavam",
    "tive",
    "tivemos",
    "tiveram",
    "teve",
    "tinham",
    "toda",
    "todo",
    "todos",
    "todas",
]


class ClinicalTextEmbedder:
    """Extrator de Embeddings textuais densos para relatos clínicos."""

    PAD_TOKEN = "<PAD>"
    UNK_TOKEN = "<UNK>"
    PAD_IDX = 0
    UNK_IDX = 1

    @staticmethod
    def _strip_accents(text: str) -> str:
        """Remove diacríticos e acentuações para normalização clínica em português."""
        return "".join(
            c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
        )

    def __init__(
        self,
        embedding_dim: int = 128,
        max_features: int = 1024,
        stop_words: list[str] | None = None,
        random_state: int = 42,
        init_strategy: Literal["gaussian", "svd"] = "gaussian",
        use_idf_weighting: bool = True,
    ) -> None:
        self.embedding_dim = embedding_dim
        self.max_features = max_features
        self.stop_words = {self._strip_accents(w) for w in stop_words} if stop_words else set()
        self.random_state = random_state
        self.init_strategy = init_strategy
        self.use_idf_weighting = use_idf_weighting

        self.vocab: dict[str, int] = {self.PAD_TOKEN: self.PAD_IDX, self.UNK_TOKEN: self.UNK_IDX}
        self.inverse_vocab: dict[int, str] = {
            self.PAD_IDX: self.PAD_TOKEN,
            self.UNK_IDX: self.UNK_TOKEN,
        }
        self.word_counts: dict[str, int] = {}
        self.idf_weights: dict[str, float] = {}
        self.embedding_matrix: np.ndarray | None = None
        self._is_fitted: bool = False

    @property
    def vocabulary_(self) -> dict[str, int]:
        """Propriedade para compatibilidade com a interface de scikit-learn."""
        return self.vocab

    def _tokenize(self, text: str) -> list[str]:
        if not isinstance(text, str):
            return []
        cleaned = self._strip_accents(text)
        tokens = re.findall(r"\b[a-z0-9_]+\b", cleaned)
        if self.stop_words:
            tokens = [t for t in tokens if t not in self.stop_words]
        return tokens

    def fit(self, texts: list[str]) -> ClinicalTextEmbedder:
        """Constrói o vocabulário e inicializa a matriz de embeddings contínuos."""
        counts: dict[str, int] = {}
        doc_counts: dict[str, int] = {}
        tokenized_docs: list[list[str]] = []

        for text in texts:
            toks = self._tokenize(text)
            tokenized_docs.append(toks)
            for token in toks:
                counts[token] = counts.get(token, 0) + 1
            for token in set(toks):
                doc_counts[token] = doc_counts.get(token, 0) + 1

        self.word_counts = counts
        # Ordena por frequência decrescente
        sorted_tokens = sorted(counts.keys(), key=lambda t: counts[t], reverse=True)
        # Limita a max_features (descontando PAD e UNK)
        max_allowed = max(0, self.max_features - 2)
        top_tokens = sorted_tokens[:max_allowed]

        self.vocab = {self.PAD_TOKEN: self.PAD_IDX, self.UNK_TOKEN: self.UNK_IDX}
        for idx, token in enumerate(top_tokens, start=2):
            self.vocab[token] = idx
        self.inverse_vocab = {idx: token for token, idx in self.vocab.items()}

        # Calcula pesos IDF suavizados
        n_docs = max(1, len(texts))
        self.idf_weights = {
            token: float(np.log((n_docs + 1.0) / (doc_counts.get(token, 0) + 1.0)) + 1.0)
            for token in self.vocab.keys()
        }
        self.idf_weights[self.PAD_TOKEN] = 0.0
        self.idf_weights[self.UNK_TOKEN] = 1.0

        rng = np.random.RandomState(self.random_state)
        vocab_size = len(self.vocab)

        # Inicialização com Semântica Distribucional (TruncatedSVD sobre co-ocorrência termo-documento)
        initialized_svd = False
        self._svd_model: TruncatedSVD | None = None
        if (
            self.init_strategy == "svd"
            and len(texts) >= self.embedding_dim
            and vocab_size > self.embedding_dim + 2
        ):
            try:
                # Constrói matriz documento-termo TF-IDF: shape (n_docs, vocab_size)
                doc_term = np.zeros((len(texts), vocab_size), dtype=np.float32)
                for d_idx, doc_toks in enumerate(tokenized_docs):
                    doc_tok_counts: dict[str, int] = {}
                    for t in doc_toks:
                        if t in self.vocab:
                            doc_tok_counts[t] = doc_tok_counts.get(t, 0) + 1
                    for t, cnt in doc_tok_counts.items():
                        v_idx = self.vocab[t]
                        # Sublinear TF * IDF
                        tf = 1.0 + np.log(cnt)
                        doc_term[d_idx, v_idx] = tf * self.idf_weights.get(t, 1.0)

                self._svd_model = TruncatedSVD(
                    n_components=self.embedding_dim, random_state=self.random_state
                )
                self._svd_model.fit(doc_term)
                # Os pesos de embedding por palavra correspondem aos componentes LSA: shape (vocab_size, embedding_dim)
                self.embedding_matrix = self._svd_model.components_.T.astype(np.float32)
                self.embedding_matrix[self.PAD_IDX] = 0.0
                if vocab_size > 2:
                    self.embedding_matrix[self.UNK_IDX] = (
                        np.mean(self.embedding_matrix[2:], axis=0) * 0.1
                    ).astype(np.float32)
                initialized_svd = True
            except Exception:
                initialized_svd = False
                self._svd_model = None

        if not initialized_svd:
            # Inicialização He / Xavier Normal para os pesos dos embeddings
            scale = np.sqrt(1.0 / self.embedding_dim)
            self.embedding_matrix = (
                rng.randn(vocab_size, self.embedding_dim) * scale
            ).astype(np.float32)
            self.embedding_matrix[self.PAD_IDX] = 0.0

        self._is_fitted = True
        return self

    def text_to_indices(self, text: str) -> list[int]:
        """Converte o texto em uma sequência de índices inteiros do vocabulário."""
        tokens = self._tokenize(text)
        if not tokens:
            return []
        return [self.vocab.get(token, self.UNK_IDX) for token in tokens]

    def texts_to_padded_tensor(self, texts: list[str], max_len: int | None = None) -> torch.Tensor:
        """Converte lista de textos em tensor 2D de índices inteiros com padding."""
        sequences = [self.text_to_indices(t) for t in texts]
        if not sequences or all(len(s) == 0 for s in sequences):
            return torch.zeros((len(texts), 1), dtype=torch.long)

        longest = max(len(s) for s in sequences)
        limit = min(longest, max_len) if max_len else longest
        limit = max(1, limit)

        padded = np.zeros((len(texts), limit), dtype=np.int64)
        for i, seq in enumerate(sequences):
            if seq:
                trunc = seq[:limit]
                padded[i, : len(trunc)] = trunc
            else:
                padded[i, 0] = self.UNK_IDX

        return torch.tensor(padded, dtype=torch.long)

    def transform(self, texts: list[str], normalize: bool = False) -> np.ndarray:
        """Converte uma lista de textos em representações densas de embeddings."""
        if not self._is_fitted or self.embedding_matrix is None:
            raise RuntimeError(
                "ClinicalTextEmbedder precisa ser ajustado com fit() antes de transform()."
            )

        svd_model = getattr(self, "_svd_model", None)
        if svd_model is not None and self.init_strategy == "svd":
            vocab_size = len(self.vocab)
            doc_term = np.zeros((len(texts), vocab_size), dtype=np.float32)
            for d_idx, text in enumerate(texts):
                toks = self._tokenize(text)
                tok_cnt: dict[str, int] = {}
                for t in toks:
                    if t in self.vocab:
                        tok_cnt[t] = tok_cnt.get(t, 0) + 1
                for t, cnt in tok_cnt.items():
                    v_idx = self.vocab[t]
                    tf = 1.0 + np.log(cnt)
                    doc_term[d_idx, v_idx] = tf * self.idf_weights.get(t, 1.0)
            embeddings = svd_model.transform(doc_term).astype(np.float32)
            if normalize:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = np.where(norms > 1e-9, embeddings / norms, embeddings)
            return embeddings

        embeddings = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

        for i, text in enumerate(texts):
            indices = self.text_to_indices(text)
            if not indices:
                # Texto vazio ou sem tokens reconhecidos: fallback para UNK
                vec = self.embedding_matrix[self.UNK_IDX].copy()
            else:
                if self.use_idf_weighting and self.idf_weights:
                    weights = np.array(
                        [
                            self.idf_weights.get(self.inverse_vocab.get(idx, ""), 1.0)
                            for idx in indices
                        ],
                        dtype=np.float32,
                    )
                    sum_w = np.sum(weights)
                    if sum_w > 1e-9:
                        vec = np.sum(
                            self.embedding_matrix[indices] * weights[:, None], axis=0
                        ) / sum_w
                    else:
                        vec = np.mean(self.embedding_matrix[indices], axis=0)
                else:
                    vec = np.mean(self.embedding_matrix[indices], axis=0)

            if normalize:
                norm = np.linalg.norm(vec)
                if norm > 1e-9:
                    vec = vec / norm
            embeddings[i] = vec

        return embeddings

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        """Ajusta o vocabulário e extrai os embeddings em um único passo."""
        return self.fit(texts).transform(texts)

    def set_embedding_weights(self, weights: np.ndarray | torch.Tensor) -> None:
        """Atualiza a tabela de embeddings com os pesos aprendidos pela rede neural PyTorch."""
        if isinstance(weights, torch.Tensor):
            w_np = weights.detach().cpu().numpy()
        else:
            w_np = np.asarray(weights)

        if w_np.shape != self.embedding_matrix.shape:
            raise ValueError(
                f"Dimensões incompatíveis de pesos de embedding: esperado {self.embedding_matrix.shape}, recebido {w_np.shape}"
            )
        self.embedding_matrix = w_np.astype(np.float32)
        self.embedding_matrix[self.PAD_IDX] = 0.0

    def get_feature_names_out(self) -> list[str]:
        """Retorna os nomes dos tokens ordenados por índice."""
        return [self.inverse_vocab.get(i, f"token_{i}") for i in range(len(self.vocab))]

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        """Retorna parâmetros para compatibilidade com a interface scikit-learn."""
        return {
            "embedding_dim": self.embedding_dim,
            "max_features": self.max_features,
            "random_state": self.random_state,
            "init_strategy": self.init_strategy,
            "use_idf_weighting": self.use_idf_weighting,
        }
