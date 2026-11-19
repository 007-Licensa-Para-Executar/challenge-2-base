import {
  createHash,
  randomBytes,
  randomUUID,
  scrypt,
  timingSafeEqual,
} from "node:crypto";
import { mkdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import path from "node:path";
import { promisify } from "node:util";

const scryptAsync = promisify(scrypt);
const scryptOptions = { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
const sessionCookieName = "diario_sessao";
const sessionLifetime = 7 * 24 * 60 * 60;
let database;

// Cria o banco local na primeira chamada. AUTH_DATABASE_PATH pode apontar para outro arquivo.
function getDatabase() {
  if (database) return database;

  const file = process.env.AUTH_DATABASE_PATH || path.join(process.cwd(), "data", "auth.sqlite");
  if (file !== ":memory:") mkdirSync(path.dirname(file), { recursive: true });

  database = new DatabaseSync(file);
  database.exec(`
    PRAGMA foreign_keys = ON;
    PRAGMA busy_timeout = 5000;
    CREATE TABLE IF NOT EXISTS patients (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT NOT NULL COLLATE NOCASE UNIQUE,
      password_salt TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY,
      patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
      expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS diary_entries (
      id TEXT PRIMARY KEY,
      patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
      text TEXT NOT NULL,
      primary_emotion TEXT NOT NULL,
      character TEXT NOT NULL,
      color_hex TEXT NOT NULL,
      color_secondary_hex TEXT,
      sub_emotion_name TEXT NOT NULL,
      sub_emotion_symbol TEXT NOT NULL,
      confidence REAL NOT NULL,
      is_risk_emotion INTEGER NOT NULL DEFAULT 0,
      input_type TEXT NOT NULL DEFAULT 'text',
      audio_name TEXT,
      audio_duration TEXT,
      audio_data TEXT,
      created_at INTEGER NOT NULL
    );
  `);

  // Migrações graduais seguras caso a tabela já existisse
  try {
    database.exec("ALTER TABLE diary_entries ADD COLUMN input_type TEXT NOT NULL DEFAULT 'text'");
  } catch {}
  try {
    database.exec("ALTER TABLE diary_entries ADD COLUMN audio_name TEXT");
  } catch {}
  try {
    database.exec("ALTER TABLE diary_entries ADD COLUMN audio_duration TEXT");
  } catch {}
  try {
    database.exec("ALTER TABLE diary_entries ADD COLUMN audio_data TEXT");
  } catch {}

  return database;
}

async function hashPassword(password, salt) {
  return Buffer.from(await scryptAsync(password, salt, 64, scryptOptions));
}

// Salva somente hash e salt da senha; e-mail fica normalizado para evitar duplicatas por caixa.
export async function criarPaciente({ nome, email, senha }) {
  const db = getDatabase();
  const id = randomUUID();
  const salt = randomBytes(16);
  const hash = await hashPassword(senha, salt);

  try {
    db.prepare(
      `INSERT INTO patients (id, name, email, password_salt, password_hash, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
    ).run(id, nome, email, salt.toString("hex"), hash.toString("hex"), Date.now());
    return { ok: true };
  } catch (error) {
    if (error.message?.includes("UNIQUE constraint failed: patients.email")) {
      return { ok: false, motivo: "email_em_uso" };
    }
    throw error;
  }
}

// Confere a senha e cria uma sessão opaca armazenada no banco e enviada em cookie HTTP-only.
export async function autenticarPaciente(email, senha) {
  const db = getDatabase();
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
  const cookie = request.headers
    .get("cookie")
    ?.split(";")
    .map((parte) => parte.trim())
    .find((parte) => parte.startsWith(`${sessionCookieName}=`));
  const token = cookie?.slice(sessionCookieName.length + 1);
  if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) return null;

  const tokenHash = createHash("sha256").update(token).digest("hex");
  const paciente = getDatabase()
    .prepare(
      `SELECT patients.id, patients.name, patients.email
       FROM sessions JOIN patients ON patients.id = sessions.patient_id
       WHERE sessions.token_hash = ? AND sessions.expires_at > ?`,
    )
    .get(tokenHash, Date.now());

  return paciente ? { ...paciente } : null;
}

// Salva um relato do diário associado ao paciente e à emoção detectada pelo modelo (com suporte a áudio)
export function salvarDiario({
  patientId,
  text,
  emotion,
  inputType = "text",
  audioName = null,
  audioDuration = null,
  audioData = null,
}) {
  const db = getDatabase();
  const id = randomUUID();
  const agora = Date.now();

  db.prepare(
    `INSERT INTO diary_entries (
      id, patient_id, text, primary_emotion, character, color_hex,
      color_secondary_hex, sub_emotion_name, sub_emotion_symbol,
      confidence, is_risk_emotion, input_type, audio_name, audio_duration, audio_data, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
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
    agora
  );

  return { id, created_at: agora };
}

// Retorna o histórico de relatos do paciente ordenados do mais recente para o mais antigo como plain objects
export function listarDiarios(patientId) {
  const db = getDatabase();
  const rows = db
    .prepare(
      `SELECT * FROM diary_entries WHERE patient_id = ? ORDER BY created_at DESC`
    )
    .all(patientId);

  return rows.map((r) => ({ ...r }));
}

