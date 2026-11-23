import { listarPacientesDoPortal } from "../../auth/_database.js";
import { getDemoPatientSummary } from "../../../lib/demoPatient.js";

export const runtime = "nodejs";

export async function GET() {
  if (process.env.REQUIRE_PSICOLOGA_AUTH === "true") {
    return Response.json(
      { message: "A lista de pacientes requer autenticação profissional." },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const portalPatients = listarPacientesDoPortal().map((p) => ({
      ...p,
      isDemo: false,
    }));
    const demoPatient = getDemoPatientSummary();
    return Response.json(
      { patients: [...portalPatients, demoPatient] },
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
