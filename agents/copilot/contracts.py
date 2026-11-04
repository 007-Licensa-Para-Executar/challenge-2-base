"""Contratos Pydantic compartilhados para o Agente 2 (Copiloto e RAG)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"
PROMPT_VERSION = "1.0.0"


class EvidenceTier(str, Enum):
    RESULTADO_EMPIRICO = "resultado_empirico_observado"
    ASSOCIACAO = "associacao_sem_causalidade"
    RECOMENDACAO_NORMATIVA = "recomendacao_normativa"
    MODELO_RISCO_SIMULADO = "modelo_de_risco_simulado"
    LIMITACAO_METODOLOGICA = "limitacao_metodologica"
    FRAMEWORK_CONCEITUAL = "framework_conceitual"


class ImpactBenchDimension(str, Enum):
    BEM_ESTAR_EMOCIONAL = "bem_estar_emocional"
    AUTONOMIA_AGENCIA = "autonomia_agencia"
    CONEXAO_SOCIAL = "conexao_social"
    PENSAMENTO_CRITICO = "pensamento_critico"
    DEPENDENCIA_IA = "dependencia_ia"


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    document_id: str
    collection: str
    title: str
    authors: list[str]
    institution: str
    year: int
    source_type: str
    evidence_tier: EvidenceTier
    target_age_group: str
    dimension_tags: list[str]
    methodology: str
    country_context: str
    section: str
    doi_or_url: str
    text: str
    limitations: str


class RetrievedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    title: str
    institution: str
    year: int
    evidence_tier: EvidenceTier
    doi_or_url: str
    claim_ou_trecho: str
    limitacoes: str


class ImpactBenchAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimensao: ImpactBenchDimension
    observacao_longitudinal: str
    alinhamento_com_literatura: str


class LongitudinalStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    periodo_dias: int = Field(ge=1)
    total_relatos: int = Field(ge=0)
    temas_frequencia: dict[str, int]
    sentimentos_frequencia: dict[str, int]
    indicios_risco_frequencia: dict[str, int]
    tema_dominante: str
    sentimento_dominante: str
    sinal_risco_detectado: bool


class CopilotDossier(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dossie_id: str = Field(default_factory=lambda: f"dos_{uuid4().hex[:12]}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    synthetic: Literal[True] = True
    stats: LongitudinalStats
    sintese_narrativa: str
    impactbench_analise: list[ImpactBenchAnalysis]
    evidencias_cientificas: list[RetrievedEvidence]
    questoes_para_o_terapeuta: list[str]
    lacunas_e_abstencoes: list[str]
    status_evidencia: Literal["evidencia_suficiente", "evidencia_parcial", "evidencia_insuficiente"]
    aviso_epistemico: str = (
        "Este dossiê é gerado por inteligência artificial para fins de síntese informacional "
        "e não constitui diagnóstico clínico, prognóstico ou prescrição. Toda conduta é de "
        "responsabilidade exclusiva do psicólogo responsável, conforme Resolução CFP nº 09/2024."
    )


class RunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    model_digest: str | None = None
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION
    latency_ms: float = Field(default=0, ge=0)
    retrieved_chunks_count: int = Field(default=0, ge=0)
    synthetic: Literal[True] = True


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str


class ProcessingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["ok", "error"]
    dossier: CopilotDossier | None = None
    error: ErrorInfo | None = None
    metadata: RunMetadata

    @model_validator(mode="after")
    def consistent_result(self):
        if self.status == "ok" and (self.dossier is None or self.error is not None):
            raise ValueError("Resultados 'ok' exigem dossier preenchido e erro nulo.")
        if self.status == "error" and (self.dossier is not None or self.error is None):
            raise ValueError("Resultados de erro não devem conter dossier e exigem info de erro.")
        return self
