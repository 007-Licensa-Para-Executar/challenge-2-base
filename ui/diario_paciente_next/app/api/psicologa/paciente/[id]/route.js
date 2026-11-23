import { NextResponse } from "next/server";
import {
  listarAnotacoesSubtemas,
  listarDiarios,
  listarRelatoriosPaciente,
  obterPacientePorId,
  removerRelatorioPaciente,
  salvarAnaliseEntrada,
  salvarAnotacaoSubtema,
  salvarRelatorioPaciente,
} from "../../../auth/_backend.js";
import { runDashboardCli } from "../../../../lib/dashboardBridge.js";
import {
  DEMO_PATIENT_ID,
  getDemoPatientEntries,
  getDemoPatientSummary,
} from "../../../../lib/demoPatient.js";

export const runtime = "nodejs";

function parseJsonSafe(raw, fallback = null) {
  if (!raw || typeof raw !== "string") return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function periodDaysToMs(daysParam) {
  if (!daysParam || daysParam === "all") return null;
  const days = Number(daysParam);
  if (!Number.isFinite(days) || days <= 0) return null;
  return days * 86400000;
}

function filterByValence(entries, valence) {
  if (!valence || valence === "all") return entries;
  return entries.filter((entry) => {
    const score = Number(entry.polarity_score ?? entry.agent1?.score_polaridade ?? 0);
    if (valence === "negative") return Boolean(entry.is_risk_emotion) || score < -0.1;
    if (valence === "positive") return score > 0.1;
    return true;
  });
}

function enrichEntry(row) {
  const agent1 = parseJsonSafe(row.agent1_json, null);
  const themeScores = parseJsonSafe(row.theme_scores_json, null);
  return {
    id: String(row.id),
    patient_id: String(row.patient_id),
    text: String(row.text),
    primary_emotion: String(row.primary_emotion),
    character: String(row.character),
    color_hex: String(row.color_hex),
    color_secondary_hex: row.color_secondary_hex ? String(row.color_secondary_hex) : "",
    sub_emotion_name: String(row.sub_emotion_name),
    sub_emotion_symbol: String(row.sub_emotion_symbol),
    confidence: Number(row.confidence || 1.0),
    is_risk_emotion: Boolean(row.is_risk_emotion),
    input_type: String(row.input_type || "text"),
    audio_name: row.audio_name ? String(row.audio_name) : null,
    audio_duration: row.audio_duration ? String(row.audio_duration) : null,
    audio_data: row.audio_data ? String(row.audio_data) : null,
    created_at: Number(row.created_at),
    theme_macro: row.theme_macro || agent1?.macro_tema_validado || null,
    theme_confidence: Number(row.theme_confidence ?? agent1?.confianca_macro_tema ?? 0),
    theme_scores: themeScores,
    polarity_score: row.polarity_score ?? agent1?.score_polaridade ?? 0,
    analysis_source: row.analysis_source || null,
    agent1,
  };
}

function applyAnnotationsToWheel(wheel, annotations) {
  if (!wheel || !Array.isArray(wheel.macrotemas) || !annotations?.length) return wheel;
  const map = new Map(
    annotations.map((a) => [`${a.macro_tema}::${a.original_name}`, a]),
  );
  return {
    ...wheel,
    macrotemas: wheel.macrotemas.map((macro) => ({
      ...macro,
      subtemas: (macro.subtemas || []).map((sub) => {
        const ann = map.get(`${macro.macro_tema}::${sub.nome}`);
        if (!ann) return sub;
        return {
          ...sub,
          original_nome: sub.nome,
          nome: ann.display_name || sub.nome,
          clinical_note: ann.clinical_note || "",
          edited_by_psychologist: ann.display_name !== sub.nome || Boolean(ann.clinical_note),
        };
      }),
    })),
  };
}

async function buildPatientDashboardPayload(
  patientId,
  { days = "all", valence = "all", forceReprocess = false, useOllama = false, modelName = null } = {},
) {
  const isDemo = patientId === DEMO_PATIENT_ID;
  const patient = isDemo ? getDemoPatientSummary() : obterPacientePorId(patientId);
  if (!patient) return null;

  let rawEntries = isDemo ? getDemoPatientEntries() : listarDiarios(patientId);
  const reports = isDemo ? [] : listarRelatoriosPaciente(patientId);
  const annotations = isDemo ? [] : listarAnotacoesSubtemas(patientId);

  if (!isDemo && rawEntries.length > 0) {
    const needsAnalysis = forceReprocess
      ? rawEntries
      : rawEntries.filter((row) => !row.agent1_json || !row.theme_macro);

    if (needsAnalysis.length > 0) {
      const cliResult = await runDashboardCli(
        "analyze-batch",
        {
          patient_id: patientId,
          use_ollama: Boolean(useOllama),
          model_name: modelName || null,
          max_subtemas: 24,
          periodo: days === "all" ? "Todo o histórico" : `Últimos ${days} dias`,
          entries: needsAnalysis.map((r) => ({
            id: r.id,
            text: r.text,
            created_at: r.created_at,
            input_type: r.input_type || "text",
            primary_emotion: r.primary_emotion,
            is_risk_emotion: Boolean(r.is_risk_emotion),
          })),
        },
        useOllama ? 180000 : 45000,
      );

      for (const item of cliResult.analyzed_entries || []) {
        salvarAnaliseEntrada(item.entry_id, {
          themeMacro: item.macro_tema,
          themeConfidence: item.macro_confidence,
          themeScoresJson: JSON.stringify(item.theme_percentages || {}),
          polarityScore: item.polarity_score,
          agent1Json: JSON.stringify(item.agent1),
          analysisSource: item.analysis_source,
        });
      }
      rawEntries = listarDiarios(patientId);
    }
  }

  const enrichedAll = rawEntries.map(enrichEntry);
  const windowMs = periodDaysToMs(days);
  const now = Date.now();

  let currentEntries = enrichedAll;
  let previousEntries = [];
  if (windowMs !== null) {
    const currentStart = now - windowMs;
    const prevStart = currentStart - windowMs;
    currentEntries = enrichedAll.filter((e) => e.created_at >= currentStart && e.created_at <= now);
    previousEntries = enrichedAll.filter((e) => e.created_at >= prevStart && e.created_at < currentStart);
  }

  const filteredCurrent = filterByValence(currentEntries, valence);
  const filteredPrev = filterByValence(previousEntries, valence);

  const currentOutputs = filteredCurrent.map((e) => e.agent1).filter(Boolean);
  const prevOutputs = filteredPrev.map((e) => e.agent1).filter(Boolean);

  const periodoLabel = days === "all" ? "Todo o histórico" : `Últimos ${days} dias`;
  const previousLabel = days === "all" ? "Sem período anterior" : `${days} dias anteriores`;

  let wheel = {
    patient_id: patientId,
    periodo: periodoLabel,
    total_subtemas_ativos: 0,
    macrotemas: [],
    sunburst_series: { ids: [], labels: [], parents: [], values: [], colors: [], hover_texts: [] },
  };
  let longitudinal = null;

  if (currentOutputs.length > 0 || prevOutputs.length > 0) {
    const wheelData = await runDashboardCli(
      "build-wheel",
      {
        patient_id: patientId,
        current_outputs: currentOutputs,
        previous_outputs: prevOutputs,
        periodo: periodoLabel,
        previous_label: previousLabel,
        max_subtemas: 24,
      },
      20000,
    );
    wheel = applyAnnotationsToWheel(wheelData.wheel, annotations);
    longitudinal = wheelData.longitudinal || null;
  }

  const positive = filteredCurrent.filter((e) => Number(e.polarity_score) >= 0.15).length;
  const negative = filteredCurrent.filter((e) => Boolean(e.is_risk_emotion) || Number(e.polarity_score) <= -0.15).length;
  const neutral = Math.max(0, filteredCurrent.length - positive - negative);
  const riskCount = filteredCurrent.filter((e) => Boolean(e.is_risk_emotion) || e.agent1?.indicio_textual_risco === "presente").length;
  const avgPolarity = filteredCurrent.length > 0
    ? Number(
        (
          filteredCurrent.reduce((acc, e) => acc + Number(e.polarity_score || 0), 0) /
          filteredCurrent.length
        ).toFixed(3),
      )
    : 0;

  return {
    patient,
    filters: { days, valence },
    entries: filteredCurrent,
    totalEntriesAllPeriods: enrichedAll.length,
    reports,
    annotations,
    wheel,
    longitudinal,
    summary: {
      entryCount: filteredCurrent.length,
      positive,
      neutral,
      negative,
      riskCount,
      avgPolarity,
    },
  };
}

export async function GET(request, context) {
  if (process.env.REQUIRE_PSICOLOGA_AUTH === "true") {
    return NextResponse.json({ message: "Acesso profissional requerido." }, { status: 403 });
  }

  try {
    const { id } = await context.params;
    const { searchParams } = new URL(request.url);
    const days = searchParams.get("days") || "all";
    const valence = searchParams.get("valence") || "all";

    const payload = await buildPatientDashboardPayload(id, { days, valence });
    if (!payload) {
      return NextResponse.json({ message: "Paciente não encontrado." }, { status: 404 });
    }
    return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    console.error("Erro em GET /api/psicologa/paciente/[id]:", error);
    return NextResponse.json(
      { message: "Não foi possível carregar a análise clínica do paciente.", detail: error.message },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export async function POST(request, context) {
  if (process.env.REQUIRE_PSICOLOGA_AUTH === "true") {
    return NextResponse.json({ message: "Acesso profissional requerido." }, { status: 403 });
  }

  try {
    const { id } = await context.params;
    const body = await request.json().catch(() => ({}));
    const action = body?.action;

    if (action === "reprocess") {
      const payload = await buildPatientDashboardPayload(id, {
        days: body.days || "all",
        valence: body.valence || "all",
        forceReprocess: true,
        useOllama: Boolean(body.useOllama),
        modelName: body.modelName || null,
      });
      if (!payload) {
        return NextResponse.json({ message: "Paciente não encontrado." }, { status: 404 });
      }
      return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
    }

    if (id === DEMO_PATIENT_ID) {
      return NextResponse.json(
        { message: "Ações de gravação no banco não alteram o caso sintético de demonstração." },
        { status: 400 },
      );
    }

    if (action === "annotate_subtopic") {
      const { macroTema, originalName, displayName, clinicalNote } = body;
      if (!macroTema || !originalName || !displayName?.trim()) {
        return NextResponse.json({ message: "Informe macroTema, originalName e displayName." }, { status: 400 });
      }
      salvarAnotacaoSubtema({
        patientId: id,
        macroTema: String(macroTema),
        originalName: String(originalName),
        displayName: String(displayName).trim().slice(0, 80),
        clinicalNote: String(clinicalNote || "").trim().slice(0, 600),
      });
      const payload = await buildPatientDashboardPayload(id, {
        days: body.days || "all",
        valence: body.valence || "all",
      });
      return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
    }

    if (action === "add_report") {
      const fileName = String(body.fileName || "").trim();
      if (!fileName) {
        return NextResponse.json({ message: "Nome do relatório é obrigatório." }, { status: 400 });
      }
      const report = salvarRelatorioPaciente({
        patientId: id,
        fileName: fileName.slice(0, 180),
        fileSize: Number(body.fileSize || 0),
        mimeType: String(body.mimeType || ""),
        notes: String(body.notes || "").slice(0, 1000),
      });
      return NextResponse.json({ report }, { status: 201, headers: { "Cache-Control": "no-store" } });
    }

    if (action === "remove_report") {
      if (!body.reportId) {
        return NextResponse.json({ message: "reportId é obrigatório." }, { status: 400 });
      }
      removerRelatorioPaciente(id, String(body.reportId));
      return NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
    }

    return NextResponse.json({ message: "Ação não suportada." }, { status: 400 });
  } catch (error) {
    console.error("Erro em POST /api/psicologa/paciente/[id]:", error);
    return NextResponse.json(
      { message: "Não foi possível processar a solicitação.", detail: error.message },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
