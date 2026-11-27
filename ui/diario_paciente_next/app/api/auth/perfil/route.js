import { atualizarPerfilProprioPaciente, obterPacienteLogado } from "../_backend";
import { getPatientProfile } from "../_database";

export const runtime = "nodejs";

const maxPhotoSize = 2 * 1024 * 1024;
const maxRequestSize = maxPhotoSize + 64 * 1024;
const allowedPhotoTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const noStore = { "Cache-Control": "no-store" };

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

function readText(formData, field, maxLength) {
  const value = formData.get(field);
  if (typeof value !== "string") return { error: `O campo ${field} é inválido.` };
  const normalized = value.replace(/\r\n?/g, "\n").trim();
  if (normalized.length > maxLength) return { error: `O campo ${field} excede o limite permitido.` };
  return { value: normalized };
}

function readPassword(formData, field) {
  const value = formData.get(field);
  if (value === null) return { value: "" };
  if (typeof value !== "string") return { error: `O campo ${field} é inválido.` };
  if (value.length > 128) return { error: "A senha deve ter no máximo 128 caracteres." };
  return { value };
}

function readAge(formData) {
  const value = formData.get("age");
  if (typeof value !== "string") return { error: "A idade informada é inválida." };
  if (value.trim() === "") return { value: null };
  if (!/^\d+$/.test(value.trim())) return { error: "Informe a idade em anos completos." };

  const age = Number(value);
  if (!Number.isSafeInteger(age) || age < 0 || age > 130) {
    return { error: "A idade deve estar entre 0 e 130 anos." };
  }
  return { value: age };
}

function unauthorized() {
  return Response.json({ message: "Entre na sua conta para acessar seu perfil." }, {
    status: 401,
    headers: noStore,
  });
}

export async function GET(request) {
  const patient = obterPacienteLogado(request);
  if (!patient) return unauthorized();

  try {
    const profile = getPatientProfile(patient.id);
    if (!profile) {
      return Response.json({ message: "Não foi possível localizar seu perfil." }, {
        status: 404,
        headers: noStore,
      });
    }
    return Response.json({ profile }, { headers: noStore });
  } catch (error) {
    console.error("Falha ao carregar o perfil do paciente:", error);
    return Response.json({ message: "Não foi possível carregar seu perfil agora." }, {
      status: 500,
      headers: noStore,
    });
  }
}

export async function PATCH(request) {
  const patient = obterPacienteLogado(request);
  if (!patient) return unauthorized();

  const contentLength = request.headers.get("content-length");
  if (contentLength && Number(contentLength) > maxRequestSize) {
    return Response.json({ message: "A foto deve ter no máximo 2 MB." }, {
      status: 413,
      headers: noStore,
    });
  }
  if (!request.headers.get("content-type")?.startsWith("multipart/form-data")) {
    return Response.json({ message: "Envie os dados do perfil em formato multipart." }, {
      status: 415,
      headers: noStore,
    });
  }

  let formData;
  try {
    formData = await request.formData();
  } catch {
    return Response.json({ message: "Não foi possível ler os dados enviados." }, {
      status: 400,
      headers: noStore,
    });
  }

  const name = readText(formData, "name", 120);
  const email = readText(formData, "email", 254);
  const address = readText(formData, "address", 500);
  const insurancePlan = readText(formData, "insurancePlan", 200);
  const age = readAge(formData);
  const currentPassword = readPassword(formData, "currentPassword");
  const newPassword = readPassword(formData, "newPassword");
  const invalidField = [name, email, address, insurancePlan, age, currentPassword, newPassword]
    .find((field) => field.error);

  if (invalidField) {
    return Response.json({ message: invalidField.error }, { status: 400, headers: noStore });
  }
  if (name.value.length < 2) {
    return Response.json({ message: "Informe um nome com pelo menos 2 caracteres." }, {
      status: 400,
      headers: noStore,
    });
  }
  const normalizedEmail = email.value.toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    return Response.json({ message: "Confira se o e-mail foi digitado corretamente." }, {
      status: 400,
      headers: noStore,
    });
  }
  if (newPassword.value && !currentPassword.value) {
    return Response.json({ message: "Informe sua senha atual para cadastrar uma nova." }, {
      status: 400,
      headers: noStore,
    });
  }
  if (currentPassword.value && !newPassword.value) {
    return Response.json({ message: "Preencha a nova senha para atualizar sua senha." }, {
      status: 400,
      headers: noStore,
    });
  }
  if (newPassword.value && (newPassword.value.length < 8 || newPassword.value.length > 128)) {
    return Response.json({ message: "A nova senha deve ter entre 8 e 128 caracteres." }, {
      status: 400,
      headers: noStore,
    });
  }

  let photo = null;
  let photoMime = null;
  const photoField = formData.get("photo");
  if (photoField && typeof photoField !== "string") {
    if (photoField.size > maxPhotoSize) {
      return Response.json({ message: "A foto deve ter no máximo 2 MB." }, {
        status: 413,
        headers: noStore,
      });
    }
    if (photoField.size > 0) {
      if (!allowedPhotoTypes.has(photoField.type)) {
        return Response.json({ message: "Use uma foto JPG, PNG ou WebP." }, {
          status: 400,
          headers: noStore,
        });
      }
      const bytes = new Uint8Array(await photoField.arrayBuffer());
      if (!isMatchingImageType(bytes, photoField.type)) {
        return Response.json({ message: "O arquivo não contém uma imagem JPG, PNG ou WebP válida." }, {
          status: 400,
          headers: noStore,
        });
      }
      photo = bytes;
      photoMime = photoField.type;
    }
  } else if (photoField) {
    return Response.json({ message: "O arquivo de foto é inválido." }, {
      status: 400,
      headers: noStore,
    });
  }

  try {
    const result = await atualizarPerfilProprioPaciente(patient.id, {
      name: name.value,
      email: normalizedEmail,
      address: address.value,
      age: age.value,
      insurancePlan: insurancePlan.value,
      photo,
      photoMime,
      currentPassword: currentPassword.value,
      newPassword: newPassword.value,
    }, request);

    if (!result.ok && result.motivo === "email_em_uso") {
      return Response.json({ message: "Este e-mail já está sendo usado por outra conta." }, {
        status: 409,
        headers: noStore,
      });
    }
    if (!result.ok && result.motivo === "senha_atual_incorreta") {
      return Response.json({ message: "A senha atual não confere." }, { status: 401, headers: noStore });
    }
    if (!result.ok) {
      return Response.json({ message: "Não foi possível localizar seu perfil." }, {
        status: 404,
        headers: noStore,
      });
    }

    return Response.json({ profile: result.profile }, { headers: noStore });
  } catch (error) {
    console.error("Falha ao salvar o perfil do paciente:", error);
    return Response.json({ message: "Não foi possível salvar seu perfil agora." }, {
      status: 500,
      headers: noStore,
    });
  }
}
