# Corpus sintético de demonstração de recuperação

Todos os textos, pessoas, datas e acontecimentos são fictícios. `diaries.jsonl` contém 20 registros validados pelo contrato `DiaryRecord`, dez por pessoa, incluindo datas antigas para testar janelas temporais. Classificação inicial: `not_requested`; a ingestão pode acrescentar resultados reais da rede sem alterar o texto.

`questions.jsonl` contém 12 perguntas, separadas em seis de desenvolvimento e seis de teste. Cada pergunta identifica pessoa, período, registros relevantes esperados ou ausência de resposta. O benchmark mede recuperação por IDs de registro, não eficácia clínica ou fidelidade de uma resposta gerada.

O conjunto é pequeno, elaborado para demonstração e testes de contexto. Não é uma avaliação independente validada por especialistas. Não ajustar parâmetros continuamente às perguntas de teste; mudar a preparação exige documentar a nova versão e reservar outro teste quando necessário.

A busca lexical tem uma limitação intencionalmente visível: a pergunta sobre senha de cartão bancário pode recuperar um relato sobre cartão-postal. Compartilhar uma palavra não demonstra que a fonte responde à pergunta. O relatório conserva esse falso positivo, e a demonstração deve explicá-lo.

O backend E5 usa somente um modelo disponível em diretório local explicitamente indicado. Ele não baixa modelos, não troca para serviços externos e não garante maior qualidade. O limiar padrão é uma configuração inicial, não uma confiança calibrada. Comparações reais devem registrar modelo, revisão, chunking, limiar, corpus, perguntas e execução.
