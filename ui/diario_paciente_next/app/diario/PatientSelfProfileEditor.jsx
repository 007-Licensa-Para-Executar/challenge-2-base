"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./patient-self-profile.module.css";

function getInitials(name = "") {
  const names = name.trim().split(/\s+/).filter(Boolean);
  return names.length > 1
    ? `${names[0][0]}${names[names.length - 1][0]}`.toLocaleUpperCase("pt-BR")
    : (names[0]?.slice(0, 2) || "PA").toLocaleUpperCase("pt-BR");
}

function profileToForm(profile) {
  return {
    name: profile.name || "",
    email: profile.email || "",
    age: profile.age === null || profile.age === undefined ? "" : String(profile.age),
    address: profile.address || "",
    insurancePlan: profile.insurancePlan || "",
  };
}

export default function PatientSelfProfileEditor({ patient, onSave }) {
  const dialogRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [profile, setProfile] = useState(null);
  const [values, setValues] = useState({ name: "", email: "", age: "", address: "", insurancePlan: "" });
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    let active = true;
    setLoading(true);
    setError("");
    setProfile(null);
    setPhotoPreview(null);
    setPhoto(null);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");

    fetch("/api/auth/perfil", { cache: "no-store" })
      .then(async (response) => {
        const payload = await response.json().catch(() => null);
        if (!response.ok || !payload?.profile) {
          throw new Error(payload?.message || "Não foi possível carregar seu perfil.");
        }
        if (!active) return;
        setProfile(payload.profile);
        setValues(profileToForm(payload.profile));
        setPhotoPreview(payload.profile.photoUrl || null);
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Não foi possível carregar seu perfil.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [open]);

  useEffect(() => {
    return () => {
      if (photoPreview?.startsWith("blob:")) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  function updateField(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function handlePhotoChange(event) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setPhoto(null);
      setPhotoPreview(profile?.photoUrl || null);
      setError("Use uma foto JPG, PNG ou WebP.");
      event.currentTarget.value = "";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setPhoto(null);
      setPhotoPreview(profile?.photoUrl || null);
      setError("A foto deve ter no máximo 2 MB.");
      event.currentTarget.value = "";
      return;
    }

    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const passwordFieldsStarted = currentPassword || newPassword || confirmPassword;
    if (passwordFieldsStarted && (!currentPassword || !newPassword || !confirmPassword)) {
      setError("Para trocar a senha, preencha os três campos.");
      return;
    }
    if (newPassword && newPassword !== confirmPassword) {
      setError("A nova senha e a confirmação não conferem.");
      return;
    }

    setSaving(true);
    setError("");
    const formData = new FormData();
    formData.set("name", values.name.trim());
    formData.set("email", values.email.trim());
    formData.set("age", values.age);
    formData.set("address", values.address);
    formData.set("insurancePlan", values.insurancePlan);
    if (photo) formData.set("photo", photo);
    if (newPassword) {
      formData.set("currentPassword", currentPassword);
      formData.set("newPassword", newPassword);
    }

    try {
      const response = await fetch("/api/auth/perfil", { method: "PATCH", body: formData });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload?.profile) {
        throw new Error(payload?.message || "Não foi possível salvar seu perfil.");
      }

      setProfile(payload.profile);
      onSave?.(payload.profile);
      setOpen(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Não foi possível salvar seu perfil.");
    } finally {
      setSaving(false);
    }
  }

  function close() {
    if (saving) return;
    setOpen(false);
  }

  return (
    <>
      <button
        className={styles.profileTrigger}
        type="button"
        aria-haspopup="dialog"
        aria-label={`Editar perfil de ${patient?.name || "Paciente"}`}
        onClick={() => setOpen(true)}
      >
        {patient?.photoUrl ? (
          <img className={styles.triggerAvatar} src={patient.photoUrl} alt="" />
        ) : (
          <span className={styles.triggerAvatarPlaceholder} aria-hidden="true">
            {getInitials(patient?.name)}
          </span>
        )}
        <span className={styles.profileTriggerName}>{patient?.name || "Paciente"}</span>
      </button>

      <dialog
        ref={dialogRef}
        className={styles.profileDialog}
        aria-labelledby="patient-self-profile-title"
        onCancel={(event) => {
          event.preventDefault();
          close();
        }}
        onClick={(event) => {
          if (event.target === dialogRef.current) close();
        }}
      >
        <form className={styles.profileEditor} onSubmit={handleSubmit}>
          <header className={styles.profileHeading}>
            <div>
              <p className={styles.eyebrow}>SEUS DADOS</p>
              <h2 id="patient-self-profile-title">Meu perfil</h2>
              <p>Atualize as informações da sua conta.</p>
            </div>
            <button
              className={styles.closeButton}
              type="button"
              aria-label="Fechar edição do perfil"
              onClick={close}
            >
              ×
            </button>
          </header>

          {loading ? (
            <p className={styles.loadingMessage} role="status">Carregando seus dados…</p>
          ) : !profile ? (
            <p className={styles.loadingMessage} role="status">
              Não foi possível carregar os dados do perfil. Feche esta janela e tente novamente.
            </p>
          ) : (
            <>
              <div className={styles.photoRow}>
                {photoPreview ? (
                  <img className={styles.photoPreview} src={photoPreview} alt="Prévia da foto de perfil" />
                ) : (
                  <span className={styles.photoPlaceholder} aria-hidden="true">
                    {getInitials(values.name)}
                  </span>
                )}
                <label className={styles.field}>
                  <span>Foto de perfil</span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handlePhotoChange}
                  />
                  <small>JPG, PNG ou WebP. Máximo de 2 MB.</small>
                </label>
              </div>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>Nome <b aria-hidden="true">*</b></span>
                  <input
                    autoFocus
                    required
                    minLength={2}
                    maxLength={120}
                    autoComplete="name"
                    value={values.name}
                    onChange={(event) => updateField("name", event.currentTarget.value)}
                  />
                </label>
                <label className={styles.field}>
                  <span>E-mail <b aria-hidden="true">*</b></span>
                  <input
                    required
                    type="email"
                    maxLength={254}
                    autoComplete="email"
                    value={values.email}
                    onChange={(event) => updateField("email", event.currentTarget.value)}
                  />
                </label>
                <label className={styles.field}>
                  <span>Idade</span>
                  <input
                    type="number"
                    min="0"
                    max="130"
                    step="1"
                    inputMode="numeric"
                    value={values.age}
                    onChange={(event) => updateField("age", event.currentTarget.value)}
                  />
                </label>
                <label className={styles.field}>
                  <span>Convênio</span>
                  <input
                    maxLength={200}
                    placeholder="Ex.: Unimed"
                    value={values.insurancePlan}
                    onChange={(event) => updateField("insurancePlan", event.currentTarget.value)}
                  />
                </label>
                <label className={`${styles.field} ${styles.fieldWide}`}>
                  <span>Endereço</span>
                  <textarea
                    rows={2}
                    maxLength={500}
                    autoComplete="street-address"
                    placeholder="Rua, número, bairro e cidade"
                    value={values.address}
                    onChange={(event) => updateField("address", event.currentTarget.value)}
                  />
                </label>
              </div>

              <section className={styles.passwordSection} aria-labelledby="password-section-title">
                <div>
                  <h3 id="password-section-title">Atualizar senha</h3>
                  <p>Os campos são opcionais. Preencha os três somente para trocar sua senha.</p>
                </div>
                <div className={styles.formGrid}>
                  <label className={styles.field}>
                    <span>Senha atual</span>
                    <input
                      type="password"
                      maxLength={128}
                      autoComplete="new-password"
                      value={currentPassword}
                      onChange={(event) => setCurrentPassword(event.currentTarget.value)}
                    />
                  </label>
                  <label className={styles.field}>
                    <span>Nova senha</span>
                    <input
                      type="password"
                      minLength={8}
                      maxLength={128}
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.currentTarget.value)}
                    />
                    <small>Use entre 8 e 128 caracteres.</small>
                  </label>
                  <label className={`${styles.field} ${styles.fieldWide}`}>
                    <span>Confirmar nova senha</span>
                    <input
                      type="password"
                      minLength={8}
                      maxLength={128}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.currentTarget.value)}
                    />
                  </label>
                </div>
              </section>
            </>
          )}

          {error ? <p className={styles.formError} role="alert">{error}</p> : null}

          <footer className={styles.actions}>
            <button className={styles.cancelButton} type="button" onClick={close} disabled={saving}>
              Cancelar
            </button>
            <button className={styles.saveButton} type="submit" disabled={loading || saving || !profile}>
              {saving ? "Salvando…" : "Salvar alterações"}
            </button>
          </footer>
        </form>
      </dialog>
    </>
  );
}
