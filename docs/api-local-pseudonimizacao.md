# API HTTP interna de pseudonimização

O modo protegido do copiloto envia o relato, o título e a pergunta à API
HTTP local da [tarefa #27](https://github.com/007-Licensa-Para-Executar/challenge-2-base/issues/27).
O servidor retorna texto tratado. O classificador e a busca recebem essa versão,
e o SQLite analítico guarda somente a representação tratada. As citações
apontam para documento, representação e posições de caracteres no texto tratado.

A demonstração usa dados sintéticos. Pseudonimização permite que a aplicação
associe o UUID a um nome por meio de informação separada. O detector pode
deixar identificadores passar, e fatos indiretos também podem identificar
pessoas. Este experimento demonstra o fluxo e mede erros observados.

## Quem faz a chamada

O cliente fica no **orquestrador do copiloto**. Ele faz a requisição antes de
entregar os dados ao Agente 1 ou ao fluxo de consulta. Assim, ambos os fluxos
usam a API no ponto em que recebem texto novo, com uma chamada por relato
ou pergunta. Os modelos recebem o texto já tratado.

| Uso | Ponto no código | Ordem de execução |
| --- | --- | --- |
| Agente 1, ingestão de diário | [`ingest` na CLI](../agents/copilot/cli.py) e [`protect_diary`](../agents/copilot/privacy_flow.py) | API trata relato e título → rede classifica se solicitada → `--subtopics` roda [`Agent1Service.process`](../agents/extractor/service.py) no texto tratado → SQLite guarda o diário tratado e o tema |
| Agente 2, consulta no protótipo | [`ask` na CLI](../agents/copilot/cli.py), [`protect_query`](../agents/copilot/privacy_flow.py) e [`CopilotService.answer`](../agents/copilot/service.py) | API trata pergunta → busca filtra por paciente e período → recupera evidências tratadas → mostra trechos ou gera resposta com Ollama |
| Preparar e listar | [`seed` e `list`](../agents/copilot/cli.py) | `seed` trata cada relato antes da importação. `list` lê registros previamente tratados, sem chamada HTTP |
| Nome e original para conferência | [CLI de identidade](../privacy/__main__.py) | Usa a credencial de identidade para consultar o cofre por UUID |

O [cliente HTTP](../privacy/client.py) abre a conexão. O
[servidor FastAPI](../privacy/server.py) valida a credencial, aplica o detector
e usa o [cofre](../privacy/vault.py). O [shell](../app/rag_shell.py) invoca
a CLI no modo protegido e passa relatos e perguntas por stdin.

A extração opcional entrega `agent1` no JSON da ingestão. Seus offsets
referem-se a `treated_text`, e o resultado traz o `representation_id` do
diário no mesmo JSON. O banco analítico mantém o diário e o tema. O RAG
consulta esse registro e suas citações, sem depender de persistir a saída
de subtemas. Em falha nessa extração opcional, o comando retorna erro antes
da gravação analítica de um novo diário. O original já aceito pode ficar no cofre.

O modo protegido é ativado por `--privacy` no shell ou na CLI do copiloto.
A chamada `bem-estar-extract` e os fluxos independentes do diário Next,
do worker de transcrição e da ponte de demonstração seguem contratos próprios.
A [especificação do correlacionador longitudinal](agente2.md) descreve um escopo
mais amplo que a consulta RAG implementada aqui.

## Iniciar o serviço

Na raiz do checkout, em macOS, Linux ou Windows CMD:

```text
uv sync --locked --extra privacy --python 3.12
uv pip install --no-deps https://github.com/explosion/spacy-models/releases/download/pt_core_news_lg-3.8.0/pt_core_news_lg-3.8.0-py3-none-any.whl
uv run --no-sync python -c "import pt_core_news_lg as m; from pathlib import Path; print(Path(m.__file__).parent / 'pt_core_news_lg-3.8.0')"
uv run --no-sync python -m privacy init
uv run --no-sync python -m privacy serve --model-path "COLE O CAMINHO IMPRESSO"
```

O download é explícito e requer rede na preparação. O servidor carrega o
modelo local e escuta em `127.0.0.1:8001`. Um modelo ausente ou inválido impede
o início. Repita a instalação do modelo se uma sincronização futura do uv o
remover. [Distribuição oficial do modelo](https://github.com/explosion/spacy-models/releases/tag/pt_core_news_lg-3.8.0)

Em outro terminal, na mesma raiz:

```text
uv run --no-sync python -m privacy register-demo
uv run --no-sync bem-estar --privacy
```

1. Confirme dados sintéticos. Use `/rag` → `preparar`. Escolha a classificação
   se já tiver rodado `/rag` → `treinar` com o dataset sintético.
2. Use `/rag` → `perguntar`, selecione `patient_ana`, deixe o período em branco
   e pergunte “Quais cuidados dos avós foram descritos?”. Use `extractive` na
   primeira execução. Para usar o gerador, inicie o Ollama local e escolha
   `ollama`.
3. Pare o servidor de privacidade e repita a consulta. O modo protegido
   interrompe o fluxo. A listagem de registros já tratados continua disponível.
4. Veja o nome fictício pela camada de apresentação com
   `uv run --no-sync python -m privacy name UUID`. Use um UUID mostrado por
   `register-demo`. Para conferir um documento, use
   `uv run --no-sync python -m privacy original UUID ID_DO_DIARIO`.

O equivalente pela CLI é `bem-estar-copilot seed --synthetic --privacy` e
`bem-estar-copilot ask --privacy --question-stdin --patient-id patient_ana --generation extractive`.
Forneça a pergunta por stdin. O formulário do shell já usa esse caminho.
O modo protegido usa comandos com barra e coleta a pergunta no formulário.

Para demonstrar o Agente 1, abra `/rag` → `registrar`, habilite a
classificação e confirme a extração de subtemas. Use Ollama local com o
modelo configurado no shell. Pela CLI, use `bem-estar-copilot ingest`
com `--synthetic --privacy --classify --subtopics`, `--patient-id`,
`--at`, `--model-path` e `--vectorizer-path`. Envie o relato por stdin
ou por arquivo com `--file`. Treine os pesos antes com `/rag` → `treinar`.

## Contrato HTTP

Base padrão `http://127.0.0.1:8001`. As requisições usam
`Authorization: Bearer <token>` e os POSTs usam JSON. Os campos são
definidos em [`privacy/contracts.py`](../privacy/contracts.py).

| Método e caminho | Credencial | Entrada | Resposta de sucesso |
| --- | --- | --- | --- |
| `POST /v1/pseudonymize` | Analítica | `patient_id` (UUID v4), `text`, `synthetic: true`. Opcionais `record_id` e `title` | `patient_id`, `record_id`, `text` e `title` tratados, `representation_id`, `detector_version` e `schema_version` |
| `POST /v1/identity/patients` | Identidade | `patient_key` (chave opaca estável), `display_name`, `synthetic: true` | `patient_id` |
| `GET /v1/identity/patients/{patient_id}` | Identidade | UUID v4 no caminho | `display_name` |
| `GET /v1/identity/patients/{patient_id}/records/{record_id}` | Identidade | UUID v4 e ID do diário no caminho | `text` e `title` originais do diário |

Envie `record_id` para um diário. O serviço mantém o original cifrado e
reaproveita a representação ao repetir o mesmo conteúdo com o mesmo ID e
versão do detector. Para perguntas, omita `record_id` e `title`. A API devolve
a pergunta tratada sem criar diário nem vínculos permanentes.
Exemplo de corpo com um UUID fictício que precisa ser cadastrado antes do teste:

```json
{
  "patient_id": "f1e6b6e4-283a-42e6-8009-184449a8b254",
  "text": "O que o relato disse sobre os cuidados com a avó?",
  "synthetic": true
}
```

A API devolve `401` para credencial ausente, incorreta ou de outra
capacidade, `404` para paciente ou diário ausente, `409` para conflito,
`413` para corpo acima de 256.000 bytes, `422` para entrada inválida e
`503` para falha de processamento ou armazenamento. O cliente analítico
usa timeout de 10 segundos e recusa uma resposta incompatível com o paciente
ou o diário solicitado. Esses erros interrompem a operação.

## Armazenamento e acesso

O serviço detecta CPF, telefone e e-mail por regras e usa Presidio com spaCy
em português para pessoas, locais e organizações. CPF, telefone e e-mail
recebem tags genéricas. O vínculo de entidades usa grafia normalizada dentro
de um paciente. Um primeiro nome isolado recebe tag genérica. Mesmo um nome
completo igual pode referir-se a pessoas diferentes, portanto o token é uma
correspondência textual. O cofre guarda originais, nomes e associações
cifrados com Fernet e mantém o UUID aleatório independente da chave.

`init` cria credenciais diferentes e uma chave no diretório local ignorado
`data/privacy/`. Restrinja a conta e as permissões do diretório a quem opera
o protótipo. Os tokens separam capacidades nas rotas. Processos com acesso à
mesma conta e arquivos locais compartilham as permissões dessa conta. A
demonstração tem um operador de identidade e não inclui autenticação Flutter.
Para rotação, o servidor aceita uma chave nova seguida das antigas no arquivo
local. Escritas usam a primeira chave e dados antigos continuam requerendo
suas chaves até uma recriptografia explícita.

Timeout, erro HTTP e resposta incompatível interrompem a análise. Uma importação
em lote trata todos os relatos antes de gravar no banco analítico. O cofre
pode reter originais já aceitos se uma etapa posterior falhar. Repetir a
importação com os mesmos IDs, conteúdo e versão reaproveita as representações.
Bancos legados permanecem separados. Para demonstrar novamente com outra
versão do detector, crie um diretório e uma base de demonstração novos.

## Validação e resultados

Execute o benchmark com o mesmo caminho do modelo:

```text
uv run --no-sync python -m evaluation.privacy --model-path "CAMINHO DO MODELO"
```

No ensaio de 18/11/2026 com Presidio 2.2.362, spaCy 3.8.18 e
`pt_core_news_lg` 3.8.0, houve 26 acertos exatos, 4 falsos positivos e 3
falsos negativos em 22 casos com 29 entidades anotadas. Precisão micro
de **86,7%** e recall de **89,7%**.

| Entidade | Acertos | Falsos positivos | Falsos negativos |
| --- | ---: | ---: | ---: |
| Pessoa | 8 | 1 | 0 |
| Organização | 3 | 0 | 2 |
| Local | 4 | 3 | 1 |
| CPF | 2 | 0 | 0 |
| Telefone | 4 | 0 | 0 |
| E-mail | 5 | 0 | 0 |

O ensaio HTTP com o modelo real importou 20 relatos e classificou os mesmos
20 também no fluxo original, com os mesmos pesos. Um tema mudou de
`outros_indeterminado` para `familia`. A consulta sobre os avós retornou os
mesmos três documentos (`ana_03`, `ana_01`, `ana_05`) nos dois fluxos.
São observações desse conjunto, sem estimativa de ganho de acurácia.

A suíte exercita o servidor HTTP em loopback com detector controlado, regras
de detecção, escopo de paciente, credenciais, reinício, rotação, idempotência,
preservação cifrada e referências. A matriz existente do projeto roda os
testes em Ubuntu, macOS e Windows CMD sem baixar o modelo spaCy.
