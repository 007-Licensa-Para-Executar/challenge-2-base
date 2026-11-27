import Link from "next/link";
import type { PortalPatient } from "./types";
import styles from "./patient-management.module.css";

interface PatientListProps {
  patients: PortalPatient[];
  selectedPatientId: string;
  searchTerm: string;
  isLoading: boolean;
  loadError: string;
  onRetry: () => void;
  onSearchChange: (value: string) => void;
  onSelectPatient: (patientId: string) => void;
}

// A lista usa o conjunto completo recebido do portal, inclusive vínculos pendentes.
export default function PatientList({
  patients,
  selectedPatientId,
  searchTerm,
  isLoading,
  loadError,
  onRetry,
  onSearchChange,
  onSelectPatient,
}: PatientListProps) {
  const visiblePatients = patients.filter((patient) => {
    const search = searchTerm.trim().toLocaleLowerCase("pt-BR");
    return (
      patient.fullName.toLocaleLowerCase("pt-BR").includes(search) ||
      patient.email.toLocaleLowerCase("pt-BR").includes(search)
    );
  });

  return (
    <aside className={styles.sidebar} aria-label="Pacientes cadastrados no portal">
      <Link className={styles.brand} href="/" aria-label="Meu Diário, tela de acesso">
        <span className={styles.brandMark} aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none">
            <path d="M16 26V13m0 6c-5.5 0-8-3.5-8-8 5.5 0 8 3.5 8 8Zm0-4c0-5.1 3.1-8 8-8 0 5.6-2.8 8-8 8Z" />
          </svg>
        </span>
        <span>meu diário</span>
      </Link>

      <div className={styles.sidebarHeading}>
        <div>
          <p className={styles.eyebrow}>ESPAÇO PROFISSIONAL</p>
          <h2>Pacientes</h2>
        </div>
        <span className={styles.patientCount} aria-label={`${patients.length} cadastros`}>
          {patients.length}
        </span>
      </div>

      <label className={styles.searchBox}>
        <span className={styles.screenReaderOnly}>Buscar por nome ou e-mail</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="10.8" cy="10.8" r="6.3" />
          <path d="m16 16 4.2 4.2" />
        </svg>
        <input
          type="search"
          value={searchTerm}
          onChange={(event) => onSearchChange(event.currentTarget.value)}
          placeholder="Buscar paciente"
          autoComplete="off"
        />
      </label>

      <ul className={styles.patientList}>
        {visiblePatients.map((patient) => {
          const isSelected = patient.id === selectedPatientId;
          const isLinked = patient.linkStatus === "vinculado";

          return (
            <li key={patient.id}>
              <button
                type="button"
                className={`${styles.patientButton} ${isSelected ? styles.patientSelected : ""}`}
                onClick={() => onSelectPatient(patient.id)}
                aria-pressed={isSelected}
              >
                <span className={styles.patientAvatar} aria-hidden="true">
                  {patient.initials}
                </span>
                <span className={styles.patientSummary}>
                  <span className={styles.patientName}>{patient.fullName}</span>
                  <span className={`${styles.linkStatus} ${patient.isDemo ? styles.demoCaseStatus : isLinked ? styles.linked : styles.pending}`}>
                    <span className={styles.statusDot} aria-hidden="true" />
                    {patient.isDemo ? "Caso fictício · demonstração" : isLinked ? "Vinculado" : "Aguardando vínculo"}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {isLoading && patients.length === 0 && (
        <p className={styles.emptySearch} role="status">Carregando cadastros do portal…</p>
      )}

      {loadError && (
        <div className={styles.listError} role="alert">
          <p>{loadError}</p>
          <button className={styles.retryButton} type="button" onClick={onRetry}>Tentar novamente</button>
        </div>
      )}

      {!isLoading && !loadError && patients.length === 0 && (
        <p className={styles.emptySearch}>Ainda não há pacientes cadastrados no portal.</p>
      )}

      {patients.length > 0 && visiblePatients.length === 0 && (
        <p className={styles.emptySearch}>Nenhum paciente encontrado com esse nome.</p>
      )}

      <p className={styles.sidebarNote}>
        A lista inclui cadastros do portal e casos de demonstração identificados como fictícios.
      </p>
    </aside>
  );
}
