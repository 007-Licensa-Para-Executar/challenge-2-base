"use client";

import { useMemo, useState } from "react";
import {
  filterExternalSupervisors,
  shouldShowExternalSupervisorsButton,
  SUPERVISOR_FILTER_GROUPS,
} from "./supervisorCatalog";
import styles from "./patient-management.module.css";

type ExternalSupervisorsProps = {
  patientId: string | null;
  patientName: string;
};

export default function ExternalSupervisors({
  patientId,
  patientName,
}: ExternalSupervisorsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const supervisors = useMemo(() => filterExternalSupervisors(query), [query]);

  if (!shouldShowExternalSupervisorsButton(patientId)) return null;

  return (
    <section className={styles.externalSupervisors}>
      <button
        className={styles.externalSupervisorsTrigger}
        type="button"
        aria-expanded={isOpen}
        aria-controls="external-supervisors-panel"
        onClick={() => setIsOpen((open) => !open)}
      >
        Supervisores externos
      </button>

      <div
        className={styles.externalSupervisorsPanel}
        id="external-supervisors-panel"
        aria-labelledby="external-supervisors-title"
        hidden={!isOpen}
      >
          <header className={styles.externalSupervisorsHeader}>
            <div>
              <h2 id="external-supervisors-title">Buscar supervisores</h2>
              <p>Busca associada ao paciente: {patientName}</p>
            </div>
            <button
              className={styles.externalSupervisorsClose}
              type="button"
              onClick={() => setIsOpen(false)}
            >
              Fechar
            </button>
          </header>

          <label className={styles.searchBox} htmlFor="external-supervisor-search">
            <span className={styles.screenReaderOnly}>
              Filtrar por especialidade, área de foco ou abordagem
            </span>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="10.8" cy="10.8" r="6.3" />
              <path d="m16 16 4.2 4.2" />
            </svg>
            <input
              id="external-supervisor-search"
              type="search"
              list="external-supervisor-options"
              value={query}
              onChange={(event) => setQuery(event.currentTarget.value)}
              placeholder="Especialidade, área ou abordagem"
              autoComplete="off"
            />
            <datalist id="external-supervisor-options">
              {SUPERVISOR_FILTER_GROUPS.flatMap((group) =>
                group.options.map((option) => <option key={option} value={option} />),
              )}
            </datalist>
          </label>

          {query.trim() ? (
            supervisors.length ? (
              <>
                <p className={styles.externalSupervisorsCount} role="status">
                  {supervisors.length} {supervisors.length === 1 ? "supervisor encontrado" : "supervisores encontrados"}
                </p>
                <ul className={styles.externalSupervisorList}>
                  {supervisors.map((supervisor) => (
                    <li className={styles.externalSupervisorCard} key={supervisor.id}>
                      <div className={styles.externalSupervisorTitle}>
                        <div>
                          <h3>{supervisor.name}</h3>
                          <span className={styles.externalSupervisorCategory}>
                            Especialista em {supervisor.primaryTerm}
                          </span>
                        </div>
                        <span className={styles.externalSupervisorExperience}>
                          {supervisor.yearsOfExperience}{" "}
                          {supervisor.yearsOfExperience === 1 ? "ano" : "anos"} de experiência
                        </span>
                      </div>
                      <dl className={styles.externalSupervisorExpertise}>
                        <div>
                          <dt>Especialidade(s)</dt>
                          <dd>{supervisor.specialties.join(", ")}</dd>
                        </div>
                        <div>
                          <dt>Áreas de foco</dt>
                          <dd>{supervisor.focusAreas.join(", ") || "Não informado"}</dd>
                        </div>
                        {supervisor.approaches.length > 0 && (
                          <div>
                            <dt>Abordagem(ns)</dt>
                            <dd>{supervisor.approaches.join(", ")}</dd>
                          </div>
                        )}
                      </dl>
                      <div className={styles.externalSupervisorContact}>
                        <span>Cidade: {supervisor.city}</span>
                        <a href={"mailto:" + supervisor.email}>{supervisor.email}</a>
                        <a href={"tel:" + supervisor.phone.replace(/[^\d+]/g, "")}>
                          {supervisor.phone}
                        </a>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className={styles.externalSupervisorsEmpty} role="status">
                Nenhum supervisor encontrado para “{query}”. Tente outra especialidade, área de foco ou abordagem.
              </p>
            )
          ) : (
            <p className={styles.externalSupervisorsEmpty}>
              Digite ou selecione uma especialidade, área de foco ou abordagem para buscar supervisores.
            </p>
          )}
      </div>
    </section>
  );
}
