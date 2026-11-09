"""Implementação da Rede Neural Perceptron Multicamadas (MLP) em PyTorch para

classificação dos 8 macrotemas clínicos + classe indeterminada.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

THEME_CLASSES: list[str] = [
    "familia",
    "trabalho",
    "relacionamentos",
    "estudos",
    "saude_sono",
    "financas",
    "luto",
    "autoestima",
    "outros_indeterminado",
]


class ClinicalThemeMLP(nn.Module):
    """Multi-Layer Perceptron (MLP) para classificação temática de diários em saúde mental.

    Arquitetura:
      Entrada (1024) -> Linear(1024, 128) -> BatchNorm1d -> ReLU -> Dropout(0.3)
                     -> Linear(128, 64)   -> ReLU        -> Dropout(0.2)
                     -> Linear(64, 9)     -> Logits (Softmax para inferência)
    """

    def __init__(
        self,
        input_dim: int = 128,
        hidden_dim1: int = 128,
        hidden_dim2: int = 64,
        num_classes: int = 9,
        dropout_rate: float = 0.3,
        vocab_size: int | None = None,
        embedding_dim: int | None = None,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.vocab_size = vocab_size

        if vocab_size is not None and vocab_size > 0:
            actual_dim = embedding_dim or input_dim
            self.embedding_bag = nn.EmbeddingBag(
                num_embeddings=vocab_size,
                embedding_dim=actual_dim,
                mode="mean",
                padding_idx=0,
            )
            self.fc1 = nn.Linear(actual_dim, hidden_dim1)
        else:
            self.embedding_bag = None
            self.fc1 = nn.Linear(input_dim, hidden_dim1)

        self.bn1 = nn.BatchNorm1d(hidden_dim1)
        self.dropout1 = nn.Dropout(dropout_rate)

        self.fc2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.dropout2 = nn.Dropout(dropout_rate * 0.7)

        self.fc3 = nn.Linear(hidden_dim2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Passagem direta computando os logits não normalizados."""
        # Se receber tensor 1D, adiciona dimensão de lote
        if x.dim() == 1:
            x = x.unsqueeze(0)

        # Se receber tensor de índices inteiros (tokens) e possuir camada de embedding
        if x.dtype in (torch.int32, torch.int64):
            if self.embedding_bag is not None:
                x = self.embedding_bag(x)
            else:
                raise ValueError(
                    "Tensor de índices recebido mas o modelo não possui embedding_bag configurado."
                )

        # Camada 1
        x = self.fc1(x)
        # BatchNorm1d requer mais de 1 amostra se em modo train;
        # se em modo eval ou se lote for unitário, trata graciosamente
        if x.size(0) > 1 or not self.training:
            x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout1(x)

        # Camada 2
        x = self.fc2(x)
        x = F.relu(x)
        x = self.dropout2(x)

        # Camada de Saída (Logits brutos para CrossEntropyLoss)
        logits = self.fc3(x)
        return logits

    def get_embedding(self, x: torch.Tensor) -> torch.Tensor:
        """Extrai a representação densa (embedding) do relato na hiperesfera unitária."""
        if x.dim() == 1:
            x = x.unsqueeze(0)
        if x.dtype in (torch.int32, torch.int64) and self.embedding_bag is not None:
            emb = self.embedding_bag(x)
            return F.normalize(emb, p=2, dim=-1)
        elif x.dtype in (torch.float32, torch.float64):
            return F.normalize(x, p=2, dim=-1)
        return x

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Retorna scores softmax normalizados, sem garantia de calibração."""
        was_training = self.training
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = F.softmax(logits, dim=-1)
        if was_training:
            self.train()
        return probs

    def predict(
        self, x: torch.Tensor, threshold: float = 0.50
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Prediz classe com regra operacional de abstenção.

        Se a probabilidade máxima for inferior ao limiar de corte (`threshold`),
        retorna a classe de fallback `outros_indeterminado` (índice 8).
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold deve estar entre 0 e 1")
        probs = self.predict_proba(x)
        max_probs, preds = torch.max(probs, dim=-1)

        fallback_idx = self.num_classes - 1  # 8: outros_indeterminado
        preds = torch.where(
            max_probs < threshold, torch.tensor(fallback_idx, device=x.device), preds
        )
        return preds, max_probs

    def predict_distribution(self, x: torch.Tensor) -> list[dict[str, float]]:
        """Retorna distribuição de probabilidades para cada classe em formato de dicionário."""
        probs = self.predict_proba(x)
        if probs.dim() == 1:
            probs = probs.unsqueeze(0)
        probs_np = probs.cpu().numpy()
        return [
            {THEME_CLASSES[i]: float(probs_np[row, i]) for i in range(len(THEME_CLASSES))}
            for row in range(probs_np.shape[0])
        ]

    def predict_percentages(self, x: torch.Tensor, round_digits: int = 2) -> list[dict[str, float]]:
        """Retorna scores softmax vezes 100; não representa composição textual."""
        distributions = self.predict_distribution(x)
        return [
            {theme: round(prob * 100.0, round_digits) for theme, prob in dist.items()}
            for dist in distributions
        ]
