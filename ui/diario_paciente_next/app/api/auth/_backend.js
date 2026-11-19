import {
  createHash,
  randomBytes,
  randomUUID,
  scrypt,
  timingSafeEqual,
} from "node:crypto";
import { promisify } from "node:util";
import { getAuthDatabase } from "./_database";

const scryptAsync = promisify(scrypt);
const scryptOptions = { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
const sessionCookieName = "diario_sessao";
const sessionLifetime = 7 * 24 * 60 * 60;
async function hashPassword(password, salt) {
  return Buffer.from(await scryptAsync(password, salt, 64, scryptOptions));
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
  const cookie = request.headers
    .get("cookie")
    ?.split(";")
    .map((parte) => parte.trim())
    .find((parte) => parte.startsWith(`${sessionCookieName}=`));
  const token = cookie?.slice(sessionCookieName.length + 1);
  if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) return null;

  const tokenHash = createHash("sha256").update(token).digest("hex");
  const paciente = getAuthDatabase()
    .prepare(
      `SELECT patients.id, patients.name, patients.email
       FROM sessions JOIN patients ON patients.id = sessions.patient_id
       WHERE sessions.token_hash = ? AND sessions.expires_at > ?`,
    )
    .get(tokenHash, Date.now());

  return paciente || null;
}
