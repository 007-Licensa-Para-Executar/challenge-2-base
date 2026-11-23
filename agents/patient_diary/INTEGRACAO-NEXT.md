# Diário — contrato para o Next.js

Isto descreve o backend que já existe. Rotas sob “Propostas” ainda não existem. Não há autenticação. O ator gravado é sempre `paciente-ficticio`, constante do servidor. Um `patient_id` enviado pelo browser é ignorado e não prova identidade.

Base local: `http://127.0.0.1:8765`. O processo escuta em `127.0.0.1`, salvo `DIARY_BIND` dentro do container. Não publicar esta porta.

O Next.js não abre o SQLite, não lê caminho de arquivo e não chama `POST /worker`.

## Rotas existentes

| Método | Caminho | Quem usa |
| --- | --- | --- |
| `POST` | `/api/texto` | Next.js. JSON. |
| `POST` | `/api/audio` | Next.js. Multipart, resposta sempre JSON. |
| `GET` | `/api/historico` | Next.js. JSON. |
| `POST` | `/audio` | Página HTML. JSON só se o pedido mandar `Accept: application/json`. |
| `OPTIONS` | `/api/texto`, `/api/audio`, `/api/historico` | Preflight do browser. |
| `GET` | `/` | Página HTML local. Não é a API. |
| `POST` | `/texto` | Formulário HTML `application/x-www-form-urlencoded`, campo `texto`. Responde `303`. |
| `POST` | `/worker` | Operador local, sem browser. Uma passagem da fila e `303`. O Next.js não chama. |
| `POST` | `/transcrever?ext=` | Prévia do operador local. Corpo cru, `text/plain`. Não grava relato. |
| `OPTIONS` | `/transcrever` | Só o mesmo operador local. |

`OPTIONS /audio` não existe. O Next.js usa `/api/audio`, que tem preflight. Um cabeçalho `Authorization` futuro ainda não é anunciado: hoje o preflight só libera `Content-Type`.

`POST /worker` e `POST /transcrever` respondem `403 {"error": "operator_only"}` quando o pedido traz `Origin`, `Sec-Fetch-Site` ou `Sec-Fetch-Mode`, e também quando o processo não está preso a `127.0.0.1` ou `localhost`. Isso não é login. Um programa na própria máquina, sem esses cabeçalhos, ainda alcança os dois. O Next.js não deve encaminhá-los.

## Texto

`POST /api/texto`

- `Content-Type: application/json`
- Corpo: `{"text": "Relato fictício."}`
- Campos extras, inclusive `patient_id` e humor, são ignorados.
- Texto vazio ou só espaços: `400 {"error": "empty_text"}`
- `text` ausente ou não string: `400 {"error": "invalid_text"}`
- JSON inválido: `400 {"error": "invalid_json"}`
- Mais de 20 000 caracteres: `400 {"error": "text_too_long"}`
- Outro `Content-Type`: `415 {"error": "unsupported_type"}`
- `Content-Length` acima de 96 KiB: `413 {"error": "payload_too_large"}`
- Sucesso `201`:

```json
{"id": "d5d5070112279c41", "created_at": "2026-11-18T19:54:59.208020+00:00", "kind": "written", "status": "ready"}
```

`created_at` é ISO 8601 com fuso. Texto já nasce `ready`.

## Áudio

`POST /api/audio` é a rota do Next.js.

- `Content-Type: multipart/form-data`, campo de arquivo `name="audio"`
- A resposta é JSON em todos os casos. Não depende de `Accept`.
- Outro `Content-Type`: `415 {"error": "unsupported_type"}`
- O nome original do arquivo não é gravado.
- Vazio: `empty_audio`. Acima de 25 MB, ou corpo HTTP acima de 26 MB: `audio_too_large`. Duração acima de 10 minutos: `audio_too_long`. Mesmo conteúdo já gravado: `duplicate_audio`.
- Formato aceito pelo probe: WAV, MP3, M4A e também OGG, WebM, MP4, MOV e 3GP quando o ffprobe reconhece trilha de áudio sem vídeo. Fora isso: `invalid_audio`.
- Erro JSON: `400 {"error": "<código>"}`.
- Sucesso `201`:

```json
{"id": "d26f356f5c03811d", "created_at": "2026-11-18T19:54:59.319950+00:00", "kind": "audio", "status": "queued", "duration_seconds": 3.91}
```

Estados do áudio: `queued`, `processing`, `ready`, `failed`. A resposta do envio é sempre `queued`. O servidor, nesse pedido, esvazia a fila no próprio processo com o worker e o Faster-Whisper já existentes. Até três tentativas; depois o estado fica `failed` e a transcrição vem vazia.

`POST /audio` continua sendo a página local. Sem `Accept: application/json`, responde `303` para `/?aviso=audio_gravado` ou `/?erro=<código>` e não parte o worker. Com esse `Accept`, o comportamento é o mesmo JSON de `/api/audio`. A página não tem mais botão de transcrever.

## Histórico

`GET /api/historico`

```json
{
  "entries": [
    {
      "id": "d5d5070112279c41",
      "created_at": "2026-11-18T19:54:59.208020+00:00",
      "kind": "written",
      "status": "ready",
      "text": "Relato fictício de integração. Nenhuma pessoa real.",
      "transcript": ""
    },
    {
      "id": "d26f356f5c03811d",
      "created_at": "2026-11-18T19:54:59.319950+00:00",
      "kind": "audio",
      "status": "ready",
      "text": "",
      "transcript": "A paz e a intifique tis a marina não é lá por favor.",
      "duration_seconds": 3.91
    }
  ],
  "order": "oldest_first",
  "limit": 100,
  "truncated": false
}
```

Ordem do banco: `created_at` crescente e, na mesma data, `id` crescente. No máximo os 100 mais recentes; `truncated: true` avisa o corte. A interface pode inverter a lista para mostrar o mais novo primeiro.

Áudio só traz `transcript` quando `status` é `ready`. O JSON não inclui `patient_id`, caminho, hash, reserva do worker nem `error_code`. Em `failed`, mostrar uma falha genérica e manter o áudio como original. Consultar de novo enquanto houver `queued` ou `processing`. O relato continua no SQLite depois de reiniciar o processo.

`patient_id` na query é ignorado.

## Erros comuns a todas as rotas

- `Host` diferente de `127.0.0.1:<porta>` ou `localhost:<porta>`: `421 {"error": "invalid_host"}`
- `Origin` que não seja `http://127.0.0.1` ou `http://localhost`, com porta opcional: `403 {"error": "forbidden"}`, sem `Access-Control-Allow-Origin`
- Caminho JSON desconhecido: `404 {"error": "not_found"}`

Origem `http://localhost:3000` passa no preflight de `/api/texto` e no envio de `/audio`. `https` e outro host não passam. CORS não autentica.

## Revisão

Não há rota HTTP de correção. Sem autenticação real, o Next.js não edita transcrição.

A correção fica em `transcript_revisions`. O revisor é o ator já vinculado ao paciente, não um `reviewer_user_id` do pedido. A linha em `transcripts` e o áudio permanecem. A rede só recebe o texto automático depois que existe revisão: até lá o contrato interno sai com `text` vazio, `text_source: "none"` e `review_status: "unreviewed"`. Relato escrito sai como `text_source: "written"` e `review_status: "not_required"`.

## Propostas — ainda não implementadas

- Autenticação de verdade antes de qualquer relato real. O token ou a sessão nasce no servidor. O Next.js não escolhe o paciente. `paciente-ficticio` deixa de ser o ator único.
- Autorização por pessoa, consentimento real e transporte HTTPS.
- `OPTIONS` e `Access-Control-Allow-Headers` para o cabeçalho de autenticação, quando ele existir. Hoje só `Content-Type` é anunciado.
- Campo público de falha no histórico, sem caminho interno. Hoje o Next.js só vê `status: "failed"`.
- Paginação. Hoje o teto é 100.
- Origem CORS do Next.js quando sair de localhost. Sem curingas.

Nada disso foi implementado nesta preparação.
