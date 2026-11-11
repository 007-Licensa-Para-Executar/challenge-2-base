"""Motor da Roda de Bem-Estar (Sunburst Wheel) e Rastreamento Longitudinal de Subtemas.

Implementa a representação concêntrica (inspirada no MIT ImpactBench / Roda de Bem-Estar):
- Centro: Paciente / Homem Vitruviano
- Anel Interno: 8 Macrotemas default classificados pela Rede Neural MLP
- Anel Externo: Até 24 Subtemas ativos extraídos dinamicamente pelo Agente 1
- Rotação Dinâmica: Atualização conforme novos diários entram e antigos perdem frequência
- Comparativo Longitudinal: Análise semanal e mensal de persistência vs. rotação de temas
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .contracts import Agent1Output, EvidenceSpan, MacroTema


def polarity_to_hex(polarity: float) -> str:
    """Mapeia score de polaridade (-1.0 a +1.0) para gradiente de cores (Vermelho -> Verde)."""
    val = max(-1.0, min(1.0, float(polarity)))
    if val < -0.25:
        # Vermelho a Coral (Sofrimento / Risco)
        return "#E57373" if val > -0.6 else "#E53935"
    elif val > 0.25:
        # Verde Claro a Verde Esmeralda (Florescimento / Bem-estar)
        return "#81C784" if val < 0.6 else "#388E3C"
    else:
        # Neutro / Âmbar
        return "#FFD54F"


@dataclass
class SubtopicNode:
    """Nó do anel externo do Sunburst (Subtema específico)."""

    nome: str
    macro_tema: str
    mencoes: int = 1
    peso_total: float = 1.0
    polaridade_media: float = 0.0
    cor_hex: str = "#FFD54F"
    evidencias: list[EvidenceSpan] = field(default_factory=list)
    primeira_mencao: datetime | None = None
    ultima_mencao: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.primeira_mencao:
            d["primeira_mencao"] = self.primeira_mencao.isoformat()
        if self.ultima_mencao:
            d["ultima_mencao"] = self.ultima_mencao.isoformat()
        return d


@dataclass
class MacrotopicNode:
    """Nó do anel interno do Sunburst (Macrotema da Rede Neural)."""

    macro_tema: str
    nome_exibicao: str
    mencoes: int = 0
    peso_total: float = 0.0
    polaridade_media: float = 0.0
    cor_hex: str = "#B0BEC5"
    subtemas: list[SubtopicNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro_tema": self.macro_tema,
            "nome_exibicao": self.nome_exibicao,
            "mencoes": self.mencoes,
            "peso_total": round(self.peso_total, 2),
            "polaridade_media": round(self.polaridade_media, 2),
            "cor_hex": self.cor_hex,
            "subtemas": [s.to_dict() for s in self.subtemas],
        }


@dataclass
class SunburstWheelData:
    """Estrutura hierárquica completa para plotagem do Sunburst Chart."""

    patient_id: str
    periodo: str
    total_subtemas_ativos: int
    macrotemas: list[MacrotopicNode]
    # Arrays compatíveis com Plotly / ECharts / D3 Sunburst
    ids: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    hover_texts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "periodo": self.periodo,
            "total_subtemas_ativos": self.total_subtemas_ativos,
            "macrotemas": [m.to_dict() for m in self.macrotemas],
            "sunburst_series": {
                "ids": self.ids,
                "labels": self.labels,
                "parents": self.parents,
                "values": self.values,
                "colors": self.colors,
                "hover_texts": self.hover_texts,
            },
        }


@dataclass
class LongitudinalComparison:
    """Comparativo temporal (Semanal ou Mensal) da rotação de subtemas para o psicólogo."""

    patient_id: str
    periodo_atual: str
    periodo_anterior: str
    subtemas_persistentes: list[str]
    subtemas_emergentes: list[str]
    subtemas_rotacionados: list[str]
    taxa_rotatividade: float
    evolucao_polaridade: dict[str, float]
    resumo_clinico_rotacao: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SubtopicWheelTracker:
    """Gerenciador dinâmico de agregação e rotação de subtemas para a Roda de Bem-Estar."""

    DEFAULT_MACROTHEMES: list[tuple[str, str]] = [
        ("familia", "Família"),
        ("trabalho", "Trabalho"),
        ("relacionamentos", "Relacionamentos"),
        ("estudos", "Estudos"),
        ("saude_sono", "Saúde & Sono"),
        ("financas", "Finanças"),
        ("luto", "Luto"),
        ("autoestima", "Autoestima"),
    ]

    def __init__(self, max_total_subtemas: int = 24) -> None:
        self.max_total_subtemas = max_total_subtemas

    def build_wheel(
        self,
        entries: list[Agent1Output],
        patient_id: str = "PACIENTE",
        periodo: str = "Semana Atual",
    ) -> SunburstWheelData:
        """Constrói a Roda Sunburst limitando a no máximo 24 subtemas no total,

        alocando dinamicamente a quantidade de subtemas por macrotema com base
        na frequência com que o paciente falou sobre cada tema.
        """
        # 1. Agrupa ocorrências de subtemas
        sub_stats: dict[str, dict[str, Any]] = {}

        for entry in entries:
            macro_val = (
                entry.macro_tema_validado.value
                if hasattr(entry.macro_tema_validado, "value")
                else str(entry.macro_tema_validado)
            )
            created_at = entry.created_at or datetime.now(UTC)

            for sub in entry.subtemas:
                key = (macro_val, sub.nome.strip())
                if key not in sub_stats:
                    sub_stats[key] = {
                        "nome": sub.nome.strip(),
                        "macro_tema": macro_val,
                        "mencoes": 0,
                        "peso_total": 0.0,
                        "polaridades": [],
                        "evidencias": [],
                        "primeira_mencao": created_at,
                        "ultima_mencao": created_at,
                    }

                stat = sub_stats[key]
                stat["mencoes"] += 1
                # Cada menção contribui para o peso proporcionalmente à quantidade de evidências
                stat["peso_total"] += max(1.0, float(len(sub.evidencias)))
                stat["polaridades"].append(entry.score_polaridade)
                stat["evidencias"].extend(sub.evidencias)
                if created_at < stat["primeira_mencao"]:
                    stat["primeira_mencao"] = created_at
                if created_at > stat["ultima_mencao"]:
                    stat["ultima_mencao"] = created_at

        # 2. Ordena todos os subtemas pelo peso/frequência decrescente e seleciona no MÁXIMO 24 no total
        all_sub_list = list(sub_stats.values())
        all_sub_list.sort(key=lambda s: (s["peso_total"], s["mencoes"]), reverse=True)
        active_sub_list = all_sub_list[: self.max_total_subtemas]

        # 3. Organiza os subtemas ativos sob seus respectivos macrotemas
        macro_to_subs = defaultdict(list)
        for stat in active_sub_list:
            mean_pol = (
                sum(stat["polaridades"]) / len(stat["polaridades"])
                if stat["polaridades"]
                else 0.0
            )
            node = SubtopicNode(
                nome=stat["nome"],
                macro_tema=stat["macro_tema"],
                mencoes=stat["mencoes"],
                peso_total=stat["peso_total"],
                polaridade_media=mean_pol,
                cor_hex=polarity_to_hex(mean_pol),
                evidencias=stat["evidencias"],
                primeira_mencao=stat["primeira_mencao"],
                ultima_mencao=stat["ultima_mencao"],
            )
            macro_to_subs[stat["macro_tema"]].append(node)

        # 4. Constrói os nós dos 8 macrotemas padrão
        macro_nodes: list[MacrotopicNode] = []
        for macro_code, macro_label in self.DEFAULT_MACROTHEMES:
            subs = macro_to_subs.get(macro_code, [])
            total_peso = sum(s.peso_total for s in subs)
            total_mencoes = sum(s.mencoes for s in subs)
            if subs:
                macro_pol = sum(s.polaridade_media * s.peso_total for s in subs) / max(
                    1e-6, total_peso
                )
                macro_color = polarity_to_hex(macro_pol)
            else:
                macro_pol = 0.0
                macro_color = "#E0E0E0"  # Cinza neutro se não citado

            macro_nodes.append(
                MacrotopicNode(
                    macro_tema=macro_code,
                    nome_exibicao=macro_label,
                    mencoes=total_mencoes,
                    peso_total=total_peso if total_peso > 0 else 1.0,  # Base mínima visual
                    polaridade_media=macro_pol,
                    cor_hex=macro_color,
                    subtemas=subs,
                )
            )

        # 5. Constrói os vetores para o gráfico Sunburst
        # Raiz: Centro (Paciente / Homem Vitruviano)
        ids = ["root"]
        labels = [patient_id]
        parents = [""]
        total_root_value = sum(m.peso_total for m in macro_nodes)
        values = [total_root_value]
        colors = ["#FFFFFF"]
        hover_texts = [f"Centro de Cuidado: {patient_id}"]

        # Nível 1: Os 8 Macrotemas default
        for m in macro_nodes:
            m_id = f"macro_{m.macro_tema}"
            ids.append(m_id)
            labels.append(m.nome_exibicao)
            parents.append("root")
            values.append(m.peso_total)
            colors.append(m.cor_hex)
            sub_count = len(m.subtemas)
            hover_texts.append(
                f"<b>{m.nome_exibicao}</b><br>{sub_count} subtemas ativos | Polaridade: {m.polaridade_media:+.2f}"
            )

            # Nível 2: Subtemas do macrotema (anel externo)
            for s in m.subtemas:
                s_id = f"sub_{m.macro_tema}_{s.nome.replace(' ', '_')}"
                ids.append(s_id)
                labels.append(s.nome)
                parents.append(m_id)
                values.append(s.peso_total)
                colors.append(s.cor_hex)
                hover_texts.append(
                    f"<b>{s.nome}</b> ({m.nome_exibicao})<br>Menções: {s.mencoes} | Polaridade: {s.polaridade_media:+.2f}"
                )

        return SunburstWheelData(
            patient_id=patient_id,
            periodo=periodo,
            total_subtemas_ativos=len(active_sub_list),
            macrotemas=macro_nodes,
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            colors=colors,
            hover_texts=hover_texts,
        )

    def compare_periods(
        self,
        current_entries: list[Agent1Output],
        previous_entries: list[Agent1Output],
        patient_id: str = "PACIENTE",
        current_label: str = "Semana Atual",
        previous_label: str = "Semana Anterior",
    ) -> LongitudinalComparison:
        """Compara dois períodos temporais (ex: Semana N vs Semana N-1) para identificar

        subtemas persistentes, novos (emergentes) e rotacionados (que deixaram de ser falados).
        """
        wheel_curr = self.build_wheel(current_entries, patient_id=patient_id, periodo=current_label)
        wheel_prev = self.build_wheel(
            previous_entries, patient_id=patient_id, periodo=previous_label
        )

        curr_subs = {
            s.nome: s for m in wheel_curr.macrotemas for s in m.subtemas
        }
        prev_subs = {
            s.nome: s for m in wheel_prev.macrotemas for s in m.subtemas
        }

        curr_names = set(curr_subs.keys())
        prev_names = set(prev_subs.keys())

        persistentes = sorted(curr_names & prev_names)
        emergentes = sorted(curr_names - prev_names)
        rotacionados = sorted(prev_names - curr_names)

        total_unique = len(curr_names | prev_names)
        taxa_rotatividade = (
            (len(emergentes) + len(rotacionados)) / (2.0 * max(1, total_unique))
            if total_unique
            else 0.0
        )

        # Evolução da polaridade nos subtemas persistentes
        evolucao_polaridade = {}
        for name in persistentes:
            delta = curr_subs[name].polaridade_media - prev_subs[name].polaridade_media
            evolucao_polaridade[name] = round(delta, 2)

        # Monta síntese clínica de rotação para o psicólogo
        resumo_lines = [
            f"Histórico Longitudinal ({current_label} vs. {previous_label}):",
            f"- Subtemas Ativos Atuais: {len(curr_names)} (máx 24)",
            f"- Subtemas Persistentes: {len(persistentes)} ({', '.join(persistentes) if persistentes else 'Nenhum'})",
            f"- Novos Subtemas Emergentes: {len(emergentes)} ({', '.join(emergentes) if emergentes else 'Nenhum'})",
            f"- Subtemas Rotacionados/Esquecidos: {len(rotacionados)} ({', '.join(rotacionados) if rotacionados else 'Nenhum'})",
            f"- Índice de Rotatividade Temática: {taxa_rotatividade * 100:.1f}%",
        ]

        return LongitudinalComparison(
            patient_id=patient_id,
            periodo_atual=current_label,
            periodo_anterior=previous_label,
            subtemas_persistentes=persistentes,
            subtemas_emergentes=emergentes,
            subtemas_rotacionados=rotacionados,
            taxa_rotatividade=round(taxa_rotatividade, 3),
            evolucao_polaridade=evolucao_polaridade,
            resumo_clinico_rotacao="\n".join(resumo_lines),
        )

    @staticmethod
    def generate_svg_preview(wheel_data: SunburstWheelData, size: int = 600) -> str:
        """Gera um arquivo SVG autocontido desenhando a Roda de Bem-Estar com Homem Vitruviano no centro."""
        cx = size // 2
        cy = size // 2
        r_inner = 90
        r_macro = 170
        r_outer = 270

        # Cria os elementos em SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
            f'<rect width="{size}" height="{size}" fill="#FAFAFA" rx="16"/>',
            f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="#F0F4F8" stroke="#E2E8F0" stroke-width="2"/>',
            f'<circle cx="{cx}" cy="{cy}" r="{r_macro}" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>',
            f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="#FFFFFF" stroke="#94A3B8" stroke-width="2"/>',
            # Silhueta estilizada do Homem Vitruviano no centro
            f'<circle cx="{cx}" cy="{cy - 40}" r="14" fill="#64748B" opacity="0.65"/>',
            f'<line x1="{cx}" y1="{cy - 26}" x2="{cx}" y2="{cy + 30}" stroke="#64748B" stroke-width="6" stroke-linecap="round"/>',
            f'<line x1="{cx - 45}" y1="{cy - 12}" x2="{cx + 45}" y2="{cy - 12}" stroke="#64748B" stroke-width="4" stroke-linecap="round"/>',
            f'<line x1="{cx - 42}" y1="{cy - 24}" x2="{cx + 42}" y2="{cy - 24}" stroke="#64748B" stroke-width="3" stroke-linecap="round" opacity="0.7"/>',
            f'<line x1="{cx}" y1="{cy + 30}" x2="{cx - 28}" y2="{cy + 75}" stroke="#64748B" stroke-width="5" stroke-linecap="round"/>',
            f'<line x1="{cx}" y1="{cy + 30}" x2="{cx + 28}" y2="{cy + 75}" stroke="#64748B" stroke-width="5" stroke-linecap="round"/>',
            f'<text x="{cx}" y="{cy + 18}" font-family="sans-serif" font-size="11" font-weight="bold" fill="#334155" text-anchor="middle">{wheel_data.patient_id}</text>',
        ]

        # Desenha os arcos e títulos
        svg_parts.append(
            f'<text x="{cx}" y="32" font-family="sans-serif" font-size="14" font-weight="bold" fill="#1E293B" text-anchor="middle">Roda de Bem-Estar — {wheel_data.periodo}</text>'
        )
        svg_parts.append(
            f'<text x="{cx}" y="50" font-family="sans-serif" font-size="11" fill="#64748B" text-anchor="middle">{wheel_data.total_subtemas_ativos} subtemas ativos (máx 24)</text>'
        )
        svg_parts.append("</svg>")
        return "\n".join(svg_parts)
