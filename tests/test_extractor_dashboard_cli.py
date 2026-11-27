"""Testes unitários e de integração da CLI de dashboard (Rede Neural + Agente 1 + RAG)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import joblib
import pytest
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

import agents.extractor.dashboard_cli as cli
from models.torch_mlp import ClinicalThemeMLP

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_model(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    vectorizer = TfidfVectorizer().fit(["familia prova trabalho insônia"])
    model = ClinicalThemeMLP(input_dim=len(vectorizer.vocabulary_))
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
        model.fc3.bias[0] = 10
    torch.save(model.state_dict(), dist / "best_theme_mlp.pt")
    joblib.dump(vectorizer, dist / "theme_embedder.joblib")
    monkeypatch.chdir(tmp_path)
    pythonpath = os.environ.get("PYTHONPATH")
    monkeypatch.setenv("PYTHONPATH", str(ROOT) + (os.pathsep + pythonpath if pythonpath else ""))



def test_analyze_batch_extracts_neural_themes_and_agent1_subtopics():
    payload = {
        "patient_id": "paciente-teste-1",
        "periodo": "Últimos 14 dias",
        "use_ollama": False,
        "entries": [
            {
                "id": "entry-1",
                "text": "Estou muito feliz com minha família e recebi apoio em casa.",
                "created_at": 1795036547805,
                "input_type": "text",
                "primary_emotion": "alegria",
                "is_risk_emotion": False,
            },
            {
                "id": "entry-2",
                "text": "Hoje vou ter prova na faculdade, que dia péssimo de cansaço.",
                "created_at": 1795036567074,
                "input_type": "text",
                "primary_emotion": "medo",
                "is_risk_emotion": True,
            },
            {
                "id": "entry-3",
                "text": "Não aguento mais sobrecarga de prazo no trabalho, estou exausto.",
                "created_at": 1795036601013,
                "input_type": "audio",
                "primary_emotion": "raiva",
                "is_risk_emotion": True,
            },
        ],
    }

    res = cli._analyze_batch(payload)
    analyzed = res["analyzed_entries"]
    assert len(analyzed) == 3

    for item in analyzed:
        assert item["macro_tema"]
        assert 0.0 <= item["macro_confidence"] <= 1.0
        assert -1.0 <= item["polarity_score"] <= 1.0
        subtemas = item["agent1"]["subtemas"]
        assert 1 <= len(subtemas) <= 3
        for sub in subtemas:
            assert sub["evidencias"]
            ev = sub["evidencias"][0]
            assert ev["start_char"] < ev["end_char"]

    wheel = res["wheel"]
    assert wheel["patient_id"] == "paciente-teste-1"
    assert wheel["total_subtemas_ativos"] >= 1
    assert wheel["total_subtemas_ativos"] <= 24
    populated = [m for m in wheel["macrotemas"] if m["subtemas"]]
    assert populated, "Ao menos um macro-tema deve conter subtemas extraídos"


def test_build_wheel_and_rag_query_extractive():
    batch = cli._analyze_batch(
        {
            "patient_id": "pac-2",
            "use_ollama": False,
            "entries": [
                {
                    "id": "a1",
                    "text": "Insônia forte a madrugada toda e aperto no peito antes da reunião.",
                    "created_at": "2026-11-15T10:00:00+00:00",
                    "primary_emotion": "ansiedade",
                    "is_risk_emotion": True,
                },
                {
                    "id": "a2",
                    "text": "Dia tranquilo caminhando no parque com minha família.",
                    "created_at": "2026-11-20T14:00:00+00:00",
                    "primary_emotion": "alegria",
                    "is_risk_emotion": False,
                },
            ],
        }
    )
    outputs = [x["agent1"] for x in batch["analyzed_entries"]]
    wheel_res = cli._build_wheel(
        {
            "patient_id": "pac-2",
            "current_outputs": outputs,
            "previous_outputs": [outputs[0]],
            "periodo": "Semana atual",
            "previous_label": "Semana anterior",
        }
    )
    assert wheel_res["wheel"]["total_subtemas_ativos"] >= 1
    assert "subtemas_emergentes" in wheel_res["longitudinal"]
    assert "subtemas_persistentes" in wheel_res["longitudinal"]

    rag_res = cli._rag_query(
        {
            "patient_id": "pac-2",
            "question": "Quando houve insônia e aperto no peito?",
            "generation_mode": "extractive",
            "entries": [
                {
                    "id": "a1",
                    "text": "Insônia forte a madrugada toda e aperto no peito antes da reunião.",
                    "created_at": "2026-11-15T10:00:00+00:00",
                    "macro_tema": batch["analyzed_entries"][0]["macro_tema"],
                    "input_type": "text",
                },
                {
                    "id": "a2",
                    "text": "Dia tranquilo caminhando no parque com minha família.",
                    "created_at": "2026-11-20T14:00:00+00:00",
                    "macro_tema": batch["analyzed_entries"][1]["macro_tema"],
                    "input_type": "text",
                },
            ],
        }
    )
    assert rag_res["status"] == "ok"
    assert rag_res["evidence"]
    assert "insônia" in rag_res["evidence"][0]["quote"].lower()


def test_cli_subprocess_json_roundtrip():
    proc = subprocess.run(
        [sys.executable, "-m", "agents.extractor.dashboard_cli", "analyze-batch"],
        input=json.dumps(
            {
                "patient_id": "p-sub",
                "entries": [
                    {
                        "id": "e-sub-1",
                        "text": "Estou ansioso com a prova e sem conseguir dormir.",
                        "created_at": 1795036567074,
                        "primary_emotion": "medo",
                        "is_risk_emotion": True,
                    }
                ],
            }
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["wheel"]["total_subtemas_ativos"] >= 1
    assert data["analyzed_entries"][0]["agent1"]["subtemas"]

    proc2 = subprocess.run(
        [sys.executable, "-m", "agents.extractor.dashboard_cli", "build-wheel"],
        input=json.dumps(
            {
                "patient_id": "p-sub",
                "current_outputs": [data["analyzed_entries"][0]["agent1"]],
                "previous_outputs": [],
            }
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc2.returncode == 0, proc2.stderr
    built = json.loads(proc2.stdout)
    assert built["wheel"]["total_subtemas_ativos"] >= 1
