"""Testes unitários para o baseline didático em NumPy puro NumpyClinicalMLP."""

import numpy as np

from models.numpy_mlp import NumpyClinicalMLP


def test_numpy_mlp_initialization_and_forward():
    """Valida inicialização e forward pass do MLP em NumPy."""
    mlp = NumpyClinicalMLP(in_dim=1024, h1=64, out_dim=9, lr=0.01)

    assert mlp.W1.shape == (1024, 64)
    assert mlp.b1.shape == (1, 64)
    assert mlp.W2.shape == (64, 9)
    assert mlp.b2.shape == (1, 9)

    X = np.random.randn(5, 1024)
    probs = mlp.forward(X)

    assert probs.shape == (5, 9)
    # Soma de cada linha do Softmax deve ser 1.0
    row_sums = np.sum(probs, axis=1)
    np.testing.assert_allclose(row_sums, np.ones(5), atol=1e-5)


def test_numpy_mlp_activation_functions():
    """Valida implementação das funções de ativação e derivadas."""
    mlp = NumpyClinicalMLP()

    z = np.array([-2.0, -0.5, 0.0, 1.5, 3.0])
    relu_out = mlp.relu(z)
    np.testing.assert_allclose(relu_out, np.array([0.0, 0.0, 0.0, 1.5, 3.0]))

    relu_grad = mlp.relu_derivative(z)
    np.testing.assert_allclose(relu_grad, np.array([0.0, 0.0, 0.0, 1.0, 1.0]))

    # Teste de estabilidade numérica do Softmax com valores altos
    large_z = np.array([[1000.0, 1001.0, 1002.0]])
    softmax_out = mlp.softmax(large_z)
    assert not np.isnan(softmax_out).any()
    np.testing.assert_allclose(np.sum(softmax_out), 1.0, atol=1e-5)


def test_numpy_mlp_backward_and_training():
    """Valida o cálculo do gradiente e a convergência do modelo em dados sintéticos."""
    np.random.seed(42)
    mlp = NumpyClinicalMLP(in_dim=16, h1=8, out_dim=3, lr=0.1)

    X = np.random.randn(20, 16)
    y_indices = np.random.randint(0, 3, size=20)

    # Treina o modelo por 30 épocas
    losses = mlp.fit(X, y_indices, epochs=30, batch_size=5)

    assert len(losses) == 30
    # A perda final deve ter reduzido em relação à inicial
    assert losses[-1] < losses[0]


def test_numpy_mlp_predict_and_safeguard():
    """Valida previsão com limiar de salvaguarda em NumPy puro."""
    mlp = NumpyClinicalMLP(in_dim=8, h1=4, out_dim=9)

    # Força pesos a zero para gerar probabilidades uniformes (1/9 ≈ 0.111 < 0.50)
    mlp.W2 = np.zeros_like(mlp.W2)
    mlp.b2 = np.zeros_like(mlp.b2)

    X = np.random.randn(3, 8)
    preds, confs = mlp.predict(X, threshold=0.50)

    # Deve recair na classe de fallback (índice 8)
    assert np.all(preds == 8)
    assert np.all(confs < 0.50)


def test_numpy_mlp_predict_distribution_and_percentages():
    """Valida distribuições e percentuais no baseline NumPy."""
    mlp = NumpyClinicalMLP(in_dim=16, h1=8, out_dim=9)
    X = np.random.randn(2, 16)

    dists = mlp.predict_distribution(X)
    assert len(dists) == 2
    for dist in dists:
        assert len(dist) == 9
        assert abs(sum(dist.values()) - 1.0) < 1e-4

    pcts = mlp.predict_percentages(X)
    assert len(pcts) == 2
    for p in pcts:
        assert len(p) == 9
        assert abs(sum(p.values()) - 100.0) < 0.1
