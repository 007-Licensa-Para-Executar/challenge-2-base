"""Menu /copiloto sobre o serviço de diários sintéticos, com bancos temporários."""

import json
from pathlib import Path

from prompt_toolkit.document import Document

from agents.copilot.cli import main
from app.router import request_intents
from app.shell import CommandCompleter
from tests.test_shell import shell


def test_copilot_command_is_in_the_menu(tmp_path):
    completer = CommandCompleter()
    assert [item.text for item in completer.get_completions(Document("/cop"), None)] == ["/copiloto"]
    instance, output, calls = shell(tmp_path, ["/sair"])
    instance.synthetic = True
    instance.handle("/ajuda")
    assert any("/copiloto:" in line for line in output)
    assert any("/extrair:" in line for line in output)
    assert not calls
    assert instance.running
    assert request_intents("abrir o copiloto de diarios sinteticos") == {"copiloto"}
    assert request_intents("Consultar o histórico local") == {"historico"}


def test_copilot_entry_exit_isolation_and_known_questions(tmp_path):
    diary_db = tmp_path / "diarios.sqlite3"
    extraction = Path(shell(tmp_path)[0].settings.db_path)
    extraction.parent.mkdir(parents=True)
    extraction.write_bytes(b"banco-de-extracoes")
    instance, output, calls = shell(tmp_path, [
        "diarios", "extrativo", "n",
        "diarios", "extrativo", "s", "voltar",
        "diarios", "extrativo", "s", "patient_ana", "Quais cuidados dos avós foram descritos?", "voltar",
        "diarios", "extrativo", "s", "patient_bruno", "Qual é a senha do cartão bancário?", "voltar",
    ])
    instance.synthetic = True
    instance.copilot_db = diary_db
    instance.handle("/copiloto")
    assert not diary_db.exists()
    instance.handle("/copiloto")
    assert diary_db.exists()
    instance.handle("/copiloto")
    instance.handle("/copiloto")
    text = "\n".join(output)
    assert "Não foram encontrados trechos suficientes para responder." in text
    assert "cartão-postal" not in text
    origins = [line for line in output if line.startswith("Origem ")]
    assert origins
    assert all(line.startswith("Origem patient_ana | ana_") for line in origins)
    assert all(record in text for record in ("ana_01", "ana_03", "ana_05"))
    assert extraction.read_bytes() == b"banco-de-extracoes"
    assert not calls
    assert instance.running


def test_copilot_failure_returns_to_the_menu(tmp_path, monkeypatch):
    def fail(self, *args, **kwargs):
        raise RuntimeError("segredo interno")

    monkeypatch.setattr("app.shell.CopilotService.answer", fail)
    instance, output, _calls = shell(
        tmp_path, ["diarios", "extrativo", "s", "patient_ana", "avós", "voltar", "/ajuda"],
    )
    instance.synthetic = True
    instance.copilot_db = tmp_path / "diarios.sqlite3"
    instance.handle("/copiloto")
    instance.handle("/ajuda")
    assert instance.running
    assert any("Consulta não concluída" in line for line in output)
    assert any("/extrair:" in line for line in output)
    assert not any("segredo" in line for line in output)


def test_ollama_mode_reports_unavailable_service_and_stays_open(tmp_path, monkeypatch):
    from agents.copilot.contracts import CopilotAnswer

    monkeypatch.setattr(
        "app.shell.Shell.models", lambda self: [{"name": "qwen3:4b"}],
    )

    def answer(self, query, generation_mode="ollama", top_k=3):
        assert generation_mode == "ollama"
        return CopilotAnswer(
            status="error",
            patient_id=query.patient_id,
            question=query.question,
            answer="Falha operacional; nenhuma síntese foi gerada.",
            generation_mode="ollama",
            retriever="bm25",
            error_code="generation_timeout",
        )

    monkeypatch.setattr("app.shell.CopilotService.answer", answer)
    instance, output, _calls = shell(
        tmp_path, ["diarios", "ollama", "s", "patient_ana", "avós", "voltar"],
    )
    instance.synthetic = True
    instance.copilot_db = tmp_path / "diarios.sqlite3"
    instance.handle("/copiloto")
    instance.handle("/ajuda")
    assert instance.running
    assert any("tempo limite" in line for line in output)
    assert any("/extrair:" in line for line in output)


def test_missing_ollama_model_returns_to_the_menu(tmp_path, monkeypatch):
    monkeypatch.setattr("app.shell.Shell.models", lambda self: [{"name": "outro"}])
    instance, output, _calls = shell(tmp_path, ["diarios", "ollama", "s", "/ajuda"])
    instance.synthetic = True
    instance.copilot_db = tmp_path / "diarios.sqlite3"
    instance.handle("/copiloto")
    assert instance.running
    assert any("não está instalado" in line for line in output)
    assert not (tmp_path / "diarios.sqlite3").exists()


def test_standalone_cli_still_answers_from_its_own_database(tmp_path, capsys):
    db = tmp_path / "cli.sqlite3"
    assert main(["seed", "--synthetic", "--db", str(db)]) == 0
    assert json.loads(capsys.readouterr().out)["saved"] == 20
    assert main([
        "ask", "Quais cuidados dos avós foram descritos?",
        "--patient-id", "patient_ana", "--generation", "extractive", "--db", str(db),
    ]) == 0
    answer = json.loads(capsys.readouterr().out)
    assert answer["status"] == "ok"
    assert {item["record_id"] for item in answer["evidence"]} == {"ana_01", "ana_03", "ana_05"}
