"""Implementação da Rede Neural Perceptron Multicamadas (MLP) em PyTorch para

classificação dos 8 macrotemas clínicos + classe de salvaguarda.
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
        input_dim: int = 1024,
        hidden_dim1: int = 128,
        hidden_dim2: int = 64,
        num_classes: int = 9,
        dropout_rate: float = 0.3,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

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

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Calcula distribuição de probabilidades calibrada via Softmax."""
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
        """Prediz classe com salvaguarda matemática.

        Se a probabilidade máxima for inferior ao limiar de corte (`threshold`),
        retorna a classe de fallback `outros_indeterminado` (índice 8).
        """
        probs = self.predict_proba(x)
        max_probs, preds = torch.max(probs, dim=-1)

        fallback_idx = self.num_classes - 1  # 8: outros_indeterminado
        preds = torch.where(
            max_probs < threshold, torch.tensor(fallback_idx, device=x.device), preds
        )
        return preds, max_probs
