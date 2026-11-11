"""Smoke offline do shell → subprocesso → SQLite → RAG, também no CMD nativo."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agents.extractor.config import Settings
from app.shell import Shell
from tests.test_shell import Scripted


def smoke():
    with TemporaryDirectory(prefix='rag diário ') as folder:
        output = []
        session = Scripted([
            's', '/rag', 'preparar', 'nao', 's',
            '/rag', 'perguntar', 'patient_ana', '', '',
            'Quais cuidados dos avós foram descritos?', 'extractive', '/sair',
        ])
        with patch('app.rag_shell.ROOT', Path(folder)):
            instance = Shell(Settings(), session=session, write=output.append)
            assert instance.run() == 0
        assert any('"saved": 20' in line for line in output)
        assert any('Estado: ok' in line for line in output)
        assert any('ana_03:0:' in line for line in output)
        assert instance.rag_db.is_file()
    print('RAG shell smoke OK: formulário → subprocesso → SQLite → pergunta → fontes')


if __name__ == '__main__':
    smoke()
