"""Testes unitários para os contratos Pydantic do Agente 2."""

import pytest

from agents.copilot.contracts import (
    CopilotDossier,
    ErrorInfo,
    EvidenceTier,
    ImpactBenchDimension,
    KnowledgeChunk,
    LongitudinalStats,
    ProcessingResult,
    RunMetadata,
)


def test_evidence_tier_and_dimensions_enums():
    assert EvidenceTier.RESULTADO_EMPIRICO == "resultado_empirico_observado"
    assert EvidenceTier.MODELO_RISCO_SIMULADO == "modelo_de_risco_simulado"
    assert ImpactBenchDimension.AUTONOMIA_AGENCIA == "autonomia_agencia"
    assert ImpactBenchDimension.BEM_ESTAR_EMOCIONAL == "bem_estar_emocional"


def test_knowledge_chunk_valid():
    chunk = KnowledgeChunk(
        chunk_id="chunk_01",
        document_id="doc_01",
        collection="impacto_ia_bem_estar",
        title="ImpactBench Overview",
        authors=["Picard, R."],
        institution="MIT Media Lab",
        year=2026,
        source_type="benchmark",
        evidence_tier=EvidenceTier.FRAMEWORK_CONCEITUAL,
        target_age_group="12-25",
        dimension_tags=["bem_estar_emocional"],
        methodology="analise_qualitativa",
        country_context="global",
        section="Secao 1",
        doi_or_url="https://doi.org/10.48550/arXiv.2610.20690",
        text="Trecho explicativo.",
        limitations="Limitacao conceitual.",
    )
    assert chunk.chunk_id == "chunk_01"
    assert chunk.evidence_tier == EvidenceTier.FRAMEWORK_CONCEITUAL


def test_longitudinal_stats_valid():
    stats = LongitudinalStats(
        periodo_dias=7,
        total_relatos=5,
        temas_frequencia={"estudos": 3, "familia": 2},
        sentimentos_frequencia={"frustracao": 3, "calma": 2},
        indicios_risco_frequencia={"nao_identificado": 5},
        tema_dominante="estudos",
        sentimento_dominante="frustracao",
        sinal_risco_detectado=False,
    )
    assert stats.total_relatos == 5
    assert stats.tema_dominante == "estudos"


def test_processing_result_consistency_validator():
    meta = RunMetadata(model="qwen3:4b-mock")
    stats = LongitudinalStats(
        periodo_dias=7,
        total_relatos=1,
        temas_frequencia={"estudos": 1},
        sentimentos_frequencia={"frustracao": 1},
        indicios_risco_frequencia={"nao_identificado": 1},
        tema_dominante="estudos",
        sentimento_dominante="frustracao",
        sinal_risco_detectado=False,
    )
    dossier = CopilotDossier(
        stats=stats,
        sintese_narrativa="Narrativa teste",
        impactbench_analise=[],
        evidencias_cientificas=[],
        questoes_para_o_terapeuta=["Pergunta 1"],
        lacunas_e_abstencoes=["Lacuna 1"],
        status_evidencia="evidencia_suficiente",
    )

    # OK status with dossier
    ok_res = ProcessingResult(status="ok", dossier=dossier, metadata=meta)
    assert ok_res.status == "ok"
    assert ok_res.dossier is not None

    # Error status with error info
    err_res = ProcessingResult(
        status="error",
        error=ErrorInfo(code="test_err", message="Erro de teste"),
        metadata=meta,
    )
    assert err_res.status == "error"

    # Inconsistent: ok with error or without dossier
    with pytest.raises(ValueError):
        ProcessingResult(status="ok", dossier=None, metadata=meta)

    with pytest.raises(ValueError):
        ProcessingResult(status="error", dossier=dossier, metadata=meta)
