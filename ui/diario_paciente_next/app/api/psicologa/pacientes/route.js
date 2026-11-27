import { listarPacientesDoPortal } from "../../auth/_database.js";
import { getDemoPatientSummaries } from "../../../lib/demoPatient.js";

export const runtime = "nodejs";

export async function GET(request) {
  if (process.env.NODE_ENV === "production" || process.env.REQUIRE_PSICOLOGA_AUTH === "true") {
    return Response.json(
      { message: "A lista de pacientes requer autenticação profissional." },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const patients = listarPacientesDoPortal().map((p) => ({
      ...p,
      isDemo: false,
    }));
    if (new URL(request.url).searchParams.get("includeDemo") === "true") {
      patients.push(
        ...getDemoPatientSummaries().map((patient) => ({
          ...patient,
          address: "",
          age: null,
          treatmentDurationMonths: null,
          psychiatricTreatment: false,
        })),
      );
    }
    return Response.json(
      { patients },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    console.error("Falha ao listar pacientes do portal:", error);
    return Response.json(
      { message: "Não foi possível carregar os cadastros do portal." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
