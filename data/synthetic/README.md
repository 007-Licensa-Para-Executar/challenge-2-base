# Casos sintéticos - versão 1

100 relatos inventados em português, com identificadores e textos distintos: 60 em
`dev.jsonl` e 40 em `holdout.jsonl`. Não representam pacientes, prontuários ou coleta humana.
As anotações de referência também foram geradas e **não tiveram revisão independente humana**.

Cada linha contém `id`, `text`, `expected`, `split`, `synthetic`, `annotation_status` e
marcações de cenário. O esquema exato e a integridade são validados pelo runner/testes.

Duas pessoas do grupo devem revisar independentemente as três categorias, resolver
conflitos e versionar as correções antes de interpretar métricas de qualidade. Não alterar
rótulos para fazê-los concordar com um modelo. O holdout não deve orientar ajustes do prompt;
se usado para isso, preparar um novo holdout para avaliação posterior.

Menções históricas, negadas, figuradas ou a terceiros receberam `indeterminado` como
convenção preliminar de contexto insuficiente, não por comprovação de risco. Ausência de
indício não significa pessoa segura. As métricas não validam uso clínico.
