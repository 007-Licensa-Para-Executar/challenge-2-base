import { randomUUID } from "node:crypto";
import { runIntegration } from "../../lib/dashboardBridge.js";
import { integrationEnabled, localDemo, patientAlias } from "../../lib/integrationDemo.js";
import { NextResponse } from "next/server";
import {
  listarDiarios,
  obterPacienteLogado,
  salvarDiario,
} from "../auth/_backend";
import { analisarRelatoComRedeNeural } from "../../lib/emotionService";

export async function GET(request) {
  const paciente = obterPacienteLogado(request);
  if (!paciente) {
    return NextResponse.json(
      { message: "Acesso não autorizado. Faça login para continuar." },
      { status: 401 }
    );
  }

  if (integrationEnabled()) {
    if (!localDemo(request) || !patientAlias(paciente.email)) {
      return NextResponse.json({ message: "Conta fora da demonstração local." }, { status: 403 });
    }
    try {
      const result = await runIntegration("dashboard", { patient: patientAlias(paciente.email) });
      if (!result.entries) throw new Error("Leitura indisponível");
      return NextResponse.json({ paciente: { id: paciente.id, name: paciente.name, email: paciente.email }, relatos: result.entries.map(({ agent1, ...entry }) => ({
        id: entry.id, text: entry.text, created_at: entry.created_at, primary_emotion: "neutro",
      })) });
    } catch {
      return NextResponse.json({ message: "Histórico indisponível." }, { status: 503 });
    }
  }
  const relatos = listarDiarios(paciente.id);
  return NextResponse.json({
    paciente: { id: paciente.id, name: paciente.name, email: paciente.email },
    relatos,
  });
}

export async function POST(request) {
  const paciente = obterPacienteLogado(request);
  if (!paciente) {
    return NextResponse.json(
      { message: "Acesso não autorizado. Faça login para continuar." },
      { status: 401 }
    );
  }

  try {
    const {
      text,
      inputType = "text",
      audioName = null,
      audioDuration = null,
      audioData = null,
    } = await request.json();
    const cleanText = typeof text === "string" ? text.trim() : "";

    if (!cleanText) {
      return NextResponse.json(
        { message: "Escreva algo antes de salvar o diário." },
        { status: 400 }
      );
    }

    if (integrationEnabled()) {
      const alias = patientAlias(paciente.email);
      if (!localDemo(request) || !alias) {
        return NextResponse.json({ message: "Conta fora da demonstração local." }, { status: 403 });
      }
      if ([...cleanText].length > 2400) {
        return NextResponse.json({ message: "Limite de 2.400 caracteres." }, { status: 400 });
      }
      const id = randomUUID();
      const date = new Date();
      const analysis = await runIntegration("ingest", {
        patient: alias, record_id: id, recorded_at: date.toISOString(), text: cleanText,
        audio: inputType === "audio",
      });
      if (!analysis.record_id) {
        return NextResponse.json({ message: "Falha ao proteger ou guardar o diário." }, { status: 503 });
      }
      return NextResponse.json({ ok: true, analysis_error: analysis.analysis_error, entry: {
        id, patient_id: paciente.id, text: analysis.treated_text, input_type: inputType,
        primary_emotion: "neutro", classification_warning: analysis.analysis_error
          ? "Análise de subtemas pendente." : undefined, created_at: date.getTime(),
      } });
    }

    // Sempre classifica no servidor para ignorar qualquer emoção enviada pelo navegador.
    const finalEmotion = await analisarRelatoComRedeNeural(cleanText);

    const { id, created_at } = salvarDiario({
      patientId: paciente.id,
      text: cleanText,
      emotion: finalEmotion,
      inputType,
      audioName,
      audioDuration,
      audioData,
    });

    return NextResponse.json({
      ok: true,
      entry: {
        id,
        patient_id: paciente.id,
        text: cleanText,
        ...finalEmotion,
        input_type: inputType,
        audio_name: audioName,
        audio_duration: audioDuration,
        audio_data: audioData,
        created_at,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { message: "Falha ao gravar relato no diário." },
      { status: 500 }
    );
  }
}
