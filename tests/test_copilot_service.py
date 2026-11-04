"""Testes unitários para o serviço central do Agente 2."""


from agents.copilot.config import CopilotSettings
from agents.copilot.service import CopilotService


def test_copilot_service_compute_stats_empty():
    service = CopilotService(CopilotSettings(mock_mode=True))
    stats = service.compute_stats([], days_window=7)
    assert stats.total_relatos == 0
    assert stats.tema_dominante == "nao_identificado"
    assert not stats.sinal_risco_detectado


def test_copilot_service_compute_stats_aggregation():
    service = CopilotService(CopilotSettings(mock_mode=True))
    extractions = [
        {"tema": "estudos", "sentimento": "frustracao", "indicio_textual_risco": "nao_identificado"},
        {"tema": "estudos", "sentimento": "preocupacao", "indicio_textual_risco": "nao_identificado"},
        {"tema": "familia", "sentimento": "frustracao", "indicio_textual_risco": "nao_identificado"},
        {"tema": "estudos", "sentimento": "frustracao", "indicio_textual_risco": "presente"},
    ]
    stats = service.compute_stats(extractions, days_window=7)

    assert stats.total_relatos == 4
    assert stats.tema_dominante == "estudos"
    assert stats.sentimento_dominante == "frustracao"
    assert stats.sinal_risco_detectado is True
    assert stats.temas_frequencia["estudos"] == 3
    assert stats.temas_frequencia["familia"] == 1


def test_copilot_service_analyze_mock_mode():
    settings = CopilotSettings(mock_mode=True)
    service = CopilotService(settings)

    extractions = [
        {"tema": "trabalho", "sentimento": "frustracao", "indicio_textual_risco": "nao_identificado"},
        {"tema": "trabalho", "sentimento": "raiva", "indicio_textual_risco": "nao_identificado"},
    ]
    res = service.analyze(extractions, days_window=7)

    assert res.status == "ok"
    assert res.dossier is not None
    assert res.dossier.stats.tema_dominante == "trabalho"
    assert len(res.dossier.impactbench_analise) >= 2
    assert len(res.dossier.questoes_para_o_terapeuta) >= 3
    assert "CFP" in res.dossier.aviso_epistemico


def test_copilot_service_export_markdown_report():
    settings = CopilotSettings(mock_mode=True)
    service = CopilotService(settings)

    extractions = [
        {"tema": "estudos", "sentimento": "tristeza", "indicio_textual_risco": "nao_identificado"},
    ]
    res = service.analyze(extractions, days_window=7)
    assert res.dossier is not None

    md_report = service.export_markdown_report(res.dossier)
    assert "# Dossiê Longitudinal do Paciente" in md_report
    assert "MIT ImpactBench" in md_report
    assert "Questões Investigativas Sugeridas" in md_report
    assert res.dossier.dossie_id in md_report
