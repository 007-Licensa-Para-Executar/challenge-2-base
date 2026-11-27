"use client";

import { useEffect, useRef, useState } from "react";
import { getValenceStatus } from "./wheelMath";
import styles from "./impactbench.module.css";

function formatDateTime(ts) {
  if (!ts) return "Sem data";
  const d = new Date(Number(ts) || ts);
  if (Number.isNaN(d.getTime())) return "Sem data";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function renderHighlightedText(text, span) {
  const full = String(text || "");
  if (!span) return full;

  const characters = Array.from(full);
  const literal = characters.slice(span.start_char, span.end_char).join("");
  if (literal === span.quote_text) {
    return <>
      {characters.slice(0, span.start_char).join("")}
      <mark className={styles.literalHighlight}>{literal}</mark>
      {characters.slice(span.end_char).join("")}
    </>;
  }

  let start = Number(span.start_char);
  let end = Number(span.end_char);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end > full.length) {
    const idx = span.quote_text ? full.indexOf(span.quote_text) : -1;
    if (idx < 0) return full;
    start = idx;
    end = idx + span.quote_text.length;
  }

  return (
    <>
      {full.slice(0, start)}
      <mark className={styles.literalHighlight}>{full.slice(start, end)}</mark>
      {full.slice(end)}
    </>
  );
}

export default function DrillDownPanel({
  patient,
  geometry,
  wheel,
  longitudinal,
  selectedThemeId,
  selectedSubtopicKey,
  selectedOccurrence,
  isDemo,
  days,
  onSelectTheme,
  onSelectSubtopic,
  onSelectOccurrence,
  onResetSelection,
  onSaveAnnotation,
}) {
  const { ring1, ring2, isEmpty } = geometry;
  const activeMacro = ring1.find((m) => m.id === selectedThemeId) || null;
  const activeSub = ring2.find((s) => s.key === selectedSubtopicKey) || null;

  // Edição clínica de subtema pela psicóloga (mantém proveniência do Agente 1)
  const [editingSub, setEditingSub] = useState(false);
  const [editName, setEditName] = useState("");
  const [editNote, setEditNote] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // Copiloto RAG embutido no 4º painel (detalhe da evidência)
  const ragRequest = useRef(null);
  const [ragQuestion, setRagQuestion] = useState("");
  const [ragLoading, setRagLoading] = useState(false);
  const [ragResult, setRagResult] = useState(null);
  const [ragError, setRagError] = useState("");

  useEffect(() => {
    setEditingSub(false);
    setEditName(activeSub?.label || "");
    setEditNote(activeSub?.clinicalNote || "");
  }, [activeSub]);

  useEffect(() => {
    setRagResult(null);
    setRagError("");
    if (selectedOccurrence?.primarySpan?.quote_text) {
      const keywords = selectedOccurrence.primarySpan.quote_text
        .replace(/[^\p{L}\p{N}\s]/gu, " ")
        .split(/\s+/)
        .filter((w) => w.length >= 4)
        .slice(0, 4)
        .join(" ");
      setRagQuestion(
        keywords
          ? `Em quais momentos apareceram relatos com "${keywords}" ou ${activeSub?.parentLabel || "esse tema"}?`
          : `Quando "${activeSub?.parentLabel || activeSub?.label}" surgiu antes nos relatos?`,
      );
    } else if (activeSub) {
      setRagQuestion(`Quando "${activeSub.parentLabel || activeSub.label}" surgiu antes nos relatos?`);
    }
  }, [selectedOccurrence?.occurrenceId, selectedOccurrence?.primarySpan?.quote_text, activeSub]);

  useEffect(() => {
    setRagResult(null);
    setRagError("");
    setRagLoading(false);
    return () => ragRequest.current?.abort();
  }, [selectedOccurrence?.occurrenceId]);

  async function handleSaveEdit(e) {
    e.preventDefault();
    if (!activeSub || !editName.trim() || !onSaveAnnotation) return;
    setSavingEdit(true);
    try {
      await onSaveAnnotation({
        macroTema: activeSub.parentId,
        originalName: activeSub.originalName,
        displayName: editName.trim(),
        clinicalNote: editNote.trim(),
      });
      setEditingSub(false);
    } finally {
      setSavingEdit(false);
    }
  }

  async function runQuickRag(customQuestion, mode = "extractive", showSpan = false) {
    const q = (customQuestion || ragQuestion || "").trim();
    if (!q || !patient?.id) return;
    ragRequest.current?.abort();
    const request = new AbortController();
    ragRequest.current = request;
    setRagQuestion(q);
    setRagLoading(true);
    setRagError("");
    try {
      const res = await fetch("/api/psicologa/rag", {
        method: "POST",
        signal: request.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patientId: patient.id,
          question: selectedOccurrence?.entry.representation_id ? `/diarios ${q}` : q,
          days,
          generationMode: mode,
          ...(showSpan && selectedOccurrence?.entry.representation_id && {
          topic: selectedOccurrence.originalSubtopicName,
          entryId: selectedOccurrence.entry.agent1?.entry_id,
          recordId: selectedOccurrence?.entry.id,
          representationId: selectedOccurrence?.entry.representation_id,
          startChar: selectedOccurrence?.primarySpan?.start_char,
          endChar: selectedOccurrence?.primarySpan?.end_char,
          }),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Falha ao consultar Copiloto RAG.");
      if (!request.signal.aborted) setRagResult(data);
    } catch (err) {
      if (!request.signal.aborted) setRagError(err.message);
    } finally {
      if (!request.signal.aborted) setRagLoading(false);
    }
  }

  const showFourthColumn = Boolean(selectedOccurrence && activeSub);
  const totalEntriesCount = ring1.reduce((acc, m) => acc + (m.mencoes || 0), 0);

  return (
    <aside
      className={`${styles.detailsShell} ${showFourthColumn ? styles.detailsShellExpanded : ""}`}
      aria-label="Detalhamento hierárquico de temas, subtemas e evidências"
    >
      {/* COLUNA 3: VISÃO GERAL -> MACRO-TEMA (ANEL 1) -> SUBTEMA (ANEL 2) -> OCORRÊNCIAS */}
      <div className={styles.detailsPrimaryCol}>
        <div className={styles.detailsHeader}>
          <nav className={styles.breadcrumb} aria-label="Navegação na roda">
            <button
              type="button"
              className={!activeMacro ? styles.crumbActive : styles.crumbLink}
              onClick={onResetSelection}
            >
              Todos
            </button>
            <span className={styles.crumbSep} aria-hidden="true">›</span>
            {!activeMacro ? (
              <span className={styles.crumbActive}>Temas</span>
            ) : !activeSub ? (
              <span className={styles.crumbActive}>{activeMacro.label}</span>
            ) : (
              <>
                <button
                  type="button"
                  className={styles.crumbLink}
                  onClick={() => onSelectTheme(activeMacro.id)}
                >
                  {activeMacro.label}
                </button>
                <span className={styles.crumbSep} aria-hidden="true">›</span>
                <span className={styles.crumbActive}>{activeSub.label}</span>
              </>
            )}
          </nav>

          {(activeMacro || activeSub || selectedOccurrence) && (
            <button
              type="button"
              className={styles.closeIconBtn}
              title="Limpar seleção"
              aria-label="Voltar para visão geral de temas"
              onClick={onResetSelection}
            >
              ✕
            </button>
          )}
        </div>

        <div className={styles.detailsScroll}>
          {/* NÍVEL 0: VISÃO GERAL DOS MACRO-TEMAS (ANEL 1) */}
          {!activeMacro && (
            <>
              <div className={styles.panelIntro}>
                <h2>Temas identificados ({isEmpty ? 0 : ring1.length})</h2>
                <p>
                  Círculo interno extraído pela <strong>Rede Neural</strong>. Clique em qualquer
                  tema na lista ou na roda para inspecionar os subtemas do <strong>Agente 1</strong>.
                </p>
              </div>

              {longitudinal &&
                (longitudinal.subtemas_emergentes?.length > 0 ||
                  longitudinal.subtemas_persistentes?.length > 0) && (
                  <div className={styles.longitudinalMini}>
                    <span>Rotação longitudinal ({wheel?.periodo || "Período"})</span>
                    <div className={styles.deltaBadges}>
                      {longitudinal.subtemas_emergentes?.length > 0 && (
                        <span className={styles.deltaNew}>
                          +{longitudinal.subtemas_emergentes.length} emergentes
                        </span>
                      )}
                      {longitudinal.subtemas_persistentes?.length > 0 && (
                        <span className={styles.deltaKeep}>
                          {longitudinal.subtemas_persistentes.length} persistentes
                        </span>
                      )}
                    </div>
                  </div>
                )}

              <div className={styles.drillCardList}>
                {ring1.map((macro) => {
                  const status = getValenceStatus(macro.polarity, false);
                  const total = Math.max(1, macro.counts.positive + macro.counts.neutral + macro.counts.negative);
                  const posPct = Math.round((macro.counts.positive / total) * 100);
                  const negPct = Math.round((macro.counts.negative / total) * 100);
                  const neuPct = Math.max(0, 100 - posPct - negPct);

                  return (
                    <button
                      key={macro.id}
                      type="button"
                      className={styles.drillCard}
                      disabled={isEmpty}
                      onClick={() => onSelectTheme(macro.id)}
                    >
                      <div className={styles.drillCardTop}>
                        <strong>{macro.label}</strong>
                        <span className={styles.countPill}>
                          {macro.mencoes}/{Math.max(totalEntriesCount, macro.mencoes)} relatos
                        </span>
                      </div>
                      <p className={styles.drillCardDesc}>{macro.description}</p>
                      {!isEmpty && (
                        <>
                          <div className={styles.miniSegmentedBar} aria-hidden="true">
                            <span style={{ width: `${negPct}%`, background: "#ef4444" }} />
                            <span style={{ width: `${neuPct}%`, background: "#cbd5e1" }} />
                            <span style={{ width: `${posPct}%`, background: "#22c55e" }} />
                          </div>
                          <div className={styles.drillCardFooter}>
                            <span className={`${styles.valenceDotLabel}`}>
                              <i style={{ background: status.dotColor }} aria-hidden="true" />
                              {status.label}
                            </span>
                            <span className={styles.subCountHint}>
                              {macro.subtemas.length} subtema(s) ›
                            </span>
                          </div>
                        </>
                      )}
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {/* NÍVEL 1: TEMA SELECIONADO -> LISTA DE SUBTEMAS DO AGENTE 1 (ANEL 2) */}
          {activeMacro && !activeSub && (
            <>
              <div className={styles.selectedHeaderBox}>
                <span className={styles.provenanceTag}>ANEL 1 · REDE NEURAL (MLP)</span>
                <h2>{activeMacro.label}</h2>
                <p>{activeMacro.description}</p>
                <div className={styles.statsInline}>
                  <span>{activeMacro.mencoes} relato(s)</span>
                  <span>·</span>
                  <span>{activeMacro.counts.positive} positivos</span>
                  <span>·</span>
                  <span>{activeMacro.counts.negative} negativos/alerta</span>
                </div>
              </div>

              <p className={styles.groupHeading}>Subtemas do Agente 1 ({activeMacro.subtemas.length})</p>

              <div className={styles.drillCardList}>
                {activeMacro.subtemas.map((sub) => {
                  const hasRiskOcc = sub.occurrences.some(
                    (o) => o.entry.is_risk_emotion || o.entry.agent1?.indicio_textual_risco === "presente",
                  );
                  const status = getValenceStatus(sub.polarity, hasRiskOcc);
                  return (
                    <button
                      key={sub.key}
                      type="button"
                      className={styles.drillCard}
                      onClick={() => onSelectSubtopic(activeMacro.id, sub.key)}
                    >
                      <div className={styles.drillCardTop}>
                        <strong>{sub.label}</strong>
                        <span className={styles.countPill}>{sub.occurrences.length || sub.mencoes} ocorr.</span>
                      </div>
                      <p className={styles.drillCardDesc}>
                        {sub.occurrences?.[0]?.description || "Subtema extraído literalmente dos trechos."}
                      </p>
                      <div className={styles.drillCardFooter}>
                        <span className={`${styles.statusBadge} ${styles[status.badgeClass]}`}>
                          {status.label}
                        </span>
                        <span className={styles.provenanceMini}>
                          {sub.editedByPsychologist ? "Editado · ref. Agente 1" : "Agente 1"}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {/* NÍVEL 2: SUBTEMA SELECIONADO -> LISTA DE OCORRÊNCIAS LITERAIS */}
          {activeSub && (
            <>
              <div className={styles.selectedHeaderBox}>
                <div className={styles.subtopicTagRow}>
                  <span className={styles.provenanceTag}>
                    ANEL 2 · {activeSub.editedByPsychologist ? "EDITADO (ORIGEM AGENTE 1)" : "AGENTE 1"}
                  </span>
                  {!isDemo && (
                    <button
                      type="button"
                      className={styles.editSubBtn}
                      onClick={() => setEditingSub((prev) => !prev)}
                    >
                      {editingSub ? "Cancelar" : "Editar / nota"}
                    </button>
                  )}
                </div>
                <h2>{activeSub.label}</h2>
                {activeSub.editedByPsychologist && activeSub.originalName !== activeSub.label && (
                  <p className={styles.originalProvenanceNote}>
                    Rótulo original do Agente 1: <em>{activeSub.originalName}</em>
                  </p>
                )}
                {activeSub.clinicalNote && (
                  <p className={styles.clinicalNoteBox}>{activeSub.clinicalNote}</p>
                )}

                {editingSub && (
                  <form className={styles.annotationForm} onSubmit={handleSaveEdit}>
                    <label>
                      Nome clínico do subtema
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        maxLength={80}
                        required
                      />
                    </label>
                    <label>
                      Anotação clínica da psicóloga
                      <textarea
                        rows={2}
                        value={editNote}
                        onChange={(e) => setEditNote(e.target.value)}
                        placeholder="Observação clínica (preserva citação original)..."
                        maxLength={600}
                      />
                    </label>
                    <button type="submit" className={styles.saveNoteBtn} disabled={savingEdit}>
                      {savingEdit ? "Salvando..." : "Salvar anotação"}
                    </button>
                  </form>
                )}
              </div>

              <p className={styles.groupHeading}>
                Evidências literais ({activeSub.occurrences.length}) — clique para abrir
              </p>

              <div className={styles.drillCardList}>
                {activeSub.occurrences.map((occ) => {
                  const isRisk =
                    occ.entry.is_risk_emotion || occ.entry.agent1?.indicio_textual_risco === "presente";
                  const status = getValenceStatus(occ.entry.polarity_score, isRisk);
                  const isOpen = selectedOccurrence?.occurrenceId === occ.occurrenceId;

                  return (
                    <button
                      key={occ.occurrenceId}
                      type="button"
                      className={`${styles.occurrenceRow} ${isOpen ? styles.occurrenceSelected : ""}`}
                      onClick={() => onSelectOccurrence(occ)}
                    >
                      <div className={styles.occurrenceTop}>
                        <span className={styles.occurrenceQuotePreview}>
                          “{occ.primarySpan?.quote_text || occ.entry.text.slice(0, 90)}”
                        </span>
                        <span className={`${styles.statusBadge} ${styles[status.badgeClass]}`}>
                          {status.key === "critical"
                            ? "Alerta"
                            : status.key === "moderate"
                              ? "Moderado"
                              : "Positivo"}
                        </span>
                      </div>
                      <div className={styles.occurrenceMeta}>
                        <span>{formatDateTime(occ.entry.created_at)}</span>
                        <span>·</span>
                        <span>
                          {occ.entry.sub_emotion_symbol} {occ.entry.sub_emotion_name}
                        </span>
                        {occ.entry.input_type === "audio" && (
                          <span className={styles.audioChip}>Áudio</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* COLUNA 4 (DESLIZANTE): EVIDÊNCIA COMPLETA + ÁUDIO + COPILOTO RAG (PADRÃO IMPACTBENCH 4ª COLUNA) */}
      {showFourthColumn && selectedOccurrence && (
        <div className={styles.evidenceDetailCol} aria-label="Detalhes da evidência selecionada">
          <div className={styles.detailsHeader}>
            <span className={styles.evidenceDetailHeaderTitle}>Evidência & Contexto Clínico</span>
            <button
              type="button"
              className={styles.closeIconBtn}
              aria-label="Fechar painel de evidência"
              onClick={() => onSelectOccurrence(null)}
            >
              ✕
            </button>
          </div>

          <div className={styles.detailsScroll}>
            {(selectedOccurrence.entry.is_risk_emotion ||
              selectedOccurrence.entry.agent1?.indicio_textual_risco === "presente") && (
              <div className={styles.riskBanner} role="alert">
                <strong>Sinal de atenção clínica</strong>
                <p>
                  O modelo detectou emoção ou expressão de risco neste trecho. Recomenda-se leitura
                  direta pela psicóloga. <em>Apoio à decisão — não é diagnóstico.</em>
                </p>
              </div>
            )}

            <div className={styles.evidenceMetaGrid}>
              <div>
                <span>Registro</span>
                <strong>{formatDateTime(selectedOccurrence.entry.created_at)}</strong>
              </div>
              <div>
                <span>Tema (Rede Neural)</span>
                <strong>
                  {activeSub.parentLabel} (
                  {Math.round(Number(selectedOccurrence.entry.theme_confidence || 0) * 100)}%)
                </strong>
              </div>
              <div>
                <span>Sentimento / Taxonomia</span>
                <strong>
                  {selectedOccurrence.entry.sub_emotion_symbol}{" "}
                  {selectedOccurrence.entry.character} · {selectedOccurrence.entry.sub_emotion_name}
                </strong>
              </div>
              <div>
                <span>Polaridade (NLP)</span>
                <strong>{Number(selectedOccurrence.entry.polarity_score ?? 0).toFixed(2)}</strong>
              </div>
            </div>

            <div className={styles.fullEntryBox}>
              <div className={styles.fullEntryTop}>
                <span>Texto completo do paciente com trecho literal destacado</span>
                <span className={styles.sourceTag}>
                  {selectedOccurrence.entry.analysis_source || "mlp+agent1"}
                </span>
              </div>
              <p className={styles.fullEntryText}>
                {renderHighlightedText(
                  selectedOccurrence.entry.text,
                  selectedOccurrence.primarySpan,
                )}
              </p>
              {selectedOccurrence.primarySpan && (
                <p className={styles.spanCoords}>
                  Span literal verificado: caracteres {selectedOccurrence.primarySpan.start_char}–
                  {selectedOccurrence.primarySpan.end_char}
                </p>
              )}
            </div>

            {selectedOccurrence.entry.audio_data && (
              <div className={styles.audioBox}>
                <span>
                  Gravação de voz original{" "}
                  {selectedOccurrence.entry.audio_duration
                    ? `(${selectedOccurrence.entry.audio_duration})`
                    : ""}
                </span>
                <audio controls src={selectedOccurrence.entry.audio_data} className={styles.audioPlayer} />
              </div>
            )}

            {/* COPILOTO RAG EMBUTIDO */}
            <div className={styles.embeddedRagBox}>
              <div className={styles.ragBoxHeader}>
                <strong>Copiloto RAG (sobre relatos deste paciente)</strong>
                <span>BM25 + Evidência literal</span>
              </div>

              <div className={styles.ragQuickChips}>
                <button
                  type="button"
                  onClick={() => runQuickRag("Mostre o trecho selecionado", "extractive", true)}
                >
                  Mostrar trecho selecionado
                </button>
                <button
                  type="button"
                  onClick={() =>
                    runQuickRag(`Quais eventos acompanham "${activeMacro?.label}"?`, "extractive")
                  }
                >
                  Contexto de {activeMacro?.label}
                </button>
              </div>

              <div className={styles.ragInputRow}>
                <input
                  type="text"
                  value={ragQuestion}
                  onChange={(e) => setRagQuestion(e.target.value)}
                  placeholder="Perguntar ao histórico com citação literal..."
                />
                <button
                  type="button"
                  disabled={ragLoading || !ragQuestion.trim()}
                  onClick={() => runQuickRag(ragQuestion, "extractive")}
                >
                  {ragLoading ? "Buscando..." : "Consultar"}
                </button>
              </div>

              {ragError && <p className={styles.ragErr}>{ragError}</p>}

              {ragResult && (
                <div className={styles.ragAnswerCard}>
                  <p className={styles.ragAnswerText}>{ragResult.answer}</p>
                  {ragResult.evidence?.length > 0 && (
                    <ul className={styles.ragEvidenceList}>
                      {ragResult.evidence.map((ev) => (
                        <li key={ev.chunk_id}>
                          <blockquote>“{ev.quote}”</blockquote>
                          <small>
                            {formatDateTime(ev.recorded_at)} · score {Number(ev.score).toFixed(2)}
                          </small>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
