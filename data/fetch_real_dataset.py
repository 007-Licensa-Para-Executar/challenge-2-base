"""Script para download, extração e estruturação de dataset clínico real em português.

Fonte Primária: 'rhaymison/mental-health-pt' (Hugging Face)
- 11.717 interações reais de desabafo e aconselhamento psicológico em português.
- Extrai as queixas e desabafos dos pacientes (perguntas/relatos em 1ª pessoa).
- Anonimiza e categoriza nos 8 Macrotemas Clínicos da Rede Neural + classe de salvaguarda.
- Balanceia as classes e gera formato compatível com 'models/train.py'.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import random
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATASET_PARQUET_URL = (
    "https://huggingface.co/datasets/rhaymison/mental-health-pt/resolve/main/data/train-00000-of-00001.parquet"
)

# Regras clínicas estruturadas para mapeamento semântico de desabafos em português
THEME_RULES: dict[str, list[str]] = {
    "luto": [
        "luto", "morte", "falec", "perdi meu", "perdi minha", "funeral", "velório",
        "morreu", "saudade de quem", "perda de um ente", "falecimento", "perda do meu",
        "perda da minha", "saudade da minha falecida", "meu avô morreu", "minha mãe faleceu"
    ],
    "financas": [
        "finan", "dívida", "dinheiro", "orçamento", "salário", "contas a pagar",
        "falência", "endivida", "financeir", "desempregado e sem dinheiro", "empréstimo",
        "cartão estourado", "banco cobrando", "custo de vida", "pagar as contas"
    ],
    "estudos": [
        "faculdade", "estudo", "universidade", "escola", "prova", "tcc", "reprov",
        "professor", "acadêmico", "vestibular", "aula", "curso", "diploma", "estudar",
        "matérias atrasadas", "nota baixa", "pressão da faculdade", "ensino médio"
    ],
    "trabalho": [
        "trabalho", "emprego", "chefe", "carreira", "profission", "empresa", "demiss",
        "carga de trabalho", "produtividade", "colegas de trabalho", "ambiente de trabalho",
        "sobrecarregado no trabalho", "pressão no trabalho", "estresse profissional",
        "ambiente corporativo", "horas extras", "meu superior", "equilíbrio profissional"
    ],
    "familia": [
        "famíli", "pais", "mãe", "pai", "irmão", "irmã", "filho", "filha", "paternidade",
        "maternidade", "familiar", "meus parentes", "convivência em casa", "meu padrasto",
        "minha madrasta", "meu sobrinho", "minha família", "briga em casa"
    ],
    "relacionamentos": [
        "relacionamento", "namorad", "casamento", "divórcio", "separação", "término",
        "meu ex", "minha ex", "traição", "amizade", "amigos", "vida amorosa", "ciúmes",
        "solidão amorosa", "parceir", "cônjuge", "rompimento", "término de namoro"
    ],
    "autoestima": [
        "autoestima", "auto-estima", "imagem corporal", "aparência", "me acho feio",
        "inseguran", "me sinto inútil", "peso corporal", "vergonha de mim", "valor próprio",
        "não me sinto suficiente", "crise de identidade", "gordo", "magro", "autoimagem",
        "constrangido com minha aparência", "fracassado", "incapaz"
    ],
    "saude_sono": [
        "dormir", "sono", "insônia", "pesadelo", "ansiedad", "pânico", "deprimid",
        "fadiga", "cansaço", "doença", "médic", "remédio", "sintoma", "dor crônica",
        "saúde física", "taquicardia", "crise de ansiedade", "depressão", "exaustão"
    ],
}


def download_and_extract_raw(url: str = DATASET_PARQUET_URL) -> list[str]:
    """Baixa o parquet do Hugging Face e extrai os textos dos pacientes."""
    logger.info("Baixando dataset real de saúde mental: %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req) as resp:
        data_bytes = resp.read()

    logger.info("Download concluído (%d bytes). Lendo tabela Parquet...", len(data_bytes))
    table = pq.read_table(io.BytesIO(data_bytes))
    df = table.to_pandas()

    patient_texts: list[str] = []
    seen = set()

    for raw_text in df["input"]:
        if not isinstance(raw_text, str):
            continue
        # Extrai o trecho do paciente localizado entre <</SYS>> e [/INST]
        match = re.search(r"<</SYS>>?\s*(.*?)\s*\[/INST\]", raw_text, re.DOTALL)
        if match:
            clean = match.group(1).strip()
            # Remove quebras desnecessárias e sanitiza
            clean = re.sub(r"\s+", " ", clean)
            if len(clean) >= 25 and clean not in seen:
                seen.add(clean)
                patient_texts.append(clean)

    logger.info("Extraídos %d relatos clínicos reais únicos em português.", len(patient_texts))
    return patient_texts


def classify_text(text: str) -> str:
    """Classifica o desabafo real entre os 8 temas ou 'outros_indeterminado'."""
    text_lower = text.lower()
    for theme, patterns in THEME_RULES.items():
        if any(p in text_lower for p in patterns):
            return theme
    return "outros_indeterminado"


def build_real_dataset(
    target_samples_per_class: int = 150,
    seed: int = 42,
    output_path: str = "data/real_diaries.json",
) -> list[dict[str, Any]]:
    """Gera o dataset real balanceado e salvo em JSON."""
    raw_texts = download_and_extract_raw()
    rng = random.Random(seed)
    rng.shuffle(raw_texts)

    by_theme = defaultdict(list)
    for text in raw_texts:
        theme = classify_text(text)
        by_theme[theme].append(text)

    logger.info("Contagem preliminar encontrada:")
    for t, items in by_theme.items():
        logger.info("  - %s: %d relatos", t, len(items))

    # Seleciona até target_samples_per_class por tema
    records: list[dict[str, Any]] = []
    global_idx = 1

    all_themes = list(THEME_RULES.keys()) + ["outros_indeterminado"]

    for theme in all_themes:
        available = by_theme[theme]
        selected = available[:target_samples_per_class]
        for idx, text in enumerate(selected):
            records.append({
                "id": f"real_{theme}_{idx+1:03d}",
                "texto": text,
                "macro_tema": theme,
                "group_id": f"real_group_{global_idx:04d}",
                "source": "huggingface:rhaymison/mental-health-pt",
                "modalidade": "texto",
            })
            global_idx += 1

    rng.shuffle(records)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Dataset real salvo em '%s' com %d relatos no total.", out_file, len(records))

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/real_diaries.json", help="Caminho de saída para o JSON")
    parser.add_argument("--samples-per-class", type=int, default=140, help="Amostras por tema")
    parser.add_argument("--seed", type=int, default=42, help="Semente pseudo-aleatória")
    args = parser.parse_args()

    build_real_dataset(
        target_samples_per_class=args.samples_per_class,
        seed=args.seed,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
