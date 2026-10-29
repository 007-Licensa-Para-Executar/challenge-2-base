# Avaliação preliminar do extrator

O conjunto contém 100 relatos inteiramente sintéticos em português: 60 de desenvolvimento e
40 reservados (holdout). Os identificadores e textos não se repetem entre splits. Cada exemplo
possui uma referência de tema, sentimento e sinal textual, além de marcações de cenário.
Os 100 exemplos são distintos, mas ainda têm **anotações geradas, não revisadas**. Duas pessoas
do grupo devem revisá-las independentemente e resolver divergências antes de interpretar os
números como evidência de qualidade. Não há validação clínica.

Cenários incluem linguagem direta, relatos mistos, entradas curtas, negação, histórico,
terceiros, figuras de linguagem, instruções maliciosas e referência explícita a dano. Menções
históricas ou de terceiros recebem inicialmente `indeterminado`, sem afirmar risco atual.
Essas escolhas são referências preliminares, não fatos clínicos. O holdout deve permanecer
fora do ajuste de prompts; consultas repetidas para ajustar o sistema exigem um novo holdout.

## Execução reproduzível

Com o ambiente instalado e Ollama local em execução, baixar `qwen3:4b` e `gemma3:4b`.
Primeiro executar um smoke, que valida integração e não mede qualidade:

```sh
bem-estar-evaluate --models qwen3:4b gemma3:4b --split dev --limit 1 --repetitions 1 --output results/smoke.json
```

Depois, executar sequencialmente na mesma máquina, com os mesmos parâmetros e poucos programas
abertos. O runner usa um modelo por vez e pede seu descarregamento antes do próximo:

```sh
bem-estar-evaluate --models qwen3:4b gemma3:4b --split dev --repetitions 3 --output results/dev.json
bem-estar-evaluate --models qwen3:4b gemma3:4b --split holdout --repetitions 3 --output results/holdout.json
```

O JSONL adjacente contém um manifesto seguido de resultados incrementais por tentativa;
`--runs-file` permite escolher seu caminho. Cada linha é gravada imediatamente, sem incluir o
texto do caso. São registrados identificadores, referências, previsões, erros sanitizados,
versões, digest de modelo, latência e alocação de memória disponível. Não há gravação no SQLite
nessa avaliação. Três falhas consecutivas interrompem a avaliação para evitar uma longa fila
de timeouts. Corrigir o serviço e repetir o comando com `--resume` retoma as tentativas ainda
não registradas; erros já registrados continuam contando como erros. Para repetir erros,
execute uma avaliação nova com outro arquivo, sem editar o benchmark anterior.

O resume rejeita configuração, conjunto ou digest de modelo diferentes. A saída existente
nunca é sobrescrita sem `--resume`. Os artefatos são locais e ignorados pelo Git. `complete`
indica se todas as tentativas planejadas foram registradas; isso não significa sucesso delas.

## Métricas e interpretação

- Sucessos/erros, taxa de extração válida e recusas detectadas. Uma extração com formato válido
  ainda pode estar semanticamente errada.
- Accuracy e macro-F1 separados para tema, sentimento e sinal. O macro-F1 considera a união de
  classes esperadas e previstas observadas, listada no relatório. Erros contam no denominador
  da accuracy e como falsos negativos da classe esperada; não são descartados para elevar notas.
- Matriz de confusão por campo, incluindo a coluna `__error__`. Para o sinal `presente`, falsos
  negativos incluem falhas operacionais, enquanto falsos positivos são previsões `presente`
  cuja referência é outra. Não são medidas de detecção de risco clínico.
- Quantidade de previsões indeterminadas e cobertura de classificações determinadas em relação
  a todas as tentativas. Indeterminação é uma saída permitida, não um erro operacional.
- Estabilidade: fração dos casos com pelo menos três execuções em que todas as previsões são
  válidas e idênticas. Constância não comprova correção.
- Latência mediana e p95 por tentativa, incluindo tentativas com erro. Inclui o tempo medido
  pelo extrator; o primeiro carregamento pode afetar resultados.
- Memória: maior `size_vram` reportado pelo serviço Ollama em `/api/ps` logo após cada tentativa.
  É uma medida de alocação, não RSS, pico de RAM, pressão de memória ou consumo total do Mac.
  Em memória unificada do M1, não interpretá-la como uso de uma GPU separada. Indisponível
  aparece como `null`; o RSS do processo Python não substitui o consumo do modelo.

O bloco `validation` compara o sentimento do LLM com o léxico heurístico do VADER em português.
Esses scores e flags não são referências anotadas e não entram nas métricas de accuracy ou
macro-F1 acima. Avaliar a qualidade dessa camada exige referências revisadas independentemente;
uma divergência não identifica qual dos dois métodos está correto.

Essa é uma **validação híbrida (LLM + PLN determinístico)**, não *LLM-as-a-Judge*: o Qwen
produz a extração e o VADER calcula uma segunda polaridade por léxico e regras. Não há uma
segunda inferência de linguagem nem tokens adicionais para um modelo juiz. O cálculo do VADER
roda em paralelo à chamada do Ollama, em uma thread de CPU, então parte do seu tempo pode ficar
sobreposta à inferência; o custo não é zero e o ganho de latência depende da execução.

A motivação é obter uma comparação barata e reproduzível, com um mecanismo diferente do LLM,
para facilitar a inspeção de desacordos. Essa diferença de abordagem não torna os métodos
estatisticamente independentes nem transforma o léxico em fonte de verdade. Os dois podem
errar, e concordância não comprova correção. A discrepância mede somente desacordo de polaridade
geral; não detecta toda alucinação, não valida os demais campos e não é um sinal clínico. Ela
não deve ser usada para corrigir automaticamente a extração ou orientar cuidado.

Compare primeiro os três campos e a taxa de erros. Em qualidade equivalente, compare latência
na mesma máquina e memória reportada, deixando explícito o limite da medição. Um smoke com
um caso não escolhe modelo. Se a máquina não completar o benchmark, preserve os resultados
parciais e registre a limitação, sem declarar vencedor nem recorrer a serviço remoto.
