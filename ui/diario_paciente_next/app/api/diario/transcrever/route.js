import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { obterPacienteLogado } from "../../auth/_backend";

export const dynamic = "force-dynamic";

const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const MIME_EXTENSIONS = {
  "audio/webm": ".webm",
  "audio/ogg": ".ogg",
  "audio/mp4": ".mp4",
  "audio/mpeg": ".mp3",
  "audio/wav": ".wav",
  "audio/x-wav": ".wav",
  "audio/aac": ".aac",
};
const EXTENSION_MIMES = Object.fromEntries(
  Object.entries(MIME_EXTENSIONS).map(([mime, extension]) => [extension, mime]),
);

function runTranscriber(pythonExec, rootDir, audioPath) {
  return new Promise((resolve) => {
    let child;
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      resolve(result);
    };
    const timeout = setTimeout(() => {
      child?.kill();
      finish({ ok: false, timedOut: true });
    }, 180_000);

    try {
      child = spawn(pythonExec, ["-m", "models.audio_transcribe_cli", "--file", audioPath], {
        cwd: rootDir,
        env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" },
      });
      child.stdout.setEncoding("utf-8");
      child.stderr.setEncoding("utf-8");
      child.stdout.on("data", (chunk) => { stdout += chunk; });
      child.stderr.on("data", (chunk) => { stderr += chunk; });
      child.on("error", () => finish({ ok: false }));
      child.on("close", (code) => {
        if (code !== 0 || !stdout.trim()) {
          console.error("Falha na transcrição local:", stderr.trim());
          return finish({ ok: false });
        }
        try {
          const result = JSON.parse(stdout.trim());
          if (result.status === "empty") {
            return finish({ ok: false, empty: true, message: result.message });
          }
          if (result.status !== "ok" || !String(result.text || "").trim()) {
            console.error("Modelo de transcrição indisponível:", result.message || stderr.trim());
            return finish({ ok: false });
          }
          finish({ ok: true, result });
        } catch {
          finish({ ok: false });
        }
      });
    } catch {
      finish({ ok: false });
    }
  });
}

export async function POST(request) {
  const paciente = obterPacienteLogado(request);
  if (!paciente) {
    return NextResponse.json(
      { message: "Acesso não autorizado. Faça login para continuar." },
      { status: 401 },
    );
  }

  let tempFilePath = null;
  try {
    const contentType = request.headers.get("content-type") || "";
    let audioBuffer;
    let fileName = "gravacao.webm";
    let mimeType = "";

    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      const file = formData.get("audio") || formData.get("file");
      if (!file || typeof file === "string") {
        return NextResponse.json({ message: "Nenhum arquivo de áudio foi enviado." }, { status: 400 });
      }
      if (file.size > MAX_AUDIO_BYTES) {
        return NextResponse.json({ message: "O arquivo de áudio excede o limite máximo de 25 MB." }, { status: 413 });
      }

      fileName = path.basename(file.name || fileName);
      mimeType = String(file.type || "").split(";")[0].toLowerCase();
      if (!MIME_EXTENSIONS[mimeType]) {
        mimeType = EXTENSION_MIMES[path.extname(fileName).toLowerCase()] || "";
      }
      audioBuffer = Buffer.from(await file.arrayBuffer());
    } else {
      const body = await request.json();
      const encoded = typeof body.audioBase64 === "string" ? body.audioBase64 : "";
      if (encoded.length > Math.ceil(MAX_AUDIO_BYTES * 1.4)) {
        return NextResponse.json({ message: "O arquivo de áudio excede o limite máximo de 25 MB." }, { status: 413 });
      }
      fileName = path.basename(String(body.fileName || fileName));
      const dataUrl = encoded.match(/^data:(audio\/[\w.+-]+);base64,/i);
      mimeType = (dataUrl?.[1] || "").toLowerCase();
      if (!MIME_EXTENSIONS[mimeType]) {
        mimeType = EXTENSION_MIMES[path.extname(fileName).toLowerCase()] || "";
      }
      audioBuffer = Buffer.from(encoded.replace(/^data:audio\/[^;]+;base64,/i, ""), "base64");
    }

    if (!mimeType) {
      return NextResponse.json(
        { message: "Formato de áudio não compatível. Grave novamente pelo diário." },
        { status: 415 },
      );
    }
    if (!audioBuffer?.length) {
      return NextResponse.json({ message: "O áudio gravado está vazio." }, { status: 400 });
    }
    if (audioBuffer.length > MAX_AUDIO_BYTES) {
      return NextResponse.json({ message: "O arquivo de áudio excede o limite máximo de 25 MB." }, { status: 413 });
    }

    const rootDir = path.resolve(process.cwd(), "..", "..");
    const windowsPython = path.join(rootDir, ".venv", "Scripts", "python.exe");
    const unixPython = path.join(rootDir, ".venv", "bin", "python");
    const pythonExec = fs.existsSync(windowsPython)
      ? windowsPython
      : fs.existsSync(unixPython)
        ? unixPython
        : "python";
    tempFilePath = path.join(os.tmpdir(), `diary-audio-${randomUUID()}${MIME_EXTENSIONS[mimeType]}`);
    fs.writeFileSync(tempFilePath, audioBuffer);

    const transcription = await runTranscriber(pythonExec, rootDir, tempFilePath);
    if (!transcription.ok) {
      return NextResponse.json(
        {
          message: transcription.timedOut
            ? "A transcrição demorou demais. Tente novamente com uma gravação mais curta."
            : transcription.empty
              ? transcription.message
              : "Não foi possível transcrever o áudio. Confira sua conexão e tente novamente.",
        },
        { status: transcription.empty ? 422 : 503 },
      );
    }

    return NextResponse.json({
      ok: true,
      text: transcription.result.text.trim(),
      fileName,
      sizeBytes: audioBuffer.length,
      model: transcription.result.model,
    });
  } catch {
    return NextResponse.json(
      { message: "Falha ao processar áudio. Tente gravar novamente." },
      { status: 500 },
    );
  } finally {
    if (tempFilePath) {
      try {
        fs.unlinkSync(tempFilePath);
      } catch {}
    }
  }
}
