// Paciente sintético de demonstração para explorar a Roda ImpactBench completa (24 subtemas max).
// Nunca é misturado aos cadastros reais do banco SQLite.

export const DEMO_PATIENT_ID = "demo-clara-mendes";

function makeDemoAgent1({
  id,
  patientId,
  createdAtIso,
  text,
  macroTema,
  confidence,
  sentimento,
  polarity,
  risk = "nao_identificado",
  modalidade = "texto",
  subtopics,
}) {
  const evidenciasFor = (quote) => {
    const start = Math.max(0, text.indexOf(quote));
    const end = start + quote.length;
    return [
      {
        quote_text: text.slice(start, end) || text.slice(0, Math.min(text.length, 80)),
        start_char: start,
        end_char: Math.max(start + 1, end),
        audio_start_sec: null,
        audio_end_sec: null,
      },
    ];
  };

  return {
    entry_id: id,
    patient_id: patientId,
    created_at: createdAtIso,
    macro_tema_validado: macroTema,
    confianca_macro_tema: confidence,
    subtemas: subtopics.map((s) => ({
      nome: s.nome,
      descricao: s.descricao,
      evidencias: evidenciasFor(s.quote),
    })),
    sentimento_predominante: sentimento,
    score_polaridade: polarity,
    indicio_textual_risco: risk,
    modalidade,
    validation: {
      nlp_polaridade: polarity > 0.15 ? "POSITIVO" : polarity < -0.15 ? "NEGATIVO" : "NEUTRO",
      nlp_score: polarity,
      discrepancia_detectada: false,
      distancia_polaridade: 0.05,
    },
  };
}

function daysAgoMs(days, hour = 20) {
  const d = new Date(Date.now() - days * 86400000);
  d.setHours(hour, 15, 0, 0);
  return d.getTime();
}

const RAW_DEMO_SPECS = [
  {
    id: "10000001-0000-4000-8000-000000000001",
    daysAgo: 1,
    text: "Fiquei até tarde revisando planilhas por cobrança de metas da chefia. Senti um cansaço extremo e falta de energia ao fechar o notebook.",
    emotion: "ansiedade",
    character: "Ansiedade",
    colorHex: "#E67E22",
    subEmotion: "Sobrecarga",
    symbol: "⏳",
    risk: false,
    macroTema: "trabalho",
    confidence: 0.91,
    sentimento: "preocupacao",
    polarity: -0.62,
    subtopics: [
      { nome: "Sobrecarga e metas", descricao: "Exigências de produtividade fora do horário regular.", quote: "revisando planilhas por cobrança de metas da chefia" },
      { nome: "Esgotamento ao fim do dia", descricao: "Fadiga acumulada ao encerrar o expediente.", quote: "Senti um cansaço extremo e falta de energia" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000002",
    daysAgo: 2,
    text: "Hoje recebi elogio da coordenadora pelo novo fluxo do projeto e consegui organizar minha semana sem pânico.",
    emotion: "alegria",
    character: "Alegria",
    colorHex: "#F4D03F",
    subEmotion: "Orgulho",
    symbol: "☀️",
    risk: false,
    macroTema: "trabalho",
    confidence: 0.87,
    sentimento: "alegria",
    polarity: 0.74,
    subtopics: [
      { nome: "Reconhecimento profissional", descricao: "Feedback positivo e sensação de competência.", quote: "recebi elogio da coordenadora pelo novo fluxo do projeto" },
      { nome: "Planejamento de rotina", descricao: "Organização prática reduzindo ansiedade antecipatória.", quote: "consegui organizar minha semana sem pânico" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000003",
    daysAgo: 2,
    text: "Acordei às 3h da manhã com taquicardia e não consegui voltar a dormir pensando nos prazos.",
    emotion: "medo",
    character: "Medo",
    colorHex: "#8E44AD",
    subEmotion: "Insônia",
    symbol: "🌙",
    risk: true,
    macroTema: "saude_sono",
    confidence: 0.93,
    sentimento: "medo",
    polarity: -0.78,
    subtopics: [
      { nome: "Despertar noturno", descricao: "Interrupção do sono na madrugada associada à ruminação.", quote: "Acordei às 3h da manhã com taquicardia" },
      { nome: "Sintomas autonômicos", descricao: "Manifestações físicas de ansiedade durante o descanso.", quote: "não consegui voltar a dormir pensando nos prazos" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000004",
    daysAgo: 3,
    text: "Caminhei 30 minutos no parque de manhã e tomei sol, meu corpo ficou mais leve o dia inteiro.",
    emotion: "calma",
    character: "Alegria",
    colorHex: "#58B368",
    subEmotion: "Vitalidade",
    symbol: "🌿",
    risk: false,
    macroTema: "saude_sono",
    confidence: 0.84,
    sentimento: "calma",
    polarity: 0.78,
    subtopics: [
      { nome: "Higiene e movimento", descricao: "Prática física matinal com alívio somático.", quote: "Caminhei 30 minutos no parque de manhã e tomei sol" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000005",
    daysAgo: 4,
    text: "Almocei com minha irmã e conversamos sem pressa; me senti acolhida e compreendida por ela.",
    emotion: "alegria",
    character: "Alegria",
    colorHex: "#58B368",
    subEmotion: "Acolhimento",
    symbol: "🤍",
    risk: false,
    macroTema: "familia",
    confidence: 0.89,
    sentimento: "alegria",
    polarity: 0.82,
    subtopics: [
      { nome: "Rede de apoio familiar", descricao: "Troca afetiva e escuta segura com familiar próximo.", quote: "conversamos sem pressa; me senti acolhida e compreendida" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000006",
    daysAgo: 5,
    text: "Tive uma discussão tensa em casa sobre divisão de tarefas e acabei me fechando no quarto.",
    emotion: "raiva",
    character: "Raiva",
    colorHex: "#C0392B",
    subEmotion: "Atrito",
    symbol: "🔥",
    risk: false,
    macroTema: "familia",
    confidence: 0.85,
    sentimento: "frustracao",
    polarity: -0.54,
    subtopics: [
      { nome: "Conflito doméstico", descricao: "Tensão por acordos e responsabilidades na casa.", quote: "discussão tensa em casa sobre divisão de tarefas" },
      { nome: "Retraimento após atrito", descricao: "Afastamento para evitar escalada emocional.", quote: "acabei me fechando no quarto" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000007",
    daysAgo: 6,
    text: "Senti muita saudade do meu avô ao ver fotos antigas; chorei bastante, mas com carinho nas lembranças.",
    emotion: "tristeza",
    character: "Tristeza",
    colorHex: "#2E86C1",
    subEmotion: "Saudade",
    symbol: "💧",
    risk: false,
    macroTema: "luto",
    confidence: 0.94,
    sentimento: "tristeza",
    polarity: -0.35,
    subtopics: [
      { nome: "Saudade e memória afetiva", descricao: "Choro ligado à lembrança de pessoa querida.", quote: "Senti muita saudade do meu avô ao ver fotos antigas" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000008",
    daysAgo: 6,
    text: "Sinto medo de me expor no relacionamento e repetir padrões antigos de silêncio quando fico magoada.",
    emotion: "medo",
    character: "Medo",
    colorHex: "#8E44AD",
    subEmotion: "Vulnerabilidade",
    symbol: "🫧",
    risk: false,
    macroTema: "relacionamentos",
    confidence: 0.86,
    sentimento: "medo",
    polarity: -0.48,
    subtopics: [
      { nome: "Comunicação afetiva", descricao: "Dificuldade em verbalizar mágoas por receio de conflito.", quote: "repetir padrões antigos de silêncio quando fico magoada" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000009",
    daysAgo: 8,
    text: "Conseguimos conversar com calma no jantar sobre limites e me senti mais segura na relação.",
    emotion: "calma",
    character: "Alegria",
    colorHex: "#3D9970",
    subEmotion: "Segurança",
    symbol: "🤝",
    risk: false,
    macroTema: "relacionamentos",
    confidence: 0.88,
    sentimento: "calma",
    polarity: 0.72,
    subtopics: [
      { nome: "Acordos e limites claros", descricao: "Diálogo assertivo fortalecendo confiança mútua.", quote: "conversar com calma no jantar sobre limites" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000010",
    daysAgo: 9,
    text: "Fiquei travada olhando o artigo da pós-graduação e senti culpa por não render o quanto eu queria.",
    emotion: "ansiedade",
    character: "Ansiedade",
    colorHex: "#D35400",
    subEmotion: "Autocobrança",
    symbol: "📚",
    risk: false,
    macroTema: "estudos",
    confidence: 0.89,
    sentimento: "frustracao",
    polarity: -0.52,
    subtopics: [
      { nome: "Procrastinação e bloqueio", descricao: "Dificuldade de iniciar escrita acadêmica sob pressão.", quote: "Fiquei travada olhando o artigo da pós-graduação" },
      { nome: "Culpa por desempenho", descricao: "Autocrítica rígida frente a metas de estudo.", quote: "senti culpa por não render o quanto eu queria" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000011",
    daysAgo: 10,
    text: "Quitei a fatura atrasada do cartão e montei uma planilha simples; tirou um peso dos ombros.",
    emotion: "alegria",
    character: "Alegria",
    colorHex: "#58B368",
    subEmotion: "Alívio",
    symbol: "📊",
    risk: false,
    macroTema: "financas",
    confidence: 0.90,
    sentimento: "alegria",
    polarity: 0.65,
    subtopics: [
      { nome: "Reorganização financeira", descricao: "Sensação de controle após regularizar pendência.", quote: "Quitei a fatura atrasada do cartão e montei uma planilha" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000012",
    daysAgo: 12,
    text: "Me comparei muito com colegas na rede social e me achei insuficiente no meu próprio ritmo.",
    emotion: "tristeza",
    character: "Tristeza",
    colorHex: "#5D6D7E",
    subEmotion: "Comparação",
    symbol: "🪞",
    risk: false,
    macroTema: "autoestima",
    confidence: 0.92,
    sentimento: "tristeza",
    polarity: -0.66,
    subtopics: [
      { nome: "Comparação social", descricao: "Autodesvalorização disparada por comparação externa.", quote: "Me comparei muito com colegas na rede social" },
      { nome: "Senso de insuficiência", descricao: "Percepção autocrítica do próprio ritmo pessoal.", quote: "me achei insuficiente no meu próprio ritmo" },
    ],
  },
  {
    id: "10000001-0000-4000-8000-000000000013",
    daysAgo: 13,
    text: "Consegui dizer não a um pedido extra sem pedir desculpas exageradas e respeitei meu descanso.",
    emotion: "alegria",
    character: "Alegria",
    colorHex: "#2E8B57",
    subEmotion: "Autocuidado",
    symbol: "✨",
    risk: false,
    macroTema: "autoestima",
    confidence: 0.88,
    sentimento: "alegria",
    polarity: 0.79,
    subtopics: [
      { nome: "Assertividade e limites", descricao: "Posicionamento firme sem culpa excessiva.", quote: "Consegui dizer não a um pedido extra" },
    ],
  },
];

export function getDemoPatientSummary() {
  let positive = 0;
  let negative = 0;
  let neutral = 0;
  let riskCount = 0;
  for (const item of RAW_DEMO_SPECS) {
    if (item.risk) riskCount += 1;
    if (item.polarity >= 0.15) positive += 1;
    else if (item.polarity <= -0.15) negative += 1;
    else neutral += 1;
  }
  return {
    id: DEMO_PATIENT_ID,
    name: "Clara Mendes (Demo 24 Subtemas)",
    email: "clara.demo@sintetico.local",
    createdAt: new Date(daysAgoMs(21)).toISOString(),
    entryCount: RAW_DEMO_SPECS.length,
    riskCount,
    valenceBreakdown: { positive, neutral, negative },
    lastEntryAt: new Date(daysAgoMs(1)).toISOString(),
    isDemo: true,
  };
}

export function getDemoPatientEntries() {
  return RAW_DEMO_SPECS.map((spec) => {
    const createdAt = daysAgoMs(spec.daysAgo);
    const createdAtIso = new Date(createdAt).toISOString();
    const agent1 = makeDemoAgent1({
      id: spec.id,
      patientId: DEMO_PATIENT_ID,
      createdAtIso,
      text: spec.text,
      macroTema: spec.macroTema,
      confidence: spec.confidence,
      sentimento: spec.sentimento,
      polarity: spec.polarity,
      risk: spec.risk ? "presente" : "nao_identificado",
      subtopics: spec.subtopics,
    });
    return {
      id: spec.id,
      patient_id: DEMO_PATIENT_ID,
      text: spec.text,
      primary_emotion: spec.emotion,
      character: spec.character,
      color_hex: spec.colorHex,
      color_secondary_hex: "#ECEFF1",
      sub_emotion_name: spec.subEmotion,
      sub_emotion_symbol: spec.symbol,
      confidence: spec.confidence,
      is_risk_emotion: spec.risk ? 1 : 0,
      input_type: "text",
      audio_name: null,
      audio_duration: null,
      audio_data: null,
      theme_macro: spec.macroTema,
      theme_confidence: spec.confidence,
      theme_scores_json: JSON.stringify({ [spec.macroTema]: Math.round(spec.confidence * 100) }),
      polarity_score: spec.polarity,
      agent1_json: JSON.stringify(agent1),
      analysis_source: "demo_sintetico_mlp+agent1",
      analyzed_at: createdAt,
      created_at: createdAt,
    };
  });
}
