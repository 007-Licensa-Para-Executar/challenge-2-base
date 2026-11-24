import assert from "node:assert/strict";
import test from "node:test";
import {
  EXTERNAL_SUPERVISORS,
  SUPERVISOR_FILTER_GROUPS,
  filterExternalSupervisors,
  shouldShowExternalSupervisorsButton,
} from "../app/psicologa/supervisorCatalog.ts";

test("o botão de supervisores depende de haver paciente selecionado", () => {
  assert.equal(shouldShowExternalSupervisorsButton(null), false);
  assert.equal(shouldShowExternalSupervisorsButton(undefined), false);
  assert.equal(shouldShowExternalSupervisorsButton("  "), false);
  assert.equal(shouldShowExternalSupervisorsButton("paciente-demo"), true);
});

test("cada especialidade, área e abordagem tem um supervisor fictício correspondente", () => {
  assert.deepEqual(SUPERVISOR_FILTER_GROUPS.map((group) => group.options.length), [13, 24, 13]);
  assert.equal(EXTERNAL_SUPERVISORS.length, 50);

  const primaryTerms = new Set(EXTERNAL_SUPERVISORS.map((supervisor) => supervisor.primaryTerm));
  for (const group of SUPERVISOR_FILTER_GROUPS) {
    for (const option of group.options) assert.ok(primaryTerms.has(option), "sem supervisor para " + option);
  }

  assert.equal(new Set(EXTERNAL_SUPERVISORS.map((supervisor) => supervisor.email)).size, 50);
  assert.ok(EXTERNAL_SUPERVISORS.every((supervisor) =>
    supervisor.name &&
    supervisor.city &&
    supervisor.yearsOfExperience >= 0 &&
    /^supervisor-\d{2}@supervisores\.example$/.test(supervisor.email) &&
    /^\+55 \(00\) 90000-\d{4}$/.test(supervisor.phone),
  ));
});

test("a busca por especialidade prioriza o especialista correspondente", () => {
  const supervisors = filterExternalSupervisors("Psicologia do Esporte");

  assert.ok(supervisors.length > 0);
  assert.equal(supervisors[0].primaryTerm, "Psicologia do Esporte");
});

test("a busca por burnout ordena primeiro a correspondência direta", () => {
  const supervisors = filterExternalSupervisors("Burnout");

  assert.ok(supervisors.length > 1);
  assert.equal(supervisors[0].primaryTerm, "Estresse e burnout");
  assert.ok(supervisors.slice(1).every((supervisor, index, relatedResults) =>
    index === 0 || relatedResults[index - 1].yearsOfExperience >= supervisor.yearsOfExperience,
  ));
});

test("termos sem correspondência retornam uma lista vazia", () => {
  assert.deepEqual(filterExternalSupervisors("Especialidade inexistente"), []);
});
