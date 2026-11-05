"""Grafo de execução LangGraph para o extrator de diário emocional.

Implementa um pipeline de extração orientado a estados (StateGraph) segundo
as melhores práticas de engenharia de agentes:
- Estado tipado e imutável com TypedDict (ExtractionState)
- Nós com responsabilidade única (validação, segurança, extração, verificação, persistência)
- Roteamento condicional determinístico e sanitização de falhas
- Injeção de dependências via RunnableConfig (configurável sem acoplamento)
- Suporte opcional a checkpointing com MemorySaver
- Geração de diagrama Mermaid para documentação e explicabilidade
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from .config import Settings
from .contracts import (
    MAX_INPUT_BYTES,
    MAX_INPUT_CHARS,
    ErrorInfo,
    Extraction,
    ProcessingResult,
    RunMetadata,
    SinalParaRevisao,
)
from .model import OllamaExtractor
from .storage import StorageError, save_result


class ExtractionState(TypedDict, total=False):
    """Estado tipado do fluxo de extração no LangGraph."""

    # Entradas da execução
    relato: str
    synthetic: bool
    db_path: str | Path | None

    # Validação estrutural e guardrails de segurança
    is_valid: bool
    is_safe: bool
    safety_flags: list[str]

    # Saídas cognitivas
    extraction: Extraction | None
    requires_human_review: bool
    review_reasons: list[str]

    # Metadados operacionais e persistência
    metadata: RunMetadata | None
    saved_id: str | None

    # Status e resultado consolidado
    status: Literal["ok", "error"]
    error: ErrorInfo | None
    result: ProcessingResult | None


# Padrões conservadores de segurança e limites éticos
_ADVERSARIAL_INJECTION_RE = re.compile(
    r"(?i)\b(ignore\s+(all\s+)?(previous\s+)?instructions|esque(ça|ca)\s+(as\s+)?instru(ções|coes)|"
    r"system\s*prompt|prompt\s+de\s+sistema|mode:\s*developer|dan\s+mode|voc[êe]\s+agora\s+[ée]\s+um\s+psic[óo]logo)\b"
)


def _normalize(text: str) -> str:
    """Normaliza texto removendo diacríticos para análises de segurança."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(c) != "Mn"
    )


# ---------------------------------------------------------------------------
# Nós do Grafo (Nodes)
# ---------------------------------------------------------------------------


def validar_entrada(state: ExtractionState, config: RunnableConfig) -> dict[str, Any]:
    """Valida requisitos técnicos e éticos de entrada antes de invocar o LLM.

    Verifica:
    - Origem sintética (--synthetic).
    - Tipo e tamanho de caracteres (1 a MAX_INPUT_CHARS).
    - Limite de bytes em UTF-8 (MAX_INPUT_BYTES).
    """
    relato = state.get("relato", "")
    synthetic = state.get("synthetic", True)

    if not synthetic:
        return {
            "is_valid": False,
            "status": "error",
            "error": ErrorInfo(
                code="invalid_input",
                message="Use --synthetic somente para entradas inteiramente inventadas.",
            ),
        }

    if not isinstance(relato, str) or not relato.strip():
        return {
            "is_valid": False,
            "status": "error",
            "error": ErrorInfo(
                code="invalid_input",
                message="Informe um relato sintético não vazio.",
            ),
        }

    cleaned = relato.strip()

    if len(cleaned) > MAX_INPUT_CHARS:
        return {
            "is_valid": False,
            "status": "error",
            "error": ErrorInfo(
                code="input_too_long",
                message=f"O relato excede o limite de {MAX_INPUT_CHARS} caracteres.",
            ),
        }

    try:
        raw_bytes = len(cleaned.encode("utf-8"))
    except UnicodeError:
        return {
            "is_valid": False,
            "status": "error",
            "error": ErrorInfo(
                code="invalid_input",
                message="O relato deve conter texto UTF-8 válido.",
            ),
        }

    if raw_bytes > MAX_INPUT_BYTES:
        return {
            "is_valid": False,
            "status": "error",
            "error": ErrorInfo(
                code="input_too_long",
                message=f"O relato excede o limite de {MAX_INPUT_BYTES} bytes UTF-8.",
            ),
        }

    return {
        "relato": cleaned,
        "is_valid": True,
        "error": None,
    }


def aplicar_guardrail_seguranca(
    state: ExtractionState, config: RunnableConfig
) -> dict[str, Any]:
    """Aplica guardrails determinísticos para prevenir injeção de prompt e violação de limites éticos."""
    relato = state.get("relato", "")
    flags: list[str] = []

    # Detecção de tentativas de injeção de instruções no relato
    if _ADVERSARIAL_INJECTION_RE.search(relato):
        return {
            "is_safe": False,
            "status": "error",
            "safety_flags": ["tentativa_injecao_prompt"],
            "error": ErrorInfo(
                code="guardrail_rejection",
                message="Conteúdo rejeitado por violar as fronteiras de segurança operacional.",
            ),
        }

    # Pré-triagem ética para indício explícito no texto
    norm = _normalize(relato)
    if any(
        kw in norm
        for kw in (
            "dar fim a minha vida",
            "acabar com minha vida",
            "me matar",
            "nao aguento mais viver",
            "pensando em suicidio",
        )
    ):
        flags.append("indicio_critico_pre_triagem")

    return {
        "is_safe": True,
        "safety_flags": flags,
        "error": None,
    }


def extrair_metadados(
    state: ExtractionState, config: RunnableConfig
) -> dict[str, Any]:
    """Invoca o extrator cognitivo Ollama de forma segura e estruturada.

    Permite injeção de dependência via config['configurable']['extractor'] ou
    config['configurable']['settings'].
    """
    relato = state["relato"]
    configurable = (config or {}).get("configurable", {})

    settings: Settings = configurable.get("settings") or Settings.from_env()
    extractor: OllamaExtractor = configurable.get("extractor") or OllamaExtractor(settings)

    started = perf_counter()
    try:
        result = extractor.extract(relato)
    except Exception:  # noqa: BLE001 - Sanitiza falha não tratada de provedores externos
        latency_ms = (perf_counter() - started) * 1000
        return {
            "status": "error",
            "extraction": None,
            "error": ErrorInfo(
                code="model_error",
                message="Falha inesperada ao executar o modelo local.",
            ),
            "metadata": RunMetadata(
                model=settings.model,
                context_tokens=settings.context_tokens,
                latency_ms=latency_ms,
            ),
        }

    if result.status == "ok":
        return {
            "status": "ok",
            "extraction": result.extraction,
            "metadata": result.metadata,
            "error": None,
        }

    return {
        "status": "error",
        "extraction": None,
        "metadata": result.metadata,
        "error": result.error,
    }


def verificar_extracao(
    state: ExtractionState, config: RunnableConfig
) -> dict[str, Any]:
    """Verifica fundamentação das evidências e sinaliza necessidade de revisão humana.

    Boas práticas agentic:
    - Checagem de fundamentação (grounding): trechos de evidência devem estar no relato.
    - Sinalização ética: casos com indício identificado exigem revisão clínica humana.
    """
    extraction = state.get("extraction")
    relato = state.get("relato", "")

    if extraction is None:
        return {
            "requires_human_review": False,
            "review_reasons": [],
        }

    reasons: list[str] = []
    requires_review = False

    # 1. Sinal para revisão explícito pelo modelo
    if extraction.sinal_para_revisao == SinalParaRevisao.SINAL_IDENTIFICADO:
        requires_review = True
        reasons.append(
            extraction.justificativa_revisao
            or "Indício textual identificado pelo modelo requer avaliação clínica humana."
        )

    # 2. Pré-triagem de segurança detectou gatilho
    if "indicio_critico_pre_triagem" in state.get("safety_flags", []):
        requires_review = True
        reasons.append("Detecção determinística prévia de indício crítico de bem-estar.")

    # 3. Grounding check de evidências
    relato_lower = relato.lower()
    for tema in extraction.temas:
        for ev in tema.evidencias:
            if ev.trecho.strip() and ev.trecho.lower() not in relato_lower:
                reasons.append(f"Evidência de tema '{tema.tema.value}' não encontrada literalmente no texto.")

    for sent in extraction.sentimentos:
        for ev in sent.evidencias:
            if ev.trecho.strip() and ev.trecho.lower() not in relato_lower:
                reasons.append(f"Evidência de sentimento '{sent.sentimento.value}' não encontrada literalmente no texto.")

    return {
        "requires_human_review": requires_review,
        "review_reasons": reasons,
    }


def persistir_resultado(
    state: ExtractionState, config: RunnableConfig
) -> dict[str, Any]:
    """Persiste o resultado validado em banco SQLite de forma atômica."""
    relato = state["relato"]
    extraction = state["extraction"]
    metadata = state.get("metadata") or RunMetadata(model="unconfigured")

    configurable = (config or {}).get("configurable", {})
    should_persist = configurable.get("persist", True)

    # Se persistência for desativada (ex: em testes puramente em memória)
    if not should_persist:
        result = ProcessingResult(
            status="ok",
            extraction=extraction,
            metadata=metadata,
        )
        return {
            "saved_id": result.id,
            "result": result,
        }

    db_path = state.get("db_path") or configurable.get("db_path")
    if not db_path:
        settings: Settings = configurable.get("settings") or Settings.from_env()
        db_path = settings.db_path

    result = ProcessingResult(
        status="ok",
        extraction=extraction,
        metadata=metadata,
    )

    try:
        save_result(db_path, relato, result)
    except StorageError:
        return {
            "status": "error",
            "saved_id": None,
            "error": ErrorInfo(
                code="storage_error",
                message="A execução não foi salva no banco local.",
            ),
        }

    return {
        "saved_id": result.id,
        "result": result,
    }


def formatar_saida(
    state: ExtractionState, config: RunnableConfig
) -> dict[str, Any]:
    """Garante que o ProcessingResult final esteja montado com status ok."""
    if state.get("result") is not None:
        return {}

    metadata = state.get("metadata") or RunMetadata(model="unconfigured")
    result = ProcessingResult(
        status="ok",
        extraction=state["extraction"],
        metadata=metadata,
    )
    return {"result": result}


def tratar_erro(
    state: ExtractionState, config: RunnableConfig
) -> dict[str, Any]:
    """Ponto central de tratamento e formatação de erros do grafo."""
    configurable = (config or {}).get("configurable", {})
    settings: Settings | None = configurable.get("settings")

    metadata = state.get("metadata") or RunMetadata(
        model=settings.model if settings else "unconfigured",
        context_tokens=settings.context_tokens if settings else 2048,
    )

    error = state.get("error") or ErrorInfo(
        code="processing_error",
        message="Falha durante o processamento do relato.",
    )

    result = ProcessingResult(
        status="error",
        error=error,
        metadata=metadata,
    )

    return {
        "status": "error",
        "result": result,
    }


# ---------------------------------------------------------------------------
# Funções de Roteamento Condicional (Conditional Edges)
# ---------------------------------------------------------------------------


def rotear_apos_validacao(state: ExtractionState) -> Literal["safety_guardrail", "handle_error"]:
    """Encaminha para guardrail se a entrada for válida, ou para erro."""
    return "safety_guardrail" if state.get("is_valid") else "handle_error"


def rotear_apos_guardrail(state: ExtractionState) -> Literal["extract_metadata", "handle_error"]:
    """Encaminha para extração se os guardrails forem respeitados."""
    return "extract_metadata" if state.get("is_safe", True) else "handle_error"


def rotear_apos_extracao(state: ExtractionState) -> Literal["verify_extraction", "handle_error"]:
    """Encaminha para verificação se o modelo respondeu com sucesso."""
    if state.get("status") == "ok" and state.get("extraction") is not None:
        return "verify_extraction"
    return "handle_error"


def rotear_apos_verificacao(state: ExtractionState) -> Literal["persist_result", "handle_error"]:
    """Encaminha para persistência ou para erro caso haja falha."""
    if state.get("status") == "error":
        return "handle_error"
    return "persist_result"


def rotear_apos_persistencia(state: ExtractionState) -> Literal["format_output", "handle_error"]:
    """Encaminha para formatação de sucesso ou tratamento de erro."""
    if state.get("status") == "ok" and state.get("saved_id"):
        return "format_output"
    return "handle_error"


# ---------------------------------------------------------------------------
# Construção e Compilação do StateGraph
# ---------------------------------------------------------------------------


def construir_grafo(checkpointer: BaseCheckpointSaver | None = None) -> Any:
    """Constrói e compila o StateGraph completo de extração com LangGraph.

    Parameters:
        checkpointer: Opcional. Instância de checkpointer (ex: MemorySaver())
                      para rastrear histórico e permitir time-travel debugging.

    Returns:
        CompiledStateGraph pronto para invocação síncrona ou assíncrona.
    """
    builder = StateGraph(ExtractionState)

    # Registro de Nós
    builder.add_node("validar_entrada", validar_entrada)
    builder.add_node("safety_guardrail", aplicar_guardrail_seguranca)
    builder.add_node("extrair_metadados", extrair_metadados)
    builder.add_node("verificar_extracao", verificar_extracao)
    builder.add_node("persistir_resultado", persistir_resultado)
    builder.add_node("formatar_saida", formatar_saida)
    builder.add_node("tratar_erro", tratar_erro)

    # Fluxo principal e transições condicionais
    builder.add_edge(START, "validar_entrada")

    builder.add_conditional_edges(
        "validar_entrada",
        rotear_apos_validacao,
        {
            "safety_guardrail": "safety_guardrail",
            "handle_error": "tratar_erro",
        },
    )

    builder.add_conditional_edges(
        "safety_guardrail",
        rotear_apos_guardrail,
        {
            "extract_metadata": "extrair_metadados",
            "handle_error": "tratar_erro",
        },
    )

    builder.add_conditional_edges(
        "extrair_metadados",
        rotear_apos_extracao,
        {
            "verify_extraction": "verificar_extracao",
            "handle_error": "tratar_erro",
        },
    )

    builder.add_conditional_edges(
        "verificar_extracao",
        rotear_apos_verificacao,
        {
            "persist_result": "persistir_resultado",
            "handle_error": "tratar_erro",
        },
    )

    builder.add_conditional_edges(
        "persistir_resultado",
        rotear_apos_persistencia,
        {
            "format_output": "formatar_saida",
            "handle_error": "tratar_erro",
        },
    )

    builder.add_edge("formatar_saida", END)
    builder.add_edge("tratar_erro", END)

    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)

    return builder.compile()


# Grafo compilado padrão exportado para o módulo
graph = construir_grafo()


def get_graph_mermaid() -> str:
    """Retorna a representação do grafo em diagrama Mermaid."""
    return graph.get_graph().draw_mermaid()


def run_extraction_graph(
    relato: str,
    settings: Settings | None = None,
    *,
    synthetic: bool = True,
    db_path: str | Path | None = None,
    extractor: OllamaExtractor | None = None,
    persist: bool = True,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_id: str | None = None,
) -> ProcessingResult:
    """Função de alto nível para executar a extração com LangGraph.

    Parameters:
        relato: Texto sintético para análise.
        settings: Configuração operacional local.
        synthetic: Confirmação de que o texto é sintético para testes.
        db_path: Caminho opcional do banco SQLite.
        extractor: Instância opcional injetável de OllamaExtractor.
        persist: Se True, persiste o resultado no SQLite.
        checkpointer: Checkpointer opcional para rastreabilidade de estado.
        thread_id: Identificador de sessão para o checkpointer.

    Returns:
        ProcessingResult validado e tipado.
    """
    g = construir_grafo(checkpointer=checkpointer) if checkpointer is not None else graph

    config: RunnableConfig = {
        "configurable": {
            "settings": settings or Settings.from_env(),
            "extractor": extractor,
            "db_path": db_path,
            "persist": persist,
        }
    }

    if thread_id is not None:
        config["configurable"]["thread_id"] = thread_id

    initial_state: ExtractionState = {
        "relato": relato,
        "synthetic": synthetic,
        "db_path": db_path,
    }

    final_state = g.invoke(initial_state, config=config)
    result = final_state.get("result")
    if result is None:
        # Fallback de segurança garantindo contrato válido
        return ProcessingResult(
            status="error",
            error=final_state.get("error") or ErrorInfo(
                code="processing_error",
                message="Falha desconhecida no encerramento do grafo.",
            ),
            metadata=final_state.get("metadata") or RunMetadata(model="unconfigured"),
        )
    return result


if __name__ == "__main__":
    exemplo = "Tenho me sentido sobrecarregado com os prazos no trabalho e isso tem tirado meu sono."
    print("Executando pipeline com LangGraph:")
    res = run_extraction_graph(exemplo, synthetic=True, persist=False)
    print(res.model_dump_json(indent=2))
