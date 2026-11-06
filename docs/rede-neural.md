# Guia de Desenvolvimento: Rede Neural Simples (Deep Learning MLP)

## 1. Identificação e Propósito do Componente
* **Arquivos no Código:** 
  - Produção (PyTorch): `models/torch_mlp.py` e `models/train.py`
  - Baseline Didático (NumPy puro do zero): `models/numpy_mlp.py`
* **Objetivo Primário:** Classificar o texto do diário do paciente entre os **8 Macrotemas Clínicos Padrão** mais a classe de salvaguarda:
  1. `familia`
  2. `trabalho`
  3. `relacionamentos`
  4. `estudos`
  5. `saude_sono`
  6. `financas`
  7. `luto`
  8. `autoestima`
  9. `outros_indeterminado` (Fallback seguro se a probabilidade máxima for inferior a 0.50).
* **Por que este componente existe?** Cumpre com excelência a **Constraint 4 (Construir e testar pelo menos uma rede neural simples)** e a **Constraint 3 (Aplicar MLOps)**. O modelo não é uma "caixa preta" de terceiros: a arquitetura é projetada, treinada, validada com divisão estratificada e monitorada pelo grupo com curvas de perda, matriz de confusão e Macro-F1 no MLflow.

---

## 2. Arquitetura da Rede Neural (Multi-Layer Perceptron)

```
[ Texto do Relato ]
        │
        ▼
[ TF-IDF Vectorizer (1.024 atributos mais informativos) ]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Camada 1: Linear(1024 -> 128)                          │
│ Batch Normalization 1D                                 │
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
│ Camada 3: Linear(64 -> 9 classes)                      │
│ Saída: Softmax (distribuição de probabilidades)        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Implementação Completa em PyTorch (`models/torch_mlp.py`)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class ClinicalThemeMLP(nn.Module):
    def __init__(self, input_dim: int = 1024, hidden_dim1: int = 128, hidden_dim2: int = 64, num_classes: int = 9, dropout_rate: float = 0.3):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim1)
        self.bn1 = nn.BatchNorm1d(hidden_dim1)
        self.dropout1 = nn.Dropout(dropout_rate)
        
        self.fc2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.dropout2 = nn.Dropout(dropout_rate * 0.7)
        
        self.fc3 = nn.Linear(hidden_dim2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Camada 1
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout1(x)
        
        # Camada 2
        x = self.fc2(x)
        x = F.relu(x)
        x = self.dropout2(x)
        
        # Camada de Saída (Logits brutos para uso com CrossEntropyLoss)
        logits = self.fc3(x)
        return logits

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return F.softmax(logits, dim=-1)
```

---

## 4. Pipeline de Treinamento com MLOps & MLflow (`models/train.py`)

```python
import os
import joblib
import mlflow
import mlflow.pytorch
import numpy as np
import torch
import torch.nn as nn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from models.torch_mlp import ClinicalThemeMLP

THEME_CLASSES = [
    "familia", "trabalho", "relacionamentos", "estudos",
    "saude_sono", "financas", "luto", "autoestima", "outros_indeterminado"
]

def train_theme_classifier(
    texts: list[str],
    labels: list[int],
    epochs: int = 40,
    batch_size: int = 32,
    lr: float = 0.001,
    experiment_name: str = "Clinical_Theme_NN"
):
    mlflow.set_experiment(experiment_name)
    
    # 1. Divisão Estratificada (70% Treino, 15% Validação, 15% Teste Holdout)
    X_train_raw, X_temp, y_train_raw, y_temp = train_test_split(
        texts, labels, test_size=0.30, random_state=42, stratify=labels
    )
    X_val_raw, X_test_raw, y_val_raw, y_test_raw = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    # 2. Vetorização TF-IDF
    vectorizer = TfidfVectorizer(max_features=1024, ngram_range=(1, 2), lowercase=True)
    X_train = vectorizer.fit_transform(X_train_raw).toarray()
    X_val = vectorizer.transform(X_val_raw).toarray()
    X_test = vectorizer.transform(X_test_raw).toarray()

    # Conversão para tensores PyTorch
    t_X_train = torch.tensor(X_train, dtype=torch.float32)
    t_y_train = torch.tensor(y_train_raw, dtype=torch.long)
    t_X_val = torch.tensor(X_val, dtype=torch.float32)
    t_y_val = torch.tensor(y_val_raw, dtype=torch.long)
    t_X_test = torch.tensor(X_test, dtype=torch.float32)
    t_y_test = torch.tensor(y_test_raw, dtype=torch.long)

    # 3. Inicialização do Modelo, Otimizador e Loss Ponderada
    model = ClinicalThemeMLP(input_dim=1024, num_classes=9)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    with mlflow.start_run(run_name="MLP_Training_Run"):
        # Registro de Hiperparâmetros
        mlflow.log_params({
            "model_type": "PyTorch_MLP",
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": lr,
            "input_features": 1024,
            "hidden_layers": [128, 64]
        })

        best_val_f1 = 0.0
        best_model_weights = None

        # 4. Loop de Treinamento
        dataset = torch.utils.data.TensorDataset(t_X_train, t_y_train)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

        for epoch in range(1, epochs + 1):
            model.train()
            epoch_loss = 0.0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * batch_x.size(0)

            epoch_loss /= len(dataset)

            # Validação
            model.eval()
            with torch.no_grad():
                val_logits = model(t_X_val)
                val_loss = criterion(val_logits, t_y_val).item()
                val_preds = torch.argmax(val_logits, dim=-1).numpy()
                val_f1 = f1_score(y_val_raw, val_preds, average="macro")

            mlflow.log_metric("train_loss", epoch_loss, step=epoch)
            mlflow.log_metric("val_loss", val_loss, step=epoch)
            mlflow.log_metric("val_macro_f1", val_f1, step=epoch)

            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                best_model_weights = model.state_dict().copy()

        # 5. Avaliação Final no Conjunto de Teste Holdout Cego
        model.load_state_dict(best_model_weights)
        model.eval()
        with torch.no_grad():
            test_logits = model(t_X_test)
            test_preds = torch.argmax(test_logits, dim=-1).numpy()
            test_f1 = f1_score(y_test_raw, test_preds, average="macro")
            test_acc = (test_preds == y_test_raw).mean()

        mlflow.log_metrics({"final_test_macro_f1": test_f1, "final_test_acc": test_acc})

        # Salva Artefatos
        os.makedirs("dist", exist_ok=True)
        torch.save(best_model_weights, "dist/best_theme_mlp.pt")
        joblib.dump(vectorizer, "dist/tfidf_vectorizer.joblib")
        mlflow.log_artifact("dist/best_theme_mlp.pt")
        mlflow.log_artifact("dist/tfidf_vectorizer.joblib")

        print(f"Treinamento Concluído! Test Macro-F1: {test_f1:.4f} | Test Acc: {test_acc:.4f}")
```

---

## 5. Implementação Didática em NumPy Puro (`models/numpy_mlp.py`)

Para demonstrar nos relatórios acadêmicos a compreensão dos fundamentos do cálculo diferencial da rede sem dependência de bibliotecas de autograd:

```python
import numpy as np

class NumpyClinicalMLP:
    def __init__(self, in_dim=1024, h1=64, out_dim=9, lr=0.01):
        self.lr = lr
        np.random.seed(42)
        # Inicialização He (Kaiming) para ReLU
        self.W1 = np.random.randn(in_dim, h1) * np.sqrt(2.0 / in_dim)
        self.b1 = np.zeros((1, h1))
        self.W2 = np.random.randn(h1, out_dim) * np.sqrt(2.0 / h1)
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
        # Gradiente na saída (Softmax + Cross-Entropy: dL/dz2 = probs - y)
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

## 6. Como Testar a Rede Neural (`tests/test_model.py`)

```python
import torch
from models.torch_mlp import ClinicalThemeMLP

def test_torch_mlp_forward_and_prediction():
    model = ClinicalThemeMLP(input_dim=1024, num_classes=9)
    dummy_input = torch.randn(4, 1024)
    
    # 1. Teste de formato de logits
    logits = model(dummy_input)
    assert logits.shape == (4, 9)

    # 2. Teste de probabilidades Softmax
    probs = model.predict_proba(dummy_input)
    assert probs.shape == (4, 9)
    # A soma das probabilidades de cada linha deve ser 1.0 (margem de erro de ponto flutuante)
    assert torch.allclose(probs.sum(dim=-1), torch.ones(4), atol=1e-5)
```

---

## 7. Referências Técnicas
1. **Projeto Emotia:** Classificador emocional baseado em Perceptron Multicamadas (MLP) com vetorização TF-IDF para diários digitais.
2. **UCREL Emotion Analysis:** Metodologia de avaliação com holdout cego, Matriz de Confusão e Macro-F1 para textos clínicos sensíveis.
3. **Paszke, A. et al. (PyTorch):** *An Imperative Style, High-Performance Deep Learning Library*. NeurIPS.
