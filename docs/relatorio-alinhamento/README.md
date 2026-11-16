# Diário Emocional Inteligênte

**Equipe 007 - Licensa para Executar | Versão 1.0 | 06/11/2026**

Especificação autônoma de requisitos e arquitetura do produto, com autoria institucional da Equipe 007. O assistente usa o placeholder **[AGENT-NAME]** até a escolha do nome definitivo.

- [Projeto LaTeX](main.tex): documento principal compilável com pdfLaTeX.
- [PDF de leitura](relatorio.pdf): conteúdo equivalente, com paginação independente.
- [Fonte editorial](relatorio.md): texto completo para revisão.
- [Perguntas para a equipe](perguntas-equipe.md): 24 decisões agrupadas por dependência.

## Como revisar

As lacunas e decisões abertas aparecem **em vermelho e entre colchetes no LaTeX e no PDF**. No Markdown, conservam os colchetes. O documento não declara funcionalidades implementadas nem resultados de avaliações ainda não realizadas.

Comece pelas decisões sobre taxonomia, quantidade de temas, dados, referências, construção da rede, corpus RAG e avaliação. Para cada resposta, registre escolha, justificativa, responsável, data e requisitos afetados. Nome, público, interface, autonomia e operação têm perguntas específicas. Requisitos e critérios de aceite têm identificadores próprios para permitir rastreabilidade.

O relatório cobre visão, atores, jornadas, funções, regras, arquitetura, ferramentas, projetos locais, dados, rede neural, RAG, subtemas, visualizações, avaliação, MLOps e requisitos acadêmicos. A pesquisa bibliográfica tem corte em **06/11/2026**, inclui fontes primárias do MIT e distingue evidência científica de orientação de engenharia de fornecedores.

## Edição e geração

Edite `relatorio.md`. Para regenerar `main.tex` e `perguntas-equipe.md`, execute dentro desta pasta:

```text
python gerar_relatorio.py
```

No macOS/Linux, use `python3` se necessário. O script usa somente a biblioteca padrão nessa operação e resolve arquivos em relação ao próprio diretório. Para gerar também o PDF de leitura:

```text
uv run --no-project --with reportlab python gerar_relatorio.py --pdf
```

O comando com `--pdf` pode baixar ReportLab na primeira execução e não altera dependências do aplicativo. O PDF é gerado diretamente do Markdown; o PDF do compilador LaTeX possui tipografia e paginação próprias. O gerador aplica vermelho aos trechos entre colchetes, inclusive ao placeholder do nome, e usa metadados determinísticos no PDF de leitura.

## LaTeX e Overleaf

Abra esta pasta no editor LaTeX do Codex. No Overleaf, envie `main.tex`, selecione-o como documento principal e use pdfLaTeX. As referências estão incorporadas; não há bibliografia externa nem dependência de shell escape. A importação no serviço Overleaf deve ser conferida quando utilizada.

Preserve a grafia institucional e o nome do produto como especificados. Não edite `main.tex` isoladamente, pois será substituído na regeneração. Após mudanças de conteúdo, confira compilação, trechos vermelhos, tabelas e paginação.

O `.gitignore` deste diretório exclui intermediários LaTeX e caches. O PDF final é um artefato documental intencional. Dados de pacientes, áudios, fotos, bancos, pesos e resultados de experimentos não pertencem a esta pasta.
