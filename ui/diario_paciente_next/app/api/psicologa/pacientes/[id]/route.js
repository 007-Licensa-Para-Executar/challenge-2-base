import { updatePatientProfile } from "../../../auth/_database";

export const runtime = "nodejs";

function unavailableInProduction() {
  return process.env.NODE_ENV === "production"
    ? Response.json(
        { message: "A edição de pacientes requer autenticação profissional." },
        { status: 403, headers: { "Cache-Control": "no-store" } },
      )
    : null;
}

function readOptionalInteger(value, label) {
  if (value === null) return { value: null };
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    return { error: `${label} deve ser um número inteiro válido e não negativo.` };
  }
  return { value };
}

export async function PATCH(request, context) {
  const unavailable = unavailableInProduction();
  if (unavailable) return unavailable;

  try {
    const { id } = await context.params;
    const body = await request.json().catch(() => null);
    if (typeof body !== "object" || body === null) {
      return Response.json(
        { message: "Os dados do paciente são inválidos." },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }

    const name = typeof body.name === "string" ? body.name.trim() : "";
    const address = typeof body.address === "string" ? body.address.trim() : null;
    const age = readOptionalInteger(body.age, "Idade");
    const treatmentDurationMonths = readOptionalInteger(
      body.treatmentDurationMonths,
      "Tempo de tratamento",
    );

    if (name.length < 2 || name.length > 120) {
      return Response.json(
        { message: "Informe um nome entre 2 e 120 caracteres." },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }
    if (address === null || address.length > 500) {
      return Response.json(
        { message: "O endereço é inválido ou excede 500 caracteres." },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }
    if (age.error || treatmentDurationMonths.error) {
      return Response.json(
        { message: age.error || treatmentDurationMonths.error },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }
    if (typeof body.psychiatricTreatment !== "boolean") {
      return Response.json(
        { message: "Informe se o paciente também faz acompanhamento psiquiátrico." },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }

    const patient = updatePatientProfile(id, {
      name,
      address,
      age: age.value,
      treatmentDurationMonths: treatmentDurationMonths.value,
      psychiatricTreatment: body.psychiatricTreatment,
    });
    if (!patient) {
      return Response.json(
        { message: "Paciente não encontrado." },
        { status: 404, headers: { "Cache-Control": "no-store" } },
      );
    }

    return Response.json(
      { patient },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    console.error("Falha ao atualizar perfil do paciente:", error);
    return Response.json(
      { message: "Não foi possível salvar o perfil do paciente." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
