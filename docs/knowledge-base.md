# 04 - Base de Conhecimento: Arquitetura, Proveniência e Governança

## 1. Visão Geral e Atendimento ao Requisito

Para atender ao **Requisito 2 (Ter uma base de conhecimento)**, o sistema estabelece um repositório estruturado e auditável dividido em **três acervos rigidamente isolados física e logicamente**:

```
                                  BASE DE CONHECIMENTO
                                           │
         ┌─────────────────────────────────┼────────────────────────────────┐
         ▼                                 ▼                                ▼
┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
│   Acervo 1: Regras    │       │ Acervo 2: Literatura  │       │ Acervo 3: Histórico   │
│   e Guardrails        │       │ Clínica Externa       │       │ do Paciente (Diários) │
├───────────────────────┤       ├───────────────────────┤       ├───────────────────────┤
│ • Prompts de Sistema  │       │ • Protocolos TCC/Beck │       │ • Relatos originais   │
│ • Schemas Pydantic    │       │ • Diretrizes APA/CFP  │       │ • Transcrições áudio  │
│ • Limites Éticos      │       │ • Critérios DSM-5-TR  │       │ • Metadados derivados │
│ (Imutável / Read-Only)│       │ (Vetorial + BM25)     │       │ (Isolamento por ID)   │
└───────────────────────┘       └───────────────────────┘       └───────────────────────┘
```

---

## 2. Detalhamento dos Três Acervos

### Acervo 1: Regras do Sistema, Schemas e Guardrails
- **Finalidade:** Controlar a execução dos agentes e impedir que desvios contextuais alterem a conduta da IA.
- **Natureza:** Código e configurações versionados em Git (`app/contracts.py`, `agents/*/prompt.py`).
- **Imutabilidade:** Nenhuma entrada do paciente ou consulta clínica tem permissão de sobrescrever esses arquivos em tempo de execução.

### Acervo 2: Literatura Clínica e Diretrizes Terapêuticas (RAG)
- **Finalidade:** Servir de âncora conceitual para o **Agente 3 (Copiloto Clínico)**, fornecendo embasamento teórico para sugestões de perguntas reflexivas na sessão.
- **Fontes Autorizadas e Proveniência Obrigatória:**
  Cada documento ingerido na base vetorial deve possuir ficha catalográfica estrita:
  1. `doc_id`: Identificador único (ex: `TCC-BECK-CH04-CRENCAS`).
  2. `autor`: Autores da obra ou entidade responsável (ex: Judith Beck, Aaron Beck).
  3. `titulo`: Nome do manual ou protocolo clínico (ex: *Terapia Cognitivo-Comportamental: Teoria e Prática*).
  4. `ano`: Ano da publicação (com preferência para edições vigentes).
  5. `licenca`: Direitos de uso acadêmico/pesquisa para o Challenge 2.
  6. `secao`: Capítulo, página e parágrafo de onde o chunk foi extraído.
- **Tópicos Clínicos Cobertos:**
  - Registro de Pensamentos Disfuncionais (RPD).
  - Protocolos de Ativação Comportamental para Tristeza e Desânimo.
  - Técnicas de Regulação Emocional e Comunicação Assertiva para Conflitos Interpessoais.
  - Higiene do Sono e psicoeducação da ansiedade somática.

### Acervo 3: Histórico Longitudinal de Diários do Paciente
- **Finalidade:** Armazenar os desabafos e memórias dos pacientes (textos, áudios transcritos e fotos anotadas) para análise temporal.
- **Isolamento por Paciente (`tenant_id` / `patient_id`):** Nenhum dado de um paciente pode vazar ou ser consultado no contexto de outro.
- **Imutabilidade do Relato Primário:** O texto digitado ou o áudio falado pelo paciente é a fonte primária inalterável. Subtemas, temas e notas geradas pelos agentes são marcados explicitamente como **dados derivados** (`derived_metadata`). Se a rede neural ou o agente for reconfigurado, os derivados podem ser recomputados sem perda do histórico original.

---

## 3. Tecnologia de Armazenamento e Recuperação

- **Banco Primário Relacional:** `SQLite` (nativo do Python, de altíssima confiabilidade e sem overhead de servidores em nuvem).
- **Extensão Vetorial:** `sqlite-vec` ou `ChromaDB` embarcado localmente, armazenando os vetores gerados pelo modelo `multilingual-e5-small`.
- **Garantia de Sigilo:** Banco 100% criptografado em repouso no ambiente local, atendendo integralmente à LGPD (Lei Geral de Proteção de Dados Pessoais) e aos preceitos éticos do CFP.
