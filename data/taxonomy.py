"""Taxonomia única de 6 classes, compartilhada por dataset real, sintético e split.

Qualquer mudança de rótulo deve ser feita apenas aqui, para que todos os scripts
usem sempre a mesma definição.
"""

from __future__ import annotations

CLASSES: tuple[str, ...] = (
    "autopercepcao",
    "vinculos",
    "desempenho",
    "fisico",
    "rupturas",
    "outros",
)
SAFEGUARD_CLASS = "outros"

CLASS_LABELS_PT: dict[str, str] = {
    "autopercepcao": "Autopercepção",
    "vinculos": "Vínculos",
    "desempenho": "Desempenho",
    "fisico": "Físico",
    "rupturas": "Rupturas",
    "outros": "Outros",
}

CLASS_DESCRIPTIONS: dict[str, str] = {
    "autopercepcao": "autoestima, identidade, imagem corporal e sensação de incapacidade ou inadequação",
    "vinculos": "relacionamentos amorosos, amizades, família, términos, traições e separações",
    "desempenho": "trabalho, estudos e finanças (cobranças, metas, provas, dívidas)",
    "fisico": "saúde física e mental em sintomas, sono, tratamento médico, dores e sonhos",
    "rupturas": "perdas por morte e luto",
    "outros": "sem tema clínico claro ou relato neutro",
}

# Desempate quando duas classes têm o mesmo número de evidências: a primeira vence.
# Rupturas vem antes de Vínculos para que "meu pai morreu" não caia em Vínculos.
TIE_BREAK_ORDER: tuple[str, ...] = (
    "rupturas",
    "vinculos",
    "autopercepcao",
    "fisico",
    "desempenho",
)

# Mapeamento das 9 classes antigas (8 temas + outros_indeterminado) para as 6 novas.
LEGACY_TO_NEW: dict[str, str] = {
    "autoestima": "autopercepcao",
    "relacionamentos": "vinculos",
    "familia": "vinculos",
    "trabalho": "desempenho",
    "estudos": "desempenho",
    "financas": "desempenho",
    "saude_sono": "fisico",
    "luto": "rupturas",
    "outros_indeterminado": SAFEGUARD_CLASS,
}


def remap_legacy_label(label: str) -> str:
    """Converte um rótulo antigo para a nova taxonomia; rótulos novos passam direto."""
    if label in CLASSES:
        return label
    if label in LEGACY_TO_NEW:
        return LEGACY_TO_NEW[label]
    raise ValueError(f"Rótulo desconhecido: {label!r}")
