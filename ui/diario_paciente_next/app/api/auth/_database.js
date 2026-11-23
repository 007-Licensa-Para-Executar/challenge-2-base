import { mkdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import path from "node:path";

let database;

function safeAlter(db, statement) {
  try {
    db.exec(statement);
  } catch {
    // Coluna já existe.
  }
}

// Compartilha o mesmo SQLite entre cadastro, login, diário e painel profissional.
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
      theme_macro TEXT,
      theme_confidence REAL,
      theme_scores_json TEXT,
      polarity_score REAL,
      agent1_json TEXT,
      analysis_source TEXT,
      analyzed_at INTEGER,
      created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS clinical_reports (
      id TEXT PRIMARY KEY,
      patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
      file_name TEXT NOT NULL,
      file_size INTEGER NOT NULL DEFAULT 0,
      mime_type TEXT,
      notes TEXT,
      uploaded_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS subtopic_annotations (
      patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
      macro_tema TEXT NOT NULL,
      original_name TEXT NOT NULL,
      display_name TEXT NOT NULL,
      clinical_note TEXT,
      updated_at INTEGER NOT NULL,
      PRIMARY KEY (patient_id, macro_tema, original_name)
    );
  `);

  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN input_type TEXT NOT NULL DEFAULT 'text'");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN audio_name TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN audio_duration TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN audio_data TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN theme_macro TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN theme_confidence REAL");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN theme_scores_json TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN polarity_score REAL");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN agent1_json TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN analysis_source TEXT");
  safeAlter(database, "ALTER TABLE diary_entries ADD COLUMN analyzed_at INTEGER");

  return database;
}

// Retorna somente os campos de exibição; hash e salt nunca saem do módulo.
export function listarPacientesDoPortal() {
  const db = getAuthDatabase();
  const pacientes = db
    .prepare("SELECT id, name, email, created_at FROM patients ORDER BY created_at DESC")
    .all();

  const statsStmt = db.prepare(`
    SELECT
      patient_id,
      COUNT(*) AS total_entries,
      SUM(CASE WHEN is_risk_emotion = 1 THEN 1 ELSE 0 END) AS risk_entries,
      SUM(CASE
        WHEN polarity_score IS NOT NULL AND polarity_score >= 0.15 THEN 1
        WHEN polarity_score IS NULL AND primary_emotion IN ('alegria', 'calma', 'afeto', 'esperanca') THEN 1
        ELSE 0
      END) AS positive_entries,
      SUM(CASE
        WHEN polarity_score IS NOT NULL AND polarity_score <= -0.15 THEN 1
        WHEN polarity_score IS NULL AND (is_risk_emotion = 1 OR primary_emotion IN ('tristeza', 'raiva', 'medo', 'ansiedade', 'nojinho', 'vergonha', 'inveja', 'tedio')) THEN 1
        ELSE 0
      END) AS negative_entries,
      MAX(created_at) AS last_entry_at
    FROM diary_entries
    GROUP BY patient_id
  `);

  const statsByPatient = new Map(statsStmt.all().map((row) => [row.patient_id, row]));

  return pacientes.map((patient) => {
    const st = statsByPatient.get(patient.id);
    const total = Number(st?.total_entries || 0);
    const pos = Number(st?.positive_entries || 0);
    const neg = Number(st?.negative_entries || 0);
    const neu = Math.max(0, total - pos - neg);
    return {
      id: patient.id,
      name: patient.name,
      email: patient.email,
      createdAt: new Date(patient.created_at).toISOString(),
      entryCount: total,
      riskCount: Number(st?.risk_entries || 0),
      valenceBreakdown: { positive: pos, neutral: neu, negative: neg },
      lastEntryAt: st?.last_entry_at ? new Date(st.last_entry_at).toISOString() : null,
    };
  });
}
