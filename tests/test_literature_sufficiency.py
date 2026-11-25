"""Pergunta de quantidade exige o número no próprio trecho. Textos fictícios."""

from datetime import UTC, datetime
from types import SimpleNamespace

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.literature import (
    LiteratureService,
    LiteratureStore,
    ingest_file,
    literature_evidence,
    literature_test_scope,
)
from agents.copilot.retriever import Retriever
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore

QUESTION = "Quantas sessões o protocolo descreve?"


def piece(quote):
    return SimpleNamespace(quote=quote)


def test_quantity_with_digit_and_written_number_is_kept():
    kept = literature_evidence(QUESTION, [
        piece("O protocolo descreve 8 sessões de leitura."),
        piece("O protocolo descreve quatro sessões de leitura."),
    ])
    assert [item.quote for item in kept] == [
        "O protocolo descreve 8 sessões de leitura.",
        "O protocolo descreve quatro sessões de leitura.",
    ]


def test_quantity_without_a_number_is_refused():
    assert literature_evidence(
        QUESTION, [piece("O protocolo descreve as sessões de leitura.")]
    ) == []


def test_year_and_a_distant_number_are_not_the_answer():
    assert literature_evidence(QUESTION, [
        piece("Em 2025 o protocolo descreve as sessões publicadas."),
        piece("O protocolo descreve as sessões e foi citado 14 vezes."),
    ]) == []


def test_count_in_the_next_passage_does_not_rescue_the_current_one():
    current = piece("O protocolo descreve as sessões clínicas.")
    following = piece("O protocolo descreve doze sessões.")
    assert literature_evidence(QUESTION, [current]) == []
    assert literature_evidence(QUESTION, [current, following]) == [following]


def test_conceptual_question_does_not_need_a_number():
    kept = literature_evidence(
        "Quais limites éticos a psicoterapia apresenta?",
        [piece("A psicoterapia apresenta limites éticos no cuidado humano.")],
    )
    assert len(kept) == 1


def test_quantity_with_no_supporting_passage_abstains_at_the_gate():
    assert literature_evidence(
        "Quantas sessões de meditação o protocolo descreve?",
        [piece("O jardim tem flores amarelas e nenhum número.")],
    ) == []


def test_quantitative_answer_keeps_the_citation(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    with literature_test_scope():
        path = tmp_path / "nota.txt"
        path.write_text(
            "A nota fictícia registra 8 sessões de leitura clínica.\n\n"
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
        answer = service.answer("Quantas sessões de leitura a nota registra?", "extractive")
        assert answer.status == "ok"
        source = answer.sources[0]
        assert source.chunk_id.startswith("nota_local")
        assert "8 sessões" in source.quote
        assert source.url == "https://example.local/nota"
        assert "referencias" not in source.section
        missing = service.answer("Quantos autores a nota registra?", "extractive")
        assert missing.status == "insufficient_evidence"


def test_diary_quantity_question_stays_on_the_diary_gate(tmp_path):
    store = DiaryStore(tmp_path / "diarios.sqlite3")
    store.save(DiaryRecord(
        record_id="ana_99", patient_id="patient_ana",
        recorded_at=datetime(2026, 1, 1, tzinfo=UTC),
        original_text="O diário cita sessões de leitura na biblioteca sem dizer a quantidade.",
        source_title="Diário sintético",
    ))
    answer = CopilotService(store, Retriever()).answer(
        Query(patient_id="patient_ana", question="Quantas sessões de leitura aparecem na biblioteca?"),
        "extractive",
    )
    assert answer.status == "ok"
    assert answer.evidence[0].record_id == "ana_99"
