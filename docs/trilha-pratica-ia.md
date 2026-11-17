# Equipe 007 — Trilha prática de IA

Em seis semanas, você vai construir e interpretar uma rede, ajustar seu treino,
avaliar prompts e comparar estratégias de RAG usando o projeto da equipe.
Reserve três sessões de 60–90 minutos por semana. Use a primeira para estudar
e formular uma hipótese, a segunda para executar e a terceira para interpretar
os erros e explicar a decisão a outra pessoa.

## Prepare o ambiente

Abra o repositório no Codex e siga a [instalação do projeto](../README.md).
Comece com os [dados sintéticos](../data/synthetic/README.md) e o
[guia de rede e RAG](rag-mvp-integrado-rede.md). Separe os experimentos em
branches próprias e guarde pesos, bancos e resultados locais nos diretórios
ignorados pelo Git.

Congele treino, validação e teste antes de comparar configurações. Mantenha
variações da mesma família de relatos no mesmo conjunto e ajuste o vetorizador
apenas com treino. Para prompts e RAG, separe perguntas de desenvolvimento
e teste com referências anotadas. Use o teste reservado após fechar as
configurações. Se ele orientar uma revisão, reserve um novo teste final.

## Como usar os subagentes

Os perfis vivem em `.codex/agents/` e orientam o trabalho no Codex.
Os agentes do aplicativo executam os fluxos de extração e consulta.

| Perfil | Pedido de exemplo | Modelo recomendado |
| --- | --- | --- |
| `mapa_codigo` | “Delegue a `mapa_codigo` o trajeto do texto até a previsão temática. Traga arquivos, funções e um comando inicial.” | GPT-6 Luna / High para mapeamento, se disponível, ou GPT-6.2 Sol / Medium |
| `tutor_ia` | “Delegue a `tutor_ia` uma sessão sobre backpropagation. Peça minha previsão e dê uma pista por vez.” | GPT-6.2 Sol / Medium |
| `avaliador_experimentos` | “Delegue a `avaliador_experimentos` a revisão dos splits e das métricas. Use casos sintéticos e aponte erros que o macro-F1 pode esconder.” | GPT-6.2 Sol / Medium. Use High para investigar vazamento ou resultados contraditórios. |
| `revisor_pr` | “Delegue a `revisor_pr` a revisão deste diff contra a main. Priorize regressões e conclusões além dos resultados.” | GPT-6.2 Sol / High |

Comece com **GPT-6.2 Sol / Medium** como agente principal. Suba para **High**
para cruzar subsistemas ou investigar resultados difíceis. Reserve **GPT-6.2
Astra** para problemas que persistirem e comece pelo esforço sugerido pelo
seletor. Os perfis deixam o modelo em aberto e configuram o esforço de
cada papel. Para usar Luna no mapeamento, peça o modelo e o esforço ao
delegar. Em delegações gerais, comece com as escolhas do agente principal.
Nos experimentos do aplicativo, mantenha o modelo Ollama fixo ao comparar
prompts ou estratégias de recuperação.
[Documentação oficial de subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents) ·
[Seleção de modelos](https://learn.chatgpt.com/docs/model-selection)

Na prática:

1. Escreva sua hipótese e o resultado esperado com ajuda de `tutor_ia`.
2. Delegue em paralelo o mapa do código e o protocolo de avaliação. Delimite
   quais arquivos o avaliador pode editar e peça comandos reproduzíveis.
3. Execute o experimento e anote sua interpretação antes de ler a do avaliador.
   Peça ao tutor um caso que possa refutar sua conclusão.
4. Peça a `revisor_pr` que confira o diff e as evidências. O agente principal
   integra as contribuições. Você aprova a interpretação.

## As seis semanas

### 1. Construir uma rede

- **Estudo:** vetorização de texto, camadas densas, ReLU, logits, softmax,
  entropia cruzada e retropropagação.
- **Prática:** abra a [MLP NumPy](../models/numpy_mlp.py). Faça uma passagem à mão
  com pesos pequenos e confira um gradiente por diferença finita. Execute uma
  rede comparável em PyTorch. Identifique as dimensões, mostre onde entra a
  não linearidade e explique como a perda orienta uma atualização de peso.
- **Entrega:** cálculo comentado e comparação de perda e desempenho com o
  baseline. Discuta o que largura, ativação e regularização mudam.

### 2. Ajustar hiperparâmetros

- **Estudo:** learning rate, batch size, épocas, largura, regularização,
  parada antecipada, busca aleatória e otimização bayesiana.
- **Prática:** consulte `uv run bem-estar-train --help` e passe
  `--data-path data/synthetic/synthetic_diaries.json` explicitamente.
  O comando atual produz métricas de teste. Prepare, num PR de experimentação,
  um modo que exponha somente validação durante a seleção.
- **Entrega:** três ajustes manuais com curvas anotadas. Compare 12 configurações
  aleatórias com 12 bayesianas, usando o mesmo espaço de busca e limite por
  execução. Selecione por macro-F1 de validação, confirme a melhor configuração
  de cada método com três seeds e compare ganho, variabilidade e tempo.
  [Otimização bayesiana](https://arxiv.org/abs/1206.2944)

### 3. Interpretar a rede

- **Estudo:** matriz de confusão, métricas por classe, abstenção, calibração e
  atribuição.
- **Prática:** inspecione 12 relatos sintéticos distribuídos entre acertos,
  erros e abstenções. Faça pares em que apenas o tema muda. Aplique Integrated
  Gradients à entrada numérica da rede com uma referência declarada. Para
  levantar hipóteses sobre palavras, remova termos do texto e refaça a
  vetorização. Atribuições às dimensões do embedding e efeitos da remoção de
  palavras respondem a perguntas diferentes.
- **Entrega:** descreva um erro com scores, evidências e limitações. Explique
  o mesmo erro para uma pessoa que não conhece a arquitetura.
  [Integrated Gradients](https://arxiv.org/abs/1703.01365)

### 4. Projetar e testar prompts

- **Estudo:** instruções de sistema, exemplos few-shot, esquemas de saída,
  abstenção e testes de regressão.
- **Prática:** compare três prompts do copiloto com o mesmo Qwen, esquema,
  parâmetros e trechos recuperados. Use instrução direta, exemplos de resposta
  e exemplos que também mostrem quando a evidência é insuficiente. Inclua
  entradas ambíguas e instruções embutidas em relatos fictícios.
- **Entrega:** compare JSON válido, afirmações sustentadas pela fonte,
  abstenção, latência e tokens quando disponíveis. Confira o suporte das
  afirmações por amostragem: um identificador de fonte válido também pode
  apontar para um trecho que não sustenta a resposta.

### 5. Construir e avaliar RAG

- **Estudo:** divisão em trechos, embeddings, busca lexical, busca vetorial,
  ranking, filtros e citações.
- **Prática:** reproduza o baseline com
  `uv run bem-estar-rag-evaluate --backend bm25 --split dev`.
  Use o [guia do RAG](rag-mvp-integrado-rede.md) para preparar o E5 local.
  Investigue primeiro o tamanho do trecho, depois o número de retornos.
  Acrescente MRR no PR de experimentação, caso ainda não esteja disponível.
- **Entrega:** meça Recall@k, MRR e abstenção nas negativas com perguntas
  anotadas. Em uma tabela separada, julgue se a resposta gerada é sustentada
  pelas fontes. Registre falsos positivos de recuperação, inclusive nos casos
  em que o gerador se abstém corretamente.
  [Trabalho original sobre RAG](https://arxiv.org/abs/2005.11401)

### 6. Otimizar e defender

- **Estudo:** busca híbrida, fusão por posição, re-ranking, custo de indexação
  e orçamento de contexto.
- **Prática:** compare BM25, E5 e fusão híbrida. Para isolar o efeito do
  re-ranking, mantenha o mesmo conjunto de candidatos. Amplie o corpus
  sintético, reporte seu tamanho e meça latência p50/p95 e custo de indexação
  na mesma máquina. Mantenha o gerador e o orçamento de contexto fixos.
- **Entrega:** compare qualidade, abstenção e custo. Demonstre uma resposta com
  fonte, uma abstenção correta e um erro observado. Justifique a estratégia
  escolhida. A experiência com um problema real de grande volume, prevista
  no formulário, exige prática adicional além deste benchmark sintético.

## Ficha de cada experimento

- Hipótese e resultado esperado.
- Commit, versão dos dados, split, seed, configuração e comando.
- Baseline, métricas, tamanho da amostra e custo observado.
- Um erro inspecionado, interpretação, decisão e próximo passo.

Você consegue defender o nível que marcou no formulário quando reproduz o
resultado, justifica suas escolhas e explica o que faria se o próximo teste
contradissesse a conclusão.
