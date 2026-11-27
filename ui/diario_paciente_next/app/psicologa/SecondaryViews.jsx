"use client";

import { useEffect, useRef, useState } from "react";
import { getMacroMeta, getValenceStatus } from "./wheelMath";
import styles from "./impactbench.module.css";

function formatDate(raw) {
  const d = new Date(Number(raw) || raw);
  if (Number.isNaN(d.getTime())) return "Data indisponível";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

export function TimelineAndReportsView({
  patient,
  entries,
  reports,
  longitudinal,
  days,
  onUploadReport,
  onRemoveReport,
}) {
  const [filterType, setFilterType] = useState("todos");
  const [reportError, setReportError] = useState("");
  const isDemo = Boolean(patient?.isDemo);

  const visibleEntries = (entries || []).filter((e) => {
    if (filterType === "audio") return e.input_type === "audio";
    if (filterType === "alerta") {
      return e.is_risk_emotion || e.agent1?.indicio_textual_risco === "presente";
    }
    return true;
  });

  async function handleFileSelect(event) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "doc", "docx", "txt"].includes(ext)) {
      setReportError("Use arquivos PDF, DOC, DOCX ou TXT.");
      return;
    }
    setReportError("");
    await onUploadReport(file);
  }

  return (
    <div className={styles.secondaryContainer}>
      <div className={styles.secondaryGrid}>
        {/* COLUNA ESQUERDA: EVOLUÇÃO LONGITUDINAL & RELATÓRIOS */}
        <section className={styles.secCard}>
          <div className={styles.secCardHead}>
            <div>
              <span className={styles.provenanceTag}>COMPARAÇÃO LONGITUDINAL</span>
              <h2>Rotatividade de Subtemas (Agente 1)</h2>
            </div>
            <span className={styles.countPill}>{days === "all" ? "Histórico total" : `${days}d`}</span>
          </div>

          {longitudinal ? (
            <div className={styles.longitudinalGrid}>
              <p className={styles.longitudinalSummary}>{longitudinal.resumo_clinico_rotacao}</p>
              <div className={styles.deltaRow}>
                <div>
                  <strong>Emergentes ({longitudinal.subtemas_emergentes?.length || 0})</strong>
                  <p>{longitudinal.subtemas_emergentes?.join(", ") || "Nenhum novo subtema"}</p>
                </div>
                <div>
                  <strong>Persistentes ({longitudinal.subtemas_persistentes?.length || 0})</strong>
                  <p>{longitudinal.subtemas_persistentes?.join(", ") || "Nenhum persistente"}</p>
                </div>
                <div>
                  <strong>Rotacionados ({longitudinal.subtemas_rotacionados?.length || 0})</strong>
                  <p>{longitudinal.subtemas_rotacionados?.join(", ") || "Nenhum reduzido"}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className={styles.mutedText}>
              Selecione uma janela temporal (7, 14 ou 30 dias) para comparar com o período imediatamente anterior.
            </p>
          )}

          <hr className={styles.secDivider} />

          <div className={styles.secCardHead}>
            <div>
              <span className={styles.provenanceTag}>ARQUIVOS CLÍNICOS</span>
              <h2>Relatórios pós-consulta ({reports.length})</h2>
            </div>
            {!isDemo && (
              <label className={styles.uploadLabelBtn}>
                Selecionar arquivo
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={handleFileSelect}
                  hidden
                />
              </label>
            )}
          </div>
          {isDemo && (
            <p className={styles.mutedText}>Anexos ficam habilitados apenas para pacientes reais cadastrados.</p>
          )}
          {reportError && <p className={styles.ragErr}>{reportError}</p>}

          {reports.length > 0 ? (
            <ul className={styles.reportListCompact}>
              {reports.map((rep) => (
                <li key={rep.id}>
                  <div>
                    <strong>{rep.fileName}</strong>
                    <small>{formatDate(rep.uploadedAt)}</small>
                  </div>
                  {!isDemo && (
                    <button type="button" onClick={() => onRemoveReport(rep.id)}>
                      Remover
                    </button>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.mutedText}>Nenhum relatório pós-consulta anexado ainda.</p>
          )}
        </section>

        {/* COLUNA DIREITA: LINHA DO TEMPO COMPLETA DE RELATOS E ÁUDIOS */}
        <section className={styles.secCard}>
          <div className={styles.secCardHead}>
            <div>
              <span className={styles.provenanceTag}>REGISTROS CRONOLÓGICOS</span>
              <h2>Linha do Tempo do Paciente ({visibleEntries.length})</h2>
            </div>
            <div className={styles.inlineFilterTabs}>
              {[
                { key: "todos", label: "Tudo" },
                { key: "audio", label: "Áudios" },
                { key: "alerta", label: "Com alerta" },
              ].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={filterType === tab.key ? styles.tabActiveSmall : styles.tabSmall}
                  onClick={() => setFilterType(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {visibleEntries.length === 0 ? (
            <p className={styles.mutedText}>Nenhum registro encontrado neste filtro.</p>
          ) : (
            <ol className={styles.timelineList}>
              {visibleEntries.map((entry) => {
                const macroLabel = getMacroMeta(entry.theme_macro).label;
                const status = getValenceStatus(entry.polarity_score, entry.is_risk_emotion);
                const subs = entry.agent1?.subtemas || [];
                return (
                  <li key={entry.id} className={styles.timelineItem}>
                    <div className={styles.timelineTop}>
                      <div className={styles.timelineTags}>
                        <span className={styles.macroPill}>{macroLabel}</span>
                        <span className={`${styles.statusBadge} ${styles[status.badgeClass]}`}>
                          {entry.sub_emotion_symbol} {entry.character} · {entry.sub_emotion_name}
                        </span>
                        {entry.input_type === "audio" && (
                          <span className={styles.audioChip}>Áudio {entry.audio_duration || ""}</span>
                        )}
                      </div>
                      <time>{formatDate(entry.created_at)}</time>
                    </div>
                    <p className={styles.timelineText}>{entry.text}</p>
                    {entry.audio_data && (
                      <audio controls src={entry.audio_data} className={styles.audioPlayer} />
                    )}
                    {subs.length > 0 && (
                      <div className={styles.timelineSubs}>
                        <span>Agente 1:</span>
                        {subs.map((s, idx) => (
                          <span key={idx} className={styles.subChip}>{s.nome}</span>
                        ))}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

export function CopilotRagView({ patient, days, onReprocessed }) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("extractive");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const requestRef = useRef(null);
  useEffect(() => () => requestRef.current?.abort(), []);

  const slashCommands = ["/diarios", "/temas", "/literatura", "/reprocessar"];
  const suggestions = [
    "Quais relatos mencionam estresse ou sobrecarga no trabalho?",
    "Em quais momentos houve dificuldade de sono ou sinais físicos?",
    "Que episódios positivos ou de acolhimento apareceram no período?",
    "/temas",
    "/literatura limites éticos da IA em psicoterapia",
  ];

  async function submitRag(qText, confirmed = false) {
    const q = (qText || question).trim();
    if (!q || !patient?.id) return;
    requestRef.current?.abort();
    const request = new AbortController();
    requestRef.current = request;
    setQuestion(q);
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/psicologa/rag", {
        method: "POST",
        signal: request.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patientId: patient.id,
          question: q,
          days,
          generationMode: mode,
          confirmed,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Falha ao executar consulta RAG.");
      if (request.signal.aborted) return;
      if (data.status === "confirmation" && window.confirm(data.answer)) {
        await submitRag(`/reprocessar ${data.record_id}`, true);
      } else {
        setResult(data);
        if (confirmed && data.status === "ok") onReprocessed?.();
      }
    } catch (err) {
      if (!request.signal.aborted) setError(err.message);
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  }

  return (
    <div className={styles.secondaryContainer}>
      <section className={styles.secCard}>
        <div className={styles.secCardHead}>
          <div>
            <span className={styles.provenanceTag}>COPILOTO RAG CLÍNICO · BM25 + CITAÇÃO LITERAL</span>
            <h2>Consulta assistida sobre relatos de {patient?.name}</h2>
          </div>
          <label className={styles.modeSelectWrap}>
            Modo:
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="extractive">Extrativo (BM25 instantâneo)</option>
              <option value="ollama">Síntese LLM local (Ollama)</option>
            </select>
          </label>
        </div>

        <p className={styles.mutedText}>
          Todas as respostas citam trechos literais preservados do diário no recorte de tempo ativo.
          Protótipo de apoio — não emite diagnóstico nem substitui avaliação clínica.
        </p>

        {question.startsWith("/") && !question.includes(" ") && (
          <div className={styles.ragQuickChips} aria-label="Comandos do copiloto">
            {slashCommands.filter((command) => command.startsWith(question)).map((command) => (
              <button key={command} type="button" onClick={() => setQuestion(command + " ")}>
                {command}
              </button>
            ))}
          </div>
        )}

        <div className={styles.ragQuickChips}>
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => submitRag(s)}>
              {s}
            </button>
          ))}
        </div>

        <form
          className={styles.ragFormLarge}
          onSubmit={(e) => {
            e.preventDefault();
            submitRag(question);
          }}
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Faça uma pergunta clínica sobre a trajetória do paciente..."
          />
          <button type="submit" disabled={loading || !question.trim()}>
            {loading ? "Consultando..." : "Consultar histórico"}
          </button>
        </form>

        {error && <p className={styles.ragErr}>{error}</p>}

        {result && (
          <div className={styles.ragFullResult}>
            <div className={styles.ragResultMeta}>
              <span className={styles.macroPill}>
                Status: {result.status === "ok" ? "Fundamentado" : result.status}
              </span>
              <span>Registros elegíveis: {result.eligible_records}</span>
              <span>Modo: {result.generation_mode}</span>
            </div>
            <div className={styles.ragAnswerBanner}>
              <strong>Resposta do copiloto</strong>
              <p>{result.answer}</p>
            </div>
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
                      <span>Relevância {Number(ev.score).toFixed(2)}</span>
                    </footer>
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
