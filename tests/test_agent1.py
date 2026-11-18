"""Testes unitários para o Agente 1 (Decompositor Temático e Extrator de Evidências)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.extractor.contracts import Agent1Output, IndicioRisco, MacroTema, Sentimento
from agents.extractor.service import Agent1Service

SAMPLE_TEXT = (
    "Ontem meu irmão pegou meu carro sem pedir de novo e ainda riu de mim. "
    "Fiquei com uma raiva insuportável."
)


def test_agent1_successful_parsing():
    """Valida o fluxo básico de decomposição de subtemas e extração de evidências."""
    mock_response = {
        "subtemas": [
            {
                "nome": "Irmão",
                "descricao": "Conflito por apropriação indevida do veículo e deboche",
                "evidencias": [
                    {
                        "quote_text": "meu irmão pegou meu carro sem pedir de novo e ainda riu de mim",
                        "start_char": 6,
                        "end_char": 68,
                    }
                ],
            }
        ],
        "sentimento_predominante": "raiva",
        "score_polaridade": -0.82,
        "indicio_textual_risco": "nao_identificado",
    }

    service = Agent1Service()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        mock_post.return_value.raise_for_status = MagicMock()

        res = service.process(
            patient_id="PAC-123",
            text=SAMPLE_TEXT,
            macro_tema="familia",
            confidence=0.92,
        )

        assert res.macro_tema_validado == MacroTema.FAMILIA
        assert res.macro_tema_validado == "familia"
        assert len(res.subtemas) == 1
        assert res.subtemas[0].nome == "Irmão"
        assert res.sentimento_predominante == Sentimento.RAIVA
        assert res.sentimento_predominante == "raiva"
        assert res.score_polaridade == -0.82
        assert res.indicio_textual_risco == IndicioRisco.NAO_IDENTIFICADO

        # Validação do span
        ev = res.subtemas[0].evidencias[0]
        assert SAMPLE_TEXT[ev.start_char : ev.end_char] == ev.quote_text


def test_agent1_span_alignment_auto_fix():
    """Valida que o alinhador conserta offsets incorretos enviados pelo LLM."""
    mock_response = {
        "subtemas": [
            {
                "nome": "Raiva Reprimida",
                "descricao": "Sentimento agudo de ira decorrente da situação",
                "evidencias": [
                    {
                        # LLM mandou start_char=0 incorreto
                        "quote_text": "raiva insuportável",
                        "start_char": 0,
                        "end_char": 0,
                    }
                ],
            }
        ],
        "sentimento_predominante": "raiva",
        "score_polaridade": -0.75,
        "indicio_textual_risco": "nao_identificado",
    }

    service = Agent1Service()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        mock_post.return_value.raise_for_status = MagicMock()

        res = service.process(
            patient_id="PAC-123",
            text=SAMPLE_TEXT,
            macro_tema="familia",
            confidence=0.88,
        )

        ev = res.subtemas[0].evidencias[0]
        # O offset foi corrigido automaticamente
        assert ev.start_char > 0
        assert SAMPLE_TEXT[ev.start_char : ev.end_char] == "raiva insuportável"


def test_agent1_audio_segments_alignment():
    """Valida associação de carimbos de áudio de transcrição com as evidências literais."""
    audio_segments = [
        {"start": 0.0, "end": 4.5, "text": "Ontem meu irmão pegou meu carro sem pedir de novo"},
        {"start": 4.6, "end": 7.8, "text": "e ainda riu de mim. Fiquei com uma raiva insuportável."},
    ]

    mock_response = {
        "subtemas": [
            {
                "nome": "Conflito Fraterno",
                "descricao": "Desrespeito material pelo irmão",
                "evidencias": [
                    {
                        "quote_text": "meu irmão pegou meu carro",
                        "start_char": 6,
                        "end_char": 31,
                    }
                ],
            }
        ],
        "sentimento_predominante": "raiva",
        "score_polaridade": -0.6,
        "indicio_textual_risco": "nao_identificado",
    }

    service = Agent1Service()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        mock_post.return_value.raise_for_status = MagicMock()

        res = service.process(
            patient_id="PAC-AUDIO",
            text=SAMPLE_TEXT,
            macro_tema="familia",
            confidence=0.95,
            modalidade="audio",
            audio_segments=audio_segments,
        )

        ev = res.subtemas[0].evidencias[0]
        assert ev.audio_start_sec == 0.0
        assert ev.audio_end_sec == 4.5


def test_agent1_hallucinated_quote_raises_error():
    """Valida que citações totalmente inventadas pelo modelo causam falha com erro sanitizado."""
    mock_response = {
        "subtemas": [
            {
                "nome": "Alucinação",
                "descricao": "Trecho inexistente no relato",
                "evidencias": [
                    {
                        "quote_text": "meu chefe me despediu ontem na empresa",
                        "start_char": 0,
                        "end_char": 30,
                    }
                ],
            }
        ],
        "sentimento_predominante": "tristeza",
        "score_polaridade": -0.5,
        "indicio_textual_risco": "nao_identificado",
    }

    service = Agent1Service()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        mock_post.return_value.raise_for_status = MagicMock()

        with pytest.raises(ValueError, match="não foi localizada no texto primário"):
            service.process(
                patient_id="PAC-123",
                text=SAMPLE_TEXT,
                macro_tema="familia",
                confidence=0.90,
            )


def test_agent1_to_clinical_summary():
    """Valida formatação do relatório clínico para auditoria rápida do psicólogo."""
    mock_output = Agent1Output(
        patient_id="PAC-TESTE",
        macro_tema_validado=MacroTema.TRABALHO,
        confianca_macro_tema=0.91,
        subtemas=[
            {
                "nome": "Sobrecarga de Metas",
                "descricao": "Exigências irrealistas impostas pela chefia",
                "evidencias": [
                    {
                        "quote_text": "não aguento mais as cobranças",
                        "start_char": 0,
                        "end_char": 29,
                        "audio_start_sec": 1.2,
                        "audio_end_sec": 3.8,
                    }
                ],
            }
        ],
        sentimento_predominante=Sentimento.FRUSTRACAO,
        score_polaridade=-0.75,
        indicio_textual_risco=IndicioRisco.PRESENTE,
        modalidade="audio",
    )

    summary = Agent1Service.to_clinical_summary(mock_output)
    assert "PAC-TESTE" in summary
    assert "trabalho" in summary
    assert "Sobrecarga de Metas" in summary
    assert "ALERTA CLÍNICO PRIORITÁRIO" in summary
    assert "1.2s - 3.8s" in summary


def test_agent1_with_neural_network_integration():
    """Valida o método ponta a ponta integrando o preditor da Rede Neural com o Agente 1."""
    mock_predictor = MagicMock()
    mock_predictor.predict_text.return_value = MagicMock(
        primary_theme="trabalho",
        confidence=0.89,
    )

    mock_llm_response = {
        "subtemas": [
            {
                "nome": "Chefe Exigente",
                "descricao": "Pressão exercida pelo superior hierárquico",
                "evidencias": [
                    {
                        "quote_text": "meu chefe me cobrou",
                        "start_char": 0,
                        "end_char": 19,
                    }
                ],
            }
        ],
        "sentimento_predominante": "preocupacao",
        "score_polaridade": -0.65,
        "indicio_textual_risco": "nao_identificado",
    }

    service = Agent1Service()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {
            "message": {"content": json.dumps(mock_llm_response)}
        }
        mock_post.return_value.raise_for_status = MagicMock()

        text = "Hoje meu chefe me cobrou resultados impossíveis na reunião."
        res = service.process_with_neural_network(
            patient_id="PAC-NN-001",
            text=text,
            predictor=mock_predictor,
        )

        assert res.macro_tema_validado == MacroTema.TRABALHO
        assert res.confianca_macro_tema == 0.89
        assert res.subtemas[0].nome == "Chefe Exigente"
        mock_predictor.predict_text.assert_called_once_with(text)


def test_wheel_builder_respects_max_24_subtopics():
    """Valida o teto de 24 subtemas no total e a alocação dinâmica flexível por tema."""
    service = Agent1Service()
    entries = []

    # Cria 30 subtemas sintéticos espalhados pelos macrotemas
    # Concentrando mais em 'trabalho' (10 subtemas) e 'familia' (8 subtemas)
    for i in range(10):
        entries.append(
            Agent1Output(
                patient_id="PAC-WHEEL",
                macro_tema_validado=MacroTema.TRABALHO,
                confianca_macro_tema=0.9,
                subtemas=[
                    {
                        "nome": f"Subtema Trabalho {i}",
                        "descricao": "Contexto",
                        "evidencias": [{"quote_text": "teste", "start_char": 0, "end_char": 5}],
                    }
                ],
                sentimento_predominante=Sentimento.FRUSTRACAO,
                score_polaridade=-0.5,
                indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
            )
        )

    for i in range(8):
        entries.append(
            Agent1Output(
                patient_id="PAC-WHEEL",
                macro_tema_validado=MacroTema.FAMILIA,
                confianca_macro_tema=0.9,
                subtemas=[
                    {
                        "nome": f"Subtema Família {i}",
                        "descricao": "Contexto",
                        "evidencias": [{"quote_text": "teste", "start_char": 0, "end_char": 5}],
                    }
                ],
                sentimento_predominante=Sentimento.TRISTEZA,
                score_polaridade=-0.4,
                indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
            )
        )

    for i in range(12):
        entries.append(
            Agent1Output(
                patient_id="PAC-WHEEL",
                macro_tema_validado=MacroTema.ESTUDOS,
                confianca_macro_tema=0.8,
                subtemas=[
                    {
                        "nome": f"Subtema Estudos {i}",
                        "descricao": "Contexto",
                        "evidencias": [{"quote_text": "teste", "start_char": 0, "end_char": 5}],
                    }
                ],
                sentimento_predominante=Sentimento.PREOCUPACAO,
                score_polaridade=-0.3,
                indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
            )
        )

    # Total de 30 subtemas únicos gerados
    wheel = service.build_wheel_data(entries, patient_id="PAC-WHEEL", max_subtemas=24)

    # O teto de 24 deve ser respeitado rigorosamente
    assert wheel.total_subtemas_ativos <= 24
    assert wheel.total_subtemas_ativos == 24

    # Verifica que não são necessariamente 3 por macrotema (distribuição flexível)
    macro_counts = {m.macro_tema: len(m.subtemas) for m in wheel.macrotemas}
    assert macro_counts["trabalho"] > 3
    assert macro_counts["luto"] == 0  # Nenhum subtema gerado para luto

    # Valida estrutura hierárquica Sunburst (raízes e pais)
    assert "root" in wheel.ids
    assert "macro_trabalho" in wheel.ids
    trabalho_idx = wheel.ids.index("macro_trabalho")
    assert wheel.parents[trabalho_idx] == "root"


def test_longitudinal_rotation_comparison():
    """Valida a rotação semanal/mensal de subtemas: persistentes, novos e rotacionados."""
    service = Agent1Service()

    # Semana 1: Paciente fala sobre 'Chefe' e 'Insônia'
    week1_entries = [
        Agent1Output(
            patient_id="PAC-LONG",
            macro_tema_validado=MacroTema.TRABALHO,
            confianca_macro_tema=0.9,
            subtemas=[
                {
                    "nome": "Conflito com Chefe",
                    "descricao": "Atrito na chefia",
                    "evidencias": [{"quote_text": "chefe", "start_char": 0, "end_char": 5}],
                }
            ],
            sentimento_predominante=Sentimento.RAIVA,
            score_polaridade=-0.8,
            indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
        ),
        Agent1Output(
            patient_id="PAC-LONG",
            macro_tema_validado=MacroTema.SAUDE_SONO,
            confianca_macro_tema=0.85,
            subtemas=[
                {
                    "nome": "Insônia Inicial",
                    "descricao": "Dificuldade para dormir",
                    "evidencias": [{"quote_text": "sono", "start_char": 0, "end_char": 4}],
                }
            ],
            sentimento_predominante=Sentimento.PREOCUPACAO,
            score_polaridade=-0.5,
            indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
        ),
    ]

    # Semana 2: Paciente parou de falar de 'Chefe', continua com 'Insônia', e começou 'Entrevista'
    week2_entries = [
        Agent1Output(
            patient_id="PAC-LONG",
            macro_tema_validado=MacroTema.SAUDE_SONO,
            confianca_macro_tema=0.85,
            subtemas=[
                {
                    "nome": "Insônia Inicial",
                    "descricao": "Dificuldade para dormir",
                    "evidencias": [{"quote_text": "sono", "start_char": 0, "end_char": 4}],
                }
            ],
            sentimento_predominante=Sentimento.CALMA,
            score_polaridade=0.1,  # Melhorou a polaridade
            indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
        ),
        Agent1Output(
            patient_id="PAC-LONG",
            macro_tema_validado=MacroTema.TRABALHO,
            confianca_macro_tema=0.88,
            subtemas=[
                {
                    "nome": "Entrevista de Emprego",
                    "descricao": "Processo seletivo",
                    "evidencias": [{"quote_text": "vaga", "start_char": 0, "end_char": 4}],
                }
            ],
            sentimento_predominante=Sentimento.ALEGRIA,
            score_polaridade=0.6,
            indicio_textual_risco=IndicioRisco.NAO_IDENTIFICADO,
        ),
    ]

    comp = service.compare_history(
        current_entries=week2_entries,
        previous_entries=week1_entries,
        patient_id="PAC-LONG",
        current_label="Semana 2",
        previous_label="Semana 1",
    )

    # Persistente: 'Insônia Inicial' esteve nas duas semanas
    assert comp.subtemas_persistentes == ["Insônia Inicial"]
    # Emergente: 'Entrevista de Emprego' surgiu na semana 2
    assert comp.subtemas_emergentes == ["Entrevista de Emprego"]
    # Rotacionado: 'Conflito com Chefe' deixou de ser falado
    assert comp.subtemas_rotacionados == ["Conflito com Chefe"]
    # A polaridade de 'Insônia Inicial' evoluiu positivamente (+0.6 delta)
    assert comp.evolucao_polaridade["Insônia Inicial"] > 0
    assert "Semana 2 vs. Semana 1" in comp.resumo_clinico_rotacao

