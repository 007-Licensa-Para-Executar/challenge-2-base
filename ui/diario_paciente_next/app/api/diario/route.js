import { NextResponse } from "next/server";
import {
  listarDiarios,
  obterPacienteLogado,
  salvarDiario,
  salvarAnaliseEntrada,
} from "../auth/_backend";
import { analisarRelatoComRedeNeural } from "../../lib/emotionService";
import { runDashboardCli } from "../../lib/dashboardBridge.js";

export async function GET(request) {
  const paciente = obterPacienteLogado(request);
  if (!paciente) {
    return NextResponse.json(
      { message: "Acesso não autorizado. Faça login para continuar." },
      { status: 401 }
    );
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

    let neuralAnalysis = null;
    let analysisWarning = null;
    try {
      const result = await runDashboardCli("analyze-batch", {
        patient_id: paciente.id,
        use_ollama: false,
        max_subtemas: 24,
        entries: [{
          id,
          text: cleanText,
          created_at,
          input_type: inputType,
          primary_emotion: finalEmotion.primary_emotion,
          is_risk_emotion: Boolean(finalEmotion.is_risk_emotion),
        }],
      });
      const item = result.analyzed_entries?.find((entry) => entry.entry_id === id);
      if (!item) throw new Error("A CLI não retornou a análise do relato.");

      salvarAnaliseEntrada(id, {
        themeMacro: item.macro_tema,
        themeConfidence: item.macro_confidence,
        themeScoresJson: JSON.stringify(item.theme_percentages || {}),
        polarityScore: item.polarity_score,
        agent1Json: JSON.stringify(item.agent1),
        analysisSource: item.analysis_source,
      });
      neuralAnalysis = {
        theme_macro: item.macro_tema,
        theme_confidence: item.macro_confidence,
        theme_scores: item.theme_percentages || {},
        polarity_score: item.polarity_score,
        analysis_source: item.analysis_source,
        agent1: item.agent1,
      };
    } catch (error) {
      console.error("Falha ao extrair tema e sentimento do relato:", error);
      analysisWarning = "Tema e sentimento não puderam ser analisados agora.";
    }

    const classificationWarning = [finalEmotion.classification_warning, analysisWarning]
      .filter(Boolean)
      .join(" ") || null;

    return NextResponse.json({
      ok: true,
      entry: {
        id,
        patient_id: paciente.id,
        text: cleanText,
        ...finalEmotion,
        ...neuralAnalysis,
        classification_warning: classificationWarning,
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
