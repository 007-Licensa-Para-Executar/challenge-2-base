"""Serviço de inferência da Rede Neural para entendimento de diários e separação em tópicos.

Cumpre os requisitos estabelecidos em docs/rede-neural.md, docs/deep-learning-neural.md
e docs/agente1.md:
- Compreensão de relatos de diários textuais com inferência rápida e determinística;
- Separação percentual entre temas (ex: 60% tema_1, 15% tema_3, 0% tema_2);
- Decomposição ("destrinchamento") do relato em tópicos e trechos literais (grounding);
- Salvaguarda clínica matemática com fallback seguro para outros_indeterminado.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path("dist/best_theme_mlp.pt")
DEFAULT_VECTORIZER_PATH = Path("dist/tfidf_vectorizer.joblib")


@dataclass
class TopicDistribution:
    """Distribuição de probabilidades e percentuais preditos pela rede neural."""

    primary_theme: str
    confidence: float
    primary_percentage: float
    percentages: dict[str, float]
    probabilities: dict[str, float]
    ranking: list[dict[str, Any]]
    top_topics: list[dict[str, Any]]
    is_fallback: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiaryTopicSegment:
    """Trecho literal do relato com o tópico e percentuais atribuídos pela rede."""

    quote: str
    start_char: int
    end_char: int
    theme: str
    confidence: float
    percentages: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiaryTopicBreakdown:
    """Decomposição do diário do paciente em tópicos com fundamentação literal."""

    text: str
    global_theme: str
    global_confidence: float
    theme_percentages: dict[str, float]
    topic_weights: dict[str, float]
    segments: list[DiaryTopicSegment]
    detected_topics: list[str]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClinicalThemePredictor:
    """Inferenciador e decompositor temático baseado na rede neural treinada."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        vectorizer_path: str | Path | None = None,
        model: ClinicalThemeMLP | None = None,
        vectorizer: TfidfVectorizer | None = None,
        device: str = "cpu",
    ) -> None:
        self.device = torch.device(device)

        if vectorizer is not None:
            self.vectorizer = vectorizer
        else:
            v_path = Path(vectorizer_path or DEFAULT_VECTORIZER_PATH)
            if not v_path.exists():
                raise FileNotFoundError(
                    f"Vetorizador TF-IDF não encontrado em '{v_path}'. "
                    "Execute 'python -m models.train' para treinar a rede."
                )
            self.vectorizer = joblib.load(v_path)

        if model is not None:
            self.model = model.to(self.device)
        else:
            m_path = Path(model_path or DEFAULT_MODEL_PATH)
            if not m_path.exists():
                raise FileNotFoundError(
                    f"Pesos da rede neural não encontrados em '{m_path}'. "
                    "Execute 'python -m models.train' para treinar a rede."
                )
            input_dim = len(self.vectorizer.vocabulary_)
            self.model = ClinicalThemeMLP(input_dim=input_dim, num_classes=len(THEME_CLASSES))
            state_dict = torch.load(m_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)

        self.model.eval()

    def predict_text(self, text: str, threshold: float = 0.50) -> TopicDistribution:
        """Processa um texto de diário e calcula a separação de temas com percentuais.

        Args:
            text: Texto do relato do paciente.
            threshold: Limiar de corte de salvaguarda (padrão 0.50). Se a probabilidade
                máxima for menor que o limiar, ativa fallback para outros_indeterminado.

        Returns:
            TopicDistribution com tema primário, probabilidades e percentuais detalhados.
        """
        cleaned = text.strip() if isinstance(text, str) else ""
        if not cleaned:
            # Caso vazio: fallback seguro
            empty_probs = {theme: 0.0 for theme in THEME_CLASSES}
            empty_probs["outros_indeterminado"] = 1.0
            empty_pcts = {theme: 0.0 for theme in THEME_CLASSES}
            empty_pcts["outros_indeterminado"] = 100.0
            return TopicDistribution(
                primary_theme="outros_indeterminado",
                confidence=1.0,
                primary_percentage=100.0,
                percentages=empty_pcts,
                probabilities=empty_probs,
                ranking=[{"tema": "outros_indeterminado", "percentual": 100.0, "probabilidade": 1.0}],
                top_topics=[{"tema": "outros_indeterminado", "percentual": 100.0, "probabilidade": 1.0}],
                is_fallback=True,
            )

        features = self.vectorizer.transform([cleaned]).toarray()
        t_features = torch.tensor(features, dtype=torch.float32, device=self.device)

        with torch.no_grad():
            probs_tensor = self.model.predict_proba(t_features)[0]
            probs_np = probs_tensor.cpu().numpy()

        probabilities = {THEME_CLASSES[i]: float(probs_np[i]) for i in range(len(THEME_CLASSES))}
        percentages = {
            THEME_CLASSES[i]: round(float(probs_np[i]) * 100.0, 2)
            for i in range(len(THEME_CLASSES))
        }

        max_idx = int(torch.argmax(probs_tensor).item())
        max_prob = float(probs_np[max_idx])
        predicted_theme = THEME_CLASSES[max_idx]

        is_fallback = max_prob < threshold
        if is_fallback:
            primary_theme = "outros_indeterminado"
            confidence = max_prob
            primary_pct = percentages.get(primary_theme, 0.0)
        else:
            primary_theme = predicted_theme
            confidence = max_prob
            primary_pct = percentages[primary_theme]

        ranking = sorted(
            [
                {"tema": theme, "percentual": percentages[theme], "probabilidade": probabilities[theme]}
                for theme in THEME_CLASSES
            ],
            key=lambda item: item["percentual"],
            reverse=True,
        )

        # Tópicos com presença significativa (>= 1.0%)
        top_topics = [item for item in ranking if item["percentual"] >= 1.0]

        return TopicDistribution(
            primary_theme=primary_theme,
            confidence=round(confidence, 4),
            primary_percentage=primary_pct,
            percentages=percentages,
            probabilities={t: round(p, 4) for t, p in probabilities.items()},
            ranking=ranking,
            top_topics=top_topics,
            is_fallback=is_fallback,
        )

    def predict_batch(
        self, texts: list[str], threshold: float = 0.50
    ) -> list[TopicDistribution]:
        """Executa a inferência vetorizada para um lote de relatos."""
        return [self.predict_text(text, threshold=threshold) for text in texts]

    def destrinchar_diario(
        self,
        text: str,
        threshold: float = 0.50,
        segment_threshold: float = 0.30,
        min_segment_chars: int = 15,
    ) -> DiaryTopicBreakdown:
        """Decompõe o relato do paciente em tópicos, evidências literais e pesos proporcionais.

        Conforme discutido nas diretrizes do projeto (docs/deep-learning-neural.md e
        docs/agente1.md), cada oração/período é associada a seu tema e evidência literal,
        permitindo ao psicólogo inspecionar a composição temática do diário (ex: 60% tema_1,
        15% tema_3, 0% tema_2).
        """
        full_text = text if isinstance(text, str) else ""
        global_dist = self.predict_text(full_text, threshold=threshold)

        if not full_text.strip():
            return DiaryTopicBreakdown(
                text=full_text,
                global_theme="outros_indeterminado",
                global_confidence=1.0,
                theme_percentages=global_dist.percentages,
                topic_weights={t: (100.0 if t == "outros_indeterminado" else 0.0) for t in THEME_CLASSES},
                segments=[],
                detected_topics=["outros_indeterminado"],
                summary="Relato vazio ou sem conteúdo analisável.",
            )

        # Decomposição do texto em sentenças mantendo índices de início e fim exatos
        sentence_pattern = re.compile(r"[^.!?\n]+(?:[.!?\n]+|$)")
        segments: list[DiaryTopicSegment] = []
        topic_char_counts: dict[str, int] = {theme: 0 for theme in THEME_CLASSES}
        total_analyzed_chars = 0

        for match in sentence_pattern.finditer(full_text):
            raw_quote = match.group()
            stripped_quote = raw_quote.strip()
            if len(stripped_quote) < min_segment_chars:
                continue

            # Ajusta os índices para coincidir estritamente com a citação sem espaços excedentes
            leading_spaces = len(raw_quote) - len(raw_quote.lstrip())
            start_char = match.start() + leading_spaces
            end_char = start_char + len(stripped_quote)

            seg_dist = self.predict_text(stripped_quote, threshold=segment_threshold)
            seg_theme = seg_dist.primary_theme

            segment = DiaryTopicSegment(
                quote=stripped_quote,
                start_char=start_char,
                end_char=end_char,
                theme=seg_theme,
                confidence=seg_dist.confidence,
                percentages=seg_dist.percentages,
            )
            segments.append(segment)

            seg_len = len(stripped_quote)
            topic_char_counts[seg_theme] = topic_char_counts.get(seg_theme, 0) + seg_len
            total_analyzed_chars += seg_len

        # Calcula o peso percentual de cada tópico baseado no volume de texto discutido
        if total_analyzed_chars > 0:
            topic_weights = {
                theme: round((topic_char_counts.get(theme, 0) / total_analyzed_chars) * 100.0, 2)
                for theme in THEME_CLASSES
            }
        else:
            # Se nenhuma sentença atingiu o comprimento mínimo, usa a distribuição global
            topic_weights = global_dist.percentages.copy()

        # Tópicos detectados com proporção relevante no relato (> 0%)
        detected = [
            theme
            for theme, weight in sorted(topic_weights.items(), key=lambda item: item[1], reverse=True)
            if weight > 0.0
        ]
        if not detected:
            detected = [global_dist.primary_theme]

        # Resumo clínico legível
        summary_parts = [
            f"{theme}: {weight:.1f}%"
            for theme, weight in sorted(topic_weights.items(), key=lambda item: item[1], reverse=True)
            if weight > 0.0
        ]
        resumo = (
            f"Tema preponderante global: {global_dist.primary_theme} "
            f"({global_dist.primary_percentage:.1f}%). "
            f"Distribuição destrinchada nos segmentos do relato: " + ", ".join(summary_parts)
            if summary_parts
            else f"Tema: {global_dist.primary_theme}"
        )

        return DiaryTopicBreakdown(
            text=full_text,
            global_theme=global_dist.primary_theme,
            global_confidence=global_dist.confidence,
            theme_percentages=global_dist.percentages,
            topic_weights=topic_weights,
            segments=segments,
            detected_topics=detected,
            summary=resumo,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entendimento de Diários e Separação de Temas via Rede Neural"
    )
    parser.add_argument("text", nargs="?", type=str, help="Texto do diário para análise")
    parser.add_argument("--text", dest="text_opt", type=str, help="Texto do diário para análise")
    parser.add_argument("--file", type=str, help="Caminho de arquivo com o relato do diário")
    parser.add_argument(
        "--destrinchar",
        action="store_true",
        help="Decompõe o relato em tópicos por sentença com citações literais",
    )
    parser.add_argument("--json", action="store_true", help="Formata a saída estritamente em JSON")
    args = parser.parse_args()

    content = ""
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.text_opt:
        content = args.text_opt
    elif args.text:
        content = args.text
    else:
        import sys

        content = sys.stdin.read()

    predictor = ClinicalThemePredictor()

    if args.destrinchar:
        breakdown = predictor.destrinchar_diario(content)
        if args.json:
            print(json.dumps(breakdown.to_dict(), ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print("DECOMPOSIÇÃO DE DIÁRIO EM TÓPICOS (REDE NEURAL MLP)")
            print("=" * 60)
            print(f"Tema Preponderante Global: {breakdown.global_theme} ({breakdown.global_confidence * 100:.1f}%)")
            print(f"Resumo: {breakdown.summary}\n")
            print("Pesos Proporcionais por Tópico no Relato:")
            for t, w in sorted(breakdown.topic_weights.items(), key=lambda x: x[1], reverse=True):
                if w > 0:
                    print(f"  - {t:<22}: {w:5.1f}%")
            print("\nSegmentos e Evidências Literais (Grounding):")
            for i, seg in enumerate(breakdown.segments, 1):
                print(f"  [{i}] Tópico: {seg.theme} ({seg.confidence * 100:.1f}%) | Chars: {seg.start_char}-{seg.end_char}")
                print(f"      \"{seg.quote}\"")
    else:
        dist = predictor.predict_text(content)
        if args.json:
            print(json.dumps(dist.to_dict(), ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print("SEPARACAO TEMATICA DO DIARIO (PROBABILIDADES & PERCENTUAIS)")
            print("=" * 60)
            print(f"Tema Primario: {dist.primary_theme} ({dist.primary_percentage:.1f}%)")
            print(f"Confianca: {dist.confidence:.4f} | Fallback Salvaguarda: {dist.is_fallback}\n")
            print("Distribuicao de Percentuais entre Todos os Temas:")
            for item in dist.ranking:
                bar = "#" * int(item["percentual"] // 4)
                print(f"  - {item['tema']:<22}: {item['percentual']:6.2f}%  {bar}")


if __name__ == "__main__":
    main()
