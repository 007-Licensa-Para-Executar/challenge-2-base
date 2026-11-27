"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import DrillDownPanel from "./DrillDownPanel";
import ImpactBenchSunburst from "./ImpactBenchSunburst";
import { CopilotRagView, TimelineAndReportsView } from "./SecondaryViews";
import { buildSunburstGeometry } from "./wheelMath";
import styles from "./impactbench.module.css";

const CADASTRO_SYNC_KEY = "meu-diario:cadastro-atualizado";

export default function PsychologistWorkspace({ activeNav, selectedPatientId }) {
  const [patients, setPatients] = useState([]);
  const [days, setDays] = useState("all"); // all | 7 | 14 | 30
  const [valenceFilter, setValenceFilter] = useState("all"); // all | negative | positive

  const [patientData, setPatientData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Seleção hierárquica ImpactBench (Anel 1 -> Anel 2 -> Ocorrência 4ª coluna)
  const [selectedThemeId, setSelectedThemeId] = useState(null);
  const [selectedSubtopicKey, setSelectedSubtopicKey] = useState(null);
  const [selectedOccurrence, setSelectedOccurrence] = useState(null);

  const loadPatients = useCallback(async () => {
    try {
      const res = await fetch("/api/psicologa/pacientes?includeDemo=true", { cache: "no-store" });
      if (!res.ok) throw new Error("Não foi possível carregar os pacientes.");
      const data = await res.json();
      const list = Array.isArray(data.patients) ? data.patients : [];
      setPatients(list);
      setErrorMsg("");
    } catch (err) {
      setErrorMsg(err.message);
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
    void loadPatients();
    const onStorage = (e) => {
      if (e.key === CADASTRO_SYNC_KEY) void loadPatients();
    };
    const interval = window.setInterval(() => void loadPatients(), 15000);
    window.addEventListener("storage", onStorage);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("storage", onStorage);
    };
  }, [loadPatients]);

  useEffect(() => {
    if (!selectedPatientId) return;
    setPatientData(null);
    setSelectedThemeId(null);
    setSelectedSubtopicKey(null);
    setSelectedOccurrence(null);
    void loadPatientDetail(selectedPatientId, days, valenceFilter);
  }, [selectedPatientId, days, valenceFilter, loadPatientDetail]);

  const geometry = useMemo(() => {
    return buildSunburstGeometry(patientData?.wheel, patientData?.entries || []);
  }, [patientData]);

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
      void loadPatients();
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
  }

  function handleSelectSubtopic(macroId, subKey) {
    setSelectedThemeId(macroId);
    setSelectedSubtopicKey(subKey);
    setSelectedOccurrence(null);
  }

  function handleResetWheelSelection() {
    setSelectedThemeId(null);
    setSelectedSubtopicKey(null);
    setSelectedOccurrence(null);
  }

  return (
    <div className={`${styles.appShell} ${styles.embeddedShell}`}>
      <div className={styles.embeddedToolbar}>
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
      </div>

      {errorMsg && (
        <div className={styles.errorBanner} role="alert">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg("")}>Fechar</button>
        </div>
      )}

      <div className={styles.exploreLayout}>
        {activeNav === "explore" && (
          <div className={styles.exploreContentArea}>
            <div className={styles.centerColumnWrap}>
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

            <div className={styles.rightColumnWrap}>
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
