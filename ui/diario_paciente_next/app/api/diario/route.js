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
