"""Inferência temática de textos sintéticos e segmentação com trechos literais.

Os scores softmax são não calibrados. A fração de caracteres analisados por tema
é uma medida separada e não representa intensidade ou relevância clínica.
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
import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

from models.embedder import ClinicalTextEmbedder
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path("dist/best_theme_mlp.pt")
DEFAULT_EMBEDDER_PATH = Path("dist/theme_embedder.joblib")
DEFAULT_VECTORIZER_PATH = Path("dist/theme_embedder.joblib")
LEGACY_VECTORIZER_PATH = Path("dist/tfidf_vectorizer.joblib")


@dataclass
class TopicDistribution:
    """Scores softmax não calibrados; campos percentuais são scores vezes 100."""

    primary_theme: str
    confidence: float
    primary_percentage: float
    percentages: dict[str, float]
    probabilities: dict[str, float]
    ranking: list[dict[str, Any]]
    top_topics: list[dict[str, Any]]
    is_fallback: bool
    candidate_theme: str | None
    abstention_reason: str | None
    score_semantics: str = "uncalibrated_softmax"

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
    candidate_theme: str | None
    is_fallback: bool
    abstention_reason: str | None
    score_semantics: str = "uncalibrated_softmax"

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
    total_chars: int
    analyzed_chars: int
    omitted_chars: int
    coverage_ratio: float
    global_candidate_theme: str | None
    global_abstention_reason: str | None
    weight_basis: str = "analyzed_characters"
    theme_score_semantics: str = "uncalibrated_softmax"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClinicalThemePredictor:
    """Inferenciador e decompositor temático baseado na rede neural treinada."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        vectorizer_path: str | Path | None = None,
        model: ClinicalThemeMLP | None = None,
        vectorizer: TfidfVectorizer | ClinicalTextEmbedder | None = None,
        device: str = "cpu",
    ) -> None:
        self.device = torch.device(device)

        if vectorizer is not None:
            self.vectorizer = vectorizer
        else:
            if vectorizer_path is not None:
                v_path = Path(vectorizer_path)
                if not v_path.exists():
                    raise FileNotFoundError(
                        f"Vetorizador/Embedder TF-IDF não encontrado em '{v_path}'. "
                        "Execute 'python -m models.train' para treinar a rede."
                    )
            else:
                if DEFAULT_EMBEDDER_PATH.exists():
                    v_path = DEFAULT_EMBEDDER_PATH
                elif LEGACY_VECTORIZER_PATH.exists():
                    v_path = LEGACY_VECTORIZER_PATH
                else:
                    raise FileNotFoundError(
                        f"Vetorizador/Embedder TF-IDF não encontrado em '{DEFAULT_EMBEDDER_PATH}'. "
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
            state_dict = torch.load(m_path, map_location=self.device, weights_only=True)
            vocab_size = None
            if "embedding_bag.weight" in state_dict:
                vocab_size = state_dict["embedding_bag.weight"].shape[0]
                input_dim = state_dict["embedding_bag.weight"].shape[1]
            elif hasattr(self.vectorizer, "embedding_dim"):
                input_dim = self.vectorizer.embedding_dim
                vocab_size = len(self.vectorizer.vocab)
            elif hasattr(self.vectorizer, "vocabulary_"):
                input_dim = len(self.vectorizer.vocabulary_)
            else:
                input_dim = 128
            self.model = ClinicalThemeMLP(
                input_dim=input_dim,
                num_classes=len(THEME_CLASSES),
                vocab_size=vocab_size,
            )
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)

        self.model.eval()

    def predict_text(self, text: str, threshold: float = 0.50) -> TopicDistribution:
        """Classifica um tema; não estima participação dos temas no texto.

        ``confidence`` é o maior score do candidato antes da abstenção. Os campos
        ``probabilities``/``percentages`` são mantidos por compatibilidade e não
        comprovam calibração. Entrada vazia não aciona a rede.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold deve estar entre 0 e 1")
        cleaned = text.strip() if isinstance(text, str) else ""
        if not cleaned:
            return TopicDistribution(
                primary_theme="outros_indeterminado",
                confidence=0.0,
                primary_percentage=0.0,
                percentages={theme: 0.0 for theme in THEME_CLASSES},
                probabilities={theme: 0.0 for theme in THEME_CLASSES},
                ranking=[],
                top_topics=[],
                is_fallback=True,
                candidate_theme=None,
                abstention_reason="empty_input",
            )

        features = self.vectorizer.transform([cleaned])
        if hasattr(features, "toarray"):
            features = features.toarray()
        features = np.asarray(features, dtype=np.float32)
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
                {
                    "tema": theme,
                    "percentual": percentages[theme],
                    "probabilidade": probabilities[theme],
                }
                for theme in THEME_CLASSES
            ],
            key=lambda item: item["percentual"],
            reverse=True,
        )

        # Uma rede exclusiva não prova presença simultânea das outras categorias.
        top_topics = [ranking[0]] if not is_fallback else []

        return TopicDistribution(
            primary_theme=primary_theme,
            confidence=round(confidence, 4),
            primary_percentage=primary_pct,
            percentages=percentages,
            probabilities={t: round(p, 4) for t, p in probabilities.items()},
            ranking=ranking,
            top_topics=top_topics,
            is_fallback=is_fallback,
            candidate_theme=predicted_theme,
            abstention_reason="below_threshold" if is_fallback else None,
        )

    def predict_batch(self, texts: list[str], threshold: float = 0.50) -> list[TopicDistribution]:
        """Executa a inferência vetorizada para um lote de relatos."""
        return [self.predict_text(text, threshold=threshold) for text in texts]

    def destrinchar_diario(
        self,
        text: str,
        threshold: float = 0.50,
        segment_threshold: float = 0.50,
        min_segment_chars: int = 15,
    ) -> DiaryTopicBreakdown:
        """Classifica sentenças e calcula sua fração dos caracteres analisados.

        Segmentos curtos e espaços externos são omitidos da contagem. A cobertura
        explicita essa omissão. Um mesmo segmento recebe somente um tema.
        """
        if min_segment_chars < 1:
            raise ValueError("min_segment_chars deve ser positivo")
        if not 0.0 <= segment_threshold <= 1.0:
            raise ValueError("segment_threshold deve estar entre 0 e 1")
        full_text = text if isinstance(text, str) else ""
        global_dist = self.predict_text(full_text, threshold=threshold)

        if not full_text.strip():
            return DiaryTopicBreakdown(
                text=full_text,
                global_theme="outros_indeterminado",
                global_confidence=0.0,
                theme_percentages=global_dist.percentages,
                topic_weights={t: 0.0 for t in THEME_CLASSES},
                segments=[],
                detected_topics=[],
                summary="Relato vazio ou sem conteúdo analisável.",
                total_chars=len(full_text),
                analyzed_chars=0,
                omitted_chars=len(full_text),
                coverage_ratio=0.0,
                global_candidate_theme=global_dist.candidate_theme,
                global_abstention_reason=global_dist.abstention_reason,
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
                candidate_theme=seg_dist.candidate_theme,
                is_fallback=seg_dist.is_fallback,
                abstention_reason=seg_dist.abstention_reason,
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
            # Sem segmento analisado, não há proporção textual para estimar.
            topic_weights = {theme: 0.0 for theme in THEME_CLASSES}

        # Tópicos detectados com proporção relevante no relato (> 0%)
        detected = [
            theme
            for theme, weight in sorted(
                topic_weights.items(), key=lambda item: item[1], reverse=True
            )
            if weight > 0.0
        ]

        # Resumo descritivo da contagem
        summary_parts = [
            f"{theme}: {weight:.1f}%"
            for theme, weight in sorted(
                topic_weights.items(), key=lambda item: item[1], reverse=True
            )
            if weight > 0.0
        ]
        resumo = (
            f"Tema preponderante global: {global_dist.primary_theme} "
            f"(score máximo do candidato: {global_dist.confidence:.4f}). "
            f"Fração dos caracteres analisados por tema: " + ", ".join(summary_parts)
            if summary_parts
            else "Nenhum segmento atingiu o comprimento mínimo; pesos textuais indisponíveis."
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
            total_chars=len(full_text),
            analyzed_chars=total_analyzed_chars,
            omitted_chars=len(full_text) - total_analyzed_chars,
            coverage_ratio=total_analyzed_chars / len(full_text),
            global_candidate_theme=global_dist.candidate_theme,
            global_abstention_reason=global_dist.abstention_reason,
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
            print(f"Resultado global da política: {breakdown.global_theme}")
            print(
                f"Candidato global: {breakdown.global_candidate_theme}; "
                f"score softmax não calibrado: {breakdown.global_confidence:.4f}; "
                f"abstenção: {breakdown.global_abstention_reason}"
            )
            print(f"Resumo: {breakdown.summary}\n")
            print("Fração dos caracteres analisados por tema:")
            for t, w in sorted(breakdown.topic_weights.items(), key=lambda x: x[1], reverse=True):
                if w > 0:
                    print(f"  - {t:<22}: {w:5.1f}%")
            print("\nSegmentos e Evidências Literais (Grounding):")
            for i, seg in enumerate(breakdown.segments, 1):
                print(
                    f"  [{i}] Resultado: {seg.theme} | Candidato: {seg.candidate_theme} | "
                    f"Score do candidato: {seg.confidence:.4f} | "
                    f"Abstenção: {seg.abstention_reason} | Chars: {seg.start_char}-{seg.end_char}"
                )
                print(f'      "{seg.quote}"')
    else:
        dist = predictor.predict_text(content)
        if args.json:
            print(json.dumps(dist.to_dict(), ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print("CLASSIFICACAO TEMATICA (SCORES SOFTMAX NAO CALIBRADOS)")
            print("=" * 60)
            print(f"Resultado da política: {dist.primary_theme}")
            print(
                f"Candidato: {dist.candidate_theme} | Score softmax não calibrado: "
                f"{dist.confidence:.4f} | Abstenção: {dist.abstention_reason}\n"
            )
            print("Ranking de scores por categoria (não é composição textual):")
            for item in dist.ranking:
                bar = "#" * int(item["percentual"] // 4)
                print(f"  - {item['tema']:<22}: {item['percentual']:6.2f}%  {bar}")


if __name__ == "__main__":
    main()
