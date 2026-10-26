# Challenge 2: Bem-Estar - Diário Emocional Inteligente

Protótipo acadêmico do time de seis pessoas da PUC-Campinas / Instituto Eldorado / TIC em
Trilhas. A proposta é organizar relatos voluntários entre sessões para apoiar o acompanhamento
humano. O público conceitual são adultos já acompanhados por psicólogo e profissionais
explicitamente autorizados pelo próprio paciente.

**A IA não é psicólogo, não diagnostica e não substitui atendimento profissional.** A hipótese
de utilidade ainda não foi validada. Este primeiro componente é um extrator/classificador de
metadados de **textos inteiramente sintéticos**, não um produto para pacientes.

## O que existe nesta entrega

`terminal → validação → Ollama local → JSON validado por Pydantic → SQLite → JSON no terminal`

- Um tema e um sentimento principais, a partir de listas fechadas.
- Um sinal de **indício textual**, com os estados `presente`, `nao_identificado` e
  `indeterminado`. Não mede gravidade, iminência ou segurança clínica.
- Separação entre indeterminação semântica e falhas de serviço, esquema ou persistência.
- SDK oficial Ollama, validação Pydantic e banco SQLite da biblioteca padrão.
- 100 casos sintéticos (60 desenvolvimento / 40 holdout) e avaliação reproduzível.
- Testes automatizados sem rede nem necessidade de baixar um modelo.

Não há conversa com usuário, encaminhamento de emergência, compartilhamento com psicólogo,
interface web ou coleta de relatos reais. Esses componentes são futuros. Um extrator isolado
não comprova o requisito de dois agentes trabalhando juntos.

## Instalação

Usar Python 3.12 e [uv](https://docs.astral.sh/uv/). Dentro deste clone:

```sh
uv sync --locked
cp .env.example .env
set -a
. ./.env
set +a
```

As variáveis são lidas do ambiente; o arquivo `.env` não é carregado automaticamente pelo
Python. O `.env` deste clone é apenas configuração do extrator: **não copiar o PAT da pasta
007-org para ele**.

Instalar o [Ollama oficial](https://ollama.com/download) compatível com sua máquina. Neste
checkout, um binário oficial verificado já foi instalado em `.local-runtime/ollama/ollama`;
para utilizá-lo neste terminal, executar `export PATH="$PWD/.local-runtime/ollama:$PATH"`.
O runtime local não faz parte do Git. Se o servidor desta implementação ainda estiver ativo
em 127.0.0.1:11434, não iniciar outro na mesma porta.

No primeiro terminal, com o ambiente acima carregado:

```sh
ollama serve
```

Em outro terminal no mesmo clone e com as mesmas variáveis, baixar os candidatos sequencialmente:

```sh
ollama pull qwen3:4b
ollama pull gemma3:4b
```

`OLLAMA_NO_CLOUD=1` precisa estar configurado **no processo do servidor** para desabilitar
recursos remotos. O cliente só aceita HTTP em loopback, não usa proxies de ambiente e rejeita
modelos com metadados de roteamento remoto. Não há fallback para APIs externas.

Os candidatos publicados são Qwen3 4B Q4_K_M (~2,5 GB) e Gemma 3 4B Q4_K_M (~3,4 GB).
Download não equivale à RAM total. No M1 com 8 GB, usar um modelo/requisição por vez, contexto
inicial de 2.048 tokens e poucos programas abertos. A escolha depende da avaliação real, não
somente do tamanho. Qwen usa licença Apache 2.0; Gemma tem termos próprios.

## Executar uma extração

```sh
printf '%s\n' 'Estou frustrado porque meu chefe cancelou minhas férias.' | uv run bem-estar-extract --synthetic
uv run bem-estar-extract --synthetic --file caminho/relato-inventado.txt
uv run python -m agents.extractor --synthetic --model gemma3:4b --db data/comparacao.sqlite3 < caminho/relato-inventado.txt
```

`--synthetic` confirma a origem inventada do texto; não é um detector de dados reais. Somente
usar exemplos de teste. Entrada UTF-8, não vazia, até 2.400 caracteres **e** 2.400 bytes. Não há
truncamento silencioso feito pelo cliente; respostas próximas ao limite de contexto são
rejeitadas conservadoramente, mas isso não é prova de completude semântica.

A saída normal é um objeto JSON em `stdout`. Exemplo de estrutura, não resultado garantido:

```json
{
  "status": "ok",
  "extraction": {
    "tema": "trabalho",
    "sentimento": "frustracao",
    "indicio_textual_risco": "nao_identificado"
  }
}
```

O objeto completo também inclui `id`, `created_at`, `error` e `metadata` com modelo, digest,
versões de prompt/esquema, contexto, tempo e identificação sintética. Em falha, `extraction`
é `null` e `error` contém código e mensagem sanitizada. Diagnósticos operacionais vão para
`stderr`, sem o texto da entrada. `--help` é a exceção convencional que exibe ajuda em texto.

| Exit code | Significado |
| --- | --- |
| 0 | Extração validada e persistida |
| 2 | Entrada, configuração ou processamento inválido/indisponível |
| 3 | Falha de persistência; não considerar a execução salva |

O banco guarda texto sintético, resultado, horário, versões, digest e estado. Execuções com
erro de modelo também são registradas quando o banco funciona; entrada inválida não é salva.
O arquivo SQLite novo é criado com permissão `0600`. Bancos existentes não sofrem migração
automática destrutiva; esquema incompatível gera erro.

## Semântica e limites

- **Temas:** `trabalho`, `familia`, `relacionamentos`, `estudos`, `saude`, `financas`, `luto`,
  `outros`, `nao_identificado`.
- **Sentimentos:** `alegria`, `tristeza`, `raiva`, `medo`, `preocupacao`, `frustracao`, `calma`,
  `nao_identificado`. São interpretações textuais, sujeitas a correção.
- **Sinal:** `presente` indica intenção/ação atual explícita do autor de causar dano a si;
  `indeterminado` cobre contexto insuficiente, inclusive menções históricas, negadas, figuradas
  ou de terceiros; `nao_identificado` significa ausência de referência identificada.

**`nao_identificado` não significa pessoa segura.** JSON válido não significa análise correta.
O extrator não é um fail-safe, uma triagem clínica ou um serviço de crise. Políticas para uso
com pessoas reais precisam de revisão profissional e avaliação ética/jurídica próprias.

“Jev-like” significa apenas inspiração em [estado e perguntas tipadas do Jev/TypeSafe](https://docs.typesafe.ai/introduction).
Não usamos Jev nem reproduzimos seu modelo. As decisões e a persistência são controladas pelo
código. [Pesquisa sobre os papéis de agentes](docs/agent-research.md).

## Testar e avaliar

```sh
uv run pytest -q
uv run ruff check .
uv run bem-estar-evaluate --models qwen3:4b gemma3:4b --split dev --limit 1 --repetitions 1 --output results/smoke.json
uv run bem-estar-evaluate --models qwen3:4b gemma3:4b --split dev --repetitions 3 --output results/dev.json
uv run bem-estar-evaluate --models qwen3:4b gemma3:4b --split holdout --repetitions 3 --output results/holdout.json
```

Os dois últimos comandos realizam 360 e 240 tentativas, respectivamente, e podem demorar no
hardware disponível. O runner tem checkpoint incremental; repetir o mesmo comando com
`--resume` retoma tentativas pendentes. Não editar o holdout para melhorar resultados. Modelos
são comparados sequencialmente e descarregados entre grupos.

[Metodologia e interpretação](docs/evaluation-method.md) · [Estado da avaliação real](docs/evaluation-results.md).
As referências esperadas foram geradas, ainda sem revisão independente de duas pessoas.
Nenhum resultado deste conjunto é evidência de validação clínica. Memória reportada pelo
Ollama não equivale ao pico de RAM ou à pressão de memória total da máquina.

## Estrutura e próximos passos

| Diretório | Finalidade |
| --- | --- |
| `agents/extractor/` | Contrato, configuração, modelo, CLI e SQLite |
| `evaluation/` | Avaliação reproduzível e métricas |
| `data/synthetic/` | Casos inventados e anotações preliminares |
| `tests/` | Testes automatizados isolados de serviços reais |
| `knowledge_base/` | Reservado para a futura base de conhecimento |
| `mlops/` | Reservado para a evolução de pipelines de experimentação |
| `models/` | Reservado para a rede neural a ser construída pelo grupo |
| `docs/` | Pesquisa, referências, avaliação e planejamento |

O uso de um LLM pronto não substitui construir e testar a rede neural exigida pelo Challenge.
Futuros agentes conversacional e sumarizador poderão consumir o contrato validado, sem
transferir julgamento clínico à IA. Ferramentas e dados dessas etapas ainda serão definidos.

[Requisitos do Challenge](docs/requirements.md) · [Referências](docs/references.md) ·
[Colaboração](CONTRIBUTING.md) · [Infraestrutura](docs/infrastructure.md) ·
[Instalação do Ponytail](docs/ponytail.md).

Não versionar credenciais, relatos reais, bancos locais, modelos baixados ou artefatos brutos
sem revisão. A questão orientadora é ampliar o potencial humano preservando autonomia,
sigilo e supervisão, nunca substituir o profissional.
