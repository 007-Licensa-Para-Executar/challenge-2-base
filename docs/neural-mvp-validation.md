# Validação técnica do MVP temático — PR #13

Data: 09/11/2026. Este registro descreve um experimento com rótulos sintéticos não revisados. Não representa validação clínica nem desempenho estimado em diários reais.

## Protocolo

- 360 registros sintéticos; nove classes (oito temas e `outros_indeterminado`).
- Separação por famílias de templates e textos idênticos, não por linha aleatória: treino 270, validação 47, teste 43. IDs e grupos disjuntos, todas as classes presentes nos três conjuntos.
- Mesmo split e TF-IDF ajustado somente no treino para PyTorch, NumPy e classe majoritária.
- Seed 42, 40 épocas, batch 32, AdamW/PyTorch lr 0,001, SGD/NumPy lr 0,05, limiar 0,50.
- Checkpoints escolhidos pelo macro-F1 de validação com a mesma política de abstenção da inferência. Empates conservam o primeiro checkpoint. Épocas selecionadas: PyTorch 27; NumPy 1.
- Execução local: macOS arm64, Python 3.12.12; uma thread OpenMP/OpenBLAS. Dependências exatas em `uv.lock`.
- Hash SHA-256 das entradas normalizadas do treinamento: `d41351635298f175bc169af1eccc67dda99d751dda68d8bc46b6caebe993f354`.
- O manifesto gerado inclui IDs, grupos, taxonomia, configurações, commit de base e hashes dos fontes executados. O experimento foi executado antes do commit de integração; os hashes identificam os fontes dessa execução.

Comando de treinamento, válido em Unix e CMD após `uv sync --locked --python 3.12`:

```text
uv run python -m models.train --epochs 40 --batch-size 32 --lr 0.001 --numpy-lr 0.05 --threshold 0.50 --dist-dir dist
```

O ensaio registrado utilizou diretório de saída e SQLite de rastreamento temporários. No Unix, `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` limita as threads; no CMD, use `set "OMP_NUM_THREADS=1"` e `set "OPENBLAS_NUM_THREADS=1"` antes do comando, se desejar a mesma limitação.

## Resultados preliminares no teste

| Método | Accuracy | Macro-F1 | Abstenções | Cobertura determinada |
| --- | ---: | ---: | ---: | ---: |
| PyTorch, política com limiar | 0,0930 | 0,0452 | 23/43 | 46,51% |
| NumPy, política com limiar | 0,0698 | 0,0145 | 43/43 | 0% |
| Classe majoritária | 0,1163 | 0,0231 | Não se aplica | Não se aplica |

Sem aplicar abstenção, o macro-F1 de `argmax` foi 0,1452 no PyTorch e 0,0445 no NumPy. São políticas diferentes; esses números não substituem os resultados da política efetivamente usada no preditor. `outros_indeterminado` também é uma classe do dataset: um acerto nessa classe não demonstra que o sistema detectou corretamente qualquer entrada desconhecida.

A avaliação anterior por linhas não é comparável diretamente ao split por famílias. Variações do mesmo template não constituem exemplos independentes; manter famílias inteiras fora do treino torna o teste mais exigente e revela a limitação de generalização deste experimento.

O NumPy se absteve em todos os exemplos com o checkpoint selecionado. Como o macro-F1 de validação empata em parte do treinamento, a regra pode conservar uma época inicial. Isso está registrado, não foi ocultado por scores de `argmax`. Um eventual desempate por perda deve ser definido antes de um novo experimento, sem escolher a regra pelo teste atual.

Não se conclui que as redes sejam úteis para classificação temática do produto. O experimento verifica o fluxo técnico e evidencia a necessidade de mais diversidade, revisão da qualidade dos rótulos e desenvolvimento controlado usando treino/validação. O conjunto de teste não deve orientar mudanças sucessivas para elevar sua pontuação.

## Artefatos e rastreabilidade

O treinamento produz `comparison_report.json`, `split_manifest.json`, `learning_curves.json`, relatório por classe, matriz de confusão, classes, pesos PyTorch e NumPy e vetorizador. Os artefatos e bancos permanecem locais e ignorados pelo Git; este documento é o resumo editorial versionado do ensaio.

A proporção de caracteres classificados por tema é distinta de um score softmax. O preditor informa denominador e cobertura; sem segmentos analisados, os pesos textuais ficam zerados. Os scores não possuem calibração demonstrada.

## Verificações técnicas

- Suíte completa local: 187 testes aprovados, incluindo apresentação textual da CLI, sem depender de pesos previamente treinados.
- Ruff aprovado; instalação travada com `uv sync --locked` aprovada.
- Smoke do shell e `bem-estar --help` aprovados no macOS.
- Build de sdist e wheel aprovado. Módulos do gerador, treinador e preditor importados fora da árvore fonte usando o wheel e dependências instaladas.
- NumPy possui teste numérico de todos os gradientes. Testes do preditor usam pesos controlados e arquivos temporários, independentes de `dist/` preexistente.
- O status de Ubuntu, macOS e Windows CMD é fornecido pelo CI do commit publicado; testes locais não substituem verificação nessas plataformas.

## Próximos passos

1. Validar a taxonomia e o critério de tema por entrada/sentença com a equipe.
2. Ampliar famílias e estilos, tratar ambiguidades e definir uma referência independente compatível com o esforço disponível.
3. Planejar mudanças de representação, hiperparâmetros, limiar e seleção usando treino/validação; preservar um novo teste final quando o atual já tiver sido utilizado para orientar decisões.
4. Manter a avaliação temática separada dos testes de formato, rastreabilidade e da futura integração com RAG/agentes.
