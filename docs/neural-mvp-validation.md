# Validação técnica do Classificador Neural de Temas — Benchmark Pré-Produção

Data: 11/11/2026. Este documento consolida a evolução do classificador neural após a integração do conjunto de relatos reais anonimizados em português (`data/real_diaries.json`), a adoção de embeddings semânticos densos contínuos via LSA (TruncatedSVD + TF-IDF sublinear e ponderação IDF) e a calibração de probabilidades pós-treinamento por Temperature Scaling (Guo et al., 2017).

---

## 1. Protocolo Experimental e Metodologia

- **Dataset:** 1.260 relatos clínicos em português cobrindo os 8 macrotemas clínicos (`familia`, `trabalho`, `relacionamentos`, `estudos`, `saude_sono`, `financas`, `luto`, `autoestima`) e a classe de controle/abstenção (`outros_indeterminado`), com 140 exemplos balanceados por classe.
- **Partição Estratificada e Agrupada:** Separação estrita por famílias de origem (`group_id`) via [`data/split.py`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/data/split.py), impedindo vazamento de dados (*data leakage*):
  - **Treino:** 882 relatos (~70%)
  - **Validação:** 189 relatos (~15%)
  - **Teste Independente:** 189 relatos (~15%)
- **Representação Semântica Contínua:** [`ClinicalTextEmbedder`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/embedder.py) com $d=128$, vocabulário de até 3.000 unigramas e bigramas clínicos em pt-br, inicialização semântica distribucional via LSA (TruncatedSVD sobre a matriz termo-documento TF-IDF sublinear) e projeção normalizada $\ell_2$.
- **Arquitetura Neural:** [`ClinicalThemeMLP`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/torch_mlp.py) em PyTorch (Linear 128 $\to$ RMSNorm/BatchNorm $\to$ ReLU $\to$ Dropout(0.3) $\to$ Linear 64 $\to$ ReLU $\to$ Dropout(0.2) $\to$ Linear 9) comparada contra [`NumpyClinicalMLP`](file:///C:/Users/BLU8CA/Projects/PUC/challenge-2-base/models/numpy_mlp.py) do zero e `DummyClassifier` (classe majoritária).
- **Otimização:** AdamW ($lr = 0{,}005$, weight decay $10^{-3}$), gradient clipping com norma máxima 1.0, 35 épocas, batch size 32.
- **Seleção de Checkpoint:** Selecionado exclusivamente pelo melhor Macro-F1 no conjunto de **validação**.
- **Calibração de Probabilidades:** Otimização de temperatura escalar $T$ no conjunto de validação minimizando a NLL (*Negative Log-Likelihood*) via L-BFGS, reduzindo o erro de calibração esperado (*Expected Calibration Error* - ECE) no conjunto de teste.

---

## 2. Resultados Consolidados no Teste Independente

### 2.1. Comparativo Geral (Benchmark Atual vs Baseline e MVP Sintético Inicial)

| Método | Macro-F1 | Acurácia | ECE (Calibração) | Abstenções ($\tau=0{,}50$) | Cobertura |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PyTorch MLP (Calibrado, $\tau=0{,}50$)** | **0,8094** | **80,95%** | **0,0777** | 15 / 189 | **92,06%** |
| PyTorch MLP (Argmax puro) | **0,8217** | **82,54%** | 0,1103 (sem calibrar) | 0 / 189 | 100% |
| NumPy MLP (From-scratch, $\tau=0{,}50$) | 0,6984 | 70,37% | N/A | 22 / 189 | 88,36% |
| Classe Majoritária (Baseline Ingênuo) | 0,0222 | 11,11% | N/A | N/A | N/A |
| *MVP Sintético Anterior (360 amostras)* | *0,0452* | *9,30%* | *0,3120* | *23 / 43* | *46,51%* |

> **Meta atingida:** O objetivo de Macro-F1 $\ge 0{,}75$ no teste independente foi amplamente superado, alcançando **0,8094** sob política com limiar e **0,8217** no argmax direto, com acurácia de **80,95% a 82,54%**.

---

### 2.2. Relatório de Desempenho por Macrotema (PyTorch com $\tau=0{,}50$)

| Macrotema Clínico | Precisão | Revocação | F1-Score | Amostras (Suporte) |
| :--- | :---: | :---: | :---: | :---: |
| **autoestima** | 1,0000 | 1,0000 | **1,0000** | 21 |
| **financas** | 1,0000 | 0,9048 | **0,9500** | 21 |
| **saude_sono** | 0,8636 | 0,9048 | **0,8837** | 21 |
| **luto** | 0,8571 | 0,8571 | **0,8571** | 21 |
| **relacionamentos** | 0,7826 | 0,8571 | **0,8182** | 21 |
| **estudos** | 0,7308 | 0,9048 | **0,8085** | 21 |
| **trabalho** | 0,9286 | 0,6190 | **0,7429** | 21 |
| **familia** | 0,6667 | 0,5714 | **0,6154** | 21 |
| **outros_indeterminado** | 0,5600 | 0,6667 | **0,6087** | 21 |
| **Média Macro** | **0,8210** | **0,8095** | **0,8094** | **189** |

---

### 2.3. Efeito da Calibração de Probabilidades (Temperature Scaling)

- **Temperatura Ótima Estimada ($T$):** **1,3736** (aprendida no conjunto de validação).
- **Diagnóstico Teórico:** $T > 1$ confirma que a rede não-calibrada apresentava **hiperconfiança (*overconfidence*)**, atribuindo probabilidades médias de 85-95% para logits moderados.
- **Expected Calibration Error (ECE):**
  - **Antes da calibração ($T=1{,}0$):** $11{,}03\%$
  - **Após a calibração ($T=1{,}3736$):** **$7{,}77\%$** (redução relativa de ~30% no erro de calibração).
- **Impacto Clínico:** Os scores de probabilidade exibidos aos psicólogos refletem com muito maior fidelidade a real taxa de acerto do modelo, mitigando falsos alarmes em casos ambíguos.

---

## 3. Artefatos e Rastreabilidade

O treinamento gera e versiona automaticamente no diretório `dist/` e no MLflow:
- `best_theme_mlp.pt`: Pesos ótimos da rede neural PyTorch com o parâmetro `temperature` acoplado.
- `theme_embedder.joblib`: Objeto do `ClinicalTextEmbedder` serializado contendo o vocabulário e a matriz de projeção semântica LSA/SVD.
- `comparison_report.json`: Relatório estruturado completo com métricas por classe, matriz de confusão e parâmetros de calibração.
- `split_manifest.json`: Manifest com hashes SHA-256 de dados e códigos, garantindo 100% de reproducibilidade.

---

## 4. Status de Prontidão Clínica e Ressalvas

1. **Prontidão Técnica:** O classificador atingiu maturidade técnica, estabilidade de gradientes, calibração matemática e performance discriminatória sustentada (Macro-F1 $> 0{,}80$).
2. **Uso em Produção:** O modelo pode ser disponibilizado em ambiente de **homologação/piloto assistido (*Human-in-the-Loop*)** como ferramenta de triagem prévia para psicólogos, onde a decisão final permanece estritamente humana.
3. **Salvaguarda Ética:** A política de abstenção ($\tau=0{,}50$) garante que trechos ambíguos ou com baixa confiança sejam direcionados para `outros_indeterminado`, exigindo revisão do profissional.
