# Guia de Desenvolvimento: Rede Neural Simples (Deep Learning MLP com SBERT)

**Propósito e Escopo.** A rede neural temática classifica o texto do diário do paciente entre os **6 Temas Clínicos** definidos em [`data/taxonomy.py`](../data/taxonomy.py) e retorna a **distribuição percentual (`%`)** de cada tema após receber o relato. A representação textual utiliza embeddings densos pré-treinados **SBERT** (`models/sbert_embedder.py`, substituindo a antiga abordagem esparsa baseada em TF-IDF), e o classificador neural (MLP em PyTorch e baseline didático em NumPy) aprende as fronteiras de decisão sobre esses vetores.

---

## 1. Identificação e Propósito do Componente
* **Arquivos no Código:**
  - Embeddings de Sentença (SBERT): `models/sbert_embedder.py` (`SBERTEmbedder`)
  - Produção (PyTorch): `models/torch_mlp.py` (`ClinicalThemeMLP`), `models/train.py` e `models/predictor.py` (`ClinicalThemePredictor`)
  - Baseline Didático (NumPy puro do zero): `models/numpy_mlp.py` (`NumpyClinicalMLP`)
  - Taxonomia Canônica: `data/taxonomy.py`
* **Objetivo Primário:** Ao receber o diário do paciente, a Rede Neural identifica o tema predominante e calcula os **percentuais (`%`, de 0% a 100%)** para cada um dos **6 Temas Clínicos**:
  1. `autopercepcao` (**Autopercepção**): autoestima, identidade, imagem corporal e sensação de incapacidade ou inadequação.
  2. `vinculos` (**Vínculos**): relacionamentos amorosos, amizades, família, términos, traições e separações.
  3. `desempenho` (**Desempenho**): trabalho, estudos e finanças (cobranças, metas, provas, dívidas).
  4. `fisico` (**Físico**): saúde física e mental em sintomas, sono, tratamento médico, dores e sonhos.
  5. `rupturas` (**Rupturas**): perdas por morte e luto.
  6. `outros` (**Outros**): sem tema clínico claro, relato neutro ou classe de salvaguarda por abstenção (quando a confiança máxima é inferior ao limiar $\tau = 0.50$).
* **Por que este componente existe?** Cumpre a **Constraint 4 (Construir e testar pelo menos uma rede neural simples)** e a **Constraint 3 (Aplicar MLOps)**. O codificador SBERT atua apenas como extrator semântico congelado; toda a classificação temática e a calibração das probabilidades são aprendidas pela arquitetura MLP treinada, validada com divisão estratificada por grupos (`data/split.py`) e monitorada com curvas de perda, matriz de confusão e Macro-F1 no MLflow.

---

## 2. Arquitetura da Rede Neural (SBERT + Multi-Layer Perceptron)

```
[ Diário do Paciente (Texto em Português) ]
        │
        ▼
[ SBERTEmbedder (sentence-transformers congelado: paraphrase-multilingual-MiniLM-L12-v2) ]
[ Saída: Embedding denso contínuo de 384 dimensões, normalizado L2 ]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada 1: Linear(384 -> 128)                           │
│ Normalização (BatchNorm1d / LayerNorm / RMSNorm)       │
│ Ativação: ReLU                                         │
│ Dropout (taxa = 0.3)                                   │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada 2: Linear(128 -> 64)                            │
│ Ativação: ReLU                                         │
│ Dropout (taxa = 0.2)                                   │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada 3: Linear(64 -> 6 classes)                      │
│ Calibração: Temperature Scaling (z / T)                │
│ Saída: Softmax -> Percentuais (%) para os 6 temas      │
└────────────────────────────────────────────────────────┘
```

---

## 3. Implementação da Arquitetura em PyTorch (`models/torch_mlp.py`)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

THEME_CLASSES = [
    "autopercepcao",
    "vinculos",
    "desempenho",
    "fisico",
    "rupturas",
    "outros",
]


class ClinicalThemeMLP(nn.Module):
    def __init__(
        self,
        input_dim: int = 384,
        hidden_dim1: int = 128,
        hidden_dim2: int = 64,
        num_classes: int = 6,
        dropout_rate: float = 0.3,
    ):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim1)
        self.bn1 = nn.BatchNorm1d(hidden_dim1)
        self.dropout1 = nn.Dropout(dropout_rate)

        self.fc2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.dropout2 = nn.Dropout(dropout_rate * 0.7)

        self.fc3 = nn.Linear(hidden_dim2, num_classes)
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        if x.size(0) > 1 or not self.training:
            x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout1(x)

        x = self.fc2(x)
        x = F.relu(x)
        x = self.dropout2(x)

        return self.fc3(x)

    def predict_proba(self, x: torch.Tensor, apply_temperature: bool = True) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            if apply_temperature:
                logits = logits / torch.clamp(self.temperature, min=0.05, max=10.0)
            return F.softmax(logits, dim=-1)

    def predict_percentages(self, x: torch.Tensor, round_digits: int = 2) -> list[dict[str, float]]:
        probs = self.predict_proba(x).cpu().numpy()
        return [
            {THEME_CLASSES[i]: round(float(probs[row, i]) * 100.0, round_digits) for i in range(len(THEME_CLASSES))}
            for row in range(probs.shape[0])
        ]
```

---

## 4. Extração de Embeddings com SBERT (`models/sbert_embedder.py`) e Treinamento (`models/train.py`)

O `SBERTEmbedder` utiliza `sentence-transformers` (modelo padrão `paraphrase-multilingual-MiniLM-L12-v2`, com 384 dimensões; também suporta `intfloat/multilingual-e5-small` com prefixo `"query: "`). Como o encoder é **pré-treinado e congelado**, `fit()` é um *no-op* e não há vazamento de dados entre treino, validação e teste.

```python
import joblib
import mlflow
import torch
import torch.nn as nn
from sklearn.metrics import f1_score

from data.split import stratified_split_dataset
from models.sbert_embedder import SBERTEmbedder
from models.torch_mlp import THEME_CLASSES, ClinicalThemeMLP

def train_theme_classifier(
    rows: list[dict],
    epochs: int = 35,
    batch_size: int = 32,
    lr: float = 0.005,
    experiment_name: str = "Theme_MLP_Preliminary",
):
    # 1. Divisão estratificada por família de origem (evita vazamento entre splits)
    train_rows, val_rows, test_rows = stratified_split_dataset(rows, random_state=42)
    theme_to_idx = {theme: idx for idx, theme in enumerate(THEME_CLASSES)}

    # 2. Extração de Embeddings Densos com SBERT (384 dimensões, normalizados L2)
    embedder = SBERTEmbedder(model_name="paraphrase-multilingual-MiniLM-L12-v2", normalize_default=True)
    X_train = embedder.fit_transform([r["texto"] for r in train_rows])
    X_val = embedder.transform([r["texto"] for r in val_rows])
    X_test = embedder.transform([r["texto"] for r in test_rows])

    t_X_train = torch.tensor(X_train, dtype=torch.float32)
    t_y_train = torch.tensor([theme_to_idx[r["macro_tema"]] for r in train_rows], dtype=torch.long)
    t_X_val = torch.tensor(X_val, dtype=torch.float32)
    t_y_val = torch.tensor([theme_to_idx[r["macro_tema"]] for r in val_rows], dtype=torch.long)
    t_X_test = torch.tensor(X_test, dtype=torch.float32)
    t_y_test = torch.tensor([theme_to_idx[r["macro_tema"]] for r in test_rows], dtype=torch.long)

    # 3. Modelo MLP (384 -> 128 -> 64 -> 6 classes)
    model = ClinicalThemeMLP(input_dim=embedder.embedding_dim, num_classes=len(THEME_CLASSES))
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    criterion = nn.CrossEntropyLoss()

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="Grouped_Comparison"):
        best_val_f1 = -1.0
        best_weights = None
        loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(t_X_train, t_y_train),
            batch_size=batch_size,
            shuffle=True,
        )

        for epoch in range(1, epochs + 1):
            model.train()
            for bx, by in loader:
                optimizer.zero_grad()
                loss = criterion(model(bx), by)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            model.eval()
            with torch.no_grad():
                val_logits = model(t_X_val)
                val_preds = torch.argmax(val_logits, dim=-1).numpy()
                val_f1 = f1_score(t_y_val.numpy(), val_preds, average="macro", zero_division=0)

            mlflow.log_metric("val_macro_f1", val_f1, step=epoch)
            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        model.load_state_dict(best_weights)
        torch.save(model.state_dict(), "dist/best_theme_mlp.pt")
        joblib.dump(embedder, "dist/theme_embedder.joblib")
```

> [!NOTE]
> O `SBERTEmbedder` implementa `__getstate__` e `__setstate__` para não duplicar os pesos do encoder pré-treinado (~470 MB) dentro de `dist/theme_embedder.joblib`: apenas a configuração do modelo SBERT é serializada e o encoder é recarregado sob demanda.

### Executando o Treinamento e a Predição

```bash
# Treinamento com SBERT (padrão)
uv run python -m models.train --embedder sbert

# Predição de um diário com retorno de percentuais (%) para os 6 temas
uv run python -m models.predictor --text "Hoje briguei com meu pai e não consegui dormir de preocupação." --json
```

---

## 5. Implementação Didática em NumPy Puro (`models/numpy_mlp.py`)

Para demonstrar nos relatórios acadêmicos a compreensão dos fundamentos do cálculo diferencial da rede sem dependência de bibliotecas de autograd, o baseline em NumPy puro opera sobre os mesmos embeddings SBERT de 384 dimensões e gera probabilidades/percentuais para as 6 classes:

```python
import numpy as np

class NumpyClinicalMLP:
    def __init__(self, in_dim: int = 384, h1: int = 64, out_dim: int = 6, lr: float = 0.05):
        self.lr = lr
        rng = np.random.RandomState(42)
        # Inicialização He (Kaiming) para ReLU
        self.W1 = rng.randn(in_dim, h1) * np.sqrt(2.0 / in_dim)
        self.b1 = np.zeros((1, h1))
        self.W2 = rng.randn(h1, out_dim) * np.sqrt(2.0 / h1)
        self.b2 = np.zeros((1, out_dim))

    def relu(self, z):
        return np.maximum(0, z)

    def relu_derivative(self, z):
        return (z > 0).astype(float)

    def softmax(self, z):
        exp_z = np.exp(z - np.max(z, axis=1, keepdims=True))
        return exp_z / np.sum(exp_z, axis=1, keepdims=True)

    def forward(self, X):
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.probs = self.softmax(self.z2)
        return self.probs

    def backward(self, X, y_onehot):
        N = X.shape[0]
        # Gradiente na saída (Softmax + Cross-Entropy: dL/dz2 = (probs - y) / N)
        dz2 = (self.probs - y_onehot) / N
        dW2 = np.dot(self.a1.T, dz2)
        db2 = np.sum(dz2, axis=0, keepdims=True)

        # Retropropagação para a camada oculta
        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * self.relu_derivative(self.z1)
        dW1 = np.dot(X.T, dz1)
        db1 = np.sum(dz1, axis=0, keepdims=True)

        # Atualização de pesos via Gradiente Descendente Estocástico (SGD)
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1
```

---

## 6. Como Testar a Rede Neural (`tests/test_torch_mlp.py` e `tests/test_predictor.py`)

```python
import torch
from models.torch_mlp import ClinicalThemeMLP

def test_torch_mlp_forward_and_prediction():
    model = ClinicalThemeMLP(input_dim=384, num_classes=6)
    dummy_input = torch.randn(4, 384)

    # 1. Teste de formato de logits para os 6 temas
    logits = model(dummy_input)
    assert logits.shape == (4, 6)

    # 2. Teste de probabilidades Softmax
    probs = model.predict_proba(dummy_input)
    assert probs.shape == (4, 6)
    assert torch.allclose(probs.sum(dim=-1), torch.ones(4), atol=1e-5)
```

---

## 7. Referências Técnicas
1. **Reimers, N., & Gurevych, I. (2019).** *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* EMNLP-IJCNLP. Base teórica do `SBERTEmbedder` (`sentence-transformers`).
2. **UCREL Emotion Analysis:** Metodologia de avaliação com holdout cego, Matriz de Confusão e Macro-F1 para textos clínicos sensíveis.
3. **Paszke, A. et al. (PyTorch):** *An Imperative Style, High-Performance Deep Learning Library.* NeurIPS.
4. **Guo, C. et al. (2017).** *On Calibration of Modern Neural Networks.* ICML (Temperature Scaling).
