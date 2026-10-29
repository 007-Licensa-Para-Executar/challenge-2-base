"""Smoke offline usando PipeInput nativo (Win32 no CMD do CI)."""

from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from agents.extractor.config import Settings
from app.processes import ProcessResult
from app.shell import Shell, bindings


def smoke():
    output = []
    with create_pipe_input() as pipe:
        session = PromptSession(input=pipe, output=DummyOutput(), key_bindings=bindings())
        shell = Shell(Settings(host="http://127.0.0.1:1"), session=session, write=output.append,
                      runner=lambda *a, **k: ProcessResult(
                          0, '{"ferramenta":"ajuda","argumentos":{}}', ""))
        # Inclui pedido -> proposta -> confirmação -> ferramenta, sem modelo ou rede.
        pipe.send_text("s\nmostrar comandos\ns\n/sair\n")
        assert shell.run() == 0
    assert any("Proposta:" in line for line in output)
    assert any("/extrair:" in line for line in output)
    print("Shell smoke OK: pedido -> proposta -> confirmação -> ajuda -> saída")


if __name__ == "__main__":
    smoke()
