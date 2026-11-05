"""Teste de integração multiagente: Agente 1 (Extrator) -> Agente 2 (Copiloto com RAG)."""

from pathlib import Path

from agents.copilot.config import CopilotSettings
from agents.copilot.service import CopilotService
from agents.extractor.contracts import (
    Extraction,
    IndicioRisco,
    Sentimento,
    Tema,
)
from agents.extractor.contracts import (
    ProcessingResult as ExtractorResult,
)
from agents.extractor.contracts import (
    RunMetadata as ExtractorMetadata,
)
from agents.extractor.storage import save_result


def test_agent_1_to_agent_2_collaboration(tmp_path: Path):
    """Verifica a colaboração entre os dois agentes com troca de informações via SQLite."""
    db_path = tmp_path / "paciente_007.sqlite3"

    # --- FASE 1: Agente 1 extrai e persiste 3 relatos ao longo da semana ---
    relatos = [
        ("Não consegui terminar o trabalho da faculdade e estou me sentindo incapaz.", Tema.ESTUDOS, Sentimento.FRUSTRACAO, IndicioRisco.NAO_IDENTIFICADO),
        ("Discuti com meu colega de grupo e preferi ficar trancado no quarto o dia todo.", Tema.RELACIONAMENTOS, Sentimento.TRISTEZA, IndicioRisco.NAO_IDENTIFICADO),
        ("Mais um dia sem ânimo para ir para a aula, tudo parece pesado demais.", Tema.ESTUDOS, Sentimento.TRISTEZA, IndicioRisco.NAO_IDENTIFICADO),
    ]

    for texto, tema, sentimento, risco in relatos:
        res = ExtractorResult(
            status="ok",
            extraction=Extraction(
                tema=tema,
                sentimento=sentimento,
                indicio_textual_risco=risco,
            ),
            metadata=ExtractorMetadata(model="qwen3:4b-test", context_tokens=2048),
        )
        save_result(db_path, texto, res)

    # --- FASE 2: Agente 2 lê os dados do Agente 1, consulta o RAG e gera Dossiê ---
    settings = CopilotSettings(
        db_path=db_path,
        mock_mode=True,
    )
    service = CopilotService(settings)

    # 1. Agente 2 carrega dados persistidos pelo Agente 1
    extractions = service.load_extractions_from_db(db_path=db_path, days_window=7)
    assert len(extractions) == 3

    # 2. Agente 2 calcula estatísticas longitudinais
    stats = service.compute_stats(extractions, days_window=7)
    assert stats.total_relatos == 3
    assert stats.tema_dominante == "estudos"
    assert stats.sentimento_dominante == "tristeza"

    # 3. Agente 2 executa RAG e síntese
    copilot_result = service.analyze(extractions, days_window=7)
    assert copilot_result.status == "ok"
    dossier = copilot_result.dossier
    assert dossier is not None

    # 4. Verificações de rastreabilidade e fundamentação
    assert dossier.stats.total_relatos == 3
    assert len(dossier.evidencias_cientificas) > 0
    assert len(dossier.impactbench_analise) >= 2
    assert len(dossier.questoes_para_o_terapeuta) >= 3

    # 5. Exportação do relatório para o psicólogo
    md_report = service.export_markdown_report(dossier)
    assert "Dossiê Longitudinal do Paciente" in md_report
    assert "estudos" in md_report
    assert "tristeza" in md_report
    assert "MIT ImpactBench" in md_report
