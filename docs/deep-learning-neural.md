# 06 - Rede Neural e Deep Learning: Classificação dos 6 Temas Clínicos com SBERT

## 1. Objetivo e Papel no Ecossistema

O componente de **Deep Learning** atende diretamente à **Restrição 4 (Construir e testar pelo menos uma rede neural simples)** e fundamenta a primeira camada de inteligência do sistema.

### Definição do Escopo
A rede neural tem a responsabilidade de realizar o primeiro nível de compreensão semântica dos diários dos pacientes: **receber o diário, identificar os temas entre as 6 categorias clínicas definidas em [`data/taxonomy.py`](../data/taxonomy.py) e atribuir percentuais (`%`) para cada um deles**, fornecendo a distribuição temática e as probabilidades preditivas para o **Agente 1 (Decompositor de Subtemas)** e para o painel do psicólogo.

Ao desacoplar a classificação temática (feita pela Rede Neural dedicada sobre embeddings SBERT) da extração de subtemas contextuais (feita pelo Agente 1 com LLM), o projeto atinge:
1. **Baixa Latência e Semântica Contextual:** Os embeddings **SBERT** (`SBERTEmbedder`) capturam significado contextual em português mesmo quando o paciente usa paráfrases ou linguagem coloquial, e a MLP classifica o relato em milissegundos localmente.
2. **Distribuição Percentual e Calibração:** A rede retorna uma distribuição percentual via Softmax calibrada (Temperature Scaling), somando 100% entre os 6 temas, além de permitir cálculo de composição por sentenças em `destrinchar_diario()` e regra de abstenção matemática ($\tau = 0.50$).
3. **Cumprimento do Requisito Acadêmico:** Construção, treino, teste e métricas reais de Deep Learning independentes de LLMs generativos de terceiros.

---

## 2. Os 6 Temas Clínicos (Taxonomia Única)

Consolidados em [`data/taxonomy.py`](../data/taxonomy.py) para unificar o dataset real anonimizado, o gerador sintético, a rede neural e os agentes, utilizamos exclusivamente **6 temas**:

1. **`autopercepcao` (Autopercepção):** Autoestima, identidade, imagem corporal e sensação de incapacidade ou inadequação.
2. **`vinculos` (Vínculos):** Relacionamentos amorosos, amizades, família, términos, traições e separações.
3. **`desempenho` (Desempenho):** Trabalho, estudos e finanças (cobranças, metas, provas, dívidas).
4. **`fisico` (Físico):** Saúde física e mental em sintomas, sono, tratamento médico, dores e sonhos.
5. **`rupturas` (Rupturas):** Perdas por morte e luto.
6. **`outros` (Outros):** Sem tema clínico claro, relato neutro ou **classe de salvaguarda/abstenção** quando a confiança máxima da rede fica abaixo do limiar operacional ($\tau = 0.50$).

---

## 3. Arquitetura da Rede Neural (SBERT + Multi-Layer Perceptron - MLP)

A rede utiliza representações densas de sentença geradas por **SBERT** (substituindo a vetorização esparsa baseada em TF-IDF) como entrada para um Perceptron Multicamadas (MLP) regularizado:

```
[ Diário do Paciente (Entrada Textual) ]
        │
        ▼
[ Vetorização Semântica: SBERTEmbedder (paraphrase-multilingual-MiniLM-L12-v2, dim=384, normalizado L2) ]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada Oculta 1: Linear(384, 128)                      │
│ Batch Normalization 1D / LayerNorm / RMSNorm           │
│ Ativação: ReLU                                         │
│ Regularização: Dropout (p = 0.3)                       │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada Oculta 2: Linear(128, 64)                       │
│ Ativação: ReLU                                         │
│ Regularização: Dropout (p = 0.2)                       │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada de Saída: Linear(64, 6 classes)                 │
│ Calibração: Temperature Scaling (z / T)                │
│ Ativação de Inferência: Softmax                        │
└────────────────────────────────────────────────────────┘
        │
        ▼
[ Percentuais (%) para Autopercepção, Vínculos, Desempenho, Físico, Rupturas e Outros ]
```

### Especificação Matemática da Rede
- **Codificação de Entrada (SBERT Congelado):**
  $$x = \frac{\text{SBERT}(\text{diário})}{\|\text{SBERT}(\text{diário})\|_2} \in \mathbb{R}^{384}$$
- **Passagem Direta (Forward):**
  $$z_1 = W_1 x + b_1$$
  $$h_1 = \text{ReLU}(\text{Norm}(z_1))$$
  $$\tilde{h}_1 = \text{Dropout}(h_1, p=0.3)$$
  $$z_2 = W_2 \tilde{h}_1 + b_2$$
  $$h_2 = \text{ReLU}(z_2)$$
  $$\tilde{h}_2 = \text{Dropout}(h_2, p=0.2)$$
  $$\hat{y}_{\text{logits}} = W_3 \tilde{h}_2 + b_3$$
  $$P(y = c \mid x) = \frac{e^{\hat{y}_c / T}}{\sum_{j=1}^{6} e^{\hat{y}_j / T}}, \quad \%_c = P(y = c \mid x) \times 100$$

- **Função de Custo (Loss):** Entropia Cruzada Categórica (*Cross-Entropy Loss*):
  $$\mathcal{L} = - \sum_{c=1}^{6} y_c \log(P(y = c \mid x))$$

- **Otimizador:** AdamW ($\text{lr} = 5 \times 10^{-3}$, $\beta_1 = 0.9, \beta_2 = 0.999$, weight decay $= 10^{-3}$).

---

## 4. Pipeline de Treino, Validação e MLOps

### Preparação do Dataset e Prevenção de Vazamento
O treinamento combina relatos reais anonimizados em português (`data/real_diaries.json`) e relatos sintéticos parametrizados (`data/synthetic/synthetic_diaries.json`), todos padronizados na taxonomia de **6 temas** via [`data/taxonomy.py`](../data/taxonomy.py):
- **Divisão Estratificada por Grupos (`data/split.py`):** Aproximadamente **70% Treino**, **15% Validação**, **15% Teste Holdout Cego**, garantindo que famílias de origem e templates semelhantes não atravessem os conjuntos.
- **Encoder Congelado:** O `SBERTEmbedder` não é treinado nem ajustado nos dados do projeto, eliminando vazamento entre os splits.

### Critérios de Seleção e Métricas
- **Seleção de Checkpoint:** Escolha exclusiva pelo melhor **Macro-F1** no conjunto de **validação**.
- **Métricas Registradas no MLflow:**
  - Macro-F1 (métrica primária de decisão) com política de abstenção ($\tau = 0.50$) e por *argmax* direto.
  - Acurácia global, perda de treino/validação/teste e Erro de Calibração Esperado (ECE antes e após *Temperature Scaling*).
  - Precisão, Recall e F1-Score por tema (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`).
  - Matriz de Confusão salva como artefato visual.

### Baseline Didático em NumPy vs. Módulo PyTorch
- **Baseline em NumPy Puro:** Para demonstrar domínio conceitual dos algoritmos de backpropagation e cálculo analítico de gradientes (atendendo ao checklist didático do projeto), o repositório disponibiliza a versão vetorizada em NumPy puro (`models/numpy_mlp.py`), também alimentada pelos embeddings SBERT de 384 dimensões.
- **Módulo de Produção em PyTorch:** Suporte a normalização modular, calibração por *Temperature Scaling*, abstenção segura e integração completa com MLflow (`models/torch_mlp.py` e `models/train.py`).

---

## 5. Viabilização Arquitetural: MLPs vs. Modelos Sequenciais (RNNs, LSTMs, GRUs)

Para processamento de relatos clínicos, o ecossistema disponibiliza tanto o MLP sobre embeddings densos SBERT quanto modelos sequenciais de referência (`models/torch_mlp.py`):

| Arquitetura | Mecanismo Central | Ponto Forte no Projeto | Quando Utilizar |
| :--- | :--- | :--- | :--- |
| **SBERT + MLP (`ClinicalThemeMLP`)** | Encoder SBERT congelado (384d) + camadas densas lineares | Alta compreensão semântica contextual em português, determinístico, baixa latência na inferência | **Padrão Atual:** Receber o diário, identificar o tema e gerar os percentuais (`%`) para os 6 temas. |
| **Simple RNN (`ClinicalSequentialClassifier`)** | Estado oculto recorrente: $h_t = \text{ReLU}(W x_t + U h_{t-1} + b)$ | Captura ordem temporal de palavras com poucos parâmetros | Textos curtos e didática de dependência temporal básica. |
| **LSTM (Long Short-Term Memory)** | Células com portões de esquecimento (*forget*), entrada (*input*) e saída (*output*) | Resolve dependências de longo prazo e mitiga vanishing gradients | Relatos longos onde o contexto do início do diário altera o sentido clínico do final. |
| **GRU (Gated Recurrent Unit)** | Portões de atualização (*update*) e reinício (*reset*) | Convergência mais rápida que LSTM com desempenho equivalente | Cenários com menor volume de dados ou restrição de memória/latência. |

---

## 6. Técnicas de Normalização: BatchNorm vs. LayerNorm vs. RMSNorm

1. **Batch Normalization (`BatchNorm1d`):** Normaliza ao longo do lote ($\hat{x} = \frac{x - \mu_B}{\sqrt{\sigma^2_B + \epsilon}} \gamma + \beta$). Ideal para o MLP em lotes $\ge 16$.
2. **Layer Normalization (`LayerNorm`):** Normaliza ao longo das *features* de cada amostra individualmente. Padrão em NLP e modelos sequenciais (RNN/LSTM/GRU/Transformers) por independer do tamanho do lote.
3. **RMSNorm (`RMSNorm`):** Normaliza pela raiz quadrática média ($\text{RMS}(x) = \sqrt{\frac{1}{d} \sum x_i^2 + \epsilon}$) sem subtrair a média, reduzindo custo computacional com mesma estabilidade numérica.

---

## 7. Diagnóstico e Resolução de Vanishing e Exploding Gradients

- **Vanishing Gradients:** *Diagnóstico:* Loss estagnada e $||\nabla W_1|| < 10^{-6}$. *Resolução:* Ativações não saturantes (ReLU), inicialização He/Kaiming ($W \sim \mathcal{N}(0, \sqrt{2/d_{\text{in}}})$), normalização (BatchNorm/LayerNorm/RMSNorm) e gates aditivos (LSTM/GRU).
- **Exploding Gradients:** *Diagnóstico:* Loss `NaN`/`Inf` ou saltos bruscos. *Resolução:* **Gradient Clipping** (`torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)`) ativo no loop de treino (`models/train.py`).

---

## 8. Quando Usar MSE, MAE, Binary Cross-Entropy e Categorical Cross-Entropy

| Função de Perda | Problema | Quando Usar no Projeto |
| :--- | :--- | :--- |
| **Categorical Cross-Entropy (CCE)** | Multiclasse mutuamente exclusiva (soma Softmax = 100%) | **Adotada nos 6 temas (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`).** |
| **Binary Cross-Entropy (BCE)** | Binária ou Multirrótulo independente (Sigmoid por classe) | Triagem binária de risco ou múltiplos temas simultâneos independentes. |
| **MSE (Mean Squared Error)** | Regressão contínua ($\frac{1}{N}\sum (y - \hat{y})^2$) | Predição de escores contínuos (ex.: PHQ-9) penalizando desvios grandes. |
| **MAE (Mean Absolute Error)** | Regressão robusta ($\frac{1}{N}\sum \|y - \hat{y}\|$) | Estimativas contínuas na presença de *outliers* severos. |
