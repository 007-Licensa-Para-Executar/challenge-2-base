# Diário Emocional Inteligênte

**Equipe 007 - Licensa para Executar | Versão 2.1 | 19/11/2026**

Especificação de requisitos e arquitetura do produto, alinhada à versão 2.1 consolidada e ao documento de insights clínicos e arquitetura de agentes.

- [Projeto LaTeX](main.tex): documento principal compilável com pdfLaTeX.
- [PDF de leitura](relatorio.pdf): versão 2.1 compilada diretamente da fonte Markdown.
- [Fonte editorial](relatorio.md): texto completo para revisão.
- [Decisões e validações pendentes](perguntas-equipe.md): escolhas consolidadas e itens técnicos ainda por validar.

## Como revisar

As validações ainda abertas aparecem **em vermelho e entre colchetes no LaTeX e no PDF**. No Markdown, conservam os colchetes. O documento não declara funcionalidades implementadas nem resultados de avaliações ainda não realizadas.

As definições consolidadas incluem público jovem-adulto, seis macrotemas, dois agentes locais e três camadas documentais. As validações pendentes concentram-se em dados e licenças, versões de modelos, metas de avaliação, controles operacionais e preparação para uso com dados reais.

O relatório cobre visão, atores, jornadas, requisitos, camadas de acesso, pseudonimização, agentes, rede neural, RAG, acompanhamento longitudinal, avaliação e MLOps. A versão foi consolidada em **19/11/2026** e distingue requisitos de implementação comprovada.

## Edição e geração

Edite `relatorio.md`. Para regenerar `main.tex` e `perguntas-equipe.md`, execute dentro desta pasta:

```text
python gerar_relatorio.py
```

No macOS/Linux, use `python3` se necessário. O script usa somente a biblioteca padrão nessa operação e resolve arquivos em relação ao próprio diretório. Para gerar também o PDF de leitura:

```text
uv run --no-project --with reportlab python gerar_relatorio.py --pdf
```

O comando com `--pdf` pode baixar ReportLab na primeira execução e não altera dependências do aplicativo. O PDF é gerado diretamente do Markdown; o PDF do compilador LaTeX possui tipografia e paginação próprias. O gerador aplica vermelho aos trechos entre colchetes e usa metadados determinísticos no PDF de leitura.

## LaTeX e Overleaf

Abra esta pasta no editor LaTeX do Codex. No Overleaf, envie `main.tex`, selecione-o como documento principal e use pdfLaTeX. As referências estão incorporadas; não há bibliografia externa nem dependência de shell escape. A importação no serviço Overleaf deve ser conferida quando utilizada.

Preserve a grafia institucional e o nome do produto como especificados. Não edite `main.tex` isoladamente, pois será substituído na regeneração. Após mudanças de conteúdo, confira compilação, trechos vermelhos, tabelas e paginação.

O `.gitignore` deste diretório exclui intermediários LaTeX e caches. O PDF final é um artefato documental intencional. Dados de pacientes, áudios, fotos, bancos, pesos e resultados de experimentos não pertencem a esta pasta.
