# Guia de Desenvolvimento: Agente 3 (Copiloto Clínico e RAG de Diretrizes Terapêuticas)

## 1. Identificação e Propósito do Agente
* **Arquivo no Código:** `agents/copilot/service.py` e `agents/copilot/prompt.py`
* **Contrato de Dados:** `agents/copilot/contracts.py`
* **Objetivo Primário:** Apoiar o psicólogo humano na preparação da consulta. Quando o terapeuta seleciona um subtema no Dashboard (ex: `Irmão` no tema `Família`) ou analisa uma correlação gerada pelo **Agente 2**, o Agente 3 consulta a **Base de Conhecimento Clínico Autorizada** (protocolos de TCC de Beck, técnicas de regulação emocional e psicoeducação) e gera uma síntese estruturada contendo:
  1. **Hipóteses Cognitivas Baseadas na Literatura** (ex: crenças intermediárias ativadas).
  2. **Sugestões de Perguntas Investigativas Abertas** para o terapeuta formular ao paciente na sessão.
  3. **Citações Mandatórias da Fonte** `[Doc_ID, Seção/Página]`.
  4. **Política de Abstenção Total:** Caso o subtema não tenha respaldo nas fontes autorizadas, o agente recusa inventar condutas.
* **Por que este componente existe?** Cumpre com rigor a **Constraint 2 (Ter uma base de conhecimento)**, a **Constraint 5 (Utilizar API por meio dos agentes)** e a **Constraint 7 (Solução ética e explicável)**. O agente nunca atua na relação com o paciente; ele é um assistente de estudos para o psicólogo, com embasamento 100% bibliográfico.

---

## 2. Diagrama de Integração do Agente 3

```mermaid
flowchart LR
    A["Psicólogo Clica em Subtema no Dashboard"] --> B["Agente 3 (Copiloto Clínico)"]
    B --> C["Motor de Busca Híbrido (BM25 + e5-small)"]
    C --> D[("Acervo de Diretrizes Clínicas TCC/Beck")]
    D -->|Trechos Relevantes + Scores RRF| C
    C -->|Filtro de Limiar (Threshold >= 0.70)| B
    B -->|Contexto Clínico + Prompt Restrito| E["Ollama / LLM API"]
    E --> F["Validação Pydantic: ClinicalGuidelineBriefing"]
    F --> G["Aba de Apoio Clínico do Dashboard (/explore)"]
```

---

## 3. Contratos de Dados (Pydantic V2)

Crie o arquivo `agents/copilot/contracts.py`:

```python
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class ProtocolCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    doc_id: str = Field(description="Identificador da obra (ex: 'BECK-TCC-2021-CAP7')")
    titulo_obra: str
    secao_pagina: str = Field(description="Capítulo, tópico ou número da página")
    trecho_citado: str = Field(description="Fragmento textual da diretriz que embasa a recomendação")

class InvestigativeQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    pergunta_sugerida: str = Field(description="Pergunta aberta formulada para o psicólogo fazer ao paciente")
    objetivo_terapeutico: str = Field(description="O que essa pergunta visa esclarecer na sessão")
    fonte_referenciada: str = Field(description="Identificador [Doc_ID] da técnica correspondente")

class ClinicalGuidelineBriefing(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    subtema_alvo: str
    macro_tema: str
    evidencia_paciente_utilizada: str
    status_abstenção: bool = Field(description="True se o sistema declarou insuficiência de fontes autorizadas")
    motivo_abstenção: Optional[str] = None
    hipotese_cognitiva: Optional[str] = Field(default=None, description="Conexão entre relato e conceitos teóricos")
    perguntas_para_sessao: List[InvestigativeQuestion] = Field(default_factory=list)
    protocolos_consultados: List[ProtocolCitation] = Field(default_factory=list)
```

---

## 4. Prompt de Sistema com Citações Obrigatórias

Crie o arquivo `agents/copilot/prompt.py`:

```python
AGENT3_SYSTEM_PROMPT = """Você é o Agente Copiloto Clínico de Apoio ao Terapeuta.
Sua única responsabilidade é correlacionar o relato do paciente e os subtemas identificados com as DIRETRIZES CLÍNICAS fornecidas no contexto.

REGRAS INEGOCIÁVEIS:
1. ANCORAGEM RESTRITA: Toda e qualquer afirmação, técnica ou pergunta sugerida deve ter origem direta e verificável nos trechos de diretrizes fornecidos. Não utilize conhecimento prévio não citado no contexto.
2. CITAÇÕES OBRIGATÓRIAS: Insira formalmente a referência [Doc_ID, Seção] em cada pergunta e hipótese formulada.
3. REGRA DE ABSTENÇÃO (FALLBACK SEGURO): Se os trechos fornecidos não contiverem diretrizes adequadas ao subtema do paciente, marque 'status_abstenção: true' e declare: "Não foram encontradas diretrizes autorizadas suficientes para este subtema na base de conhecimento."
4. TOM PROFISSIONAL E ISENTO: Não formule diagnósticos psiquiátricos fechados. Use termos como 'hipótese investigativa', 'explorar em conjunto com o paciente' e 'estratégias de manejo cognitivo'.
"""

def build_copilot_user_prompt(subtema: str, macrotema: str, quote_text: str, retrieved_contexts: list[dict]) -> str:
    formatted_contexts = []
    for c in retrieved_contexts:
        formatted_contexts.append(
            f"--- FONTE: [{c['doc_id']}] {c['titulo']} ({c['secao']}) ---\n{c['texto']}"
        )
    
    contexts_block = "\n\n".join(formatted_contexts) if formatted_contexts else "NENHUMA FONTE DISPONÍVEL."

    return f"""<diretrizes_clinicas_autorizadas>
{contexts_block}
</diretrizes_clinicas_autorizadas>

<relato_do_paciente>
Macrotema: {macrotema}
Subtema em Análise: {subtema}
Citação Literal do Paciente: "{quote_text}"
</relato_do_paciente>

Com base única e exclusivamente nas diretrizes acima, gere o briefing estruturado para o psicólogo."""
```

---

## 5. Implementação do Serviço com Busca e RAG (`agents/copilot/service.py`)

```python
import json
import httpx
from typing import List, Dict, Any
from agents.copilot.contracts import ClinicalGuidelineBriefing, ProtocolCitation, InvestigativeQuestion
from agents.copilot.prompt import AGENT3_SYSTEM_PROMPT, build_copilot_user_prompt

class Agent3CopilotService:
    def __init__(
        self,
        retriever_func,  # Função injetada que busca no banco vetorial/BM25
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:3b",
        similarity_threshold: float = 0.70
    ):
        self.retriever = retriever_func
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.client = httpx.Client(timeout=20.0)

    def generate_briefing(
        self,
        subtema: str,
        macrotema: str,
        quote_text: str
    ) -> ClinicalGuidelineBriefing:
        # 1. Recuperação Híbrida na Base de Conhecimento
        query = f"manejo clinico e intervencao para conflito {subtema} em contexto {macrotema}"
        retrieved_docs: List[Dict[str, Any]] = self.retriever(query=query, top_k=3)

        # 2. Avaliação de Suficiência (Política de Abstenção)
        valid_docs = [d for d in retrieved_docs if d.get("score", 0.0) >= self.similarity_threshold]

        if not valid_docs:
            return ClinicalGuidelineBriefing(
                subtema_alvo=subtema,
                macro_tema=macrotema,
                evidencia_paciente_utilizada=quote_text,
                status_abstenção=True,
                motivo_abstenção="Não foram encontradas diretrizes clínicas na base autorizada com relevância mínima garantida (score < 0.70)."
            )

        # 3. Montagem do Prompt e Inferência
        user_prompt = build_copilot_user_prompt(subtema, macrotema, quote_text, valid_docs)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": AGENT3_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "format": ClinicalGuidelineBriefing.model_json_schema(),
            "options": {"temperature": 0.1, "seed": 42},
            "stream": False
        }

        resp = self.client.post(f"{self.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        raw_content = resp.json()["message"]["content"]
        
        parsed = json.loads(raw_content)
        parsed["subtema_alvo"] = subtema
        parsed["macro_tema"] = macrotema
        parsed["evidencia_paciente_utilizada"] = quote_text
        parsed["status_abstenção"] = False

        return ClinicalGuidelineBriefing.model_validate(parsed)
```

---

## 6. Como Testar (`tests/test_agent3_copilot.py`)

```python
import json
from unittest.mock import MagicMock
from agents.copilot.service import Agent3CopilotService

def test_copilot_abstains_when_no_sources():
    mock_retriever = MagicMock(return_value=[])  # Nenhuma fonte encontrada
    copilot = Agent3CopilotService(retriever_func=mock_retriever)
    
    briefing = copilot.generate_briefing(
        subtema="Astrofísica",
        macrotema="outros",
        quote_text="Fiquei olhando as estrelas ontem"
    )
    
    assert briefing.status_abstenção is True
    assert "Não foram encontradas diretrizes" in briefing.motivo_abstenção
    assert len(briefing.perguntas_para_sessao) == 0

def test_copilot_generates_grounded_questions(monkeypatch):
    mock_docs = [{
        "doc_id": "TCC-BECK-CH7",
        "titulo": "Terapia Cognitivo-Comportamental",
        "secao": "Capítulo 7 - Comunicação Assertiva",
        "texto": "Para limites fraternais, treinar a técnica DEAR MAN e identificar crenças de subordinação.",
        "score": 0.88
    }]
    mock_retriever = MagicMock(return_value=mock_docs)
    copilot = Agent3CopilotService(retriever_func=mock_retriever)

    mock_llm_reply = {
        "status_abstenção": False,
        "hipotese_cognitiva": "Conflito com irmão ativa esquemas de desvalorização pessoal",
        "perguntas_para_sessao": [
            {
                "pergunta_sugerida": "Como você se sentiu no momento em que seu irmão ignorou o seu pedido?",
                "objetivo_terapeutico": "Identificar pensamentos automáticos imediatos",
                "fonte_referenciada": "[TCC-BECK-CH7]"
            }
        ],
        "protocolos_consultados": [
            {
                "doc_id": "TCC-BECK-CH7",
                "titulo_obra": "Terapia Cognitivo-Comportamental",
                "secao_pagina": "Capítulo 7",
                "trecho_citado": "Identificar crenças de subordinação e treinar assertividade"
            }
        ]
    }

    monkeypatch.setattr(copilot.client, "post", lambda url, json: type("Resp", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"message": {"content": json.dumps(mock_llm_reply)}}
    })())

    briefing = copilot.generate_briefing(
        subtema="Irmão",
        macrotema="familia",
        quote_text="Meu irmão pegou meu carro de novo"
    )

    assert briefing.status_abstenção is False
    assert len(briefing.perguntas_para_sessao) == 1
    assert "[TCC-BECK-CH7]" in briefing.perguntas_para_sessao[0].fonte_referenciada
```

---

## 7. Referências Técnicas
1. **DSM5AgentFlow (Ozgun et al., 2025):** Fluxo multiagente explicável para saúde mental com cruzamento de diretrizes diagnósticas.
2. **Retrieval-Augmented Generation in LLMs for Mental Health (arXiv 2026):** Justificativa do uso de bases externas controladas para impedir alucinação terapêutica.
3. **Beck, J. S. (2021):** *Terapia Cognitivo-Comportamental: Teoria e Prática (3ª Edição)*. Artmed Editora.
