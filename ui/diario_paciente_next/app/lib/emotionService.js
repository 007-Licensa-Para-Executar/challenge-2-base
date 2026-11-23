import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { getEmotionProfile } from "./emotionTaxonomy.js";

/**
 * Executa a inferência da rede neural em Python (models/emotion_cli.py)
 * passando o texto via stdin para análise determinística com suporte UTF-8.
 */
export async function analisarRelatoComRedeNeural(texto) {
  const clean = (texto || "").trim();
  if (!clean) {
    const neutro = getEmotionProfile("neutro");
    return {
      primary_emotion: "neutro",
      character: neutro.personagem,
      color_hex: neutro.corHex,
      color_secondary_hex: neutro.corSecundariaHex,
      sub_emotion_name: neutro.subSentimentos[0].nome,
      sub_emotion_symbol: neutro.subSentimentos[0].simbolo,
      confidence: 1.0,
      is_risk_emotion: false,
    };
  }

  // Localiza o ambiente virtual Python do repositório ou comando do sistema
  const rootDir = path.resolve(process.cwd(), "..", "..");
  const venvPythonWin = path.join(rootDir, ".venv", "Scripts", "python.exe");
  const venvPythonUnix = path.join(rootDir, ".venv", "bin", "python");

  let pythonExec = "python";
  if (fs.existsSync(venvPythonWin)) {
    pythonExec = venvPythonWin;
  } else if (fs.existsSync(venvPythonUnix)) {
    pythonExec = venvPythonUnix;
  }

  return new Promise((resolve) => {
    try {
      const child = spawn(
        pythonExec,
        ["-m", "models.emotion_cli"],
        {
          cwd: rootDir,
          env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        }
      );

      let stdoutData = "";
      let stderrData = "";

      child.stdout.on("data", (chunk) => {
        stdoutData += chunk.toString("utf-8");
      });

      child.stderr.on("data", (chunk) => {
        stderrData += chunk.toString("utf-8");
      });

      child.on("close", (code) => {
        if (code === 0 && stdoutData.trim()) {
          try {
            const parsed = JSON.parse(stdoutData.trim());
            return resolve({
              primary_emotion: parsed.primary_emotion,
              character: parsed.character,
              color_hex: parsed.color_hex,
              color_secondary_hex: parsed.color_secondary_hex,
              sub_emotion_name:
                parsed.active_sub_emotion?.nome || parsed.sub_emotion_name || parsed.character,
              sub_emotion_symbol:
                parsed.active_sub_emotion?.simbolo || parsed.sub_emotion_symbol || "⚖️",
              confidence: parsed.confidence,
              relative_score: parsed.relative_score,
              is_risk_emotion: Boolean(parsed.is_risk_emotion),
              detected_emotions: parsed.detected_emotions || [],
              probabilities: parsed.probabilities || {},
              active_sub_emotion: parsed.active_sub_emotion,
            });
          } catch {
            // Em caso de falha de parse, cai no fallback
          }
        }

        // Fallback heurístico resiliente baseado na taxonomia se o Python demorar ou não responder
        resolve(fallbackAnaliseHeuristica(clean));
      });

      child.on("error", () => {
        resolve(fallbackAnaliseHeuristica(clean));
      });

      child.stdin.write(clean, "utf-8");
      child.stdin.end();
    } catch {
      resolve(fallbackAnaliseHeuristica(clean));
    }
  });
}

function fallbackAnaliseHeuristica(texto) {
  const lower = (texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  let selected = "neutro";
  let subIndex = 0;

  if (/(explod|quebrar|matar|esganar|arrebentar|destruir|raiva|odio|furia|irritad|revolta|indignad|absurdo)/.test(lower)) {
    selected = "raiva";
    subIndex = /(explod|matar|destruir|arrebentar)/.test(lower) ? 2 : 0; // Fúria ou Irritação
  } else if (/(prova|exame|teste|concurso|prazo|ansiedad|panico|apavorad|assustad|terror|aflit|medo)/.test(lower)) {
    selected = "medo";
    subIndex = 0; // Ansiedade
  } else if (/(pessim|horrivel|ruim|triste|choro|chorei|luto|desanimo|lagrima|vazio|deprim)/.test(lower)) {
    selected = "tristeza";
    subIndex = /(pessim|horrivel|desanimo)/.test(lower) ? 0 : 1; // Desânimo ou Luto
  } else if (/(nojo|repulsa|nausea|estragad|podre|aversao|enjoo)/.test(lower)) {
    selected = "nojinho";
    subIndex = 0;
  } else if (/(feliz|alegr|grat|otimo|maravilh|esperanc|alivio)/.test(lower)) {
    selected = "alegria";
    subIndex = /(otimo|maravilh|feliz)/.test(lower) ? 2 : 0; // Entusiasmo ou Gratidão
  }

  const profile = getEmotionProfile(selected);
  const sub = profile.subSentimentos[subIndex] || profile.subSentimentos[0];

  return {
    primary_emotion: profile.id,
    character: profile.personagem,
    color_hex: profile.corHex,
    color_secondary_hex: profile.corSecundariaHex,
    sub_emotion_name: sub.nome,
    sub_emotion_symbol: sub.simbolo,
    confidence: 0.85,
    is_risk_emotion: profile.isRiskEmotion,
  };
}
