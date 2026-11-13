# MVP de classificação temática: dados sintéticos, redes neurais e avaliação

Este protótipo classifica textos de diário em temas predefinidos. Inclui um gerador de exemplos fictícios, uma rede com cálculos explícitos em NumPy, uma implementação de comparação em PyTorch e rastreamento de experimentos no MLflow.

Os resultados são experimentais. Os exemplos sintéticos e seus rótulos não possuem validação clínica nem demonstram desempenho em relatos reais. As métricas devem ser obtidas na versão atual do pipeline, com os grupos de origem separados entre os conjuntos. Números de uma divisão anterior por exemplos não são comparáveis diretamente à avaliação por grupos.

## Escopo e categorias

As nove categorias desta versão são:

- `familia`
- `trabalho`
- `relacionamentos`
- `estudos`
- `saude_sono`
- `financas`
- `luto`
- `autoestima`
- `outros_indeterminado`

O modelo é um classificador de **tema único por entrada**. O preditor pode dividir um diário em sentenças e classificar cada sentença; isso permite apresentar temas diferentes ao longo do texto, mas não transforma a rede em um classificador multirrótulo. Uma sentença que aborda dois assuntos ainda recebe uma categoria segundo a política do preditor.

Subtemas pessoais, diagnóstico, interpretação clínica, atendimento terapêutico e RAG não são implementados por este componente. A integração com os agentes e a migração da taxonomia dos consumidores precisam ser verificadas separadamente.

## Dados sintéticos e separação dos conjuntos

O gerador usa perfis fictícios e templates locais. A opção de geração por Ollama utiliza um modelo instalado pelo usuário. Perfis, estilo de escrita e parâmetros de geração não garantem realismo representativo, validade clínica ou ausência de viés.

Variações de introdução e conclusão de um mesmo texto-base não são exemplos independentes. O dataset registra grupos de origem para que versões da mesma família não sejam distribuídas entre treino, validação e teste. Textos duplicados também precisam permanecer no mesmo grupo. O pipeline verifica a separação; ter identificadores diferentes não basta para considerar os exemplos independentes.

A divisão busca as proporções configuradas respeitando os grupos. Seus tamanhos e a distribuição das classes podem variar; não se promete uma proporção exata de 70/15/15. O manifesto do experimento deve ser consultado para conhecer os IDs e grupos de cada conjunto. A rotina de compatibilidade com dados legados e suas restrições estão documentadas em [data/split.py](data/split.py).

O vocabulário TF-IDF é ajustado apenas no treino. Validação e teste usam esse mesmo transformador, sem ajustá-lo novamente. O teste final não deve ser usado repetidamente para escolher a arquitetura ou o limiar de abstenção.

Os rótulos são definidos pela geração e não foram estabelecidos como referência independente por especialistas. A avaliação mede desempenho sobre esse conjunto sintético. Erros de geração, ambiguidade entre categorias, pouca diversidade de linguagem e distribuição artificialmente equilibrada são limitações que devem acompanhar os resultados.

## Arquiteturas e aprendizado

O fluxo compartilhado é:

```text
Textos e rótulos sintéticos
  -> separação por grupos
  -> TF-IDF ajustado no treino
  -> treinamento e seleção pela validação
  -> avaliação final e registro de artefatos
```

O TF-IDF usa até 1.024 características, com palavras e pares de palavras. O tamanho efetivo da entrada depende do vocabulário aprendido no conjunto de treino.

| Implementação | Arquitetura | Papel |
| --- | --- | --- |
| NumPy | Entrada -> camada oculta/ReLU -> saída/softmax | Construção didática com operações e derivadas explícitas |
| PyTorch | Entrada -> 128 unidades/BatchNorm/ReLU/Dropout -> 64 unidades/ReLU/Dropout -> nove logits | Comparação com treinamento por autograd |
| Baseline simples | Referência de classificação sem a arquitetura neural | Verificar se a rede supera uma solução trivial no mesmo conjunto |

Na versão NumPy, a passagem direta calcula:

```text
z1 = X @ W1 + b1
h  = ReLU(z1)
z2 = h @ W2 + b2
p  = softmax(z2)
```

A perda compara `p` com a referência. A retropropagação calcula as derivadas, começando por `(p - y) / N`, e o SGD atualiza os pesos. Os testes devem verificar a correção numérica dos gradientes e a redução da perda em um caso controlado; isso não substitui a avaliação temática.

Para a comparação, as implementações utilizam a mesma divisão e representação de entrada. A arquitetura, o otimizador e os hiperparâmetros de cada uma devem ser registrados: não são redes idênticas, e uma diferença de resultado não pode ser atribuída somente à biblioteca.

## Saídas, abstenção e percentuais

A distribuição softmax indica pontuações entre as categorias exclusivas. **Somar 100% não significa estar calibrada**, nem permite interpretar os valores como proporção temática do diário.

O preditor também calcula uma composição por segmentos: soma os caracteres dos trechos associados a cada tema e divide pelo total de caracteres analisados. Essa é uma medida descritiva do texto classificado, sujeita aos erros de segmentação e da rede. Não mede importância do assunto, intensidade emocional ou condição clínica.

Para apresentar um gráfico, informar a medida escolhida, o denominador, a cobertura do texto e o critério de seleção dos segmentos. Trechos descartados não devem desaparecer silenciosamente da interpretação. Quando não houver segmentos analisáveis, a distribuição softmax não deve ser usada como substituta da composição por caracteres.

A regra de abstenção aplica um limiar às pontuações do modelo. Um resultado abaixo desse limiar pode ser direcionado a `outros_indeterminado`; isso é uma política operacional, não uma garantia de segurança. A avaliação deve usar a mesma regra executada pelo preditor e apresentar separadamente a taxa de abstenção. A pontuação da melhor classe original não é a confiança da classe de fallback.

As citações de segmentos conservam posições de início e fim no original para permitir conferência. Uma evidência literal comprova que o trecho existe; não comprova que sua classificação está correta.

Os campos legados de distribuição são conservados para compatibilidade. Sua interpretação é explícita:

| Campo | Significado |
| --- | --- |
| `score_semantics` | `uncalibrated_softmax`: pontuações sem calibração demonstrada |
| `candidate_theme` | Categoria com maior score antes da política de abstenção |
| `abstention_reason` | `empty_input`, `below_threshold` ou ausência de abstenção |
| `confidence` | Score máximo do candidato; zero no texto vazio, que não passa pela rede |
| `weight_basis` | `analyzed_characters`: base dos pesos por segmento |
| `total_chars`, `analyzed_chars`, `omitted_chars` | Tamanho original, analisado e não analisado |
| `coverage_ratio` | Fração do texto coberta pelos segmentos analisados |

Sem segmentos analisáveis, os pesos ficam zerados. `top_topics` apresenta apenas a categoria aceita; não transforma pequenas pontuações softmax em presença de vários temas.

## Execução a partir de clone limpo

Execute os comandos na raiz do repositório com Python 3.12 e uv instalados. Os comandos abaixo funcionam em terminais Unix e no CMD, sem exigir ativação manual de ambiente virtual.

### 1. Instalar as dependências travadas

```text
uv sync --locked --python 3.12
```

Se o lockfile não corresponder ao `pyproject.toml`, o comando falha. O responsável pela alteração das dependências deve atualizar e versionar `uv.lock`; não remover `--locked` do CI para ocultar a divergência.

### 2. Gerar exemplos fictícios, se necessário

O dataset versionado permite iniciar o experimento sem Ollama. Para gerar uma nova versão offline:

```text
uv run python -m data.synthetic_generator --samples-per-theme 40 --output data/synthetic/synthetic_diaries.json
```

Para usar o modo Ollama, o serviço e o modelo precisam estar disponíveis previamente:

```text
uv run python -m data.synthetic_generator --ollama --samples-per-theme 40
```

A geração por LLM pode variar. Registre sua origem e confira o conteúdo antes de usá-lo como referência. Gerar novamente o dataset muda o experimento; conserve seus IDs, hash e configuração.

### 3. Treinar e avaliar

```text
uv run python -m models.train --epochs 40 --batch-size 32 --lr 0.001 --numpy-lr 0.05 --threshold 0.50
```

Por padrão, o comando carrega e concatena `data/real_diaries.json` e
`data/synthetic/synthetic_diaries.json`. É possível informar outro conjunto ou
mais de um conjunto com `--data-path arquivo1.json arquivo2.json`; IDs
duplicados são rejeitados. Os grupos continuam separados pelo `group_id` no
split, evitando que a mesma família/template atravesse treino, validação e teste.

O pipeline registra os resultados da execução atual. `classification_report.json`
mostra o desempenho bruto por argmax; `threshold_classification_report.json`
mostra separadamente a política de abstinência (`--threshold`). Os artefatos
locais ficam no diretório de saída; pesos e vetorizador precisam ser produzidos
antes de uma demonstração com o preditor padrão. Não adicionar esses arquivos ao
Git para fazer os testes passarem.

Além dos pesos e relatórios por classe, são gerados `comparison_report.json`, `split_manifest.json`, `learning_curves.json` e `best_numpy_mlp.npz`. O manifesto identifica os grupos de cada split e as versões do ensaio. Em empate de macro-F1 de validação, conserva-se o primeiro checkpoint.

A [validação de 09/11/2026](docs/neural-mvp-validation.md) registra a execução com split por famílias e suas baixas métricas. As correções de reprodução não demonstram que o classificador esteja pronto para uso real.

### 4. Executar uma previsão

Após o treinamento, use um relato inteiramente fictício:

```text
uv run python -m models.predictor --text "Hoje conversei com minha mãe e meu irmão sobre a organização da casa." --json
```

Para conferir a segmentação e as referências ao texto:

```text
uv run python -m models.predictor --text "Hoje conversei com minha mãe sobre a casa. Depois estudei para a prova." --destrinchar --json
```

Esses exemplos demonstram a interface, não resultados esperados garantidos. O teste de generalização deve incluir textos novos e ambíguos, além dos templates.

### 5. Consultar o MLflow

```text
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Abra `http://127.0.0.1:5000`. Consulte as perdas de treino/validação, configurações, métricas e artefatos da execução. Observe a origem dos dados e a regra de inferência antes de comparar runs.

### 6. Verificar testes e lint

```text
uv run ruff check .
uv run pytest -q
uv build
```

Os testes do preditor devem preparar suas próprias dependências ou injetar modelos controlados. Um clone limpo não deve exigir que alguém tenha treinado e mantido arquivos em `dist/` previamente. O resultado real do CI é a referência para a versão testada; este documento não fixa uma contagem de testes aprovados.

## Como interpretar e apresentar a avaliação

Apresentar macro-F1, precisão/recall por classe, matriz de confusão, erros e taxa de abstenção. Comparar NumPy, PyTorch e baseline com o mesmo conjunto de teste. Declarar os tamanhos dos conjuntos e a inexistência de grupos compartilhados. Quando houver poucas famílias independentes por categoria, registrar essa limitação.

Uma boa demonstração deve mostrar o fluxo que funciona, uma entrada ambígua, um caso de abstenção e um erro. Pontuações elevadas em templates sintéticos não demonstram desempenho em outros autores ou relatos reais.

O módulo contribui para os requisitos de rede neural, versionamento e MLOps. A conclusão do Challenge depende também da integração, do RAG, das demais evidências e da avaliação dos mentores. A interpretação acadêmica de construção do zero deve ser confirmada com a orientação.

## Arquivos principais

| Arquivo | Finalidade |
| --- | --- |
| [data/personas.json](data/personas.json) | Perfis fictícios para geração |
| [data/synthetic_generator.py](data/synthetic_generator.py) | Gerador offline ou por Ollama |
| [data/split.py](data/split.py) | Separação dos dados por grupos |
| [models/numpy_mlp.py](models/numpy_mlp.py) | Rede NumPy com derivadas explícitas |
| [models/torch_mlp.py](models/torch_mlp.py) | Rede de comparação PyTorch |
| [models/train.py](models/train.py) | Treinamento, avaliação e artefatos |
| [models/predictor.py](models/predictor.py) | Inferência e decomposição em segmentos |
| [mlops/tracker.py](mlops/tracker.py) | Registro de experimentos |

Os artefatos de treinamento, bancos locais e resultados voláteis permanecem ignorados pelo Git. A configuração de um perfil fictício não constitui adoção comprovada de um framework científico. Qualquer referência futura a PsychAdapter, Ulster ou outro trabalho deve incluir a publicação original exata e explicar quais procedimentos foram reproduzidos e quais não foram.
