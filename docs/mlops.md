# 07 - MLOps: Rastreabilidade, Automação e Ciclo de Vida dos Modelos

## 1. Visão Geral e Atendimento às Restrições

Este documento formaliza as práticas de engenharia de software e operações de aprendizado de máquina para atender integralmente ao **Requisito 3 (Aplicar MLOps)** e **Requisito 6 (Utilizar ferramenta de versionamento de código)**.

O objetivo do nosso pipeline de MLOps é garantir que todo experimento de modelagem neural, versão de prompt de agente e ingestão na base de conhecimento seja estritamente **reprodutível, rastreável e auditável**.

---

## 2. Componentes Estruturais do Pipeline de MLOps

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               PIPELINE DE MLOPS                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
         │
         ├─► [ 1. Versionamento & CI/CD ]
         │     • Git / GitHub: Branches 'feat/*', 'fix/*', PRs com revisão
         │     • GitHub Actions: Linter Ruff + Suíte de Testes Pytest
         │     • uv: Bloqueio estrito de dependências via 'uv.lock'
         │
         ├─► [ 2. Rastreamento de Experimentos (MLflow) ]
         │     • Logging de hiperparâmetros (learning rate, batch size, dropout)
         │     • Métricas em tempo real (train/val loss, Macro-F1, Confusion Matrix)
         │     • Registro de artefatos (.pt, .joblib, classification_report.json)
         │
         ├─► [ 3. Governança de Prompts e Schemas ]
         │     • Hash do digest dos modelos locais (Ollama Qwen/Gemma)
         │     • Versionamento semântico de contratos Pydantic (SCHEMA_VERSION)
         │     • Versionamento de templates de prompts (PROMPT_VERSION)
         │
         └─► [ 4. Avaliação Contínua e Detecção de Drift ]
               • Holdout set cego para validação de integridade
               • Monitoramento de taxas de abstenção e latência P95
```

---

## 3. Rastreamento de Experimentos com MLflow

Para monitorar o treinamento da Rede Neural MLP dos 8 temas clínicos, utilizamos o **MLflow** integrado ao banco local SQLite (`mlflow.db`):

### Parâmetros Rastreados (Params)
- `model_architecture`: MLP-128-64-9
- `feature_extractor`: `TF-IDF-1024` ou `e5-small-dense`
- `learning_rate`: $10^{-3}$
- `batch_size`: 32
- `dropout_rate`: 0.3
- `optimizer`: `AdamW`
- `weight_decay`: $10^{-4}$
- `seed`: 42

### Métricas Monitoradas por Época (Metrics)
- `train_loss` e `val_loss` (curva de convergência para detectar overfitting)
- `val_accuracy`
- `val_macro_f1`
- `top2_accuracy`

### Artefatos Versionados (Artifacts)
- Pesos serializados do modelo (`best_model.pt`)
- Vetorizador ajustado (`tfidf_vectorizer.joblib`)
- Gráfico da Matriz de Confusão (`confusion_matrix.png`)
- Relatório analítico completo por classe (`classification_report.json`)

---

## 4. Governança de Código, CI/CD e Reprodutibilidade

### Gerenciamento de Ambiente com `uv`
- Todas as dependências e sub-dependências estão trancadas deterministicamente no arquivo `uv.lock`.
- Um desenvolvedor pode clonar o repositório em máquina limpa e restaurar com um único comando:
  ```bash
  uv sync --frozen
  ```

### Integração Contínua (CI) via GitHub Actions
O arquivo `.github/workflows/ci.yml` executa automaticamente a cada push ou pull request:
1. **Verificação Estática de Código:**
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   ```
2. **Execução de Testes Automatizados:**
   ```bash
   uv run pytest -v --cov=app --cov=agents --cov=models
   ```
3. **Bloqueio de Merge:** Nenhum código é integrado à branch principal (`main`) se houver quebra de testes ou regressão no linter.

---

## 5. Versionamento de Contratos de Dados e Prompts

Para impedir desalinhamento entre o que os agentes produzem e o que a interface exibe, todas as chamadas de inferência salvam os seguintes metadados nos logs:
- `SCHEMA_VERSION`: Versão do contrato Pydantic dos agentes (ex: `1.1.0`).
- `PROMPT_VERSION`: Versão do template de prompt utilizado (ex: `1.0.0`).
- `MODEL_DIGEST`: Hash SHA-256 do peso do modelo local do Ollama, garantindo que alterações silenciosas no modelo base sejam detectadas.
