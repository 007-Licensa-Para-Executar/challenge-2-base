"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { EditablePatientProfile, PortalPatient } from "./types";
import styles from "./patient-management.module.css";

type PatientForm = {
  name: string;
  address: string;
  age: string;
  treatmentDurationMonths: string;
  psychiatricTreatment: boolean;
};

function toForm(patient: PortalPatient): PatientForm {
  return {
    name: patient.fullName,
    address: patient.address,
    age: patient.age === null ? "" : String(patient.age),
    treatmentDurationMonths: patient.treatmentDurationMonths === null
      ? ""
      : String(patient.treatmentDurationMonths),
    psychiatricTreatment: patient.psychiatricTreatment,
  };
}

type Props = {
  open: boolean;
  patient: PortalPatient;
  onClose: () => void;
  onSave: (patient: EditablePatientProfile) => void;
};

export default function PatientProfileEditor({ open, patient, onClose, onSave }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [values, setValues] = useState<PatientForm>(() => toForm(patient));
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setValues(toForm(patient));
    setError("");
  }, [
    open,
    patient.id,
    patient.fullName,
    patient.address,
    patient.age,
    patient.treatmentDurationMonths,
    patient.psychiatricTreatment,
  ]);

  function updateField(field: keyof PatientForm, value: string | boolean) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = values.name.trim();
    if (name.length < 2) {
      setError("Informe um nome com pelo menos 2 caracteres.");
      return;
    }

    setIsSaving(true);
    setError("");

    try {
      const response = await fetch(`/api/psicologa/pacientes/${encodeURIComponent(patient.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          address: values.address,
          age: values.age === "" ? null : Number(values.age),
          treatmentDurationMonths: values.treatmentDurationMonths === ""
            ? null
            : Number(values.treatmentDurationMonths),
          psychiatricTreatment: values.psychiatricTreatment,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload?.patient) {
        throw new Error(payload?.message || "Não foi possível salvar o perfil do paciente.");
      }

      onSave(payload.patient as EditablePatientProfile);
      onClose();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Não foi possível salvar o perfil do paciente.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className={styles.profileDialog}
      aria-labelledby="patient-profile-title"
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
            <p className={styles.eyebrow}>PERFIL DO PACIENTE</p>
            <h2 id="patient-profile-title">Editar paciente</h2>
            <p>Atualize os dados de cadastro e acompanhamento.</p>
          </div>
          <button
            className={styles.profileCloseButton}
            type="button"
            aria-label="Fechar edição do paciente"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className={styles.profileFormGrid}>
          <label className={`${styles.profileField} ${styles.profileFieldWide}`}>
            <span>Nome <b aria-hidden="true">*</b></span>
            <input
              autoFocus
              required
              minLength={2}
              maxLength={120}
              value={values.name}
              onChange={(event) => updateField("name", event.currentTarget.value)}
            />
          </label>
          <label className={`${styles.profileField} ${styles.profileFieldWide}`}>
            <span>Endereço</span>
            <textarea
              rows={2}
              maxLength={500}
              placeholder="Rua, número, bairro e cidade"
              value={values.address}
              onChange={(event) => updateField("address", event.currentTarget.value)}
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
            <span>Tempo de tratamento comigo (meses)</span>
            <input
              type="number"
              min="0"
              step="1"
              value={values.treatmentDurationMonths}
              onChange={(event) => updateField("treatmentDurationMonths", event.currentTarget.value)}
            />
          </label>
          <label className={`${styles.profileCheckboxField} ${styles.profileFieldWide}`}>
            <input
              type="checkbox"
              checked={values.psychiatricTreatment}
              onChange={(event) => updateField("psychiatricTreatment", event.currentTarget.checked)}
            />
            <span>
              <strong>Também faz acompanhamento psiquiátrico</strong>
              <small>Marque se o paciente também faz tratamento com psiquiatra.</small>
            </span>
          </label>
        </div>

        {error ? <p className={styles.formError} role="alert">{error}</p> : null}

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
