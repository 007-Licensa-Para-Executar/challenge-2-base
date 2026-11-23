import { NextResponse } from "next/server";
import { obterPacienteLogado } from "../../auth/_backend";
import { analisarRelatoComRedeNeural } from "../../../lib/emotionService";

export async function POST(request) {
  const paciente = obterPacienteLogado(request);
  if (!paciente) {
    return NextResponse.json(
      { message: "Acesso não autorizado. Faça login para continuar." },
      { status: 401 }
    );
  }

  try {
    const { text } = await request.json();
    const resultado = await analisarRelatoComRedeNeural(text || "");
    return NextResponse.json(resultado);
  } catch (error) {
    return NextResponse.json(
      { message: "Erro ao processar análise emocional." },
      { status: 500 }
    );
  }
}
