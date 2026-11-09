"""Testes unitários para o ClinicalTextEmbedder."""

import numpy as np
import torch

from models.embedder import ClinicalTextEmbedder


def test_embedder_fit_and_vocabulary():
    """Valida construção do vocabulário com tokens especiais e frequências."""
    corpus = [
        "Estou muito cansado no trabalho hoje.",
        "Meu trabalho e minha carreira estao dificeis.",
        "A reuniao no trabalho foi desgastante.",
    ]
    embedder = ClinicalTextEmbedder(embedding_dim=64, max_features=10, stop_words=["no", "e"])
    embedder.fit(corpus)

    assert embedder._is_fitted
    assert embedder.embedding_matrix is not None
    assert embedder.embedding_matrix.shape == (len(embedder.vocab), 64)

    # PAD_TOKEN deve ser índice 0 e ter vetor estritamente nulo
    assert embedder.vocab[ClinicalTextEmbedder.PAD_TOKEN] == 0
    np.testing.assert_allclose(embedder.embedding_matrix[0], np.zeros(64))

    # UNK_TOKEN deve ser índice 1
    assert embedder.vocab[ClinicalTextEmbedder.UNK_TOKEN] == 1

    # 'trabalho' deve estar no vocabulário pois é o mais frequente
    assert "trabalho" in embedder.vocab
    assert embedder.vocab["trabalho"] >= 2


def test_embedder_transform_l2_normalization():
    """Valida que todos os vetores de embedding gerados possuem norma L2 unitária (1.0)."""
    corpus = [
        "Pressão por metas na empresa e sobrecarga de trabalho.",
        "Insônia terrível durante a madrugada.",
        "Dia neutro e tranquilo.",
    ]
    embedder = ClinicalTextEmbedder(embedding_dim=128, random_state=42)
    embedder.fit(corpus)
    embeddings = embedder.transform(corpus, normalize=True)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (3, 128)

    # Cada vetor deve ter norma 1.0 (hiperesfera unitária)
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, np.ones(3), atol=1e-5)


def test_embedder_oov_and_empty_text():
    """Valida resiliência a textos vazios e palavras fora do vocabulário (OOV)."""
    embedder = ClinicalTextEmbedder(embedding_dim=32, random_state=42)
    embedder.fit(["casa", "carro", "trabalho"])

    # Texto vazio
    res_empty = embedder.transform([""], normalize=True)
    assert res_empty.shape == (1, 32)
    assert not np.isnan(res_empty).any()
    np.testing.assert_allclose(np.linalg.norm(res_empty[0]), 1.0, atol=1e-5)

    # Texto com palavra desconhecida (OOV)
    res_oov = embedder.transform(["palavradesconhecidaqualquer"], normalize=True)
    assert res_oov.shape == (1, 32)
    assert not np.isnan(res_oov).any()
    np.testing.assert_allclose(np.linalg.norm(res_oov[0]), 1.0, atol=1e-5)


def test_embedder_texts_to_padded_tensor():
    """Valida conversão para tensor PyTorch com padding apropriado."""
    embedder = ClinicalTextEmbedder(embedding_dim=16)
    embedder.fit(["um dois tres", "um"])

    tensor = embedder.texts_to_padded_tensor(["um dois", "um", ""])
    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (3, 2)
    assert tensor.dtype == torch.long

    # A segunda sequência deve ter padding 0 na segunda posição
    assert tensor[1, 1].item() == 0


def test_embedder_set_embedding_weights():
    """Valida atualização de pesos aprendidos pelo PyTorch."""
    embedder = ClinicalTextEmbedder(embedding_dim=16, random_state=42)
    embedder.fit(["teste um", "teste dois"])

    vocab_size = len(embedder.vocab)
    new_weights = torch.ones((vocab_size, 16)) * 0.5
    embedder.set_embedding_weights(new_weights)

    # O vetor de PAD deve permanecer 0
    assert np.all(embedder.embedding_matrix[0] == 0.0)
    # Os demais vetores devem ser 0.5
    assert np.all(embedder.embedding_matrix[1:] == 0.5)
