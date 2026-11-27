/**
 * Taxonomia Visual Divertidamente (Inside Out) e How We Feel para o front-end Next.js.
 */

export const EMOTIONS_DIVERTIDAMENTE = {
  alegria: {
    id: "alegria",
    personagem: "Alegria",
    corNome: "Amarelo",
    corHex: "#FFD700",
    corSecundariaHex: "#FFF9C4",
    corTexto: "#7A6000",
    descricao: "Celebração da vida, otimismo, gratidão e estados de ânimo radiantes.",
    isRiskEmotion: false,
    subSentimentos: [
      { id: "gratidao", nome: "Gratidão", simbolo: "🙏", descricao: "Apreço caloroso pelo suporte e pequenas vitórias." },
      { id: "otimismo", nome: "Otimismo", simbolo: "☀️", descricao: "Esperança e confiança em dias melhores." },
      { id: "entusiasmo", nome: "Entusiasmo", simbolo: "🌟", descricao: "Vitalidade e energia radiante no presente." },
    ],
  },
  tristeza: {
    id: "tristeza",
    personagem: "Tristeza",
    corNome: "Azul",
    corHex: "#1E88E5",
    corSecundariaHex: "#BBDEFB",
    corTexto: "#0D47A1",
    descricao: "Recolhimento, elaboração de perdas e necessidade de acolhimento.",
    isRiskEmotion: true,
    subSentimentos: [
      { id: "desanimo", nome: "Desânimo", simbolo: "🌧️", descricao: "Falta de motivação e sensação de peso interior." },
      { id: "luto", nome: "Luto", simbolo: "💧", descricao: "Dor profunda por uma perda e choro doloroso." },
      { id: "decepcao", nome: "Decepção", simbolo: "🌫️", descricao: "Frustração diante de expectativas não atendidas." },
    ],
  },
  medo: {
    id: "medo",
    personagem: "Medo",
    corNome: "Roxo",
    corHex: "#8E24AA",
    corSecundariaHex: "#E1BEE7",
    corTexto: "#4A148C",
    descricao: "Alerta protetor diante de ameaças ou incertezas de saúde.",
    isRiskEmotion: true,
    subSentimentos: [
      { id: "ansiedade", nome: "Ansiedade", simbolo: "🌀", descricao: "Preocupação antecipatória e pensamentos acelerados." },
      { id: "panico", nome: "Pânico", simbolo: "⚡", descricao: "Alarme físico súbito, taquicardia e falta de ar." },
      { id: "inseguranca", nome: "Insegurança", simbolo: "〰️", descricao: "Vulnerabilidade e receio perante o tratamento." },
    ],
  },
  raiva: {
    id: "raiva",
    personagem: "Raiva",
    corNome: "Vermelho",
    corHex: "#E53935",
    corSecundariaHex: "#FFCDD2",
    corTexto: "#B71C1C",
    descricao: "Mobilização de energia impulsionada por injustiças ou dores.",
    isRiskEmotion: true,
    subSentimentos: [
      { id: "irritacao", nome: "Irritação", simbolo: "💢", descricao: "Impaciência com atritos e incômodos cotidianos." },
      { id: "indignacao", nome: "Indignação", simbolo: "🔥", descricao: "Revolta moral contra descaso ou desrespeito." },
      { id: "furia", nome: "Fúria", simbolo: "💥", descricao: "Cólera explosiva que demanda acolhimento e escuta." },
    ],
  },
  nojinho: {
    id: "nojinho",
    personagem: "Nojinho",
    corNome: "Verde",
    corHex: "#43A047",
    corSecundariaHex: "#C8E6C9",
    corTexto: "#1B5E20",
    descricao: "Instinto de proteção contra estímulos desagradáveis ou atitudes tóxicas.",
    isRiskEmotion: false,
    subSentimentos: [
      { id: "aversao", nome: "Aversão", simbolo: "🛡️", descricao: "Repulsa física a cheiros, gostos ou medicamentos insalubres." },
      { id: "desconforto", nome: "Desconforto", simbolo: "🍋", descricao: "Estranhamento corporal, mal-estar ou enjoo." },
      { id: "desprezo", nome: "Desprezo", simbolo: "🚫", descricao: "Rejeição a falsidades ou atitudes invasivas." },
    ],
  },
  neutro: {
    id: "neutro",
    personagem: "Equilíbrio",
    corNome: "Cinza",
    corHex: "#9E9E9E",
    corSecundariaHex: "#ECEFF1",
    corTexto: "#424242",
    descricao: "Relato factual da rotina diária sem oscilações emocionais marcantes.",
    isRiskEmotion: false,
    subSentimentos: [
      { id: "equilibrio", nome: "Equilíbrio", simbolo: "⚖️", descricao: "Estabilidade cotidiana e fatos normais do dia." },
      { id: "serenidade", nome: "Serenidade", simbolo: "🌊", descricao: "Paz de espírito, sossego e tranquilidade suave." },
      { id: "sobriedade", nome: "Sobriedade", simbolo: "🍃", descricao: "Foco objetivo em horários de remédios e exames." },
    ],
  },
  surpresa: {
    id: "surpresa",
    personagem: "Surpresa",
    corNome: "Laranja",
    corHex: "#FB8C00",
    corSecundariaHex: "#FFE0B2",
    corTexto: "#7A4300",
    descricao: "ReaÃ§Ã£o de impacto ou quebra de expectativa diante do inesperado.",
    isRiskEmotion: false,
    subSentimentos: [
      { id: "espanto", nome: "Espanto", simbolo: "😮", descricao: "Sobressalto diante de um acontecimento inesperado." },
      { id: "curiosidade", nome: "Curiosidade", simbolo: "🔍", descricao: "Interesse desperto para compreender uma novidade." },
      { id: "descoberta", nome: "Descoberta", simbolo: "💡", descricao: "Clareza repentina diante de uma nova percepÃ§Ã£o." },
    ],
  },
};

export function getEmotionProfile(id) {
  if (!id) return EMOTIONS_DIVERTIDAMENTE.neutro;
  const key = id.toLowerCase().trim();
  if (key === "nojo") return EMOTIONS_DIVERTIDAMENTE.nojinho;
  return EMOTIONS_DIVERTIDAMENTE[key] || EMOTIONS_DIVERTIDAMENTE.neutro;
}

const subEmotionColors = {
  gratidao: ["#45C898", "#E3F6ED"],
  otimismo: ["#E7C34F", "#FBF4D9"],
  entusiasmo: ["#E8A93F", "#F9ECD9"],
  desanimo: ["#78A8E8", "#E9F1FC"],
  luto: ["#5D77C8", "#E9ECF8"],
  decepcao: ["#8798D8", "#EDF0FA"],
  ansiedade: ["#E98776", "#F9EAE6"],
  panico: ["#D84F5B", "#F7E5E7"],
  inseguranca: ["#8076C5", "#EEECF8"],
  irritacao: ["#E88B56", "#F9ECE2"],
  indignacao: ["#D95F4D", "#F7E6E2"],
  furia: ["#C9434B", "#F5E2E4"],
  aversao: ["#78AA83", "#EAF3E9"],
  desconforto: ["#5AA89C", "#E5F2EF"],
  desprezo: ["#9A9A59", "#F1F0E4"],
  equilibrio: ["#7F8D86", "#EAEFEB"],
  serenidade: ["#55A88C", "#E4F2EB"],
  sobriedade: ["#80959A", "#E9EFF0"],
  espanto: ["#E9A847", "#FBF1DF"],
  curiosidade: ["#D59238", "#F8EEDD"],
  descoberta: ["#C98032", "#F6E9DD"],
};

function normalizeEmotionName(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

export function getSubEmotionProfile(emotionId, subEmotion) {
  const profile = getEmotionProfile(emotionId);
  const target = normalizeEmotionName(subEmotion);
  const sub = profile.subSentimentos.find(
    (item) => item.id === target || normalizeEmotionName(item.nome) === target,
  );
  if (!sub) return null;

  const [corHex, corSecundariaHex] = subEmotionColors[sub.id] || [profile.corHex, profile.corSecundariaHex];
  return { ...sub, corHex, corSecundariaHex };
}
