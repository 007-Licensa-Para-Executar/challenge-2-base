"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PatientDashboard from "./PatientDashboard";
import PatientHistory from "./PatientHistory";
import PatientList from "./PatientList";
import PatientChatbot from "./PatientChatbot";
import PatientProfileEditor from "./PatientProfileEditor";
import ExternalSupervisors from "./ExternalSupervisors";
import ReportUpload from "./ReportUpload";
import PsychologistProfileEditor, {
  getPsychologistInitials,
  type PsychologistProfile,
} from "./PsychologistProfileEditor";
import type {
  EditablePatientProfile,
  PatientHistoryItem,
  PortalPatient,
  PortalPatientRecord,
  ThemeDistribution,
  UploadedReport,
} from "./types";
import { DASHBOARD_THEMES } from "./types";
import styles from "./patient-management.module.css";

const patientUpdateKey = "meu-diario:cadastro-atualizado";
const defaultPsychologistProfile: PsychologistProfile = {
  name: "Dra. Marina",
  age: null,
  profession: "Psicóloga",
  specialty: "",
  insurancePlans: "",
  resume: "",
  professionalExperiences: "",
  experienceYears: null,
  photoUrl: null,
  updatedAt: 0,
};

function formatRegistrationDate(date: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(date));
}

function isPortalPatientRecord(value: unknown): value is PortalPatientRecord {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;

  return (
    typeof record.id === "string" &&
    typeof record.name === "string" &&
    typeof record.email === "string" &&
    typeof record.createdAt === "string" &&
    !Number.isNaN(Date.parse(record.createdAt)) &&
    typeof record.address === "string" &&
    (record.age === null ||
      (typeof record.age === "number" && Number.isSafeInteger(record.age) && record.age >= 0)) &&
    (record.treatmentDurationMonths === null ||
      (typeof record.treatmentDurationMonths === "number" &&
        Number.isSafeInteger(record.treatmentDurationMonths) && record.treatmentDurationMonths >= 0)) &&
    typeof record.psychiatricTreatment === "boolean"
  );
}

function getPatientInitials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const initials = words.length > 1
    ? `${words[0][0]}${words[words.length - 1][0]}`
    : words[0]?.slice(0, 2) || "P";
  return initials.toLocaleUpperCase("pt-BR");
}

function formatTreatmentDuration(months: number | null) {
  if (months === null) return "Não informado";
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  const parts = [
    years ? `${years} ${years === 1 ? "ano" : "anos"}` : "",
    remainingMonths ? `${remainingMonths} ${remainingMonths === 1 ? "mês" : "meses"}` : "",
  ].filter(Boolean);
  return parts.join(" e ") || "0 meses";
}

function toPortalPatient(record: PortalPatientRecord): PortalPatient {
  const nameParts = record.name.trim().split(/\s+/).filter(Boolean);
  const initials = nameParts.length > 1
    ? `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`
    : nameParts[0]?.slice(0, 2) || "P";
  const themeDistribution = Object.fromEntries(
    DASHBOARD_THEMES.map((theme) => [theme, 0]),
  ) as ThemeDistribution;

  return {
    id: record.id,
    portalUserId: record.id,
    fullName: record.name,
    email: record.email,
    address: record.address,
    age: record.age,
    treatmentDurationMonths: record.treatmentDurationMonths,
    psychiatricTreatment: record.psychiatricTreatment,
    initials: initials.toLocaleUpperCase("pt-BR"),
    registeredAt: record.createdAt,
    source: "portal_cadastro",
    linkStatus: "aguardando_vinculo",
    psychologistId: null,
    reports: [],
    history: [],
    weeklyDiaryCounts: [],
    themeDistribution,
  };
}

// A lista vem do mesmo banco que recebe os cadastros do portal.
export default function PatientManagement() {
  const [patients, setPatients] = useState<PortalPatient[]>([]);
  const [psychologistProfile, setPsychologistProfile] = useState(defaultPsychologistProfile);
  const [isProfileEditorOpen, setIsProfileEditorOpen] = useState(false);
  const [isPatientProfileEditorOpen, setIsPatientProfileEditorOpen] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const uploadTimers = useRef<Map<string, number>>(new Map());
  const selectedPatient = patients.find((patient) => patient.id === selectedPatientId) ?? null;
  const professionalSummaryFacts = [
    psychologistProfile.age !== null ? `${psychologistProfile.age} anos` : "",
    psychologistProfile.specialty,
    psychologistProfile.experienceYears !== null
      ? `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(psychologistProfile.experienceYears)} anos de experiência`
      : "",
  ].filter(Boolean);
  const hasProfessionalSummary = Boolean(
    professionalSummaryFacts.length || psychologistProfile.insurancePlans || psychologistProfile.resume || psychologistProfile.professionalExperiences,
  );

  useEffect(() => {
    let isMounted = true;

    async function refreshPsychologistProfile() {
      try {
        const response = await fetch("/api/psicologa/perfil", { cache: "no-store" });
        if (!response.ok) throw new Error("Não foi possível carregar o perfil profissional.");
        const payload = await response.json();
        if (isMounted && payload?.profile) setPsychologistProfile(payload.profile);
      } catch (error) {
        console.error("Falha ao carregar o perfil profissional:", error);
      }
    }

    void refreshPsychologistProfile();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      uploadTimers.current.forEach((timer) => window.clearInterval(timer));
      uploadTimers.current.clear();
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    let requestInProgress = false;

    async function refreshPatients(showLoading = false) {
      if (requestInProgress) return;
      requestInProgress = true;
      if (showLoading) setIsLoading(true);

      try {
        const response = await fetch("/api/psicologa/pacientes", { cache: "no-store" });
        if (!response.ok) throw new Error("Não foi possível carregar os pacientes do portal.");

        const payload: unknown = await response.json();
        if (
          typeof payload !== "object" ||
          payload === null ||
          !("patients" in payload) ||
          !Array.isArray(payload.patients) ||
          !payload.patients.every(isPortalPatientRecord)
        ) {
          throw new Error("A resposta da lista de pacientes está inválida.");
        }

        const portalPatients = payload.patients.map(toPortalPatient);
        if (!isMounted) return;

        // Mantém os relatórios locais já enviados enquanto atualiza os cadastros do portal.
        setPatients((currentPatients) =>
          portalPatients.map((newPatient) => {
            const previousPatient = currentPatients.find((patient) => patient.id === newPatient.id);
            return previousPatient
              ? {
                  ...newPatient,
                  linkStatus: previousPatient.linkStatus,
                  psychologistId: previousPatient.psychologistId,
                  reports: previousPatient.reports,
                  history: previousPatient.history,
                  weeklyDiaryCounts: previousPatient.weeklyDiaryCounts,
                  themeDistribution: previousPatient.themeDistribution,
                }
              : newPatient;
          }),
        );
        setSelectedPatientId((currentId) =>
          portalPatients.some((patient) => patient.id === currentId)
            ? currentId
            : portalPatients[0]?.id ?? "",
        );
        setLoadError("");
      } catch (error) {
        if (isMounted) {
          setLoadError(error instanceof Error ? error.message : "Não foi possível atualizar a lista.");
        }
      } finally {
        requestInProgress = false;
        if (isMounted) setIsLoading(false);
      }
    }

    const refreshNow = () => void refreshPatients();
    const handleStorage = (event: StorageEvent) => {
      if (event.key === patientUpdateKey) refreshNow();
    };
    const handleVisibility = () => {
      if (document.visibilityState === "visible") refreshNow();
    };

    void refreshPatients(true);
    const interval = window.setInterval(refreshNow, 5000);
    window.addEventListener("storage", handleStorage);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      isMounted = false;
      window.clearInterval(interval);
      window.removeEventListener("storage", handleStorage);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [retryCount]);

  function handleReportUpload(file: File) {
    if (!selectedPatient) return;

    const patientId = selectedPatient.id;
    const reportId = `relatorio-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const uploadedAt = new Date().toISOString();
    let progress = 0;

    const newReport: UploadedReport = {
      id: reportId,
      fileName: file.name,
      uploadedAt,
      status: "enviando",
      progress,
    };

    setPatients((currentPatients) =>
      currentPatients.map((patient) =>
        patient.id === patientId
          ? { ...patient, reports: [newReport, ...patient.reports] }
          : patient,
      ),
    );

    const timer = window.setInterval(() => {
      progress = Math.min(progress + 20, 100);

      setPatients((currentPatients) =>
        currentPatients.map((patient) =>
          patient.id === patientId
            ? {
                ...patient,
                reports: patient.reports.map((report) =>
                  report.id === reportId ? { ...report, progress } : report,
                ),
              }
            : patient,
        ),
      );

      if (progress === 100) {
        window.clearInterval(timer);
        uploadTimers.current.delete(reportId);

        const historyItem: PatientHistoryItem = {
          id: `evento-${reportId}`,
          type: "relatorio",
          title: file.name,
          description: "Relatório pós-consulta enviado.",
          date: uploadedAt,
          reportId,
        };

        setPatients((currentPatients) =>
          currentPatients.map((patient) => {
            if (patient.id !== patientId || !patient.reports.some((report) => report.id === reportId)) {
              return patient;
            }

            return {
              ...patient,
              reports: patient.reports.map((report) =>
                report.id === reportId ? { ...report, status: "concluido", progress: 100 } : report,
              ),
              history: [historyItem, ...patient.history],
            };
          }),
        );
      }
    }, 180);

    uploadTimers.current.set(reportId, timer);
  }

  function handleReportRemove(reportId: string) {
    const timer = uploadTimers.current.get(reportId);
    if (timer !== undefined) {
      window.clearInterval(timer);
      uploadTimers.current.delete(reportId);
    }

    if (!selectedPatient) return;

    setPatients((currentPatients) =>
      currentPatients.map((patient) =>
        patient.id === selectedPatient.id
          ? {
              ...patient,
              reports: patient.reports.filter((report) => report.id !== reportId),
              history: patient.history.filter((item) => item.reportId !== reportId),
            }
          : patient,
      ),
    );
  }

  function handlePatientProfileSave(updatedProfile: EditablePatientProfile) {
    setPatients((currentPatients) =>
      currentPatients.map((patient) =>
        patient.id === updatedProfile.id
          ? {
              ...patient,
              fullName: updatedProfile.name,
              initials: getPatientInitials(updatedProfile.name),
              address: updatedProfile.address,
              age: updatedProfile.age,
              treatmentDurationMonths: updatedProfile.treatmentDurationMonths,
              psychiatricTreatment: updatedProfile.psychiatricTreatment,
            }
          : patient,
      ),
    );
  }

  return (
    <div className={styles.workspace}>
      <PatientList
        patients={patients}
        selectedPatientId={selectedPatientId}
        searchTerm={searchTerm}
        isLoading={isLoading}
        loadError={loadError}
        onRetry={() => setRetryCount((count) => count + 1)}
        onSearchChange={setSearchTerm}
        onSelectPatient={setSelectedPatientId}
      />

      <main className={styles.mainContent}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.eyebrow}>MEU DIÁRIO · PAINEL PROFISSIONAL</p>
            <h1>Gestão de pacientes</h1>
            <p>Acompanhe registros e relatórios em um só lugar.</p>
          </div>
          <div className={styles.professionalBadge}>
            <button
              className={styles.professionalProfileButton}
              type="button"
              aria-haspopup="dialog"
              aria-label={`Editar perfil de ${psychologistProfile.name}`}
              onClick={() => setIsProfileEditorOpen(true)}
            >
              {psychologistProfile.photoUrl ? (
                <img className={styles.professionalAvatar} src={psychologistProfile.photoUrl} alt="" />
              ) : (
                <span className={styles.professionalAvatar} aria-hidden="true">
                  {getPsychologistInitials(psychologistProfile.name)}
                </span>
              )}
              <span>
                <strong>{psychologistProfile.name}</strong>
                <small>{psychologistProfile.profession || "Profissional"}</small>
              </span>
            </button>
          </div>
          <Link className={styles.impactBenchLink} href="/psicologa/impactbench">
            Painel clínico
          </Link>
        </header>

        <PsychologistProfileEditor
          open={isProfileEditorOpen}
          profile={psychologistProfile}
          onClose={() => setIsProfileEditorOpen(false)}
          onSave={setPsychologistProfile}
        />

        {hasProfessionalSummary ? (
          <section className={`${styles.card} ${styles.professionalSummary}`} aria-labelledby="professional-summary-title">
            <div className={styles.professionalSummaryHeading}>
              <h2 id="professional-summary-title">Perfil profissional</h2>
              <button type="button" onClick={() => setIsProfileEditorOpen(true)}>
                Editar perfil
              </button>
            </div>
            {professionalSummaryFacts.length ? (
              <ul className={styles.professionalSummaryFacts}>
                {professionalSummaryFacts.map((fact) => <li key={fact}>{fact}</li>)}
              </ul>
            ) : null}
            {psychologistProfile.insurancePlans || psychologistProfile.resume || psychologistProfile.professionalExperiences ? (
              <div className={styles.professionalSummarySections}>
                {psychologistProfile.insurancePlans ? (
                  <div>
                    <h3>Convênios atendidos</h3>
                    <p>{psychologistProfile.insurancePlans}</p>
                  </div>
                ) : null}
                {psychologistProfile.resume ? (
                  <div>
                    <h3>Currículo</h3>
                    <p>{psychologistProfile.resume}</p>
                  </div>
                ) : null}
                {psychologistProfile.professionalExperiences ? (
                  <div>
                    <h3>Experiências profissionais</h3>
                    <p>{psychologistProfile.professionalExperiences}</p>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        {selectedPatient ? (
          <>
            <PatientProfileEditor
              open={isPatientProfileEditorOpen}
              patient={selectedPatient}
              onClose={() => setIsPatientProfileEditorOpen(false)}
              onSave={handlePatientProfileSave}
            />
            <section className={styles.patientProfile} aria-labelledby="patient-name">
              <div className={styles.patientProfileHeader}>
                <span className={styles.largeAvatar} aria-hidden="true">{selectedPatient.initials}</span>
                <div className={styles.profileDetails}>
                  <div className={styles.profileTitleRow}>
                    <h2 id="patient-name">{selectedPatient.fullName}</h2>
                    <span
                      className={`${styles.profileStatus} ${selectedPatient.linkStatus === "vinculado" ? styles.linked : styles.pending}`}
                    >
                      <span className={styles.statusDot} aria-hidden="true" />
                      {selectedPatient.linkStatus === "vinculado" ? "Vinculado" : "Aguardando vínculo"}
                    </span>
                  </div>
                  <p>{selectedPatient.email}</p>
                  <p className={styles.registeredDate}>
                    Cadastro pelo portal em {formatRegistrationDate(selectedPatient.registeredAt)}
                  </p>
                </div>
                <div className={styles.patientProfileHeaderActions}>
                  <button
                    className={styles.editPatientProfileButton}
                    type="button"
                    aria-haspopup="dialog"
                    onClick={() => setIsPatientProfileEditorOpen(true)}
                  >
                    Editar perfil
                  </button>
                  <ExternalSupervisors
                    key={selectedPatient.id}
                    patientId={selectedPatient.id}
                    patientName={selectedPatient.fullName}
                  />
                </div>
              </div>
              <h3 className={styles.patientCareHeading}>Dados do paciente</h3>
              <dl className={styles.patientCareGrid}>
                <div className={styles.patientAddress}>
                  <dt>Endereço</dt>
                  <dd>{selectedPatient.address || "Não informado"}</dd>
                </div>
                <div>
                  <dt>Idade</dt>
                  <dd>{selectedPatient.age === null ? "Não informada" : `${selectedPatient.age} anos`}</dd>
                </div>
                <div>
                  <dt>Tempo de tratamento comigo</dt>
                  <dd>{formatTreatmentDuration(selectedPatient.treatmentDurationMonths)}</dd>
                </div>
                <div>
                  <dt>Acompanhamento psiquiátrico</dt>
                  <dd>{selectedPatient.psychiatricTreatment ? "Sim" : "Não"}</dd>
                </div>
              </dl>
            </section>

            <PatientDashboard patient={selectedPatient} />

            <div className={styles.recordsGrid}>
              <ReportUpload
                key={selectedPatient.id}
                reports={selectedPatient.reports}
                onUpload={handleReportUpload}
                onRemove={handleReportRemove}
              />
              <PatientHistory history={selectedPatient.history} />
            </div>
            <PatientChatbot
              key={selectedPatient.id}
              patientId={selectedPatient.id}
              patientName={selectedPatient.fullName}
            />
          </>
        ) : (
          <section className={`${styles.card} ${styles.noPatient}`} aria-live="polite">
            <h2>{isLoading ? "Carregando pacientes" : "Nenhum paciente cadastrado"}</h2>
            <p>
              {isLoading
                ? "Buscando os cadastros criados pelo portal."
                : "Quando alguém criar um acesso em /cadastro, o cadastro aparecerá nesta lista."}
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
