"""Testes unitários para o gerador sintético de personas e divisão estratificada."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from data.split import stratified_split_dataset
from data.synthetic_generator import (
    ALL_THEMES_WITH_FALLBACK,
    CLINICAL_THEMES,
    DEFAULT_PERSONAS,
    generate_single_report_offline,
    generate_single_report_ollama,
    generate_synthetic_dataset,
    load_personas,
)


def test_personas_definitions():
    """Valida o esquema e conteúdo das 4 personas centrais."""
    personas = load_personas()
    assert len(personas) >= 4

    expected_ids = {
        "persona_universitario",
        "persona_cuidador",
        "persona_burnout",
        "persona_luto",
    }
    loaded_ids = {p["id"] for p in personas}
    assert expected_ids.issubset(loaded_ids)

    for p in personas:
        assert "id" in p
        assert "nome" in p
        assert "tracos" in p
        assert "temas_frequentes" in p
        assert "estilo_linguagem" in p
        assert isinstance(p["temas_frequentes"], list)


def test_personas_json_file_validity():
    """Valida integridade do arquivo data/personas.json no disco."""
    json_path = Path("data/personas.json")
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 4


def test_offline_report_generation():
    """Verifica que o gerador offline produz textos não-vazios para todos os temas."""
    personas = load_personas()
    for persona in personas:
        for theme in CLINICAL_THEMES:
            report = generate_single_report_offline(persona, theme)
            assert isinstance(report, str)
            assert len(report.strip()) > 30

    # Teste para salvaguarda outros_indeterminado
    safeguard_report = generate_single_report_offline(personas[0], "outros_indeterminado")
    assert isinstance(safeguard_report, str)
    assert len(safeguard_report.strip()) > 10


def test_generate_synthetic_dataset_in_memory(tmp_path):
    """Verifica a geração completa de um dataset sintético balanceado."""
    out_file = tmp_path / "test_synthetic.json"
    dataset = generate_synthetic_dataset(
        output_path=str(out_file),
        samples_per_theme=3,
        include_safeguard=True,
        use_ollama=False,
        seed=123,
    )

    expected_total = len(ALL_THEMES_WITH_FALLBACK) * 3
    assert len(dataset) == expected_total
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert len(saved_data) == expected_total

    # Verifica integridade dos campos
    for rec in saved_data:
        assert "id" in rec
        assert "persona_id" in rec
        assert "macro_tema" in rec
        assert "texto" in rec
        assert rec["modalidade"] == "texto"
        assert rec["macro_tema"] in ALL_THEMES_WITH_FALLBACK


def test_stratified_split_dataset():
    """Verifica a divisão estratificada 70% Treino, 15% Validação, 15% Holdout."""
    records = []
    # 9 temas x 20 amostras = 180 registros
    for theme in ALL_THEMES_WITH_FALLBACK:
        for i in range(20):
            records.append(
                {
                    "id": f"{theme}_{i}",
                    "macro_tema": theme,
                    "texto": f"Exemplo de relato sobre {theme} número {i}",
                }
            )

    train, val, test = stratified_split_dataset(
        records,
        train_size=0.70,
        val_size=0.15,
        test_size=0.15,
        random_state=42,
    )

    assert len(train) == round(180 * 0.70)
    assert len(val) == round(180 * 0.15)
    assert len(test) == round(180 * 0.15)
    assert len(train) + len(val) + len(test) == 180

    # Verifica estratificação: todas as classes devem estar presentes em cada partição
    train_themes = {r["macro_tema"] for r in train}
    val_themes = {r["macro_tema"] for r in val}
    test_themes = {r["macro_tema"] for r in test}

    assert train_themes == set(ALL_THEMES_WITH_FALLBACK)
    assert val_themes == set(ALL_THEMES_WITH_FALLBACK)
    assert test_themes == set(ALL_THEMES_WITH_FALLBACK)


def test_ollama_generation_mock():
    """Valida chamada ao Ollama com resposta simulada."""
    persona = DEFAULT_PERSONAS[0]

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": "Desabafo simulado via Ollama LLM com alta fidelidade."}
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp):
        text = generate_single_report_ollama(persona, "estudos")
        assert "Desabafo simulado via Ollama" in text
