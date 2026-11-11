"""Treino e inferência devem usar a mesma transformação e os pesos completos."""

import joblib
import numpy as np
import pytest
import torch

from models.embedder import ClinicalTextEmbedder
from models.predictor import ClinicalThemePredictor
from models.torch_mlp import ClinicalThemeMLP


def test_saved_dense_model_matches_original_normalized_prediction(tmp_path):
    vectorizer = ClinicalTextEmbedder(embedding_dim=8, init_strategy='gaussian', random_state=42)
    vectorizer.fit(['minha família avós cuidados', 'trabalho chefe reunião'])
    model = ClinicalThemeMLP(input_dim=8, hidden_dim1=12, hidden_dim2=6)
    model.eval()
    text = 'cuidados da minha família'
    expected = model.predict_proba(torch.tensor(
        vectorizer.transform([text], normalize=True), dtype=torch.float32,
    )).detach().numpy()[0]
    weights, embedder = tmp_path / 'weights.pt', tmp_path / 'embedder.joblib'
    torch.save(model.state_dict(), weights)
    joblib.dump(vectorizer, embedder)
    predictor = ClinicalThemePredictor(model_path=weights, vectorizer_path=embedder)
    assert predictor.model.embedding_bag is None
    actual = list(predictor.predict_text(text).probabilities.values())
    np.testing.assert_allclose(actual, expected, atol=0.00005)
    np.testing.assert_allclose(
        predictor.model.predict_proba(torch.tensor(
            vectorizer.transform([text], normalize=True), dtype=torch.float32,
        )).detach().numpy()[0], expected, rtol=1e-6,
    )
    broken = model.state_dict()
    del broken['fc2.weight']
    torch.save(broken, weights)
    with pytest.raises((KeyError, RuntimeError)):
        ClinicalThemePredictor(model_path=weights, vectorizer_path=embedder)
