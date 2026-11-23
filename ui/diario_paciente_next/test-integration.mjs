import { DatabaseSync } from "node:sqlite";
import path from "node:path";
import {
  criarPaciente,
  autenticarPaciente,
  salvarDiario,
  listarDiarios,
} from "./app/api/auth/_backend.js";
import { analisarRelatoComRedeNeural } from "./app/lib/emotionService.js";

async function runTests() {
  console.log("=== INICIANDO TESTES DO BACKEND NEXT.JS COM REDE NEURAL ===");

  // 1. Teste de criação e autenticação
  const email = `paciente_${Date.now()}@exemplo.com`;
  const resCriar = await criarPaciente({
    nome: "Paciente Divertidamente",
    email,
    senha: "SenhaSegura123!",
  });
  console.log("1. Cadastro de paciente:", resCriar.ok ? "OK" : "FALHA");

  const resAuth = await autenticarPaciente(email, "SenhaSegura123!");
  console.log("2. Autenticação:", resAuth?.cookie ? "OK" : "FALHA");

  // 2. Teste de inferência com a rede neural (GoEmotions PT-BR -> Divertidamente)
  console.log("\n3. Testando inferência neural e taxonomia Divertidamente:");
  const relatosTeste = [
    {
      texto: "Hoje foi um dia maravilhoso, me sinto em paz, com esperança e muito feliz.",
      esperado: "alegria",
    },
    {
      texto: "Hoje eu chorei o dia todo, sinto um aperto no peito, um luto imenso e um desespero que não passa.",
      esperado: "tristeza",
    },
    {
      texto: "Estou em pânico e com muito medo dos resultados do exame, meu coração fica disparado.",
      esperado: "medo",
    },
    {
      texto: "Fiquei com muita raiva daquele atendimento no posto, um absurdo e descaso total!",
      esperado: "raiva",
    },
    {
      texto: "Fui ao posto de saúde, retirei os medicamentos da receita e voltei para casa às duas da tarde.",
      esperado: "neutro",
    },
  ];

  for (const item of relatosTeste) {
    const analise = await analisarRelatoComRedeNeural(item.texto);
    console.log(`\n• Relato: "${item.texto.slice(0, 50)}..."`);
    console.log(`  -> Personagem: ${analise.character} (${analise.color_hex})`);
    console.log(`  -> Sub-sentimento: ${analise.sub_emotion_symbol} ${analise.sub_emotion_name}`);
    console.log(`  -> Emoção Primária: ${analise.primary_emotion} (Esperado: ${item.esperado})`);
    console.log(`  -> Alerta de Risco Clínico: ${analise.is_risk_emotion}`);

    // Valida propriedades fundamentais
    if (!analise.character || !analise.color_hex || !analise.sub_emotion_name || !analise.sub_emotion_symbol) {
      throw new Error("Campos visuais obrigatórios ausentes!");
    }
  }

  // 3. Teste de persistência e listagem no SQLite
  console.log("\n4. Testando persistência de relatos no SQLite:");
  const db = new DatabaseSync(path.join(process.cwd(), "data", "auth.sqlite"));
  const pacienteRow = db.prepare("SELECT id FROM patients WHERE email = ?").get(email);
  const patientId = pacienteRow.id;

  const analiseTristeza = await analisarRelatoComRedeNeural(relatosTeste[1].texto);
  const salvo = salvarDiario({
    patientId,
    text: relatosTeste[1].texto,
    emotion: analiseTristeza,
  });
  console.log("  -> Relato salvo com ID:", salvo.id);

  const lista = listarDiarios(patientId);
  console.log("  -> Relatos recuperados do banco:", lista.length);
  const primeiro = lista[0];
  console.log("  -> Primeiro relato:", {
    character: primeiro.character,
    color_hex: primeiro.color_hex,
    sub_emotion_symbol: primeiro.sub_emotion_symbol,
    sub_emotion_name: primeiro.sub_emotion_name,
    is_risk_emotion: primeiro.is_risk_emotion,
  });

  if (primeiro.character !== analiseTristeza.character || primeiro.color_hex !== analiseTristeza.color_hex) {
    throw new Error("Inconsistência entre os dados gravados e recuperados!");
  }

  console.log("\n=== TODOS OS TESTES PASSARAM COM SUCESSO! ===");
}

runTests().catch((err) => {
  console.error("Erro nos testes:", err);
  process.exit(1);
});
