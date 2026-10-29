
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ExtractionState(TypedDict):
    relato: str
    relato_validado: bool
    erro: str | None


def validar_entrada(state: ExtractionState) -> dict:
    relato = state["relato"].strip()

    if not relato:
        return {
            "relato_validado": False,
            "erro": "Relato vazio.",
        }

    if len(relato) > 2400:
        return {
            "relato_validado": False,
            "erro": "Relato excede o limite permitido.",
        }

    return {
        "relato": relato,
        "relato_validado": True,
        "erro": None,
    }


def decidir_proximo_passo(
    state: ExtractionState,
) -> str:
    if state["relato_validado"]:
        return "fim"

    return "fim"


def construir_grafo():
    builder = StateGraph(ExtractionState)

    builder.add_node("validar_entrada", validar_entrada)

    builder.add_edge(START, "validar_entrada")
    builder.add_conditional_edges(
        "validar_entrada",
        decidir_proximo_passo,
        {
            "fim": END,
        },
    )

    return builder.compile()


graph = construir_grafo()


if __name__ == "__main__":
    resultado = graph.invoke(
        {
            "relato": "Tenho me sentido sobrecarregado com os estudos.",
            "relato_validado": False,
            "erro": None,
        }
    )

    print(resultado)
