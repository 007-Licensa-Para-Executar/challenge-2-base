import {
  createHash,
  randomBytes,
  randomUUID,
  scrypt,
  timingSafeEqual,
} from "node:crypto";
import { promisify } from "node:util";
import { getAuthDatabase, getPatientProfile } from "./_database.js";

const scryptAsync = promisify(scrypt);
const scryptOptions = { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
const sessionCookieName = "diario_sessao";
const sessionLifetime = 7 * 24 * 60 * 60;

async function hashPassword(password, salt) {
  return Buffer.from(await scryptAsync(password, salt, 64, scryptOptions));
}

function extractSessionToken(request) {
  const cookie = request.headers
    .get("cookie")
    ?.split(";")
    .map((parte) => parte.trim())
    .find((parte) => parte.startsWith(`${sessionCookieName}=`));
  const token = cookie?.slice(sessionCookieName.length + 1);
  if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) return null;
  return token;
}

// Salva somente hash e salt da senha; e-mail fica normalizado para evitar duplicatas por caixa.
export async function criarPaciente({ nome, email, senha }) {
  const db = getAuthDatabase();
  const id = randomUUID();
  const salt = randomBytes(16);
  const hash = await hashPassword(senha, salt);

  try {
    db.prepare(
      `INSERT INTO patients (id, name, email, password_salt, password_hash, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
    ).run(id, nome, email, salt.toString("hex"), hash.toString("hex"), Date.now());
    return { ok: true, id };
  } catch (error) {
    if (error.message?.includes("UNIQUE constraint failed: patients.email")) {
      return { ok: false, motivo: "email_em_uso" };
    }
    throw error;
  }
}

// Confere a senha e cria uma sessão opaca armazenada no banco e enviada em cookie HTTP-only.
export async function autenticarPaciente(email, senha) {
  const db = getAuthDatabase();
  const paciente = db
    .prepare("SELECT id, password_salt, password_hash FROM patients WHERE email = ?")
    .get(email);
  const salt = paciente ? Buffer.from(paciente.password_salt, "hex") : Buffer.alloc(16);
  const esperado = paciente ? Buffer.from(paciente.password_hash, "hex") : Buffer.alloc(64);
  const calculado = await hashPassword(senha, salt);
  const senhaCorreta = esperado.length === calculado.length && timingSafeEqual(calculado, esperado);

  if (!paciente || !senhaCorreta) return null;

  const token = randomBytes(32).toString("base64url");
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const agora = Date.now();
  db.prepare("DELETE FROM sessions WHERE expires_at <= ?").run(agora);
  db.prepare("INSERT INTO sessions (token_hash, patient_id, expires_at) VALUES (?, ?, ?)")
    .run(tokenHash, paciente.id, agora + sessionLifetime * 1000);

  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return {
    cookie: `${sessionCookieName}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${sessionLifetime}${secure}`,
  };
}

// Lê a sessão para que outras rotas do diário possam exigir um paciente autenticado.
export function obterPacienteLogado(request) {
  const token = extractSessionToken(request);
  if (!token) return null;

  const tokenHash = createHash("sha256").update(token).digest("hex");
  const paciente = getAuthDatabase()
    .prepare(
      `SELECT patients.id, patients.name, patients.email
       FROM sessions JOIN patients ON patients.id = sessions.patient_id
       WHERE sessions.token_hash = ? AND sessions.expires_at > ?`,
    )
    .get(tokenHash, Date.now());

  return paciente ? { ...paciente } : null;
}

// Atualiza somente o cadastro vinculado à sessão atual. A senha antiga é
// necessária sempre que o paciente escolhe uma senha nova.
export async function atualizarPerfilProprioPaciente(patientId, profile, request) {
  const db = getAuthDatabase();
  const patient = db.prepare(
    "SELECT password_salt, password_hash FROM patients WHERE id = ?",
  ).get(patientId);
  if (!patient) return { ok: false, motivo: "nao_encontrado" };

  let passwordSalt = null;
  let passwordHash = null;
  if (profile.newPassword) {
    const currentSalt = Buffer.from(patient.password_salt, "hex");
    const expectedHash = Buffer.from(patient.password_hash, "hex");
    const currentHash = await hashPassword(profile.currentPassword, currentSalt);
    if (expectedHash.length !== currentHash.length || !timingSafeEqual(currentHash, expectedHash)) {
      return { ok: false, motivo: "senha_atual_incorreta" };
    }

    passwordSalt = randomBytes(16);
    passwordHash = await hashPassword(profile.newPassword, passwordSalt);
  }

  try {
    const result = db.prepare(
      `UPDATE patients
       SET name = ?, email = ?, address = ?, age = ?, insurance_plan = ?,
           photo = COALESCE(?, photo), photo_mime = COALESCE(?, photo_mime),
           profile_photo_updated_at = CASE WHEN ? IS NULL THEN profile_photo_updated_at ELSE ? END,
           password_salt = COALESCE(?, password_salt),
           password_hash = COALESCE(?, password_hash)
       WHERE id = ?`,
    ).run(
      profile.name,
      profile.email,
      profile.address,
      profile.age,
      profile.insurancePlan,
      profile.photo,
      profile.photoMime,
      profile.photo,
      profile.photo ? Date.now() : null,
      passwordSalt?.toString("hex") || null,
      passwordHash?.toString("hex") || null,
      patientId,
    );

    if (!result.changes) return { ok: false, motivo: "nao_encontrado" };

    if (passwordHash) {
      const token = extractSessionToken(request);
      if (token) {
        const tokenHash = createHash("sha256").update(token).digest("hex");
        db.prepare("DELETE FROM sessions WHERE patient_id = ? AND token_hash <> ?")
          .run(patientId, tokenHash);
      }
    }

    return { ok: true, profile: getPatientProfile(patientId) };
  } catch (error) {
    if (error.message?.includes("UNIQUE constraint failed: patients.email")) {
      return { ok: false, motivo: "email_em_uso" };
    }
    throw error;
  }
}

// Remove a sessão do banco e devolve o cabeçalho Set-Cookie expirado.
export function encerrarSessao(request) {
  const token = extractSessionToken(request);
  if (token) {
    const tokenHash = createHash("sha256").update(token).digest("hex");
    getAuthDatabase().prepare("DELETE FROM sessions WHERE token_hash = ?").run(tokenHash);
  }
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return {
    cookie: `${sessionCookieName}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure}`,
  };
}

// Salva um relato do diário associado ao paciente e à emoção detectada pelo modelo (com suporte a áudio).
export function salvarDiario({
  patientId,
  text,
  emotion,
  inputType = "text",
  audioName = null,
  audioDuration = null,
  audioData = null,
}) {
  const db = getAuthDatabase();
  const id = randomUUID();
  const agora = Date.now();

  db.prepare(
    `INSERT INTO diary_entries (
      id, patient_id, text, primary_emotion, character, color_hex,
      color_secondary_hex, sub_emotion_name, sub_emotion_symbol,
      confidence, is_risk_emotion, input_type, audio_name, audio_duration, audio_data, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).run(
    id,
    patientId,
    text,
    emotion.primary_emotion || "neutro",
    emotion.character || "Equilíbrio",
    emotion.color_hex || "#9E9E9E",
    emotion.color_secondary_hex || "#ECEFF1",
    emotion.active_sub_emotion?.nome || emotion.sub_emotion_name || "Equilíbrio",
    emotion.active_sub_emotion?.simbolo || emotion.sub_emotion_symbol || "⚖️",
    Number(emotion.confidence || 1.0),
    emotion.is_risk_emotion ? 1 : 0,
    inputType || "text",
    audioName || null,
    audioDuration || null,
    audioData || null,
    agora,
  );

  return { id, created_at: agora };
}

// Retorna o histórico de relatos do paciente ordenados do mais recente para o mais antigo.
export function listarDiarios(patientId) {
  const rows = getAuthDatabase()
    .prepare("SELECT * FROM diary_entries WHERE patient_id = ? ORDER BY created_at DESC")
    .all(patientId);

  return rows.map((r) => ({ ...r }));
}

export function obterPacientePorId(patientId) {
  const row = getAuthDatabase()
    .prepare("SELECT id, name, email, created_at FROM patients WHERE id = ?")
    .get(patientId);
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    createdAt: new Date(row.created_at).toISOString(),
  };
}

export function salvarAnaliseEntrada(
  entryId,
  { themeMacro, themeConfidence, themeScoresJson, polarityScore, agent1Json, analysisSource },
) {
  getAuthDatabase()
    .prepare(
      `UPDATE diary_entries
       SET theme_macro = ?,
           theme_confidence = ?,
           theme_scores_json = ?,
           polarity_score = ?,
           agent1_json = ?,
           analysis_source = ?,
           analyzed_at = ?
       WHERE id = ?`,
    )
    .run(
      themeMacro || null,
      themeConfidence ?? null,
      themeScoresJson || null,
      polarityScore ?? null,
      agent1Json || null,
      analysisSource || null,
      Date.now(),
      entryId,
    );
}

export function listarRelatoriosPaciente(patientId) {
  return getAuthDatabase()
    .prepare(
      `SELECT id, patient_id, file_name, file_size, mime_type, notes, uploaded_at
       FROM clinical_reports WHERE patient_id = ? ORDER BY uploaded_at DESC`,
    )
    .all(patientId)
    .map((row) => ({
      id: row.id,
      patientId: row.patient_id,
      fileName: row.file_name,
      fileSize: Number(row.file_size || 0),
      mimeType: row.mime_type || "application/octet-stream",
      notes: row.notes || "",
      uploadedAt: new Date(row.uploaded_at).toISOString(),
      status: "concluido",
      progress: 100,
    }));
}

export function salvarRelatorioPaciente({ patientId, fileName, fileSize = 0, mimeType = "", notes = "" }) {
  const id = `relatorio-${randomUUID()}`;
  const agora = Date.now();
  getAuthDatabase()
    .prepare(
      `INSERT INTO clinical_reports (id, patient_id, file_name, file_size, mime_type, notes, uploaded_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(id, patientId, fileName, Number(fileSize || 0), mimeType || null, notes || null, agora);
  return {
    id,
    patientId,
    fileName,
    fileSize: Number(fileSize || 0),
    mimeType: mimeType || "application/octet-stream",
    notes: notes || "",
    uploadedAt: new Date(agora).toISOString(),
    status: "concluido",
    progress: 100,
  };
}

export function removerRelatorioPaciente(patientId, reportId) {
  getAuthDatabase()
    .prepare("DELETE FROM clinical_reports WHERE id = ? AND patient_id = ?")
    .run(reportId, patientId);
}

export function listarAnotacoesSubtemas(patientId) {
  return getAuthDatabase()
    .prepare(
      `SELECT macro_tema, original_name, display_name, clinical_note, updated_at
       FROM subtopic_annotations WHERE patient_id = ?`,
    )
    .all(patientId)
    .map((r) => ({ ...r }));
}

export function salvarAnotacaoSubtema({ patientId, macroTema, originalName, displayName, clinicalNote = "" }) {
  getAuthDatabase()
    .prepare(
      `INSERT INTO subtopic_annotations (patient_id, macro_tema, original_name, display_name, clinical_note, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT (patient_id, macro_tema, original_name)
       DO UPDATE SET display_name = excluded.display_name,
                     clinical_note = excluded.clinical_note,
                     updated_at = excluded.updated_at`,
    )
    .run(patientId, macroTema, originalName, displayName, clinicalNote || "", Date.now());
}
