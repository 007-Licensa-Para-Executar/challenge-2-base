"""Decisão de licença do auditor, sem rede e sem banco."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "literature_audit", ROOT / "knowledge_base" / "literature" / "staging" / "audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def _record(**extra):
    record = {
        "extraction_status": "texto_extraido",
        "extraction_warnings": [],
        "doi_in_text": True,
        "title_in_text": True,
        "license_verified": False,
    }
    record.update(extra)
    return record


def test_official_page_approves_when_the_pdf_has_no_license_sentence():
    record = _record()
    audit.apply_license(record, {
        "status": "confirmed_on_official_page",
        "license": "CC BY 4.0",
        "license_source_url": "https://exemplo.oficial/artigo",
        "quote": "Creative Commons Attribution License",
        "attribution_required": True,
        "checked_at": "2026-11-12T21:20:00+00:00",
    }, "Resumo sem a palavra licença.")
    assert record["license_verified"] is True
    assert record["license_verification_method"] == "official_page"
    assert record["license_verification_status"] == "confirmada_na_pagina_oficial"
    assert audit._decision(record) == "APTO PARA INGESTÃO"


def test_unreachable_official_page_stays_pending_and_is_not_invalid():
    record = _record()
    audit.apply_license(record, {
        "status": "human_review_required",
        "license": None,
        "license_source_url": "https://exemplo.oficial/artigo",
        "note": "página bloqueada; licença não classificada como inválida",
    }, "Resumo sem licença.")
    assert record["license_verified"] is False
    assert record["license_verification_status"] == "revisao_humana"
    assert record["license"] is None
    assert audit._decision(record) == "VALIDAÇÃO PENDENTE"


def test_poor_extraction_blocks_an_official_license():
    record = _record(extraction_warnings=["texto fragmentado"])
    audit.apply_license(record, {
        "status": "confirmed_on_official_page",
        "license": "CC BY 4.0",
        "quote": "Creative Commons",
        "attribution_required": True,
        "checked_at": "2026-11-12T21:20:00+00:00",
    })
    assert audit._decision(record) == "CORREÇÃO NECESSÁRIA"


def test_numeric_table_is_flagged_without_changing_the_source_text():
    text = "Tabela 1\n" + "\n".join(str(number) for number in range(20))
    record = _record()
    audit.apply_license(record, None, text)
    assert "Tabela numérica" in record["retrieval_exclusion"]
    assert text.startswith("Tabela 1")
