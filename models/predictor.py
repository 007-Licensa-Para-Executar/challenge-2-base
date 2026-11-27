"""Inferência temática de textos clínicos e segmentação com trechos literais.

A distribuição softmax entre os 6 temas (autopercepcao, vinculos, desempenho,
fisico, rupturas, outros) atribui percentuais cuja soma é 100%. A fração de
caracteres analisados por tema em `destrinchar_diario` é uma medida separada
baseada no comprimento dos segmentos classificados.
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

from data.taxonomy import SAFEGUARD_CLASS
from models.embedder import ClinicalTextEmbedder
from models.sbert_embedder import SBERTEmbedder
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path("dist/best_theme_mlp.pt")
DEFAULT_EMBEDDER_PATH = Path("dist/theme_embedder.joblib")
DEFAULT_VECTORIZER_PATH = Path("dist/theme_embedder.joblib")
LEGACY_VECTORIZER_PATH = Path("dist/tfidf_vectorizer.joblib")


def _infer_score_semantics(model: ClinicalThemeMLP) -> str:
    temp_attr = getattr(model, "temperature", None)
    if temp_attr is not None:
        temp_val = float(temp_attr.detach().cpu().item())
        if abs(temp_val - 1.0) > 1e-4:
            return "temperature_scaled_softmax"
    return "uncalibrated_softmax"


def _infer_norm_type(state_dict: dict[str, torch.Tensor]) -> str:
    if "bn1.running_mean" in state_dict:
        return "batch_norm"
    if "bn1.scale" in state_dict:
        return "rms_norm"
    if "bn1.weight" in state_dict:
        return "layer_norm"
    return "batch_norm"


@dataclass
class TopicDistribution:
    """Distribuição de probabilidades e percentuais (0 a 100%) nos 6 temas."""

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
        vectorizer: TfidfVectorizer | ClinicalTextEmbedder | SBERTEmbedder | None = None,
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
                        f"Vetorizador/Embedder não encontrado em '{v_path}'. "
                        "Execute 'python -m models.train' para treinar a rede."
                    )
            else:
                if DEFAULT_EMBEDDER_PATH.exists():
                    v_path = DEFAULT_EMBEDDER_PATH
                elif LEGACY_VECTORIZER_PATH.exists():
                    v_path = LEGACY_VECTORIZER_PATH
                else:
                    raise FileNotFoundError(
                        f"Vetorizador/Embedder não encontrado em '{DEFAULT_EMBEDDER_PATH}'. "
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
                vocab_size = int(state_dict["embedding_bag.weight"].shape[0])
                input_dim = int(state_dict["embedding_bag.weight"].shape[1])
            elif "fc1.weight" in state_dict:
                input_dim = int(state_dict["fc1.weight"].shape[1])
            elif hasattr(self.vectorizer, "embedding_dim"):
                input_dim = int(self.vectorizer.embedding_dim)
            elif hasattr(self.vectorizer, "vocabulary_"):
                input_dim = len(self.vectorizer.vocabulary_)
            else:
                input_dim = 384

            hidden_dim1 = int(state_dict["fc1.weight"].shape[0]) if "fc1.weight" in state_dict else 128
            hidden_dim2 = int(state_dict["fc2.weight"].shape[0]) if "fc2.weight" in state_dict else 64
            num_classes = (
                int(state_dict["fc3.weight"].shape[0])
                if "fc3.weight" in state_dict
                else len(THEME_CLASSES)
            )
            norm_type = _infer_norm_type(state_dict)

            self.model = ClinicalThemeMLP(
                input_dim=input_dim,
                hidden_dim1=hidden_dim1,
                hidden_dim2=hidden_dim2,
                num_classes=num_classes,
                vocab_size=vocab_size,
                norm_type=norm_type,  # type: ignore[arg-type]
            )
            self.model.load_state_dict(state_dict, strict=True)
            self.model.to(self.device)

        self.model.eval()
        self.score_semantics = _infer_score_semantics(self.model)

    def _encode_texts(self, cleaned_texts: list[str]) -> np.ndarray:
        if isinstance(self.vectorizer, (ClinicalTextEmbedder, SBERTEmbedder)):
            features = self.vectorizer.transform(cleaned_texts, normalize=True)
        else:
            features = self.vectorizer.transform(cleaned_texts)
            if hasattr(features, "toarray"):
                features = features.toarray()
        return np.asarray(features, dtype=np.float32)

    def _encode_text(self, cleaned_text: str) -> np.ndarray:
        return self._encode_texts([cleaned_text])

    def _empty_distribution(self, reason: str) -> TopicDistribution:
        return TopicDistribution(
            primary_theme=SAFEGUARD_CLASS,
            confidence=0.0,
            primary_percentage=0.0,
            percentages={theme: 0.0 for theme in THEME_CLASSES},
            probabilities={theme: 0.0 for theme in THEME_CLASSES},
            ranking=[],
            top_topics=[],
            is_fallback=True,
            candidate_theme=None,
            abstention_reason=reason,
            score_semantics=self.score_semantics,
        )

    def _build_distribution(self, probs_np: np.ndarray, threshold: float) -> TopicDistribution:
        probabilities = {THEME_CLASSES[i]: float(probs_np[i]) for i in range(len(THEME_CLASSES))}
        percentages = {
            THEME_CLASSES[i]: round(float(probs_np[i]) * 100.0, 2)
            for i in range(len(THEME_CLASSES))
        }

        max_idx = int(np.argmax(probs_np))
        max_prob = float(probs_np[max_idx])
        predicted_theme = THEME_CLASSES[max_idx]

        is_fallback = max_prob < threshold
        if is_fallback:
            primary_theme = SAFEGUARD_CLASS
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
            score_semantics=self.score_semantics,
        )

    def predict_text(self, text: str, threshold: float = 0.50) -> TopicDistribution:
        """Classifica o diário entre os 6 temas e devolve percentuais (%).

        ``confidence`` é o maior score do candidato antes da abstenção.
        Quando ``confidence < threshold``, a decisão operacional recai em ``outros``.
        Entrada vazia não aciona a rede.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold deve estar entre 0 e 1")
        cleaned = text.strip() if isinstance(text, str) else ""
        if not cleaned or not re.search(r"[A-Za-zÀ-ÿ]", cleaned):
            reason = "empty_input" if not cleaned else "non_textual_input"
            return self._empty_distribution(reason)

        features = self._encode_text(cleaned)
        t_features = torch.tensor(features, dtype=torch.float32, device=self.device)

        with torch.no_grad():
            probs_np = self.model.predict_proba(t_features)[0].cpu().numpy()

        return self._build_distribution(probs_np, threshold=threshold)

    def predict_batch(self, texts: list[str], threshold: float = 0.50) -> list[TopicDistribution]:
        """Executa a inferência vetorizada em lote para uma lista de relatos."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold deve estar entre 0 e 1")
        if not texts:
            return []

        results: list[TopicDistribution | None] = [None] * len(texts)
        valid_indices: list[int] = []
        valid_texts: list[str] = []

        for idx, text in enumerate(texts):
            cleaned = text.strip() if isinstance(text, str) else ""
            if not cleaned or not re.search(r"[A-Za-zÀ-ÿ]", cleaned):
                reason = "empty_input" if not cleaned else "non_textual_input"
                results[idx] = self._empty_distribution(reason)
            else:
                valid_indices.append(idx)
                valid_texts.append(cleaned)

        if valid_texts:
            features = self._encode_texts(valid_texts)
            t_features = torch.tensor(features, dtype=torch.float32, device=self.device)
            with torch.no_grad():
                probs_batch = self.model.predict_proba(t_features).cpu().numpy()
            for idx, probs_np in zip(valid_indices, probs_batch, strict=True):
                results[idx] = self._build_distribution(probs_np, threshold=threshold)

        return [r for r in results if r is not None]

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
                global_theme=SAFEGUARD_CLASS,
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
                theme_score_semantics=self.score_semantics,
            )

        sentence_pattern = re.compile(r"[^.!?\n]+(?:[.!?\n]+|$)")
        segments: list[DiaryTopicSegment] = []
        topic_char_counts: dict[str, int] = {theme: 0 for theme in THEME_CLASSES}
        total_analyzed_chars = 0

        for match in sentence_pattern.finditer(full_text):
            raw_quote = match.group()
            stripped_quote = raw_quote.strip()
            if len(stripped_quote) < min_segment_chars:
                continue

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
                score_semantics=self.score_semantics,
            )
            segments.append(segment)

            seg_len = len(stripped_quote)
            topic_char_counts[seg_theme] = topic_char_counts.get(seg_theme, 0) + seg_len
            total_analyzed_chars += seg_len

        if total_analyzed_chars > 0:
            topic_weights = {
                theme: round((topic_char_counts.get(theme, 0) / total_analyzed_chars) * 100.0, 2)
                for theme in THEME_CLASSES
            }
        else:
            topic_weights = {theme: 0.0 for theme in THEME_CLASSES}

        detected = [
            theme
            for theme, weight in sorted(
                topic_weights.items(), key=lambda item: item[1], reverse=True
            )
            if weight > 0.0
        ]

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
            "Fração dos caracteres analisados por tema: " + ", ".join(summary_parts)
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
            theme_score_semantics=self.score_semantics,
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
    cal_label = (
        "calibrado (temperature scaling)"
        if predictor.score_semantics == "temperature_scaled_softmax"
        else "não calibrado"
    )

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
                f"score softmax {cal_label}: {breakdown.global_confidence:.4f}; "
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
            print(f"CLASSIFICACAO TEMATICA (SOFTMAX {cal_label.upper()})")
            print("=" * 60)
            print(f"Resultado da política: {dist.primary_theme}")
            print(
                f"Candidato: {dist.candidate_theme} | Score softmax {cal_label}: "
                f"{dist.confidence:.4f} | Abstenção: {dist.abstention_reason}\n"
            )
            print("Ranking de percentuais por tema:")
            for item in dist.ranking:
                bar = "#" * int(item["percentual"] // 4)
                print(f"  - {item['tema']:<22}: {item['percentual']:6.2f}%  {bar}")


if __name__ == "__main__":
    main()
