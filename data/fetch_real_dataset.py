"""Download, extração, reclassificação e balanceamento do dataset de saúde mental em português.

Fonte: 'rhaymison/mental-health-pt' (Hugging Face).

Limitações conhecidas:
- É um dataset público de pares pergunta/resposta. Não há garantia de que os textos
  sejam relatos reais de pacientes: confirmar licença e procedência antes de uso.
- Os rótulos vêm de regras de palavras-chave (heurística). Registros com evidência
  fraca recebem 'revisar_manual': True para revisão humana.
- A anonimização cobre apenas padrões (e-mail, CPF, telefone). Nomes não são removidos.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import random
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from data.taxonomy import CLASSES, SAFEGUARD_CLASS, TIE_BREAK_ORDER

logger = logging.getLogger(__name__)

DATASET_PARQUET_URL = (
    "https://huggingface.co/datasets/rhaymison/mental-health-pt/resolve/main/data/train-00000-of-00001.parquet"
)
DEFAULT_CACHE_PATH = Path("data/cache/mental_health_pt.parquet")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
SOURCE_TAG = "huggingface:rhaymison/mental-health-pt"

# Padrões aplicados sobre o texto em minúsculas. Cada padrão conta no máximo uma vez por classe.
# O \b inicial evita falsos positivos como 'pai' em 'paixão' ou 'prova' em 'comprova'.
THEME_RULES: dict[str, list[str]] = {
    "rupturas": [  # apenas perdas por morte e luto
        r"\bluto\b",
        r"\bfaleci",
        r"\bmorreu\b",
        r"\bmorreram\b",
        r"\bmorte\b",
        r"\bfunera",
        r"\bvelório|\bvelorio",
        r"\bente querido",
        r"\bperda recente",
        r"\bperdi (meu|minha) (pai|mãe|mae|avô|avó|avo|irmã|irmão|filh|marido|esposa|melhor amig)",
        r"\bperda (de|do|da) (um |uma )?(ente|pessoa|pai|mãe|filh)",
        r"\bsaudade d[oae] (quem|meu|minha|ele|ela)\b",
    ],
    "vinculos": [  # relacionamentos, família, términos, traições e separações
        r"\brelacionament",
        r"\bnamorad",
        r"\bcasament",
        r"\bdivórcio|\bdivorcio",
        r"\bseparaç|\bseparac",
        r"\btérmino|\btermino",
        r"\brompimento",
        r"\bmeu ex\b",
        r"\bminha ex\b",
        r"\btra[ií]ç|\btraíd|\btraid",
        r"\bamizade",
        r"\bamig[oa]s?\b",
        r"\bfam[ií]li",
        r"\bpais\b",
        r"\bpai\b",
        r"\bm[aã]e\b",
        r"\bfilh[oa]s?\b",
        r"\birm[ãa]o?s?\b",
        r"\bsobrinh",
        r"\bpadrasto|\bmadrasta",
        r"\bparceir",
        r"\bcônjuge|\bconjuge",
        r"\bciúme|\bciume",
        r"\bsolid[ãa]o",
        r"\bsolit[aá]ri[oa]\b",
        r"\bisolad[oa]\b",
        r"\bme sentindo muito s[oó]\b",
        r"\bsozinh",
    ],
    "autopercepcao": [  # autoestima, identidade, imagem corporal, sensação de incapacidade
        r"\bautoestima",
        r"\bauto-estima",
        r"\bautoimagem",
        r"\bautocr[ií]tica",
        r"\bimagem corporal",
        r"\baparência|\baparencia",
        r"\bme acho\b",
        r"\binseguran",
        r"\bincapaz",
        r"\bfracass",
        r"\binút[ei]l|\binutil",
        r"\binutilidade",
        r"\bfeio\b|\bfeia\b",
        r"\bgord[oa]\b|\bmagr[oa]\b",
        r"\bvergonha\b",
        r"\bculpa\b|\bculpad[oa]\b",
        r"\bdecepcionad[oa] comigo",
        r"\bbom o suficiente",
        r"\bvalor próprio|\bvalor proprio",
        r"\bidentidade",
        r"\bquem sou\b",
        r"\bsem prop[oó]sito|\bsem rumo\b|\bsem dire[çc][ãa]o",
        r"\bfraude\b",
        r"\bburro\b|\bburra\b",
        r"\bnão me sinto suficiente|\bnao me sinto suficiente",
    ],
    "fisico": [  # saúde, sono, tratamento médico, dores e sonhos
        r"\bdorm",
        r"\bsono\b",
        r"\binsônia|\binsonia",
        r"\bpesadel",
        r"\bsonh",
        r"\bansiedad|\bansios[oa]\b",
        r"\bpânico|\bpanico",
        r"\bdeprim|\bdepress",
        r"\bfadiga",
        r"\bcansa[çc]o",
        r"\bexaust",
        r"\bestresse\b",
        r"\bdoen[çc]",
        r"\bm[eé]dic",
        r"\bremédio|\bremedio",
        r"\bsintoma",
        r"\bdores?\b",
        r"\btratamento",
        r"\bterapia",
        r"\bfisioterap",
        r"\btaquicardia",
        r"\bgastrite|\bestômago|\bestomago",
        r"\bpress[ãa]o arterial",
        r"\bapetite\b",
    ],
    "desempenho": [  # trabalho, estudos e finanças em geral
        r"\btrabalh",
        r"\bemprego",
        r"\bchefe",
        r"\bcarreira",
        r"\bempresa",
        r"\bdemiss",
        r"\bprodutividade",
        r"\bmetas?\b",
        r"\bobjetivos\b",
        r"\bresponsabilidades\b",
        r"\bprocrastin",
        r"\bconcentra[çc][ãa]o|\bmotiva[çc][ãa]o|\bmem[oó]ria\b",
        r"\bprazo",
        r"\bcliente",
        r"\best[aá]gio",
        r"\bestud",
        r"\bfaculdade",
        r"\buniversidade",
        r"\bprovas?\b",
        r"\btcc\b",
        r"\breprov",
        r"\bprofessor",
        r"\bvestibular",
        r"\baulas?\b",
        r"\bcurso\b",
        r"\bdiploma",
        r"\bmat[ée]rias?\b",
        r"\bnotas?\b",
        r"\bfinan",
        r"\bdívida|\bdivida|\bendivid",
        r"\bdinheiro",
        r"\borçamento|\borcamento",
        r"\bsalário|\bsalario",
        r"\bcontas? (a pagar|vencid)|\bpagar as contas",
        r"\bcusto de vida",
        r"\bempréstimo|\bemprestimo",
    ],
}

_COMPILED_RULES: dict[str, list[re.Pattern[str]]] = {
    cls: [re.compile(p) for p in patterns] for cls, patterns in THEME_RULES.items()
}

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b"), "[TELEFONE]"),
]

# Formato Llama-2: o relato do paciente fica entre <</SYS> (ou <</SYS>>) e [/INST].
_EXTRACT_RE = re.compile(r"<</SYS>>?\s*(.*?)\s*\[/INST\]", re.DOTALL)


def scrub_pii(text: str) -> str:
    """Remove padrões de identificação. Não substitui uma anonimização completa."""
    for rx, replacement in _PII_PATTERNS:
        text = rx.sub(replacement, text)
    return text


def classify_text(text: str) -> tuple[str, int]:
    """Classifica pela quantidade de padrões que batem em cada classe.

    Retorna (classe, força), em que força é o número de padrões que bateram na classe vencedora.
    Empates seguem TIE_BREAK_ORDER. Sem nenhuma evidência, retorna (outros, 0).
    """
    lowered = text.lower()
    scores = {cls: sum(1 for rx in rxs if rx.search(lowered)) for cls, rxs in _COMPILED_RULES.items()}
    best = max(scores.values())
    if best == 0:
        return SAFEGUARD_CLASS, 0
    winner = next(cls for cls in TIE_BREAK_ORDER if scores[cls] == best)
    return winner, best


def load_parquet_bytes(
    url: str = DATASET_PARQUET_URL,
    cache_path: Path | None = DEFAULT_CACHE_PATH,
    timeout: float = 60.0,
) -> bytes:
    """Lê o parquet do cache local, ou baixa e salva no cache."""
    if cache_path is not None and cache_path.exists():
        logger.info("Usando cache local: %s", cache_path)
        return cache_path.read_bytes()

    logger.info("Baixando dataset: %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)
    return data


def extract_patient_texts(data: bytes) -> list[str]:
    """Extrai relatos únicos do paciente, com espaços normalizados e PII removida."""
    table = pq.read_table(io.BytesIO(data), columns=["input"])
    texts: list[str] = []
    seen: set[str] = set()
    for raw in table.column("input").to_pylist():
        if not isinstance(raw, str):
            continue
        match = _EXTRACT_RE.search(raw)
        if not match:
            continue
        clean = scrub_pii(re.sub(r"\s+", " ", match.group(1)).strip())
        if len(clean) >= 25 and clean not in seen:
            seen.add(clean)
            texts.append(clean)
    logger.info("Relatos únicos extraídos: %d", len(texts))
    return texts


def reclassify_real_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reclassifica registros reais existentes pelo texto, preservando o rótulo anterior."""
    before = Counter(rec.get("macro_tema") for rec in records)
    out: list[dict[str, Any]] = []
    for rec in records:
        label, strength = classify_text(rec.get("texto", ""))
        new = dict(rec)
        new["macro_tema_anterior"] = rec.get("macro_tema")
        new["macro_tema"] = label
        new["forca_regra"] = strength
        new["revisar_manual"] = strength < 2
        out.append(new)
    logger.info("Distribuição anterior: %s", dict(before))
    logger.info("Distribuição nova: %s", dict(Counter(r["macro_tema"] for r in out)))
    return out


def build_real_dataset(
    target_samples_per_class: int = 140,
    seed: int = 42,
    output_path: str = "data/real_diaries.json",
    cache_path: Path | None = DEFAULT_CACHE_PATH,
    include_outros: bool = False,
) -> list[dict[str, Any]]:
    """Gera o dataset real balanceado por classe e salva em JSON."""
    texts = extract_patient_texts(load_parquet_bytes(cache_path=cache_path))
    rng = random.Random(seed)
    rng.shuffle(texts)

    by_class: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for text in texts:
        label, strength = classify_text(text)
        by_class[label].append((text, strength))

    target_classes = CLASSES if include_outros else tuple(c for c in CLASSES if c != SAFEGUARD_CLASS)
    records: list[dict[str, Any]] = []
    for cls in target_classes:
        pool = by_class.get(cls, [])
        if len(pool) < target_samples_per_class:
            logger.warning(
                "Classe %s: %d relatos disponíveis, abaixo do alvo de %d",
                cls, len(pool), target_samples_per_class,
            )
        # Mistura evidência forte (>=2) e moderada (==1) para manter diversidade lexical.
        strong = [item for item in pool if item[1] >= 2]
        moderate = [item for item in pool if item[1] < 2]
        selected = strong[: target_samples_per_class // 2] + moderate
        if len(selected) < target_samples_per_class:
            selected = strong + moderate
        else:
            remaining = target_samples_per_class - len(strong[: target_samples_per_class // 2])
            if len(moderate) < remaining:
                selected = strong[: target_samples_per_class - len(moderate)] + moderate
            else:
                selected = strong[: target_samples_per_class // 2] + moderate[:remaining]
        for idx, (text, strength) in enumerate(selected[:target_samples_per_class], start=1):
            records.append(
                {
                    "id": f"real_{cls}_{idx:03d}",
                    "texto": text,
                    "macro_tema": cls,
                    "forca_regra": strength,
                    "revisar_manual": strength < 2,
                    "group_id": "",
                    "source": SOURCE_TAG,
                    "modalidade": "texto",
                    "taxonomia": "v6",
                }
            )

    rng.shuffle(records)
    for n, rec in enumerate(records, start=1):
        rec["group_id"] = f"real_group_{n:04d}"

    _write_json(records, output_path)
    logger.info("Dataset real salvo em %s (%d relatos).", output_path, len(records))
    return records


def _write_json(data: Any, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/real_diaries.json", help="Caminho de saída do JSON")
    parser.add_argument("--samples-per-class", type=int, default=140, help="Amostras por classe")
    parser.add_argument("--seed", type=int, default=42, help="Semente pseudoaleatória")
    parser.add_argument("--cache", default=str(DEFAULT_CACHE_PATH), help="Cache local do parquet")
    parser.add_argument(
        "--include-outros",
        action="store_true",
        help="Inclui relatos sem correspondência de regra como classe 'outros'",
    )
    parser.add_argument(
        "--reclassify", metavar="JSON", default=None,
        help="Reclassifica um JSON real existente pelo texto, sem baixar nada",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.reclassify:
        records = json.loads(Path(args.reclassify).read_text(encoding="utf-8"))
        _write_json(reclassify_real_records(records), args.output)
        return

    build_real_dataset(
        target_samples_per_class=args.samples_per_class,
        seed=args.seed,
        output_path=args.output,
        cache_path=Path(args.cache) if args.cache else None,
        include_outros=args.include_outros,
    )


if __name__ == "__main__":
    main()
