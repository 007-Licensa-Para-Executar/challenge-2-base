"""Menu de desenvolvimento para dados sintéticos; preferências apenas em memória."""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, DynamicCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import ColorDepth

from agents.extractor.config import Settings
from agents.extractor.contracts import MAX_INPUT_BYTES, ProcessingResult
from app.contracts import COMMANDS, Arguments, Proposal
from app.history import read_history
from app.processes import ROOT, run_module
from app.rag_shell import RagMenu
from app.router import installed_models


def safe_text(value: object) -> str:
    # Remove controles de terminal de textos não confiáveis, incluindo OSC e ANSI.
    text = re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", "", str(value))
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    return "".join(c for c in text if c in "\n\t" or (c.isprintable() and c != "\x1b"))


class CommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/") or any(c.isspace() for c in text):
            return
        for command, description in COMMANDS.items():
            if ("/" + command).startswith(text):
                yield Completion("/" + command, start_position=-len(text), display_meta=description)


def active_completer(buffer):
    completer = buffer.completer
    return completer.get_completer() if isinstance(completer, DynamicCompleter) else completer


def bindings():
    keys = KeyBindings()

    @keys.add("/")
    def slash(event):
        buffer = event.current_buffer
        initial = not buffer.text and isinstance(active_completer(buffer), CommandCompleter)
        # A abertura explícita deve ser a única tarefa de completamento inicial.
        buffer.insert_text("/", fire_event=not initial)
        if initial:
            buffer.start_completion(select_first=True)

    @keys.add("tab")
    def tab(event):
        buffer = event.current_buffer
        if buffer.complete_state:
            buffer.complete_next()
        elif isinstance(active_completer(buffer), CommandCompleter):
            completions = list(active_completer(buffer).get_completions(buffer.document, None))
            if len(completions) == 1:
                buffer.apply_completion(completions[0])
            elif completions:
                buffer.start_completion(select_first=True)

    @keys.add("enter")
    def enter(event):
        buffer = event.current_buffer
        if buffer.complete_state and buffer.complete_state.completions:
            completion = (buffer.complete_state.current_completion
                          or buffer.complete_state.completions[0])
            buffer.apply_completion(completion)
        buffer.validate_and_handle()

    @keys.add("escape", eager=True)
    def escape(event):
        if event.current_buffer.complete_state:
            event.current_buffer.cancel_completion()
        else:
            event.app.exit(exception=KeyboardInterrupt())

    return keys


class Shell(RagMenu):
    def __init__(self, settings=None, *, session=None, write=print, runner=run_module):
        self.settings = settings or Settings.from_env()
        db = Path(self.settings.db_path).expanduser()
        if not db.is_absolute():
            self.settings = replace(self.settings, db_path=str(ROOT / db))
        self.router_model = os.environ.get("SHELL_ROUTER_MODEL", "qwen3:0.6b")
        self.router_timeout = float(os.environ.get("SHELL_ROUTER_TIMEOUT_SECONDS", "15"))
        replace(self.settings, model=self.router_model, timeout_seconds=self.router_timeout)
        self.session = session or PromptSession(
            key_bindings=bindings(), color_depth=ColorDepth.DEPTH_1_BIT,
            complete_while_typing=True,
        )
        self.write_raw = write
        self.runner = runner
        self.synthetic = False
        self.running = True
        self.last_progress = 0.0

    def say(self, value):
        self.write_raw(safe_text(value))

    def ask(self, message, *, menu=False):
        return self.session.prompt(
            message, completer=CommandCompleter() if menu else None,
        ).strip()

    def confirm(self, message):
        while True:
            answer = self.ask(message + " [s/N]: ").casefold()
            if answer in {"s", "sim"}:
                return True
            if answer in {"", "n", "nao", "não"}:
                return False
            self.say("Digite s para confirmar ou n para cancelar.")

    def choose(self, message, values, default=None):
        while True:
            answer = self.ask(message + " (" + ", ".join(values) + "): ")
            if not answer and default is not None:
                return default
            if answer in values:
                return answer
            self.say("Opção inválida. Use uma das opções acima; Ctrl+C cancela.")

    def integer(self, message, default, minimum=1, maximum=100000):
        while True:
            value = self.ask(f"{message} [{default}]: ")
            try:
                number = int(value) if value else default
                if minimum <= number <= maximum:
                    return number
            except ValueError:
                pass
            self.say(f"Informe um inteiro entre {minimum} e {maximum}.")

    def progress(self):
        now = time.monotonic()
        if now - self.last_progress > 5:
            self.say("Processando... Ctrl+C cancela e retorna ao menu.")
            self.last_progress = now

    def process(self, module, arguments, **kwargs):
        self.last_progress = 0
        self.progress()
        return self.runner(module, arguments, self.settings, progress=self.progress, **kwargs)

    def models(self):
        return installed_models(replace(self.settings, timeout_seconds=3))

    def status(self):
        try:
            names = [model["name"] for model in self.models()]
            self.say("Ollama disponível. Modelos locais: " + (", ".join(names) or "nenhum"))
        except (httpx.HTTPError, ConnectionError, TypeError, RuntimeError):
            self.say("Ollama indisponível. Comandos com barra continuam disponíveis.")
        self.say(f"Extrator: {self.settings.model}; roteador: {self.router_model}")
        try:
            exists = Path(self.settings.db_path).is_file()
            read_history(self.settings.db_path)
            self.say("Banco: disponível (somente leitura na consulta)." if exists else
                     "Banco: ainda não existe; será criado apenas ao salvar uma extração.")
        except (OSError, sqlite3.Error, ValueError):
            self.say("Banco existente inacessível ou incompatível.")

    def propose(self, proposal, details=None):
        self.say("Proposta:\n" + json.dumps(
            {**proposal.model_dump(exclude_none=True), **(details or {})},
            ensure_ascii=False, indent=2,
        ))
        return self.confirm("Executar esta proposta?")

    def extract(self, proposal):
        while True:
            text = self.ask("Relato sintético (texto literal; Ctrl+C cancela): ")
            if text and len(text.encode("utf-8")) <= MAX_INPUT_BYTES:
                break
            self.say("Use texto não vazio com até 2.400 bytes UTF-8.")
        if not self.propose(proposal, {"texto_sintetico": text, "modelo": self.settings.model,
                                       "banco": self.settings.db_path}):
            return
        result = self.process(
            "agents.extractor", ["--synthetic", "--model", self.settings.model,
                                 "--db", self.settings.db_path], text=text,
        )
        try:
            parsed = ProcessingResult.model_validate_json(result.stdout)
        except ValueError:
            self.say("Extração não concluída. Nenhum resultado validado recebido.")
            return
        self.say(parsed.model_dump_json(indent=2))
        if result.code == 3:
            self.say("Falha ao gravar no banco; o resultado acima não foi salvo.")
        elif result.code:
            self.say("Erro operacional registrado; não foi fabricada uma classificação.")
        else:
            self.say("Resultado validado e salvo no banco local.")

    def history(self, page):
        while True:
            records, more = read_history(self.settings.db_path, page)
            self.say(f"Histórico - página {page}")
            if not records:
                self.say("Nenhum registro nesta página. Nenhum banco foi criado.")
            for record in records:
                self.say(json.dumps(record, ensure_ascii=False))
            choice = self.choose("Navegação", ["anterior", "proxima", "voltar"], "voltar")
            if choice == "voltar":
                return
            if choice == "proxima" and more:
                page += 1
            elif choice == "anterior" and page > 1:
                page -= 1
            else:
                self.say("Não há página nessa direção.")

    def model_selection(self, proposal):
        names = [item["name"] for item in self.models()]
        self.say("Modelos locais: " + (", ".join(names) or "nenhum"))
        if not names:
            return
        target = self.choose("Selecionar para", ["extrator", "roteador", "voltar"], "voltar")
        if target == "voltar":
            return
        model = self.choose("Modelo", names)
        if self.propose(proposal, {"destino": target, "modelo": model}):
            if target == "extrator":
                self.settings = replace(self.settings, model=model)
            else:
                replace(self.settings, model=model)
                self.router_model = model
            self.say("Modelo alterado somente nesta sessão.")

    def configure(self, proposal):
        self.say(json.dumps({
            "extrator": self.settings.model, "roteador": self.router_model,
            "contexto": self.settings.context_tokens, "timeout": self.settings.timeout_seconds,
            "timeout_roteador": self.router_timeout, "banco": self.settings.db_path,
        }, ensure_ascii=False, indent=2))
        field = self.choose("Alterar", ["contexto", "timeout", "timeout_roteador", "banco", "voltar"],
                            "voltar")
        if field == "voltar":
            return
        if field == "contexto":
            value = self.integer("Tokens de contexto", self.settings.context_tokens, 2048, 4096)
            settings = replace(self.settings, context_tokens=value)
        elif field in {"timeout", "timeout_roteador"}:
            value = self.integer("Timeout em segundos", 15 if field == "timeout_roteador" else 60,
                                 1, 600)
            settings = replace(self.settings, timeout_seconds=value) if field == "timeout" else None
        else:
            value = self.ask("Caminho do banco (relativo ao projeto ou absoluto): ")
            if not value or value == ":memory:":
                self.say("Caminho de arquivo obrigatório.")
                return
            path = Path(value).expanduser()
            value = str(path if path.is_absolute() else ROOT / path)
            settings = replace(self.settings, db_path=value)
        if self.propose(proposal, {"preferencia": field, "valor": value}):
            if settings is not None:
                self.settings = settings
            else:
                self.router_timeout = value
            self.say("Preferência alterada somente nesta sessão.")

    def evaluate(self, proposal):
        mode = proposal.argumentos.modo or self.choose("Avaliação", ["smoke", "dev", "holdout"])
        names = [item["name"] for item in self.models()]
        if not names:
            self.say("Nenhum modelo instalado; avaliação cancelada.")
            return
        model = self.choose("Modelo a avaliar", names,
                            self.settings.model if self.settings.model in names else None)
        reps = 1 if mode == "smoke" else self.integer("Repetições", 3, 1, 10)
        output_dir = ROOT / "results"
        checkpoints = sorted(output_dir.glob("shell-*.jsonl"))
        resume = False
        output = output_dir / ("shell-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json")
        if checkpoints and self.confirm("Retomar um checkpoint existente?"):
            selected = self.choose("Checkpoint", [p.name for p in checkpoints])
            output = output_dir / selected.replace(".jsonl", ".json")
            resume = True
        if not self.propose(proposal, {"modo": mode, "modelo": model, "repeticoes": reps,
                                       "resultado": str(output), "retomar": resume}):
            return
        args = ["--models", model, "--split", "dev" if mode == "smoke" else mode,
                "--repetitions", str(reps), "--output", str(output)]
        if mode == "smoke":
            args += ["--limit", "3"]
        if resume:
            args += ["--resume"]
        result = self.process("evaluation.runner", args)
        self.say(result.stdout)
        self.say("Avaliação concluída." if result.code == 0 else
                 "Avaliação interrompida ou com erro. Consulte o checkpoint em results/.")
        if result.stderr:
            self.say(result.stderr)

    def execute(self, proposal, *, natural=False):
        tool = proposal.ferramenta
        if tool == "esclarecer":
            self.say("Pedido ambíguo ou não permitido. Escolha uma ação por vez; use /ajuda.")
            return
        if tool not in {"ajuda", "status", "sair"} and not self.synthetic:
            self.synthetic = self.confirm("Confirma usar exclusivamente dados sintéticos nesta sessão?")
            if not self.synthetic:
                self.say("Use /ajuda, /status ou /sair até confirmar dados sintéticos.")
                return
        # Formulários exibem a proposta completa depois de coletar os campos.
        if (natural and tool in {"ajuda", "status", "sair", "limpar", "historico"}
                and not self.propose(proposal)):
            return
        if tool == "ajuda":
            self.say("\n".join(f"/{name}: {description}" for name, description in COMMANDS.items()))
            self.say("/ abre menu; setas navegam; Tab completa; Enter seleciona; Esc cancela.\n"
                     "Ctrl+C cancela operação; EOF ou /sair encerra.\n"
                     "Exemplos: /extrair; /historico; 'ver status do ambiente'.\n"
                     "Texto no formulário é dado literal, inclusive comandos. Sem diagnóstico.")
        elif tool == "status":
            self.status()
        elif tool == "sair":
            self.running = False
        elif tool == "limpar":
            self.session.app.output.erase_screen()
            self.session.app.output.cursor_goto(0, 0)
            self.session.app.output.flush()
        elif tool == "rag":
            self.rag(proposal)
        elif tool == "extrair":
            self.extract(proposal)
        elif tool == "historico":
            self.history(proposal.argumentos.pagina or 1)
        elif tool == "modelos":
            self.model_selection(proposal)
        elif tool == "config":
            self.configure(proposal)
        elif tool == "avaliar":
            self.evaluate(proposal)
        elif tool == "testes" and self.propose(proposal, {"execucao": "python -m pytest -q"}):
            result = self.process("pytest", ["-q"])
            self.say(result.stdout)
            self.say(result.stderr)
            self.say(f"Testes encerrados com código {result.code}.")

    def handle(self, text):
        if not text:
            return
        if text.startswith("/"):
            command = text[1:]
            if command not in COMMANDS:
                self.say("Comando desconhecido. Use /ajuda; comandos não aceitam argumentos livres.")
                return
            self.execute(Proposal(ferramenta=command, argumentos=Arguments()))
            return
        if not self.synthetic:
            self.synthetic = self.confirm("Confirma usar exclusivamente dados sintéticos nesta sessão?")
            if not self.synthetic:
                return
        result = self.process("app.router", [self.router_model, str(self.router_timeout)],
                              text=text, timeout=self.router_timeout)
        if result.code:
            self.say("Roteador indisponível ou inválido. Use os comandos com barra.")
            return
        try:
            proposal = Proposal.model_validate_json(result.stdout)
        except ValueError:
            self.say("Proposta inválida; nenhuma ação executada.")
            return
        self.execute(proposal, natural=True)

    def run(self):
        self.say("Diário Emocional Inteligente - ambiente de desenvolvimento\n"
                 "Somente dados sintéticos. /ajuda para começar; /sair para encerrar.")
        try:
            self.synthetic = self.confirm("Confirma usar exclusivamente dados sintéticos nesta sessão?")
        except KeyboardInterrupt:
            self.say("Confirmação cancelada.")
        except EOFError:
            return 0
        while self.running:
            try:
                self.handle(self.ask("bem-estar> ", menu=True))
            except KeyboardInterrupt:
                self.say("Operação cancelada; de volta ao menu.")
            except EOFError:
                break
            except (TimeoutError, OSError, ValueError, sqlite3.Error):
                self.say("Operação não concluída. Verifique /status e /config; de volta ao menu.")
            except (httpx.HTTPError, ConnectionError, TypeError, RuntimeError):
                self.say("Serviço indisponível; nenhuma próxima ação será executada.")
        self.say("Sessão encerrada. Preferências e conversa não foram gravadas.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Shell local para desenvolvimento com dados sintéticos")
    parser.parse_args()
    if not sys.stdin.isatty():
        print("Abra um terminal interativo e execute: uv run bem-estar", file=sys.stderr)
        return 2
    try:
        return Shell().run()
    except ValueError:
        print("Configuração inválida. Consulte .env.example.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
