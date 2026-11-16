"""Fluxo do menu integrado com serviços reais e processo controlado."""

from datetime import UTC, datetime

import pytest
from prompt_toolkit.document import Document

from app.contracts import Proposal
from app.processes import ProcessResult
from app.shell import CommandCompleter
from tests.test_shell import Scripted, shell


def test_rag_menu_is_completed_and_schema_is_closed():
    assert [c.text for c in CommandCompleter().get_completions(Document('/ra'), None)] == ['/rag']
    with pytest.raises(ValueError):
        Proposal.model_validate({'ferramenta': 'rag', 'argumentos': {'comando': 'whoami'}})


def test_training_requires_confirmation_and_uses_fixed_synthetic_module(tmp_path):
    instance, _, calls = shell(tmp_path, ['treinar', 'n'])
    instance.synthetic = True
    instance.handle('/rag')
    assert not calls
    instance.session = Scripted(['treinar', 's'])
    instance.handle('/rag')
    assert calls[0][0][:2] == ('app.research_demo', ['train'])


def test_preparation_cancelled_does_not_start_process(tmp_path):
    instance, _, calls = shell(tmp_path, ['preparar', 'nao', 'n'])
    instance.synthetic = True
    instance.handle('/rag')
    assert not calls
    assert not hasattr(instance, 'rag_db')


def test_missing_model_does_not_save_diaries(tmp_path, monkeypatch):
    monkeypatch.setattr('app.rag_shell.ROOT', tmp_path)
    instance, output, calls = shell(tmp_path, ['preparar', 'sim'])
    instance.synthetic = True
    instance.handle('/rag')
    assert not calls
    assert any('Artefatos ausentes' in line for line in output)
    assert not (tmp_path / 'data').exists()


def test_invalid_dates_or_patient_do_not_run(tmp_path):
    instance, _, calls = shell(tmp_path, ['perguntar', 'patient_ana', 'ontem', '', 'avós'])
    instance.synthetic = True
    with pytest.raises(ValueError):
        instance.handle('/rag')
    assert not calls


def test_literal_diary_sent_over_stdin_and_paths_with_spaces(tmp_path):
    instance, _, calls = shell(tmp_path, ['registrar', 'nao', 'patient_ana', '', '/sair'])
    instance.synthetic = True
    instance.rag_db = tmp_path / 'pasta com espaço' / 'diários.sqlite3'
    instance.session = Scripted(['registrar', 'nao', 'patient_ana', '', '/sair', 's'])
    instance.handle('/rag')
    args, kwargs = calls[0]
    assert args[0] == 'agents.copilot'
    assert args[1][:2] == ['ingest', '--synthetic']
    assert kwargs['text'] == '/sair'
    assert str(instance.rag_db) in args[1]
    assert instance.running


def test_query_shows_original_sources_and_passes_exact_scope(tmp_path):
    from agents.copilot.cli import main
    from agents.copilot.contracts import DiaryRecord
    from agents.copilot.storage import DiaryStore

    db = tmp_path / 'dados espaços' / 'memória.sqlite3'
    DiaryStore(db).save(DiaryRecord(
        record_id='ana_1', patient_id='patient_ana', recorded_at=datetime(2026, 11, 1, tzinfo=UTC),
        original_text='Hoje levei meus avós para comprar alimentos.',
    ))
    # Execute the real CLI through the shell's process boundary, using redirected streams.
    import contextlib
    import io

    def runner(module, arguments, settings, **kwargs):
        assert module == 'agents.copilot'
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(arguments)
        return ProcessResult(code, out.getvalue(), err.getvalue())

    instance, output, _ = shell(tmp_path, [
        'perguntar', 'patient_ana', '2026-11-01T00:00:00Z', '2026-11-02T00:00:00Z',
        'avós', 'extractive',
    ], runner=runner)
    instance.synthetic = True
    instance.rag_db = db
    instance.handle('/rag')
    assert any('ana_1:0:' in line and 'Hoje levei meus avós' in line for line in output)
    assert any('Estado: ok' in line for line in output)


def test_cancelled_query_never_invokes_tool(tmp_path):
    instance, _, calls = shell(tmp_path, ['perguntar', 'patient_ana', '', KeyboardInterrupt()])
    instance.synthetic = True
    with pytest.raises(KeyboardInterrupt):
        instance.handle('/rag')
    assert not calls


def test_rag_requires_synthetic_confirmation(tmp_path):
    instance, _, calls = shell(tmp_path, ['n'])
    instance.handle('/rag')
    assert not calls
