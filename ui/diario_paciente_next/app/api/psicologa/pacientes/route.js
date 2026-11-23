import { listarPacientesDoPortal } from "../../auth/_database";

export const runtime = "nodejs";

// Lista local para desenvolvimento. Produção deve proteger esta leitura com login profissional.
export async function GET() {
  if (process.env.NODE_ENV === "production") {
    return Response.json(
      { message: "A lista de pacientes requer autenticação profissional." },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const patients = listarPacientesDoPortal();
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
