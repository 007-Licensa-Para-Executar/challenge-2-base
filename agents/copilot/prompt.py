"""Prompts e instruções restritivas para o Agente 2 (Copiloto com RAG)."""

from __future__ import annotations

import json

from .contracts import LongitudinalStats, RetrievedEvidence

SYSTEM_PROMPT = """Você é o Agente 2 do Projeto 007, um copiloto de inteligência e síntese de evidências científicas para psicólogos e terapeutas.
A proposta é apoiar a preparação da consulta clínica, analisando relatos semanais estruturados de jovens (12-25 anos).

DIRETRIZES DE SEGURANÇA E EPISTEMOLOGIA CLÍNICA:
1. RASTREABILIDADE TOTAL: Toda correlação teórica DEVE citar explicitamente os chunks recuperados ([chunk_id]).
2. DISTINÇÃO CATEGÓRICA OBRIGATÓRIA:
   - "Fatos Observados": Frequências e menções textuais dos relatos semanais.
   - "Evidência Científica": O que os estudos de referência (MIT, Harvard, USP, CFP) observaram.
   - "Hipóteses Exploratórias": Perguntas para o psicólogo humano investigar na sessão.
3. CAUSALIDADE vs. ASSOCIAÇÃO: Jamais afirme que um evento ou uso de IA causou um sintoma; use 'associação observada'.
4. NÃO DIAGNOSTIQUE: Jamais atribua transtornos psiquiátricos (ex: Depressão Maior, TAG) ou prescreva tratamentos.
5. ABSTENÇÃO: Se as evidências científicas fornecidas não cobrirem o tema, informe explicitamente nas lacunas.
6. ALINHAMENTO COM MIT IMPACTBENCH: Relacione os padrões às dimensões de Bem-Estar Emocional, Autonomia/Agência, Conexão Social e Pensamento Crítico."""


def build_copilot_prompt(stats: LongitudinalStats, evidences: list[RetrievedEvidence]) -> str:
    """Monta o prompt de entrada para o LLM com os dados longitudinais e os chunks recuperados."""
    evidence_blocks = []
    for idx, ev in enumerate(evidences, 1):
        evidence_blocks.append(
            f"--- CHUNK [{ev.chunk_id}] ---\n"
            f"Título: {ev.title} ({ev.institution}, {ev.year})\n"
            f"Nível: {ev.evidence_tier.value}\n"
            f"DOI/URL: {ev.doi_or_url}\n"
            f"Trecho: {ev.claim_ou_trecho}\n"
            f"Limitações: {ev.limitacoes}\n"
        )

    evidences_text = "\n".join(evidence_blocks) if evidence_blocks else "Nenhuma evidência relevante recuperada."

    stats_dict = {
        "periodo_dias": stats.periodo_dias,
        "total_relatos": stats.total_relatos,
        "temas_frequencia": stats.temas_frequencia,
        "sentimentos_frequencia": stats.sentimentos_frequencia,
        "indicios_risco_frequencia": stats.indicios_risco_frequencia,
        "tema_dominante": stats.tema_dominante,
        "sentimento_dominante": stats.sentimento_dominante,
        "sinal_risco_detectado": stats.sinal_risco_detectado,
    }

    return (
        f"DADOS LONGITUDINAIS DO PACIENTE (Últimos {stats.periodo_dias} dias):\n"
        f"{json.dumps(stats_dict, ensure_ascii=False, indent=2)}\n\n"
        f"EVIDÊNCIAS CIENTÍFICAS RECUPERADAS DA BASE DE CONHECIMENTO:\n"
        f"{evidences_text}\n\n"
        f"Gere um dossiê analítico para o psicólogo, com síntese narrativa temporal, análise nas dimensões "
        f"do MIT ImpactBench, perguntas clínicas investigativas e limitações das evidências."
    )
