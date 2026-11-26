"""Coleção científica local, separada dos diários sintéticos."""

import hashlib
import json
import sqlite3
import subprocess
import zlib
from datetime import UTC, datetime

import pytest

from agents.copilot.contracts import DiaryRecord, DraftAnswer, Query, Statement
from agents.copilot.literature import (
    LITERATURE_GENERATION_TIMEOUT,
    UNVERIFIED_NOTICE,
    DuplicateDocumentError,
    LicenseError,
    LiteratureService,
    LiteratureStore,
    ingest_file,
    literature_evidence,
    literature_test_scope,
    load_catalog,
    read_document,
)
from agents.copilot.model import GenerationError, OllamaGenerator
from agents.copilot.retriever import Retriever, chunk_record, supported_evidence
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore


@pytest.fixture(autouse=True)
def literature_fixtures(monkeypatch):
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    with literature_test_scope():
        yield


QUESTION = "Quais efeitos de agentes conversacionais no bem-estar?"
MINORITY = "Quais efeitos de agentes conversacionais no bem-estar humano?"
PARTIAL = "Agentes conversacionais aparecem neste texto fictício."


def pdf_bytes(text: str, *, compress: bool = False) -> bytes:
    return page_pdf([text], compress=compress)


def page_pdf(pages: list[str], *, compress: bool = False) -> bytes:
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]

    def add(body: bytes) -> None:
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{len(offsets) - 1} 0 obj\n".encode() + body + b"\nendobj\n")

    first_page = 3
    first_content = 3 + len(pages)
    kids = " ".join(f"{first_page + index} 0 R" for index in range(len(pages)))
    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    streams = []
    for text in pages:
        literal = text.encode("latin-1").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        shown = b"(" + literal + b") Tj" if text else b""
        streams.append(b"BT /F1 12 Tf " + shown + b" ET")
    font = (
        b"<< /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
        b"/BaseFont /Helvetica /Encoding /WinAnsiEncoding >> >> >>"
    )
    for index in range(len(pages)):
        add(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 400] "
            + font
            + f" /Contents {first_content + index} 0 R >>".encode()
        )
    for stream in streams:
        payload = zlib.compress(stream) if compress else stream
        filt = b" /Filter /FlateDecode" if compress else b""
        add(f"<< /Length {len(payload)}{filt.decode()} >>\nstream\n".encode() + payload + b"\nendstream")
    xref_at = sum(len(chunk) for chunk in chunks)
    xref = [f"xref\n0 {len(offsets)}\n".encode(), b"0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    chunks.extend(xref)
    chunks.append(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    return b"".join(chunks)


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


def test_long_article_keeps_order_license_and_rejects_a_second_text(tmp_path, monkeypatch):
    paragraph = "A psicoterapia discute limites da empatia artificial e da privacidade. "
    text = (paragraph * 500).strip()
    path = tmp_path / "longo.txt"
    path.write_text(text, encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    metadata = {
        "document_id": "artigo_longo", "title": "Artigo longo", "authors": ["Autora"], "year": 2025,
        "doi": "10.0000/longo", "url": "https://doi.org/10.0000/longo", "license": "CC BY 4.0",
        "synthetic": False,
    }
    manifest = tmp_path / "manifesto.json"
    manifest.write_text(json.dumps({"documents": [{
        "document_id": "artigo_longo", "title": "Artigo longo", "license": "CC BY 4.0",
        "doi": "10.0000/longo", "status": "aprovada",
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }]}), encoding="utf-8")
    monkeypatch.setattr("agents.copilot.literature.LITERATURE_MANIFEST", manifest)
    assert ingest_file(store, path, **metadata) == "saved"
    saved = store.list_documents()[0]
    assert saved.license == "CC BY 4.0"
    assert saved.synthetic is False
    assert len(saved.sections) > 1
    assert all(len(section.text) <= 18000 for section in saved.sections)
    cursor = 0
    for section in saved.sections:
        found = saved.original_text.find(section.text, cursor)
        assert found >= cursor
        cursor = found + len(section.text)
    assert ingest_file(store, path, **metadata) == "skipped"
    path.write_text(text + " Outro texto.", encoding="utf-8")
    with pytest.raises(LicenseError) as refused:
        ingest_file(store, path, **metadata)
    assert refused.value.code == "license_identity_mismatch"
    assert store.list_documents()[0].original_text == text


def _article(tmp_path, text, name="artigo.txt"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    ingest_file(
        store, path, document_id="artigo_local", title="Artigo local",
        authors=["Autora"], year=2024, doi="10.0000/local",
    )
    return store


def test_bibliography_stays_stored_and_out_of_the_answer(tmp_path):
    store = _article(tmp_path, """A discussão conclui que a psicoterapia mantém o cuidado humano.
A conclusão não recomenda substituir o profissional.

Referências
Silva, A. (2024). Assistentes virtuais e saúde mental. Revista Exemplo. https://doi.org/10.0000/exemplo
Souza, B. (2023). Outro estudo sobre regulação. Revista Exemplo. https://doi.org/10.0000/outro
""")
    saved = store.list_documents()[0]
    assert saved.bibliography_status == "separada"
    assert "10.0000/exemplo" in saved.original_text
    bibliography = [section for section in saved.sections if section.role == "bibliography"]
    assert bibliography and bibliography[0].chunk_ids
    chunk_id = bibliography[0].chunk_ids[0]
    record_id, start, end = chunk_id.rsplit(":", 2)
    assert record_id == bibliography[0].record_id
    assert bibliography[0].text[int(start) : int(end)] in saved.original_text
    service = LiteratureService(store, Retriever())
    foreign = service.answer(
        "Quais resultados a Revista Exemplo apresenta sobre assistentes virtuais?", "extractive",
    )
    assert foreign.status == "insufficient_evidence"
    assert foreign.sources == ()
    discussion = service.answer(
        "O que a discussão conclui sobre o cuidado humano na psicoterapia?", "extractive",
    )
    assert discussion.status == "ok"
    assert discussion.support == "extrativo"
    assert "cuidado humano" in discussion.answer
    assert all("referencias" not in source.section for source in discussion.sources)


def test_inline_citation_remains_searchable(tmp_path):
    store = _article(tmp_path, """A discussão cita Silva (2024) ao descrever o cuidado humano na psicoterapia.
O parágrafo permanece no corpo do artigo.

Referências
Silva, A. (2024). Assistentes virtuais e saúde mental. https://doi.org/10.0000/exemplo
Souza, B. (2023). Outro estudo sobre regulação. https://doi.org/10.0000/outro
""")
    answer = LiteratureService(store, Retriever()).answer(
        "O que a discussão descreve sobre o cuidado humano na psicoterapia?", "extractive",
    )
    assert answer.status == "ok"
    assert "Silva (2024)" in answer.answer
    assert all(source.section == "texto" for source in answer.sources)


def test_unclear_reference_heading_is_kept_and_not_answered(tmp_path):
    store = _article(tmp_path, """A discussão descreve o cuidado humano na psicoterapia.

Referências
Esta nota isolada não forma uma lista de obras.
""")
    saved = store.list_documents()[0]
    assert saved.bibliography_status == "incerta"
    assert any(section.role == "uncertain" for section in saved.sections)
    assert "nota isolada" in saved.original_text
    service = LiteratureService(store, Retriever())
    assert service.answer(
        "O que diz a nota isolada sobre a lista de obras?", "extractive",
    ).status == "insufficient_evidence"
    kept = service.answer(
        "O que a discussão descreve sobre o cuidado humano na psicoterapia?", "extractive",
    )
    assert kept.status == "ok"
    assert "nota isolada" not in kept.answer


def test_generation_timeout_and_missing_support_do_not_invent_a_source(tmp_path):
    store = _article(tmp_path, "A discussão conclui que a psicoterapia mantém o cuidado humano.\n")
    question = "O que a discussão conclui sobre o cuidado humano na psicoterapia?"

    class Down:
        def generate(self, query, evidence, *, instructions=None):
            raise GenerationError("generation_timeout")

    timed = LiteratureService(store, Retriever(), Down()).answer(question, "ollama")
    assert timed.status == "error"
    assert timed.error_code == "generation_timeout"
    assert timed.sources == ()

    class Offline:
        def generate(self, query, evidence, *, instructions=None):
            raise GenerationError("service_unavailable")

    offline = LiteratureService(store, Retriever(), Offline()).answer(question, "ollama")
    assert offline.status == "error"
    assert offline.error_code == "service_unavailable"

    class Empty:
        def generate(self, query, evidence, *, instructions=None):
            raise GenerationError("insufficient_evidence")

    assert LiteratureService(store, Retriever(), Empty()).answer(question, "ollama").status == (
        "insufficient_evidence"
    )

    class Extra:
        def generate(self, query, evidence, *, instructions=None):
            return DraftAnswer(statements=[Statement(
                text="A discussão recomenda uma dose empírica inédita.",
                evidence_ids=[evidence[0].chunk_id],
            )])

    synthesized = LiteratureService(store, Retriever(), Extra()).answer(question, "ollama")
    assert synthesized.status == "ok"
    assert synthesized.support == "nao_verificada"
    assert UNVERIFIED_NOTICE in synthesized.answer
    assert "validação clínica" in synthesized.answer
    assert synthesized.sources[0].quote.startswith("A discussão conclui")
    assert OllamaGenerator().timeout == 60
    assert LITERATURE_GENERATION_TIMEOUT == 150


def _pair(tmp_path):
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    first = tmp_path / "cuidado.txt"
    second = tmp_path / "privacidade.txt"
    first.write_text(
        "A discussão conclui que a psicoterapia mantém o cuidado humano.\n", encoding="utf-8",
    )
    second.write_text(
        "A discussão conclui que a psicoterapia mantém o cuidado humano e a privacidade.\n",
        encoding="utf-8",
    )
    ingest_file(
        store, first, document_id="artigo_cuidado",
        title="Cuidado humano na psicoterapia contemporanea", authors=["Autora"],
        year=2024, doi="10.0000/cuidado",
    )
    ingest_file(
        store, second, document_id="artigo_privacidade",
        title="Privacidade digital em servicos clinicos", authors=["Autor"],
        year=2023, doi="10.0000/privacidade",
    )
    return store


def test_named_study_is_not_replaced_by_another_document(tmp_path):
    store = _pair(tmp_path)
    service = LiteratureService(store, Retriever())
    present = service.answer(
        "O que conclui o artigo Cuidado humano na psicoterapia contemporanea?", "extractive",
    )
    assert present.status == "ok"
    assert {source.document_id for source in present.sources} == {"artigo_cuidado"}
    assert "10.0000/cuidado" in present.answer
    assert "Origem:" in present.answer
    absent = service.answer(
        'O que conclui o artigo "Regulacao etica de algoritmos clinicos"?', "extractive",
    )
    assert absent.status == "insufficient_evidence"
    assert "não contém o documento" in absent.answer
    assert absent.sources == ()
    by_doi = service.answer(
        "O que o documento 10.0000/privacidade conclui sobre o cuidado humano?", "extractive",
    )
    assert {source.document_id for source in by_doi.sources} == {"artigo_privacidade"}
    missing_doi = service.answer(
        "Silva, A. (2024). Regulacao etica de algoritmos clinicos. https://doi.org/10.9999/ausente "
        "O que esse estudo conclui sobre o cuidado humano na psicoterapia?",
        "extractive",
    )
    assert missing_doi.status == "insufficient_evidence"
    assert "10.9999/ausente" in missing_doi.answer
    assert missing_doi.sources == ()
    generic = service.answer(
        "O que a discussão conclui sobre o cuidado humano na psicoterapia?", "extractive",
    )
    assert generic.status == "ok"
    assert {source.document_id for source in generic.sources} == {
        "artigo_cuidado", "artigo_privacidade",
    }


def test_diary_retrieval_stays_independent_of_literature(tmp_path):
    diary_path = tmp_path / "diarios.sqlite3"
    DiaryStore(diary_path).save(DiaryRecord(
        record_id="ana_99", patient_id="patient_ana", recorded_at=datetime.now(UTC),
        original_text="Hoje li um livro na biblioteca.", source_title="Diário sintético",
    ))
    diary = CopilotService(DiaryStore(diary_path), Retriever()).answer(
        Query(patient_id="patient_ana", question="Onde está o livro da biblioteca?"), "extractive",
    )
    assert diary.status == "ok"
    assert "biblioteca" in diary.answer


def test_pdf_reading_order_accents_and_ingest_metadata(tmp_path):
    path = tmp_path / "artigo.pdf"
    path.write_bytes(page_pdf([
        "Ação científica e saúde mental.",
        "Referências do segundo estudo.",
    ]))
    text = read_document(path)
    assert "Ação científica e saúde mental." in text
    assert "Referências do segundo estudo." in text
    assert "\n\n" in text
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    assert ingest_file(
        store, path, document_id="nota_acento", title="Ação científica",
        authors=["Autora"], year=2025, doi="10.0000/acao",
    ) == "saved"
    saved = store.list_documents()[0]
    assert saved.doi == "10.0000/acao"
    assert saved.authors == ["Autora"]
    assert "Ação científica" in saved.original_text
    assert saved.chunk_ids


def test_pdf_rejects_corrupt_empty_fragmented_and_timeout(tmp_path, monkeypatch):
    corrupt = tmp_path / "ruim.pdf"
    corrupt.write_bytes(b"%PDF-1.4\nisto nao e um corpo de pdf")
    with pytest.raises(ValueError, match="inválido"):
        read_document(corrupt)
    empty = tmp_path / "vazio.pdf"
    empty.write_bytes(page_pdf([""]))
    with pytest.raises(ValueError, match="sem texto|ilegível"):
        read_document(empty)

    class Expired:
        def __call__(self, *args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="pdftotext", timeout=30)

    monkeypatch.setattr("agents.copilot.literature.subprocess.run", Expired())
    timed = tmp_path / "tempo.pdf"
    timed.write_bytes(pdf_bytes("agentes conversacionais e bem-estar"))
    with pytest.raises(ValueError, match="tempo limite"):
        read_document(timed)
    monkeypatch.setattr("agents.copilot.literature.shutil.which", lambda _name: None)
    assert read_document(timed) == "agentes conversacionais e bem-estar"
    fragmented = tmp_path / "frag.pdf"
    fragmented.write_bytes(pdf_bytes("R e v i s t a B i o e t i c a d a s a u d e"))
    with pytest.raises(ValueError, match="ilegível"):
        read_document(fragmented)


def test_pdf_joins_a_hyphen_split_across_lines(tmp_path, monkeypatch):
    path = tmp_path / "nota.pdf"
    path.write_bytes(pdf_bytes("agentes conversacionais e bem-estar"))

    class Result:
        returncode = 0
        stdout = "psico-\nterapia e saúde\fReferências finais\n".encode()

    monkeypatch.setattr("agents.copilot.literature.subprocess.run", lambda *args, **kwargs: Result())
    assert read_document(path) == "psicoterapia e saúde\n\nReferências finais"


def table_names(path):
    with sqlite3.connect(path) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
