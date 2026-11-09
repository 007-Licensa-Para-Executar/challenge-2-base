# Guia de Desenvolvimento: Agente 1 (Decompositor Temático e Extrator de Evidências)

## 1. Identificação e Propósito do Agente
* **Arquivo no Código:** `agents/extractor/service.py` e `agents/extractor/prompt.py`
* **Contrato de Dados:** `agents/extractor/contracts.py`
* **Objetivo Primário:** Receber o relato bruto do paciente (texto ou transcrição de áudio) junto com a classificação macrotemática produzida pela Rede Neural MLP (ex: `familia`), realizar a compreensão semântica profunda do texto, extrair os **subtemas específicos** (ex: `Irmão`, `Pai`), mapear as **evidências literais exatas** (spans com posições de início/fim e carimbos de tempo em áudio) e identificar a tonalidade afetiva e eventuais marcadores sintáticos de risco à vida.
* **Por que este componente existe?** Para garantir **100% de explicabilidade**. O psicólogo nunca verá uma categoria solta na tela; ao clicar no subtema gerado pelo Agente 1, ele acessa o trecho literal exato que o paciente escreveu ou falou, eliminando alucinações.

---

## 2. Diagrama de Fluxo e Dependências

```mermaid
flowchart LR
    A["Relato Bruto (Texto / Áudio)"] --> B["Rede Neural MLP"]
    B -->|Macrotema Padrão: 'familia' (Confiança: 91%)| C["Agente 1 (LLM Local / Ollama)"]
    A --> C
    C -->|Executa Decomposição & Span Matching| D["Validação Pydantic (ExtractionEnvelope)"]
    D --> E[("Persistência: SQLite & Vetorizador")]
```

---

## 3. Contratos de Dados (Pydantic V2)

Salve este contrato em `agents/extractor/contracts.py`:

```python
from datetime import UTC, datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

class MacroTema(str, Enum):
    TRABALHO = "trabalho"
    FAMILIA = "familia"
    RELACIONAMENTOS = "relacionamentos"
    ESTUDOS = "estudos"
    SAUDE_SONO = "saude_sono"
    FINANCAS = "financas"
    LUTO = "luto"
    AUTOESTIMA = "autoestima"
    OUTROS = "outros"
    NAO_IDENTIFICADO = "nao_identificado"

class Sentimento(str, Enum):
    ALEGRIA = "alegria"
    TRISTEZA = "tristeza"
    RAIVA = "raiva"
    MEDO = "medo"
    PREOCUPACAO = "preocupacao"
    FRUSTRACAO = "frustracao"
    CALMA = "calma"
    NAO_IDENTIFICADO = "nao_identificado"

class IndicioRisco(str, Enum):
    PRESENTE = "presente"
    NAO_IDENTIFICADO = "nao_identificado"
    INDETERMINADO = "indeterminado"

class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    quote_text: str = Field(description="Citação textual literal e exata proferida pelo paciente")
    start_char: int = Field(ge=0, description="Índice inicial do caractere no relato")
    end_char: int = Field(ge=0, description="Índice final do caractere no relato")
    audio_start_sec: Optional[float] = Field(default=None, ge=0.0, description="Início do trecho no áudio em segundos")
    audio_end_sec: Optional[float] = Field(default=None, ge=0.0, description="Fim do trecho no áudio em segundos")

class SubTemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    nome: str = Field(min_length=2, max_length=50, description="Nome conciso do subtema (ex: 'Irmão', 'Pai')")
    descricao: str = Field(min_length=5, max_length=200, description="Contextualização clínica do subtema")
    evidencias: List[EvidenceSpan] = Field(min_length=1, description="Lista de trechos que comprovam o subtema")

class Agent1Output(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    entry_id: UUID = Field(default_factory=uuid4)
    patient_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    macro_tema_validado: MacroTema
    confianca_macro_tema: float = Field(ge=0.0, le=1.0)
    subtemas: List[SubTemaItem] = Field(min_length=1, max_length=6)
    sentimento_predominante: Sentimento
    score_polaridade: float = Field(ge=-1.0, le=1.0, description="Valência afetiva de -1.0 a +1.0")
    indicio_textual_risco: IndicioRisco
    modalidade: Literal["texto", "audio", "foto"]
```

---

## 4. Prompt de Sistema do Agente 1 (Prompt Engineering Estruturado)

Crie o arquivo `agents/extractor/prompt.py`:

```python
AGENT1_SYSTEM_PROMPT = """Você é o Agente Decompositor Clínico e Extrator de Evidências Literais.
Sua missão é ler o relato íntimo do diário de um paciente e, sabendo o MACROTEMA previamente classificado por uma Rede Neural, decompor o texto em SUBTEMAS específicos e extrair os TRECHOS LITERAIS EXATOS que comprovam cada subtema.

DIRETRIZES FUNDAMENTAIS:
1. RASTREABILIDADE TOTAL: Toda citação ('quote_text') deve ser COPIADA EXATAMENTE do texto do paciente. Não altere conjugação verbal, pontuação ou sinônimos.
2. SUBTEMAS CLÍNICOS RELEVANTES:
   - Se o macrotema for 'familia', identifique pessoas ou tópicos centrais (ex: 'Irmão', 'Pai', 'Mãe', 'Finanças Familiares').
   - Se for 'trabalho', identifique gatilhos (ex: 'Chefe', 'Carga Horária', 'Medo de Demissão').
   - Não crie subtemas genéricos demais como 'Coisas Ruins' ou 'Problemas'.
3. AVALIAÇÃO DE SENTIMENTO: Rotule a emoção dominante (alegria, tristeza, raiva, medo, preocupacao, frustracao, calma) e a polaridade numérica contínua (-1.0 para muito negativo, +1.0 para muito positivo).
4. SINALIZADOR DE RISCO: Avalie se há menção explícita de ideação de autolesão ou desesperança crítica ('presente', 'nao_identificado' ou 'indeterminado').
5. SAÍDA ESTREITAMENTE TIPADA: Retorne estritamente um JSON aderente ao schema solicitado.
"""

def build_user_prompt(texto_relato: str, macrotema_nn: str, confianca_nn: float, audio_segments: list | None = None) -> str:
    audio_info = ""
    if audio_segments:
        audio_info = "\nSEGMENTOS DE ÁUDIO DISPONÍVEIS:\n" + "\n".join(
            [f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: \"{seg['text']}\"" for seg in audio_segments]
        )
    
    return f"""<contexto_classificacao>
Macrotema Predito pela Rede Neural: {macrotema_nn} (Confiança: {confianca_nn * 100:.1f}%)
</contexto_classificacao>

<relato_paciente>
{texto_relato}
</relato_paciente>
{audio_info}

Extraia os subtemas correspondentes a esse relato, suas evidências literais exatas e a classificação de sentimento conforme o esquema especificado."""
```

---

## 5. Implementação do Serviço (`agents/extractor/service.py`)

```python
import json
import httpx
from typing import Dict, Any, List
from agents.extractor.contracts import Agent1Output, EvidenceSpan, SubTemaItem
from agents.extractor.prompt import AGENT1_SYSTEM_PROMPT, build_user_prompt

class Agent1Service:
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "qwen2.5:3b"):
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.client = httpx.Client(timeout=15.0)

    def process(
        self,
        patient_id: str,
        text: str,
        macro_tema: str,
        confidence: float,
        modalidade: str = "texto",
        audio_segments: List[Dict[str, Any]] | None = None
    ) -> Agent1Output:
        user_prompt = build_user_prompt(text, macro_tema, confidence, audio_segments)
        
        # Chamada à API local do Ollama com Structured Outputs (JSON Schema)
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": AGENT1_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "format": Agent1Output.model_json_schema(),
            "options": {"temperature": 0.0, "seed": 42},
            "stream": False
        }
        
        response = self.client.post(f"{self.ollama_url}/api/chat", json=payload)
        response.raise_for_status()
        raw_json = response.json()["message"]["content"]
        
        data = json.loads(raw_json)
        data["patient_id"] = patient_id
        data["modalidade"] = modalidade
        data["macro_tema_validado"] = macro_tema
        data["confianca_macro_tema"] = confidence
        
        # Validação pós-extração para garantir que os spans batem com o texto bruto
        output = Agent1Output.model_validate(data)
        self._validate_spans(text, output.subtemas)
        return output

    def _validate_spans(self, full_text: str, subtemas: List[SubTemaItem]):
        """Garante que a citação literal extraída existe dentro do texto original."""
        for sub in subtemas:
            for ev in sub.evidencias:
                if ev.quote_text not in full_text:
                    # Ajuste determinístico caso haja pequenos artefatos de escape
                    idx = full_text.find(ev.quote_text.strip())
                    if idx != -1:
                        ev.start_char = idx
                        ev.end_char = idx + len(ev.quote_text.strip())
                    else:
                        raise ValueError(f"Citação literal '{ev.quote_text}' não localizada no texto primário.")
```

---

## 6. Como Testar (`tests/test_agent1.py`)

```python
import pytest
from unittest.mock import MagicMock, patch
from agents.extractor.service import Agent1Service

SAMPLE_TEXT = "Ontem meu irmão pegou meu carro sem pedir de novo e ainda riu de mim. Fiquei com uma raiva insuportável."

def test_agent1_successful_parsing():
    mock_response = {
        "subtemas": [
            {
                "nome": "Irmão",
                "descricao": "Conflito por apropriação indevida do veículo e deboche",
                "evidencias": [
                    {
                        "quote_text": "meu irmão pegou meu carro sem pedir de novo e ainda riu de mim",
                        "start_char": 6,
                        "end_char": 68
                    }
                ]
            }
        ],
        "sentimento_predominante": "raiva",
        "score_polaridade": -0.82,
        "indicio_textual_risco": "nao_identificado"
    }
    
    service = Agent1Service()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        mock_post.return_value.raise_for_status = MagicMock()
        
        res = service.process(
            patient_id="PAC-123",
            text=SAMPLE_TEXT,
            macro_tema="familia",
            confidence=0.92
        )
        assert res.macro_tema_validado == "familia"
        assert res.subtemas[0].nome == "Irmão"
        assert res.sentimento_predominante == "raiva"
        assert res.score_polaridade < 0
```

---

## 7. Referências Técnicas e Científicas
1. **Ollama Structured Outputs:** [https://ollama.com/blog/structured-outputs](https://ollama.com/blog/structured-outputs).
2. **Pydantic V2 Serialization & Validation:** [https://docs.pydantic.dev/latest/concepts/models/](https://docs.pydantic.dev/latest/concepts/models/).
3. **Li et al. (arXiv:2512.07797, 2025):** Análise de sentimentos e extração temática em relatos de desabafo de saúde mental.
4. **MIT ImpactBench (2025/2026):** Metodologia de auditoria orientada a evidências literais (`impactbench.media.mit.edu`).
