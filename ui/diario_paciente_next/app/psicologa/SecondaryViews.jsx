"use client";

import { useState } from "react";
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
