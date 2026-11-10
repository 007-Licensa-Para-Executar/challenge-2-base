"""Implementação da Rede Neural Perceptron Multicamadas (MLP) em PyTorch para

classificação dos 8 macrotemas clínicos + classe indeterminada.
"""

from __future__ import annotations

from typing import Literal

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


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization (RMSNorm)."""

    def __init__(self, dim: int, eps: float = 1e-8) -> None:
        super().__init__()
        self.eps = eps
        self.scale = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        variance = x.pow(2).mean(dim=-1, keepdim=True)
        return self.scale * (x * torch.rsqrt(variance + self.eps))


class ClinicalThemeMLP(nn.Module):
    """Multi-Layer Perceptron (MLP) para classificação temática de diários em saúde mental.

    Arquitetura:
      Entrada (1024) -> Linear(1024, 128) -> Norm(BatchNorm | LayerNorm | RMSNorm) -> ReLU -> Dropout(0.3)
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
        norm_type: Literal["batch_norm", "layer_norm", "rms_norm", "none"] = "batch_norm",
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.vocab_size = vocab_size
        self.norm_type = norm_type

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

        if norm_type == "batch_norm":
            self.bn1: nn.Module = nn.BatchNorm1d(hidden_dim1)
        elif norm_type == "layer_norm":
            self.bn1 = nn.LayerNorm(hidden_dim1)
        elif norm_type == "rms_norm":
            self.bn1 = RMSNorm(hidden_dim1)
        else:
            self.bn1 = nn.Identity()
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
        if self.norm_type == "batch_norm":
            # BatchNorm1d requer mais de 1 amostra se em modo train;
            # se em modo eval ou se lote for unitário, trata graciosamente
            if x.size(0) > 1 or not self.training:
                x = self.bn1(x)
        else:
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


class ClinicalSequentialClassifier(nn.Module):
    """Classificador neural para dados sequenciais (RNN, LSTM e GRU) com camada de Embedding."""

    def __init__(
        self,
        vocab_size: int = 5000,
        embed_dim: int = 128,
        hidden_dim: int = 128,
        num_classes: int = 9,
        num_layers: int = 1,
        bidirectional: bool = True,
        recurrent_type: Literal["lstm", "gru", "rnn"] = "lstm",
        norm_type: Literal["layer_norm", "rms_norm", "none"] = "layer_norm",
        dropout_rate: float = 0.3,
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.recurrent_type = recurrent_type
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1

        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.emb_dropout = nn.Dropout(dropout_rate)

        rnn_dropout = dropout_rate if num_layers > 1 else 0.0
        if recurrent_type == "lstm":
            self.rnn: nn.Module = nn.LSTM(
                input_size=embed_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                bidirectional=bidirectional,
                dropout=rnn_dropout,
            )
        elif recurrent_type == "gru":
            self.rnn = nn.GRU(
                input_size=embed_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                bidirectional=bidirectional,
                dropout=rnn_dropout,
            )
        elif recurrent_type == "rnn":
            self.rnn = nn.RNN(
                input_size=embed_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                nonlinearity="relu",
                batch_first=True,
                bidirectional=bidirectional,
                dropout=rnn_dropout,
            )
        else:
            raise ValueError(f"Tipo recorrente não suportado: {recurrent_type}")

        recurrent_out_dim = hidden_dim * self.num_directions
        if norm_type == "layer_norm":
            self.norm: nn.Module = nn.LayerNorm(recurrent_out_dim)
        elif norm_type == "rms_norm":
            self.norm = RMSNorm(recurrent_out_dim)
        else:
            self.norm = nn.Identity()

        self.fc1 = nn.Linear(recurrent_out_dim, 64)
        self.dropout = nn.Dropout(dropout_rate)
        self.fc_out = nn.Linear(64, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)
        embedded = self.emb_dropout(self.embedding(x))
        if self.recurrent_type == "lstm":
            _out, (h_n, _c_n) = self.rnn(embedded)
        else:
            _out, h_n = self.rnn(embedded)
        if self.bidirectional:
            feat = torch.cat([h_n[-2, :, :], h_n[-1, :, :]], dim=-1)
        else:
            feat = h_n[-1, :, :]
        feat = self.norm(feat)
        hidden = self.dropout(F.relu(self.fc1(feat)))
        return self.fc_out(hidden)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        was_training = self.training
        self.eval()
        with torch.no_grad():
            probs = F.softmax(self.forward(x), dim=-1)
        if was_training:
            self.train()
        return probs

    def predict(
        self, x: torch.Tensor, threshold: float = 0.50
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold deve estar entre 0 e 1")
        probs = self.predict_proba(x)
        max_probs, preds = torch.max(probs, dim=-1)
        fallback_idx = self.num_classes - 1
        preds = torch.where(
            max_probs < threshold, torch.tensor(fallback_idx, device=x.device), preds
        )
        return preds, max_probs

    def predict_percentages(
        self, x: torch.Tensor, round_digits: int = 2
    ) -> list[dict[str, float]]:
        probs = self.predict_proba(x).cpu().numpy()
        return [
            {
                THEME_CLASSES[i]: round(float(probs[row, i]) * 100.0, round_digits)
                for i in range(len(THEME_CLASSES))
            }
            for row in range(probs.shape[0])
        ]
