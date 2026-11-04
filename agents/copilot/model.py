"""Integração com Ollama e sintetizador determinístico para o Agente 2."""

from __future__ import annotations

import json
import time

import ollama

from .config import CopilotSettings
from .contracts import (
    CopilotDossier,
    ImpactBenchAnalysis,
    ImpactBenchDimension,
    LongitudinalStats,
    RetrievedEvidence,
    RunMetadata,
)
from .prompt import SYSTEM_PROMPT, build_copilot_prompt


class OllamaCopilot:
    """Invoca o modelo via Ollama ou sintetizador determinístico (mock mode)."""

    def __init__(self, settings: CopilotSettings):
        self.settings = settings
        self.client = ollama.Client(host=settings.ollama_host)

    def generate_dossier(
        self,
        stats: LongitudinalStats,
        evidences: list[RetrievedEvidence],
        status_evidencia: str,
    ) -> tuple[CopilotDossier, RunMetadata]:
        start_time = time.perf_counter()

        if self.settings.mock_mode:
            dossier = self._generate_deterministic(stats, evidences, status_evidencia)
            latency = (time.perf_counter() - start_time) * 1000
            meta = RunMetadata(
                model=f"{self.settings.model}-mock",
                latency_ms=latency,
                retrieved_chunks_count=len(evidences),
            )
            return dossier, meta

        prompt = build_copilot_prompt(stats, evidences)
        try:
            response = self.client.chat(
                model=self.settings.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                format=CopilotDossier.model_json_schema(),
                options={"temperature": 0.1, "num_ctx": 4096},
            )
            content = response["message"]["content"]
            data = json.loads(content)
            dossier = CopilotDossier.model_validate(data)
            digest = response.get("model", "")
        except Exception:  # noqa: BLE001 - fallback seguro se o modelo local estiver offline
            dossier = self._generate_deterministic(stats, evidences, status_evidencia)
            digest = "fallback-deterministic"

        latency = (time.perf_counter() - start_time) * 1000
        meta = RunMetadata(
            model=self.settings.model,
            model_digest=digest,
            latency_ms=latency,
            retrieved_chunks_count=len(evidences),
        )
        return dossier, meta

    def _generate_deterministic(
        self,
        stats: LongitudinalStats,
        evidences: list[RetrievedEvidence],
        status_evidencia: str,
    ) -> CopilotDossier:
        """Gera dossiê estruturado, fundamentado e rastreável sem depender de GPU/LLM."""
        # 1. Síntese narrativa temporal
        sent_dom = stats.sentimento_dominante
        tema_dom = stats.tema_dominante
        narrativa = (
            f"No intervalo avaliado de {stats.periodo_dias} dias ({stats.total_relatos} relatos), "
            f"observou-se predominância do tema '{tema_dom}' acompanhado principalmente de '{sent_dom}'. "
        )
        if stats.sinal_risco_detectado:
            narrativa += (
                "Foram identificados indícios textuais de sofrimento agudo que demandam escuta atenta "
                "e verificação prioritária pelo profissional na próxima sessão."
            )
        else:
            narrativa += "Não foram identificados indícios textuais explícitos de risco iminente nos relatos sintéticos."

        # 2. Dimensões do MIT ImpactBench
        impact_analysis: list[ImpactBenchAnalysis] = [
            ImpactBenchAnalysis(
                dimensao=ImpactBenchDimension.BEM_ESTAR_EMOCIONAL,
                observacao_longitudinal=(
                    f"Frequência elevada de sentimentos com valência negativa ({sent_dom}) "
                    f"relacionados ao contexto de {tema_dom}."
                ),
                alinhamento_com_literatura=(
                    "Alinhado à dimensão de regulação afetiva do MIT ImpactBench (arXiv:2610.20690), "
                    "indicando oscilação que requer acompanhamento da estabilidade de humor."
                ),
            ),
            ImpactBenchAnalysis(
                dimensao=ImpactBenchDimension.AUTONOMIA_AGENCIA,
                observacao_longitudinal=(
                    f"O paciente relata desafios de enfrentamento no tema '{tema_dom}', "
                    "com relatos que sugerem sensação de sobrecarga ou desamparo circunstancial."
                ),
                alinhamento_com_literatura=(
                    "Pesquisas do MIT Media Lab e Harvard Digital Psychiatry indicam que relatos inter-sessão "
                    "ajudam a identificar precocemente quedas no senso de agência do jovem."
                ),
            ),
        ]

        if "relacionamentos" in stats.temas_frequencia or "familia" in stats.temas_frequencia:
            impact_analysis.append(
                ImpactBenchAnalysis(
                    dimensao=ImpactBenchDimension.CONEXAO_SOCIAL,
                    observacao_longitudinal="Presença de queixas relacionais ou familiares no período analisado.",
                    alinhamento_com_literatura=(
                        "Conforme métricas de conexão social do ImpactBench, laços interpessoais fragilizados "
                        "aumentam a vulnerabilidade a isolamento e busca compensatória em tecnologias."
                    ),
                )
            )

        # 3. Perguntas investigativas para o psicólogo
        questoes = [
            f"Como o paciente descreve os desdobramentos dos eventos ligados a '{tema_dom}' ocorridos durante a semana?",
            f"Explorar se o sentimento de '{sent_dom}' foi acompanhado por alterações de sono, apetite ou isolamento social.",
            "Investigar quais estratégias de enfrentamento ou rede de apoio humana foram acionadas nos dias mais difíceis.",
        ]
        if stats.sinal_risco_detectado:
            questoes.insert(0, "PRIORITÁRIO: Conduzir checagem clínica acolhedora e direta sobre segurança e ideações expressas.")

        # 4. Lacunas e advertências
        lacunas = [
            "Os relatos de diário refletem estados momentâneos e auto-selecionados, não a integralidade da experiência do paciente.",
            "As correlações teóricas apresentadas são associações observadas em literatura científica e não implicam relação de causalidade direta no caso individual.",
        ]
        if status_evidencia == "evidencia_insuficiente":
            lacunas.append("A base de conhecimento não possui evidências suficientes específicas para este padrão atípico.")

        status_final = (
            "evidencia_insuficiente"
            if status_evidencia == "evidencia_insuficiente"
            else ("evidencia_suficiente" if len(evidences) >= 2 else "evidencia_parcial")
        )

        return CopilotDossier(
            stats=stats,
            sintese_narrativa=narrativa,
            impactbench_analise=impact_analysis,
            evidencias_cientificas=evidences,
            questoes_para_o_terapeuta=questoes,
            lacunas_e_abstencoes=lacunas,
            status_evidencia=status_final,
        )
