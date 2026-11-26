# Roteiro de Execução do MVP e Atendimento às Restrições

Este cronograma orienta o desenvolvimento do **Diário Clínico Assistido & Copiloto Psicológico**, cobrindo o ciclo de 8 semanas de entrega acadêmica e técnica, garantindo que as **9 Constraints** sejam cumpridas de forma verificável.

---

## 1. Matriz de Atendimento às 9 Constraints do Desafio

| Restrição (Constraint) | Componente Técnico Responsável | Evidência Comprovável |
| :--- | :--- | :--- |
| **1. Ter pelo menos 2 agentes que trabalhem juntos** | Agente 1 (Decompositor de Subtemas e Evidências) integrado ao Agente 2 (Correlacionador Longitudinal) e Agente 3 (RAG). | Testes de integração em `tests/test_agents_collaboration.py` demonstrando passagem de dados estruturados entre os agentes. |
| **2. Ter uma base de conhecimento** | Base tripartite: Acervo de Diretrizes Clínicas (TCC/Beck), Histórico do Paciente e Regras do Sistema. | Módulo `knowledge_base/` com índice vetorial e documentos com metadados de proveniência (autor, licença, data). |
| **3. Aplicar MLOps** | Pipeline em `mlops/`, lock do `uv`, CI e MLflow em SQLite com artefatos ao lado do banco. | `uv run bem-estar-mlops`, tag `promoted`, matriz de confusão e registry só após o gate de F1 macro. Ver `docs/mlops.md`. |
| **4. Construir e testar rede neural simples** | Rede Neural MLP (PyTorch e NumPy puro) alimentada por embeddings densos **SBERT** para identificar os **6 temas** (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`) e atribuir seus percentuais (`%`), comparada a um baseline de classe mais frequente. | `models/sbert_embedder.py`, `models/torch_mlp.py`, `models/numpy_mlp.py`, `models/train.py`, `models/predictor.py` e suíte `tests/test_*mlp*.py`. |
| **5. Utilizar API por meio dos agentes** | Chamadas à API local Ollama, API de transcrição (STT Whisper) e API de busca vetorial. | Módulo de cliente HTTP tipado via `httpx` com tratamento de timeout, retry e testes de falha. |
| **6. Ferramenta de versionamento de código** | Repositório Git com branches temáticas (`feat/*`), Conventional Commits e Pull Requests. | Histórico de commits claro, branches documentadas e PRs revisados. |
| **7. Solução ética e explicável** | Governança CFP/LGPD, diário assíncrono (sem bot direto) e pop-up com citações literais exatas. | Documento `docs/etic-risks.md` e modal de rastreabilidade implementado na interface. |
| **8. Pelo menos 1 resource de até 2 anos** | Artigos recentes: Li et al. (arXiv 2025), McBain et al. (JAMA 2025/2026), PsychAdapter (2024/2025), ImpactBench (2025/2026). | Documento `docs/references.md` com análise crítica e data de referência validada. |
| **9. MVP funcional** | Aplicação executável ponta a ponta: ingestão do relato -> classificação neural -> agentes -> dashboard (/explore). | Comando unificado de inicialização e demonstração interativa completa. |

---

## 2. Cronograma Semanal de Desenvolvimento

```
Semana 1: Escopo, Fronteiras Clínicas e Alinhamento das 9 Constraints
Semana 2: Geração de Dados Sintéticos (PsychAdapter) & Preparação do Dataset dos 6 Temas
Semana 3: Construção, Treino e Teste da Rede Neural Simples (SBERT + MLP) + Rastreamento no MLflow
Semana 4: Implementação do Agente 1 (Decompositor de Subtemas e Ancoragem Literal)
Semana 5: Ingestão da Base de Conhecimento Clínico e Pipeline Híbrido de RAG (BM25 + e5-small)
Semana 6: Implementação do Agente 2 (Correlacionador Longitudinal) e Agente 3 (Copiloto RAG)
Semana 7: Interface do Psicólogo Inspirada no ImpactBench (/explore) com Modal Pop-up de Citações
Semana 8: Auditoria Geral de MLOps, Testes Ponta a Ponta, Gravação da Demonstração e Entrega
```

---

## 3. Critérios de Aceite para Demonstração do MVP

1. **Entrada:** Um relato sintético (texto ou áudio simulado) é submetido ao sistema.
2. **Processamento Neural:** A Rede Neural (com **SBERT**) identifica o tema correto (ex: `vinculos`) e calcula os percentuais (`%`) dos 6 temas em menos de 50 ms.
3. **Execução Multiagente:** O Agente 1 extrai os subtemas (`irmão`, `pai`) e os recortes literais exatos com índices de caracteres.
4. **Armazenamento:** O relato e os metadados são salvos no SQLite e vetorizados.
5. **Dashboard Interativo:** O psicólogo abre a tela `/explore`, clica no cartão `Vínculos`, visualiza a pílula `Irmão`, clica e o **Pop-up Modal** exibe a citação exata e a opção de ouvir o áudio.
6. **RAG Clínico:** O psicólogo solicita apoio do Copiloto, e o Agente 3 retorna orientações fundamentadas em TCC com citação expressa do ID do documento.
