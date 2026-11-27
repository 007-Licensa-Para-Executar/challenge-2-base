"""Gerar fontes Overleaf e, opcionalmente, PDF de leitura a partir do Markdown.

Ferramenta documental independente do aplicativo. Sem rede ou leitura de .env.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TITLE = "Diário Emocional Inteligênte"
SUBTITLE = "Especificação de requisitos, conformidade ético-legal e arquitetura de referência"
VERSION = "Equipe 007 - Licensa para Executar | Versão 2.1 | 19/11/2026"
PENDING = r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]"


def blocks(text: str):
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            yield "table", rows
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            yield f"h{level}", line[level:].strip()
            i += 1
            continue
        if line.startswith("- ") or re.match(r"\d+\. ", line):
            yield "bullet", line
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "- ")):
            paragraph.append(lines[i].strip())
            i += 1
        yield "p", " ".join(paragraph)


def escape_tex(text: str) -> str:
    chars = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(chars.get(c, c) for c in text)


def tex_inline(text: str) -> str:
    out = []
    for part in re.split(r"(https?://\S+|\*\*.*?\*\*|" + PENDING + r")", text):
        if part.startswith("http"):
            out.append(r"\url{" + part + "}")
        elif part.startswith("**") and part.endswith("**"):
            out.append(r"\textbf{" + tex_inline(part[2:-2]) + "}")
        elif part.startswith("[") and part.endswith("]"):
            out.append(r"\pendencia{" + escape_tex(part[1:-1]) + "}")
        else:
            out.append(escape_tex(part))
    return "".join(out)


def make_tex(content) -> str:
    output = [
        r"""% Gerado de relatorio.md por gerar_relatorio.py; não editar este arquivo isoladamente.
\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[brazil]{babel}
\usepackage{lmodern}
\usepackage[margin=23mm]{geometry}
\usepackage{microtype}
\usepackage[table]{xcolor}
\usepackage{longtable,array,booktabs}
\usepackage{xurl}
\usepackage[colorlinks=true,linkcolor=blue!45!black,urlcolor=blue!45!black]{hyperref}
\definecolor{pendente}{HTML}{B42318}
\newcommand{\pendencia}[1]{\textcolor{pendente}{[#1]}}
\hypersetup{pdftitle={Diário Emocional Inteligênte},pdfauthor={Equipe 007 - Licensa para Executar}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\setlength{\emergencystretch}{3em}
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.18}
\begin{document}
\begin{titlepage}
\vspace*{25mm}
{\large EQUIPE 007\par}
{\large Licensa para Executar\par}
\vspace{12mm}
{\Huge\bfseries Diário Emocional Inteligênte\par}
\vspace{6mm}
{\LARGE Especificação de requisitos, conformidade ético-legal e arquitetura de referência\par}
\vspace{14mm}
{\large Versão 2.1 / 19 de novembro de 2026\par}
\vspace{8mm}
Dois agentes locais sob supervisão da psicóloga.\par
Agente 1: Extrator. Agente 2: Analista Longitudinal e Copiloto RAG.\par
\vfill
Autoria institucional: Equipe 007 - Licensa para Executar.\par
Challenge 2 - Bem-estar.\par
\pendencia{Validações técnicas abertas aparecem em vermelho e entre colchetes.}\par
Especificação do produto pretendido; não representa declaração de implementação.\par
\end{titlepage}
\tableofcontents
\newpage
"""
    ]
    for kind, value in content:
        if kind == "h1":
            continue
        if kind in ("h2", "h3"):
            title = re.sub(r"^\d+(?:\.\d+)*\.\s*", "", value)
            cmd = "section" if kind == "h2" else "subsection"
            output.append("\\" + cmd + "{" + tex_inline(title) + "}\n")
        elif kind == "table":
            n = len(value[0])
            widths = [0.23, 0.36, 0.41] if n == 3 else [1 / n] * n
            columns = "".join(
                r">{\raggedright\arraybackslash}p{\dimexpr"
                + str(w)
                + r"\linewidth-2\tabcolsep\relax}"
                for w in widths
            )
            output.append(r"\begingroup\small" + "\n" + r"\begin{longtable}{" + columns + "}\n")
            header = " & ".join(r"\textbf{" + tex_inline(c) + "}" for c in value[0])
            output.append(r"\toprule" + "\n" + header + r" \\ \midrule\endfirsthead" + "\n")
            output.append(r"\toprule" + "\n" + header + r" \\ \midrule\endhead" + "\n")
            output.append(r"\bottomrule\endfoot" + "\n")
            for row in value[1:]:
                if len(row) != n:
                    raise ValueError("Tabela com quantidade inconsistente de colunas")
                output.append(" & ".join(tex_inline(c) for c in row) + r" \\[3pt]" + "\n")
            output.append("\\end{longtable}\n\\endgroup\n")
        elif kind == "bullet":
            output.append(r"\hangindent=1em " + tex_inline(value) + "\n\n")
        else:
            output.append(tex_inline(value) + "\n\n")
    output.append("\\end{document}\n")
    return "".join(output)


def pdf_inline(text: str) -> str:
    # XML escaping before applying the very small supported Markdown vocabulary.
    formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(text))
    return re.sub(PENDING, lambda m: '<font color="#B42318">' + m[0] + "</font>", formatted)


def make_pdf(content) -> None:
    # ReportLab ships the Vera family, avoiding system-specific font locations.
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        CondPageBreak,
        LongTable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        TableStyle,
    )

    fonts = Path(reportlab.__file__).parent / "fonts"
    pdfmetrics.registerFont(TTFont("Vera", str(fonts / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Bold", str(fonts / "VeraBd.ttf")))
    pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="Vera-Bold")
    body = ParagraphStyle(
        "BodyLocal",
        fontName="Vera",
        fontSize=9.4,
        leading=14,
        spaceAfter=7,
        allowOrphans=0,
        allowWidows=0,
    )
    small = ParagraphStyle("CellLocal", parent=body, fontSize=8.1, leading=11.6, spaceAfter=0)
    h1 = ParagraphStyle(
        "H1Local",
        parent=body,
        fontName="Vera-Bold",
        fontSize=15,
        leading=19,
        spaceBefore=16,
        spaceAfter=9,
        keepWithNext=False,
    )
    h2 = ParagraphStyle(
        "H2Local", parent=h1, fontSize=11, leading=15, spaceBefore=10, keepWithNext=True
    )
    label = ParagraphStyle("LabelLocal", parent=body, textColor=colors.HexColor("#236475"))
    title = ParagraphStyle(
        "TitleLocal",
        parent=body,
        fontName="Vera-Bold",
        fontSize=29,
        leading=35,
        spaceAfter=14,
        alignment=TA_LEFT,
    )
    subtitle = ParagraphStyle("SubtitleLocal", parent=body, fontSize=18, leading=25)
    story = [
        Spacer(1, 24 * mm),
        Paragraph("EQUIPE 007 / LICENSA PARA EXECUTAR", label),
        Spacer(1, 12 * mm),
        Paragraph(TITLE, title),
        Paragraph(SUBTITLE, subtitle),
        Spacer(1, 12 * mm),
        Paragraph(pdf_inline(VERSION), body),
        Paragraph("Dois agentes locais sob supervisão da psicóloga.", body),
        Paragraph("Agente 1: Extrator. Agente 2: Analista Longitudinal e Copiloto RAG.", body),
        Spacer(1, 30 * mm),
        Paragraph("Autoria institucional: Equipe 007 - Licensa para Executar.", body),
        Paragraph("Challenge 2 - Bem-estar.", body),
        Paragraph(
            pdf_inline("[Validações técnicas abertas aparecem em vermelho e entre colchetes.]"),
            body,
        ),
        Paragraph(
            "Especificação do produto pretendido; não representa declaração de implementação.", body
        ),
        PageBreak(),
    ]
    # Compact, visible navigation; numbered headings match the Markdown.
    story.append(Paragraph("Roteiro de leitura", h1))
    for kind, value in content:
        if kind == "h2":
            story.append(Paragraph(pdf_inline(value), body))
    story.append(PageBreak())
    width = 164 * mm
    for kind, value in content:
        if kind == "h1":
            continue
        if kind == "h2":
            story.append(CondPageBreak(100))
            story.append(Paragraph(pdf_inline(value), h1))
        elif kind == "h3":
            story.append(Paragraph(pdf_inline(value), h2))
        elif kind == "table":
            n = len(value[0])
            weights = [0.23, 0.36, 0.41] if n == 3 else [1 / n] * n
            rows = [[Paragraph(pdf_inline(c), small) for c in row] for row in value]
            table = LongTable(
                rows, colWidths=[width * w for w in weights], repeatRows=1, hAlign="LEFT"
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f0f2")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#236475")),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#d9e0e3")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.extend([table, Spacer(1, 6)])
        else:
            story.append(Paragraph(pdf_inline(value), body))

    def footer(canvas, doc):
        if doc.page > 1:
            canvas.setFont("Vera", 7.5)
            canvas.setFillColor(colors.HexColor("#526471"))
            canvas.drawString(23 * mm, 13 * mm, "Equipe 007 | Requisitos | v2.1 | 19/11/2026")
            canvas.drawRightString(187 * mm, 13 * mm, str(doc.page))

    doc = SimpleDocTemplate(
        str(ROOT / "relatorio.pdf"),
        pagesize=(210 * mm, 297 * mm),
        leftMargin=23 * mm,
        rightMargin=23 * mm,
        topMargin=21 * mm,
        bottomMargin=23 * mm,
        title=TITLE + " - " + SUBTITLE,
        author="Equipe 007 - Licensa para Executar",
    )
    from reportlab.pdfgen.canvas import Canvas

    def deterministic_canvas(*args, **kwargs):
        kwargs["invariant"] = 1
        return Canvas(*args, **kwargs)

    doc.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=deterministic_canvas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", action="store_true", help="Gerar também PDF com ReportLab")
    args = parser.parse_args()
    markdown = (ROOT / "relatorio.md").read_text(encoding="utf-8")
    content = list(blocks(markdown))
    (ROOT / "main.tex").write_text(make_tex(content), encoding="utf-8")
    questions = markdown.split("## 20. Decisões consolidadas e validações pendentes\n", 1)[1]
    questions = questions.split("## 21.", 1)[0]
    (ROOT / "perguntas-equipe.md").write_text(
        "# Decisões consolidadas e validações pendentes - Equipe 007\n\n"
        "Diário Emocional Inteligênte | 19/11/2026 | Versão 2.1\n\n"
        "No PDF e no LaTeX, os itens entre colchetes aparecem em vermelho.\n\n" + questions,
        encoding="utf-8",
    )
    if args.pdf:
        make_pdf(content)


if __name__ == "__main__":
    main()
