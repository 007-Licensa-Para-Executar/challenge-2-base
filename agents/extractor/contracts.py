from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

SCHEMA_VERSION = "2.0.0"
PROMPT_VERSION = "2.0.0"
MAX_INPUT_CHARS = 2400
MAX_INPUT_BYTES = 2400


class Sentimento(str, Enum):
    ALEGRIA = "alegria"
    TRISTEZA = "tristeza"
    RAIVA = "raiva"
    MEDO = "medo"
    PREOCUPACAO = "preocupacao"
    FRUSTRACAO = "frustracao"
    CALMA = "calma"
    OUTRO = "outro"
    NAO_IDENTIFICADO = "nao_identificado"


class TipoEvidencia(str, Enum):
    EXPLICITA = "explicita"
    IMPLICITA = "implicita"
    AMBIGUA = "ambigua"


class SinalParaRevisao(str, Enum):
    SINAL_IDENTIFICADO = "sinal_identificado"
    NENHUM_SINAL_IDENTIFICADO = "nenhum_sinal_identificado"
    INDETERMINADO = "indeterminado"


class IndicioRisco(str, Enum):
    PRESENTE = "presente"
    NAO_IDENTIFICADO = "nao_identificado"
    INDETERMINADO = "indeterminado"


class Tema(str, Enum):
    TRABALHO = "trabalho"
    FAMILIA = "familia"
    RELACIONAMENTOS = "relacionamentos"
    ESTUDOS = "estudos"
    SAUDE = "saude"
    SAUDE_BEM_ESTAR = "saude_bem_estar"
    FINANCAS = "financas"
    LUTO = "luto"
    AUTOESTIMA_IDENTIDADE = "autoestima_identidade"
    VIDA_SOCIAL_PERTENCIMENTO = "vida_social_pertencimento"
    ROTINA_RESPONSABILIDADES = "rotina_responsabilidades"
    FUTURO_OBJETIVOS = "futuro_objetivos"
    MUDANCAS_PERDAS = "mudancas_perdas"
    LAZER_INTERESSES = "lazer_interesses"
    OUTROS = "outros"
    NAO_IDENTIFICADO = "nao_identificado"


class Evidencia(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trecho: str = Field(min_length=1, max_length=500)
    tipo: TipoEvidencia = TipoEvidencia.EXPLICITA


class ClassificacaoTema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tema: Tema
    evidencias: list[Evidencia] = Field(default_factory=list, max_length=5)


class ClassificacaoSentimento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentimento: Sentimento
    evidencias: list[Evidencia] = Field(default_factory=list, max_length=5)


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temas: list[ClassificacaoTema] = Field(default_factory=list, max_length=5)
    sentimentos: list[ClassificacaoSentimento] = Field(
        default_factory=list,
        max_length=5,
    )
    sinal_para_revisao: SinalParaRevisao = SinalParaRevisao.NENHUM_SINAL_IDENTIFICADO
    justificativa_revisao: str | None = Field(
        default=None,
        max_length=500,
    )

    # Campos de compatibilidade com v1 (usados em testes e runners existentes)
    tema: Tema | None = None
    sentimento: Sentimento | None = None
    indicio_textual_risco: IndicioRisco | None = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_v1_and_v2_input(cls, data):
        if not isinstance(data, dict):
            return data

        # Se dados v1 foram passados
        v1_tema = data.get("tema")
        v1_sentimento = data.get("sentimento")
        v1_risco = data.get("indicio_textual_risco")

        # Se 'temas' não veio, mas 'tema' veio
        if "temas" not in data and v1_tema:
            data["temas"] = [
                {
                    "tema": v1_tema,
                    "evidencias": [{"trecho": "relato", "tipo": "explicita"}],
                }
            ]

        # Se 'sentimentos' não veio, mas 'sentimento' veio
        if "sentimentos" not in data and v1_sentimento:
            data["sentimentos"] = [
                {
                    "sentimento": v1_sentimento,
                    "evidencias": [{"trecho": "relato", "tipo": "explicita"}],
                }
            ]

        # Mapeamento do sinal de revisão / risco
        if "sinal_para_revisao" not in data and v1_risco:
            if v1_risco == "presente" or v1_risco == IndicioRisco.PRESENTE:
                data["sinal_para_revisao"] = SinalParaRevisao.SINAL_IDENTIFICADO.value
                if not data.get("justificativa_revisao"):
                    data["justificativa_revisao"] = "Indício textual de risco identificado no relato."
            elif v1_risco == "indeterminado" or v1_risco == IndicioRisco.INDETERMINADO:
                data["sinal_para_revisao"] = SinalParaRevisao.INDETERMINADO.value
            else:
                data["sinal_para_revisao"] = SinalParaRevisao.NENHUM_SINAL_IDENTIFICADO.value

        return data

    @model_validator(mode="after")
    def validate_review_signal_and_sync(self):
        if not self.temas and not self.tema:
            raise ValueError("A extração deve conter ao menos um tema identificado ou classificado.")

        # Sincroniza campos v1 para conveniência
        if not self.tema and self.temas:
            self.tema = self.temas[0].tema
        if not self.sentimento and self.sentimentos:
            self.sentimento = self.sentimentos[0].sentimento
        if not self.indicio_textual_risco:
            if self.sinal_para_revisao == SinalParaRevisao.SINAL_IDENTIFICADO:
                self.indicio_textual_risco = IndicioRisco.PRESENTE
            elif self.sinal_para_revisao == SinalParaRevisao.INDETERMINADO:
                self.indicio_textual_risco = IndicioRisco.INDETERMINADO
            else:
                self.indicio_textual_risco = IndicioRisco.NAO_IDENTIFICADO

        if (
            self.sinal_para_revisao == SinalParaRevisao.SINAL_IDENTIFICADO
            and not self.justificativa_revisao
        ):
            raise ValueError(
                "Um sinal identificado exige justificativa."
            )

        if (
            self.sinal_para_revisao != SinalParaRevisao.SINAL_IDENTIFICADO
            and self.justificativa_revisao is not None
        ):
            raise ValueError(
                "A justificativa de sinal só pode ser preenchida "
                "quando houver sinal identificado."
            )

        return self


class RunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    model_digest: str | None = None
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION
    context_tokens: int = Field(default=2048, ge=2048, le=4096)
    latency_ms: float = Field(default=0, ge=0)
    synthetic: bool = True


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str = Field(max_length=300)


class ProcessingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    status: Literal["ok", "error"]
    extraction: Extraction | None = None
    error: ErrorInfo | None = None
    metadata: RunMetadata

    @model_validator(mode="after")
    def consistent_result(self):
        if self.status == "ok" and (
            self.extraction is None or self.error is not None
        ):
            raise ValueError(
                "Resultado bem-sucedido exige extraction "
                "e não pode conter error."
            )

        if self.status == "error" and (
            self.extraction is not None or self.error is None
        ):
            raise ValueError(
                "Resultado com erro não pode conter extraction "
                "e deve conter error."
            )

        return self
