# Challenge 2: Bem-Estar - Diário Emocional Inteligente

## Demonstração de pesquisa: rede + RAG no shell

Na pasta do repositório, no macOS/Linux ou no **CMD do Windows**:

```text
uv sync --locked --python 3.12
uv run bem-estar
```

Confirme dados fictícios com `s`. Digite `/rag` e siga estas ações (uma por vez):

1. `treinar`: treina as redes com o dataset sintético e salva em `dist/rag-demo/`.
2. `preparar` → `sim`: classifica e importa 20 diários fictícios em um banco novo.
3. `perguntar` → `patient_ana` → Enter nos dois limites de data →
   `Quais cuidados dos avós foram descritos?` → `extractive` → `s`.
4. Confira os trechos originais, datas e identificadores apresentados como fontes.
5. Repita com `ollama` para síntese pelo Qwen local, ou escolha `avaliar` para métricas.

O treino e a resposta `extractive` funcionam **sem Ollama**. Para a síntese `ollama`,
inicie o serviço conforme o quick start abaixo e instale `qwen3:4b` explicitamente
com `ollama pull qwen3:4b`, uma única vez. Nada é baixado automaticamente pelo menu.
Pesos e bancos são locais: cada integrante deve treinar/preparar sua própria demonstração.
O banco preparado fica selecionado até sair do shell; a próxima sessão começa no banco
padrão `data/copilot_demo.sqlite3`. Os caminhos aparecem antes das ações.

Trata-se exclusivamente de um **protótipo acadêmico**, sem uso com pessoas reais.
As previsões são experimentais e podem errar. Veja o
[roteiro completo e as limitações](docs/rag-mvp-integrado-rede.md).

> **MVP de RAG + rede temática:** consulta de diários inteiramente fictícios por pessoa e período, com fontes originais. Comece pelo [guia de integração e demonstração](docs/rag-mvp-integrado-rede.md). A recuperação extrativa funciona sem pesos ou Ollama; embeddings e síntese local são modos explícitos. Consulte as limitações e os resultados dos experimentos antes de interpretar as saídas.

> **MVP de classificação temática:** gerador de relatos fictícios, redes NumPy e PyTorch e avaliação com rastreamento no MLflow. As métricas são experimentais e devem ser obtidas com os grupos de origem separados.
> Consulte [README_MVP.md](README_MVP.md) para instalação, treinamento, inferência e limitações.

## Quick start: abrir e usar

Abra os terminais na pasta `challenge-2-base`. É preciso ter **uv, Python 3.12 e Ollama**;
se ainda não instalou, veja as instruções de instalação mais abaixo. Use somente relatos sintéticos.

**1. Terminal 1: iniciar o Ollama após reiniciar o computador.**
Se o Ollama já estiver aberto e disponível, pule este passo. Escolha apenas uma opção e
deixe esse terminal aberto enquanto usa o aplicativo:

macOS / Linux, com `ollama` instalado no PATH:

```sh
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

Neste Mac, se aparecer `command not found: ollama`, use o runtime local já instalado:

```sh
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS="$PWD/.local-runtime/models" OLLAMA_NO_CLOUD=1 ./.local-runtime/ollama/ollama serve
```

O diretório `.local-runtime` não vem no clone: essa alternativa só funciona onde o binário
e os modelos locais já foram instalados. Nos outros computadores, instale o Ollama normalmente.

Windows, no CMD, com `ollama` instalado no PATH:

```bat
set "OLLAMA_HOST=127.0.0.1:11434"
set "OLLAMA_NO_CLOUD=1"
ollama serve
```

Se aparecer que a porta `11434` já está em uso, não inicie outro servidor: confira `/status`
no aplicativo. O Ollama também pode já estar rodando como aplicativo em segundo plano.

**2. Terminal 2: preparar as dependências e abrir o menu.**

Os mesmos comandos funcionam no macOS, Linux e CMD:

```text
uv sync --locked --python 3.12
uv run bem-estar
```

Depois da primeira instalação, basta `uv run bem-estar`. O comando usa o ambiente Python do
projeto; não é necessário ativar a `.venv` manualmente nem fornecer um PAT do GitHub.

**3. No aplicativo: confirme `s` para dados sintéticos e use os comandos com barra.**

| Comando | Para começar |
| --- | --- |
| `/status` | Conferir conexão com Ollama, modelos e banco |
| `/extrair` | Digitar um relato inventado e confirmar a gravação |
| `/historico` | Consultar os resultados locais |
| `/ajuda` | Ver todos os comandos e atalhos |
| `/sair` | Encerrar diretamente, sem depender do roteador |

Se aparecer **`Ollama local indisponível`**, confira se o Terminal 1 continua aberto.
Se o modelo não estiver instalado, baixe-o uma vez com o servidor ativo, em outro terminal:

```text
ollama pull qwen3:4b
ollama pull qwen3:0.6b
```

Neste Mac sem `ollama` no PATH, use `./.local-runtime/ollama/ollama` no lugar de `ollama`
nesses comandos. O modelo 4B faz a extração; o 0.6B interpreta pedidos em linguagem natural.
Os comandos com barra dispensam o roteador, mas `/extrair` ainda precisa do servidor e do 4B.

Protótipo acadêmico do time de seis pessoas da PUC-Campinas / Instituto Eldorado / TIC em
Trilhas. A proposta é organizar relatos voluntários entre sessões para apoiar o acompanhamento
humano. O público conceitual são adultos já acompanhados por psicólogo e profissionais
explicitamente autorizados pelo próprio paciente.

**A IA não é psicólogo, não diagnostica e não substitui atendimento profissional.** A hipótese
de utilidade ainda não foi validada. Este primeiro componente é um extrator/classificador de
metadados de **textos inteiramente sintéticos**, não um produto para pacientes.

## O que existe nesta entrega

`shell/CLI → validação → Ollama local → JSON validado por Pydantic → SQLite → JSON no terminal`

- Um tema e um sentimento principais, a partir de listas fechadas.
- Polaridade determinística paralela com VADER e léxico heurístico em português; distância
  e divergências extremas ficam no bloco `validation` e em colunas auditáveis do SQLite.
- Um sinal de **indício textual**, com os estados `presente`, `nao_identificado` e
  `indeterminado`. Não mede gravidade, iminência ou segurança clínica.
- Separação entre indeterminação semântica e falhas de serviço, esquema ou persistência.
- SDK oficial Ollama, validação Pydantic e banco SQLite da biblioteca padrão.
- 100 casos sintéticos (60 desenvolvimento / 40 holdout) e avaliação reproduzível.
- Testes automatizados sem rede nem necessidade de baixar um modelo.

Não há conversa terapêutica com usuário, encaminhamento de emergência, compartilhamento com psicólogo,
interface web ou coleta de relatos reais. Esses componentes são futuros. Um extrator isolado
não comprova o requisito de dois agentes trabalhando juntos.

## Menu principal

Dentro do clone, execute **`uv run bem-estar`**. O shell é uma bancada para o time desenvolver
com dados sintéticos; não é um chatbot para pacientes. As CLIs JSON anteriores continuam disponíveis.

| Comando | Ação |
| --- | --- |
| `/ajuda` | Comandos, atalhos e exemplos |
| `/status` | Ollama, modelos locais e banco |
| `/extrair` | Formulário de relato sintético e confirmação antes de salvar |
| `/historico` | Registros locais, 10 por página; não cria banco ausente |
| `/modelos` | Listar e escolher extrator ou roteador para a sessão |
| `/avaliar` | Smoke (3 casos dev, 1 repetição), dev ou holdout; retomada de checkpoint |
| `/testes` | Executar a suíte automatizada com confirmação |
| `/config` | Consultar e alterar contexto, timeouts e caminho do banco na sessão |
| `/limpar` | Limpar a tela sem apagar arquivos |
| `/sair` | Encerrar |

Digite `/` no início para abrir o menu. Setas navegam, Tab completa, Enter seleciona e
Esc fecha as sugestões (fora delas cancela o formulário). Ctrl+C interrompe a operação e
retorna ao menu; EOF também encerra. A conversa usa o scrollback do terminal e não é salva
pelo aplicativo. Preferências também ficam apenas em memória. O terminal pode manter seu
próprio scrollback; limpar a tela não é apagamento seguro.

Confirme dados exclusivamente sintéticos uma vez por sessão. Sem confirmar, somente ajuda,
status e saída ficam disponíveis. Para corrigir um formulário, recuse a proposta ou use
Ctrl+C e abra o comando novamente. O texto do relato é literal, inclusive `/sair` ou instruções.

Também é possível pedir **“ver status do ambiente”**: Qwen3 0.6B propõe uma ferramenta e
argumentos validados; o shell mostra os detalhes e pede confirmação. Campos faltantes são
coletados por formulário. Somente uma ação é executada; nunca há encadeamento automático.
Pedidos sem intenção clara, compostos ou fora do menu pedem esclarecimento. Um filtro
conservador restringe as intenções antes do modelo e pode rejeitar frases legítimas: reformule
ou use a barra. Esse filtro não é uma prova de segurança. A fronteira de execução é a lista
fechada de ferramentas e argumentos, seguida da confirmação humana.

O roteador recebe só o pedido atual e o catálogo de ferramentas, sem histórico, PATs ou arquivos
`.env`. Seus processos recebem um ambiente reduzido, sem credenciais herdadas. Não há download
ou fallback automático. Se o modelo não estiver instalado ou falhar (timeout inicial de 15s),
os comandos com barra continuam disponíveis. Qwen3 4B permanece o extrator. `/config` não muda
arquivos; `/modelos` muda os modelos somente nesta sessão.

## Instalação no macOS / Linux (zsh ou bash)

Instale Python 3.12, [uv](https://docs.astral.sh/uv/) e [Ollama](https://ollama.com/download).
Entre no clone:

```sh
uv sync --locked --python 3.12
cp -n .env.example .env
uv run bem-estar
```

Os padrões funcionam sem carregar `.env`. Para alterar uma opção neste terminal:

```sh
export EXTRACTOR_MODEL=qwen3:4b
export SHELL_ROUTER_MODEL=qwen3:0.6b
```

## Instalação no Windows (CMD nativo)

Instale Python 3.12, uv e o [Ollama para Windows](https://docs.ollama.com/windows).
Abra **Prompt de Comando (CMD)**, entre no clone (use `cd /d` para mudar de unidade):

```bat
cd /d "C:\Projetos\challenge-2-base"
uv sync --locked --python 3.12
if not exist .env copy .env.example .env
set "EXTRACTOR_MODEL=qwen3:4b"
set "SHELL_ROUTER_MODEL=qwen3:0.6b"
uv run bem-estar
```

Não é necessário ativar venv, usar PowerShell, Git Bash ou WSL. O aplicativo usa UTF-8 e
não depende de cores ou emojis. Em consoles antigos com exibição incorreta de acentos,
experimente `chcp 65001` e uma fonte Unicode; isso não substitui salvar os arquivos em UTF-8.

## Modelos e configuração local (todas as plataformas)

Com o Ollama já aberto, baixe manualmente os modelos desejados; não inicie outro servidor
se `/status` já indicar disponibilidade:

```text
ollama pull qwen3:0.6b
ollama pull qwen3:4b
```

Gemma 3 4B é comparação opcional: `ollama pull gemma3:4b`. O shell nunca baixa modelos.
Se precisar iniciar o daemon manualmente, use `ollama serve` em outro terminal. Para desativar
recursos remotos, configure `OLLAMA_NO_CLOUD=1` no **processo do servidor** antes de iniciá-lo
(`export OLLAMA_NO_CLOUD=1` no Unix; `set "OLLAMA_NO_CLOUD=1"` no CMD). Uma variável definida
no CMD atual não altera um Ollama que já estava aberto. O cliente só aceita HTTP em loopback,
não usa proxies e rejeita metadados de roteamento remoto.

As variáveis são lidas do ambiente; `.env` não é carregado automaticamente. O arquivo é um
exemplo de configuração, **sem PAT**. Não copie o token da pasta `007-org` para este clone.
Consulte `.env.example` para modelos, contexto, timeouts e banco. Não é preciso um token GitHub
para executar o app. Não use `source` em arquivos de ambiente que contenham credenciais.

No M1 com 8 GB, use uma requisição por vez e contexto inicial de 2.048 tokens. O tamanho do
download não equivale à RAM necessária. A seleção do extrator continua dependente de avaliação;
usar modelos prontos não substitui construir a rede neural exigida pelo Challenge.

## Executar uma extração

Os comandos abaixo também funcionam no CMD. Crie o arquivo de entrada em um editor e salve
em UTF-8; caminhos com espaços devem estar entre aspas.

```text
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
  },
  "validation": {
    "nlp_polaridade": "NEGATIVO",
    "nlp_score": -0.62,
    "discrepancia_detectada": false,
    "distancia_polaridade": 0.38
  }
}
```

`validation` compara o score composto do VADER com uma âncora de polaridade do sentimento do
LLM (`alegria`: +1; sentimentos negativos: -1; `calma` e `nao_identificado`: 0). A distância
é absoluta; a divergência só é marcada quando os lados discordam e ambos são extremos
(âncora de pelo menos 0,6 e score VADER de magnitude mínima 0,7). O score `compound` fica
entre -1 e +1: não é porcentagem, probabilidade ou intensidade clínica. Neste projeto,
`nlp_polaridade` usa os limiares `-0,05` e `+0,05`; portanto, `0,5423` já é positivo, não
quase neutro. A regra de discrepância continua sendo uma checagem heurística, não uma medida de
confiança ou uma correção automática do LLM.

Essa arquitetura é uma **validação híbrida (LLM + PLN determinístico)**, não
*LLM-as-a-Judge*. No *LLM-as-a-Judge*, outro modelo de linguagem avalia a resposta do primeiro.
Aqui, o extrator chama o Qwen uma vez, enquanto o VADER calcula a polaridade por léxico e
regras; não há uma segunda inferência de linguagem nem tokens adicionais para um juiz. A análise
VADER roda em uma thread separada durante a chamada ao modelo, usando CPU, e pode ter seu tempo
parcialmente sobreposto à inferência do Ollama. Portanto, ela tende a acrescentar pouco tempo
perceptível em relatos curtos, mas não é literalmente gratuita nem há garantia de que todo o
custo fique oculto na latência.

A combinação oferece uma segunda medida, determinística e reproduzível, com limitações
diferentes das do LLM. Isso pode destacar alguns desacordos sem depender da avaliação de outra
IA generativa, mas não prova que o LLM alucinou nem que o VADER está certo: ambos podem errar,
e a regra compara apenas polaridade geral, não o contexto completo ou a correção de toda a
extração. A divergência serve para auditoria e análise posterior, não para corrigir o resultado
automaticamente ou orientar decisões clínicas.

O léxico em português é pequeno, explícito e não treinado; suas entradas foram conferidas
contra vocabulário do split `dev` sintético, sem ajustar o holdout. Foram incluídas algumas
formas observadas de alegria, frustração, preocupação e calma, mas essa cobertura não equivale
a uma avaliação independente nem torna o léxico completo. Regras de idioma, negação e
intensificadores (incluindo “tão”) também são heurísticas. A saída não é validada para uso clínico
e pode errar com ironia, contexto, variações regionais e palavras fora do léxico. A extração do LLM
continua intacta. A justificativa e os limites da validação híbrida estão em
[docs/agent-research.md](docs/agent-research.md) e [docs/evaluation-method.md](docs/evaluation-method.md).
O objeto completo também inclui `id`, `created_at`, `error` e `metadata` com modelo, digest,
versões de prompt/esquema, contexto, tempo e identificação sintética. Em falha, `extraction` é
`null` e `error` contém código e mensagem sanitizada. Diagnósticos operacionais vão para
`stderr`, sem o texto da entrada. `--help` é a exceção convencional que exibe ajuda em texto.

| Exit code | Significado |
| --- | --- |
| 0 | Extração validada e persistida |
| 2 | Entrada, configuração ou processamento inválido/indisponível |
| 3 | Falha de persistência; não considerar a execução salva |

O banco guarda texto sintético, resultado, polaridade, score, divergência, distância, horário,
versões, digest e estado. Bancos da versão 1 são migrados aditivamente na primeira gravação;
as colunas de validação de registros antigos permanecem nulas. Execuções com
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

## O que vai para o GitHub

O `.gitignore` é específico deste protótipo. Ele exclui ambientes virtuais, caches, runtimes e
ferramentas locais, bancos SQLite e seus arquivos auxiliares, pesos de modelos, executáveis,
arquivos compactados, logs, checkpoints e resultados brutos. Também exclui configurações
pessoais de editor e arquivos do sistema operacional.

Em `data/`, somente `synthetic/README.md`, `synthetic/dev.jsonl` e `synthetic/holdout.jsonl`
são compartilhados. Outros dados locais ficam ignorados por padrão. Novos datasets para
compartilhamento exigem revisão de conteúdo e ajuste explícito dessas regras. Nunca colocar
relatos reais nos dois arquivos sintéticos permitidos: o Git não consegue verificar sua origem.

Permanecem versionados o código, os testes, a documentação, as skills do projeto, o workflow
de CI, `pyproject.toml`, **`uv.lock`** e **`.env.example`**. O lockfile é necessário para
reproduzir as dependências; o exemplo de ambiente contém apenas configuração, sem credenciais.
Resultados selecionados para discussão podem ser resumidos em `docs/`, após revisão.

Antes de publicar:

```sh
git status --short
git diff --cached --stat
git ls-files -ci --exclude-standard
```

O último comando deve ficar sem saída: ele identifica arquivos já versionados que agora
correspondem ao `.gitignore`. Ignorar um arquivo não o remove do histórico nem impede
`git add -f`; sempre revisar o conteúdo do commit. Se uma credencial já tiver sido publicada,
removê-la em um novo commit não substitui revogá-la.

As verificações do shell e seus limites estão em [docs/shell-validation.md](docs/shell-validation.md).
O CI executa testes e build com Python 3.12 em Ubuntu, macOS e Windows; as etapas Windows
usam explicitamente CMD. Os modelos são simulados no CI. Não há vencedor declarado para o extrator.

## Estrutura e próximos passos

| Diretório | Finalidade |
| --- | --- |
| `app/` | Shell, propostas tipadas, roteador e processos canceláveis |
| `agents/extractor/` | Contrato, configuração, modelo, CLI e SQLite |
| `evaluation/` | Avaliação reproduzível e métricas |
| `data/synthetic/` | Casos inventados e anotações preliminares |
| `tests/` | Testes automatizados isolados de serviços reais |
| `knowledge_base/` | Reservado para a futura base de conhecimento |
| `mlops/` | Pipeline de experimento, tracking MLflow e gate por F1 macro |
| `models/` | Baseline e rede MLP de sentimento, com métricas compartilhadas |
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
