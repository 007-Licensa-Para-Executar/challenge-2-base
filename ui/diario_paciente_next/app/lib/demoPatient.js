// Paciente sintético de demonstração para explorar a Roda ImpactBench completa (24 subtemas max).
// Nunca é misturado aos cadastros reais do banco SQLite.

export const DEMO_PATIENT_ID = "demo-clara-mendes";
export const DEMO_BRUNO_PATIENT_ID = "demo-bruno-henrique-almeida-lima";

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

// Caso de demonstração independente do paciente real homônimo; 24 subtemas cobrem os nove macros.
const RAW_BRUNO_CORE_SPECS = [
  { id: "20000002-0000-4000-8000-000000000001", daysAgo: 1, text: "Adiei uma conversa importante com alguém próximo porque fiquei receoso de não encontrar as palavras certas.", emotion: "ansiedade", character: "Ansiedade", colorHex: "#E67E22", subEmotion: "Inquietação", symbol: "💬", risk: false, macroTema: "relacionamentos", confidence: 0.88, sentimento: "preocupacao", polarity: -0.38, subtopics: [{ nome: "Conversas adiadas", descricao: "Receio de iniciar diálogos importantes e de como serão recebidos.", quote: "Adiei uma conversa importante com alguém próximo" }] },
  { id: "20000002-0000-4000-8000-000000000002", daysAgo: 2, text: "Consegui dizer a um amigo que precisava de uma noite tranquila; respeitar meu limite me deixou mais leve.", emotion: "calma", character: "Alegria", colorHex: "#58B368", subEmotion: "Alívio", symbol: "🧭", risk: false, macroTema: "relacionamentos", confidence: 0.86, sentimento: "calma", polarity: 0.58, subtopics: [{ nome: "Limites em amizades", descricao: "Expressão clara de necessidades pessoais em uma amizade.", quote: "Consegui dizer a um amigo que precisava de uma noite tranquila" }] },
  { id: "20000002-0000-4000-8000-000000000003", daysAgo: 3, text: "Uma pessoa de confiança me ouviu sem pressa e percebi que a relação ficou mais segura depois da conversa.", emotion: "alegria", character: "Alegria", colorHex: "#3D9970", subEmotion: "Segurança", symbol: "🤝", risk: false, macroTema: "relacionamentos", confidence: 0.9, sentimento: "alegria", polarity: 0.68, subtopics: [{ nome: "Confiança construída", descricao: "Segurança relacional fortalecida por escuta e diálogo.", quote: "Uma pessoa de confiança me ouviu sem pressa" }] },
  { id: "20000002-0000-4000-8000-000000000004", daysAgo: 4, text: "Fui dormir mais tarde do que planejava e acordei com a sensação de que a noite não foi suficiente.", emotion: "cansaco", character: "Cansaço", colorHex: "#6687A3", subEmotion: "Sono curto", symbol: "🌙", risk: false, macroTema: "saude_sono", confidence: 0.91, sentimento: "tristeza", polarity: -0.44, subtopics: [{ nome: "Rotina de sono", descricao: "Horários irregulares associados à percepção de descanso insuficiente.", quote: "Fui dormir mais tarde do que planejava" }] },
  { id: "20000002-0000-4000-8000-000000000005", daysAgo: 5, text: "Desliguei as telas um pouco antes de deitar e consegui desacelerar os pensamentos com mais facilidade.", emotion: "calma", character: "Calma", colorHex: "#58B368", subEmotion: "Desaceleração", symbol: "☁️", risk: false, macroTema: "saude_sono", confidence: 0.85, sentimento: "calma", polarity: 0.52, subtopics: [{ nome: "Desacelerar à noite", descricao: "Pequenos rituais noturnos que ajudam a reduzir estímulos antes do sono.", quote: "Desliguei as telas um pouco antes de deitar" }] },
  { id: "20000002-0000-4000-8000-000000000006", daysAgo: 6, text: "Fiz uma caminhada leve no começo do dia e notei mais disposição para as tarefas da manhã.", emotion: "alegria", character: "Alegria", colorHex: "#58B368", subEmotion: "Vitalidade", symbol: "🌿", risk: false, macroTema: "saude_sono", confidence: 0.83, sentimento: "alegria", polarity: 0.61, subtopics: [{ nome: "Disposição após movimento", descricao: "Percepção de energia associada a movimento físico leve.", quote: "Fiz uma caminhada leve no começo do dia" }] },
  { id: "20000002-0000-4000-8000-000000000007", daysAgo: 7, text: "Revisei as despesas do mês e separei o valor das contas antes de decidir o que mais cabia no orçamento.", emotion: "calma", character: "Equilíbrio", colorHex: "#5A8A78", subEmotion: "Organização", symbol: "🪙", risk: false, macroTema: "financas", confidence: 0.89, sentimento: "calma", polarity: 0.34, subtopics: [{ nome: "Planejamento do orçamento", descricao: "Organização de despesas e prioridades financeiras do mês.", quote: "Revisei as despesas do mês e separei o valor das contas" }] },
  { id: "20000002-0000-4000-8000-000000000008", daysAgo: 8, text: "Esperei um dia antes de comprar algo que queria e percebi que a decisão ficou mais consciente.", emotion: "calma", character: "Equilíbrio", colorHex: "#5A8A78", subEmotion: "Escolha consciente", symbol: "🛒", risk: false, macroTema: "financas", confidence: 0.82, sentimento: "calma", polarity: 0.41, subtopics: [{ nome: "Compra consciente", descricao: "Pausa para avaliar uma compra antes de comprometer o orçamento.", quote: "Esperei um dia antes de comprar algo que queria" }] },
  { id: "20000002-0000-4000-8000-000000000009", daysAgo: 9, text: "Uma despesa inesperada apareceu e fiquei preocupado por alguns minutos, até reorganizar as prioridades.", emotion: "ansiedade", character: "Ansiedade", colorHex: "#E67E22", subEmotion: "Preocupação", symbol: "🧾", risk: false, macroTema: "financas", confidence: 0.87, sentimento: "preocupacao", polarity: -0.49, subtopics: [{ nome: "Preocupação com imprevistos", descricao: "Inquietação diante de despesas inesperadas e necessidade de replanejamento.", quote: "Uma despesa inesperada apareceu e fiquei preocupado" }] },
  { id: "20000002-0000-4000-8000-000000000010", daysAgo: 10, text: "A mudança de horário bagunçou um pouco minha rotina, mas consegui reorganizar os compromissos sem pressa.", emotion: "neutro", character: "Equilíbrio", colorHex: "#8B9A93", subEmotion: "Adaptação", symbol: "🧩", risk: false, macroTema: "outros_indeterminado", confidence: 0.8, sentimento: "nao_identificado", polarity: 0.03, subtopics: [{ nome: "Mudança de rotina", descricao: "Ajuste cotidiano diante de alteração de horários ou planos.", quote: "A mudança de horário bagunçou um pouco minha rotina" }] },
  { id: "20000002-0000-4000-8000-000000000011", daysAgo: 11, text: "Passei um tempo longe do celular durante o almoço e voltei ao trabalho me sentindo mais presente.", emotion: "calma", character: "Calma", colorHex: "#58B368", subEmotion: "Presença", symbol: "🫧", risk: false, macroTema: "outros_indeterminado", confidence: 0.84, sentimento: "calma", polarity: 0.48, subtopics: [{ nome: "Pausa digital", descricao: "Intervalo de notificações e telas para recuperar atenção no momento presente.", quote: "Passei um tempo longe do celular durante o almoço" }] },
  { id: "20000002-0000-4000-8000-000000000012", daysAgo: 12, text: "Tentei encaixar trabalho, descanso e compromissos pessoais sem cobrar que tudo ficasse perfeito.", emotion: "neutro", character: "Equilíbrio", colorHex: "#8B9A93", subEmotion: "Ajuste", symbol: "⚖️", risk: false, macroTema: "outros_indeterminado", confidence: 0.81, sentimento: "nao_identificado", polarity: 0.08, subtopics: [{ nome: "Equilíbrio entre atividades", descricao: "Percepção de espaço e limites entre diferentes áreas da rotina.", quote: "Tentei encaixar trabalho, descanso e compromissos pessoais" }] },
  { id: "20000002-0000-4000-8000-000000000013", daysAgo: 13, text: "Anotei três prioridades para o expediente e consegui avançar sem alternar entre tantas tarefas.", emotion: "alegria", character: "Alegria", colorHex: "#58B368", subEmotion: "Foco", symbol: "📎", risk: false, macroTema: "trabalho", confidence: 0.9, sentimento: "alegria", polarity: 0.55, subtopics: [{ nome: "Organização de prioridades", descricao: "Definição de foco e sequência de tarefas no trabalho.", quote: "Anotei três prioridades para o expediente" }] },
  { id: "20000002-0000-4000-8000-000000000014", daysAgo: 14, text: "Recebi um retorno positivo sobre uma tarefa que concluí e fiquei satisfeito com o cuidado que coloquei nela.", emotion: "alegria", character: "Alegria", colorHex: "#58B368", subEmotion: "Reconhecimento", symbol: "⭐", risk: false, macroTema: "trabalho", confidence: 0.87, sentimento: "alegria", polarity: 0.67, subtopics: [{ nome: "Reconhecimento profissional", descricao: "Valorização de uma contribuição ou tarefa realizada no trabalho.", quote: "Recebi um retorno positivo sobre uma tarefa que concluí" }] },
  { id: "20000002-0000-4000-8000-000000000015", daysAgo: 15, text: "Fiz uma pausa curta entre reuniões e percebi que voltei com mais atenção para a conversa seguinte.", emotion: "calma", character: "Calma", colorHex: "#58B368", subEmotion: "Pausa", symbol: "☕", risk: false, macroTema: "trabalho", confidence: 0.82, sentimento: "calma", polarity: 0.43, subtopics: [{ nome: "Pausas no expediente", descricao: "Intervalos breves para descansar e retomar atividades profissionais.", quote: "Fiz uma pausa curta entre reuniões" }] },
  { id: "20000002-0000-4000-8000-000000000016", daysAgo: 16, text: "Cometi um pequeno erro e passei um tempo me cobrando, embora tenha conseguido corrigir a situação.", emotion: "tristeza", character: "Tristeza", colorHex: "#6687A3", subEmotion: "Autocrítica", symbol: "🪞", risk: false, macroTema: "autoestima", confidence: 0.89, sentimento: "frustracao", polarity: -0.51, subtopics: [{ nome: "Autocrítica e expectativas", descricao: "Cobrança pessoal elevada diante de falhas cotidianas.", quote: "Cometi um pequeno erro e passei um tempo me cobrando" }] },
  { id: "20000002-0000-4000-8000-000000000017", daysAgo: 17, text: "Olhei para trás e reconheci que avancei em algo que há algumas semanas parecia difícil para mim.", emotion: "alegria", character: "Alegria", colorHex: "#58B368", subEmotion: "Orgulho", symbol: "🏁", risk: false, macroTema: "autoestima", confidence: 0.86, sentimento: "alegria", polarity: 0.62, subtopics: [{ nome: "Reconhecimento das próprias conquistas", descricao: "Percepção de progresso pessoal e valorização do esforço realizado.", quote: "reconheci que avancei em algo que há algumas semanas parecia difícil" }] },
  { id: "20000002-0000-4000-8000-000000000018", daysAgo: 18, text: "Me comparei com outras pessoas nas redes sociais e precisei lembrar que cada um tem seu próprio ritmo.", emotion: "tristeza", character: "Tristeza", colorHex: "#6687A3", subEmotion: "Comparação", symbol: "🧱", risk: false, macroTema: "autoestima", confidence: 0.9, sentimento: "tristeza", polarity: -0.56, subtopics: [{ nome: "Comparação social", descricao: "Comparação com outras pessoas e impacto na percepção do próprio ritmo.", quote: "Me comparei com outras pessoas nas redes sociais" }] },
  { id: "20000002-0000-4000-8000-000000000019", daysAgo: 19, text: "Uma lembrança de alguém querido apareceu durante o dia; senti saudade e também gratidão pela convivência.", emotion: "tristeza", character: "Tristeza", colorHex: "#6687A3", subEmotion: "Saudade", symbol: "🕯️", risk: false, macroTema: "luto", confidence: 0.92, sentimento: "tristeza", polarity: -0.32, subtopics: [{ nome: "Saudade em lembranças", descricao: "Lembranças de pessoa querida acompanhadas de saudade e afeto.", quote: "senti saudade e também gratidão pela convivência" }] },
  { id: "20000002-0000-4000-8000-000000000020", daysAgo: 20, text: "Uma data especial me fez lembrar de uma pessoa que já não está aqui; conversei sobre isso com alguém próximo.", emotion: "tristeza", character: "Tristeza", colorHex: "#6687A3", subEmotion: "Memória afetiva", symbol: "📷", risk: false, macroTema: "luto", confidence: 0.88, sentimento: "tristeza", polarity: -0.36, subtopics: [{ nome: "Datas que despertam memória", descricao: "Datas significativas que trazem lembranças e sentimentos ligados a uma perda.", quote: "Uma data especial me fez lembrar de uma pessoa que já não está aqui" }] },
  { id: "20000002-0000-4000-8000-000000000021", daysAgo: 21, text: "Minha família me ofereceu ajuda com uma tarefa e foi bom perceber que posso contar com esse apoio.", emotion: "alegria", character: "Alegria", colorHex: "#58B368", subEmotion: "Acolhimento", symbol: "🏠", risk: false, macroTema: "familia", confidence: 0.9, sentimento: "alegria", polarity: 0.64, subtopics: [{ nome: "Apoio familiar", descricao: "Ajuda e disponibilidade de familiares diante de tarefas cotidianas.", quote: "Minha família me ofereceu ajuda com uma tarefa" }] },
  { id: "20000002-0000-4000-8000-000000000022", daysAgo: 22, text: "Conversei em casa sobre dividir melhor algumas tarefas e saímos com um combinado mais claro.", emotion: "calma", character: "Calma", colorHex: "#58B368", subEmotion: "Acordo", symbol: "🍲", risk: false, macroTema: "familia", confidence: 0.85, sentimento: "calma", polarity: 0.47, subtopics: [{ nome: "Divisão de tarefas em casa", descricao: "Acordos familiares para compartilhar responsabilidades domésticas.", quote: "Conversei em casa sobre dividir melhor algumas tarefas" }] },
  { id: "20000002-0000-4000-8000-000000000023", daysAgo: 23, text: "Separei um horário curto para estudar e avancei mais do que quando tentava deixar tudo para o fim do dia.", emotion: "alegria", character: "Alegria", colorHex: "#58B368", subEmotion: "Concentração", symbol: "📖", risk: false, macroTema: "estudos", confidence: 0.86, sentimento: "alegria", polarity: 0.5, subtopics: [{ nome: "Planejamento de estudos", descricao: "Organização de horário e etapas para manter uma rotina de estudos.", quote: "Separei um horário curto para estudar" }] },
  { id: "20000002-0000-4000-8000-000000000024", daysAgo: 24, text: "Fiquei um pouco tenso antes de uma avaliação, então revisei os pontos principais e fiz uma pausa para respirar.", emotion: "ansiedade", character: "Ansiedade", colorHex: "#E67E22", subEmotion: "Expectativa", symbol: "🗓️", risk: false, macroTema: "estudos", confidence: 0.88, sentimento: "preocupacao", polarity: -0.29, subtopics: [{ nome: "Preparação para avaliação", descricao: "Expectativa antes de uma avaliação e estratégias de preparação.", quote: "Fiquei um pouco tenso antes de uma avaliação" }] },
];

const BRUNO_REVISIT_SOURCE_INDICES = [0, 4, 7, 10, 13, 16, 18, 20, 22];
const RAW_BRUNO_SPECS = [
  ...RAW_BRUNO_CORE_SPECS,
  ...BRUNO_REVISIT_SOURCE_INDICES.map((sourceIndex, index) => {
    const source = RAW_BRUNO_CORE_SPECS[sourceIndex];
    return {
      ...source,
      id: `20000002-0000-4000-8000-${String(index + 25).padStart(12, "0")}`,
      daysAgo: 25 + index,
      text: `${source.text} Ao revisitar o assunto, consegui olhar para ele com um pouco mais de perspectiva.`,
    };
  }),
];

function getDemoSpecs(patientId) {
  if (patientId === DEMO_PATIENT_ID) return RAW_DEMO_SPECS;
  if (patientId === DEMO_BRUNO_PATIENT_ID) return RAW_BRUNO_SPECS;
  return null;
}

export function isDemoPatientId(patientId) {
  return getDemoSpecs(patientId) !== null;
}

export function getDemoPatientSummary(patientId = DEMO_PATIENT_ID) {
  const specs = getDemoSpecs(patientId);
  if (!specs) return null;

  let positive = 0;
  let negative = 0;
  let neutral = 0;
  let riskCount = 0;
  for (const item of specs) {
    if (item.risk) riskCount += 1;
    if (item.polarity >= 0.15) positive += 1;
    else if (item.polarity <= -0.15) negative += 1;
    else neutral += 1;
  }
  const latestDaysAgo = Math.min(...specs.map((item) => item.daysAgo));
  const oldestDaysAgo = Math.max(...specs.map((item) => item.daysAgo));
  const isBrunoDemo = patientId === DEMO_BRUNO_PATIENT_ID;
  return {
    id: patientId,
    name: isBrunoDemo
      ? "Bruno Henrique de Almeida Lima — CASO FICTÍCIO"
      : "Clara Mendes (Demo 24 Subtemas)",
    email: isBrunoDemo ? "bruno.demo@sintetico.local" : "clara.demo@sintetico.local",
    createdAt: new Date(daysAgoMs(isBrunoDemo ? oldestDaysAgo + 1 : 21)).toISOString(),
    entryCount: specs.length,
    riskCount,
    valenceBreakdown: { positive, neutral, negative },
    lastEntryAt: new Date(daysAgoMs(latestDaysAgo)).toISOString(),
    isDemo: true,
  };
}

export function getDemoPatientSummaries() {
  return [DEMO_PATIENT_ID, DEMO_BRUNO_PATIENT_ID].map((patientId) => getDemoPatientSummary(patientId));
}

export function getDemoPatientEntries(patientId = DEMO_PATIENT_ID) {
  const specs = getDemoSpecs(patientId);
  if (!specs) return [];

  return specs.map((spec) => {
    const createdAt = daysAgoMs(spec.daysAgo);
    const createdAtIso = new Date(createdAt).toISOString();
    const agent1 = makeDemoAgent1({
      id: spec.id,
      patientId,
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
      patient_id: patientId,
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
