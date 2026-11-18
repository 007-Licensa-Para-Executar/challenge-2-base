import pytest

from privacy.detector import FixtureDetector, Span, build_detector


def test_detects_all_supported_entities_with_original_unicode_offsets():
    text = (
        "📓 Érica Sá chegou à Clínica Horizonte de Papel, em Vale Imaginário.\n"
        "CPF 123.456.789-00, celular +55 (11) 9 8765-4321, "
        "e-mail erica.teste+notas@clinica.invalid."
    )
    detector = FixtureDetector(
        {
            "érica sá": "PERSON",
            "Clínica Horizonte de Papel": "ORG",
            "Vale Imaginário": "LOCATION",
        }
    )
    expected = [
        ("Érica Sá", "PERSON"),
        ("Clínica Horizonte de Papel", "ORG"),
        ("Vale Imaginário", "LOCATION"),
        ("123.456.789-00", "CPF"),
        ("+55 (11) 9 8765-4321", "PHONE"),
        ("erica.teste+notas@clinica.invalid", "EMAIL"),
    ]

    assert detector.detect(text) == [
        Span(text.index(value), text.index(value) + len(value), kind) for value, kind in expected
    ]


@pytest.mark.parametrize(
    ("label", "identifier", "kind"),
    [
        ("CPF", "12345678900", "CPF"),
        ("CPF", "11987654321", "CPF"),
        ("Cadastro", "11900000083", "CPF"),
        ("Celular", "11987654321", "PHONE"),
        ("Celular", "+5511987654321", "PHONE"),
        ("Telefone", "(21) 2345-6789", "PHONE"),
        ("Telefone", "2345-6789", "PHONE"),
        ("E-mail", "equípe@serviço-exemplo.invalid", "EMAIL"),
    ],
)
def test_detects_common_identifier_variants(label, identifier, kind):
    prefix = f"{label}: "
    text = f"{prefix}{identifier}."
    assert FixtureDetector().detect(text) == [Span(len(prefix), len(text) - 1, kind)]


def test_resolves_overlaps_and_repeated_matches_deterministically():
    email = "12345678900@exemplo.invalid"
    full_name = "Nina Estrela de Papel"
    text = f"{full_name} escreveu para {email}. {full_name} confirmou."
    supplied_entities = {
        "Nina Estrela": "PERSON",
        full_name: "PERSON",
        "exemplo": "ORG",
    }
    expected = [
        Span(0, len(full_name), "PERSON"),
        Span(text.index(email), text.index(email) + len(email), "EMAIL"),
        Span(text.rindex(full_name), text.rindex(full_name) + len(full_name), "PERSON"),
    ]

    assert FixtureDetector(supplied_entities).detect(text) == expected
    assert FixtureDetector(dict(reversed(supplied_entities.items()))).detect(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "\n\t", "Hoje, 18/11/2026, dormi 8 horas.", "Ref: ABC12345678900XYZ e 00119876543210."],
)
def test_leaves_unrelated_text_without_matches(text):
    assert FixtureDetector().detect(text) == []


def test_missing_production_model_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError, match="local pt_core_news_lg model"):
        build_detector(tmp_path / "missing")
