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

## Protótipo no painel

A rota `POST /api/psicologa/literatura` chama esta biblioteca. Ela só existe no modo de desenvolvimento. Em produção, e quando `REQUIRE_PSICOLOGA_AUTH=true`, a resposta é 403. O painel da psicóloga não tem sessão própria. O cookie `diario_sessao` autentica o paciente e não autoriza esta consulta. Não há autenticação improvisada.

O navegador envia a pergunta e o corte. Não envia caminho de banco nem relato clínico. O processo Python é o do `.venv` desta worktree, com o módulo fixo `agents.copilot.literature_http`.

O ambiente local usa o lockfile do projeto, sem o extra de embeddings:

```bash
uv sync --locked --python 3.12
```

A base experimental fica em `data/literature_local.sqlite3`, fora do Git. Para reconstruí-la, confira o PDF e o texto de PT-001 e PT-002 com o manifesto e grave só esses dois, pela mesma porta de licença da biblioteca:

```bash
PYTHONPATH=. .venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
from agents.copilot.literature import (
    LITERATURE_MANIFEST, LiteratureStore, build_document, read_document,
)
root = Path(".").resolve()
target = root / "data" / "literature_local.sqlite3"
manifest = json.loads(LITERATURE_MANIFEST.read_text(encoding="utf-8"))
store = LiteratureStore(target)
body = 0
for item in manifest["documents"]:
    if item["document_id"] not in {"PT-001", "PT-002"}:
        continue
    if item.get("ingestion_approved") is not True:
        raise SystemExit(item["document_id"])
    pdf = root / item["file_path"]
    file_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    text = read_document(pdf)
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    if file_hash != item["sha256"] or text_hash != item["text_sha256"]:
        raise SystemExit(f"hash divergente em {item['document_id']}")
    document = build_document(
        document_id=item["document_id"], title=item["title"], authors=item["authors"],
        original_text=text, year=item["publication_year"], doi=item["doi"],
        url=item["source_url"], license=item["license"], synthetic=False,
    )
    store.save(document)
    body += sum(len(section.chunk_ids) for section in document.sections if section.role == "body")
if body != 136:
    raise SystemExit(f"corpo inesperado: {body}")
print(target)
PY
```

PT-003 e PT-004 permanecem fora. O manifesto não é alterado. Aponte `LITERATURE_DB_PATH` para `data/literature_local.sqlite3` e suba o Next em `127.0.0.1`, a partir de `ui/diario_paciente_next`. O pacote pede Node.js 22.13 ou mais novo. Nesta máquina, `nvm install 22` trouxe o 22.23.5 a partir de nodejs.org e o padrão do nvm continuou em 20.19.2. O `node:sqlite` abre sem flag e emite aviso de recurso experimental.

## Agente 2

A integração ainda não existe. O Agente 2 não deve enviar o relato do paciente. A camada de integração, quando for autorizada, traduz o tema para uma pergunta genérica, escolhe o `db_path` persistente e lê `sources` somente se `evidence_sufficient` for verdadeiro.
