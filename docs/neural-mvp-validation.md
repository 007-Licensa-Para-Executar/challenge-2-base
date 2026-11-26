# Validação Técnica do Classificador Neural de Temas — Taxonomia de 6 Classes & SBERT

Este documento descreve o protocolo experimental de validação do classificador neural de temas após a consolidação da taxonomia única de **6 classes** em [`data/taxonomy.py`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/data/taxonomy.py) e a substituição da vetorização baseada em TF-IDF pelos embeddings densos de sentença **SBERT** em [`models/sbert_embedder.py`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/sbert_embedder.py).

---

## 1. Protocolo Experimental e Metodologia

- **Taxonomia Única (6 Temas Clínicos):** Todos os datasets (real anonimizado em `data/real_diaries.json` e sintético em `data/synthetic/synthetic_diaries.json`), o script de divisão, a rede neural e o preditor operam exclusivamente sobre os **6 temas**:
  - `autopercepcao` (**Autopercepção**)
  - `vinculos` (**Vínculos**)
  - `desempenho` (**Desempenho**)
  - `fisico` (**Físico**)
  - `rupturas` (**Rupturas**)
  - `outros` (**Outros** — sem tema clínico claro, relato neutro ou classe de salvaguarda por abstenção)
- **Partição Estratificada e Agrupada:** Separação estrita por famílias de origem (`group_id`) via [`data/split.py`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/data/split.py), impedindo vazamento de dados (*data leakage*) entre treino (~70%), validação (~15%) e teste independente (~15%).
- **Representação Semântica Contínua (SBERT):** [`SBERTEmbedder`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/sbert_embedder.py) utilizando `sentence-transformers` com o modelo padrão congelado `paraphrase-multilingual-MiniLM-L12-v2` ($d = 384$, normalização $\ell_2$). Por ser pré-treinado e congelado, não vaza informação entre splits (ao contrário de ajustes de vocabulário locais).
- **Arquitetura Neural:** [`ClinicalThemeMLP`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/torch_mlp.py) em PyTorch (`Linear(384, 128) -> Norm -> ReLU -> Dropout(0.3) -> Linear(128, 64) -> ReLU -> Dropout(0.2) -> Linear(64, 6)`) comparada contra [`NumpyClinicalMLP`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/numpy_mlp.py) do zero e `DummyClassifier` (classe majoritária).
- **Saída Percentual e Abstenção:** Ao receber um diário, o classificador identifica o tema e gera percentuais (`%`) para cada uma das 6 classes via Softmax calibrada. Confiança máxima inferior a $\tau = 0.50$ direciona a decisão operacional para `outros`.
- **Otimização e Calibração:** AdamW ($lr = 0{,}005$, weight decay $10^{-3}$), gradient clipping com norma máxima 1.0, 35 épocas, batch size 32, seleção de checkpoint pelo melhor Macro-F1 de **validação** e calibração pós-treino por **Temperature Scaling** (Guo et al., 2017) minimizando NLL via L-BFGS.

---

## 2. Como Executar e Inspecionar a Validação Atualizada

Para reproduzir o treinamento e gerar os relatórios oficiais da rodada atual na taxonomia de 6 temas com SBERT:

```bash
uv run python -m models.train --embedder sbert
```

O pipeline registra automaticamente as métricas no MLflow e salva os seguintes artefatos em `dist/`:
- `best_theme_mlp.pt`: Pesos ótimos da rede neural PyTorch (`384 -> 128 -> 64 -> 6`) com o parâmetro `temperature` acoplado.
- `theme_embedder.joblib`: Configuração serializada do `SBERTEmbedder` (sem duplicar os pesos do encoder pré-treinado).
- `best_numpy_mlp.npz`: Pesos do baseline didático em NumPy puro.
- `comparison_report.json`: Comparativo entre PyTorch MLP (com política de limiar e argmax puro), NumPy MLP e baseline majoritário, além dos parâmetros de calibração (`temperature`, `ece_before`, `ece_after`).
- `classification_report.json` e `threshold_classification_report.json`: Precisão, revocação e F1-Score para cada um dos 6 temas (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`).
- `split_manifest.json`: Manifesto com hashes SHA-256 de dados e código-fonte para reprodutibilidade.

---

## 3. Referência Histórica (Benchmark Anterior — 9 Classes / ClinicalTextEmbedder)

> [!NOTE]
> Em 11/11/2026, antes da consolidação para os **6 temas** e da migração para **SBERT**, o protótipo foi medido sobre 1.260 relatos distribuídos na taxonomia legada de 9 classes (`familia`, `trabalho`, `relacionamentos`, `estudos`, `saude_sono`, `financas`, `luto`, `autoestima`, `outros_indeterminado`) com `ClinicalTextEmbedder` ($d=128$, LSA/SVD), obtendo Macro-F1 de `0,8094` ($\tau=0{,}50$) / `0,8217` (argmax) e redução de ECE de `11,03%` para `7,77%` ($T=1{,}3736$). Esses valores são estritamente históricos e **não** devem ser confundidos com medições da taxonomia atual de 6 classes com SBERT.

---

## 4. Status de Prontidão Clínica e Ressalvas

1. **Supervisão Humana (*Human-in-the-Loop*):** O modelo atua exclusivamente como ferramenta de triagem e organização temática prévia para psicólogos; a interpretação clínica permanece 100% humana.
2. **Semântica dos Percentuais:** Os percentuais (`%`) emitidos por `predict_text()` correspondem aos scores Softmax atribuídos às 6 categorias exclusivas; na decomposição por sentenças (`destrinchar_diario()`), `topic_weights` mede a fração de caracteres analisados atribuída a cada tema com citação literal auditável.
3. **Salvaguarda Ética:** A política de abstenção ($\tau = 0{,}50$) garante que relatos ambíguos ou com baixa confiança sejam encaminhados para `outros`.
