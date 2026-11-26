import { spawn } from "node:child_process";
import path from "node:path";
import { resolvePythonExecutable } from "./dashboardBridge.js";

const MESSAGES = {
  invalid_json: "Pedido inválido.",
  invalid_body: "Pedido inválido.",
  empty_query: "Informe uma pergunta.",
  query_too_long: "A pergunta passa de 2000 caracteres.",
  invalid_top_k: "top_k deve ser um inteiro de 1 a 5.",
  db_path_forbidden: "O caminho do banco não é aceito nesta consulta.",
};

export function literatureRequest(payload, env = process.env) {
  if (env.NODE_ENV === "production" || env.REQUIRE_PSICOLOGA_AUTH === "true") {
    return {
      status: 403,
      body: { message: "A consulta científica fica restrita ao protótipo local." },
    };
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { status: 400, body: { message: "Pedido inválido." } };
  }
  if ("db_path" in payload) {
    return { status: 400, body: { message: literatureErrorMessage("db_path_forbidden") } };
  }
  return null;
}

export function literatureErrorMessage(code) {
  return MESSAGES[code] || "Pedido inválido.";
}

const STDOUT_LIMIT = 1_000_000;

export function projectPython() {
  const resolved = resolvePythonExecutable();
  const marker = `${path.sep}.venv${path.sep}`;
  if (!resolved.pythonExec.includes(marker)) return null;
  return resolved;
}

export function literatureHttpResult(result) {
  if (result.code === 2) {
    return { status: 400, body: { message: literatureErrorMessage(result.body.error) } };
  }
  if (result.code !== 0) {
    return { status: 500, body: { message: "Falha ao consultar a literatura." } };
  }
  return { status: 200, body: result.body };
}

export function runLiteratureProcess({ python, args, payload, timeoutMs, cwd, env }) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, args, {
      cwd,
      env: { ...env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill("SIGKILL");
      reject(new Error("Tempo esgotado na consulta científica."));
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf-8");
      if (stdout.length > STDOUT_LIMIT) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        child.kill("SIGKILL");
        reject(new Error("Resposta da consulta científica excedeu o limite."));
      }
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf-8");
    });
    child.on("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      let body = {};
      try {
        body = JSON.parse(stdout.trim() || "{}");
      } catch {
        reject(new Error("Resposta inválida da consulta científica."));
        return;
      }
      resolve({ code, body, stderr });
    });

    child.stdin.write(JSON.stringify(payload ?? {}), "utf-8");
    child.stdin.end();
  });
}

export function runLiteratureSearch(payload, timeoutMs = 20000) {
  const resolved = projectPython();
  if (!resolved) {
    return Promise.reject(new Error("Ambiente Python do projeto ausente."));
  }
  return runLiteratureProcess({
    python: resolved.pythonExec,
    args: ["-m", "agents.copilot.literature_http"],
    payload,
    timeoutMs,
    cwd: resolved.rootDir,
    env: process.env,
  });
}
