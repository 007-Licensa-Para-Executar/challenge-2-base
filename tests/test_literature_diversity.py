"""Seleção de trechos científicos. Os textos são fictícios e não abrem a base real."""

from datetime import UTC, datetime
from types import SimpleNamespace

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.literature import (
    LiteratureService,
    LiteratureStore,
    editorial_header,
    ingest_file,
    literature_test_scope,
    select_literature_passages,
    translated_abstract,
)
from agents.copilot.retriever import Retriever
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore

PORTUGUESE = "O resumo em português diz que a psicoterapia preserva o cuidado humano."
SPANISH = "El resumen presenta los desafios de la psicoterapia y los limites del cuidado humano."
ENGLISH = (
    "The abstract describes the limits of psychotherapy and the care of patients "
    "with anxiety from that perspective and without another source."
)
BODY = "O corpo descreve a supervisão humana no atendimento clínico diário."
HEADER = "Revista Exemplo Print version ISSN 0000-0000 vol. 9 Editorial."
QUESTION = "O que a psicoterapia faz com o cuidado humano?"


def piece(quote):
    return SimpleNamespace(quote=quote)


def test_translation_does_not_take_a_second_slot():
    assert translated_abstract(SPANISH)
    assert translated_abstract(ENGLISH)
    assert not translated_abstract(PORTUGUESE)
    chosen = select_literature_passages(
        QUESTION, [piece(SPANISH), piece(PORTUGUESE), piece(BODY)], 2
    )
    assert [item.quote for item in chosen] == [PORTUGUESE, BODY]


def test_translation_stays_when_it_is_the_only_evidence():
    chosen = select_literature_passages(QUESTION, [piece(SPANISH), piece(BODY)], 1)
    assert chosen[0].quote == SPANISH


def test_pure_header_yields_to_the_body_and_a_glued_abstract_stays():
    assert editorial_header(HEADER)
    glued = f"{HEADER} Resumo {PORTUGUESE}"
    assert not editorial_header(glued)
    chosen = select_literature_passages(
        "O que a supervisão humana descreve no atendimento clínico?",
        [piece(HEADER), piece(BODY)],
        1,
    )
    assert chosen[0].quote == BODY


def test_distinct_passages_of_the_same_document_both_stay():
    other = "Outra passagem mostra que a formação clínica exige supervisão humana contínua."
    chosen = select_literature_passages(
        "O que a supervisão humana descreve no atendimento e na formação?",
        [piece(BODY), piece(other)],
        2,
    )
    assert [item.quote for item in chosen] == [BODY, other]


def test_answer_keeps_identity_abstains_and_skips_bibliography(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    with literature_test_scope():
        path = tmp_path / "nota.txt"
        path.write_text(
            "A discussão conclui que a psicoterapia mantém o cuidado humano.\n\n"
            "Referências\n"
            "Silva, A. (2024). Revista Exemplo. https://doi.org/10.0000/exemplo\n",
            encoding="utf-8",
        )
        store = LiteratureStore(tmp_path / "literatura.sqlite3")
        ingest_file(
            store, path, document_id="nota_local", title="Nota local",
            authors=["Autora Demo"], year=2024, url="https://example.local/nota",
        )
        service = LiteratureService(store, Retriever())
        answer = service.answer(
            "O que a discussão conclui sobre o cuidado humano na psicoterapia?", "extractive",
        )
        assert answer.status == "ok"
        source = answer.sources[0]
        assert source.chunk_id.startswith("nota_local")
        assert source.quote in answer.answer
        assert source.url == "https://example.local/nota"
        assert "referencias" not in source.section
        missing = service.answer("Qual é a dose do medicamento controlado?", "extractive")
        assert missing.status == "insufficient_evidence"
        assert missing.sources == ()


def test_diary_retrieval_is_unchanged(tmp_path):
    store = DiaryStore(tmp_path / "diarios.sqlite3")
    when = datetime(2026, 1, 1, tzinfo=UTC)
    store.save(DiaryRecord(
        record_id="ana_99", patient_id="patient_ana", recorded_at=when,
        original_text="Hoje li um livro na biblioteca.", source_title="Diário sintético",
    ))
    store.save(DiaryRecord(
        record_id="ana_100", patient_id="patient_ana", recorded_at=when,
        original_text="O outro relato fala de caminhada no parque.", source_title="Diário sintético",
    ))
    answer = CopilotService(store, Retriever()).answer(
        Query(patient_id="patient_ana", question="Onde está o livro da biblioteca?"), "extractive",
    )
    assert answer.status == "ok"
    assert [item.record_id for item in answer.evidence] == ["ana_99"]
