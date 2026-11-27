const patients = {
  patient_ana: { name: "Ana de Exemplo", email: "ana@integration.test" },
  patient_bruno: { name: "Bruno de Exemplo", email: "bruno@integration.test" },
};

export function integrationEnabled() {
  return process.env.DIARY_INTEGRATION_DEMO === "1";
}

export function localDemo(request) {
  const host = request.headers.get("host")?.split(":")[0];
  if (host !== "localhost" && host !== "127.0.0.1") return false;
  const origin = request.headers.get("origin");
  return !origin || origin === `http://${request.headers.get("host")}`;
}

export function integrationPatient(id) {
  if (!Object.hasOwn(patients, id)) return null;
  return {
    id, ...patients[id], isDemo: true, createdAt: "2026-11-27T00:00:00Z",
    address: "", age: null, treatmentDurationMonths: null, psychiatricTreatment: false,
  };
}

export function integrationPatients() {
  return Object.keys(patients).map(integrationPatient);
}

export function patientAlias(email) {
  return integrationPatients().find((patient) => patient.email === email)?.id;
}
