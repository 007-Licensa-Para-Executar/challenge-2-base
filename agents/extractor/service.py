"""Serviço do Agente 1: Decompositor Temático e Extrator de Evidências Literais.

Integração entre a classificação macrotemática da Rede Neural MLP e a extração
estruturada de subtemas clínicos via Ollama local (Structured Outputs).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from models.torch_mlp import THEME_CLASSES

from .config import Settings
from .contracts import (
    Agent1LLMExtraction,
    Agent1Output,
    EvidenceSpan,
    MacroTema,
    SubTemaItem,
)
from .prompt import AGENT1_SYSTEM_PROMPT, build_user_prompt
from .sentiment import analyze_polarity, validate_polarity
from .wheel import (
    LongitudinalComparison,
    MacrotopicNode,
    SubtopicNode,
    SubtopicWheelTracker,
    SunburstWheelData,
)

logger = logging.getLogger(__name__)


class Agent1Service:
    """Decompositor temático clínico e extrator de evidências literais (Agente 1)."""

    def __init__(
        self,
        ollama_url: str | None = None,
        model_name: str | None = None,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.ollama_url = (ollama_url or self.settings.host).rstrip("/")
        self.model_name = model_name or self.settings.model
        self.client = (
            client
            if client is not None
            else httpx.Client(
                trust_env=False,
                follow_redirects=False,
                timeout=self.settings.timeout_seconds,
            )
        )

    def process(
        self,
        patient_id: str,
        text: str,
        macro_tema: str,
        confidence: float,
        modalidade: str = "texto",
        audio_segments: list[dict[str, Any]] | None = None,
    ) -> Agent1Output:
        """Decompõe o relato do paciente em subtemas e evidências literais exatas.

        Args:
            patient_id: Identificador anônimo do paciente (ex: 'PAC-101').
            text: Texto integral do relato ou transcrição de áudio.
            macro_tema: Macrotema predito pela Rede Neural (ex: 'familia').
            confidence: Confiança ou probabilidade predita pela rede (0.0 a 1.0).
            modalidade: Modalidade da entrada ('texto', 'audio' ou 'foto').
            audio_segments: Segmentos com carimbos de áudio [{'start': s, 'end': s, 'text': str}].

        Returns:
            Agent1Output com subtemas validados e spans literais alinhados.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Texto do relato não pode ser vazio.")

        user_prompt = build_user_prompt(
            texto_relato=text,
            macrotema_nn=macro_tema,
            confianca_nn=confidence,
            audio_segments=audio_segments,
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": AGENT1_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "format": Agent1LLMExtraction.model_json_schema(),
            "options": {"temperature": 0.0, "seed": 42},
            "stream": False,
        }

        response = self.client.post(f"{self.ollama_url}/api/chat", json=payload)
        response.raise_for_status()

        resp_json = response.json()
        raw_content = resp_json.get("message", {}).get("content", "")
        if not raw_content or not isinstance(raw_content, str):
            raise ValueError("Ollama retornou resposta vazia para o Agente 1.")

        data = json.loads(raw_content)

        # Injeta metadados de controle e rastreabilidade
        data["patient_id"] = patient_id
        data["modalidade"] = modalidade
        data["macro_tema_validado"] = macro_tema
        data["confianca_macro_tema"] = float(confidence)

        # Validação cruzada determinística de polaridade léxica (VADER PT)
        try:
            pol = analyze_polarity(text)
            sentimento_str = str(data.get("sentimento_predominante", "nao_identificado"))
            val_metrics = validate_polarity(sentimento_str, pol)
            data["validation"] = val_metrics
        except Exception as exc:
            logger.debug("Validação de polaridade omitida: %s", exc)

        output = Agent1Output.model_validate(data)

        # Valida e alinha os spans literais para garantir zero alucinação
        self._validate_and_align_spans(text, output.subtemas, audio_segments=audio_segments)

        return output

    def process_with_neural_network(
        self,
        patient_id: str,
        text: str,
        predictor: Any | None = None,
        modalidade: str = "texto",
        audio_segments: list[dict[str, Any]] | None = None,
    ) -> Agent1Output:
        """Executa o pipeline completo: Rede Neural MLP (tema) + Agente 1 (subtemas)."""
        if predictor is None:
            from models.predictor import ClinicalThemePredictor

            predictor = ClinicalThemePredictor()

        res = predictor.predict_text(text)
        return self.process(
            patient_id=patient_id,
            text=text,
            macro_tema=res.primary_theme,
            confidence=res.confidence,
            modalidade=modalidade,
            audio_segments=audio_segments,
        )

    def build_wheel_data(
        self,
        entries: list[Agent1Output],
        patient_id: str = "PACIENTE",
        periodo: str = "Semana Atual",
        max_subtemas: int = 24,
    ) -> SunburstWheelData:
        """Gera a estrutura hierárquica da Roda de Bem-Estar (Sunburst Chart).

        - Anel Interno: 8 Macrotemas da Rede Neural
        - Anel Externo: Até 24 Subtemas ativos ponderados pela fala do paciente
        """
        tracker = SubtopicWheelTracker(max_total_subtemas=max_subtemas)
        return tracker.build_wheel(entries, patient_id=patient_id, periodo=periodo)

    def compare_history(
        self,
        current_entries: list[Agent1Output],
        previous_entries: list[Agent1Output],
        patient_id: str = "PACIENTE",
        current_label: str = "Semana Atual",
        previous_label: str = "Semana Anterior",
        max_subtemas: int = 24,
    ) -> LongitudinalComparison:
        """Compara o histórico longitudinal (semanal ou mensal) do paciente,

        rastreando subtemas persistentes, novos tópicos emergentes e tópicos rotacionados.
        """
        tracker = SubtopicWheelTracker(max_total_subtemas=max_subtemas)
        return tracker.compare_periods(
            current_entries=current_entries,
            previous_entries=previous_entries,
            patient_id=patient_id,
            current_label=current_label,
            previous_label=previous_label,
        )

    def _validate_and_align_spans(
        self,
        full_text: str,
        subtemas: list[SubTemaItem],
        audio_segments: list[dict[str, Any]] | None = None,
    ) -> None:
        """Garante que todas as citações literais existam exatamente no texto primário

        e ajusta os índices de caractere (start_char e end_char) de forma determinística.
        Também alinha carimbos de tempo de áudio caso disponíveis.
        """
        for sub in subtemas:
            for ev in sub.evidencias:
                quote = ev.quote_text

                # 1. Teste exato nos índices já informados
                if (
                    0 <= ev.start_char < len(full_text)
                    and 0 < ev.end_char <= len(full_text)
                    and full_text[ev.start_char : ev.end_char] == quote
                ):
                    pass
                # 2. Busca exata de substring em qualquer ponto do relato
                elif quote in full_text:
                    idx = full_text.find(quote)
                    ev.start_char = idx
                    ev.end_char = idx + len(quote)
                else:
                    # 3. Limpeza de aspas externas ou espaços
                    cleaned = quote.strip().strip('"\'')
                    if cleaned and cleaned in full_text:
                        idx = full_text.find(cleaned)
                        ev.quote_text = cleaned
                        ev.start_char = idx
                        ev.end_char = idx + len(cleaned)
                    else:
                        # 4. Busca insensível a maiúsculas/minúsculas
                        idx = full_text.lower().find(quote.lower().strip())
                        if idx != -1:
                            matched = full_text[idx : idx + len(quote.strip())]
                            ev.quote_text = matched
                            ev.start_char = idx
                            ev.end_char = idx + len(matched)
                        else:
                            raise ValueError(
                                f"Citação literal '{quote}' não foi localizada no texto primário."
                            )

                # 5. Mapeamento de carimbos de áudio com base nos segmentos disponíveis
                if audio_segments and (ev.audio_start_sec is None or ev.audio_end_sec is None):
                    self._align_audio_timestamps(ev, audio_segments)

    @staticmethod
    def _align_audio_timestamps(
        ev: EvidenceSpan,
        audio_segments: list[dict[str, Any]],
    ) -> None:
        """Associa a citação literal ao segmento de áudio correspondente."""
        quote_lower = ev.quote_text.lower()
        best_seg = None
        best_overlap = 0

        for seg in audio_segments:
            seg_text = seg.get("text", "").lower()
            if not seg_text:
                continue

            # Verificação de contenção direta
            if quote_lower in seg_text or seg_text in quote_lower:
                best_seg = seg
                break

            # Verificação de sobreposição de palavras
            quote_words = set(quote_lower.split())
            seg_words = set(seg_text.split())
            overlap = len(quote_words & seg_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_seg = seg

        if best_seg:
            ev.audio_start_sec = round(float(best_seg.get("start", 0.0)), 2)
            ev.audio_end_sec = round(float(best_seg.get("end", 0.0)), 2)

    @staticmethod
    def to_clinical_summary(output: Agent1Output) -> str:
        """Gera resumo estruturado em Markdown pronto para auditoria do psicólogo."""
        lines = [
            f"### Relatório Clínico do Agente 1 — Paciente `{output.patient_id}`",
            f"- **Entrada ID:** `{output.entry_id}`",
            f"- **Macrotema Validado:** `{output.macro_tema_validado.value}` (Confiança da Rede: {output.confianca_macro_tema * 100:.1f}%)",
            f"- **Sentimento Predominante:** `{output.sentimento_predominante.value}` (Polaridade: {output.score_polaridade:+.2f})",
            f"- **Sinalizador de Risco:** `{output.indicio_textual_risco.value}`",
        ]

        if output.indicio_textual_risco.value == "presente":
            lines.append(
                "> [!WARNING] **ALERTA CLÍNICO PRIORITÁRIO**: Detectado indício textual de autolesão ou ideação crítica."
            )

        lines.append("\n#### Subtemas e Evidências Literais Identificadas:")
        for idx, sub in enumerate(output.subtemas, 1):
            lines.append(f"**{idx}. {sub.nome}**")
            lines.append(f"   *Contextualização:* {sub.descricao}")
            for ev in sub.evidencias:
                audio_str = (
                    f" | Áudio: [{ev.audio_start_sec:.1f}s - {ev.audio_end_sec:.1f}s]"
                    if ev.audio_start_sec is not None
                    else ""
                )
                lines.append(
                    f'   *Evidência Literal:* "{ev.quote_text}" (chars {ev.start_char}-{ev.end_char}{audio_str})'
                )

        return "\n".join(lines)
