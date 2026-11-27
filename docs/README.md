# Índice Mestre de Documentação do Projeto

O [contrato da demonstração integrada](contrato-integracao-agentes.md) descreve o fluxo executável de diário, roda e chat, com os passos para rodá-lo localmente.

Bem-vindo à documentação técnica do **Diário Psicológico Assistido & Copiloto Clínico Multiagente**. 

Este repositório foi projetado para atender com excelência às **9 Constraints do Challenge 2**, fornecendo guias modulares passo a passo para que você abra o documento correspondente e saiba exatamente o que fazer, como codificar, como testar e quais referências científicas seguir.

## Documento consolidado de requisitos

Para o alinhamento atual do produto, use como referência principal o [relatório consolidado v2.1](relatorio-alinhamento/relatorio.md). A versão consolidada define seis macrotemas, dois agentes locais e distingue requisitos pretendidos das capacidades efetivamente implementadas.

Os documentos técnicos abaixo podem conter propostas, detalhes históricos ou nomes de implementação anteriores. Onde houver divergência, prevalece o relatório consolidado.

---

## 🗺️ Mapa de Navegação Rápida para Desenvolvedores

### 1. Visão Arquitetural e Governança
* [**`project-knowledge.md`**](file:///docs/project-knowledge.md): Visão panorâmica do ecossistema, fluxo de 4 camadas e fronteiras clínicas.
* [**`etic-risks.md`**](file:///docs/etic-risks.md): Governança ética, conformidade com CFP/LGPD, mitigação de riscos de LLMs e matriz de risco textual.
* [**`references.md`**](file:///docs/references.md): Bibliografia científica e recursos técnicos elegíveis (janela 2024–2026: JAMA, arXiv, PsychAdapter, MIT ImpactBench).
* [**`roadmap.md`**](file:///docs/roadmap.md): Roteiro de 8 semanas e matriz de evidências verificáveis para o MVP.

---

### 2. Guias de Implementação dos Agentes
* [**`agente-1-flow.md`**](file:///docs/agente-1-flow.md): **Fluxo de Processamento do Agente 1 (Roda Sunburst e Subtemas)**.
  - *O que faz:* Diagrama de fluxo de ponta a ponta, integração com a Rede Neural MLP, motor da Roda de Bem-Estar (máx 24 subtemas), dinâmica de rotação e comparativo longitudinal semanal/mensal para psicólogos.
* [**`agente1.md`**](file:///docs/agente1.md): **Agente 1 (Decompositor Temático e Evidências Literais)**.
  - *O que faz:* Recebe o tema da Rede Neural, decompõe em subtemas (`Irmão`, `Pai`), mapeia citações literais exatas com índices de caractere e carimbos de áudio.
  - *Código:* `agents/extractor/service.py` e contratos Pydantic.
* [**`agente2.md`**](file:///docs/agente2.md): **Agente 2 (Analista Longitudinal e Copiloto RAG)**.
  - *O que faz:* Resume o histórico autorizado, calcula comparações factuais e consulta fontes normativas com citações.
  - *Código:* `agents/correlator/service.py` e `agents/copilot/service.py`.

---

### 3. Guias de Inteligência Artificial e Dados
* [**`dossie-tecnico-rede-neural.md`**](file:///docs/dossie-tecnico-rede-neural.md): **Dossiê Técnico e Teórico da Rede Neural (Master Reference)**.
  - *O que faz:* Formalização matemática completa, dedução do gradiente da Softmax/Cross-Entropy, engenharia de embeddings no `ClinicalTextEmbedder`, dualidade NumPy puro vs PyTorch, otimizadores e regularização.
* [**`neural-network-flow.md`**](file:///docs/neural-network-flow.md): **Fluxograma e Funcionamento da Rede Neural**.
  - *O que faz:* Diagramas do MLP implementado e comparação histórica entre MLP e arquiteturas sequenciais ainda não implementadas.
* [**`rede-neural.md`**](file:///docs/rede-neural.md): **Rede Neural MLP (Classificador Temático)**.
  - *O que faz:* Multi-Layer Perceptron que pode usar oito rótulos operacionais (`familia`, `trabalho`, `relacionamentos`, `estudos`, `saude_sono`, `financas`, `luto`, `autoestima`) mapeados aos seis macrotemas consolidados. Implementações completas em PyTorch e em NumPy puro.
  - *Código:* `models/torch_mlp.py` e `models/train.py`.
* [**`banco-vetorial.md`**](file:///docs/banco-vetorial.md): **Armazenamento Local e Recuperação Vetorial**.
  - *O que faz:* Documenta SQLite, recuperação BM25 e o backend E5 local, distinguindo o demonstrador atual de um índice vetorial futuro.
  - *Código:* `agents/copilot/storage.py` e `agents/copilot/retriever.py`.
* [**`rag-mvp-integrado-rede.md`**](rag-mvp-integrado-rede.md): **Demonstrador de RAG integrado à rede temática**.
  - *O que faz:* Documenta o fluxo executável com BM25, E5 local opcional, evidências literais e limites do protótipo.
* [**`dataset-personas.md`**](file:///docs/dataset-personas.md): **Síntese de Dados e Personas Clínicas (PsychAdapter & Ulster)**.
  - *O que faz:* Geração ética de relatos sintéticos parametrizados pelo Big Five (OCEAN) e arquétipos de sofrimento para treino e teste cego.
  - *Código:* `data/synthetic_generator.py`.

---

### 4. Interface e Operações
* [**`impactbench-dashboard-spec.md`**](impactbench-dashboard-spec.md): **Especificação da Interface do Psicólogo**.
  - *O que faz:* Define a experiência `/explore`, os seis macrotemas, subtemas, evidências literais, tarefas e o briefing citado pelo Agente 2.
  - *Estado:* Especificação visual ainda não implementada; não existe dashboard ativo no repositório.
* [**`mlops-pipeline.md`**](mlops-pipeline.md): **Esteira de MLOps (uv, GitHub Actions e MLflow)**.
  - *O que faz:* descreve a rodada real: SQLite, artefatos ao lado do banco, gate por F1 macro e o Pytest do CI.
  - *Código:* `mlops/pipeline.py`, `mlops/tracker.py` e [`mlops.md`](mlops.md).
