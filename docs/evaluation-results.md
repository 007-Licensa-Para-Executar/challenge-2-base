# Estado da avaliação real - 26/10/2026

## Verificações concluídas

- Python 3.12 e dependências fixadas por uv.lock.
- 78 testes automatizados passaram, sem chamadas a modelos reais.
- Ruff check e format check aprovados.
- Wheel construído e instalado em ambiente isolado; os 100 casos são carregados fora do checkout.
- Pacote fonte inspecionado para excluir runtime, credenciais e bancos locais.
- Integração real com Ollama: modelo inexistente retornou erro sanitizado, sem extração, e o
  estado de erro foi persistido no SQLite. Isso testa falha operacional, não classificação.

## Ambiente preparado

- Apple M1, 8 GB RAM, macOS 14.4.1.
- Ollama v0.40.11, pacote Darwin oficial verificado por SHA-256.
- Servidor somente em loopback, OLLAMA_NO_CLOUD=1, um modelo e uma requisição por vez.
- Contexto de 2.048 tokens, temperatura 0, saída limitada a 160 tokens.
- Qwen3 4B Q4_K_M e Gemma 3 4B Q4_K_M como candidatos, sem vencedor declarado.

## Medição semântica

**Ainda não concluída.** Os downloads dos modelos estão em andamento e foram observados
como lentos nesta execução. Ainda não há accuracy, F1, estabilidade, latência de inferência
ou memória de modelo medidas que possam fundamentar uma escolha. Não confundir testes com
SDKs simulados, tempo de download ou erro de modelo ausente com avaliação de qualidade.

Uma execução local em segundo plano foi iniciada para aguardar os dois downloads e rodar
três repetições de desenvolvimento e holdout, sequencialmente. O estado está em
`results/benchmark-state.json`; tentativas em `results/dev.jsonl` e `results/holdout.jsonl`,
e resumos em `results/dev.json` e `results/holdout.json`. O processo depende de o servidor
Ollama e o processo local permanecerem ativos; não é uma automação agendada nem uma promessa
de conclusão após reiniciar o computador. O aguardo dos downloads tem limite de duas horas.

O runner preserva tentativas incrementais e permite retomar com `--resume`.
Os comandos completos e a interpretação das métricas estão em [evaluation-method.md](evaluation-method.md).
Relatórios locais ficam em results/ e não são commitados automaticamente.

Todas as anotações de referência dos 100 exemplos ainda precisam da revisão independente
de duas pessoas do grupo. Mesmo depois do benchmark, os resultados serão preliminares e
não validarão uso clínico, triagem de crises ou atendimento a pacientes.
