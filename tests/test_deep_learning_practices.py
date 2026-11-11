"""Testes de boas práticas de deep learning (sanity checks canônicos de redes neurais)."""

import math

import pytest
import torch
from torch import nn

from models.torch_mlp import THEME_CLASSES, ClinicalSequentialClassifier, ClinicalThemeMLP

NUM_CLASSES = len(THEME_CLASSES)


def _fit(model: nn.Module, x: torch.Tensor, y: torch.Tensor, steps: int = 250) -> float:
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    criterion = nn.CrossEntropyLoss()
    model.train()
    for _ in range(steps):
        optimizer.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
    model.eval()
    with torch.no_grad():
        return criterion(model(x), y).item()


def test_initial_loss_matches_uniform_guess():
    """Sem treino a loss deve ficar perto de ln(C): valores distantes indicam erro de init/loss."""
    torch.manual_seed(0)
    model = ClinicalThemeMLP(input_dim=64).eval()
    x = torch.randn(128, 64) * 0.1
    y = torch.randint(0, NUM_CLASSES, (128,))
    with torch.no_grad():
        loss = nn.CrossEntropyLoss()(model(x), y).item()
    assert abs(loss - math.log(NUM_CLASSES)) < 0.5


@pytest.mark.parametrize("norm_type", ["batch_norm", "layer_norm", "rms_norm"])
def test_mlp_can_overfit_tiny_batch(norm_type):
    torch.manual_seed(0)
    x = torch.randn(18, 32)
    y = torch.arange(18) % NUM_CLASSES
    model = ClinicalThemeMLP(input_dim=32, dropout_rate=0.0, norm_type=norm_type)
    assert _fit(model, x, y) < 0.05


@pytest.mark.parametrize("recurrent_type", ["rnn", "gru", "lstm"])
def test_sequential_models_can_overfit_tiny_batch(recurrent_type):
    torch.manual_seed(0)
    tokens = torch.randint(1, 50, (18, 10))
    y = torch.arange(18) % NUM_CLASSES
    model = ClinicalSequentialClassifier(
        vocab_size=50, embed_dim=16, hidden_dim=32, recurrent_type=recurrent_type, dropout_rate=0.0
    )
    assert _fit(model, tokens, y, steps=350) < 0.1


def test_every_parameter_receives_finite_nonzero_gradient():
    torch.manual_seed(0)
    model = ClinicalSequentialClassifier(vocab_size=50, embed_dim=16, hidden_dim=32, dropout_rate=0.0)
    tokens = torch.randint(1, 50, (8, 10))
    nn.CrossEntropyLoss()(model(tokens), torch.randint(0, NUM_CLASSES, (8,))).backward()
    for name, param in model.named_parameters():
        assert param.grad is not None, name
        assert torch.isfinite(param.grad).all(), name
        assert param.grad.abs().sum() > 0, name


def test_gradient_clipping_caps_exploding_gradients():
    torch.manual_seed(0)
    model = ClinicalThemeMLP(input_dim=16, dropout_rate=0.0)
    x = torch.randn(8, 16) * 1e4
    nn.CrossEntropyLoss()(model(x), torch.randint(0, NUM_CLASSES, (8,))).backward()
    before = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    after = torch.sqrt(sum((p.grad**2).sum() for p in model.parameters() if p.grad is not None))
    assert before > 1.0
    assert after <= 1.0 + 1e-4
