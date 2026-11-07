"""Implementação didática de Rede Neural Perceptron Multicamadas (MLP) em NumPy puro.

Desenvolvida sem bibliotecas de autograd para demonstrar os fundamentos matemáticos
do cálculo diferencial (Forward, Backward, Cross-Entropy Loss e Gradiente Descendente).
"""

from __future__ import annotations

import numpy as np


class NumpyClinicalMLP:
    """Perceptron Multicamadas (MLP) didático implementado do zero em NumPy.

    Arquitetura:
      Entrada (in_dim) -> Linear(in_dim, h1) -> ReLU -> Linear(h1, out_dim) -> Softmax
    """

    def __init__(
        self,
        in_dim: int = 1024,
        h1: int = 64,
        out_dim: int = 9,
        lr: float = 0.01,
        random_state: int = 42,
    ) -> None:
        self.in_dim = in_dim
        self.h1 = h1
        self.out_dim = out_dim
        self.lr = lr

        rng = np.random.RandomState(random_state)
        # Inicialização He (Kaiming) para a camada com ativação ReLU
        self.W1 = rng.randn(in_dim, h1) * np.sqrt(2.0 / in_dim)
        self.b1 = np.zeros((1, h1))

        # Inicialização Xavier / He para a camada de saída
        self.W2 = rng.randn(h1, out_dim) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros((1, out_dim))

        # Caches intermediários para retropropagação
        self.z1: np.ndarray | None = None
        self.a1: np.ndarray | None = None
        self.z2: np.ndarray | None = None
        self.probs: np.ndarray | None = None

    @staticmethod
    def relu(z: np.ndarray) -> np.ndarray:
        """Função de ativação Rectified Linear Unit."""
        return np.maximum(0, z)

    @staticmethod
    def relu_derivative(z: np.ndarray) -> np.ndarray:
        """Derivada da ReLU: 1 se z > 0, 0 caso contrário."""
        return (z > 0).astype(float)

    @staticmethod
    def softmax(z: np.ndarray) -> np.ndarray:
        """Softmax numericamente estável subtraindo o valor máximo."""
        exp_z = np.exp(z - np.max(z, axis=1, keepdims=True))
        return exp_z / np.sum(exp_z, axis=1, keepdims=True)

    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagação direta (Forward pass)."""
        if X.ndim == 1:
            X = X.reshape(1, -1)

        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.probs = self.softmax(self.z2)
        return self.probs

    def compute_loss(self, probs: np.ndarray, y_onehot: np.ndarray) -> float:
        """Calcula a perda de Entropia Cruzada Categórica."""
        eps = 1e-15
        clipped_probs = np.clip(probs, eps, 1 - eps)
        loss = -np.sum(y_onehot * np.log(clipped_probs)) / probs.shape[0]
        return float(loss)

    def backward(
        self, X: np.ndarray, y_onehot: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Retropropagação do gradiente (Backward pass) e atualização via SGD."""
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if y_onehot.ndim == 1:
            y_onehot = y_onehot.reshape(1, -1)

        n_samples = X.shape[0]

        # Gradiente da saída combinando Softmax e Cross-Entropy Loss: dL/dz2 = (probs - y) / N
        assert self.probs is not None
        assert self.a1 is not None
        assert self.z1 is not None

        dz2 = (self.probs - y_onehot) / n_samples
        dW2 = np.dot(self.a1.T, dz2)
        db2 = np.sum(dz2, axis=0, keepdims=True)

        # Gradiente propagado para a camada oculta
        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * self.relu_derivative(self.z1)
        dW1 = np.dot(X.T, dz1)
        db1 = np.sum(dz1, axis=0, keepdims=True)

        # Atualização dos pesos e bias (Gradiente Descendente)
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1

        return dW1, db1, dW2, db2

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        verbose: bool = False,
    ) -> list[float]:
        """Treina a rede neural utilizando mini-batch SGD."""
        n_samples = X.shape[0]

        # Se y for vetor de índices inteiros, converte para one-hot
        if y.ndim == 1 or (y.ndim == 2 and y.shape[1] == 1):
            y_indices = y.ravel().astype(int)
            y_onehot = np.zeros((n_samples, self.out_dim))
            y_onehot[np.arange(n_samples), y_indices] = 1.0
        else:
            y_onehot = y

        loss_history: list[float] = []

        for epoch in range(1, epochs + 1):
            # Embaralha os dados em cada época
            indices = np.random.permutation(n_samples)
            X_shuffled = X[indices]
            y_shuffled = y_onehot[indices]

            epoch_loss = 0.0

            for start_idx in range(0, n_samples, batch_size):
                end_idx = min(start_idx + batch_size, n_samples)
                X_batch = X_shuffled[start_idx:end_idx]
                y_batch = y_shuffled[start_idx:end_idx]

                probs = self.forward(X_batch)
                batch_loss = self.compute_loss(probs, y_batch)
                self.backward(X_batch, y_batch)

                epoch_loss += batch_loss * (end_idx - start_idx)

            epoch_loss /= n_samples
            loss_history.append(epoch_loss)

            if verbose and (epoch % 10 == 0 or epoch == 1):
                print(f"NumPy MLP Época {epoch:03d}/{epochs:03d} - Loss: {epoch_loss:.4f}")

        return loss_history

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Retorna as probabilidades Softmax para cada amostra."""
        return self.forward(X)

    def predict(self, X: np.ndarray, threshold: float = 0.50) -> tuple[np.ndarray, np.ndarray]:
        """Retorna classes preditas e suas respectivas confianças com salvaguarda."""
        probs = self.predict_proba(X)
        preds = np.argmax(probs, axis=1)
        confidences = np.max(probs, axis=1)

        # Salvaguarda: se confiança < threshold, classifica como outros_indeterminado (última classe)
        fallback_idx = self.out_dim - 1
        preds[confidences < threshold] = fallback_idx
        return preds, confidences

    def predict_distribution(self, X: np.ndarray) -> list[dict[str, float]]:
        """Retorna distribuição de probabilidades para cada classe em formato de dicionário."""
        probs = self.predict_proba(X)
        if probs.ndim == 1:
            probs = probs.reshape(1, -1)
        from models.torch_mlp import THEME_CLASSES

        classes = THEME_CLASSES[: self.out_dim]
        return [
            {classes[i]: float(probs[row, i]) for i in range(len(classes))}
            for row in range(probs.shape[0])
        ]

    def predict_percentages(
        self, X: np.ndarray, round_digits: int = 2
    ) -> list[dict[str, float]]:
        """Retorna separação temática em percentuais (0.0% a 100.0%) por amostra."""
        distributions = self.predict_distribution(X)
        return [
            {theme: round(prob * 100.0, round_digits) for theme, prob in dist.items()}
            for dist in distributions
        ]
