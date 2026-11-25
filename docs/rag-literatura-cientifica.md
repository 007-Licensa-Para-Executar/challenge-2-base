# RAG científico

O componente responde a uma pergunta sobre literatura já ingerida. Ele não atende o paciente, não lê o diário e não está ligado ao Agente 2.

A entrada pública é `search_literature(query, top_k=5, db_path=...)`, em `agents.copilot.literature`. Sem `db_path`, a função lê `LITERATURE_DB_PATH`. Se nenhum dos dois existir, a consulta para em `configuration_error` e não procura um arquivo em `/tmp` nem o catálogo de demonstração do shell.

Nenhum SQLite de literatura entra no repositório. A consulta não cria banco e não usa um caminho padrão.

## Chamada

```python
from agents.copilot.literature import search_literature

result = search_literature(
    "Quais limites éticos a inteligência artificial impõe à psicoterapia?",
    top_k=5,
    db_path="data/literatura.sqlite3",
)
```

A função só aceita a pergunta e o corte. Não há identificador de paciente. O recuperador é o BM25 já aprovado, com a diversificação e a suficiência quantitativa atuais. E5 não entra nesse caminho: um serviço configurado com esse backend devolve `configuration_error`.

Esta entrega não altera o shell. O comando `rag` da main permanece. A biblioteca não abre esse menu.

## Resposta

`LiteratureConsultation` separa o que foi ordenado do que pode ser citado.

| Campo | Conteúdo |
|---|---|
| `query_original` | Pergunta recebida |
| `status` | `evidence`, `insufficient_evidence`, `empty_corpus`, `configuration_error` ou `error` |
| `evidence_sufficient` | Verdadeiro somente quando `status` é `evidence` |
| `answer_extractive` | Trechos mantidos, sem síntese por modelo |
| `sources` | Citações que passaram na suficiência |
| `retrieved_passages` | Trechos depois da diversificação, antes do filtro de suficiência |
| `retrieval_backend` | `bm25` |
| `limitations` | O escore não é probabilidade; a resposta não é diagnóstico; não há número de página |

Cada `LiteraturePassage` traz `document_id`, `chunk_id`, `title`, `authors`, `year`, `doi`, `source_url`, `license`, `quote_text`, `start_char` e `end_char`. O `chunk_id` tem a forma `registro:início:fim`. O intervalo aponta para o texto autorizado. O pipeline não inventa página.

`evidence` exige ao menos uma fonte. `error` e `configuration_error` trazem `error_code` e não devolvem sucesso com texto vazio. Corpus sem documento utilizável é `empty_corpus`. Arquivo ausente, diretório ou caminho em branco é `configuration_error`. Arquivo ilegível é `error` com `storage_error`.

## Citação e abstenção

A citação visível repete o trecho e a origem: título, autores, ano e DOI ou URL. Documento sem DOI usa a URL. A bibliografia fica armazenada e fora da busca.

A abstenção ocorre quando o documento pedido não está no acervo, quando o BM25 não acha trecho, ou quando o filtro recusa os trechos ordenados. Nesse último caso, `retrieved_passages` pode continuar preenchido e `sources` fica vazio. O filtro exige dois termos da pergunta no mesmo trecho, e um termo só quando a pergunta tem um. Pergunta de quantidade (`quantas`, `quantos`, `quanta`, `quantidade`) ainda exige o número junto da unidade. Pergunta conceitual não exige número.

## Licença

`LiteratureStore.save` recusa texto sem licença reconhecida. Entram os demonstrativos sintéticos com hash fixo, os artigos do manifesto oficial cujo texto confere com o SHA-256, e o texto fictício de teste enquanto `PYTEST_CURRENT_TEST` e `LITERATURE_FIXTURES=1` estão ativos. Documento pendente ou negado não é gravado. A consulta não contorna essa porta.

## Limites conhecidos

O BM25 não recupera um trecho que não compartilha vocabulário com a pergunta. A expansão lexical foi medida e rejeitada: piorou a primeira posição e o MRR. A busca híbrida com `multilingual-e5-small` também foi rejeitada no benchmark de 18 perguntas: a Precision@1 caiu de 0,600 para 0,400 e o MRR de passagem de 0,719 para 0,594. O produto não carrega esse modelo.

O recall do benchmark é a cobertura das passagens anotadas, não do corpus. O filtro de dois termos pode descartar um trecho certo que use outras palavras. A checagem de quantidade não olha o trecho vizinho.

## Agente 2

A integração ainda não existe. O Agente 2 não deve enviar o relato do paciente. A camada de integração, quando for autorizada, traduz o tema para uma pergunta genérica, escolhe o `db_path` persistente e lê `sources` somente se `evidence_sufficient` for verdadeiro.
