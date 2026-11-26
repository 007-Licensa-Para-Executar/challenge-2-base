"""Audita PDFs colocados em staging. Não baixa arquivos e não abre SQLite.

Coloque cada artigo como PT-001.pdf … PT-004.pdf nesta pasta e execute:

    PYTHONPATH=. .venv/bin/python knowledge_base/literature/staging/audit.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from agents.copilot.literature import read_document

STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[2]
ARTICLES = (
    {
        "document_id": "PT-001",
        "title": "Psicoterapia e inteligência artificial: limites tecnológicos na promoção da saúde",
        "doi": "10.1590/1983-803420253958PT",
    },
    {
        "document_id": "PT-002",
        "title": "Inteligência Artificial Generativa e seu Impacto na Formação e no Exercício Profissional da Psicologia",
        "doi": "10.1590/1982-3703003298224",
    },
    {
        "document_id": "PT-003",
        "title": "Assistentes Virtuais Inteligentes e saúde mental: debates regulatórios no Brasil",
        "doi": "10.29397/reciis.v18i3.4310",
    },
    {
        "document_id": "PT-004",
        "title": "Desenvolvimento de uma tecnologia baseada em inteligência artificial para identificação de depressão em acadêmicos",
        "doi": "10.5935/1808-5687.20250509",
    },
)
_LICENSE = re.compile(
    r"creative commons|cc by(?:-nc)?(?:-nd|-sa)?|licen[cç]a creative", re.IGNORECASE
)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _pdfinfo(path: Path) -> dict[str, str]:
    result = _run(["pdfinfo", "-enc", "UTF-8", str(path)])
    info = {}
    if result.returncode != 0:
        return info
    for line in result.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def _page_text(path: Path, page: int) -> str:
    result = _run(
        ["pdftotext", "-enc", "UTF-8", "-layout", "-f", str(page), "-l", str(page), str(path), "-"]
    )
    return result.stdout if result.returncode == 0 else ""


def _warnings_for(text: str, pages: list[str]) -> list[str]:
    warnings = []
    if "\ufffd" in text or text.count("Ã") > 20:
        warnings.append("sinais de falha de codificação")
    tokens = re.findall(r"\S+", text)
    short = sum(len(token) == 1 for token in tokens)
    if tokens and short / len(tokens) > 0.15:
        warnings.append("texto fragmentado: muitos caracteres isolados")
    if pages and sum(len(page.strip()) < 40 for page in pages) > max(1, len(pages) // 3):
        warnings.append("várias páginas com pouco ou nenhum texto")
    return warnings


def _license_evidence() -> dict:
    path = STAGING / "license_evidence.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    checked = payload.get("checked_at")
    documents = payload.get("documents", {})
    for item in documents.values():
        item.setdefault("checked_at", checked)
    return documents


def _numeric_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    numeric = sum(bool(re.fullmatch(r"\d+(?:[.,]\d+)?%?", line)) for line in lines)
    return numeric >= 12 and "tabela" in text.casefold()


def apply_license(record: dict, evidence: dict | None, pdf_text: str = "") -> None:
    """Licença no PDF ou em página oficial conferida. Ausência no PDF não a invalida."""
    record["third_party_content_review"] = (
        "há marca de reprodução ou adaptação de obra de terceiros; revisar antes da recuperação"
        if re.search(r"reproduzido de|adaptado de|fonte:\s", pdf_text, re.IGNORECASE)
        else "nenhuma reprodução de obra de terceiros encontrada no texto"
    )
    if _numeric_table(pdf_text):
        record["retrieval_exclusion"] = (
            "Tabela numérica linearizada: cabeçalhos e valores não ficam na mesma linha. "
            "Excluir essa tabela da recuperação até revisão humana. O PDF original não foi alterado."
        )
    match = _LICENSE.search(pdf_text)
    if match:
        record.update(
            license=match.group(0),
            license_verification_method="pdf_text",
            license_verification_status="confirmada_no_pdf",
            license_verified=True,
            attribution_required=True,
        )
        return
    evidence = evidence or {}
    record["license_source_url"] = evidence.get("license_source_url")
    record["license_note"] = evidence.get("note") or (
        "o PDF não declara licença; isso não a invalida"
    )
    if evidence.get("status") == "confirmed_on_official_page" and evidence.get("quote"):
        record.update(
            license=evidence.get("license"),
            license_verification_method="official_page",
            license_verified_at=evidence.get("checked_at"),
            license_verification_status="confirmada_na_pagina_oficial",
            license_verified=True,
            attribution_required=bool(evidence.get("attribution_required")),
        )
        return
    record.update(
        license=evidence.get("license"),
        license_verification_method="official_page_insufficient",
        license_verified_at=None,
        license_verification_status="revisao_humana",
        license_verified=False,
        attribution_required=evidence.get("attribution_required"),
    )


def _decision(record: dict) -> str:
    if record["extraction_status"] == "arquivo_ausente":
        return "VALIDAÇÃO PENDENTE"
    if record["extraction_status"] in {"assinatura_invalida", "sem_texto"}:
        return "REJEITADO"
    if record["extraction_warnings"] or not record["doi_in_text"] or not record["title_in_text"]:
        return "CORREÇÃO NECESSÁRIA"
    if not record["license_verified"]:
        return "VALIDAÇÃO PENDENTE"
    return "APTO PARA INGESTÃO"


def _identity_text(path: Path) -> str:
    info = _pdfinfo(path)
    pages = int(info["Pages"]) if info.get("Pages", "").isdigit() else 1
    return "\n".join(_page_text(path, number) for number in range(1, min(pages, 2) + 1)).casefold()


def _locate(article: dict, pdfs: list[Path]) -> Path | None:
    exact = STAGING / f"{article['document_id']}.pdf"
    if exact.is_file():
        return exact
    doi = article["doi"].casefold()
    opened = [(path, _identity_text(path)) for path in pdfs]
    hits = [path for path, text in opened if doi in text]
    if not hits:
        words = [word for word in re.findall(r"\w+", article["title"].casefold()) if len(word) > 4][:5]
        hits = [
            path for path, text in opened if sum(word in text for word in words) >= 3
        ]
    return hits[0] if len(hits) == 1 else None


def _base(article: dict, path: Path) -> dict:
    return {
        "document_id": article["document_id"],
        "title": article["title"],
        "authors": [],
        "publication_year": None,
        "doi": article["doi"],
        "source_url": "https://doi.org/" + article["doi"],
        "language": "pt",
        "language_verified": False,
        "license": None,
        "license_source_url": None,
        "license_verification_method": None,
        "license_verified_at": None,
        "license_verification_status": "pendente",
        "attribution_required": None,
        "third_party_content_review": None,
        "license_verified": False,
        "file_path": str(path.relative_to(ROOT)),
        "sha256": None,
        "page_count": None,
        "extraction_status": "arquivo_ausente",
        "extraction_warnings": ["PDF não está no repositório; nenhum download foi feito"],
        "ingestion_approved": False,
        "doi_in_text": False,
        "title_in_text": False,
        "poppler_words": None,
        "rag_words": None,
        "weak_pages": [],
    }


def _content_words(text: str) -> list[str]:
    return [word.casefold() for word in re.findall(r"\w+", text) if len(word) > 3]


def _coverage(reference: str, extracted: str) -> float:
    words = _content_words(reference)
    if not words:
        return 0.0
    found = set(_content_words(extracted))
    return sum(word in found for word in words) / len(words)


def _publication_year(first_page: str, doi: str) -> int | None:
    text = first_page.replace(doi, " ")
    text = re.sub(r"\b(?:19|20)\d{2}-\d{3,4}\b", " ", text)
    years = [int(year) for year in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text) if int(year) >= 1990]
    return years[-1] if years else None


def _authors(first_page: str) -> list[str]:
    head = re.split(r"\bResumo\b", first_page, maxsplit=1)[0]
    for line in reversed([re.sub(r"\s+", " ", item).strip() for item in head.splitlines() if item.strip()]):
        if re.search(r"Universidade|http|DOI|ISSN|Revista|vol\.", line, re.IGNORECASE):
            continue
        if not re.search(r"[A-Za-zÀ-ÿ]\d|,", line):
            continue
        names = [re.sub(r"\d+", "", part).strip(" ,") for part in line.split(",")]
        names = [name for name in names if len(name.split()) >= 2]
        if names:
            return names
    return []


def _loss_cause() -> str:
    return (
        "O extrator junta strings literais em Latin-1, sem posição e sem mapa da fonte. "
        "O texto sai espaçado letra a letra e, em parte do arquivo, misturado com bytes que não são palavras. "
        "O Poppler reconstrói os parágrafos. A rotação da página é 0; colunas e tabelas não são recompostas."
    )


def _weak_pages(page_texts: list[str], extracted: str) -> list[dict]:
    gaps = []
    for number, poppler in enumerate(page_texts, start=1):
        total = len(_content_words(poppler))
        if total < 20:
            continue
        ratio = _coverage(poppler, extracted)
        if ratio < 0.7:
            gaps.append(
                {
                    "page": number,
                    "poppler_content_words": total,
                    "coverage": round(ratio, 3),
                }
            )
    return gaps


def audit_file(article: dict, path: Path) -> dict:
    record = _base(article, path)
    data = path.read_bytes()
    record["sha256"] = hashlib.sha256(data).hexdigest()
    if not data.startswith(b"%PDF-"):
        record["extraction_status"] = "assinatura_invalida"
        record["extraction_warnings"] = ["arquivo não começa com %PDF-"]
        record["decision"] = _decision(record)
        return record
    info = _pdfinfo(path)
    pages = int(info["Pages"]) if info.get("Pages", "").isdigit() else None
    record["page_count"] = pages
    warnings = []
    if b"startxref" not in data and b"trailer" not in data:
        warnings.append("estrutura PDF sem trailer ou startxref")
    if info.get("Encrypted", "").lower().startswith("yes"):
        warnings.append("PDF marcado como criptografado")
    if pages is None or pages < 1:
        record["extraction_status"] = "sem_texto"
        record["extraction_warnings"] = warnings + ["pdfinfo não informou páginas"]
        record["decision"] = _decision(record)
        return record
    page_texts = [_page_text(path, number) for number in range(1, pages + 1)]
    reference = "\n".join(page_texts)
    empty = sum(not page.strip() for page in page_texts)
    if empty:
        warnings.append(f"{empty} página(s) sem texto no pdftotext; OCR não foi usado")
    warnings.extend(_warnings_for(reference, page_texts))
    lowered = reference.casefold()
    record["doi_in_text"] = article["doi"].casefold() in lowered
    title_terms = [
        term for term in re.findall(r"\w+", article["title"].casefold()) if len(term) > 4
    ]
    present = sum(term in lowered for term in title_terms)
    record["title_in_text"] = bool(title_terms) and present >= max(1, len(title_terms) // 2)
    if not record["doi_in_text"]:
        warnings.append("DOI declarado não aparece no texto extraído")
    if not record["title_in_text"]:
        warnings.append("título declarado não foi encontrado no texto")
    record["has_sections"] = bool(re.search(r"resumo|introdu|refer[eê]ncias", lowered))
    record["has_tables_or_figures"] = bool(re.search(r"\btabela\b|\bfigura\b", lowered))
    if not record["has_sections"]:
        warnings.append("não foi encontrada marca de resumo, introdução ou referências")
    try:
        extracted = read_document(path)
    except (OSError, ValueError) as error:
        extracted = ""
        warnings.append(f"extrator do projeto não obteve texto: {error}")
    reference_size = len(reference.split())
    extracted_size = len(extracted.split())
    record["poppler_words"] = reference_size
    record["rag_words"] = extracted_size
    record["content_coverage"] = round(_coverage(reference, extracted), 3)
    record["authors"] = _authors(page_texts[0])
    record["weak_pages"] = _weak_pages(page_texts, extracted)
    record["extraction_cause"] = (
        _loss_cause() if record["content_coverage"] < 0.7
        else "pdftotext no modo de leitura, com páginas separadas e hífen de fim de linha recomposto"
    )
    record["page_rotation"] = info.get("Page rot")
    year = _publication_year(page_texts[0], article["doi"])
    if year:
        record["publication_year"] = year
        record["publication_year_source"] = "primeira_pagina"
    if reference_size < 200:
        warnings.append("pdftotext devolveu pouco texto; o arquivo pode ser digitalizado")
    elif record["content_coverage"] < 0.7:
        pages = ", ".join(str(item["page"]) for item in record["weak_pages"]) or "várias"
        warnings.append(
            f"o extrator preserva {record['content_coverage']:.0%} das palavras do Poppler "
            f"({extracted_size} tokens contra {reference_size}). Páginas afetadas: {pages}. "
            f"{record['extraction_cause']}"
        )
    record["language_verified"] = bool(re.search(r"\b(não|saúde|artigo|resumo)\b", lowered))
    record["extraction_status"] = "texto_extraido" if extracted.strip() else "sem_texto"
    record["extraction_warnings"] = warnings
    apply_license(
        record, _license_evidence().get(article["document_id"]), extracted or reference
    )
    record["decision"] = _decision(record)
    record["ingestion_approved"] = record["decision"] == "APTO PARA INGESTÃO"
    return record


def main() -> None:
    pdfs = sorted(STAGING.glob("*.pdf"))
    hashes: dict[str, list[str]] = {}
    for path in pdfs:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.setdefault(digest, []).append(path.name)
    documents = []
    used: set[Path] = set()
    for article in ARTICLES:
        path = _locate(article, [item for item in pdfs if item not in used])
        if path is None:
            record = _base(article, STAGING / f"{article['document_id']}.pdf")
            record["decision"] = _decision(record)
            documents.append(record)
            continue
        used.add(path)
        documents.append(audit_file(article, path))
    manifest = {
        "audited_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "production_sqlite_written": False,
        "reference_tool": "pdftotext/pdfinfo (Poppler, já instalado)",
        "project_extractor": "agents.copilot.literature.read_document",
        "duplicate_sha256": [names for names in hashes.values() if len(names) > 1],
        "unassigned_pdfs": [path.name for path in pdfs if path not in used],
        "documents": documents,
    }
    (STAGING / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for item in documents:
        print(
            f"{item['document_id']}\t{item['extraction_status']}\t"
            f"{item['page_count']}\t{item['decision']}"
        )


if __name__ == "__main__":
    main()
