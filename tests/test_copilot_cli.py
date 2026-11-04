"""Testes unitários para a CLI do Agente 2."""

import json
from pathlib import Path

from agents.copilot.cli import main


def test_copilot_cli_requires_synthetic():
    exit_code = main([])
    assert exit_code == 2


def test_copilot_cli_with_file_mock(tmp_path: Path, capsys):
    input_file = tmp_path / "extractions.jsonl"
    input_file.write_text(
        json.dumps({"tema": "estudos", "sentimento": "frustracao", "indicio_textual_risco": "nao_identificado"}) + "\n" +
        json.dumps({"tema": "estudos", "sentimento": "preocupacao", "indicio_textual_risco": "nao_identificado"}),
        encoding="utf-8",
    )

    output_json = tmp_path / "dossier.json"
    report_md = tmp_path / "relatorio.md"

    exit_code = main([
        "--synthetic",
        "--mock",
        "--file", str(input_file),
        "--output", str(output_json),
        "--report-md", str(report_md),
    ])

    assert exit_code == 0
    assert output_json.exists()
    assert report_md.exists()

    data = json.loads(output_json.read_text(encoding="utf-8"))
    assert data["status"] == "ok"
    assert data["dossier"]["stats"]["tema_dominante"] == "estudos"

    md_text = report_md.read_text(encoding="utf-8")
    assert "Dossiê Longitudinal do Paciente" in md_text


def test_copilot_cli_no_data_fails(tmp_path: Path):
    empty_db = tmp_path / "empty.sqlite3"
    exit_code = main([
        "--synthetic",
        "--mock",
        "--db", str(empty_db),
    ])
    assert exit_code == 2
