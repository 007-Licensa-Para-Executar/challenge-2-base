"""Propostas fechadas: texto do modelo nunca se torna código ou argumento de processo."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

COMMANDS = {
    "ajuda": "Mostrar comandos, atalhos e exemplos",
    "status": "Consultar Ollama, modelos e banco local",
    "extrair": "Analisar e salvar um relato sintético (formulário)",
    "historico": "Consultar registros locais com paginação",
    "modelos": "Listar modelos e escolher modelo para esta sessão",
    "avaliar": "Configurar avaliação smoke, desenvolvimento ou holdout",
    "testes": "Executar a suíte automatizada do projeto",
    "config": "Consultar ou alterar preferências desta sessão",
    "limpar": "Limpar a tela, preservando arquivos",
    "copiloto": "Consultar diários sintéticos ou literatura local com trechos e citações",
    "sair": "Encerrar o shell",
}
Tool = Literal[
    "ajuda", "status", "extrair", "historico", "modelos", "avaliar", "testes", "config",
    "limpar", "copiloto", "sair", "esclarecer",
]


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    pagina: int | None = Field(default=None, ge=1, le=100000)
    modo: Literal["smoke", "dev", "holdout"] | None = None


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ferramenta: Tool
    argumentos: Arguments

    @model_validator(mode="after")
    def permitted_arguments(self):
        allowed = {"historico": {"pagina"}, "avaliar": {"modo"}}
        supplied = self.argumentos.model_dump(exclude_none=True)
        if set(supplied) - allowed.get(self.ferramenta, set()):
            raise ValueError("Argumentos incompatíveis com a ferramenta")
        return self
