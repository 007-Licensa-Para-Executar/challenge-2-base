# Índice Mestre de Documentação do Projeto

Bem-vindo à documentação técnica do **Diário Psicológico Assistido & Copiloto Clínico Multiagente**. 

Este repositório foi projetado para atender com excelência às **9 Constraints do Challenge 2**, fornecendo guias modulares passo a passo para que você abra o documento correspondente e saiba exatamente o que fazer, como codificar, como testar e quais referências científicas seguir.

---

## 🗺️ Mapa de Navegação Rápida para Desenvolvedores

### 1. Visão Arquitetural e Governança
* [**`project-knowledge.md`**](file:///docs/project-knowledge.md): Visão panorâmica do ecossistema, fluxo de 4 camadas e fronteiras clínicas.
* [**`etic-risks.md`**](file:///docs/etic-risks.md): Governança ética, conformidade com CFP/LGPD, mitigação de riscos de LLMs e matriz de risco textual.
* [**`references.md`**](file:///docs/references.md): Bibliografia científica e recursos técnicos elegíveis (janela 2024–2026: JAMA, arXiv, PsychAdapter, MIT ImpactBench).
* [**`roadmap.md`**](file:///docs/roadmap.md): Roteiro de 8 semanas e matriz de evidências verificáveis para o MVP.

---

### 2. Guias de Implementação dos Agentes
* [**`agente1.md`**](file:///docs/agente1.md): **Agente 1 (Decompositor Temático e Evidências Literais)**.
  - *O que faz:* Recebe o tema da Rede Neural, decompõe em subtemas (`Irmão`, `Pai`), mapeia citações literais exatas com índices de caractere e carimbos de áudio.
  - *Código:* `agents/extractor/service.py` e contratos Pydantic.
* [**`agente2.md`**](file:///docs/agente2.md): **Agente 2 (Correlacionador Longitudinal e Padrões)**.
  - *O que faz:* Cruza dados históricos de 7 a 30 dias do paciente, detecta correlações temporais, gatilhos de sofrimento e fatores protetivos de florescimento.
  - *Código:* `agents/correlator/service.py`.
* [**`agente3.md`**](file:///docs/agente3.md): **Agente 3 (Copiloto Clínico e RAG de Diretrizes TCC)**.
  - *O que faz:* Consulta acervos de literatura clínica autorizada, sugere perguntas investigativas para a sessão com citações mandatórias `[Doc_ID]` e política de abstenção segura.
  - *Código:* `agents/copilot/service.py`.

---

### 3. Guias de Inteligência Artificial e Dados
* [**`rede-neural.md`**](rede-neural.md): **Desenho de uma MLP para macrotemas clínicos**.
  - *O que faz:* registra uma proposta ainda não implementada de classificador de temas em PyTorch e NumPy.
  - *Código em uso:* a rede versionada classifica sentimento em `models/neural_net.py`. O ciclo de treino está em [`mlops.md`](mlops.md).
* [**`banco-vetorial.md`**](file:///docs/banco-vetorial.md): **Banco Vetorial Local (`sqlite-vec`)**.
  - *O que faz:* Armazenamento relacional e vetorial de 384 dimensões 100% local, criptografado e sem envio de dados para a nuvem.
  - *Código:* `knowledge_base/vector_store.py` e `knowledge_base/schema.sql`.
* [**`rag.md`**](file:///docs/rag.md): **Pipeline de RAG e Busca Híbrida (BM25 + Vetorial com RRF)**.
  - *O que faz:* Combina correspondência lexical exata e busca densa usando Reciprocal Rank Fusion, com limiar de corte $\ge 0.70$ para abstenção de alucinações.
  - *Código:* `knowledge_base/hybrid_retriever.py`.
* [**`dataset-personas.md`**](file:///docs/dataset-personas.md): **Síntese de Dados e Personas Clínicas (PsychAdapter & Ulster)**.
  - *O que faz:* Geração ética de relatos sintéticos parametrizados pelo Big Five (OCEAN) e arquétipos de sofrimento para treino e teste cego.
  - *Código:* `data/synthetic_generator.py`.

---

### 4. Interface e Operações
* [**`dashboard-ux.md`**](file:///docs/dashboard-ux.md): **Interface do Psicólogo (Estilo MIT ImpactBench `/explore`)**.
  - *O que faz:* Dashboard interativo em Streamlit com os 8 cards temáticos, desdobramento em pílulas de subtemas e **Modal Pop-up com Citação Literal e Player de Áudio Recortado**.
  - *Código:* `app/dashboard.py`.
* [**`mlops-pipeline.md`**](mlops-pipeline.md): **Esteira de MLOps (uv, GitHub Actions e MLflow)**.
  - *O que faz:* descreve a rodada real: SQLite, artefatos ao lado do banco, gate por F1 macro e o Pytest do CI.
  - *Código:* `mlops/pipeline.py`, `mlops/tracker.py` e [`mlops.md`](mlops.md).
