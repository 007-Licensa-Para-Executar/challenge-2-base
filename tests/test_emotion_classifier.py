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

    net = EmotionNeuralNetwork(
        dimension=[in_dim, hidden, out_dim], activation="relu", random_state=42
    )

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
    Y_train = np.array(
        [
            [0, 0, 0, 0, 0, 1, 0],  # alegria
            [0, 1, 0, 0, 0, 0, 0],  # tristeza
            [0, 0, 1, 0, 0, 0, 0],  # raiva
            [1, 0, 0, 0, 0, 0, 0],  # medo
            [0, 0, 0, 0, 1, 0, 0],  # surpresa
            [0, 0, 0, 1, 0, 0, 0],  # nojo
            [0, 0, 0, 0, 0, 0, 1],  # neutro
        ]
    )

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
    assert res_tristeza.character == "Tristeza"
    assert res_tristeza.color_name == "Azul"
    assert res_tristeza.color_hex == "#1E88E5"
    assert res_tristeza.is_risk_emotion is True
    assert res_tristeza.confidence > 0.4
    assert res_tristeza.active_sub_emotion is not None
    assert res_tristeza.active_sub_emotion.id == "luto"
    assert res_tristeza.active_sub_emotion.simbolo == "💧"
    assert len(res_tristeza.all_sub_emotions) == 3

    # Caso 2: Medo / Pânico
    res_medo = predictor.predict(
        "Estou em pânico e com muito medo dos resultados do exame, meu coração fica disparado e não consigo dormir."
    )
    assert res_medo.primary_emotion == "medo"
    assert res_medo.character == "Medo"
    assert res_medo.color_name == "Roxo"
    assert res_medo.color_hex == "#8E24AA"
    assert res_medo.is_risk_emotion is True
    assert res_medo.active_sub_emotion is not None
    assert res_medo.active_sub_emotion.id == "panico"
    assert res_medo.active_sub_emotion.simbolo == "⚡"
    assert len(res_medo.all_sub_emotions) == 3

    # Caso 3: Alegria / Gratidão
    res_alegria = predictor.predict(
        "Hoje foi um dia maravilhoso, a medicação fez efeito, me sinto em paz, com esperança e muito feliz."
    )
    assert res_alegria.primary_emotion == "alegria"
    assert res_alegria.character == "Alegria"
    assert res_alegria.color_name == "Amarelo"
    assert res_alegria.color_hex == "#FFD700"
    assert res_alegria.is_risk_emotion is False
    assert res_alegria.active_sub_emotion is not None
    assert len(res_alegria.all_sub_emotions) == 3

    # Caso 4: Raiva / Fúria
    res_raiva = predictor.predict(
        "Senti uma fúria e um ódio gigantesco com o descaso dos médicos, que raiva desse hospital."
    )
    assert res_raiva.primary_emotion == "raiva"
    assert res_raiva.character == "Raiva"
    assert res_raiva.color_name == "Vermelho"
    assert res_raiva.color_hex == "#E53935"
    assert res_raiva.is_risk_emotion is True
    assert res_raiva.active_sub_emotion is not None
    assert res_raiva.active_sub_emotion.id == "furia"
    assert res_raiva.active_sub_emotion.simbolo == "💥"

    # Caso 5: Nojinho / Aversão
    res_nojinho = predictor.predict(
        "Que nojo terrível daquela comida podre e estragada, fiquei com uma repulsa e náusea insuportável."
    )
    assert res_nojinho.primary_emotion == "nojinho"
    assert res_nojinho.ekman_emotion == "nojo"
    assert res_nojinho.character == "Nojinho"
    assert res_nojinho.color_name == "Verde"
    assert res_nojinho.color_hex == "#43A047"
    assert res_nojinho.active_sub_emotion is not None
    assert res_nojinho.active_sub_emotion.id == "aversao"
    assert res_nojinho.active_sub_emotion.simbolo == "🛡️"

    # Caso 6: Neutro / Fato cotidiano
    res_neutro = predictor.predict(
        "Fui até o posto de saúde, peguei os medicamentos da receita e voltei para casa às duas da tarde."
    )
    assert res_neutro.primary_emotion == "neutro"
    assert res_neutro.character == "Neutro"
    assert res_neutro.color_name == "Cinza"
    assert res_neutro.color_hex == "#9E9E9E"
    assert res_neutro.is_risk_emotion is False

    # Caso 7: Texto vazio e None
    res_vazio = predictor.predict("")
    assert res_vazio.primary_emotion == "neutro"
    assert res_vazio.character == "Neutro"
    assert res_vazio.confidence == 1.0
    assert res_vazio.active_sub_emotion is not None
    assert res_vazio.active_sub_emotion.simbolo == "⚖️"

    res_none = predictor.predict(None)
    assert res_none.primary_emotion == "neutro"
    assert res_none.confidence == 1.0
    assert res_none.active_sub_emotion is not None

    # Validação da conversão em contrato EmotionCheckin
    checkin_alegria = res_alegria.to_checkin(entry_id="relato-alegria-01")
    assert checkin_alegria.entry_id == "relato-alegria-01"
    assert checkin_alegria.character == "Alegria"
    assert checkin_alegria.color_hex == "#FFD700"
    assert checkin_alegria.primary_emotion == "alegria"
    assert checkin_alegria.sub_emotion_symbol in {"🙏", "☀️", "🌟"}

    # Validação de analyze_entry
    from agents.patient_diary.contracts import EmotionCheckin

    class _MockEntry:
        entry_id = "entry-xyz"
        original_text = "Estou muito feliz e cheio de gratidão pelos enfermeiros."

    checkin_mock = predictor.analyze_entry(_MockEntry())
    assert isinstance(checkin_mock, EmotionCheckin)
    assert checkin_mock.entry_id == "entry-xyz"
    assert checkin_mock.character == "Alegria"
    assert checkin_mock.color_hex == "#FFD700"
    assert checkin_mock.sub_emotion_symbol == "🙏"

    # Validação da serialização to_dict()
    dict_res = res_alegria.to_dict()
    assert dict_res["character"] == "Alegria"
    assert dict_res["color_hex"] == "#FFD700"
    assert "active_sub_emotion" in dict_res
    assert "all_sub_emotions" in dict_res
    assert len(dict_res["all_sub_emotions"]) == 3


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
