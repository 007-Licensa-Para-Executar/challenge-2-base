"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import DrillDownPanel from "./DrillDownPanel";
import ImpactBenchSunburst from "./ImpactBenchSunburst";
import { CopilotRagView, TimelineAndReportsView } from "./SecondaryViews";
import { buildSunburstGeometry } from "./wheelMath";
import styles from "./impactbench.module.css";

const CADASTRO_SYNC_KEY = "meu-diario:cadastro-atualizado";

export default function PsychologistWorkspace() {
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [sidebarTab, setSidebarTab] = useState("all"); // all | risk

  const [activeNav, setActiveNav] = useState("explore"); // explore | timeline | rag
  const [days, setDays] = useState("all"); // all | 7 | 14 | 30
  const [valenceFilter, setValenceFilter] = useState("all"); // all | negative | positive
  const [mobilePanel, setMobilePanel] = useState("wheel"); // patients | wheel | details

  const [patientData, setPatientData] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Seleção hierárquica ImpactBench (Anel 1 -> Anel 2 -> Ocorrência 4ª coluna)
  const [selectedThemeId, setSelectedThemeId] = useState(null);
  const [selectedSubtopicKey, setSelectedSubtopicKey] = useState(null);
  const [selectedOccurrence, setSelectedOccurrence] = useState(null);

  const loadPatients = useCallback(async (selectFallback = true) => {
    try {
      const res = await fetch("/api/psicologa/pacientes", { cache: "no-store" });
      if (!res.ok) throw new Error("Não foi possível carregar os pacientes.");
      const data = await res.json();
      const list = Array.isArray(data.patients) ? data.patients : [];
      setPatients(list);
      if (selectFallback) {
        setSelectedPatientId((prev) => {
          if (prev && list.some((p) => p.id === prev)) return prev;
          // Prioriza paciente real com entradas se existir, caso contrário o primeiro cadastrado
          const withEntries = list.find((p) => !p.isDemo && p.entryCount > 0);
          return withEntries?.id || list[0]?.id || "";
        });
      }
      setErrorMsg("");
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadPatientDetail = useCallback(
    async (pid, daysVal, valenceVal) => {
      if (!pid) return;
      setLoadingDetail(true);
      setErrorMsg("");
      try {
        const params = new URLSearchParams({ days: daysVal, valence: valenceVal });
        const res = await fetch(`/api/psicologa/paciente/${encodeURIComponent(pid)}?${params}`, {
          cache: "no-store",
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || "Falha ao carregar dados do paciente.");
        setPatientData(data);
      } catch (err) {
        setErrorMsg(err.message);
      } finally {
        setLoadingDetail(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadPatients(true);
    const onStorage = (e) => {
      if (e.key === CADASTRO_SYNC_KEY) void loadPatients(false);
    };
    const interval = window.setInterval(() => void loadPatients(false), 15000);
    window.addEventListener("storage", onStorage);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("storage", onStorage);
    };
  }, [loadPatients]);

  useEffect(() => {
    if (!selectedPatientId) return;
    setSelectedThemeId(null);
    setSelectedSubtopicKey(null);
    setSelectedOccurrence(null);
    void loadPatientDetail(selectedPatientId, days, valenceFilter);
  }, [selectedPatientId, days, valenceFilter, loadPatientDetail]);

  const geometry = useMemo(() => {
    return buildSunburstGeometry(patientData?.wheel, patientData?.entries || []);
  }, [patientData]);

  const visiblePatients = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return patients.filter((p) => {
      if (sidebarTab === "risk" && !(p.riskCount > 0 || p.valenceBreakdown?.negative > 0)) {
        return false;
      }
      if (!q) return true;
      return (
        p.name.toLowerCase().includes(q) ||
        p.email.toLowerCase().includes(q)
      );
    });
  }, [patients, searchTerm, sidebarTab]);

  const selectedPatientSummary =
    patients.find((p) => p.id === selectedPatientId) || patientData?.patient || null;

  async function handleReprocess(useOllama) {
    if (!selectedPatientId || selectedPatientSummary?.isDemo) return;
    setReprocessing(true);
    setErrorMsg("");
    try {
      const res = await fetch(
        `/api/psicologa/paciente/${encodeURIComponent(selectedPatientId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "reprocess",
            useOllama,
            days,
            valence: valenceFilter,
          }),
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Falha ao reprocessar relatos.");
      setPatientData(data);
      void loadPatients(false);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setReprocessing(false);
    }
  }

  async function handleSaveAnnotation({ macroTema, originalName, displayName, clinicalNote }) {
    if (!selectedPatientId) return;
    const res = await fetch(`/api/psicologa/paciente/${encodeURIComponent(selectedPatientId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "annotate_subtopic",
        macroTema,
        originalName,
        displayName,
        clinicalNote,
        days,
        valence: valenceFilter,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Erro ao salvar anotação.");
    setPatientData(data);
  }

  async function handleUploadReport(file) {
    if (!selectedPatientId) return;
    const res = await fetch(`/api/psicologa/paciente/${encodeURIComponent(selectedPatientId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "add_report",
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
      }),
    });
    if (res.ok) {
      await loadPatientDetail(selectedPatientId, days, valenceFilter);
    }
  }

  async function handleRemoveReport(reportId) {
    if (!selectedPatientId) return;
    const res = await fetch(`/api/psicologa/paciente/${encodeURIComponent(selectedPatientId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "remove_report", reportId }),
    });
    if (res.ok) {
      await loadPatientDetail(selectedPatientId, days, valenceFilter);
    }
  }

  function handleSelectTheme(macroId) {
    setSelectedThemeId(macroId);
    setSelectedSubtopicKey(null);
    setSelectedOccurrence(null);
    setMobilePanel("details");
  }

  function handleSelectSubtopic(macroId, subKey) {
    setSelectedThemeId(macroId);
    setSelectedSubtopicKey(subKey);
    setSelectedOccurrence(null);
    setMobilePanel("details");
  }

  function handleResetWheelSelection() {
    setSelectedThemeId(null);
    setSelectedSubtopicKey(null);
    setSelectedOccurrence(null);
  }

  return (
    <div className={styles.appShell}>
      {/* BARRA SUPERIOR PADRÃO IMPACTBENCH */}
      <header className={styles.topNavbar}>
        <div className={styles.navLeft}>
          <Link href="/" className={styles.navBrand}>
            <span className={styles.navBrandMark} aria-hidden="true">
              <svg viewBox="0 0 32 32" fill="none">
                <path d="M16 26V13m0 6c-5.5 0-8-3.5-8-8 5.5 0 8 3.5 8 8Zm0-4c0-5.1 3.1-8 8-8 0 5.6-2.8 8-8 8Z" />
              </svg>
            </span>
            <span>meu diário</span>
          </Link>

          <nav className={styles.navLinks} aria-label="Navegação do painel clínico">
            <button
              type="button"
              className={activeNav === "explore" ? styles.navTabActive : styles.navTab}
              onClick={() => setActiveNav("explore")}
            >
              Explorar Roda
            </button>
            <button
              type="button"
              className={activeNav === "timeline" ? styles.navTabActive : styles.navTab}
              onClick={() => setActiveNav("timeline")}
            >
              Linha do Tempo & Relatórios
            </button>
            <button
              type="button"
              className={activeNav === "rag" ? styles.navTabActive : styles.navTab}
              onClick={() => setActiveNav("rag")}
            >
              Copiloto RAG
            </button>
            <Link href="/diario" className={styles.navSecondaryLink}>
              Diário do Paciente ↗
            </Link>
          </nav>
        </div>

        <div className={styles.navRight}>
          <label className={styles.periodSelectLabel}>
            Período:
            <select
              aria-label="Janela temporal dos dados"
              value={days}
              onChange={(e) => setDays(e.target.value)}
            >
              <option value="all">Todo o histórico</option>
              <option value="7">Últimos 7 dias</option>
              <option value="14">Últimos 14 dias</option>
              <option value="30">Últimos 30 dias</option>
            </select>
          </label>

          {selectedPatientSummary && !selectedPatientSummary.isDemo && (
            <button
              type="button"
              className={styles.reprocessBtn}
              disabled={reprocessing || (patientData?.totalEntriesAllPeriods || 0) === 0}
              onClick={() => handleReprocess(true)}
              title="Executa Rede Neural + Agente 1 via Ollama nos relatos do paciente"
            >
              {reprocessing ? "Analisando IA..." : "Reprocessar Agente 1"}
            </button>
          )}

          <span className={styles.prototypeBadge}>Protótipo · Não é diagnóstico</span>

          <div className={styles.profChip}>
            <span className={styles.profAvatar} aria-hidden="true">DM</span>
            <span>Dra. Marina</span>
          </div>
        </div>
      </header>

      {errorMsg && (
        <div className={styles.errorBanner} role="alert">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg("")}>Fechar</button>
        </div>
      )}

      {/* CORPO PRINCIPAL ESTILO IMPACTBENCH /EXPLORE */}
      <div className={styles.exploreLayout}>
        {/* BARRA MÓVEL DE ABAS (< 1024PX) */}
        {activeNav === "explore" && (
          <div className={styles.mobileViewTabs}>
            <button
              type="button"
              className={mobilePanel === "patients" ? styles.mobileTabActive : ""}
              onClick={() => setMobilePanel("patients")}
            >
              Pacientes ({visiblePatients.length})
            </button>
            <button
              type="button"
              className={mobilePanel === "wheel" ? styles.mobileTabActive : ""}
              onClick={() => setMobilePanel("wheel")}
            >
              Roda IA
            </button>
            <button
              type="button"
              className={mobilePanel === "details" ? styles.mobileTabActive : ""}
              onClick={() => setMobilePanel("details")}
            >
              Detalhes
            </button>
          </div>
        )}

        {/* COLUNA 1: SIDEBAR DE PACIENTES */}
        <aside
          className={`${styles.leftSidebar} ${
            activeNav === "explore" && mobilePanel !== "patients" ? styles.mobileHidden : ""
          }`}
          aria-label="Lista de pacientes"
        >
          <div className={styles.sidebarIntro}>
            <h1>Pacientes</h1>
            <p>
              Selecione um paciente para explorar temas (Rede Neural) e subtemas (Agente 1).
            </p>
          </div>

          <div className={styles.sidebarSearch}>
            <input
              type="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar paciente ou e-mail..."
              aria-label="Buscar paciente"
            />
          </div>

          <div className={styles.sidebarTabs} role="tablist" aria-label="Filtrar lista de pacientes">
            <button
              type="button"
              role="tab"
              aria-selected={sidebarTab === "all"}
              className={sidebarTab === "all" ? styles.sidebarTabActive : styles.sidebarTab}
              onClick={() => setSidebarTab("all")}
            >
              Todos ({patients.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={sidebarTab === "risk"}
              className={sidebarTab === "risk" ? styles.sidebarTabActive : styles.sidebarTab}
              onClick={() => setSidebarTab("risk")}
            >
              Com alerta
            </button>
          </div>

          <div className={styles.patientScrollList}>
            {loadingList && patients.length === 0 ? (
              <p className={styles.emptySidebarMsg}>Carregando pacientes…</p>
            ) : visiblePatients.length === 0 ? (
              <p className={styles.emptySidebarMsg}>Nenhum paciente neste filtro.</p>
            ) : (
              visiblePatients.map((p) => {
                const isSelected = p.id === selectedPatientId;
                const val = p.valenceBreakdown || { positive: 0, neutral: 0, negative: 0 };
                const total = Math.max(1, val.positive + val.neutral + val.negative);
                const negW = p.entryCount > 0 ? (val.negative / total) * 100 : 0;
                const neuW = p.entryCount > 0 ? (val.neutral / total) * 100 : 100;
                const posW = p.entryCount > 0 ? (val.positive / total) * 100 : 0;

                return (
                  <button
                    key={p.id}
                    type="button"
                    aria-pressed={isSelected}
                    className={`${styles.patientCard} ${isSelected ? styles.patientCardSelected : ""}`}
                    onClick={() => {
                      setSelectedPatientId(p.id);
                      setMobilePanel("wheel");
                    }}
                  >
                    <div className={styles.patientCardTop}>
                      <span className={styles.patientCardName}>{p.name}</span>
                      {p.isDemo ? (
                        <span className={styles.demoChip}>DEMO</span>
                      ) : p.riskCount > 0 ? (
                        <span className={styles.alertChip} title="Registros com alerta">
                          {p.riskCount} alerta
                        </span>
                      ) : null}
                    </div>
                    <span className={styles.patientCardSub}>
                      {p.entryCount} {p.entryCount === 1 ? "relato" : "relatos"} · {p.email}
                    </span>
                    <div className={styles.patientCardBar} aria-hidden="true">
                      <span style={{ width: `${negW}%`, background: "#ef4444" }} />
                      <span style={{ width: `${neuW}%`, background: p.entryCount > 0 ? "#cbd5e1" : "#e5e7eb" }} />
                      <span style={{ width: `${posW}%`, background: "#22c55e" }} />
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        {/* ÁREA CENTRAL + PAINEL DIREITO */}
        {activeNav === "explore" && (
          <div className={styles.exploreContentArea}>
            <div
              className={`${styles.centerColumnWrap} ${
                mobilePanel !== "wheel" ? styles.mobileHidden : ""
              }`}
            >
              {loadingDetail && !patientData ? (
                <div className={styles.loadingStage} role="status">
                  <div className={styles.spinner} />
                  <p>Executando Rede Neural e Agente 1 sobre os relatos…</p>
                </div>
              ) : (
                <ImpactBenchSunburst
                  geometry={geometry}
                  selectedThemeId={selectedThemeId}
                  selectedSubtopicKey={selectedSubtopicKey}
                  valenceFilter={valenceFilter}
                  totalSubtemas={patientData?.wheel?.total_subtemas_ativos || 0}
                  maxSubtemas={24}
                  isDemo={Boolean(selectedPatientSummary?.isDemo)}
                  onSelectTheme={handleSelectTheme}
                  onSelectSubtopic={handleSelectSubtopic}
                  onResetSelection={handleResetWheelSelection}
                  onChangeValenceFilter={setValenceFilter}
                />
              )}
            </div>

            <div
              className={`${styles.rightColumnWrap} ${
                mobilePanel !== "details" ? styles.mobileHidden : ""
              }`}
            >
              <DrillDownPanel
                patient={selectedPatientSummary}
                geometry={geometry}
                wheel={patientData?.wheel}
                longitudinal={patientData?.longitudinal}
                selectedThemeId={selectedThemeId}
                selectedSubtopicKey={selectedSubtopicKey}
                selectedOccurrence={selectedOccurrence}
                isDemo={Boolean(selectedPatientSummary?.isDemo)}
                days={days}
                onSelectTheme={handleSelectTheme}
                onSelectSubtopic={handleSelectSubtopic}
                onSelectOccurrence={setSelectedOccurrence}
                onResetSelection={handleResetWheelSelection}
                onSaveAnnotation={handleSaveAnnotation}
              />
            </div>
          </div>
        )}

        {activeNav === "timeline" && (
          <main className={styles.secondaryMain}>
            <TimelineAndReportsView
              patient={selectedPatientSummary}
              entries={patientData?.entries || []}
              reports={patientData?.reports || []}
              longitudinal={patientData?.longitudinal}
              days={days}
              onUploadReport={handleUploadReport}
              onRemoveReport={handleRemoveReport}
            />
          </main>
        )}

        {activeNav === "rag" && (
          <main className={styles.secondaryMain}>
            <CopilotRagView patient={selectedPatientSummary} days={days} />
          </main>
        )}
      </div>
    </div>
  );
}
