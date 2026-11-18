"""Testes unitários para a rede neural de emoções e inferenciador de diários."""

from __future__ import annotations

import numpy as np

from models.emotion_net import EKMAN_LABELS, EmotionNeuralNetwork, EmotionPipeline
from models.emotion_predictor import EmotionDiaryPredictor, EmotionDiaryResult


def test_emotion_neural_network_forward_backward():
    """Valida o ciclo de propagação direta e reversa da rede em NumPy puro."""
    in_dim = 20
    hidden = 16
    out_dim = len(EKMAN_LABELS)
    batch_size = 8

    net = EmotionNeuralNetwork(dimension=[in_dim, hidden, out_dim], activation="relu", random_state=42)

    X = np.random.randn(batch_size, in_dim)
    Y = np.random.randint(0, 2, size=(batch_size, out_dim))

    net.definir_pesos(Y)
    assert net.pos_weight is not None
    assert net.pos_weight.shape == (out_dim, 1)

    probs = net.predict_proba_batches(X, batch_size=4)
    assert probs.shape == (batch_size, out_dim)
    assert np.all((probs >= 0.0) & (probs <= 1.0))

    initial_W1 = net.parametros["W1"].copy()
    net.fit_batches(X, Y, epocas=3, taxa_aprendizado=0.1, batch_size=4)
    assert not np.array_equal(initial_W1, net.parametros["W1"])
    assert len(net.loss_curve_) == 3


def test_emotion_pipeline_small_dataset(tmp_path):
    """Testa treino reduzido, persistência e carregamento do EmotionPipeline."""
    texts_train = [
        "Estou muito feliz e radiante hoje",
        "Sinto uma tristeza profunda e choro sem parar",
        "Que ódio e raiva dessa situação injusta",
        "Estou apavorado e com muito medo do diagnóstico",
        "Que surpresa inacreditável ver isso acontecer",
        "Que nojo dessa comida estragada e podre",
        "Peguei o ônibus e comprei o pão na padaria",
    ]
    # One-hot correspondente a cada classe de EKMAN_LABELS:
    # ["medo", "tristeza", "raiva", "nojo", "surpresa", "alegria", "neutro"]
    Y_train = np.array([
        [0, 0, 0, 0, 0, 1, 0],  # alegria
        [0, 1, 0, 0, 0, 0, 0],  # tristeza
        [0, 0, 1, 0, 0, 0, 0],  # raiva
        [1, 0, 0, 0, 0, 0, 0],  # medo
        [0, 0, 0, 0, 1, 0, 0],  # surpresa
        [0, 0, 0, 1, 0, 0, 0],  # nojo
        [0, 0, 0, 0, 0, 0, 1],  # neutro
    ])

    pipeline = EmotionPipeline(n_features=50, hidden_units=[16], random_state=42)
    pipeline.fit(
        texts_train=texts_train,
        Y_train=Y_train,
        texts_val=texts_train,
        Y_val=Y_train,
        epochs=5,
        lr=0.5,
        batch_size=2,
    )

    save_path = tmp_path / "test_pipeline.joblib"
    pipeline.save(save_path)
    assert save_path.exists()

    loaded = EmotionPipeline.load(save_path)
    assert loaded.thresholds_.shape == (len(EKMAN_LABELS),)

    pred = loaded.predict_primary_emotion("Hoje estou muito feliz e contente")
    assert isinstance(pred, dict)
    assert "primary_emotion" in pred
    assert pred["primary_emotion"] in EKMAN_LABELS


def test_emotion_diary_predictor_live_model():
    """Valida o preditor utilizando os pesos reais salvos em dist/."""
    predictor = EmotionDiaryPredictor()
    assert predictor.is_ready()

    # Caso 1: Tristeza / Luto
    res_tristeza = predictor.predict(
        "Hoje eu chorei o dia todo, sinto um aperto no peito, um luto imenso e um desespero que não passa."
    )
    assert isinstance(res_tristeza, EmotionDiaryResult)
    assert res_tristeza.primary_emotion == "tristeza"
    assert res_tristeza.is_risk_emotion is True
    assert res_tristeza.confidence > 0.4

    # Caso 2: Medo / Pânico
    res_medo = predictor.predict(
        "Estou em pânico e com muito medo dos resultados do exame, meu coração fica disparado e não consigo dormir."
    )
    assert res_medo.primary_emotion == "medo"
    assert res_medo.is_risk_emotion is True

    # Caso 3: Alegria / Gratidão
    res_alegria = predictor.predict(
        "Hoje foi um dia maravilhoso, a medicação fez efeito, me sinto em paz, com esperança e muito feliz."
    )
    assert res_alegria.primary_emotion == "alegria"
    assert res_alegria.is_risk_emotion is False

    # Caso 4: Neutro / Fato cotidiano
    res_neutro = predictor.predict(
        "Fui até o posto de saúde, peguei os medicamentos da receita e voltei para casa às duas da tarde."
    )
    assert res_neutro.primary_emotion == "neutro"
    assert res_neutro.is_risk_emotion is False

    # Caso 5: Texto vazio
    res_vazio = predictor.predict("")
    assert res_vazio.primary_emotion == "neutro"
    assert res_vazio.confidence == 1.0


def test_emotion_diary_predictor_batch():
    """Valida inferência em lote."""
    predictor = EmotionDiaryPredictor()
    batch = [
        "Estou me sentindo muito animado e feliz com o progresso do tratamento.",
        "Não sinto mais alegria em nada, tudo parece cinza e triste.",
    ]
    results = predictor.predict_batch(batch)
    assert len(results) == 2
    assert results[0].primary_emotion == "alegria"
    assert results[1].primary_emotion == "tristeza"
