"use client";

import { useEffect, useImperativeHandle, useRef, useState } from "react";
import { createPortal } from "react-dom";
import styles from "./impactbench.module.css";

function formatDate(value) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" }).format(new Date(value));
}

const SERVICE_ERRORS = {
  service_unavailable: "Ollama local indisponível. Você pode continuar usando Trechos citados.",
  model_unavailable: "O Qwen configurado está indisponível no Ollama local.",
  generation_timeout: "O Ollama não respondeu no tempo disponível.",
  retrieval_unavailable: "Não foi possível recuperar trechos do diário.",
};

export default function CopilotPrompt({
  ref, patient, days, onDaysChange, showPeriod, mode, onModeChange,
  resultsTarget, onOpenHistory, onReprocessed,
}) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [error, setError] = useState("");
  const [tools, setTools] = useState([]);
  const requestRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const catalogueRequest = new AbortController();
    fetch("/api/psicologa/rag", { signal: catalogueRequest.signal })
      .then((response) => response.ok ? response.json() : { tools: [] })
      .then((data) => {
        if (!catalogueRequest.signal.aborted) setTools(data.tools || []);
      })
      .catch(() => {});
    return () => {
      catalogueRequest.abort();
      requestRef.current?.abort();
    };
  }, []);

  async function submit(text, { confirmed = false, evidence, generationMode = mode } = {}) {
    const prompt = text.trim();
    if (!prompt || !patient?.id) return;
    requestRef.current?.abort();
    const request = new AbortController();
    requestRef.current = request;
    setQuestion("");
    setResult(null);
    setProposal(null);
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/psicologa/rag", {
        method: "POST",
        signal: request.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patientId: patient.id, question: prompt, days, generationMode, confirmed, ...evidence,
        }),
      });
      const data = await response.json();
      if (request.signal.aborted) return;
      if (!response.ok) throw new Error(data.message || "Falha ao consultar o copiloto.");
      if (data.status === "confirmation") {
        setProposal(data);
      } else if (data.action === "historico") {
        onOpenHistory();
      } else if (data.action !== "limpar") {
        setResult(data);
        if (confirmed && data.status === "ok") onReprocessed();
      }
    } catch (err) {
      if (!request.signal.aborted) setError(err.message);
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  }

  useImperativeHandle(ref, () => ({
    showEvidence(occurrence) {
      const { entry, primarySpan, originalSubtopicName } = occurrence;
      if (!entry.representation_id || !entry.agent1?.entry_id || !primarySpan) return;
      void submit("/diarios Mostre o trecho selecionado", {
        generationMode: "extractive",
        evidence: {
          topic: originalSubtopicName, entryId: entry.agent1.entry_id, recordId: entry.id,
          representationId: entry.representation_id,
          startChar: primarySpan.start_char, endChar: primarySpan.end_char,
        },
      });
    },
  }));

  const slashMenu = question.startsWith("/") && !question.includes(" ");
  const responses = (
      <div className={resultsTarget ? undefined : styles.copilotResponses} aria-live="polite">
        {loading && <p role="status">Consultando…</p>}
        {error && <p role="alert" className={styles.ragErr}>{error}</p>}
        {proposal && (
          <div role="group" aria-label="Confirmar reprocessamento">
            <p>{proposal.answer}</p>
            <div className={styles.ragQuickChips}>
              <button type="button" onClick={() => submit(`/reprocessar ${proposal.record_id}`, { confirmed: true })}>
                Confirmar
              </button>
              <button type="button" onClick={() => {
                setProposal(null);
                setResult({ status: "cancelled", answer: "Reprocessamento cancelado." });
              }}>
                Cancelar
              </button>
            </div>
          </div>
        )}
        {result && (
          <div className={styles.ragFullResult}>
            <div className={styles.ragResultMeta}>
              <span className={styles.macroPill}>
                {result.status === "ok" ? "Concluído" : result.status === "insufficient_evidence" ? "Evidência insuficiente" : result.status}
              </span>
              {Number.isInteger(result.eligible_records) && <span>Registros elegíveis: {result.eligible_records}</span>}
              {result.generation_mode && <span>
                {result.generation_mode === "ollama"
                  ? `Ollama · ${result.model || "Qwen"}`
                  : "Trechos citados"}
              </span>}
            </div>
            <div className={styles.ragAnswerBanner}>
              <strong>Resposta do copiloto</strong>
              <p>{SERVICE_ERRORS[result.error_code] || result.answer}</p>
            </div>
            {result.tools && (
              <ul>{result.tools.map(({ command, description }) => (
                <li key={command}><code>{command}</code> · {description}</li>
              ))}</ul>
            )}
            {result.sources?.map((source) => (
              <article key={source.chunk_id} className={styles.ragEvCard}>
                <blockquote>{source.quote_text}</blockquote>
                <a href={source.source_url} target="_blank" rel="noreferrer">{source.title}</a>
              </article>
            ))}
            {result.evidence?.length > 0 && (
              <div className={styles.ragEvidenceCards}>
                {result.evidence.map((ev) => (
                  <article key={ev.chunk_id} className={styles.ragEvCard}>
                    <blockquote>“{ev.quote}”</blockquote>
                    <footer>
                      <span>{ev.source_title}</span>
                      <time>{formatDate(ev.recorded_at)}</time>
                      {ev.representation_id && <span>Diário {ev.record_id} · trecho {ev.start_char}–{ev.end_char}</span>}
                      {!ev.entry_id && <span>Relevância {Number(ev.score).toFixed(2)}</span>}
                    </footer>
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
  );
  return (
    <section className={styles.copilotDock} aria-label="Copiloto">
      {resultsTarget ? createPortal(
        <section className={styles.secCard}>
          <div className={styles.secCardHead}>
            <div>
              <span className={styles.provenanceTag}>COPILOTO RAG</span>
              <h2>Consulta assistida sobre relatos de {patient?.name}</h2>
            </div>
          </div>
          <div className={styles.ragQuickChips}>
            {["/diarios sobrecarga no trabalho", "/diarios sono", "/temas"].map((example) => (
              <button key={example} type="button" onClick={() => submit(example)}>{example}</button>
            ))}
          </div>
          {responses}
        </section>, resultsTarget,
      ) : responses}
      <div className={styles.copilotControls}>
        <strong>{patient ? `Copiloto · ${patient.name}` : "Selecione um paciente para usar o copiloto"}</strong>
        {showPeriod && <label>
          Período{" "}
          <select value={days} onChange={(event) => onDaysChange(event.target.value)}>
            <option value="all">Todo o histórico</option>
            <option value="7">Últimos 7 dias</option>
            <option value="14">Últimos 14 dias</option>
            <option value="30">Últimos 30 dias</option>
          </select>
        </label>}
        <div className={styles.copilotModes} role="group" aria-label="Modo de resposta do diário">
          <button type="button" aria-pressed={mode === "extractive"}
            onClick={() => onModeChange("extractive")}>
            Trechos citados
          </button>
          <button type="button" aria-pressed={mode === "ollama"}
            onClick={() => onModeChange("ollama")}>
            Ollama · Qwen
          </button>
        </div>
      </div>
      {slashMenu && (
        <div className={styles.ragQuickChips} aria-label="Ferramentas do copiloto">
          {tools.filter(({ command }) => command.startsWith(question)).map(({ command, description }) => (
            <button key={command} type="button" title={description}
              onClick={() => {
                setQuestion(command + " ");
                inputRef.current?.focus();
              }}>
              {command}
            </button>
          ))}
        </div>
      )}
      <form className={styles.ragFormLarge} onSubmit={(event) => {
        event.preventDefault();
        void submit(question);
      }}>
        <input
          ref={inputRef}
          aria-label="Mensagem ao copiloto"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Escreva uma pergunta ou digite / para ver as ferramentas"
          disabled={!patient}
        />
        <button type="submit" disabled={!patient || loading || !question.trim()}>Enviar</button>
      </form>
    </section>
  );
}
