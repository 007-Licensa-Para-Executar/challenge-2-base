"""Taxonomia de Emoções inspirada no filme Divertidamente e na plataforma How We Feel.

Estrutura os sentimentos da rede neural (GoEmotions PT-BR) no espectro do Divertidamente:
- Alegria: Amarelo (#FFD700)
- Tristeza: Azul (#1E88E5)
- Medo: Roxo (#8E24AA)
- Raiva: Vermelho (#E53935)
- Nojinho: Verde (#43A047)

Cada sentimento principal possui exatamente 3 sub-sentimentos com símbolos visuais,
nuances e mapeamento para as emoções granulares do GoEmotions / How We Feel.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SubEmotion:
    """Sub-sentimento granular com símbolo e nuance descritiva (How We Feel)."""

    id: str
    nome: str
    simbolo: str
    simbolo_slug: str
    descricao: str
    valencia: str  # "positiva", "negativa", "neutra"
    energia: str  # "alta", "moderada", "baixa"
    goemotions_origin: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["goemotions_origin"] = list(self.goemotions_origin)
        d["keywords"] = list(self.keywords)
        return d


@dataclass(frozen=True)
class EmotionDivertidamente:
    """Perfil emocional principal no universo Divertidamente com cores e sub-sentimentos."""

    id: str
    personagem: str
    cor_nome: str
    cor_hex: str
    cor_secundaria_hex: str
    descricao: str
    is_risk_emotion: bool
    sub_sentimentos: tuple[SubEmotion, ...]
    ekman_aliases: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "personagem": self.personagem,
            "cor_nome": self.cor_nome,
            "cor_hex": self.cor_hex,
            "cor_secundaria_hex": self.cor_secundaria_hex,
            "descricao": self.descricao,
            "is_risk_emotion": self.is_risk_emotion,
            "ekman_aliases": list(self.ekman_aliases),
            "sub_sentimentos": [s.to_dict() for s in self.sub_sentimentos],
        }

    def get_sub_emotion(self, sub_id_or_name: str | None) -> SubEmotion | None:
        if not sub_id_or_name:
            return None
        target = sub_id_or_name.strip().lower()
        for sub in self.sub_sentimentos:
            if sub.id.lower() == target or sub.nome.lower() == target:
                return sub
        return None


# 1. ALEGRIA (Amarelo / #FFD700)
ALEGRIA_DEF = EmotionDivertidamente(
    id="alegria",
    personagem="Alegria",
    cor_nome="Amarelo",
    cor_hex="#FFD700",
    cor_secundaria_hex="#FFF9C4",
    descricao="Celebração da vida, otimismo, gratidão e estados de ânimo radiantes e acolhedores.",
    is_risk_emotion=False,
    ekman_aliases=("alegria", "joy"),
    sub_sentimentos=(
        SubEmotion(
            id="gratidao",
            nome="Gratidão",
            simbolo="🙏",
            simbolo_slug="glowing-heart",
            descricao="Apreço caloroso pelo suporte, pelas pequenas vitórias e pelas pessoas queridas ao redor.",
            valencia="positiva",
            energia="moderada",
            goemotions_origin=("gratitude", "caring"),
            keywords=(
                "gratidão",
                "grato",
                "grata",
                "obrigado",
                "obrigada",
                "agradeço",
                "agradecer",
                "agradecida",
                "agradecido",
                "abençoado",
                "abençoada",
                "reconhecimento",
            ),
        ),
        SubEmotion(
            id="otimismo",
            nome="Otimismo",
            simbolo="☀️",
            simbolo_slug="radiant-sun",
            descricao="Confiança no futuro, esperança de melhoras e perspectiva positiva diante dos desafios clínicos.",
            valencia="positiva",
            energia="alta",
            goemotions_origin=("optimism", "relief"),
            keywords=(
                "esperança",
                "otimista",
                "confiante",
                "vai dar certo",
                "melhorando",
                "futuro",
                "fé",
                "progresso",
                "alívio",
                "aliviado",
                "aliviada",
                "recuperação",
            ),
        ),
        SubEmotion(
            id="entusiasmo",
            nome="Entusiasmo",
            simbolo="🌟",
            simbolo_slug="vibrant-star",
            descricao="Energia vibrante, empolgação, vitalidade e alegria expansiva no momento presente.",
            valencia="positiva",
            energia="alta",
            goemotions_origin=("joy", "excitement", "amusement", "pride"),
            keywords=(
                "animado",
                "animada",
                "empolgado",
                "empolgada",
                "radiante",
                "feliz",
                "alegria",
                "maravilha",
                "maravilhoso",
                "maravilhosa",
                "celebro",
                "vibrante",
                "ótimo",
                "ótima",
                "excelente",
            ),
        ),
    ),
)

# 2. TRISTEZA (Azul / #1E88E5)
TRISTEZA_DEF = EmotionDivertidamente(
    id="tristeza",
    personagem="Tristeza",
    cor_nome="Azul",
    cor_hex="#1E88E5",
    cor_secundaria_hex="#BBDEFB",
    descricao="Sinaliza a necessidade de recolhimento, elaboração de perdas e pedido de acolhimento e suporte.",
    is_risk_emotion=True,
    ekman_aliases=("tristeza", "sadness"),
    sub_sentimentos=(
        SubEmotion(
            id="desanimo",
            nome="Desânimo",
            simbolo="🌧️",
            simbolo_slug="rain-cloud",
            descricao="Falta de motivação, apatia emocional e sensação de cansaço ou peso interior constante.",
            valencia="negativa",
            energia="baixa",
            goemotions_origin=("sadness",),
            keywords=(
                "desânimo",
                "desanimado",
                "desanimada",
                "cansado",
                "cansada",
                "sem energia",
                "apático",
                "apática",
                "desmotivado",
                "desmotivada",
                "pesado",
                "cinza",
                "sem vontade",
            ),
        ),
        SubEmotion(
            id="luto",
            nome="Luto",
            simbolo="💧",
            simbolo_slug="teardrop",
            descricao="Dor profunda por uma perda, choro doloroso, desolação e vazio emocional agudo.",
            valencia="negativa",
            energia="baixa",
            goemotions_origin=("grief",),
            keywords=(
                "luto",
                "chorei",
                "choro",
                "chorando",
                "lágrimas",
                "perda",
                "vazio",
                "saudade dolorosa",
                "desolação",
                "aperto no peito",
                "coração doendo",
                "partida",
            ),
        ),
        SubEmotion(
            id="decepcao",
            nome="Decepção",
            simbolo="🌫️",
            simbolo_slug="fog-mist",
            descricao="Frustração diante de expectativas frustradas, remorso ou desalento após recaídas.",
            valencia="negativa",
            energia="baixa",
            goemotions_origin=("disappointment", "remorse", "embarrassment"),
            keywords=(
                "decepção",
                "decepcionado",
                "decepcionada",
                "desapontado",
                "desapontada",
                "remorso",
                "culpa",
                "desiludido",
                "desiludida",
                "esperava mais",
                "fracasso",
                "vergonha",
            ),
        ),
    ),
)

# 3. MEDO (Roxo / #8E24AA)
MEDO_DEF = EmotionDivertidamente(
    id="medo",
    personagem="Medo",
    cor_nome="Roxo",
    cor_hex="#8E24AA",
    cor_secundaria_hex="#E1BEE7",
    descricao="Alerta protetor diante de ameaças reais ou imaginadas, ativando prudência e antecipação de riscos.",
    is_risk_emotion=True,
    ekman_aliases=("medo", "fear"),
    sub_sentimentos=(
        SubEmotion(
            id="ansiedade",
            nome="Ansiedade",
            simbolo="🌀",
            simbolo_slug="inner-vortex",
            descricao="Preocupação antecipatória, pensamentos em turbilhão acelerado e incerteza persistente sobre exames ou futuro.",
            valencia="negativa",
            energia="alta",
            goemotions_origin=("nervousness",),
            keywords=(
                "ansioso",
                "ansiosa",
                "ansiedade",
                "preocupado",
                "preocupada",
                "preocupação",
                "aflito",
                "aflita",
                "angústia",
                "angustiado",
                "pensamentos não param",
                "insônia",
                "inquieto",
                "tensão",
            ),
        ),
        SubEmotion(
            id="panico",
            nome="Pânico",
            simbolo="⚡",
            simbolo_slug="sharp-pulse",
            descricao="Alarme físico extremo, taquicardia súbita, falta de ar e sensação de perigo iminente ou perda de controle.",
            valencia="negativa",
            energia="alta",
            goemotions_origin=("fear",),
            keywords=(
                "pânico",
                "apavorado",
                "apavorada",
                "coração disparado",
                "falta de ar",
                "terror",
                "desespero",
                "medo insuportável",
                "paralisado",
                "paralisada",
                "socorro",
                "crise",
            ),
        ),
        SubEmotion(
            id="inseguranca",
            nome="Insegurança",
            simbolo="〰️",
            simbolo_slug="tremor-wave",
            descricao="Fragilidade pessoal, hesitação receosa e sensação de desamparo perante decisões de saúde.",
            valencia="negativa",
            energia="moderada",
            goemotions_origin=("nervousness",),
            keywords=(
                "inseguro",
                "insegura",
                "insegurança",
                "vulnerável",
                "medo de falhar",
                "hesitante",
                "sem chão",
                "desprotegido",
                "desprotegida",
                "dúvida",
                "indecisão",
            ),
        ),
    ),
)

# 4. RAIVA (Vermelho / #E53935)
RAIVA_DEF = EmotionDivertidamente(
    id="raiva",
    personagem="Raiva",
    cor_nome="Vermelho",
    cor_hex="#E53935",
    cor_secundaria_hex="#FFCDD2",
    descricao="Mobilização energética impulsionada por injustiças, quebra de limites, dores ou barreiras impostas.",
    is_risk_emotion=True,
    ekman_aliases=("raiva", "anger"),
    sub_sentimentos=(
        SubEmotion(
            id="irritacao",
            nome="Irritação",
            simbolo="💢",
            simbolo_slug="spark-annoyance",
            descricao="Impaciência e atrito com incômodos cotidianos, demoras ou atritos de convivência.",
            valencia="negativa",
            energia="alta",
            goemotions_origin=("annoyance",),
            keywords=(
                "irritado",
                "irritada",
                "irritação",
                "impaciente",
                "estressado",
                "estressada",
                "saco cheio",
                "incômodo",
                "chateado",
                "chateada",
                "nervoso",
                "nervosa",
            ),
        ),
        SubEmotion(
            id="indignacao",
            nome="Indignação",
            simbolo="🔥",
            simbolo_slug="blaze-flame",
            descricao="Revolta vigorosa e protesto moral diante de descaso, desrespeito ou injustiça no tratamento.",
            valencia="negativa",
            energia="alta",
            goemotions_origin=("disapproval",),
            keywords=(
                "indignado",
                "indignada",
                "indignação",
                "injustiça",
                "revolta",
                "absurdo",
                "desrespeito",
                "inaceitável",
                "descaso",
                "revoltado",
                "revoltada",
                "injusto",
            ),
        ),
        SubEmotion(
            id="furia",
            nome="Fúria",
            simbolo="💥",
            simbolo_slug="burst-rage",
            descricao="Cólera intensa, pulso explosivo e forte desejo de rompimento que demanda contenção cuidadosa.",
            valencia="negativa",
            energia="alta",
            goemotions_origin=("anger",),
            keywords=(
                "fúria",
                "furioso",
                "furiosa",
                "ódio",
                "raiva cega",
                "vontade de quebrar tudo",
                "explodi",
                "ira",
                "incontrolável",
            ),
        ),
    ),
)

# 5. NOJINHO (Verde / #43A047)
NOJINHO_DEF = EmotionDivertidamente(
    id="nojinho",
    personagem="Nojinho",
    cor_nome="Verde",
    cor_hex="#43A047",
    cor_secundaria_hex="#C8E6C9",
    descricao="Instinto protetor de repulsa contra alimentos deteriorados, odores aversivos ou comportamentos tóxicos.",
    is_risk_emotion=False,
    ekman_aliases=("nojo", "nojinho", "disgust"),
    sub_sentimentos=(
        SubEmotion(
            id="aversao",
            nome="Aversão",
            simbolo="🛡️",
            simbolo_slug="barrier-repulsion",
            descricao="Repulsa visceral e necessidade física de afastamento frente a cheiros, gostos ou estímulos insalubres.",
            valencia="negativa",
            energia="moderada",
            goemotions_origin=("disgust",),
            keywords=(
                "nojo",
                "nojento",
                "nojenta",
                "repulsa",
                "náusea",
                "ânsia",
                "podre",
                "estragado",
                "aversão",
                "enjoo",
                "vomitar",
                "asqueroso",
            ),
        ),
        SubEmotion(
            id="desconforto",
            nome="Desconforto",
            simbolo="🍋",
            simbolo_slug="acid-leaf",
            descricao="Desagrado sutil, mal-estar gustativo ou estranhamento corporal e sensorial incômodo.",
            valencia="negativa",
            energia="moderada",
            goemotions_origin=("disapproval",),
            keywords=(
                "desconforto",
                "desagradável",
                "gosto ruim",
                "amargo",
                "enjoado",
                "enjoada",
                "mal-estar",
                "desconfortável",
                "repugnância",
                "ruim",
            ),
        ),
        SubEmotion(
            id="desprezo",
            nome="Desprezo",
            simbolo="🚫",
            simbolo_slug="cold-dismissal",
            descricao="Julgamento desaprovador e distanciamento crítico em relação a atitudes falsas ou degradantes.",
            valencia="negativa",
            energia="baixa",
            goemotions_origin=("disapproval",),
            keywords=(
                "desprezo",
                "desdém",
                "falsidade",
                "hipocrisia",
                "patético",
                "patética",
                "rejeição",
                "falsas",
                "falsos",
            ),
        ),
    ),
)

# FALLBACK HARMONIZADO: NEUTRO (Cinza / #9E9E9E)
NEUTRO_DEF = EmotionDivertidamente(
    id="neutro",
    personagem="Neutro",
    cor_nome="Cinza",
    cor_hex="#9E9E9E",
    cor_secundaria_hex="#ECEFF1",
    descricao="Estado basal de calma e estabilidade, com relatos objetivos de fatos cotidianos sem alta carga emocional.",
    is_risk_emotion=False,
    ekman_aliases=("neutro", "neutral"),
    sub_sentimentos=(
        SubEmotion(
            id="equilibrio",
            nome="Equilíbrio",
            simbolo="⚖️",
            simbolo_slug="balance-scale",
            descricao="Estabilidade emocional e factual, registrando a rotina diária sem grandes oscilações.",
            valencia="neutra",
            energia="moderada",
            goemotions_origin=("neutral",),
            keywords=("normal", "rotina", "comum", "neutro", "fato", "dia normal", "trabalho"),
        ),
        SubEmotion(
            id="serenidade",
            nome="Serenidade",
            simbolo="🌊",
            simbolo_slug="gentle-wave",
            descricao="Quietude e tranquilidade mental suave, sem euforia nem angústia.",
            valencia="neutra",
            energia="baixa",
            goemotions_origin=("neutral",),
            keywords=(
                "calmo",
                "calma",
                "sereno",
                "serena",
                "tranquilo",
                "tranquila",
                "em paz",
                "sossegado",
            ),
        ),
        SubEmotion(
            id="sobriedade",
            nome="Sobriedade",
            simbolo="🍃",
            simbolo_slug="neutral-leaf",
            descricao="Foco pragmático em atividades de saúde, medicamentos e compromissos.",
            valencia="neutra",
            energia="moderada",
            goemotions_origin=("neutral",),
            keywords=(
                "posto de saúde",
                "remédio",
                "consulta",
                "horário",
                "almoço",
                "médico",
                "exame",
            ),
        ),
    ),
)

# FALLBACK HARMONIZADO: SURPRESA (Laranja / #FB8C00)
SURPRESA_DEF = EmotionDivertidamente(
    id="surpresa",
    personagem="Surpresa",
    cor_nome="Laranja",
    cor_hex="#FB8C00",
    cor_secundaria_hex="#FFE0B2",
    descricao="Reação de impacto ou quebra de expectativa diante do inesperado.",
    is_risk_emotion=False,
    ekman_aliases=("surpresa", "surprise"),
    sub_sentimentos=(
        SubEmotion(
            id="espanto",
            nome="Espanto",
            simbolo="⚡",
            simbolo_slug="shock-spark",
            descricao="Sobressalto imediato frente a um acontecimento imprevisto.",
            valencia="neutra",
            energia="alta",
            goemotions_origin=("surprise",),
            keywords=(
                "espanto",
                "chocado",
                "chocada",
                "inacreditável",
                "surpreso",
                "surpresa",
                "susto",
            ),
        ),
        SubEmotion(
            id="curiosidade",
            nome="Curiosidade",
            simbolo="🔍",
            simbolo_slug="curious-lens",
            descricao="Interesse vívido e atenção desperta para compreender uma novidade.",
            valencia="positiva",
            energia="alta",
            goemotions_origin=("curiosity",),
            keywords=(
                "curioso",
                "curiosa",
                "curiosidade",
                "interessante",
                "querendo saber",
                "intrigado",
            ),
        ),
        SubEmotion(
            id="descoberta",
            nome="Descoberta",
            simbolo="💡",
            simbolo_slug="insight-bulb",
            descricao="Clareza repentina e revelação positiva a partir de uma constatação nova.",
            valencia="positiva",
            energia="alta",
            goemotions_origin=("realization",),
            keywords=("percebi", "descobri", "entendi", "ficha caiu", "compreendi", "insight"),
        ),
    ),
)


# Catálogo completo indexado por ID canônico
DIVERTIDAMENTE_EMOTIONS: dict[str, EmotionDivertidamente] = {
    "alegria": ALEGRIA_DEF,
    "tristeza": TRISTEZA_DEF,
    "medo": MEDO_DEF,
    "raiva": RAIVA_DEF,
    "nojinho": NOJINHO_DEF,
    "neutro": NEUTRO_DEF,
    "surpresa": SURPRESA_DEF,
}

# As 5 emoções nucleares de Divertidamente (Inside Out)
DIVERTIDAMENTE_CORE_EMOTIONS: list[EmotionDivertidamente] = [
    ALEGRIA_DEF,
    TRISTEZA_DEF,
    MEDO_DEF,
    RAIVA_DEF,
    NOJINHO_DEF,
]

# Mapa de aliases (incluindo Ekman labels) para o ID canônico
_ALIAS_MAP: dict[str, str] = {
    # Nojo / Nojinho
    "nojo": "nojinho",
    "nojinho": "nojinho",
    "disgust": "nojinho",
    # Alegria
    "alegria": "alegria",
    "joy": "alegria",
    # Tristeza
    "tristeza": "tristeza",
    "sadness": "tristeza",
    # Medo
    "medo": "medo",
    "fear": "medo",
    # Raiva
    "raiva": "raiva",
    "anger": "raiva",
    # Neutro
    "neutro": "neutro",
    "neutral": "neutro",
    # Surpresa
    "surpresa": "surpresa",
    "surprise": "surpresa",
}


def canonicalize_emotion_id(label_or_name: str | None) -> str:
    """Normaliza rótulos do Ekman/GoEmotions para o ID canônico do Divertidamente."""
    if not label_or_name:
        return "neutro"
    cleaned = label_or_name.strip().lower()
    if not cleaned:
        return "neutro"
    return _ALIAS_MAP.get(cleaned, cleaned)


def get_divertidamente_emotion(label_or_name: str | None) -> EmotionDivertidamente:
    """Recupera o perfil do Divertidamente correspondente ao rótulo."""
    can_id = canonicalize_emotion_id(label_or_name)
    if can_id in DIVERTIDAMENTE_EMOTIONS:
        return DIVERTIDAMENTE_EMOTIONS[can_id]
    # Fallback seguro para neutro caso venha um rótulo desconhecido
    return NEUTRO_DEF


def resolve_sub_emotion(emotion_id: str, text: str | None) -> SubEmotion:
    """Identifica o sub-sentimento mais específico no texto do relato.

    Analisa palavras-chave contextuais do paciente dentro do subconjunto
    de 3 sub-sentimentos da emoção identificada pela rede neural.
    Se não houver termo distintivo ou houver empate, retorna o primeiro (primário).
    """
    profile = get_divertidamente_emotion(emotion_id)
    sub_list = profile.sub_sentimentos
    if not sub_list:
        raise ValueError(f"Perfil {profile.id} não possui sub-sentimentos cadastrados.")

    if not text:
        return sub_list[0]

    clean_text = text.lower().strip()
    if not clean_text:
        return sub_list[0]

    # Tokenização simples de palavras para matching exato
    words = set(re.findall(r"[a-záàâãéêíóôõúüç]+", clean_text))

    best_sub: SubEmotion = sub_list[0]
    best_score = -1

    for sub in sub_list:
        score = 0
        for kw in sub.keywords:
            kw_clean = kw.lower()
            if " " in kw_clean:
                # Frase/expressão composta
                if kw_clean in clean_text:
                    score += 3
            else:
                if kw_clean in words:
                    score += 2

        if score > best_score and score > 0:
            best_score = score
            best_sub = sub

    return best_sub


def get_all_divertidamente_taxonomy() -> dict[str, Any]:
    """Retorna a árvore taxonômica completa estruturada para consumo via API/UI."""
    return {
        "source": "Divertidamente (Inside Out) & How We Feel",
        "core_emotions": [e.to_dict() for e in DIVERTIDAMENTE_CORE_EMOTIONS],
        "all_emotions": {k: v.to_dict() for k, v in DIVERTIDAMENTE_EMOTIONS.items()},
    }
