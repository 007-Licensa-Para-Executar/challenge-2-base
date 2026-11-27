"""Formulários do protótipo: argumentos fechados, execução cancelável e fontes visíveis."""

import json
from datetime import UTC, datetime

from agents.copilot.contracts import DiaryRecord, Query
from app.processes import ROOT


class RagMenu:
    def rag(self, proposal, *, natural=False):
        action = self.choose("RAG de pesquisa", [
            "treinar", "preparar", "registrar", "listar", "perguntar", "avaliar", "voltar",
            *(["chat"] if self.privacy_mode else []),
        ], "voltar")
        if action == "voltar":
            return
        if action == "chat":
            self.integrated_chat()
            return
        db = getattr(self, "rag_db", ROOT / "data" / "copilot_demo.sqlite3")
        protected = self.privacy_mode
        if protected:
            db = getattr(self, "rag_db", ROOT / "data" / "privacy" / "analytics.sqlite3")
        artifacts = ROOT / "dist" / "rag-demo"
        if action == "treinar":
            if not self.propose(proposal, {
                "acao": action, "dataset": "data/synthetic/synthetic_diaries.json",
                "epocas": 35, "inicializacao": "gaussian", "artefatos": str(artifacts),
                "aviso": "Experimento sintético; pode demorar. Substitui apenas dist/rag-demo.",
            }):
                return
            result = self.process("app.research_demo", ["train"])
            self.say(result.stdout)
            if result.stderr:
                self.say(result.stderr)
            self.say("Treino concluído. Use /rag → preparar com classificação." if not result.code
                     else "Treino não concluído; não prepare uma base com artefatos parciais.")
            return
        if action == "avaliar":
            split = self.choose("Conjunto congelado", ["dev", "test"], "dev")
            output = ROOT / "results" / (
                "rag-shell-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json"
            )
            if not self.propose(proposal, {"acao": action, "backend": "bm25", "split": split,
                                           "arquivo": str(output)}):
                return
            result = self.process("evaluation.patient_rag", [
                "--backend", "bm25", "--split", split, "--output", str(output),
            ])
            self.rag_result(result)
            return
        if action in {"preparar", "registrar"}:
            classify = self.choose("Classificar com a rede treinada?", ["sim", "nao"], "sim")
            classification = []
            if classify == "sim":
                weights = artifacts / "best_theme_mlp.pt"
                embedder = artifacts / "theme_embedder.joblib"
                if not weights.is_file() or not embedder.is_file():
                    self.say("Artefatos ausentes. Use /rag → treinar primeiro, ou escolha nao "
                             "para demonstrar somente a recuperação.")
                    return
                classification = ["--classify", "--model-path", str(weights),
                                  "--vectorizer-path", str(embedder)]
            if action == "preparar":
                # Base nova evita reutilizar registros sem classificação ou versões antigas.
                db = ROOT / "data" / (
                    "copilot-demo-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".sqlite3"
                )
                if protected:
                    db = ROOT / "data" / "privacy" / db.name
                args = ["seed", "--synthetic", "--db", str(db), *classification]
                details = {"acao": action, "banco_novo": str(db), "classificar": classify,
                           "conteudo": "20 diários fictícios: patient_ana e patient_bruno"}
                text = None
            else:
                patient = self.ask("ID do paciente fictício (ex.: patient_ana): ")
                at = self.ask("Data ISO com fuso [agora UTC]: ") or datetime.now(UTC).isoformat()
                text = self.ask("Diário fictício (texto literal; Ctrl+C cancela): ")
                record = DiaryRecord(patient_id=patient, recorded_at=at, original_text=text)
                args = ["ingest", "--synthetic", "--patient-id", record.patient_id,
                        "--at", record.recorded_at.isoformat(), "--db", str(db), *classification]
                details = {"acao": action, "banco": str(db), "classificar": classify,
                           "paciente": patient, "data": at,
                           "texto_literal": f"{len(text)} caracteres" if protected else text}
                if protected and classify == "sim":
                    subtopics = self.confirm("Executar Agente 1 para extrair subtemas?")
                    details["extrair_subtemas"] = subtopics
                    if subtopics:
                        args += ["--subtopics", "--model", self.settings.model,
                                 "--ollama-host", self.settings.host, "--timeout", "90"]
            if not self.propose(proposal, details):
                return
            if protected:
                args.append("--privacy")
            result = self.process("agents.copilot", args, text=text)
            # Mesmo quando a classificação falha, o CLI pode conservar o original.
            if db.is_file():
                self.rag_db = db
            self.rag_result(result)
            return
        patient = self.ask("ID do paciente fictício (patient_ana / patient_bruno): ")
        start = self.ask("De (ISO com fuso; Enter = sem limite): ") or None
        end = self.ask("Até (ISO com fuso; Enter = sem limite): ") or None
        question = self.ask("Pergunta (texto literal): ") if action == "perguntar" else "listar"
        query = Query(patient_id=patient, question=question, start_at=start, end_at=end)
        args = ["list"]
        input_text = None
        if action == "perguntar":
            args = ["ask", "--question-stdin"] if protected else ["ask", question]
            input_text = question if protected else None
        if protected:
            args.append("--privacy")
        args += ["--patient-id", query.patient_id, "--db", str(db)]
        if start:
            args += ["--from", start]
        if end:
            args += ["--to", end]
        if action == "perguntar":
            mode = self.choose("Resposta", ["extractive", "ollama"], "extractive")
            args += ["--generation", mode, "--model", self.settings.model,
                     "--ollama-host", self.settings.host, "--timeout", "90"]
        # Consulta direta é somente leitura; pedido natural confirma a ação/contexto.
        self.say(f"Contexto: {patient}; banco: {db}; período: {start or '*'} até {end or '*'}")
        if natural and not self.propose(proposal, {
            "acao": action, "paciente": patient, "de": start, "ate": end,
            "pergunta": question, "banco": str(db),
        }):
            return
        self.rag_result(self.process("agents.copilot", args, text=input_text) if protected
                        else self.process("agents.copilot", args))

    def integrated_chat(self):
        patient = self.choose("Paciente fictício", ["patient_ana", "patient_bruno"])
        days = self.choose("Período em dias", ["all", "7", "14", "30"], "all")
        question = self.ask("Chat (/diarios, /temas, /literatura, /reprocessar): ")
        payload = {"patient": patient, "days": days, "question": question}
        result = self.process("agents.copilot.integration_cli", ["chat"], text=json.dumps(payload))
        try:
            proposal = json.loads(result.stdout)
        except ValueError:
            self.rag_result(result)
            return
        if proposal.get("status") == "confirmation" and self.confirm(proposal["answer"]):
            payload.update(question=f"/reprocessar {proposal['record_id']}", confirmed=True)
            result = self.process("agents.copilot.integration_cli", ["chat"],
                                  text=json.dumps(payload))
        self.rag_result(result)

    def rag_result(self, result):
        if result.stderr:
            self.say(result.stderr)
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            self.say(result.stdout)
            self.say(f"Operação encerrada com código {result.code}; nenhum resultado inventado.")
            return
        if isinstance(payload, dict) and "answer" in payload:
            self.say(f"Estado: {payload['status']}\n{payload['answer']}")
            self.say(f"Registros no período: {payload.get('eligible_records', '—')}; "
                     f"temas previstos: {payload.get('theme_counts', {})}")
            for source in payload.get("sources", []):
                self.say(f"{source['title']} | {source['source_url']}\n{source['quote_text']}")
            for evidence in payload.get("evidence", []):
                self.say(f"[{evidence['chunk_id']}] {evidence['patient_id']} | "
                         f"{evidence['recorded_at']} | {evidence['source_title']}\n"
                         f"{evidence['quote']}")
        else:
            self.say(json.dumps(payload, ensure_ascii=False, indent=2))
        if result.code:
            self.say("Operação com erro; confira o estado acima. Nenhuma ação posterior executada.")
