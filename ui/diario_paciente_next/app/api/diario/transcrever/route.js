import { NextResponse } from "next/server";
import { obterPacienteLogado } from "../../auth/_backend";
import { analisarRelatoComRedeNeural } from "../../../lib/emotionService";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawn } from "node:child_process";

export const dynamic = "force-dynamic";

export async function POST(request) {
  const paciente = obterPacienteLogado(request);
  if (!paciente) {
    return NextResponse.json(
      { message: "Acesso não autorizado. Faça login para continuar." },
      { status: 401 }
    );
  }

  try {
    const contentType = request.headers.get("content-type") || "";
    let audioBuffer = null;
    let fileName = "gravacao.webm";

    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      const file = formData.get("audio") || formData.get("file");
      if (!file || typeof file === "string") {
        return NextResponse.json(
          { message: "Nenhum arquivo de áudio foi enviado." },
          { status: 400 }
        );
      }
      fileName = file.name || "audio.webm";
      const arrayBuffer = await file.arrayBuffer();
      audioBuffer = Buffer.from(arrayBuffer);
    } else {
      const body = await request.json();
      if (body.audioBase64) {
        fileName = body.fileName || "audio.webm";
        // Remove prefixo data:audio/...;base64, se houver
        const base64Data = body.audioBase64.replace(/^data:audio\/[^;]+;base64,/, "");
        audioBuffer = Buffer.from(base64Data, "base64");
      }
    }

    if (!audioBuffer || audioBuffer.length === 0) {
      return NextResponse.json(
        { message: "O arquivo de áudio enviado está vazio." },
        { status: 400 }
      );
    }

    if (audioBuffer.length > 25 * 1024 * 1024) {
      return NextResponse.json(
        { message: "O arquivo de áudio excede o limite máximo de 25 MB." },
        { status: 400 }
      );
    }

    // Salva temporariamente para processamento local
    const tempDir = os.tmpdir();
    const ext = path.extname(fileName) || ".webm";
    const tempFilePath = path.join(tempDir, `audio_${Date.now()}_${Math.random().toString(36).substring(7)}${ext}`);
    fs.writeFileSync(tempFilePath, audioBuffer);

    let transcribedText = "";
    try {
      const rootDir = path.resolve(process.cwd(), "..", "..");
      const venvPythonWin = path.join(rootDir, ".venv", "Scripts", "python.exe");
      const venvPythonUnix = path.join(rootDir, ".venv", "bin", "python");
      const pythonExec = fs.existsSync(venvPythonWin)
        ? venvPythonWin
        : fs.existsSync(venvPythonUnix)
        ? venvPythonUnix
        : "python";

      transcribedText = await new Promise((resolve) => {
        const child = spawn(
          pythonExec,
          ["-m", "models.audio_transcribe_cli", "--file", tempFilePath],
          { cwd: rootDir, env: { ...process.env, PYTHONIOENCODING: "utf-8" } }
        );

        let out = "";
        child.stdout.on("data", (d) => {
          out += d.toString("utf-8");
        });
        child.on("close", (code) => {
          if (code === 0 && out.trim()) {
            try {
              const res = JSON.parse(out.trim());
              return resolve(res.text || "");
            } catch {}
          }
          resolve("");
        });
        child.on("error", () => resolve(""));
      });
    } finally {
      try {
        fs.unlinkSync(tempFilePath);
      } catch {}
    }

    // Se transcrito texto, analisa o sentimento
    let emotion = null;
    if (transcribedText.trim()) {
      emotion = await analisarRelatoComRedeNeural(transcribedText);
    }

    return NextResponse.json({
      ok: true,
      text: transcribedText,
      emotion,
      fileName,
      sizeBytes: audioBuffer.length,
    });
  } catch (error) {
    return NextResponse.json(
      { message: "Falha ao processar arquivo de áudio." },
      { status: 500 }
    );
  }
}
