"use client";

import { useState } from "react";
import type { HistoryType, PatientHistoryItem } from "./types";
import styles from "./patient-management.module.css";

interface PatientHistoryProps {
  history: PatientHistoryItem[];
}

type HistoryFilter = "todos" | HistoryType;

const filters: { value: HistoryFilter; label: string }[] = [
  { value: "todos", label: "Tudo" },
  { value: "relatorio", label: "Relatórios" },
  { value: "diario", label: "Diário" },
  { value: "consulta", label: "Consultas" },
];

const typeLabels: Record<HistoryType, string> = {
  relatorio: "Relatório",
  diario: "Diário",
  consulta: "Consulta",
};

function formatDate(date: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

// O filtro altera apenas a visualização; todos os registros permanecem no histórico.
export default function PatientHistory({ history }: PatientHistoryProps) {
  const [filter, setFilter] = useState<HistoryFilter>("todos");
  const visibleHistory = history
    .filter((item) => filter === "todos" || item.type === filter)
    .sort((first, second) => new Date(second.date).getTime() - new Date(first.date).getTime());

  return (
    <section className={styles.card} aria-labelledby="history-heading">
      <div className={styles.cardHeading}>
        <div>
          <p className={styles.eyebrow}>LINHA DO TEMPO</p>
          <h2 id="history-heading">Histórico completo</h2>
        </div>
        <span className={styles.cardCount}>{history.length}</span>
      </div>

      <div className={styles.historyFilters} role="group" aria-label="Filtrar histórico por tipo">
        {filters.map((item) => (
          <button
            key={item.value}
            type="button"
            className={`${styles.filterButton} ${filter === item.value ? styles.filterActive : ""}`}
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {visibleHistory.length > 0 ? (
        <ol className={styles.historyList} aria-live="polite">
          {visibleHistory.map((item) => (
            <li className={styles.historyItem} key={item.id}>
              <span className={`${styles.historyMarker} ${styles[`marker_${item.type}`]}`} aria-hidden="true">
                {item.type === "relatorio" ? "R" : item.type === "diario" ? "D" : "C"}
              </span>
              <div className={styles.historyCopy}>
                <div className={styles.historyTitleRow}>
                  <strong>{item.title}</strong>
                  <span className={styles.historyType}>{typeLabels[item.type]}</span>
                </div>
                <p>{item.description}</p>
                <time dateTime={item.date}>{formatDate(item.date)}</time>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className={styles.emptyCard}>
          {history.length === 0
            ? "Este paciente ainda não tem registros no histórico."
            : "Não há registros deste tipo no histórico."}
        </p>
      )}
    </section>
  );
}
