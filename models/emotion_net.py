"""Rede neural feedforward em NumPy puro para classificação de emoções em português.

Implementada do zero com álgebra linear e cálculo diferencial direto (sem dependência
de PyTorch/TensorFlow para inferência), com extração de features híbridas TF-IDF
(palavra + caractere), seleção estatística via Chi-quadrado (chi2) e calibração de
limiares para predição multirrótulo e extração da emoção predominante.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import chi2
from sklearn.metrics import precision_recall_curve, roc_auc_score

logger = logging.getLogger(__name__)

EKMAN_LABELS = ["medo", "tristeza", "raiva", "nojo", "surpresa", "alegria", "neutro"]
CLINICAL_PRIORITY = ["medo", "tristeza", "raiva", "nojo", "surpresa", "alegria", "neutro"]


class EmotionNeuralNetwork:
    """Perceptron Multicamadas (MLP) puro em NumPy com entropia cruzada binária ponderada."""

    def __init__(
        self,
        dimension: list[int] | None = None,
        activation: str = "relu",
        random_state: int = 42,
    ) -> None:
        self.dimension = dimension
        self.activation_name = activation.lower()
        self.random_state = random_state
        self.historico: dict[str, np.ndarray] = {}
        self.loss_curve_: list[float] = []
        self.pos_weight: np.ndarray | None = None
        self.parametros: dict[str, np.ndarray] = {}

        self._funcoes_ativacao = {
            "sigmoid": self._sigmoide,
            "relu": self._relu,
            "gelu": self._gelu,
        }
        self._funcoes_derivadas = {
            "sigmoid": self._derivada_sigmoide,
            "relu": self._derivada_relu,
            "gelu": self._derivada_gelu,
        }

        if self.activation_name not in self._funcoes_ativacao:
            raise ValueError(
                f"Ativação '{activation}' não suportada. Escolha entre: 'sigmoid', 'relu', 'gelu'"
            )

        if dimension is not None:
            self.configurar_rede(dimension)

    def configurar_rede(self, dimension: list[int]) -> None:
        self.dimension = dimension
        self.parametros = {}
        rng = np.random.RandomState(self.random_state)
        for l_idx in range(1, len(dimension)):
            n_in, n_out = dimension[l_idx - 1], dimension[l_idx]
            if self.activation_name == "sigmoid":
                fator = np.sqrt(2.0 / (n_in + n_out))
            else:
                fator = np.sqrt(2.0 / n_in)
            self.parametros[f"W{l_idx}"] = rng.randn(n_out, n_in) * fator
            self.parametros[f"b{l_idx}"] = np.zeros((n_out, 1))

    def definir_pesos(self, Y: np.ndarray, maximo: float = 30.0) -> None:
        """Calcula pesos por classe: sqrt(negativos / positivos)."""
        pos = Y.sum(axis=0)
        neg = Y.shape[0] - pos
        w = np.sqrt(neg / np.maximum(pos, 1))
        self.pos_weight = np.clip(w, 1.0, maximo).reshape(-1, 1)

    @staticmethod
    def _sigmoide(z: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    @staticmethod
    def _derivada_sigmoide(_z: np.ndarray, a: np.ndarray) -> np.ndarray:
        return a * (1.0 - a)

    @staticmethod
    def _relu(z: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, z)

    @staticmethod
    def _derivada_relu(z: np.ndarray, _a: np.ndarray) -> np.ndarray:
        return (z > 0.0).astype(float)

    @staticmethod
    def _gelu(z: np.ndarray) -> np.ndarray:
        return 0.5 * z * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (z + 0.044715 * np.power(z, 3))))

    @staticmethod
    def _derivada_gelu(z: np.ndarray, _a: np.ndarray) -> np.ndarray:
        s = np.sqrt(2.0 / np.pi) * (z + 0.044715 * np.power(z, 3))
        tanh_s = np.tanh(s)
        ds_dz = np.sqrt(2.0 / np.pi) * (1.0 + 3.0 * 0.044715 * np.power(z, 2))
        return 0.5 * (1.0 + tanh_s) + 0.5 * z * (1.0 - np.power(tanh_s, 2)) * ds_dz

    def forward(self, X: np.ndarray) -> np.ndarray:
        """X: matriz densa de formato (n_features, batch_size)."""
        ativacao = self._funcoes_ativacao[self.activation_name]
        self.historico = {"A0": X}
        L = len(self.dimension)
        A = X
        for l_idx in range(1, L):
            W = self.parametros[f"W{l_idx}"]
            b = self.parametros[f"b{l_idx}"]
            Z = np.dot(W, A) + b
            A = self._sigmoide(Z) if l_idx == L - 1 else ativacao(Z)
            self.historico[f"Z{l_idx}"] = Z
            self.historico[f"A{l_idx}"] = A
        return A

    def backward(self, Y: np.ndarray, taxa_aprendizado: float) -> None:
        L = len(self.dimension)
        m = Y.shape[1]
        derivada = self._funcoes_derivadas[self.activation_name]

        A_final = self.historico[f"A{L - 1}"]
        if self.pos_weight is None:
            dZ = A_final - Y
        else:
            w = self.pos_weight
            dZ = A_final * (1.0 + (w - 1.0) * Y) - w * Y

        for l_idx in range(L - 1, 0, -1):
            A_anterior = self.historico[f"A{l_idx - 1}"]
            dW = np.dot(dZ, A_anterior.T) / m
            db = np.sum(dZ, axis=1, keepdims=True) / m

            if l_idx > 1:
                W_atual = self.parametros[f"W{l_idx}"]
                Z_anterior = self.historico[f"Z{l_idx - 1}"]
                dZ = np.dot(W_atual.T, dZ) * derivada(Z_anterior, A_anterior)

            self.parametros[f"W{l_idx}"] -= taxa_aprendizado * dW
            self.parametros[f"b{l_idx}"] -= taxa_aprendizado * db

    def _loss(self, A: np.ndarray, Y: np.ndarray) -> float:
        A = np.clip(A, 1e-12, 1.0 - 1e-12)
        w = 1.0 if self.pos_weight is None else self.pos_weight
        loss = -np.mean(w * Y * np.log(A) + (1.0 - Y) * np.log(1.0 - A))
        return float(loss)

    @staticmethod
    def _lote_denso(Xb: Any) -> np.ndarray:
        if hasattr(Xb, "toarray"):
            Xb = Xb.toarray()
        return np.asarray(Xb).T

    def fit_batches(
        self,
        X: Any,
        y: np.ndarray,
        epocas: int = 15,
        taxa_aprendizado: float = 0.5,
        batch_size: int = 64,
        verbose: bool = False,
    ) -> EmotionNeuralNetwork:
        y = np.asarray(y)
        if y.ndim == 1:
            y = y.reshape(-1, 1)
        m = X.shape[0]
        self.loss_curve_ = []
        rng = np.random.RandomState(self.random_state)
        for epoca in range(epocas):
            idx = rng.permutation(m)
            perdas = []
            for i in range(0, m, batch_size):
                lote = idx[i : i + batch_size]
                Xb = self._lote_denso(X[lote])
                Yb = y[lote].T
                A = self.forward(Xb)
                perdas.append(self._loss(A, Yb))
                self.backward(Yb, taxa_aprendizado)
            epoch_loss = float(np.mean(perdas))
            self.loss_curve_.append(epoch_loss)
            if verbose:
                logger.info("Época %3d | loss = %.4f", epoca + 1, epoch_loss)
        return self

    def predict_proba_batches(self, X: Any, batch_size: int = 2048) -> np.ndarray:
        probs = []
        for i in range(0, X.shape[0], batch_size):
            Xb = self._lote_denso(X[i : i + batch_size])
            probs.append(self.forward(Xb).T)
        P = np.vstack(probs)
        return P.ravel() if P.shape[1] == 1 else P


class EmotionPipeline:
    """Pipeline completo de classificação emocional: TF-IDF + chi2 + EmotionNeuralNetwork."""

    def __init__(
        self,
        n_features: int = 5000,
        hidden_units: list[int] | None = None,
        activation: str = "relu",
        labels: list[str] | None = None,
        random_state: int = 42,
    ) -> None:
        self.n_features = n_features
        self.hidden_units = hidden_units or [64]
        self.activation = activation
        self.labels = labels or EKMAN_LABELS
        self.random_state = random_state

        self.vec_word = TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, max_features=50000, sublinear_tf=True
        )
        self.vec_char = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=3, max_features=50000, sublinear_tf=True
        )
        self.selected_indices_: np.ndarray | None = None
        self.net_: EmotionNeuralNetwork | None = None
        self.thresholds_: np.ndarray = np.full(len(self.labels), 0.5)

    def _extract_and_select(
        self, texts_train: list[str], Y_train: np.ndarray
    ) -> Any:
        logger.info("Extraindo features TF-IDF (palavras + caracteres)...")
        Xw = self.vec_word.fit_transform(texts_train)
        Xc = self.vec_char.fit_transform(texts_train)
        X_combined = hstack([Xw, Xc]).tocsr()
        logger.info("Vocabulário combinado: %d features.", X_combined.shape[1])

        # Seleção estatística Chi-quadrado
        logger.info("Calculando Chi-quadrado para as top %d features...", self.n_features)
        chi_scores = np.max(
            [
                np.nan_to_num(chi2(X_combined, Y_train[:, j])[0])
                for j in range(Y_train.shape[1])
            ],
            axis=0,
        )
        self.selected_indices_ = np.argsort(-chi_scores)[: self.n_features]
        return X_combined[:, self.selected_indices_]

    def _transform(self, texts: list[str]) -> Any:
        Xw = self.vec_word.transform(texts)
        Xc = self.vec_char.transform(texts)
        X_combined = hstack([Xw, Xc]).tocsr()
        assert self.selected_indices_ is not None
        return X_combined[:, self.selected_indices_]

    def _optimize_thresholds(self, Y_val: np.ndarray, P_val: np.ndarray) -> np.ndarray:
        lim = []
        for j in range(Y_val.shape[1]):
            p, r, t = precision_recall_curve(Y_val[:, j], P_val[:, j])
            f1 = 2.0 * p * r / np.maximum(p + r, 1e-12)
            best_idx = np.argmax(f1[:-1]) if len(t) > 0 else 0
            best_thresh = float(t[best_idx]) if len(t) > 0 else 0.5
            lim.append(best_thresh)
        return np.array(lim)

    def fit(
        self,
        texts_train: list[str],
        Y_train: np.ndarray,
        texts_val: list[str],
        Y_val: np.ndarray,
        epochs: int = 15,
        lr: float = 0.5,
        batch_size: int = 64,
    ) -> EmotionPipeline:
        X_train = self._extract_and_select(texts_train, Y_train)
        X_val = self._transform(texts_val)

        in_dim = X_train.shape[1]
        dimension = [in_dim] + self.hidden_units + [len(self.labels)]
        self.net_ = EmotionNeuralNetwork(
            dimension=dimension,
            activation=self.activation,
            random_state=self.random_state,
        )
        self.net_.definir_pesos(Y_train)

        logger.info("Iniciando treino da rede neural: %s | %d épocas | lr=%.2f", dimension, epochs, lr)
        best_auc = -1.0
        best_params = None
        best_epoch = 0

        for ep in range(1, epochs + 1):
            self.net_.fit_batches(
                X_train, Y_train, epocas=1, taxa_aprendizado=lr, batch_size=batch_size, verbose=False
            )
            Pv = self.net_.predict_proba_batches(X_val)
            auc_val = float(roc_auc_score(Y_val, Pv, average="macro"))
            loss_train = self.net_.loss_curve_[-1]
            loss_val = self.net_._loss(Pv.T, Y_val.T)
            logger.info(
                "Época %2d/%2d - Loss Treino: %.4f - Loss Val: %.4f - ROC-AUC Val: %.4f",
                ep, epochs, loss_train, loss_val, auc_val,
            )
            if auc_val > best_auc:
                best_auc = auc_val
                best_params = copy.deepcopy(self.net_.parametros)
                best_epoch = ep

        logger.info("Melhor época: %d com ROC-AUC Val: %.4f", best_epoch, best_auc)
        assert best_params is not None
        self.net_.parametros = best_params

        # Otimização de limiares por classe
        P_val = self.net_.predict_proba_batches(X_val)
        self.thresholds_ = self._optimize_thresholds(Y_val, P_val)
        for label, th in zip(self.labels, self.thresholds_):
            logger.info("Limiar otimizado [%-8s]: %.3f", label, th)

        return self

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        assert self.net_ is not None
        X = self._transform(texts)
        return self.net_.predict_proba_batches(X)

    def predict_multilabel(self, texts: list[str]) -> list[list[str]]:
        probs = self.predict_proba(texts)
        active_per_sample: list[list[str]] = []
        for p in probs:
            active = [self.labels[j] for j in range(len(self.labels)) if p[j] >= self.thresholds_[j]]
            active_per_sample.append(active)
        return active_per_sample

    def predict_primary_emotion(self, text: str) -> dict[str, Any]:
        """Extrai a emoção principal mais condizente para um relato de diário.

        Utiliza a regra de probabilidade relativa ao limiar (P / limiar).
        Em caso de empate, prioriza emoções clínicas de maior relevância.
        """
        assert self.net_ is not None
        P = self.predict_proba([text])[0]
        rel_scores = P / np.maximum(self.thresholds_, 1e-6)

        # Ranking ordenado por score relativo decrescente
        ranking_indices = np.argsort(-rel_scores)
        top_idx = int(ranking_indices[0])
        primary = self.labels[top_idx]

        # Desempate clínico se o maior score relativo estiver muito próximo de outro
        # Ex: se tristeza e alegria estiverem quase empatados, prioriza tristeza
        for clinical_candidate in CLINICAL_PRIORITY:
            cand_idx = self.labels.index(clinical_candidate)
            if rel_scores[cand_idx] >= 1.0 and (rel_scores[top_idx] - rel_scores[cand_idx]) < 0.15:
                primary = clinical_candidate
                top_idx = cand_idx
                break

        prob_dict = {label: float(round(P[j], 4)) for j, label in enumerate(self.labels)}
        thresh_dict = {label: float(round(self.thresholds_[j], 4)) for j, label in enumerate(self.labels)}
        active_emotions = [self.labels[j] for j, val in enumerate(P) if val >= self.thresholds_[j]]

        return {
            "primary_emotion": primary,
            "confidence": float(round(P[top_idx], 4)),
            "relative_score": float(round(rel_scores[top_idx], 4)),
            "detected_emotions": active_emotions,
            "probabilities": prob_dict,
            "thresholds": thresh_dict,
            "is_risk_emotion": primary in {"medo", "tristeza", "raiva"},
        }

    def save(self, filepath: Path | str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("Pipeline emocional salvo em %s", path)

    @classmethod
    def load(cls, filepath: Path | str) -> EmotionPipeline:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Modelo não encontrado em {path}")
        pipeline = joblib.load(path)
        if not isinstance(pipeline, cls):
            raise TypeError(f"Objeto carregado não é {cls.__name__}")
        return pipeline
