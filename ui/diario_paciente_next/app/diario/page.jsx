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

  const paciente = obterPacienteLogado(mockRequest);
  if (!paciente) {
    redirect("/");
  }

  const relatos = listarDiarios(paciente.id);

  return (
    <DiaryWorkspace
      initialPaciente={paciente}
      initialRelatos={relatos}
    />
  );
}
