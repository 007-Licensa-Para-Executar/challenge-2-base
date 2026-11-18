import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { listarDiarios, obterPacienteLogado } from "../api/auth/_backend";
import DiaryWorkspace from "./DiaryWorkspace";

export const metadata = {
  title: "Meu Diário | Registro de Emoções Divertidamente",
  description: "Espaço de cuidado e reflexão emocional para pacientes.",
};

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

  const plainPaciente = {
    id: String(rawPaciente.id),
    name: String(rawPaciente.name),
    email: String(rawPaciente.email),
  };

  const rawRelatos = listarDiarios(plainPaciente.id);
  const plainRelatos = (rawRelatos || []).map((r) => ({
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
    created_at: Number(r.created_at),
  }));

  return (
    <DiaryWorkspace
      initialPaciente={plainPaciente}
      initialRelatos={plainRelatos}
    />
  );
}
