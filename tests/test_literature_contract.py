"""Contrato de consulta da literatura. Usa texto fictício e não abre a base experimental."""

import sqlite3

import pytest

from agents.copilot.literature import (
    LicenseError,
    LiteraturePassage,
    LiteratureService,
    LiteratureStore,
    Retriever,
    build_document,
    ingest_file,
    literature_test_scope,
    search_literature,
)


@pytest.fixture
def fixtures(monkeypatch):
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    with literature_test_scope():
        yield


def _article(tmp_path, text, name, **metadata):
    path = tmp_path / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    ingest_file(store, path, document_id=name, **metadata)
    return store


def test_contract_returns_a_citation_and_keeps_the_bm25_passage(tmp_path, fixtures):
    store = _article(
        tmp_path,
        "A discussão conclui que a psicoterapia mantém o cuidado humano.\n",
        "nota_doi",
        title="Cuidado humano na psicoterapia",
        authors=["Autora Demo"],
        year=2024,
        doi="10.0000/cuidado",
        license="CC BY 4.0",
    )
    question = "O que a discussão conclui sobre o cuidado humano na psicoterapia?"
    result = search_literature(question, db_path=store.db_path)
    answer = LiteratureService(store, Retriever()).answer(question, "extractive")
    assert result.status == "evidence"
    assert result.evidence_sufficient is True
    assert result.retrieval_backend == "bm25"
    source = result.sources[0]
    assert source.title == "Cuidado humano na psicoterapia"
    assert source.authors == ("Autora Demo",)
    assert source.doi == "10.0000/cuidado"
    assert source.license == "CC BY 4.0"
    assert source.chunk_id == answer.sources[0].chunk_id
    record = store.list_documents()[0].original_text
    assert record[source.start_char:source.end_char] == source.quote_text
    assert source.chunk_id.endswith(f":{source.start_char}:{source.end_char}")
    again = search_literature(question, db_path=store.db_path)
    assert again.sources[0].chunk_id == source.chunk_id
    assert "patient_id" not in LiteraturePassage.model_fields
    assert "patient_id" not in result.model_dump()


def test_contract_accepts_a_url_when_the_doi_is_absent(tmp_path, fixtures):
    store = _article(
        tmp_path,
        "A discussão conclui que a psicoterapia mantém o cuidado humano.\n",
        "nota_url",
        title="Nota sem identificador DOI",
        authors=["Autora Demo"],
        year=2024,
        url="https://example.local/nota",
    )
    result = search_literature(
        "O que a discussão conclui sobre o cuidado humano na psicoterapia?",
        db_path=store.db_path,
    )
    source = result.sources[0]
    assert source.doi is None
    assert source.source_url == "https://example.local/nota"


def test_contract_separates_retrieval_from_insufficient_quantity(tmp_path, fixtures):
    store = _article(
        tmp_path,
        "A nota fictícia registra 8 sessões de leitura clínica.\n",
        "nota_quantidade",
        title="Nota de quantidade",
        authors=["Autora Demo"],
        year=2024,
        doi="10.0000/quantidade",
    )
    kept = search_literature("Quantas sessões de leitura a nota registra?", db_path=store.db_path)
    assert kept.evidence_sufficient is True
    assert "8 sessões" in kept.sources[0].quote_text
    missing = search_literature("Quantos autores a nota registra?", db_path=store.db_path)
    assert missing.status == "insufficient_evidence"
    assert missing.evidence_sufficient is False
    assert missing.sources == ()
    assert missing.retrieved_passages


def test_contract_abstains_without_evidence(tmp_path, fixtures):
    store = _article(
        tmp_path,
        "A discussão conclui que a psicoterapia mantém o cuidado humano.\n",
        "nota_tema",
        title="Cuidado humano",
        authors=["Autora Demo"],
        year=2024,
        doi="10.0000/tema",
    )
    result = search_literature("Qual é a dose de sertralina para insônia?", db_path=store.db_path)
    assert result.status == "insufficient_evidence"
    assert result.sources == ()


def test_contract_reports_configuration_and_empty_corpus(tmp_path, monkeypatch, fixtures):
    monkeypatch.delenv("LITERATURE_DB_PATH", raising=False)
    missing = search_literature("cuidado humano")
    assert missing.status == "configuration_error"
    assert missing.error_code == "database_unconfigured"
    absent = search_literature("cuidado humano", db_path=tmp_path / "ausente.sqlite3")
    assert absent.error_code == "database_unavailable"
    blocked = search_literature("cuidado humano", db_path=tmp_path)
    assert blocked.error_code == "database_unavailable"
    invalid = search_literature("cuidado humano", top_k=0, db_path=tmp_path / "ausente.sqlite3")
    assert invalid.error_code == "invalid_top_k"
    empty = tmp_path / "vazia.sqlite3"
    with sqlite3.connect(empty) as conn:
        conn.execute("SELECT 1")
    corpus = search_literature("cuidado humano", db_path=empty)
    assert corpus.status == "empty_corpus"
    assert corpus.evidence_sufficient is False
    corrupt = tmp_path / "ilegivel.sqlite3"
    corrupt.write_text("isto não é sqlite", encoding="utf-8")
    failed = search_literature("cuidado humano", db_path=corrupt)
    assert failed.status == "error"
    assert failed.error_code == "storage_error"
    assert failed.answer_extractive


def test_unlicensed_text_stays_out_and_e5_is_not_consulted(tmp_path, monkeypatch):
    monkeypatch.delenv("LITERATURE_FIXTURES", raising=False)
    store = LiteratureStore(tmp_path / "fechada.sqlite3")
    document = build_document(
        document_id="nota_bloqueada",
        title="Nota bloqueada",
        authors=["Autora"],
        original_text="A discussão conclui que a psicoterapia mantém o cuidado humano.\n",
        synthetic=True,
    )
    with pytest.raises(LicenseError):
        store.save(document)
    assert search_literature("cuidado humano", db_path=store.db_path).error_code == "database_unavailable"
    refused = LiteratureService(store, Retriever("e5")).consult("O que a discussão conclui sobre o cuidado humano?")
    assert refused.status == "configuration_error"
    assert refused.error_code == "backend_not_bm25"
