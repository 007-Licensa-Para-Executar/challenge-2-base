"""Testes da taxonomia Divertidamente (Inside Out) e How We Feel para sentimentos clínicos."""

from __future__ import annotations

import json

import pytest

from agents.patient_diary.contracts import EmotionCheckin, InvalidEntryError, parse_emotion_checkin
from models.emotion_taxonomy import (
    DIVERTIDAMENTE_CORE_EMOTIONS,
    DIVERTIDAMENTE_EMOTIONS,
    canonicalize_emotion_id,
    get_all_divertidamente_taxonomy,
    get_divertidamente_emotion,
    resolve_sub_emotion,
)


def test_core_divertidamente_emotions_count_and_colors():
    """Valida que existem exatamente 5 emoções nucleares de Divertidamente com as cores corretas."""
    assert len(DIVERTIDAMENTE_CORE_EMOTIONS) == 5

    core_map = {e.id: e for e in DIVERTIDAMENTE_CORE_EMOTIONS}
    expected_emotions = {
        "alegria": {"personagem": "Alegria", "cor_nome": "Amarelo", "cor_hex": "#FFD700"},
        "tristeza": {"personagem": "Tristeza", "cor_nome": "Azul", "cor_hex": "#1E88E5"},
        "medo": {"personagem": "Medo", "cor_nome": "Roxo", "cor_hex": "#8E24AA"},
        "raiva": {"personagem": "Raiva", "cor_nome": "Vermelho", "cor_hex": "#E53935"},
        "nojinho": {"personagem": "Nojinho", "cor_nome": "Verde", "cor_hex": "#43A047"},
    }

    for eid, expected in expected_emotions.items():
        assert eid in core_map
        emo = core_map[eid]
        assert emo.personagem == expected["personagem"]
        assert emo.cor_nome == expected["cor_nome"]
        assert emo.cor_hex.upper() == expected["cor_hex"].upper()
        assert emo.cor_secundaria_hex.startswith("#")


def test_each_emotion_has_exactly_three_sub_emotions_with_symbols():
    """Valida que cada emoção nuclear possui exatamente 3 sub-sentimentos com símbolos (How We Feel)."""
    for emo in DIVERTIDAMENTE_CORE_EMOTIONS:
        assert len(emo.sub_sentimentos) == 3, f"{emo.id} deve ter exatamente 3 sub-sentimentos"

        symbol_set = set()
        id_set = set()
        for sub in emo.sub_sentimentos:
            assert len(sub.id) > 0
            assert len(sub.nome) > 0
            assert len(sub.simbolo) > 0, f"Símbolo ausente para {sub.id}"
            assert len(sub.simbolo_slug) > 0
            assert len(sub.descricao) > 10
            assert sub.valencia in {"positiva", "negativa", "neutra"}
            assert sub.energia in {"alta", "moderada", "baixa"}
            assert len(sub.goemotions_origin) >= 1
            assert len(sub.keywords) >= 3

            symbol_set.add(sub.simbolo)
            id_set.add(sub.id)

        # Garante que cada sub-sentimento tem identificador e símbolo únicos dentro da emoção
        assert len(id_set) == 3
        assert len(symbol_set) == 3


def test_canonicalize_and_aliases():
    """Valida o mapeamento de aliases e labels do Ekman/GoEmotions para o Divertidamente."""
    assert canonicalize_emotion_id("nojo") == "nojinho"
    assert canonicalize_emotion_id("NOJINHO") == "nojinho"
    assert canonicalize_emotion_id("disgust") == "nojinho"
    assert canonicalize_emotion_id("alegria") == "alegria"
    assert canonicalize_emotion_id("joy") == "alegria"
    assert canonicalize_emotion_id("tristeza") == "tristeza"
    assert canonicalize_emotion_id("medo") == "medo"
    assert canonicalize_emotion_id("raiva") == "raiva"

    # get_divertidamente_emotion com alias
    prof_nojo = get_divertidamente_emotion("nojo")
    assert prof_nojo.id == "nojinho"
    assert prof_nojo.personagem == "Nojinho"
    assert prof_nojo.cor_nome == "Verde"

    # Fallback seguro para desconhecido
    prof_unknown = get_divertidamente_emotion("desconhecido_xyz")
    assert prof_unknown.id == "neutro"


def test_sub_emotion_resolution_alegria():
    """Valida resolução contextual de sub-sentimentos para Alegria (Gratidão, Otimismo, Entusiasmo)."""
    # Gratidão: 🙏
    sub1 = resolve_sub_emotion(
        "alegria", "Quero deixar registrado meu agradecimento e gratidão a todos."
    )
    assert sub1.id == "gratidao"
    assert sub1.simbolo == "🙏"

    # Otimismo: ☀️
    sub2 = resolve_sub_emotion(
        "alegria", "Tenho muita esperança de que esse tratamento novo vai trazer a recuperação."
    )
    assert sub2.id == "otimismo"
    assert sub2.simbolo == "☀️"

    # Entusiasmo: 🌟
    sub3 = resolve_sub_emotion(
        "alegria", "Hoje acordei radiante e muito animado com essa grande notícia."
    )
    assert sub3.id == "entusiasmo"
    assert sub3.simbolo == "🌟"


def test_sub_emotion_resolution_tristeza():
    """Valida resolução contextual de sub-sentimentos para Tristeza (Desânimo, Luto, Decepção)."""
    # Luto: 💧
    sub1 = resolve_sub_emotion(
        "tristeza", "Chorei o dia todo em lágrimas, sinto um luto imenso e vazio."
    )
    assert sub1.id == "luto"
    assert sub1.simbolo == "💧"

    # Desânimo: 🌧️
    sub2 = resolve_sub_emotion(
        "tristeza", "Sinto um desânimo que não passa, sem energia e tudo parece cinza."
    )
    assert sub2.id == "desanimo"
    assert sub2.simbolo == "🌧️"

    # Decepção: 🌫️
    sub3 = resolve_sub_emotion(
        "tristeza", "Fiquei com muita decepção e desapontado com o resultado do exame."
    )
    assert sub3.id == "decepcao"
    assert sub3.simbolo == "🌫️"


def test_sub_emotion_resolution_medo():
    """Valida resolução contextual de sub-sentimentos para Medo (Ansiedade, Pânico, Insegurança)."""
    # Ansiedade: 🌀
    sub1 = resolve_sub_emotion(
        "medo", "Estou muito ansioso com a biópsia de amanhã, meus pensamentos não param."
    )
    assert sub1.id == "ansiedade"
    assert sub1.simbolo == "🌀"

    # Pânico: ⚡
    sub2 = resolve_sub_emotion(
        "medo", "Tive uma crise súbita de pânico, coração disparado e falta de ar."
    )
    assert sub2.id == "panico"
    assert sub2.simbolo == "⚡"

    # Insegurança: 〰️
    sub3 = resolve_sub_emotion(
        "medo", "Me sinto vulnerável e insegura, com medo de tomar o remédio errado."
    )
    assert sub3.id == "inseguranca"
    assert sub3.simbolo == "〰️"


def test_sub_emotion_resolution_raiva():
    """Valida resolução contextual de sub-sentimentos para Raiva (Irritação, Indignação, Fúria)."""
    # Irritação: 💢
    sub1 = resolve_sub_emotion(
        "raiva", "Estou muito irritado com a demora de três horas na fila de espera."
    )
    assert sub1.id == "irritacao"
    assert sub1.simbolo == "💢"

    # Indignação: 🔥
    sub2 = resolve_sub_emotion(
        "raiva", "É uma injustiça e um absurdo cancelarem a consulta sem avisar, que indignação."
    )
    assert sub2.id == "indignacao"
    assert sub2.simbolo == "🔥"

    # Fúria: 💥
    sub3 = resolve_sub_emotion(
        "raiva", "Fiquei cego de fúria e ódio com aquele deboche, quase explodi."
    )
    assert sub3.id == "furia"
    assert sub3.simbolo == "💥"


def test_sub_emotion_resolution_nojinho():
    """Valida resolução contextual de sub-sentimentos para Nojinho (Aversão, Desconforto, Desprezo)."""
    # Aversão: 🛡️
    sub1 = resolve_sub_emotion(
        "nojinho", "Que nojo daquela comida estragada, fiquei com uma repulsa e náusea terrível."
    )
    assert sub1.id == "aversao"
    assert sub1.simbolo == "🛡️"

    # Desconforto: 🍋
    sub2 = resolve_sub_emotion(
        "nojinho", "Fiquei com um desconforto e um mal-estar enjoado durante todo o trajeto."
    )
    assert sub2.id == "desconforto"
    assert sub2.simbolo == "🍋"

    # Desprezo: 🚫
    sub3 = resolve_sub_emotion(
        "nojinho", "Sinto um desprezo profundo por essa hipocrisia e falsidade descarada."
    )
    assert sub3.id == "desprezo"
    assert sub3.simbolo == "🚫"


def test_sub_emotion_resolution_fallback():
    """Valida que texto sem palavras-chave específicas retorna o sub-sentimento padrão (primário)."""
    sub_default = resolve_sub_emotion("alegria", "Hoje o dia transcorreu bem.")
    assert sub_default == DIVERTIDAMENTE_EMOTIONS["alegria"].sub_sentimentos[0]


def test_taxonomy_serialization():
    """Valida que toda a taxonomia serializa limpa para JSON."""
    summary = get_all_divertidamente_taxonomy()
    assert "core_emotions" in summary
    assert "all_emotions" in summary
    assert len(summary["core_emotions"]) == 5

    json_str = json.dumps(summary, ensure_ascii=False)
    assert "Divertidamente" in json_str
    assert "How We Feel" in json_str
    assert "#FFD700" in json_str
    assert "#1E88E5" in json_str
    assert "#8E24AA" in json_str
    assert "#E53935" in json_str
    assert "#43A047" in json_str


def test_patient_diary_emotion_contract():
    """Valida o contrato Pydantic de checagem emocional do diário."""
    valid_data = {
        "entry_id": "relato-001",
        "primary_emotion": "alegria",
        "character": "Alegria",
        "color_name": "Amarelo",
        "color_hex": "#FFD700",
        "sub_emotion_name": "Gratidão",
        "sub_emotion_symbol": "🙏",
        "confidence": 0.92,
        "is_risk_emotion": False,
    }

    checkin = parse_emotion_checkin(**valid_data)
    assert isinstance(checkin, EmotionCheckin)
    assert checkin.entry_id == "relato-001"
    assert checkin.character == "Alegria"
    assert checkin.color_hex == "#FFD700"
    assert checkin.sub_emotion_symbol == "🙏"

    # Rejeita cor inválida (não hexadecimal)
    with pytest.raises(InvalidEntryError):
        parse_emotion_checkin(**{**valid_data, "color_hex": "amarelo-invalido"})

    # Rejeita confiança fora do intervalo 0.0 - 1.0
    with pytest.raises(InvalidEntryError):
        parse_emotion_checkin(**{**valid_data, "confidence": 1.5})

    # Rejeita campos extras desconhecidos (strict contract)
    with pytest.raises(InvalidEntryError):
        parse_emotion_checkin(**{**valid_data, "campo_estranho": "ataque"})


def test_edge_cases_and_null_safety():
    """Valida robustez contra entradas nulas, vazias e desconhecidas."""
    # Canonicalização com None e vazio
    assert canonicalize_emotion_id(None) == "neutro"
    assert canonicalize_emotion_id("") == "neutro"
    assert canonicalize_emotion_id("   ") == "neutro"

    # Perfil seguro para None e desconhecido
    prof_none = get_divertidamente_emotion(None)
    assert prof_none.id == "neutro"
    assert prof_none.personagem == "Neutro"

    # Resolução de sub-emoção com None e vazio
    sub_none = resolve_sub_emotion("alegria", None)
    assert sub_none == DIVERTIDAMENTE_EMOTIONS["alegria"].sub_sentimentos[0]

    sub_empty = resolve_sub_emotion("alegria", "   ")
    assert sub_empty == DIVERTIDAMENTE_EMOTIONS["alegria"].sub_sentimentos[0]

    # Busca de sub-emoção com None e vazio
    assert DIVERTIDAMENTE_EMOTIONS["alegria"].get_sub_emotion(None) is None
    assert DIVERTIDAMENTE_EMOTIONS["alegria"].get_sub_emotion("") is None


def test_import_from_patient_diary_package():
    """Valida que EmotionCheckin e parse_emotion_checkin estão disponíveis na raiz do módulo agents.patient_diary."""
    from agents.patient_diary import EmotionCheckin as DirectEmotionCheckin
    from agents.patient_diary import parse_emotion_checkin as direct_parse

    item = direct_parse(
        entry_id="e-teste",
        primary_emotion="medo",
        character="Medo",
        color_name="Roxo",
        color_hex="#8E24AA",
        sub_emotion_name="Ansiedade",
        sub_emotion_symbol="🌀",
        confidence=0.88,
        is_risk_emotion=True,
    )
    assert isinstance(item, DirectEmotionCheckin)
    assert item.character == "Medo"
    assert item.color_hex == "#8E24AA"
    assert item.sub_emotion_symbol == "🌀"
