# 06 - Rede Neural e Deep Learning: Classificação dos 8 Temas Clínicos

## 1. Objetivo e Papel no Ecossistema

O componente de **Deep Learning** atende diretamente à **Restrição 4 (Construir e testar pelo menos uma rede neural simples)** e fundamenta a primeira camada de inteligência do sistema.

### Definição do Escopo
A rede neural tem a responsabilidade de realizar o primeiro nível de compreensão semântica dos diários dos pacientes: **classificar cada relato entre os 8 Temas Clínicos Padrão**, fornecendo as probabilidades preditivas para o **Agente 1 (Decompositor de Subtemas)**.

Ao desacoplar a classificação macrotemática (feita pela Rede Neural dedicada) da extração de subtemas contextuais (feita pelo Agente 1 com LLM), o projeto atinge:
1. **Velocidade e Baixa Latência:** A inferência neural roda em milissegundos localmente.
2. **Determinismo e Calibração de Probabilidades:** A rede retorna distribuições de probabilidade reais via Softmax/Sigmoid, permitindo limiares de corte e abstenção matemática.
3. **Cumprimento do Requisito Acadêmico:** Construção, treino, teste e métricas reais de Deep Learning independentes de LLMs de terceiros.

---

## 2. Os 8 Temas Clínicos Padrão (Macrotemas)

Baseados na literatura clássica de psicologia clínica (Terapia Cognitivo-Comportamental de Beck, domínios de funcionamento do DSM-5-TR e eixos do MIT ImpactBench), foram definidos 8 temas estruturantes mais uma classe de salvaguarda:

1. **`familia` (Dinâmicas Familiares):** Relações com pais, irmãos, cônjuge, convivência domiciliar, disputas ou apoio familiar.
2. **`trabalho` (Carreira e Ambiente Laboral):** Sobrecarga de tarefas, relação com lideranças e pares, medo de demissão, síndrome de burnout.
3. **`relacionamentos` (Vida Afetiva e Relações Sociais):** Namoro, casamento, amizades, solidão, rompimentos afetivos, pertencimento a grupos.
4. **`estudos` (Vida Acadêmica e Formação):** Provas, faculdade, prazos escolares, desempenho cognitivo, ansiedade de vestibular/concurso.
5. **`saude_sono` (Saúde Física, Sono e Rotina Somática):** Qualidade do sono, insônia, fadiga física crônica, queixas somáticas de ansiedade, hábitos alimentares.
6. **`financas` (Segurança Material e Gestão Financeira):** Dívidas, aperto orçamentário, ansiedade com sobrevivência material, insegurança econômica familiar.
7. **`luto` (Luto, Perdas e Transições Abruptas):** Falecimento de pessoas próximas, separações dolorosas, perdas de status de vida, processos de despedida.
8. **`autoestima` (Autoimagem, Identidade e Valor Pessoal):** Autocrítica excessiva, sentimento de insuficiência, percepção corporal, crises existenciais de identidade.
9. **`outros_indeterminado` (Classe de Abstenção):** Textos ambíguos, incoerentes ou fora do domínio clínico coberto.

---

## 3. Arquitetura da Rede Neural (Multi-Layer Perceptron - MLP)

A rede é concebida como um Perceptron Multicamadas (MLP) com regularização estrita para evitar overfitting em dados textuais de vocabulário sensível:

```
[ Entrada Textual ]
        │
        ▼
[ Vetorização: TF-IDF n-grams (dim=512 a 1024) ou Dense Embeddings (dim=384) ]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada Oculta 1: Linear(in_features, 128)               │
│ Batch Normalization 1D                                 │
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
│ Camada de Saída: Linear(64, 9 classes)                 │
│ Ativação de Inferência: Softmax (Multiclasse exclusiva)│
│                     ou Sigmoid (Multirrótulo)          │
└────────────────────────────────────────────────────────┘
        │
        ▼
[ Distribuição de Probabilidades P(Tema_i) ]
```

### Especificação Matemática da Rede
- **Passagem Direta (Forward):**
  $$z_1 = W_1 x + b_1$$
  $$h_1 = \text{ReLU}(\text{BatchNorm}(z_1))$$
  $$\tilde{h}_1 = \text{Dropout}(h_1, p=0.3)$$
  $$z_2 = W_2 \tilde{h}_1 + b_2$$
  $$h_2 = \text{ReLU}(z_2)$$
  $$\tilde{h}_2 = \text{Dropout}(h_2, p=0.2)$$
  $$\hat{y}_{\text{logits}} = W_3 \tilde{h}_2 + b_3$$
  $$P(y = c | x) = \frac{e^{\hat{y}_c}}{\sum_{j=1}^{C} e^{\hat{y}_j}}$$

- **Função de Custo (Loss):** Entropia Cruzada Ponderada (*Weighted Cross-Entropy Loss*) para compensar eventuais desbalanceamentos entre classes raras (ex: Luto vs. Trabalho):
  $$\mathcal{L} = - \sum_{c=1}^{C} w_c \cdot y_c \log(P(y = c | x))$$

- **Otimizador:** AdamW ($\text{lr} = 10^{-3}$, $\beta_1 = 0.9, \beta_2 = 0.999$, weight decay $= 10^{-4}$).

---

## 4. Pipeline de Treino, Validação e MLOps

### Preparação do Dataset Sintético
Diários de pacientes reais envolvem sigilo médico e proteção de dados sensíveis (LGPD / HIPAA). Portanto, o treinamento e a validação são conduzidos utilizando datasets sintéticos gerados segundo a metodologia do **PsychAdapter** (Nature/arXiv 2024/2025) e simulações clínicas da **Universidade de Ulster** (2025):
- Geração de 500 a 1.000 relatos sintéticos parametrizados por personas e traços psicológicos.
- Divisão Estratificada: **70% Treino**, **15% Validação**, **15% Teste Holdout Cego**.

### Critérios de Parada e Métricas
- **Early Stopping:** Monitoramento da perda de validação com paciência (*patience*) de 10 épocas para mitigar overfitting.
- **Métricas Registradas no MLflow:**
  - Macro-F1 (métrica primária de decisão).
  - Acurácia global e Top-2 Accuracy.
  - Precisão e Recall por classe temática.
  - Matriz de Confusão salva como artefato visual.

### Baseline Didático em NumPy vs. Módulo PyTorch
- **Baseline em NumPy Puro:** Para demonstrar domínio conceitual dos algoritmos de backpropagation e cálculo analítico de gradientes (atendendo ao checklist didático do projeto), a biblioteca disponibiliza a versão vetorizada em NumPy puro (`models/numpy_mlp.py`).
- **Módulo de Produção em PyTorch:** Para integração escalável no MVP, integração com GPU/MPS e suporte ao pipeline do MLflow (`models/torch_mlp.py`).

---

## 5. Viabilização Arquitetural: MLPs vs. Modelos Sequenciais (RNNs, LSTMs, GRUs)

Para processamento de relatos clínicos, o ecossistema disponibiliza tanto modelos baseados em vetores densos/esparsos quanto processadores de sequências temporais de texto (`models/torch_mlp.py`):

| Arquitetura | Mecanismo Central | Ponto Forte no Projeto | Quando Utilizar |
| :--- | :--- | :--- | :--- |
| **MLP (`ClinicalThemeMLP`)** | Camadas densas lineares + `EmbeddingBag` / Embeddings médios | Ultrarrápido (< 5ms), determinístico, baixa latência | **Padrão do MVP:** Classificar o tema dominante do diário a partir do vocabulário e embeddings. |
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
| **Categorical Cross-Entropy (CCE)** | Multiclasse mutuamente exclusiva (soma Softmax = 100%) | **Adotada nos 8 temas + salvaguarda.** |
| **Binary Cross-Entropy (BCE)** | Binária ou Multirrótulo independente (Sigmoid por classe) | Triagem binária de risco ou múltiplos temas simultâneos independentes. |
| **MSE (Mean Squared Error)** | Regressão contínua ($\frac{1}{N}\sum (y - \hat{y})^2$) | Predição de escores contínuos (ex.: PHQ-9) penalizando desvios grandes. |
| **MAE (Mean Absolute Error)** | Regressão robusta ($\frac{1}{N}\sum \|y - \hat{y}\|$) | Estimativas contínuas na presença de *outliers* severos. |

