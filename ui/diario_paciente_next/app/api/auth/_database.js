import { mkdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import path from "node:path";

let database;

// Compartilha o mesmo SQLite entre cadastro, login e listagem profissional.
export function getAuthDatabase() {
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
  `);

  return database;
}

// Retorna somente os campos de exibição; hash e salt nunca saem do módulo.
export function listarPacientesDoPortal() {
  return getAuthDatabase()
    .prepare("SELECT id, name, email, created_at FROM patients ORDER BY created_at DESC")
    .all()
    .map((patient) => ({
      id: patient.id,
      name: patient.name,
      email: patient.email,
      createdAt: new Date(patient.created_at).toISOString(),
    }));
}
