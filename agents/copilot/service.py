"""Serviço central de agregação e geração do Agente 2 (Copiloto com RAG)."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import CopilotSettings
from .contracts import (
    CopilotDossier,
    ErrorInfo,
    LongitudinalStats,
    ProcessingResult,
    RunMetadata,
)
from .model import OllamaCopilot
from .retriever import HybridRetriever


class CopilotService:
    """Orquestra a leitura de extrações (Agente 1), RAG e síntese clínica (Agente 2)."""

    def __init__(self, settings: CopilotSettings | None = None):
        self.settings = settings or CopilotSettings.from_env()
        self.retriever = HybridRetriever(
            corpus_path=self.settings.corpus_path,
            abstention_threshold=self.settings.abstention_threshold,
        )
        self.copilot_model = OllamaCopilot(self.settings)

    def load_extractions_from_db(
        self,
        db_path: str | Path | None = None,
        days_window: int = 7,
    ) -> list[dict[str, Any]]:
        """Lê os resultados produzidos pelo Agente 1 no banco SQLite."""
        target_db = Path(db_path or self.settings.db_path).expanduser()
        if not target_db.exists():
            return []

        extractions: list[dict[str, Any]] = []
        with sqlite3.connect(target_db) as conn:
            # Verifica existência da tabela runs criada pelo Agente 1
            has_table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
            ).fetchone()
            if not has_table:
                return []

            cursor = conn.execute(
                "SELECT created_at, input_text, result_json FROM runs WHERE status = 'ok' ORDER BY created_at ASC"
            )
            for row in cursor.fetchall():
                created_at_str, input_text, result_json_str = row
                try:
                    res_data = json.loads(result_json_str)
                    ext = res_data.get("extraction")
                    if ext:
                        extractions.append({
                            "created_at": created_at_str,
                            "input_text": input_text,
                            "tema": ext.get("tema", "outros"),
                            "sentimento": ext.get("sentimento", "nao_identificado"),
                            "indicio_textual_risco": ext.get("indicio_textual_risco", "nao_identificado"),
                        })
                except (json.JSONDecodeError, KeyError):
                    continue

        # Filtragem por janela temporal se houver data válida
        if days_window > 0 and extractions:
            cutoff = datetime.now(UTC) - timedelta(days=days_window)
            filtered = []
            for item in extractions:
                try:
                    dt = datetime.fromisoformat(item["created_at"])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    if dt >= cutoff:
                        filtered.append(item)
                except (ValueError, TypeError):
                    filtered.append(item)
            return filtered if filtered else extractions

        return extractions

    def compute_stats(self, extractions: list[dict[str, Any]], days_window: int = 7) -> LongitudinalStats:
        """Calcula métricas agregadas da série temporal de relatos."""
        if not extractions:
            return LongitudinalStats(
                periodo_dias=days_window,
                total_relatos=0,
                temas_frequencia={},
                sentimentos_frequencia={},
                indicios_risco_frequencia={},
                tema_dominante="nao_identificado",
                sentimento_dominante="nao_identificado",
                sinal_risco_detectado=False,
            )

        temas = [item["tema"] for item in extractions]
        sentimentos = [item["sentimento"] for item in extractions]
        riscos = [item["indicio_textual_risco"] for item in extractions]

        temas_count = Counter(temas)
        sentimentos_count = Counter(sentimentos)
        riscos_count = Counter(riscos)

        tema_dom = temas_count.most_common(1)[0][0] if temas_count else "outros"
        sent_dom = sentimentos_count.most_common(1)[0][0] if sentimentos_count else "nao_identificado"
        has_risk = any(r == "presente" for r in riscos)

        return LongitudinalStats(
            periodo_dias=days_window,
            total_relatos=len(extractions),
            temas_frequencia=dict(temas_count),
            sentimentos_frequencia=dict(sentimentos_count),
            indicios_risco_frequencia=dict(riscos_count),
            tema_dominante=tema_dom,
            sentimento_dominante=sent_dom,
            sinal_risco_detectado=has_risk,
        )

    def analyze(
        self,
        extractions: list[dict[str, Any]],
        days_window: int = 7,
    ) -> ProcessingResult:
        """Executa a recuperação RAG e a síntese clínica do Agente 2."""
        if not extractions:
            return ProcessingResult(
                status="error",
                error=ErrorInfo(
                    code="no_extractions",
                    message="Nenhum relato estruturado encontrado para o período especificado.",
                ),
                metadata=RunMetadata(model=self.settings.model),
            )

        stats = self.compute_stats(extractions, days_window=days_window)

        # Monta consulta clínica para o RAG a partir das variáveis agregadas
        query_parts = [
            stats.tema_dominante,
            stats.sentimento_dominante,
            "impactbench bem estar",
            "apoio psicologico jovens",
        ]
        if stats.sinal_risco_detectado:
            query_parts.append("risco crise avaliacao psicologica")
        if "relacionamentos" in stats.temas_frequencia or "familia" in stats.temas_frequencia:
            query_parts.append("conexao social isolamento")

        query = " ".join(query_parts)
        retrieved_evidences, status_evidencia = self.retriever.retrieve(
            query=query,
            top_k=self.settings.top_k,
        )

        dossier, metadata = self.copilot_model.generate_dossier(
            stats=stats,
            evidences=retrieved_evidences,
            status_evidencia=status_evidencia,
        )

        return ProcessingResult(
            status="ok",
            dossier=dossier,
            metadata=metadata,
        )

    def export_markdown_report(self, dossier: CopilotDossier) -> str:
        """Converte o Dossiê estruturado em um relatório Markdown elegante para leitura rápida do psicólogo."""
        lines = [
            "# Dossiê Longitudinal do Paciente — Copiloto 007",
            f"**ID do Dossiê:** `{dossier.dossie_id}` | **Gerado em:** {dossier.created_at.strftime('%d/%m/%Y %H:%M:%S UTC')}",
            f"**Período Avaliado:** {dossier.stats.periodo_dias} dias | **Total de Relatos:** {dossier.stats.total_relatos}",
            "",
            "## 1. Síntese Temporal e Frequências",
            f"- **Tema Predominante:** `{dossier.stats.tema_dominante}`",
            f"- **Sentimento Predominante:** `{dossier.stats.sentimento_dominante}`",
            f"- **Alerta Textual de Risco:** {'🚨 **Presente** (Atenção prioritária)' if dossier.stats.sinal_risco_detectado else '✅ Não identificado'}",
            "",
            f"**Narrativa:** {dossier.sintese_narrativa}",
            "",
            "### Distribuição de Sentimentos",
        ]

        for s, count in dossier.stats.sentimentos_frequencia.items():
            lines.append(f"- **{s.capitalize()}:** {count} registro(s)")

        lines.extend([
            "",
            "## 2. Alinhamento Multidimensional (MIT ImpactBench)",
        ])

        for item in dossier.impactbench_analise:
            lines.append(f"### Dimensão: `{item.dimensao.value}`")
            lines.append(f"- **Observação Clínica:** {item.observacao_longitudinal}")
            lines.append(f"- **Fundamentação:** {item.alinhamento_com_literatura}")
            lines.append("")

        lines.extend([
            "## 3. Evidências Científicas Recuperadas (RAG)",
        ])

        if dossier.evidencias_cientificas:
            for ev in dossier.evidencias_cientificas:
                lines.append(f"#### [{ev.chunk_id}] {ev.title} ({ev.institution}, {ev.year})")
                lines.append(f"- **Nível Epistêmico:** `{ev.evidence_tier.value}`")
                lines.append(f"- **DOI/Link:** [{ev.doi_or_url}]({ev.doi_or_url})")
                lines.append(f"- **Trecho:** *\"{ev.claim_ou_trecho}\"*")
                lines.append(f"- **Limitações:** {ev.limitacoes}")
                lines.append("")
        else:
            lines.append("*Nenhuma evidência suficiente na base para este padrão específico.*")
            lines.append("")

        lines.extend([
            "## 4. Questões Investigativas Sugeridas para a Consulta",
        ])
        for q in dossier.questoes_para_o_terapeuta:
            lines.append(f"1. {q}")

        lines.extend([
            "",
            "## 5. Limitações e Lacunas de Evidência",
        ])
        for lacuna in dossier.lacunas_e_abstencoes:
            lines.append(f"- {lacuna}")

        lines.extend([
            "",
            "---",
            f"> ⚠️ **Aviso de Responsabilidade Profissional:** {dossier.aviso_epistemico}",
        ])

        return "\n".join(lines)
