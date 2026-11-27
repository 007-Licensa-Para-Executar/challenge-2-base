import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export function resolvePythonExecutable() {
  const rootDir = path.resolve(process.cwd(), "..", "..");
  const venvWin = path.join(rootDir, ".venv", "Scripts", "python.exe");
  const venvUnix = path.join(rootDir, ".venv", "bin", "python");

  if (fs.existsSync(venvWin)) return { pythonExec: venvWin, rootDir };
  if (fs.existsSync(venvUnix)) return { pythonExec: venvUnix, rootDir };
  return { pythonExec: "python", rootDir };
}

export function runDashboardCli(command, payload, timeoutMs = 45000) {
  return runPython("agents.extractor.dashboard_cli", command, payload, timeoutMs);
}

export function runIntegration(command, payload) {
  return runPython("agents.copilot.integration_cli", command, payload, 180000);
}

function runPython(module, command, payload, timeoutMs) {
  const { pythonExec, rootDir } = resolvePythonExecutable();

  return new Promise((resolve, reject) => {
    const child = spawn(pythonExec, ["-m", module, command], {
      cwd: rootDir,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    let stdout = "";
    let stderr = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try {
        child.kill();
      } catch {}
      reject(new Error(`Timeout ao executar dashboard_cli (${command}) após ${timeoutMs}ms.`));
    }, timeoutMs);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });

    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });

    child.on("error", (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(err);
    });

    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (code !== 0) {
        reject(new Error(stderr.trim() || `dashboard_cli (${command}) retornou código ${code}.`));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim() || "{}"));
      } catch (err) {
        reject(new Error(`JSON inválido retornado por dashboard_cli (${command}): ${err.message}`));
      }
    });

    child.stdin.write(JSON.stringify(payload ?? {}), "utf-8");
    child.stdin.end();
  });
}
