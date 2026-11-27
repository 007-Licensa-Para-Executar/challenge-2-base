import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agents.copilot import integration_cli as cli
from agents.copilot.contracts import DiaryRecord, Query, ThemePrediction
from agents.copilot.integration import IntegratedStore, StoredAnalysis, validate_analysis
from agents.extractor.contracts import Agent1Output


def test_wheel_chat_and_revision_share_exact_stored_evidence(tmp_path, monkeypatch):
    patient_id = str(uuid4())
    unrelated = str(uuid4())
    literal = "cuidei dos avós"
    treated = "🙂 Hoje cuidei dos avós."
    start = treated.index(literal)
    record = DiaryRecord(
        patient_id=patient_id, record_id="ref1", recorded_at=datetime.now(UTC),
        treated_text=treated, representation_id="rep1", detector_version="test",
        schema_version="2.0.0",
        classification=ThemePrediction(status="ok", primary_theme="familia", candidate_score=0.8),
    )
    output = Agent1Output(
        patient_id=patient_id, macro_tema_validado="familia", confianca_macro_tema=0.8,
        subtemas=[{
            "nome": "Avós", "descricao": "Cuidado com os avós",
            "evidencias": [{"quote_text": literal, "start_char": start,
                           "end_char": start + len(literal)}],
        }],
        sentimento_predominante="calma", score_polaridade=0.1,
        indicio_textual_risco="nao_identificado",
    )
    store = IntegratedStore(tmp_path / "analytics.sqlite3")
    store.save(record)
    store.publish(record, output)
    newer = output.model_copy(update={"entry_id": uuid4()})
    store.publish(record, newer)
    monkeypatch.setattr(cli, "map_patient", lambda alias, _directory: (
        patient_id if alias == "patient_ana" else unrelated
    ))
    monkeypatch.setattr(cli, "PrivacyClient", lambda *_: object())
    monkeypatch.setattr(cli, "protect_query", lambda query, *_: query)
    dash = cli.dispatch("dashboard", {"patient": "patient_ana"}, directory=tmp_path)
    assert dash["wheel"]["macrotemas"][0]["macro_tema"] == "vinculos"
    assert len(dash["entries"]) == 1
    json.dumps(dash, ensure_ascii=False)
    payload = {
        "patient": "patient_ana", "question": "Mostre o trecho", "topic": "Avós",
        "record_id": "ref1", "representation_id": "rep1", "entry_id": str(newer.entry_id),
        "start_char": start, "end_char": start + len(literal),
    }
    answer = cli.dispatch("chat", payload, directory=tmp_path)
    assert answer["evidence"][0]["quote"] == literal
    assert answer["evidence"][0]["entry_id"] == str(newer.entry_id)
    assert answer["evidence"][0]["representation_id"] == "rep1"
    assert cli.dispatch(
        "chat", {**payload, "patient": "patient_bruno"}, directory=tmp_path,
    )["status"] == "insufficient_evidence"
    assert cli.dispatch(
        "chat", {**payload, "representation_id": "stale"}, directory=tmp_path,
    )["status"] == "insufficient_evidence"
    assert cli.dispatch(
        "chat", {**payload, "entry_id": str(output.entry_id)}, directory=tmp_path,
    )["status"] == "insufficient_evidence"
    command = {"patient": "patient_ana", "question": "/reprocessar ref1"}
    assert cli.dispatch("chat", command, directory=tmp_path)["status"] == "confirmation"
    natural_reprocess = {**command, "question": "Reprocesse o diário ref1.", "confirmed": True}
    assert cli.dispatch("chat", natural_reprocess, directory=tmp_path)["status"] == "confirmation"
    natural_query = {**command, "question": "Nos diários, o que foi escrito sobre os avós?"}
    natural_result = cli.dispatch("chat", natural_query, directory=tmp_path)
    assert natural_result["status"] == "ok"
    assert natural_result["evidence"][0]["record_id"] == "ref1"
    outside = {**command, "question": "Consulte os diários do Bruno."}
    assert cli.dispatch("chat", outside, directory=tmp_path)["status"] == "clarification"
    replacement = output.model_copy(update={"entry_id": uuid4()})

    def extract(treated_record, _args, modalidade):
        assert treated_record.original_text is None
        assert treated_record.analysis_text == treated
        assert modalidade == "texto"
        return replacement

    monkeypatch.setattr(cli, "_extract_subtopics", extract)
    assert cli.dispatch(
        "chat", {**command, "confirmed": True}, directory=tmp_path,
    )["status"] == "ok"
    assert store.analyses(Query(patient_id=patient_id, question="listar"))[0][1].output == replacement
    assert store.analyses(Query(patient_id=patient_id, question="listar"))[0][1].version == "1.0.0"
    earlier = record.model_copy(update={
        "record_id": "ref0", "recorded_at": record.recorded_at - timedelta(days=8),
    })
    store.save(earlier)
    store.publish(earlier, output.model_copy(update={"entry_id": uuid4(), "score_polaridade": -0.6}))
    current = cli.dispatch("dashboard", {"patient": "patient_ana", "days": "7"}, directory=tmp_path)
    assert current["totalEntriesAllPeriods"] == 2
    assert [entry["id"] for entry in current["entries"]] == ["ref1"]
    assert "Avós" in current["longitudinal"]["subtemas_persistentes"]
    filtered = cli.dispatch(
        "dashboard", {"patient": "patient_ana", "valence": "negative"}, directory=tmp_path,
    )
    assert [entry["id"] for entry in filtered["entries"]] == ["ref0"]

    edited = cli.dispatch("presentation", {
        "patient": "patient_ana", "action": "annotate_subtopic",
        "macroTema": "vinculos", "originalName": "Avós", "displayName": "Família",
    }, directory=tmp_path)
    assert edited["annotations"][0]["display_name"] == "Família"
    assert edited["entries"][0]["agent1"]["subtemas"][0]["nome"] == "Avós"
    report = cli.dispatch("presentation", {
        "patient": "patient_ana", "action": "add_report", "fileName": "demo.txt",
        "fileSize": 42,
    }, directory=tmp_path)["reports"][0]
    cli.dispatch("presentation", {
        "patient": "patient_bruno", "action": "remove_report", "reportId": report["id"],
    }, directory=tmp_path)
    assert store.presentation(patient_id)["reports"] == [report]
    assert store.presentation(unrelated) == {"reports": [], "annotations": []}
    cli.dispatch("presentation", {
        "patient": "patient_ana", "action": "remove_report", "reportId": report["id"],
    }, directory=tmp_path)
    assert store.presentation(patient_id)["reports"] == []

    with pytest.raises(ValueError):
        validate_analysis(record, StoredAnalysis(
            record_id="ref1", representation_id="wrong", output=output,
        ))


def test_catalogue_lists_only_callable_slash_commands():
    assert cli._route("Conte os temas registrados neste período.") == "temas"
    commands = cli.dispatch("tools", {})["tools"]
    assert {item["command"] for item in commands} == {
        "/diarios", "/temas", "/literatura", "/reprocessar",
        "/ajuda", "/status", "/modelos", "/historico", "/limpar",
    }
    for item in commands:
        command = item["command"]
        assert item["description"]
        assert cli._route(command) == command.removeprefix("/")


@pytest.mark.parametrize(("text", "tool"), [
    ("Mostre os comandos.", "ajuda"),
    ("Como está o status do Ollama?", "status"),
    ("Quais modelos locais estão instalados?", "modelos"),
    ("Mostre o histórico deste paciente.", "historico"),
    ("Mostre a contagem por tema neste período.", "temas"),
    ("Busque nos diários sobre os avós.", "diarios"),
    ("Nos diários, o que foi escrito sobre os avós?", "diarios"),
    ("Procure artigos sobre agentes conversacionais.", "literatura"),
    ("Reprocesse o diário ana_07.", "reprocessar"),
    ("Limpe a conversa e abra o histórico.", "esclarecer"),
])
def test_common_natural_commands_are_resolved_without_a_model(text, tool, monkeypatch):
    def unexpected_model_call(**_kwargs):
        pytest.fail("Comando conhecido deve funcionar com o roteador indisponível")

    monkeypatch.setattr(cli, "Client", unexpected_model_call)
    assert cli._route(text) == tool
