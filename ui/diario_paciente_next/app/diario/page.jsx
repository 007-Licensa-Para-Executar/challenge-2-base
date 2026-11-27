import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { listarDiarios, obterPacienteLogado } from "../api/auth/_backend";
import { getPatientProfile } from "../api/auth/_database";
import DiaryWorkspace from "./DiaryWorkspace";

export const metadata = {
  title: "Meu Diário | Registro de Emoções Divertidamente",
  description: "Espaço de cuidado e reflexão emocional para pacientes.",
};

function parseJsonSafe(value) {
  if (typeof value !== "string") return value || null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

export default async function DiarioPage() {
  const cookieStore = await cookies();
  const allCookies = cookieStore.getAll();
  const cookieHeader = allCookies.map((c) => `${c.name}=${c.value}`).join("; ");

  const mockRequest = {
    headers: new Headers({ cookie: cookieHeader }),
  };

  const rawPaciente = obterPacienteLogado(mockRequest);
  if (!rawPaciente) {
    redirect("/");
  }

  const profile = getPatientProfile(rawPaciente.id);

  const plainPaciente = {
    id: String(rawPaciente.id),
    name: String(rawPaciente.name),
    email: String(rawPaciente.email),
    photoUrl: profile?.photoUrl || null,
  };

  const rawRelatos = listarDiarios(plainPaciente.id);
  const plainRelatos = (rawRelatos || []).map((r) => {
    const agent1 = parseJsonSafe(r.agent1_json);
    const themeScores = parseJsonSafe(r.theme_scores_json);
    return {
      id: String(r.id),
      patient_id: String(r.patient_id),
      text: String(r.text),
      primary_emotion: String(r.primary_emotion),
      character: String(r.character),
      color_hex: String(r.color_hex),
      color_secondary_hex: String(r.color_secondary_hex || ""),
      sub_emotion_name: String(r.sub_emotion_name),
      sub_emotion_symbol: String(r.sub_emotion_symbol),
      confidence: Number(r.confidence || 1.0),
      is_risk_emotion: Boolean(r.is_risk_emotion),
      input_type: String(r.input_type || "text"),
      audio_name: r.audio_name ? String(r.audio_name) : "",
      audio_duration: r.audio_duration ? String(r.audio_duration) : "",
      audio_data: r.audio_data ? String(r.audio_data) : "",
      created_at: Number(r.created_at),
      theme_macro: r.theme_macro || agent1?.macro_tema_validado || null,
      theme_confidence: Number(r.theme_confidence ?? agent1?.confianca_macro_tema ?? 0),
      theme_scores: themeScores,
      polarity_score: r.polarity_score ?? agent1?.score_polaridade ?? null,
      analysis_source: r.analysis_source || null,
      agent1,
    };
  });

  return (
    <DiaryWorkspace
      initialPaciente={plainPaciente}
      initialRelatos={plainRelatos}
    />
  );
}
