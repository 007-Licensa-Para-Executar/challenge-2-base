# Papéis dos agentes e decisão de implementação

## Problema e limite

A hipótese do grupo é organizar relatos voluntários entre sessões, identificando temas para
posterior interpretação humana. A finalidade é informacional: não se produzirá diagnóstico,
classificação clínica, recomendação terapêutica ou previsão de crise.

| Papel arquitetural | Entrada e saída | Lugar no projeto |
| --- | --- | --- |
| Extração/classificação | Relato → metadados de categorias definidas | Único componente implementado nesta entrega |
| Roteamento | Resultado validado + regras → próximo passo permitido | Decisões explícitas no código; não é avaliação clínica |
| Conversação | Contexto permitido → resposta reflexiva | Futuro, ainda não implementado |
| Sumarização | Registros por período → síntese com proveniência | Futuro, depende de autorização e revisão humana |

Esses nomes descrevem responsabilidades, não uma taxonomia universal de agentes. Um workflow
fixo com uma chamada ao modelo pode ser descrito mais precisamente como extrator do que como
agente autônomo. SDK/framework ou arquivos separados não comprovam colaboração multiagente.
A demonstração futura deverá mostrar troca de informações e integração real entre pelo menos
dois componentes, com o enquadramento acadêmico confirmado com a orientação.

## Por que uma implementação pequena

Uma chamada de classificação, validação de esquema, persistência e CLI não precisa de um
framework de equipes autônomas. Usamos SDK oficial Ollama e Pydantic, com SQLite stdlib. Isso
facilita inspecionar o que foi enviado ao modelo, testar falhas e medir o comportamento. Não
é treinamento de modelo do zero: reutilizamos modelos abertos e bibliotecas existentes.

PydanticAI seria uma evolução possível para agentes tipados; LangGraph, para fluxos com
estados e transições mais complexos. Nenhum deles é necessário para o primeiro extrator.
Não há evidência de que adicionar agentes por si só melhore precisão ou segurança.

## Validação híbrida não é LLM-as-a-Judge

O extrator combina uma interpretação do Qwen com uma comparação determinística de polaridade
usando o algoritmo de pontuação do VADER e um léxico heurístico em português. Isso é uma
**validação híbrida (LLM + PLN tradicional)**, não *LLM-as-a-Judge*: não há um segundo modelo
de linguagem avaliando a saída do primeiro. O VADER não gera uma explicação nem julga a
resposta inteira; calcula apenas uma polaridade geral a partir das palavras e regras cobertas
pelo léxico.

Essa escolha evita uma segunda inferência no Ollama e não consome tokens de outro modelo juiz.
No runtime, o cálculo VADER ocorre em uma thread de CPU enquanto a requisição ao Qwen está em
andamento. Assim, parte do trabalho pode se sobrepor à inferência, mas ainda há custo de CPU e
criação/coordenação da thread; a execução não é literalmente gratuita e seu impacto de latência
depende do relato e do ambiente.

A comparação tem modos de falha diferentes dos do LLM e é reproduzível, o que a torna útil para
expor alguns desacordos e organizar dados para auditoria. Isso não significa independência
estatística, superioridade ou correção: o léxico é pequeno, ambos os métodos podem errar e a
concordância não comprova que a classificação está certa. A métrica compara somente polaridade
geral com uma âncora grosseira do sentimento do LLM; não detecta toda alucinação, não avalia
tema ou indício textual e não deve corrigir a saída automaticamente. Seus limites e a forma de
avaliá-la estão em [evaluation-method.md](evaluation-method.md).

O repositório Health Journal pode ser estudado como referência, mas não será usado como base:
sua finalidade inclui acompanhamento de sintomas/recomendações e um produto mais amplo que o
nosso escopo. Copiar uma aplicação inteira exigiria revisar licença, dependências, tratamento
de dados e pressupostos de uso. A pesquisa bibliográfica não equivale a auditoria desse código.

## Jev-like e saídas estruturadas

Jev é um produto da TypeSafe que recebe estado e perguntas tipadas (Choice, Score, Noul) para
decisões consumidas pelo programa. Nossa inspiração é separar interpretação textual de lógica
operacional; não usamos a API Jev, seus pesos ou suas probabilidades. Não chamamos um valor
autodeclarado pelo LLM de probabilidade calibrada.

Ollama recebe um JSON Schema derivado de Pydantic; a resposta é validada novamente no cliente.
As categorias são estáveis para permitir avaliação. Nenhuma dessas etapas garante veracidade
ou ausência de viés. `indeterminado` é uma saída válida; falha operacional é outra coisa.

## Referências técnicas primárias

- TypeSafe, Jev: https://docs.typesafe.ai/introduction
- Ollama, Structured Outputs: https://docs.ollama.com/capabilities/structured-outputs
- Pydantic, validação: https://docs.pydantic.dev/latest/concepts/models/
- PydanticAI: https://ai.pydantic.dev/
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- Health Journal (referência exploratória): https://github.com/BirgerMoell/health-journal

As duas resources acadêmicas e seus limites estão em [references.md](references.md).
