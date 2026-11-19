"use client";

import { useId, useState } from "react";
import type { ChangeEvent } from "react";
import type { UploadedReport } from "./types";
import styles from "./patient-management.module.css";

interface ReportUploadProps {
  reports: UploadedReport[];
  onUpload: (file: File) => void;
  onRemove: (reportId: string) => void;
}

const allowedExtensions = ["pdf", "doc", "docx", "txt"];

function formatDate(date: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));
}

// O progresso é demonstrativo: nesta versão, nenhum arquivo sai do navegador.
export default function ReportUpload({ reports, onUpload, onRemove }: ReportUploadProps) {
  const inputId = useId();
  const [error, setError] = useState("");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;

    const extension = file.name.split(".").pop()?.toLocaleLowerCase("pt-BR");
    if (!extension || !allowedExtensions.includes(extension)) {
      setError("Escolha um arquivo PDF, DOC, DOCX ou TXT.");
      return;
    }

    setError("");
    onUpload(file);
  }

  return (
    <section className={styles.card} aria-labelledby="reports-heading">
      <div className={styles.cardHeading}>
        <div>
          <p className={styles.eyebrow}>ARQUIVOS DO PACIENTE</p>
          <h2 id="reports-heading">Relatórios pós-consulta</h2>
        </div>
        <span className={styles.cardCount}>{reports.length}</span>
      </div>

      <div className={styles.uploadBox}>
        <span className={styles.uploadIcon} aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 15.5v3h14v-3" />
          </svg>
        </span>
        <div className={styles.uploadCopy}>
          <strong>Adicione um relatório</strong>
          <span>PDF, DOC, DOCX ou TXT</span>
        </div>
        <input
          className={styles.fileInput}
          id={inputId}
          type="file"
          accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          onChange={handleFileChange}
        />
        <label className={styles.secondaryButton} htmlFor={inputId}>
          Selecionar arquivo
        </label>
      </div>

      {error && <p className={styles.formError} role="alert">{error}</p>}
      <p className={styles.uploadDisclaimer}>
        Demonstração local: os arquivos ficam nesta sessão e não são enviados a um servidor.
      </p>

      {reports.length > 0 ? (
        <ul className={styles.reportList} aria-live="polite">
          {reports.map((report) => (
            <li className={styles.reportItem} key={report.id}>
              <span className={styles.fileBadge} aria-hidden="true">
                {report.fileName.split(".").pop()?.toUpperCase() ?? "DOC"}
              </span>
              <div className={styles.reportDetails}>
                <strong title={report.fileName}>{report.fileName}</strong>
                <time dateTime={report.uploadedAt}>Enviado em {formatDate(report.uploadedAt)}</time>
                <div className={styles.progressLine}>
                  <progress
                    value={report.progress}
                    max={100}
                    aria-label={`Progresso do envio de ${report.fileName}: ${report.progress}%`}
                  />
                  <span>{report.status === "concluido" ? "Concluído" : "Enviando"} · {report.progress}%</span>
                </div>
              </div>
              <button
                className={styles.removeButton}
                type="button"
                onClick={() => onRemove(report.id)}
                aria-label={`Remover o relatório ${report.fileName}`}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 7h14M10 11v6m4-6v6M7.5 7l.7 13h7.6l.7-13M9 7V4h6v3" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.emptyCard}>Nenhum relatório enviado para este paciente.</p>
      )}
    </section>
  );
}
