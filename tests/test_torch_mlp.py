"""Testes unitários para o modelo PyTorch ClinicalThemeMLP."""

import torch
from torch import nn

from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP


def test_torch_mlp_forward_and_prediction():
    """Valida forward pass e probabilidades Softmax conforme especificado em docs/rede-neural.md."""
    model = ClinicalThemeMLP(input_dim=1024, num_classes=9)
    dummy_input = torch.randn(4, 1024)

    # 1. Formato de saída dos logits
    logits = model(dummy_input)
    assert logits.shape == (4, 9)

    # 2. Formato e calibração das probabilidades Softmax
    probs = model.predict_proba(dummy_input)
    assert probs.shape == (4, 9)
    # A soma das probabilidades de cada linha deve ser 1.0 (margem de tolerância numérica)
    assert torch.allclose(probs.sum(dim=-1), torch.ones(4), atol=1e-5)


def test_torch_mlp_single_sample_inference():
    """Valida inferência em tensor 1D ou batch de tamanho 1."""
    model = ClinicalThemeMLP(input_dim=1024, num_classes=9)
    model.eval()

    # Tensor 1D
    single_1d = torch.randn(1024)
    probs_1d = model.predict_proba(single_1d)
    assert probs_1d.shape == (1, 9)
    assert torch.isclose(probs_1d.sum(), torch.tensor(1.0), atol=1e-5)

    # Tensor 2D com batch=1
    single_2d = torch.randn(1, 1024)
    probs_2d = model.predict_proba(single_2d)
    assert probs_2d.shape == (1, 9)


def test_torch_mlp_safeguard_fallback():
    """Valida salvaguarda quando probabilidade máxima for inferior a 0.50."""
    model = ClinicalThemeMLP(input_dim=10, num_classes=9)

    # Cria probabilidades deliberadamente planas (uniformes = 1/9 ≈ 0.111 < 0.50)
    flat_input = torch.zeros(2, 10)
    # Força os pesos da última camada a zero para saída uniforme
    with torch.no_grad():
        model.fc3.weight.fill_(0.0)
        model.fc3.bias.fill_(0.0)

    preds, confs = model.predict(flat_input, threshold=0.50)

    # Como a confiança máxima é < 0.50, deve recair na classe outros_indeterminado (índice 8)
    assert torch.all(preds == 8)
    assert torch.all(confs < 0.50)


def test_torch_mlp_training_step():
    """Valida que uma passada de backward e otimizador atualiza os pesos da rede."""
    model = ClinicalThemeMLP(input_dim=32, hidden_dim1=16, hidden_dim2=8, num_classes=9)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    criterion = nn.CrossEntropyLoss()

    x = torch.randn(8, 32)
    y = torch.randint(0, 9, (8,))

    # Salva cópia inicial dos pesos
    initial_w1 = model.fc1.weight.clone()

    model.train()
    optimizer.zero_grad()
    out = model(x)
    loss = criterion(out, y)
    loss.backward()
    optimizer.step()

    # Pesos devem ter mudado
    assert not torch.equal(initial_w1, model.fc1.weight)
    assert loss.item() > 0.0


def test_theme_classes_list():
    """Garante que THEME_CLASSES possui exatamente os 8 macrotemas + outros_indeterminado."""
    assert len(THEME_CLASSES) == 9
    assert THEME_CLASSES[-1] == "outros_indeterminado"
    expected = [
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
    assert THEME_CLASSES == expected
