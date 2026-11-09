# Guia Prático de MLOps: Rastreamento, Reprodutibilidade e CI/CD

## 1. Identificação e Propósito
* **Arquivos no Código:** `.github/workflows/ci.yml`, `mlops/tracker.py`, `pyproject.toml`, `uv.lock`
* **Objetivo Primário:** Operacionalizar as boas práticas de engenharia de software e aprendizado de máquina para atender à **Constraint 3 (Aplicar MLOps)** e à **Constraint 6 (Utilizar ferramenta de versionamento de código)**.
* **Garantias do Pipeline:**
  1. **Reprodutibilidade 100% Determinística:** Qualquer desenvolvedor ou avaliador que clonar o projeto roda o mesmo código sem conflitos de versão de pacotes, graças ao `uv.lock`.
  2. **Rastreamento Total de Modelos:** Todo treinamento da Rede Neural MLP tem hiperparâmetros, curvas de loss, métricas de Macro-F1 e pesos registrados no **MLflow**.
  3. **Integração Contínua (CI):** Testes unitários e verificação de estilo são validados a cada commit no GitHub Actions antes de qualquer merge.

---

## 2. Diagrama do Ciclo de Vida MLOps

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                 CICLO DE VIDA MLOPS                               │
└───────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
[ 1. Desenvolvimento & Git ] ──► Branches 'feat/*', Commits Semânticos
         │
         ▼
[ 2. CI no GitHub Actions ] ──► Ruff (Linter & Format) + Pytest Automatizado
         │
         ▼
[ 3. Treino da Rede Neural ] ──► Log no MLflow (Loss, F1, Matriz de Confusão)
         │
         ▼
[ 4. Registro de Artefatos ] ──► 'dist/best_theme_mlp.pt' + 'tfidf_vectorizer.joblib'
         │
         ▼
[ 5. Monitoramento Local ]   ──► Visualização interativa na MLflow UI
```

---

## 3. Comandos Essenciais do Ambiente com `uv`

Para garantir que o ambiente seja idêntico em qualquer máquina:
```bash
# 1. Sincronizar o ambiente limpo a partir do lockfile
uv sync --frozen

# 2. Executar a suíte de testes automatizados com cobertura
uv run pytest -v --cov=app --cov=agents --cov=models

# 3. Executar o linter e o formatador de código
uv run ruff check .
uv run ruff format --check .

# 4. Iniciar a interface visual do MLflow
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

---

## 4. Pipeline de CI no GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: CI Multiagente & ML Pipeline

on:
  push:
    branches: [main, develop, "feat/**"]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout do Repositório
        uses: actions/checkout@v4

      - name: Instalar o uv (Gerenciador Rápido de Python)
        uses: astral-sh/setup-uv@v2
        with:
          version: "latest"

      - name: Configurar o Python 3.12
        run: uv python install 3.12

      - name: Sincronizar Dependências do uv.lock
        run: uv sync --frozen

      - name: Executar Linter e Formatação com Ruff
        run: |
          uv run ruff check .
          uv run ruff format --check .

      - name: Executar Testes Automatizados (Pytest)
        run: |
          uv run pytest -v --cov=agents --cov=models --cov=knowledge_base
```

---

## 5. Módulo Centralizado de Rastreamento MLflow (`mlops/tracker.py`)

```python
import mlflow
import os

class MLFlowTracker:
    def __init__(self, experiment_name: str = "Clinica_Theme_MLP", db_uri: str = "sqlite:///mlflow.db"):
        self.db_uri = db_uri
        self.experiment_name = experiment_name
        mlflow.set_tracking_uri(self.db_uri)
        mlflow.set_experiment(self.experiment_name)

    def log_training_session(
        self,
        params: dict,
        metrics: dict,
        artifacts_paths: list[str] = None,
        run_name: str = "training_run"
    ):
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            
            if artifacts_paths:
                for path in artifacts_paths:
                    if os.path.exists(path):
                        mlflow.log_artifact(path)
                        print(f"Artefato registrado no MLflow: {path}")

    @staticmethod
    def get_best_model_run(experiment_name: str, metric_name: str = "final_test_macro_f1"):
        exp = mlflow.get_experiment_by_name(experiment_name)
        if not exp:
            return None
        runs = mlflow.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=[f"metrics.{metric_name} DESC"],
            max_results=1
        )
        return runs.iloc[0] if not runs.empty else None
```

---

## 6. Referências Técnicas
1. **MLflow Official Documentation:** [https://mlflow.org/docs/latest/index.html](https://mlflow.org/docs/latest/index.html).
2. **Astral `uv` Package Manager:** [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/).
3. **GitHub Actions for Python:** [https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python).
