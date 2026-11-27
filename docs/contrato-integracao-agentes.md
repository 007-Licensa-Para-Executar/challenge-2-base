# Contrato de integração dos agentes

Uma paciente fictícia envia “Hoje cuidei dos meus avós”. A API guarda o original no cofre e devolve a representação tratada. A rede classifica Família e o Agente 1 devolve o subtema “Cuidado com os avós”, com a citação “cuidei dos meus avós”. O orquestrador grava a análise com o ID da entrada, do diário e da representação. A roda mostra a ocorrência em Relacionamentos e Família. Ao perguntar pelo trecho dessa ocorrência, o Agente 2 devolve a mesma citação, os mesmos identificadores e a posição no texto tratado.

## Respostas para a integração

1. **Contrato de entrada.** O adaptador combina `DiaryRecord` protegido com `Agent1Output`. O diário fornece `record_id`, UUID do paciente, `recorded_at`, `treated_text`, `representation_id`, versão do detector e classificação. A análise fornece `entry_id`, `created_at`, rótulo, confiança, subtemas e suas evidências. O envelope `StoredAnalysis` registra o vínculo, a versão e a origem. O armazenamento verifica o conjunto na gravação e na leitura.
2. **Implementação do Agente 2.** O fluxo usa `CopilotService` para perguntas sobre diários e `search_literature` para publicações. Síntese longitudinal completa, rascunho de evolução e briefing metodológico são requisitos de evolução.
3. **Texto e privacidade.** A roda e as contagens usam dados estruturados. Uma pergunta sobre um caso passa pela API de privacidade. O gerador recebe a pergunta tratada e as evidências recuperadas. A ferramenta de literatura recebe a pergunta tratada sem histórico ou contexto dos diários. O original fica no cofre da API de privacidade.
4. **Campos usados.** A roda usa macrotema, subtema e trecho literal. Sentimento, polaridade e indício textual permanecem no artefato. O contrato atual ainda não inclui ABC. A interface agrupa o rótulo da rede em seis macrotemas e preserva sua origem no armazenamento.
5. **Identificadores e datas.** `record_id` é o diário, `representation_id` é a versão tratada e `entry_id` é a execução do Agente 1. A janela usa `recorded_at` em UTC. `created_at` pertence à execução. Reprocessar insere uma revisão e mantém a data do diário.
6. **Ausências e erros.** Uma janela vazia ou busca sem fonte suficiente resulta em `insufficient_evidence`. Um diário tratado sem análise pode sustentar uma busca textual e fica fora dos subtemas. A roda informa a quantidade pendente no campo `pending`. Uma inconsistência validada na leitura interrompe a operação.
7. **Proveniência.** O servidor devolve ID do trecho, do diário, da representação, citação literal e intervalo `[start_char, end_char)` em caracteres Unicode Python. A consulta de subtema também devolve `entry_id`. A validação compara a fatia diretamente com o texto tratado. A literatura devolve trecho, documento, autores, ano e DOI ou URL.
8. **Versões aceitas.** A base integrada aceita `DiaryRecord` protegido `2.0.0`, `StoredAnalysis` `1.0.0` e dados fictícios. Para importar uma fixture legada, use o comando protegido `seed` ou registre os relatos fictícios novamente. O banco legado permanece separado.
9. **Divisão do trabalho.** A #74 cobre contrato, adaptador e persistência do artefato com leitura testável. A #30 cobre a orquestração, ferramentas e consumo por painel e shell.
10. **Testes conjuntos.** O caso de integração verifica a mesma evidência na roda e no chat, Unicode, troca de paciente, representação divergente e revisão sem duplicar o diário. Rodar também os testes do copilot, privacidade, shell e literatura. Na demonstração, trocar de paciente durante uma requisição e conferir que o resultado anterior desaparece.

## Procedimento do Agente 1

O orquestrador trata o texto via HTTP local, classifica com os artefatos sintéticos de `dist/rag-demo`, chama `Agent1Service` e compara cada citação com a representação tratada. Salva a análise por execução e lê a mais recente na roda. Falhas de classificação ou extração deixam o texto tratado disponível. O catálogo de ações do Agente 2 fica no código de `integration_cli.py`. As ferramentas recebem argumentos fixos, usam escopo de paciente e período, e passam pelo armazenamento parametrizado. Solicitações de reprocessamento mostram o ID do diário e aguardam a confirmação na interface.

## Demonstração local

1. Instale Python e Node conforme o README. Na raiz execute `uv sync --locked --extra privacy` e siga o [guia da API local](api-local-pseudonimizacao.md) para instalar o modelo português, iniciar o serviço e executar `register-demo`.
2. Execute `uv run --no-sync python -m app.research_demo train`. Inicie o Ollama na máquina com `qwen3:4b` para extração e síntese e `qwen3:0.6b` para o roteamento. Os comandos explícitos do chat continuam disponíveis com o roteador desligado.
3. Inicialize o corpus de demonstração com `uv run --no-sync python -c 'from agents.copilot.literature import LiteratureStore, load_catalog; print(load_catalog(LiteratureStore("data/privacy/literature.sqlite3")))' `. Esse catálogo tem textos sintéticos identificados. Para usar os artigos aprovados, reconstrua o banco seguindo [as instruções de licença e ingestão](rag-literatura-cientifica.md) e use o destino `data/privacy/literature.sqlite3`.
4. Para voz, instale previamente o modelo Whisper local em `data/models/faster-whisper-base` ou no cache do Faster Whisper. O modo integrado consulta arquivos locais. A gravação passa por um temporário de transcrição descartado ao final.
5. Em `ui/diario_paciente_next`, execute `npm ci` e `DIARY_INTEGRATION_DEMO=1 npm run dev -- --hostname 127.0.0.1`. Use `http://127.0.0.1:3000` e cadastre as contas fictícias `ana@integration.test` e `bruno@integration.test` com senhas locais distintas. A carteira do perfil demo contém exclusivamente essas duas contas.
6. Salve um diário de texto e um de voz. Abra `/psicologa` no mesmo endereço e selecione a pessoa no painel. Abra um subtema e consulte o trecho. No chat, tente `/diarios avós`, `/temas`, `/literatura IA em psicoterapia` ou `/reprocessar ID_DO_DIÁRIO`. Para linguagem natural, escreva a pergunta sem barra. Pelo terminal, `uv run --no-sync bem-estar --privacy` → `/rag` → `chat` abre a mesma base protegida.

O código de busca e as avaliações de literatura vêm da branch do PR #76. O treinamento e o mapeamento da apresentação usam a rede já incorporada à main. A interface integrada é uma demonstração loopback com carteira fixa. Seu teste com dados reais está fora do escopo.

## Verificação desta branch

- O smoke HTTP local passou com Next.js, API de pseudonimização real e dois pacientes sintéticos. Verificou gravação, recuperação do trecho, remoção de um identificador, isolamento entre pacientes e abstenção em literatura.
- A suíte Python local passou com 496 testes e 7 pulados. Também passaram o build Python, o build Next.js e os 5 testes Node. O teste da roda e do chat usa uma extração controlada para verificar identidade, revisão e offsets.
- O endpoint do diário transcreveu uma fala sintética em português com Whisper Tiny. O Qwen3 4B extraiu subtemas, e roda e chat devolveram a mesma citação do áudio e o mesmo ID de análise. O Qwen3 0.6B selecionou a operação de contagem a partir de uma pergunta em português. Uma tentativa anterior de extração atingiu o tempo limite e deixou o diário disponível para busca textual e reprocessamento.
- O treino executado no checkout gerou os artefatos a partir do corpus sintético atual. O macro-F1 de teste com a política de abstenção foi 0,111 em 43 exemplos. A métrica registra a rodada do demonstrador e limita o que podemos inferir sobre a qualidade da rede.
