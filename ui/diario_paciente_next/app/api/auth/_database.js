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
  `);

  const profileColumns = database.prepare("PRAGMA table_info(psychologist_profiles)").all();
  if (!profileColumns.some((column) => column.name === "insurance_plans")) {
    database.exec(
      "ALTER TABLE psychologist_profiles ADD COLUMN insurance_plans TEXT NOT NULL DEFAULT ''",
    );
  }

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

export function getPsychologistProfile() {
  const profile = getAuthDatabase()
    .prepare(
      `SELECT name, age, profession, specialty, insurance_plans, resume, professional_experiences,
              experience_years, photo IS NOT NULL AS has_photo, updated_at
       FROM psychologist_profiles WHERE id = 'primary'`,
    )
    .get();

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
    photoUrl: profile.has_photo
      ? `/api/psicologa/perfil/foto?v=${profile.updated_at}`
      : null,
    updatedAt: profile.updated_at,
  };
}

export function getPsychologistProfilePhoto() {
  const profile = getAuthDatabase()
    .prepare("SELECT photo, photo_mime FROM psychologist_profiles WHERE id = 'primary'")
    .get();

  if (!profile?.photo) return null;
  return { data: new Uint8Array(profile.photo), mimeType: profile.photo_mime };
}

export function updatePsychologistProfile(profile) {
  getAuthDatabase()
    .prepare(
      `UPDATE psychologist_profiles
       SET name = ?, age = ?, profession = ?, specialty = ?, insurance_plans = ?, resume = ?,
           professional_experiences = ?, experience_years = ?,
           photo = COALESCE(?, photo), photo_mime = COALESCE(?, photo_mime), updated_at = ?
       WHERE id = 'primary'`,
    )
    .run(
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
