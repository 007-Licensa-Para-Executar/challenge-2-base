import { obterPacienteLogado } from "../../_backend";
import { getPatientProfilePhoto } from "../../_database";

export const runtime = "nodejs";

export async function GET(request) {
  const patient = obterPacienteLogado(request);
  if (!patient) {
    return Response.json(
      { message: "Entre na sua conta para acessar sua foto de perfil." },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const photo = getPatientProfilePhoto(patient.id);
    if (!photo) {
      return new Response(null, { status: 404, headers: { "Cache-Control": "no-store" } });
    }

    return new Response(photo.data, {
      headers: {
        "Content-Type": photo.mimeType,
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    console.error("Falha ao carregar a foto do paciente:", error);
    return Response.json(
      { message: "Não foi possível carregar sua foto de perfil." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
