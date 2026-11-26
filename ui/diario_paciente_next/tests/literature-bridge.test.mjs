import assert from "node:assert/strict";
import test from "node:test";
import {
  literatureErrorMessage,
  literatureHttpResult,
  literatureRequest,
  runLiteratureProcess,
} from "../app/lib/literatureBridge.js";

test("the prototype stays closed in production and rejects a database path", () => {
  const blocked = literatureRequest(
    { query: "ética", db_path: "/tmp/outro.sqlite3" },
    { NODE_ENV: "production" },
  );
  assert.equal(blocked.status, 403);
  assert.equal(JSON.stringify(blocked.body).includes("/tmp"), false);

  const flagged = literatureRequest({ query: "ética" }, { REQUIRE_PSICOLOGA_AUTH: "true" });
  assert.equal(flagged.status, 403);

  const rejected = literatureRequest(
    { query: "ética", db_path: "/tmp/outro.sqlite3" },
    { NODE_ENV: "development" },
  );
  assert.equal(rejected.status, 400);
  assert.equal(rejected.body.message, literatureErrorMessage("db_path_forbidden"));
});

test("a python failure does not return the process error text", () => {
  const http = literatureHttpResult({
    code: 1,
    body: {},
    stderr: "Traceback /home/secret/literature.py",
  });
  assert.equal(http.status, 500);
  assert.equal(http.body.message, "Falha ao consultar a literatura.");
  assert.equal(JSON.stringify(http.body).includes("/home/secret"), false);
});

test("validation stays a client error", () => {
  const http = literatureHttpResult({ code: 2, body: { error: "empty_query" }, stderr: "" });
  assert.equal(http.status, 400);
  assert.equal(http.body.message, literatureErrorMessage("empty_query"));
});

test("a failing process does not expose its error text", async () => {
  const result = await runLiteratureProcess({
    python: "python3",
    args: ["-c", "import sys; sys.stderr.write('/tmp/segredo'); sys.exit(1)"],
    payload: {},
    timeoutMs: 5000,
    cwd: process.cwd(),
    env: process.env,
  });
  const http = literatureHttpResult(result);
  assert.equal(http.status, 500);
  assert.equal(JSON.stringify(http.body).includes("segredo"), false);
});

test("a stuck process is stopped", async () => {
  await assert.rejects(
    runLiteratureProcess({
      python: "python3",
      args: ["-c", "import time; time.sleep(30)"],
      payload: {},
      timeoutMs: 200,
      cwd: process.cwd(),
      env: process.env,
    }),
    /Tempo esgotado/,
  );
});
