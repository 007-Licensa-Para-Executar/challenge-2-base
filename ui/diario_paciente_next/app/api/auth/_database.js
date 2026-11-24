import { mkdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import path from "node:path";

let database;

function safeAlter(db, statement) {
  try {
    db.exec(statement);
  } catch {
    // A migração pode já ter sido aplicada em uma versão anterior.
  }
}

// Compartilha o mesmo SQLite entre cadastro, diário e gestão profissional.
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
      created_at INTEGER NOT NULL,
      address TEXT NOT NULL DEFAULT '',
      age INTEGER CHECK (age IS NULL OR age >= 0),
      treatment_duration_months INTEGER CHECK (treatment_duration_months IS NULL OR treatment_duration_months >= 0),
      psychiatric_treatment INTEGER NOT NULL DEFAULT 0 CHECK (psychiatric_treatment IN (0, 1))
    );
    CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY,
      patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
      expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS psychologist_profiles (
      id TEXT PRIMARY KEY CHECK (id = 'primary'),
      name TEXT NOT NULL,
      age INTEGER CHECK (age IS NULL OR age >= 0),
      photo BLOB,
      photo_mime TEXT,
      profession TEXT NOT NULL DEFAULT '',
      specialty TEXT NOT NULL DEFAULT '',
      insurance_plans TEXT NOT NULL DEFAULT '',
      resume TEXT NOT NULL DEFAULT '',
      professional_experiences TEXT NOT NULL DEFAULT '',
      experience_years REAL CHECK (experience_years IS NULL OR experience_years >= 0),
      updated_at INTEGER NOT NULL
    );
    INSERT OR IGNORE INTO psychologist_profiles (id, name, profession, updated_at)
      VALUES ('primary', 'Dra. Marina', 'Psicóloga', 0);
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

  const patientColumns = new Set(database.prepare("PRAGMA table_info(patients)").all().map((column) => column.name));
  if (!patientColumns.has("address")) safeAlter(database, "ALTER TABLE patients ADD COLUMN address TEXT NOT NULL DEFAULT ''");
  if (!patientColumns.has("age")) safeAlter(database, "ALTER TABLE patients ADD COLUMN age INTEGER CHECK (age IS NULL OR age >= 0)");
  if (!patientColumns.has("treatment_duration_months")) {
    safeAlter(database, "ALTER TABLE patients ADD COLUMN treatment_duration_months INTEGER CHECK (treatment_duration_months IS NULL OR treatment_duration_months >= 0)");
  }
  if (!patientColumns.has("psychiatric_treatment")) {
    safeAlter(database, "ALTER TABLE patients ADD COLUMN psychiatric_treatment INTEGER NOT NULL DEFAULT 0 CHECK (psychiatric_treatment IN (0, 1))");
  }

  const profileColumns = new Set(database.prepare("PRAGMA table_info(psychologist_profiles)").all().map((column) => column.name));
  if (!profileColumns.has("insurance_plans")) {
    safeAlter(database, "ALTER TABLE psychologist_profiles ADD COLUMN insurance_plans TEXT NOT NULL DEFAULT ''");
  }

  for (const [name, definition] of [
    ["input_type", "TEXT NOT NULL DEFAULT 'text'"],
    ["audio_name", "TEXT"],
    ["audio_duration", "TEXT"],
    ["audio_data", "TEXT"],
    ["theme_macro", "TEXT"],
    ["theme_confidence", "REAL"],
    ["theme_scores_json", "TEXT"],
    ["polarity_score", "REAL"],
    ["agent1_json", "TEXT"],
    ["analysis_source", "TEXT"],
    ["analyzed_at", "INTEGER"],
  ]) {
    safeAlter(database, `ALTER TABLE diary_entries ADD COLUMN ${name} ${definition}`);
  }

  return database;
}

// Retorna apenas dados de exibição; hashes e salts de autenticação não saem do módulo.
export function listarPacientesDoPortal() {
  const db = getAuthDatabase();
  const patients = db.prepare(
    `SELECT id, name, email, created_at, address, age, treatment_duration_months, psychiatric_treatment
     FROM patients ORDER BY created_at DESC`,
  ).all();
  const stats = db.prepare(`
    SELECT patient_id,
      COUNT(*) AS total_entries,
      SUM(CASE WHEN is_risk_emotion = 1 THEN 1 ELSE 0 END) AS risk_entries,
      SUM(CASE
        WHEN polarity_score IS NOT NULL AND polarity_score >= 0.15 THEN 1
        WHEN polarity_score IS NULL AND primary_emotion IN ('alegria', 'calma', 'afeto', 'esperanca') THEN 1
        ELSE 0 END) AS positive_entries,
      SUM(CASE
        WHEN polarity_score IS NOT NULL AND polarity_score <= -0.15 THEN 1
        WHEN polarity_score IS NULL AND (is_risk_emotion = 1 OR primary_emotion IN ('tristeza', 'raiva', 'medo', 'ansiedade', 'nojinho', 'vergonha', 'inveja', 'tedio')) THEN 1
        ELSE 0 END) AS negative_entries,
      MAX(created_at) AS last_entry_at
    FROM diary_entries GROUP BY patient_id
  `);
  const statsByPatient = new Map(stats.all().map((row) => [row.patient_id, row]));

  return patients.map((patient) => {
    const row = statsByPatient.get(patient.id);
    const total = Number(row?.total_entries || 0);
    const positive = Number(row?.positive_entries || 0);
    const negative = Number(row?.negative_entries || 0);
    return {
      ...toPortalPatientRecord(patient),
      entryCount: total,
      riskCount: Number(row?.risk_entries || 0),
      valenceBreakdown: { positive, neutral: Math.max(0, total - positive - negative), negative },
      lastEntryAt: row?.last_entry_at ? new Date(row.last_entry_at).toISOString() : null,
    };
  });
}

function toPortalPatientRecord(patient) {
  return {
    id: patient.id,
    name: patient.name,
    email: patient.email,
    createdAt: new Date(patient.created_at).toISOString(),
    address: patient.address,
    age: patient.age,
    treatmentDurationMonths: patient.treatment_duration_months,
    psychiatricTreatment: Boolean(patient.psychiatric_treatment),
  };
}

export function updatePatientProfile(id, profile) {
  const db = getAuthDatabase();
  const result = db.prepare(
    `UPDATE patients
     SET name = ?, address = ?, age = ?, treatment_duration_months = ?, psychiatric_treatment = ?
     WHERE id = ?`,
  ).run(
    profile.name,
    profile.address,
    profile.age,
    profile.treatmentDurationMonths,
    profile.psychiatricTreatment ? 1 : 0,
    id,
  );

  if (!result.changes) return null;
  return toPortalPatientRecord(db.prepare(
    `SELECT id, name, email, created_at, address, age, treatment_duration_months, psychiatric_treatment
     FROM patients WHERE id = ?`,
  ).get(id));
}

export function getPsychologistProfile() {
  const profile = getAuthDatabase().prepare(
    `SELECT name, age, profession, specialty, insurance_plans, resume, professional_experiences,
            experience_years, photo IS NOT NULL AS has_photo, updated_at
     FROM psychologist_profiles WHERE id = 'primary'`,
  ).get();

  if (!profile) throw new Error("Perfil da psicóloga não encontrado.");
  return {
    name: profile.name,
    age: profile.age,
    profession: profile.profession,
    specialty: profile.specialty,
    insurancePlans: profile.insurance_plans,
    resume: profile.resume,
    professionalExperiences: profile.professional_experiences,
    experienceYears: profile.experience_years,
    photoUrl: profile.has_photo ? `/api/psicologa/perfil/foto?v=${profile.updated_at}` : null,
    updatedAt: profile.updated_at,
  };
}

export function getPsychologistProfilePhoto() {
  const profile = getAuthDatabase().prepare(
    "SELECT photo, photo_mime FROM psychologist_profiles WHERE id = 'primary'",
  ).get();
  if (!profile?.photo) return null;
  return { data: new Uint8Array(profile.photo), mimeType: profile.photo_mime };
}

export function updatePsychologistProfile(profile) {
  getAuthDatabase().prepare(
    `UPDATE psychologist_profiles
     SET name = ?, age = ?, profession = ?, specialty = ?, insurance_plans = ?, resume = ?,
         professional_experiences = ?, experience_years = ?,
         photo = COALESCE(?, photo), photo_mime = COALESCE(?, photo_mime), updated_at = ?
     WHERE id = 'primary'`,
  ).run(
    profile.name,
    profile.age,
    profile.profession,
    profile.specialty,
    profile.insurancePlans,
    profile.resume,
    profile.professionalExperiences,
    profile.experienceYears,
    profile.photo,
    profile.photoMime,
    Date.now(),
  );
  return getPsychologistProfile();
}
