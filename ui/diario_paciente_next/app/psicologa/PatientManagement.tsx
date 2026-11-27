"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PatientHistory from "./PatientHistory";
import PatientList from "./PatientList";
import ExternalSupervisors from "./ExternalSupervisors";
import ReportUpload from "./ReportUpload";
import PsychologistWorkspace from "./PsychologistWorkspace";
import PsychologistProfileEditor, {
  getPsychologistInitials,
  type PsychologistProfile,
} from "./PsychologistProfileEditor";
import type {
  PatientHistoryItem,
  PortalPatient,
  PortalPatientRecord,
  ThemeDistribution,
  UploadedReport,
} from "./types";
import { DASHBOARD_THEMES } from "./types";
import styles from "./patient-management.module.css";

const patientUpdateKey = "meu-diario:cadastro-atualizado";
const sections = [
  { id: "gestao", label: "Gestão de pacientes" },
  { id: "explorar", label: "Explorar Roda" },
  { id: "timeline", label: "Linha do Tempo & Relatórios" },
  { id: "rag", label: "Copiloto RAG" },
] as const;
type SectionId = (typeof sections)[number]["id"];
const sectionIds = new Set<string>(sections.map((section) => section.id));

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
    (record.isDemo === undefined || typeof record.isDemo === "boolean") &&
    (record.age === null ||
      (typeof record.age === "number" && Number.isSafeInteger(record.age) && record.age >= 0)) &&
    (record.treatmentDurationMonths === null ||
      (typeof record.treatmentDurationMonths === "number" &&
        Number.isSafeInteger(record.treatmentDurationMonths) && record.treatmentDurationMonths >= 0)) &&
    typeof record.psychiatricTreatment === "boolean"
  );
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
    isDemo: record.isDemo === true,
  };
}

// A lista vem do mesmo banco que recebe os cadastros do portal.
export default function PatientManagement({ initialSection }: { initialSection?: string }) {
  const [patients, setPatients] = useState<PortalPatient[]>([]);
  const [psychologistProfile, setPsychologistProfile] = useState(defaultPsychologistProfile);
  const [isProfileEditorOpen, setIsProfileEditorOpen] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [activeSection, setActiveSection] = useState<SectionId>(
    initialSection && sectionIds.has(initialSection) ? (initialSection as SectionId) : "gestao",
  );
  const uploadTimers = useRef<Map<string, number>>(new Map());
  const selectedPatient = patients.find((patient) => patient.id === selectedPatientId) ?? null;

  useEffect(() => {
    setActiveSection(
      initialSection && sectionIds.has(initialSection) ? (initialSection as SectionId) : "gestao",
    );
  }, [initialSection]);
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
        const response = await fetch("/api/psicologa/pacientes?includeDemo=true", { cache: "no-store" });
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
    if (!selectedPatient || selectedPatient.isDemo) return;

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

    if (!selectedPatient || selectedPatient.isDemo) return;

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
          <div className={styles.pageHeaderTop}>
            <div>
              <p className={styles.eyebrow}>MEU DIÁRIO · PAINEL PROFISSIONAL</p>
              <h1>Painel profissional</h1>
              <p>Acompanhe pacientes, temas e relatórios em um só lugar.</p>
            </div>
            <div className={styles.pageHeaderActions}>
              {selectedPatient ? (
                <ExternalSupervisors
                  key={selectedPatient.id}
                  patientId={selectedPatient.id}
                  patientName={selectedPatient.fullName}
                />
              ) : null}
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
            </div>
          </div>
          <nav className={styles.sectionNav} aria-label="Seções do painel profissional">
            {sections.map((section) => (
              <Link
                key={section.id}
                className={activeSection === section.id ? styles.sectionNavLinkActive : styles.sectionNavLink}
                href={section.id === "gestao" ? "/psicologa" : `/psicologa?secao=${section.id}`}
                aria-current={activeSection === section.id ? "page" : undefined}
              >
                {section.label}
              </Link>
            ))}
            <Link className={styles.sectionNavExternal} href="/diario">
              Diário do Paciente ↗
            </Link>
          </nav>
        </header>

        <PsychologistProfileEditor
          open={isProfileEditorOpen}
          profile={psychologistProfile}
          onClose={() => setIsProfileEditorOpen(false)}
          onSave={setPsychologistProfile}
        />

        {activeSection === "gestao" && selectedPatient?.isDemo ? (
          <section className={`${styles.card} ${styles.noPatient}`}>
            <h2>Caso fictício de demonstração</h2>
            <p>
              Os diários sintéticos estão disponíveis em Explorar Roda, Linha do Tempo &amp; Relatórios e Copiloto RAG.
              Eles ficam separados do cadastro e dos registros reais do paciente.
            </p>
          </section>
        ) : activeSection === "gestao" && selectedPatient ? (
          <>
            <div className={styles.recordsGrid}>
              <ReportUpload
                key={selectedPatient.id}
                reports={selectedPatient.reports}
                onUpload={handleReportUpload}
                onRemove={handleReportRemove}
              />
              <PatientHistory history={selectedPatient.history} />
            </div>
          </>
        ) : activeSection === "gestao" ? (
          <section className={`${styles.card} ${styles.noPatient}`} aria-live="polite">
            <h2>{isLoading ? "Carregando pacientes" : "Nenhum paciente cadastrado"}</h2>
            <p>
              {isLoading
                ? "Buscando os cadastros criados pelo portal."
                : "Quando alguém criar um acesso em /cadastro, o cadastro aparecerá nesta lista."}
            </p>
          </section>
        ) : selectedPatient ? (
          <PsychologistWorkspace
            activeNav={activeSection === "explorar" ? "explore" : activeSection === "timeline" ? "timeline" : "rag"}
            selectedPatientId={selectedPatient.id}
          />
        ) : (
          <section className={`${styles.card} ${styles.noPatient}`} aria-live="polite">
            <h2>{isLoading ? "Carregando pacientes" : "Selecione um paciente"}</h2>
            <p>
              {isLoading
                ? "Buscando os cadastros criados pelo portal."
                : "Cadastre um paciente para explorar a Roda, a linha do tempo e o copiloto."}
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
