"use client";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import styles from "./patient-management.module.css";

export type PsychologistProfile = {
  name: string;
  age: number | null;
  profession: string;
  specialty: string;
  insurancePlans: string;
  resume: string;
  professionalExperiences: string;
  experienceYears: number | null;
  photoUrl: string | null;
  updatedAt: number;
};

type ProfileForm = {
  name: string;
  age: string;
  profession: string;
  specialty: string;
  insurancePlans: string;
  resume: string;
  professionalExperiences: string;
  experienceYears: string;
};

export function getPsychologistInitials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const nameWords = words.filter(
    (word) => !["dra.", "dr.", "doutora", "doutor", "profa.", "prof."].includes(word.toLocaleLowerCase("pt-BR")),
  );
  const initials = nameWords.length > 1
    ? `${nameWords[0][0]}${nameWords[nameWords.length - 1][0]}`
    : nameWords[0]?.slice(0, 2) || "PS";
  return initials.toLocaleUpperCase("pt-BR");
}

function toForm(profile: PsychologistProfile): ProfileForm {
  return {
    name: profile.name,
    age: profile.age === null ? "" : String(profile.age),
    profession: profile.profession,
    specialty: profile.specialty,
    insurancePlans: profile.insurancePlans,
    resume: profile.resume,
    professionalExperiences: profile.professionalExperiences,
    experienceYears: profile.experienceYears === null ? "" : String(profile.experienceYears),
  };
}

type Props = {
  open: boolean;
  profile: PsychologistProfile;
  onClose: () => void;
  onSave: (profile: PsychologistProfile) => void;
};

export default function PsychologistProfileEditor({ open, profile, onClose, onSave }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [values, setValues] = useState<ProfileForm>(() => toForm(profile));
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(profile.photoUrl);
  const [error, setError] = useState("");
  const [photoError, setPhotoError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setValues(toForm(profile));
    setPhoto(null);
    setPhotoPreview(profile.photoUrl);
    setError("");
    setPhotoError("");
  }, [open, profile]);

  useEffect(() => {
    return () => {
      if (photoPreview?.startsWith("blob:")) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  function updateField(field: keyof ProfileForm, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function handlePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setPhoto(null);
      setPhotoPreview(profile.photoUrl);
      setPhotoError("Use uma foto JPG, PNG ou WebP.");
      event.currentTarget.value = "";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setPhoto(null);
      setPhotoPreview(profile.photoUrl);
      setPhotoError("A foto deve ter no máximo 2 MB.");
      event.currentTarget.value = "";
      return;
    }

    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
    setPhotoError("");
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!values.name.trim()) {
      setError("Informe o nome da psicóloga.");
      return;
    }
    if (photoError) {
      setError(photoError);
      return;
    }

    setIsSaving(true);
    setError("");
    const formData = new FormData();
    formData.set("name", values.name.trim());
    formData.set("age", values.age);
    formData.set("profession", values.profession);
    formData.set("specialty", values.specialty);
    formData.set("insurancePlans", values.insurancePlans);
    formData.set("resume", values.resume);
    formData.set("professionalExperiences", values.professionalExperiences);
    formData.set("experienceYears", values.experienceYears);
    if (photo) formData.set("photo", photo);

    try {
      const response = await fetch("/api/psicologa/perfil", {
        method: "PATCH",
        body: formData,
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload?.profile) {
        throw new Error(payload?.message || "Não foi possível salvar o perfil.");
      }

      onSave(payload.profile as PsychologistProfile);
      onClose();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Não foi possível salvar o perfil.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className={styles.profileDialog}
      aria-labelledby="psychologist-profile-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose();
      }}
    >
      <form className={styles.profileEditor} onSubmit={handleSubmit}>
        <div className={styles.profileEditorHeading}>
          <div>
            <p className={styles.eyebrow}>PERFIL PROFISSIONAL</p>
            <h2 id="psychologist-profile-title">Editar perfil</h2>
            <p>Atualize as informações exibidas na gestão da clínica.</p>
          </div>
          <button
            className={styles.profileCloseButton}
            type="button"
            aria-label="Fechar edição do perfil"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className={styles.profilePhotoField}>
          {photoPreview ? (
            <img className={styles.profilePhotoPreview} src={photoPreview} alt="" />
          ) : (
            <span className={styles.profilePhotoPlaceholder} aria-hidden="true">
              {getPsychologistInitials(values.name)}
            </span>
          )}
          <label className={styles.profileField}>
            <span>Foto</span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handlePhotoChange}
            />
            <small>JPG, PNG ou WebP. Máximo de 2 MB.</small>
          </label>
        </div>

        <div className={styles.profileFormGrid}>
          <label className={styles.profileField}>
            <span>Nome <b aria-hidden="true">*</b></span>
            <input
              autoFocus
              required
              maxLength={120}
              value={values.name}
              onChange={(event) => updateField("name", event.currentTarget.value)}
            />
          </label>
          <label className={styles.profileField}>
            <span>Idade</span>
            <input
              type="number"
              min="0"
              step="1"
              value={values.age}
              onChange={(event) => updateField("age", event.currentTarget.value)}
            />
          </label>
          <label className={styles.profileField}>
            <span>Profissão</span>
            <input
              maxLength={120}
              value={values.profession}
              onChange={(event) => updateField("profession", event.currentTarget.value)}
            />
          </label>
          <label className={styles.profileField}>
            <span>Especialização</span>
            <input
              maxLength={200}
              value={values.specialty}
              onChange={(event) => updateField("specialty", event.currentTarget.value)}
            />
          </label>
          <label className={styles.profileField}>
            <span>Tempo de experiência (anos)</span>
            <input
              type="number"
              min="0"
              step="any"
              value={values.experienceYears}
              onChange={(event) => updateField("experienceYears", event.currentTarget.value)}
            />
          </label>
          <label className={`${styles.profileField} ${styles.profileFieldWide}`}>
            <span>Convênios atendidos</span>
            <textarea
              rows={3}
              maxLength={2000}
              placeholder="Ex.: Unimed, Bradesco Saúde"
              value={values.insurancePlans}
              onChange={(event) => updateField("insurancePlans", event.currentTarget.value)}
            />
            <small>Separe os convênios por vírgula ou informe um por linha.</small>
          </label>
          <label className={`${styles.profileField} ${styles.profileFieldWide}`}>
            <span>Currículo</span>
            <textarea
              rows={4}
              maxLength={5000}
              value={values.resume}
              onChange={(event) => updateField("resume", event.currentTarget.value)}
            />
          </label>
          <label className={`${styles.profileField} ${styles.profileFieldWide}`}>
            <span>Experiências profissionais</span>
            <textarea
              rows={4}
              maxLength={5000}
              value={values.professionalExperiences}
              onChange={(event) => updateField("professionalExperiences", event.currentTarget.value)}
            />
          </label>
        </div>

        {error || photoError ? (
          <p className={styles.formError} role="alert">{error || photoError}</p>
        ) : null}

        <div className={styles.profileEditorActions}>
          <button className={styles.profileCancelButton} type="button" onClick={onClose}>
            Cancelar
          </button>
          <button className={styles.profileSaveButton} type="submit" disabled={isSaving}>
            {isSaving ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
