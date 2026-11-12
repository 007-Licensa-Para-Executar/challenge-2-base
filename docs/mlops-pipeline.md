# Guia prático de MLOps

## 1. O que está no repositório

O pipeline executável está em `mlops/` e os modelos em `models/`. O contrato operacional, o gate e os comandos estão em [`docs/mlops.md`](mlops.md).

Arquivos principais:

- `mlops/pipeline.py` orquestra a rodada.
- `mlops/tracker.py` fala com o MLflow.
- `mlops/store.py` coloca os artefatos ao lado do SQLite.
- `models/neural_net.py` e `models/baseline.py` treinam e avaliam.
- `pyproject.toml` e `uv.lock` fixam o ambiente.
- `.github/workflows/ci.yml` roda Ruff, Pytest e o build.

Uma rodada com a mesma semente e o mesmo hash de `data/synthetic/dev.jsonl` repete as métricas de validação. O MLflow guarda parâmetros, a curva de perda, o F1 macro, a matriz de confusão e, quando o gate aprova, uma versão no Model Registry.

## 2. Ciclo da rodada

1. O desenvolvimento segue em branches `feat/*`, com o histórico no Git.
2. O GitHub Actions executa Ruff e Pytest, inclusive `tests/test_mlops.py`.
3. `uv run bem-estar-mlops` treina o baseline e o MLP no split `dev`.
4. O tracking `sqlite:///mlflow.db` grava as tabelas no banco e os arquivos em `mlflow-artifacts/`.
5. O modelo entra no registry com o nome `mlp-sentiment-classifier` somente se o F1 macro da validação cobre o baseline e o limiar de 0.25.
6. A interface local é `uv run mlflow ui --backend-store-uri sqlite:///mlflow.db`.

O holdout pode ser medido com `--holdout`. Essa medida não altera a promoção.

## 3. Comandos

```bash
uv sync --locked --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run bem-estar-mlops --holdout
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## 4. CI

O workflow versionado é [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). Ele sincroniza o lock, roda o Ruff, o Pytest e `uv build` em Ubuntu, macOS e Windows. Os modelos do extrator continuam simulados nesse workflow. O treino da rede deste pipeline acontece dentro do Pytest, num banco temporário.

## 5. Referências

1. [Documentação do MLflow](https://mlflow.org/docs/latest/index.html)
2. [Documentação do uv](https://docs.astral.sh/uv/)
3. [GitHub Actions para Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)
