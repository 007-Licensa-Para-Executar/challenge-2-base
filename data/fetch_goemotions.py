"""Download e estruturação do dataset GoEmotions traduzido para PT-BR.

Mapeia as 28 emoções originais do GoEmotions para as 7 emoções de Paul Ekman
(medo, tristeza, raiva, nojo, surpresa, alegria, neutro), unifica duplicatas sem
vazamento entre splits e exporta conjuntos balanceados para treino da rede neural.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/Equilibrium-Residencia-IA/emotional-dataset-pt-br.git"

EMOTIONS_28 = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring",
    "confusion", "curiosity", "desire", "disappointment", "disapproval",
    "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief",
    "joy", "love", "nervousness", "optimism", "pride", "realization",
    "relief", "remorse", "sadness", "surprise", "neutral",
]

EKMAN_MAP: dict[str, list[str]] = {
    "medo": ["fear", "nervousness"],
    "tristeza": ["sadness", "grief", "disappointment", "remorse", "embarrassment"],
    "raiva": ["anger", "annoyance", "disapproval"],
    "nojo": ["disgust"],
    "surpresa": ["surprise", "realization", "confusion", "curiosity"],
    "alegria": [
        "joy", "amusement", "approval", "excitement", "gratitude", "love",
        "optimism", "relief", "pride", "admiration", "desire", "caring",
    ],
    "neutro": ["neutral"],
}

EKMAN_LABELS = list(EKMAN_MAP.keys())

# Ordem de prioridade clínica para definir a emoção predominante (Single Label)
# Emoções associadas a sofrimento/risco têm prioridade sobre estados positivos ou neutros
CLINICAL_PRIORITY = ["medo", "tristeza", "raiva", "nojo", "surpresa", "alegria", "neutro"]

PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+\]")
WORD_RE = re.compile(r"[a-záàâãéêíóôõúüç]+", re.IGNORECASE)


def count_content_words(text: str) -> int:
    """Conta palavras reais desconsiderando placeholders como [NAME], [RELIGION]."""
    cleaned = PLACEHOLDER_RE.sub(" ", text)
    return len(WORD_RE.findall(cleaned))


def normalize_text(text: str) -> str:
    """Decodifica entidades HTML e limpa URLs, marcações de subreddit e espaços extras."""
    text = html.unescape(text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"(?<!\w)/?[ru]/\w+", " ", text)
    text = re.sub(r"^\s*>+\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def load_raw_batches(source_dir: Path) -> pd.DataFrame:
    """Lê todos os lotes JSON traduzidos."""
    search_paths = [
        source_dir / "*_translated.json",
        source_dir / "translated" / "*_translated.json",
    ]
    files: list[str] = []
    for pattern in search_paths:
        matched = sorted(glob.glob(str(pattern)))
        if matched:
            files = matched
            break

    if not files:
        raise FileNotFoundError(f"Nenhum arquivo *_translated.json encontrado em {source_dir}")

    logger.info("Carregando %d arquivos de lotes em %s...", len(files), source_dir)
    records = []
    for fpath in files:
        with open(fpath, encoding="utf-8") as f:
            records.extend(json.load(f))

    df = pd.DataFrame(records)
    logger.info("Carregados %d registros brutos.", len(df))
    return df


def preprocess_goemotions(
    raw_df: pd.DataFrame,
    min_words: int = 2,
    drop_neutral_mixed: bool = True,
) -> pd.DataFrame:
    """Aplica o pipeline completo de limpeza, desduplicação e mapeamento Ekman."""
    txt = raw_df["translated_text"].fillna("")
    orig = raw_df["original_text"].fillna("")

    # 1. Filtros de qualidade da tradução
    is_broken = txt.str.contains(r'^\s*\{|"items"\s*:|\{response\}|\{[a-z_.]+\}', regex=True)
    is_untranslated = txt.str.strip() == orig.str.strip()
    is_bot = txt.str.contains(r"(?i)^\s*!?\s*remind ?me|good bot|bad bot", regex=True)

    valid_mask = ~(is_broken | is_untranslated | is_bot)
    clean_df = raw_df[valid_mask].copy()
    logger.info("Após remoção de traduções inválidas/bots: %d registros.", len(clean_df))

    # 2. Normalização textual e filtro de extensão mínima
    clean_df["text"] = clean_df["translated_text"].map(normalize_text)
    clean_df = clean_df[clean_df["text"].map(count_content_words) >= min_words].copy()
    logger.info("Após normalização e remoção de textos curtos (<%d palavras): %d.", min_words, len(clean_df))

    # 3. Tratamento de rótulo 'neutral' misturado
    def filter_neutral(emotions: list[str]) -> list[str]:
        if drop_neutral_mixed and len(emotions) > 1 and "neutral" in emotions:
            return [e for e in emotions if e != "neutral"]
        return list(emotions)

    clean_df["emotions"] = clean_df["emotions"].map(filter_neutral)

    # 4. Desduplicação unificando rótulos
    clean_df["norm"] = clean_df["text"].str.lower()
    dedup = (
        clean_df.groupby("norm", sort=False)
        .agg(
            id=("id", "first"),
            split_original=("split", "first"),
            text=("text", "first"),
            emotions=("emotions", lambda s: sorted({x for l in s for x in l if x in EMOTIONS_28})),
        )
        .reset_index(drop=True)
    )
    logger.info("Após unificação de duplicatas: %d registros únicos.", len(dedup))

    # 5. Mapeamento para as 7 emoções de Ekman (Multi-hot)
    for ekman_label, sub_emotions in EKMAN_MAP.items():
        dedup[ekman_label] = dedup["emotions"].map(
            lambda emo_list, sub=set(sub_emotions): int(bool(sub.intersection(emo_list)))
        )

    # 6. Emoção principal de acordo com a ordem de prioridade clínica
    def assign_primary_emotion(row: pd.Series) -> str:
        for p in CLINICAL_PRIORITY:
            if row[p] == 1:
                return p
        return "neutro"

    dedup["primary_emotion"] = dedup.apply(assign_primary_emotion, axis=1)
    return dedup


def export_splits(df: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    """Exporta os CSVs por split e salva metadados do processamento."""
    output_dir.mkdir(parents=True, exist_ok=True)
    split_map = {"train": "train", "dev": "validation", "test": "test"}

    cols = ["id", "text"] + EKMAN_LABELS + ["primary_emotion"]
    stats: dict[str, Any] = {"total_samples": len(df), "splits": {}}

    for orig_split, split_name in split_map.items():
        split_df = df[df["split_original"] == orig_split][cols]
        out_csv = output_dir / f"{split_name}.csv"
        split_df.to_csv(out_csv, index=False, encoding="utf-8")

        distribution = {label: int(split_df[label].sum()) for label in EKMAN_LABELS}
        primary_distribution = split_df["primary_emotion"].value_counts().to_dict()

        stats["splits"][split_name] = {
            "samples": len(split_df),
            "file": str(out_csv.name),
            "multilabel_distribution": distribution,
            "primary_emotion_distribution": primary_distribution,
        }
        logger.info("Exportado %s: %d registros -> %s", split_name, len(split_df), out_csv)

    meta_file = output_dir / "dataset_summary.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    logger.info("Metadados salvos em %s", meta_file)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Processa GoEmotions PT-BR para Ekman.")
    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help="Diretório onde os arquivos *_translated.json estão localizados.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/goemotions",
        help="Diretório de saída para os CSVs gerados (default: data/goemotions).",
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=2,
        help="Mínimo de palavras de conteúdo para manter o texto (default: 2).",
    )
    args = parser.parse_args()

    # Busca em locais padrão se source-dir não fornecido
    source_path = None
    if args.source_dir:
        source_path = Path(args.source_dir)
    else:
        candidates = [
            Path("C:/Users/BLU8CA/.gemini/antigravity-cli/brain/c62d62fa-8f23-4f94-85eb-5b9ec3900962/scratch/emotional-dataset-pt-br"),
            Path("data/raw/emotional-dataset-pt-br"),
            Path("emotional-dataset-pt-br"),
        ]
        for c in candidates:
            if c.exists() and (c / "translated").exists():
                source_path = c
                break

    if source_path is None or not source_path.exists():
        logger.info("Clonando repositório de dados: %s", REPO_URL)
        clone_dest = Path("data/raw/emotional-dataset-pt-br")
        clone_dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(clone_dest)], check=True)
        source_path = clone_dest

    output_path = Path(args.output_dir)

    raw_df = load_raw_batches(source_path)
    clean_df = preprocess_goemotions(raw_df, min_words=args.min_words)
    stats = export_splits(clean_df, output_path)

    print("\nResumo do Processamento do Dataset GoEmotions PT-BR:")
    print(f"Total de registros únicos: {stats['total_samples']}")
    for split, info in stats["splits"].items():
        print(f"  • {split.capitalize():12s}: {info['samples']} amostras")


if __name__ == "__main__":
    main()
