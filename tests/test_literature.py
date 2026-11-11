"""Coleção científica local, separada dos diários sintéticos."""

import json
import sqlite3
import zlib
from datetime import UTC, datetime

import pytest

from agents.copilot.contracts import DiaryRecord, DraftAnswer, Query, Statement
from agents.copilot.literature import (
    DuplicateDocumentError,
    LiteratureService,
    LiteratureStore,
    ingest_file,
    literature_evidence,
    load_catalog,
    read_document,
)
from agents.copilot.retriever import Retriever, chunk_record, supported_evidence
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore
from tests.test_shell import shell

QUESTION = "Quais efeitos de agentes conversacionais no bem-estar?"
MINORITY = "Quais efeitos de agentes conversacionais no bem-estar humano?"
PARTIAL = "Agentes conversacionais aparecem neste texto fictício."


def pdf_bytes(text: str, *, compress: bool) -> bytes:
    literal = (
        text.encode("latin-1").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    )
    stream = b"BT (" + literal + b") Tj ET"
    payload = zlib.compress(stream) if compress else stream
    filt = b" /Filter /FlateDecode" if compress else b""
    header = f"<< /Length {len(payload)}{filt.decode()} >>".encode()
    return b"%PDF-1.4\n1 0 obj\n" + header + b"\nstream\n" + payload + b"\nendstream\nendobj\n%%EOF\n"


def test_txt_and_pdf_text_and_sections(tmp_path):
    txt = tmp_path / "nota.txt"
    txt.write_text("# introducao\n\nAgentes conversacionais e bem-estar.\n", encoding="utf-8")
    assert "bem-estar" in read_document(txt)
    for compress in (False, True):
        path = tmp_path / f"nota-{compress}.pdf"
        path.write_bytes(pdf_bytes("agentes conversacionais e bem-estar (local)", compress=compress))
        assert read_document(path) == "agentes conversacionais e bem-estar (local)"


def test_chunk_ids_match_the_shared_chunker(tmp_path):
    path = tmp_path / "artigo.txt"
    path.write_text(PARTIAL + "\n", encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    assert ingest_file(
        store, path, document_id="nota_local", title="Nota local", authors=["Autora"],
        year=2024, doi="10.0000/local",
    ) == "saved"
    document = store.list_documents()[0]
    record = DiaryRecord(
        record_id=document.sections[0].record_id,
        patient_id="literature",
        recorded_at=datetime(2024, 1, 1, tzinfo=UTC),
        original_text=document.sections[0].text,
        source_title=document.title[:200],
    )
    assert document.chunk_ids == [item.chunk_id for item in chunk_record(record, 600)]
    assert document.sections[0].name == "texto"
    assert document.doi == "10.0000/local"
    raw = sqlite3.connect(store.db_path).execute(
        "SELECT document_json FROM literature_documents"
    ).fetchone()[0]
    assert "patient_id" not in json.loads(raw)


def test_reingest_skips_the_same_text_and_keeps_the_original(tmp_path):
    path = tmp_path / "artigo.txt"
    path.write_text(PARTIAL, encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    metadata = {"document_id": "nota_local", "title": "Nota local", "authors": ["Autora"]}
    assert ingest_file(store, path, **metadata) == "saved"
    assert ingest_file(store, path, **metadata) == "skipped"
    path.write_text(PARTIAL + " Outro fato.", encoding="utf-8")
    with pytest.raises(DuplicateDocumentError):
        ingest_file(store, path, **metadata)
    assert store.list_documents()[0].original_text == PARTIAL
    assert len(store.list_documents()) == 1


def test_bm25_citation_metadata_and_a_gate_different_from_diaries(tmp_path):
    path = tmp_path / "artigo.txt"
    path.write_text(PARTIAL, encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    ingest_file(
        store, path, document_id="nota_local", title="Nota local", authors=["Autora Demo"],
        year=2024, url="https://example.local/nota",
    )
    document = store.list_documents()[0]
    record = DiaryRecord(
        record_id=document.sections[0].record_id,
        patient_id="literature",
        recorded_at=datetime(2024, 1, 1, tzinfo=UTC),
        original_text=document.sections[0].text,
        source_title=document.title,
    )
    ranked = Retriever().search([record], MINORITY, top_k=3)
    assert literature_evidence(MINORITY, ranked)
    assert supported_evidence(MINORITY, ranked) == []
    answer = LiteratureService(store, Retriever()).answer(MINORITY, "extractive")
    assert answer.status == "ok"
    source = answer.sources[0]
    assert source.quote == document.sections[0].text[0 : len(source.quote)]
    assert source.chunk_id == document.chunk_ids[0]
    assert source.document_id == "nota_local"
    assert source.authors == ("Autora Demo",)
    assert source.year == 2024
    assert source.url == "https://example.local/nota"
    assert source.section == "texto"
    missing = LiteratureService(store, Retriever()).answer(
        "Qual é a dose do medicamento controlado?", "extractive",
    )
    assert missing.status == "insufficient_evidence"
    assert missing.sources == ()


def test_catalog_retrieval_and_base_isolation(tmp_path):
    literature = LiteratureStore(tmp_path / "literatura.sqlite3")
    assert load_catalog(literature) == 3
    assert load_catalog(literature) == 0
    outside = tmp_path / "catalogo"
    outside.mkdir()
    (tmp_path / "secret.txt").write_text("segredo", encoding="utf-8")
    (outside / "catalog.jsonl").write_text(json.dumps({
        "document_id": "fuga", "title": "Fora", "authors": ["X"], "path": "../secret.txt",
    }), encoding="utf-8")
    with pytest.raises(ValueError):
        load_catalog(LiteratureStore(tmp_path / "outro.sqlite3"), outside)
    answer = LiteratureService(literature, Retriever()).answer(QUESTION, "extractive")
    assert answer.status == "ok"
    assert {item.document_id for item in answer.sources} == {"demo_agentes"}
    assert answer.sources[0].section == "introducao"
    diary_path = tmp_path / "diarios.sqlite3"
    DiaryStore(diary_path).save(DiaryRecord(
        record_id="ana_99", patient_id="patient_ana", recorded_at=datetime.now(UTC),
        original_text="Hoje li um livro na biblioteca.", source_title="Diário sintético",
    ))
    diary = CopilotService(DiaryStore(diary_path), Retriever()).answer(
        Query(patient_id="patient_ana", question="Onde está o livro da biblioteca?"), "extractive",
    )
    assert diary.status == "ok"
    assert diary.evidence[0].record_id == "ana_99"
    assert "demo_agentes" not in diary.answer
    assert "ana_99" not in answer.answer
    literature_tables = table_names(literature.db_path)
    diary_tables = table_names(diary_path)
    assert "diary_records" not in literature_tables
    assert "literature_documents" not in diary_tables


def test_ollama_generation_cites_only_retrieved_chunks(tmp_path):
    path = tmp_path / "artigo.txt"
    path.write_text(PARTIAL, encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    ingest_file(store, path, document_id="nota_local", title="Nota local", authors=["Autora"])

    class Fake:
        model = "qwen3:4b"

        def generate(self, query, evidence, *, instructions=None):
            assert query.patient_id == "literature"
            assert "literatura" in instructions.casefold()
            return DraftAnswer(statements=[Statement(
                text="O trecho local cita agentes conversacionais.",
                evidence_ids=[evidence[0].chunk_id],
            )])

    answer = LiteratureService(store, Retriever(), Fake()).answer(MINORITY, "ollama")
    assert answer.status == "ok"
    assert answer.sources[0].chunk_id in answer.answer
    assert answer.sources[0].quote == PARTIAL

    class Invented:
        def generate(self, query, evidence, *, instructions=None):
            return DraftAnswer(statements=[Statement(text="Fonte inventada.", evidence_ids=["ausente"])])

    refused = LiteratureService(store, Retriever(), Invented()).answer(MINORITY, "ollama")
    assert refused.status == "error"
    assert refused.error_code == "invalid_citation"
    assert refused.sources == ()


def test_menu_literature_stays_apart_from_diaries(tmp_path):
    diary_db = tmp_path / "diarios.sqlite3"
    literature_db = tmp_path / "literatura.sqlite3"
    instance, output, calls = shell(tmp_path, [
        "literatura", "extrativo", "s", QUESTION, "voltar",
    ])
    instance.synthetic = True
    instance.copilot_db = diary_db
    instance.literature_db = literature_db
    instance.handle("/copiloto")
    text = "\n".join(output)
    assert "Origem literatura | demo_agentes |" in text
    assert "introducao" in text
    assert "patient_ana" not in text
    assert literature_db.exists()
    assert not diary_db.exists()
    assert not calls


def table_names(path):
    with sqlite3.connect(path) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
