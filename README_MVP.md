# 🧠 MVP: Gerador de Dataset Sintético, Rede Neural MLP e Pipeline MLOps
> **Branch de Desenvolvimento:** `feat/dataset-neural-network-mvp`  
> **Componente:** Classificação Macrotemática Clínica e Rastreamento Experimental  
> **Status da Suíte de Testes:** ✅ **161 testes aprovados (100% de sucesso)**

---

## 📋 Sumário Executivo

Este documento detalha minuciosamente todas as implementações, decisões de arquitetura e validações realizadas para os primeiros passos do MVP do projeto **Diário Psicológico Assistido & Copiloto Clínico Multiagente**.

O objetivo primordial desta etapa foi estabelecer a **primeira camada de inteligência e governança do sistema**, composta por:
1. **Síntese Ética de Dados Clínicos:** Framework de 4 personas psicológicas (*PsychAdapter / Universidade de Ulster*) cobrindo os 8 macrotemas clínicos.
2. **Classificador de Deep Learning (PyTorch):** Perceptron Multicamadas (MLP) com regularização estrita e salvaguarda matemática.
3. **Baseline Didático em NumPy Puro:** Implementação matemática do zero (cálculo diferencial, forward, backward e SGD) para comprovação acadêmica.
4. **Pipeline de MLOps & Rastreamento (MLflow):** Partição estratificada (70/15/15), curvas de perda, Macro-F1, matriz de confusão visual e versionamento de artefatos.
5. **Garantia de Qualidade:** 19 novos testes unitários e de integração com Pytest e conformidade estrita com o linter Ruff.

---

## 1. 🔍 O Que Foi Feito (What Was Done)

### A. Engenharia de Dados Sintéticos
* **`data/personas.json`:** Modelagem de 4 personas psicológicas parametrizadas pelos cinco grandes fatores de personalidade (**Big Five / OCEAN**), contendo histórico, dinâmica expressiva, estilos de vocabulário e temas preponderantes.
* **`data/synthetic_generator.py`:** Módulo de geração de relatos clínicos autênticos em língua portuguesa.
  - Cobre os **8 Macrotemas Clínicos**: `familia`, `trabalho`, `relacionamentos`, `estudos`, `saude_sono`, `financas`, `luto` e `autoestima`.
  - Cobre a **Classe de Salvaguarda**: `outros_indeterminado` (para abstenção segura de textos ambíguos ou neutros).
  - Suporta dois modos de operação: geração offline determinística (via pool combinatório de templates clínicos de alta fidelidade) e geração online via LLM local com Ollama (`qwen2.5:3b`).
* **`data/split.py`:** Utilitário determinístico para partição estratificada preservando a distribuição proporcional exata de cada macrotema.
* **`data/synthetic/synthetic_diaries.json`:** Dataset de treino e validação gerado com **360 relatos clínicos sintéticos** (40 amostras homogêneas por classe).

### B. Deep Learning e Modelagem Matemática
* **`models/torch_mlp.py` (`ClinicalThemeMLP`):**
  - Rede neural profunda em PyTorch para classificação temático-clínica.
  - Arquitetura de 3 camadas: `Entrada (1024) -> Linear(128) -> BatchNorm1d -> ReLU -> Dropout(0.3) -> Linear(64) -> ReLU -> Dropout(0.2) -> Linear(9 logits)`.
  - Método `predict_proba`: probabilidades calibradas via Softmax.
  - Método `predict`: salvaguarda matemática com fallback automático para `outros_indeterminado` (classe 8) caso a probabilidade da classe dominante seja inferior a 0.50 (50%).
* **`models/numpy_mlp.py` (`NumpyClinicalMLP`):**
  - Implementação didática do zero em NumPy puro, sem frameworks de autograd.
  - Inicialização He (Kaiming), ativação ReLU, derivada analítica, Softmax numericamente estável.
  - Retropropagação analítica da perda de Entropia Cruzada Categórica ($\frac{\partial \mathcal{L}}{\partial z_2} = \frac{p - y}{N}$) e atualização de pesos via Gradiente Descendente Estocástico (SGD).

### C. MLOps e Rastreamento Experimental
* **`mlops/tracker.py` (`MLFlowTracker`):**
  - Encapsulamento centralizado para sessões de experimentos no MLflow utilizando backend SQLite (`sqlite:///mlflow.db`).
  - Rastreamento estruturado de hiperparâmetros, perdas por época, Macro-F1 de validação e teste.
  - Geração e logging de artefatos visuais: matriz de confusão em JSON e imagem PNG com heatmap anotado.
* **`models/train.py`:**
  - Pipeline de ponta a ponta: carregamento de dados -> divisão estratificada 70/15/15 -> vetorização TF-IDF (1.024 features, n-grams 1-2) -> treinamento com otimizador AdamW -> Early Stopping/Melhor Checkpoint no Macro-F1 -> avaliação cega no conjunto Holdout -> exportação de pesos e transformadores para o diretório `dist/`.

### D. Infraestrutura e Testes Automatizados
* **19 Novos Testes Automatizados:**
  - `tests/test_personas_and_generator.py` (6 testes)
  - `tests/test_torch_mlp.py` (5 testes)
  - `tests/test_numpy_mlp.py` (4 testes)
  - `tests/test_train_pipeline.py` (4 testes)
* **Total da Suíte:** **161 testes passando sem erros** (142 pré-existentes + 19 novos).
* **Configuração:** Atualização de `pyproject.toml` e `.gitignore` para empacotamento formal e exclusão de bancos/artefatos locais voláteis.

---

## 2. ⚙️ Como Foi Feito (How It Was Done)

### Arquitetura da Rede Neural (PyTorch MLP)

```
[ Relato Textual do Diário ]
             │
             ▼
[ TF-IDF Vectorizer (max_features = 1024, ngram_range = (1, 2)) ]
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ Camada 1: Linear(1024 -> 128)                          │
│ Normalização: BatchNorm1d(128)                         │
│ Ativação: ReLU(x) = max(0, x)                          │
│ Regularização: Dropout(taxa = 0.3)                     │
└────────────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ Camada 2: Linear(128 -> 64)                            │
│ Ativação: ReLU(x) = max(0, x)                          │
│ Regularização: Dropout(taxa = 0.2)                     │
└────────────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ Camada 3: Linear(64 -> 9 classes)                      │
│ Saída: Logits não normalizados (para CrossEntropyLoss) │
└────────────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ Inferência: Softmax P(Tema_i | x)                      │
│ Salvaguarda: Se max(P) < 0.50 => 'outros_indeterminado'│
└────────────────────────────────────────────────────────┘
```

### Formulação Matemática do Baseline em NumPy Puro

Para atender aos requisitos de explicabilidade matemática, a classe `NumpyClinicalMLP` implementa o cálculo diferencial explícito:

1. **Propagação Direta (Forward Pass):**
   $$z_1 = X \cdot W_1 + b_1$$
   $$a_1 = \max(0, z_1) \quad (\text{ReLU})$$
   $$z_2 = a_1 \cdot W_2 + b_2$$
   $$\hat{y}_i = \frac{e^{z_{2,i} - \max(z_2)}}{\sum_j e^{z_{2,j} - \max(z_2)}} \quad (\text{Softmax estável})$$

2. **Função de Custo (Cross-Entropy Loss):**
   $$\mathcal{L} = -\frac{1}{N} \sum_{n=1}^{N} \sum_{c=1}^{C} y_{n,c} \log(\hat{y}_{n,c} + \epsilon)$$

3. **Retropropagação do Gradiente (Backward Pass):**
   $$\frac{\partial \mathcal{L}}{\partial z_2} = \frac{\hat{y} - y}{N}$$
   $$\frac{\partial \mathcal{L}}{\partial W_2} = a_1^T \cdot \frac{\partial \mathcal{L}}{\partial z_2}, \quad \frac{\partial \mathcal{L}}{\partial b_2} = \sum \frac{\partial \mathcal{L}}{\partial z_2}$$
   $$\frac{\partial \mathcal{L}}{\partial a_1} = \frac{\partial \mathcal{L}}{\partial z_2} \cdot W_2^T$$
   $$\frac{\partial \mathcal{L}}{\partial z_1} = \frac{\partial \mathcal{L}}{\partial a_1} \odot \mathbb{I}(z_1 > 0) \quad (\text{Derivada da ReLU})$$
   $$\frac{\partial \mathcal{L}}{\partial W_1} = X^T \cdot \frac{\partial \mathcal{L}}{\partial z_1}, \quad \frac{\partial \mathcal{L}}{\partial b_1} = \sum \frac{\partial \mathcal{L}}{\partial z_1}$$

### Ciclo de MLOps no MLflow

```
[ Dataset Sintético (360 amostras) ]
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ Divisão Estratificada Determinística (Seed: 42)        │
│ ├─ 70% Treino (252 amostras)                           │
│ ├─ 15% Validação (54 amostras)                         │
│ └─ 15% Teste Holdout Cego (54 amostras)                │
└────────────────────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ Treinamento & Validação (AdamW, lr=1e-3, epochs=40)    │
│ ├─ Registro de parâmetros (arquitetura, lr, splits)    │
│ ├─ Log step-by-step: train_loss, val_loss, val_macro_f1│
│ └─ Checkpoint automático do melhor modelo              │
└────────────────────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ Avaliação Cega Final (Holdout Test)                    │
│ ├─ Test Macro-F1 (0.9814) e Test Accuracy (0.9815)     │
│ ├─ Matriz de Confusão (JSON + Heatmap PNG)             │
│ └─ Registro de Artefatos no MLflow                     │
│    ('best_theme_mlp.pt' + 'tfidf_vectorizer.joblib')   │
└────────────────────────────────────────────────────────┘
```

---

## 3. 🎯 Por Que Foi Feito (Why It Was Done)

As implementações foram concebidas para satisfazer diretamente e integralmente as **Constraints do Challenge 2**:

| Restrição do Edital | Como Nosso MVP Cumpre |
| :--- | :--- |
| **Constraint 7: Ética e Explicabilidade** | **Privacidade Absoluta (LGPD e Código de Ética do CFP):** É vedado o uso de dados de pacientes reais sem comitê de ética (CEP/CONEP). O uso do gerador sintético baseado no framework **PsychAdapter** assegura dados com validade clínica e verossimilhança sem violar direitos de privacidade. |
| **Constraint 8: Recursos com até 2 anos** | Adota a metodologia do **PsychAdapter** (*Nature Portfolio / npj AI & arXiv, 2024/2025*) e pesquisas da **Universidade de Ulster** (*Using LLMs in Simulated Mental Health Assessment, 2024–2026*). |
| **Constraint 4: Construir e testar pelo menos uma rede neural simples** | Implementamos uma **Rede Neural MLP própria dedicada**, sem depender de APIs externas para a macroclassificação. Criamos a versão de produção em **PyTorch** e o baseline didático demonstrativo em **NumPy puro**. |
| **Constraint 3: Aplicar MLOps** | Rastreamento determinístico, logging de curvas de aprendizado, matriz de confusão e métrica **Macro-F1** no **MLflow**, com controle estrito de dependências via `uv.lock`. |
| **Constraint 6: Versionamento de Código** | Ciclo de vida profissional com branch dedicada `feat/dataset-neural-network-mvp`, testes de regressão antes do merge e commits semânticos rastreáveis. |

---

## 4. 🚀 Como Executar e Validar

### 1. Sincronizar o Ambiente
```bash
uv sync --frozen
```

### 2. Gerar Novos Relatos Sintéticos (Opcional)
```bash
# Geração offline ultrarrápida:
uv run python -m data.synthetic_generator --samples-per-theme 40 --output data/synthetic/synthetic_diaries.json

# Ou geração via Ollama local (se o serviço estiver ativo):
uv run python -m data.synthetic_generator --ollama --samples-per-theme 40
```

### 3. Executar o Treinamento da Rede Neural com MLflow
```bash
uv run python -m models.train --epochs 40 --batch-size 32 --lr 0.001
```
*Saída gerada no console:*
```text
[INFO] Divisão dos dados: Treino=252, Validação=54, Teste Holdout=54
[INFO] Artefato registrado no MLflow: dist\confusion_matrix.json
[INFO] Artefato registrado no MLflow: dist\confusion_matrix.png
[INFO] Artefato registrado no MLflow: dist\classification_report.json
[INFO] Artefato registrado no MLflow: dist\theme_classes.json
[INFO] Artefato registrado no MLflow: dist\best_theme_mlp.pt
[INFO] Artefato registrado no MLflow: dist\tfidf_vectorizer.joblib
[INFO] Treinamento Concluído! Test Macro-F1: 0.9814 | Test Acc: 0.9815 | Run ID: ...
```

### 4. Abrir a Interface Visual do MLflow
```bash
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```
Abra o navegador em `http://127.0.0.1:5000` para inspecionar gráficos de perda, hiperparâmetros e baixar a matriz de confusão PNG.

### 5. Executar os Testes Automatizados e Linter
```bash
# Executa todos os 161 testes:
uv run pytest -v

# Executa apenas a nova suíte do MVP:
uv run pytest tests/test_personas_and_generator.py tests/test_torch_mlp.py tests/test_numpy_mlp.py tests/test_train_pipeline.py -v

# Validação do linter e formatação:
uv run ruff check .
uv run ruff format --check .
```

---

## 5. 📂 Mapeamento de Arquivos Criados

| Arquivo | Finalidade Principal |
| :--- | :--- |
| [**`data/personas.json`**](file:///data/personas.json) | Especificação das 4 personas clínicas (Big Five / OCEAN). |
| [**`data/synthetic_generator.py`**](file:///data/synthetic_generator.py) | Gerador de dataset sintético dos 8 macrotemas + salvaguarda (offline/Ollama). |
| [**`data/split.py`**](file:///data/split.py) | Script de divisão estratificada (70% treino, 15% validação, 15% holdout). |
| [**`models/torch_mlp.py`**](file:///models/torch_mlp.py) | Rede Neural MLP em PyTorch com Softmax e salvaguarda de abstenção matemática. |
| [**`models/numpy_mlp.py`**](file:///models/numpy_mlp.py) | Baseline didático em NumPy puro com cálculo explícito do gradiente. |
| [**`models/train.py`**](file:///models/train.py) | Pipeline de treino, checkpointing, avaliação cega e salvamento de artefatos. |
| [**`mlops/tracker.py`**](file:///mlops/tracker.py) | Rastreamento de métricas, hiperparâmetros e artefatos no MLflow. |
| [**`tests/test_personas_and_generator.py`**](file:///tests/test_personas_and_generator.py) | Testes unitários do gerador sintético e partição estratificada. |
| [**`tests/test_torch_mlp.py`**](file:///tests/test_torch_mlp.py) | Testes unitários da rede PyTorch e mecanismo de salvaguarda. |
| [**`tests/test_numpy_mlp.py`**](file:///tests/test_numpy_mlp.py) | Testes unitários da formulação analítica em NumPy puro. |
| [**`tests/test_train_pipeline.py`**](file:///tests/test_train_pipeline.py) | Testes de integração do pipeline de treino e MLflow. |
| [**`dist/`**](file:///dist/) | Diretório contendo os artefatos gerados (`.pt`, `.joblib`, `.json`, `.png`). |
