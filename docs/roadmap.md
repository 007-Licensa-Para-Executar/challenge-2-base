# Roteiro de Execução do MVP e Atendimento às Restrições

Este cronograma orienta o desenvolvimento do **Diário Clínico Assistido & Copiloto Psicológico**, cobrindo o ciclo de 8 semanas de entrega acadêmica e técnica, garantindo que as **9 Constraints** sejam cumpridas de forma verificável.

---

## 1. Matriz de Atendimento às 9 Constraints do Desafio

| Restrição (Constraint) | Componente Técnico Responsável | Evidência Comprovável |
| :--- | :--- | :--- |
| **1. Ter pelo menos 2 agentes que trabalhem juntos** | Arquitetura consolidada com Agente 1 (Extrator) e Agente 2 (Analista Longitudinal e Copiloto RAG). | Testes de integração demonstrando passagem de dados estruturados entre os dois agentes. |
| **2. Ter uma base de conhecimento** | Base tripartite planejada: diretrizes clínicas autorizadas, histórico do paciente e regras do sistema. | BM25 demonstrado em dados sintéticos; índice clínico vetorial persistente permanece a definir. |
| **3. Aplicar MLOps** | Pipeline em `mlops/`, lock do `uv`, CI e MLflow em SQLite com artefatos ao lado do banco. | `uv run bem-estar-mlops`, tag `promoted`, matriz de confusão e registry só após o gate de F1 macro. Ver `docs/mlops.md`. |
| **4. Construir e testar rede neural simples** | Rede Neural MLP (PyTorch e NumPy puro) alimentada por embeddings densos **SBERT** para identificar os **6 temas** (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`) e atribuir seus percentuais (`%`), comparada a um baseline de classe mais frequente. | `models/sbert_embedder.py`, `models/torch_mlp.py`, `models/numpy_mlp.py`, `models/train.py`, `models/predictor.py` e suíte `tests/test_*mlp*.py`. |
| **5. Utilizar API por meio dos agentes** | API local Ollama e API HTTP local de pseudonimização. Transcrição e busca vetorial são integrações futuras ou opcionais. | Clientes HTTP tipados com timeout, erro sanitizado e testes controlados. |
| **6. Ferramenta de versionamento de código** | Repositório Git com branches temáticas (`feat/*`), Conventional Commits e Pull Requests. | Histórico de commits claro, branches documentadas e PRs revisados. |
| **7. Solução ética e explicável** | Governança CFP/LGPD, diário assíncrono e rastreabilidade por citações literais. | Documentos de risco e pseudonimização; a interface visual permanece especificação. |
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
Semana 6: Implementação do Agente 2 (Análise Longitudinal e Copiloto RAG)
Semana 7: Interface do Psicólogo Inspirada no ImpactBench (/explore) com Modal Pop-up de Citações
Semana 8: Auditoria Geral de MLOps, Testes Ponta a Ponta, Gravação da Demonstração e Entrega
```

---

## 3. Critérios de Aceite para Demonstração do MVP

1. **Entrada:** Um relato sintético (texto ou áudio simulado) é submetido ao sistema.
2. **Processamento Neural:** A Rede Neural (com **SBERT**) identifica o tema predominante (ex: `vinculos`) e calcula os percentuais (`%`) dos 6 temas sem apresentar o resultado como diagnóstico; latência deve ser medida no ambiente declarado.
3. **Execução Multiagente:** O Agente 1 extrai os subtemas (`irmão`, `pai`) e os recortes literais exatos com índices de caracteres.
4. **Armazenamento:** o relato e os metadados são salvos no SQLite; índice vetorial persistente não é pré-requisito desta demonstração.
5. **Dashboard Interativo:** a interface `/explore` pode ser demonstrada apenas após implementação; a especificação atual não deve ser apresentada como tela disponível.
6. **RAG Clínico:** O psicólogo solicita apoio ao Agente 2, e o copiloto retorna informações fundamentadas em fontes autorizadas com citação expressa do documento e seção.

## 4. Desafios de Evolução e Validação

Os próximos marcos de pesquisa devem ser separados das entregas já implementadas:

1. **Integração longitudinal ponta a ponta:** acompanhar o paciente ao longo de sessões sem promover diagnóstico, prognóstico ou tratamento automático.
2. **Sintomas evolutivos e comorbidades:** testar mudanças temporais e diferentes quadros sem assumir causalidade ou confundir estados clínicos distintos.
3. **Dados culturalmente nativos:** aumentar o corpus em português por coleta ou produção culturalmente contextualizada, reduzindo tradução direta do inglês e dependência de modelos fechados.
4. **Diversidade clínica:** ampliar avaliação além de depressão e ansiedade e revisar referências de abordagens como DBT e terapia humanista, sem apresentar qualquer terapia como conduta automática.
