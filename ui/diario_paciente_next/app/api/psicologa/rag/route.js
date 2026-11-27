import { integrationEnabled, integrationPatient, localDemo } from "../../../lib/integrationDemo.js";
import { NextResponse } from "next/server";
import { listarDiarios } from "../../auth/_backend.js";
import { runDashboardCli, runIntegration } from "../../../lib/dashboardBridge.js";
import { getDemoPatientEntries, isDemoPatientId } from "../../../lib/demoPatient.js";

export const runtime = "nodejs";

export async function GET(request) {
  if (process.env.NODE_ENV === "production" || process.env.REQUIRE_PSICOLOGA_AUTH === "true" ||
      !localDemo(request)) {
    return NextResponse.json({ message: "Acesso profissional requerido." }, { status: 403 });
  }
  try {
    const result = integrationEnabled() ? await runIntegration("tools", {}) : { tools: [] };
    return NextResponse.json(result, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ message: "Catálogo indisponível." }, { status: 503 });
  }
}

export async function POST(request) {
  if (process.env.NODE_ENV === "production" || process.env.REQUIRE_PSICOLOGA_AUTH === "true") {
    return NextResponse.json({ message: "Acesso profissional requerido." }, { status: 403 });
  }

  try {
    const body = await request.json().catch(() => ({}));
    const patientId = String(body.patientId || "").trim();
    const question = String(body.question || "").trim();
    const days = body.days || "all";
    const generationMode = body.generationMode === "ollama" ? "ollama" : "extractive";

    if (!patientId || !question) {
      return NextResponse.json(
        { message: "Informe paciente e pergunta para consultar o Copiloto RAG." },
        { status: 400 },
      );
    }

    if (integrationEnabled()) {
      if (!localDemo(request) || !integrationPatient(patientId)) {
        return NextResponse.json({ message: "Paciente fora da demonstração." }, { status: 403 });
      }
      const result = await runIntegration("chat", {
        patient: patientId, question, days, generation_mode: generationMode,
        topic: body.topic, record_id: body.recordId, representation_id: body.representationId,
        entry_id: body.entryId,
        start_char: body.startChar, end_char: body.endChar,
        confirmed: body.confirmed === true,
      });
      return NextResponse.json(result, { headers: { "Cache-Control": "no-store" } });
    }

    const rawEntries = isDemoPatientId(patientId)
      ? getDemoPatientEntries(patientId)
      : listarDiarios(patientId);

    let filtered = rawEntries;
    if (days !== "all") {
      const daysNum = Number(days);
      if (Number.isFinite(daysNum) && daysNum > 0) {
        const cutoff = Date.now() - daysNum * 86400000;
        filtered = rawEntries.filter((r) => Number(r.created_at) >= cutoff);
      }
    }

    if (filtered.length === 0) {
      return NextResponse.json(
        {
          status: "insufficient_evidence",
          patient_id: patientId,
          question,
          answer: "Não há registros no período selecionado para embasar uma resposta.",
          evidence: [],
          eligible_records: 0,
          generation_mode: generationMode,
          retriever: "bm25",
        },
        { headers: { "Cache-Control": "no-store" } },
      );
    }

    const result = await runDashboardCli(
      "rag-query",
      {
        patient_id: patientId,
        question,
        generation_mode: generationMode,
        top_k: 4,
        entries: filtered.map((r) => ({
          id: r.id,
          text: r.text,
          created_at: r.created_at,
          input_type: r.input_type || "text",
          macro_tema: r.theme_macro || null,
        })),
      },
      generationMode === "ollama" ? 150000 : 25000,
    );

    return NextResponse.json(result, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    console.error("Erro em POST /api/psicologa/rag:", error);
    return NextResponse.json(
      { message: "Falha ao consultar o Copiloto RAG.", detail: error.message },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
