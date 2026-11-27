import {
  getPsychologistProfile,
  updatePsychologistProfile,
} from "../../auth/_database";

export const runtime = "nodejs";

const maxPhotoSize = 2 * 1024 * 1024;
const maxRequestSize = maxPhotoSize + 64 * 1024;
const allowedPhotoTypes = new Set(["image/jpeg", "image/png", "image/webp"]);

function unavailableInProduction() {
  return process.env.NODE_ENV === "production"
    ? Response.json(
        { message: "A edição do perfil requer autenticação profissional." },
        { status: 403, headers: { "Cache-Control": "no-store" } },
      )
    : null;
}

function isMatchingImageType(bytes, mimeType) {
  if (mimeType === "image/jpeg") {
    return bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  }
  if (mimeType === "image/png") {
    return bytes.length >= 8 &&
      [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a].every((byte, index) => bytes[index] === byte);
  }
  if (mimeType === "image/webp") {
    return bytes.length >= 12 &&
      String.fromCharCode(...bytes.slice(0, 4)) === "RIFF" &&
      String.fromCharCode(...bytes.slice(8, 12)) === "WEBP";
  }
  return false;
}

function readText(formData, name, maxLength) {
  const value = formData.get(name);
  if (typeof value !== "string") return { error: `O campo ${name} é inválido.` };
  if (value.length > maxLength) return { error: `O campo ${name} excede o limite permitido.` };
  return { value: value.replace(/\r\n?/g, "\n").trim() };
}

function readNumber(formData, name, label, integer = false) {
  const raw = formData.get(name);
  if (typeof raw !== "string") return { error: `O campo ${label} é inválido.` };
  if (raw.trim() === "") return { value: null };

  const numberPattern = integer ? /^\d+$/ : /^\d+(?:[.,]\d+)?$/;
  if (!numberPattern.test(raw.trim())) {
    return { error: `${label} deve ser um número válido e não negativo.` };
  }

  const value = Number(raw.trim().replace(",", "."));
  if (!Number.isFinite(value) || value < 0 || (integer && !Number.isSafeInteger(value))) {
    return { error: `${label} deve ser um número válido e não negativo.` };
  }
  return { value };
}

export async function GET() {
  const unavailable = unavailableInProduction();
  if (unavailable) return unavailable;

  try {
    return Response.json(
      { profile: getPsychologistProfile() },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    console.error("Falha ao carregar perfil da psicóloga:", error);
    return Response.json(
      { message: "Não foi possível carregar o perfil da psicóloga." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export async function PATCH(request) {
  const unavailable = unavailableInProduction();
  if (unavailable) return unavailable;

  const contentLength = request.headers.get("content-length");
  if (contentLength && Number(contentLength) > maxRequestSize) {
    return Response.json(
      { message: "A foto deve ter no máximo 2 MB." },
      { status: 413, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (!request.headers.get("content-type")?.startsWith("multipart/form-data")) {
    return Response.json(
      { message: "Envie os dados do perfil em formato multipart." },
      { status: 415, headers: { "Cache-Control": "no-store" } },
    );
  }

  let formData;
  try {
    formData = await request.formData();
  } catch {
    return Response.json(
      { message: "Não foi possível ler os dados enviados." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  const name = readText(formData, "name", 120);
  const profession = readText(formData, "profession", 120);
  const specialty = readText(formData, "specialty", 200);
  const insurancePlans = readText(formData, "insurancePlans", 2000);
  const resume = readText(formData, "resume", 5000);
  const professionalExperiences = readText(formData, "professionalExperiences", 5000);
  const age = readNumber(formData, "age", "Idade", true);
  const experienceYears = readNumber(formData, "experienceYears", "Tempo de experiência");
  const invalidField = [
    name,
    profession,
    specialty,
    insurancePlans,
    resume,
    professionalExperiences,
    age,
    experienceYears,
  ].find((field) => field.error);

  if (invalidField) {
    return Response.json(
      { message: invalidField.error },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (!name.value) {
    return Response.json(
      { message: "Informe o nome da psicóloga." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  let photo = null;
  let photoMime = null;
  const photoField = formData.get("photo");
  if (photoField && typeof photoField !== "string") {
    if (photoField.size > maxPhotoSize) {
      return Response.json(
        { message: "A foto deve ter no máximo 2 MB." },
        { status: 413, headers: { "Cache-Control": "no-store" } },
      );
    }
    if (photoField.size > 0) {
      if (!allowedPhotoTypes.has(photoField.type)) {
        return Response.json(
          { message: "Use uma imagem JPG, PNG ou WebP." },
          { status: 400, headers: { "Cache-Control": "no-store" } },
        );
      }
      const bytes = new Uint8Array(await photoField.arrayBuffer());
      if (!isMatchingImageType(bytes, photoField.type)) {
        return Response.json(
          { message: "O conteúdo do arquivo não corresponde a uma imagem JPG, PNG ou WebP válida." },
          { status: 400, headers: { "Cache-Control": "no-store" } },
        );
      }
      photo = bytes;
      photoMime = photoField.type;
    }
  } else if (photoField) {
    return Response.json(
      { message: "O arquivo de foto é inválido." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const profile = updatePsychologistProfile({
      name: name.value,
      age: age.value,
      profession: profession.value,
      specialty: specialty.value,
      insurancePlans: insurancePlans.value,
      resume: resume.value,
      professionalExperiences: professionalExperiences.value,
      experienceYears: experienceYears.value,
      photo,
      photoMime,
    });
    return Response.json(
      { profile },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    console.error("Falha ao salvar perfil da psicóloga:", error);
    return Response.json(
      { message: "Não foi possível salvar o perfil. Tente novamente." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
