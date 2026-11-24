export type SupervisorCategory = "Especialidade" | "Área de foco" | "Abordagem";

export type ExternalSupervisor = {
  id: string;
  name: string;
  category: SupervisorCategory;
  primaryTerm: string;
  specialties: string[];
  focusAreas: string[];
  approaches: string[];
  email: string;
  city: string;
  phone: string;
  yearsOfExperience: number;
};

type SupervisorSeed = Omit<ExternalSupervisor, "id" | "email" | "phone">;

export const SUPERVISOR_FILTER_GROUPS = [
  {
    label: "Especialidades",
    options: [
      "Psicologia Clínica",
      "Psicologia Escolar e Educacional",
      "Psicologia Organizacional e do Trabalho",
      "Psicologia de Tráfego",
      "Psicologia Jurídica",
      "Psicologia do Esporte",
      "Psicologia Hospitalar",
      "Psicopedagogia",
      "Psicomotricidade",
      "Psicologia Social",
      "Neuropsicologia",
      "Psicologia em Saúde",
      "Avaliação Psicológica",
    ],
  },
  {
    label: "Áreas de foco",
    options: [
      "Ansiedade e síndrome do pânico",
      "Depressão",
      "Relacionamentos amorosos",
      "Terapia de casal",
      "Terapia familiar",
      "Autoestima e autoconhecimento",
      "Luto e perdas",
      "Traumas psicológicos",
      "Psicologia infantil",
      "Psicologia do adolescente",
      "Psicologia do idoso",
      "Sexualidade",
      "Dependência química",
      "Dependência emocional",
      "Transtornos alimentares",
      "Transtornos de personalidade",
      "Estresse e burnout",
      "Transtorno de Déficit de Atenção e Hiperatividade – TDAH",
      "Transtorno do Espectro Autista – TEA",
      "Transtorno Obsessivo-Compulsivo – TOC",
      "Transtornos do sono",
      "Orientação profissional",
      "Comportamento financeiro",
      "Psicologia perinatal e parentalidade",
    ],
  },
  {
    label: "Abordagens",
    options: [
      "Terapia Cognitivo-Comportamental – TCC",
      "Psicanálise",
      "Gestalt-terapia",
      "Psicologia Analítica – Junguiana",
      "Abordagem Centrada na Pessoa – ACP",
      "Terapia Sistêmica",
      "Análise do Comportamento",
      "Terapia de Aceitação e Compromisso – ACT",
      "Terapia Comportamental Dialética – DBT",
      "Terapia do Esquema",
      "Logoterapia",
      "EMDR",
      "Terapia Existencial",
    ],
  },
] as const;

const SUPERVISOR_SEEDS: SupervisorSeed[] = [
  { name: "Ada Valen", category: "Especialidade", primaryTerm: "Psicologia Clínica", specialties: ["Psicologia Clínica"], focusAreas: ["Ansiedade e síndrome do pânico", "Depressão", "Relacionamentos amorosos", "Traumas psicológicos"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "São Paulo, SP", yearsOfExperience: 22 },
  { name: "Nilo Arven", category: "Especialidade", primaryTerm: "Psicologia Escolar e Educacional", specialties: ["Psicologia Escolar e Educacional"], focusAreas: ["Psicologia infantil", "Transtorno de Déficit de Atenção e Hiperatividade – TDAH", "Transtorno do Espectro Autista – TEA"], approaches: ["Análise do Comportamento"], city: "Curitiba, PR", yearsOfExperience: 18 },
  { name: "Lina Seravel", category: "Especialidade", primaryTerm: "Psicologia Organizacional e do Trabalho", specialties: ["Psicologia Organizacional e do Trabalho"], focusAreas: ["Estresse e burnout", "Orientação profissional"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "São Paulo, SP", yearsOfExperience: 20 },
  { name: "Ivo Norvale", category: "Especialidade", primaryTerm: "Psicologia de Tráfego", specialties: ["Psicologia de Tráfego"], focusAreas: ["Avaliação Psicológica"], approaches: [], city: "Brasília, DF", yearsOfExperience: 17 },
  { name: "Maya Lioren", category: "Especialidade", primaryTerm: "Psicologia Jurídica", specialties: ["Psicologia Jurídica"], focusAreas: ["Terapia familiar", "Relacionamentos amorosos"], approaches: ["Terapia Sistêmica"], city: "Recife, PE", yearsOfExperience: 21 },
  { name: "Cael Verdan", category: "Especialidade", primaryTerm: "Psicologia do Esporte", specialties: ["Psicologia do Esporte"], focusAreas: ["Autoestima e autoconhecimento", "Estresse e burnout"], approaches: ["Abordagem Centrada na Pessoa – ACP"], city: "Belo Horizonte, MG", yearsOfExperience: 19 },
  { name: "Lia Maren", category: "Especialidade", primaryTerm: "Psicologia Hospitalar", specialties: ["Psicologia Hospitalar"], focusAreas: ["Luto e perdas", "Traumas psicológicos", "Psicologia do idoso"], approaches: ["Abordagem Centrada na Pessoa – ACP"], city: "Rio de Janeiro, RJ", yearsOfExperience: 24 },
  { name: "Noa Estelar", category: "Especialidade", primaryTerm: "Psicopedagogia", specialties: ["Psicopedagogia"], focusAreas: ["Psicologia infantil", "Transtorno de Déficit de Atenção e Hiperatividade – TDAH"], approaches: ["Análise do Comportamento"], city: "Campinas, SP", yearsOfExperience: 16 },
  { name: "Ravi Alvor", category: "Especialidade", primaryTerm: "Psicomotricidade", specialties: ["Psicomotricidade"], focusAreas: ["Psicologia infantil", "Transtorno do Espectro Autista – TEA"], approaches: [], city: "Florianópolis, SC", yearsOfExperience: 18 },
  { name: "Dara Virel", category: "Especialidade", primaryTerm: "Psicologia Social", specialties: ["Psicologia Social"], focusAreas: ["Autoestima e autoconhecimento", "Dependência química"], approaches: ["Terapia Sistêmica"], city: "Salvador, BA", yearsOfExperience: 23 },
  { name: "Elian Solver", category: "Especialidade", primaryTerm: "Neuropsicologia", specialties: ["Neuropsicologia"], focusAreas: ["Transtorno de Déficit de Atenção e Hiperatividade – TDAH", "Transtorno do Espectro Autista – TEA", "Transtorno Obsessivo-Compulsivo – TOC"], approaches: [], city: "Curitiba, PR", yearsOfExperience: 22 },
  { name: "Nara Velnor", category: "Especialidade", primaryTerm: "Psicologia em Saúde", specialties: ["Psicologia em Saúde"], focusAreas: ["Transtornos do sono", "Transtornos alimentares", "Psicologia perinatal e parentalidade"], approaches: ["Terapia de Aceitação e Compromisso – ACT"], city: "Porto Alegre, RS", yearsOfExperience: 20 },
  { name: "Lume Arvato", category: "Especialidade", primaryTerm: "Avaliação Psicológica", specialties: ["Avaliação Psicológica"], focusAreas: ["Transtorno de Déficit de Atenção e Hiperatividade – TDAH", "Transtornos de personalidade"], approaches: [], city: "Brasília, DF", yearsOfExperience: 25 },

  { name: "Viana Solen", category: "Área de foco", primaryTerm: "Ansiedade e síndrome do pânico", specialties: ["Psicologia Clínica"], focusAreas: ["Ansiedade e síndrome do pânico"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "São Paulo, SP", yearsOfExperience: 15 },
  { name: "Ciro Meral", category: "Área de foco", primaryTerm: "Depressão", specialties: ["Psicologia Clínica"], focusAreas: ["Depressão", "Luto e perdas"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "Curitiba, PR", yearsOfExperience: 18 },
  { name: "Amira Norval", category: "Área de foco", primaryTerm: "Relacionamentos amorosos", specialties: ["Psicologia Clínica"], focusAreas: ["Relacionamentos amorosos", "Dependência emocional"], approaches: ["Abordagem Centrada na Pessoa – ACP"], city: "Rio de Janeiro, RJ", yearsOfExperience: 14 },
  { name: "Theo Seral", category: "Área de foco", primaryTerm: "Terapia de casal", specialties: ["Psicologia Clínica"], focusAreas: ["Terapia de casal", "Relacionamentos amorosos"], approaches: ["Terapia Sistêmica"], city: "Campinas, SP", yearsOfExperience: 16 },
  { name: "Iara Belmonte", category: "Área de foco", primaryTerm: "Terapia familiar", specialties: ["Psicologia Jurídica", "Psicologia Clínica"], focusAreas: ["Terapia familiar", "Terapia de casal"], approaches: ["Terapia Sistêmica"], city: "Belo Horizonte, MG", yearsOfExperience: 17 },
  { name: "Sora Ventrel", category: "Área de foco", primaryTerm: "Autoestima e autoconhecimento", specialties: ["Psicologia Clínica"], focusAreas: ["Autoestima e autoconhecimento"], approaches: ["Gestalt-terapia"], city: "Porto Alegre, RS", yearsOfExperience: 13 },
  { name: "Milo Ardan", category: "Área de foco", primaryTerm: "Luto e perdas", specialties: ["Psicologia Hospitalar"], focusAreas: ["Luto e perdas", "Psicologia do idoso"], approaches: ["Logoterapia"], city: "Recife, PE", yearsOfExperience: 19 },
  { name: "Yara Solmar", category: "Área de foco", primaryTerm: "Traumas psicológicos", specialties: ["Psicologia Clínica", "Psicologia Hospitalar"], focusAreas: ["Traumas psicológicos", "Ansiedade e síndrome do pânico"], approaches: ["EMDR"], city: "São Paulo, SP", yearsOfExperience: 20 },
  { name: "Luan Arvella", category: "Área de foco", primaryTerm: "Psicologia infantil", specialties: ["Psicologia Escolar e Educacional", "Psicologia Clínica"], focusAreas: ["Psicologia infantil", "Transtorno do Espectro Autista – TEA"], approaches: ["Análise do Comportamento"], city: "Curitiba, PR", yearsOfExperience: 16 },
  { name: "Iris Valora", category: "Área de foco", primaryTerm: "Psicologia do adolescente", specialties: ["Psicologia Clínica", "Psicologia Escolar e Educacional"], focusAreas: ["Psicologia do adolescente", "Autoestima e autoconhecimento"], approaches: ["Terapia Comportamental Dialética – DBT"], city: "Brasília, DF", yearsOfExperience: 13 },
  { name: "Gael Novera", category: "Área de foco", primaryTerm: "Psicologia do idoso", specialties: ["Psicologia em Saúde", "Psicologia Hospitalar"], focusAreas: ["Psicologia do idoso", "Luto e perdas"], approaches: ["Abordagem Centrada na Pessoa – ACP"], city: "Santos, SP", yearsOfExperience: 22 },
  { name: "Eloa Marven", category: "Área de foco", primaryTerm: "Sexualidade", specialties: ["Psicologia Clínica"], focusAreas: ["Sexualidade", "Relacionamentos amorosos"], approaches: ["Gestalt-terapia"], city: "Salvador, BA", yearsOfExperience: 15 },
  { name: "Enzo Lumin", category: "Área de foco", primaryTerm: "Dependência química", specialties: ["Psicologia em Saúde", "Psicologia Clínica"], focusAreas: ["Dependência química", "Estresse e burnout"], approaches: ["Terapia Comportamental Dialética – DBT"], city: "Goiânia, GO", yearsOfExperience: 18 },
  { name: "Talia Seravim", category: "Área de foco", primaryTerm: "Dependência emocional", specialties: ["Psicologia Clínica"], focusAreas: ["Dependência emocional", "Relacionamentos amorosos"], approaches: ["Terapia do Esquema"], city: "São Paulo, SP", yearsOfExperience: 12 },
  { name: "Ruan Alver", category: "Área de foco", primaryTerm: "Transtornos alimentares", specialties: ["Psicologia em Saúde", "Psicologia Clínica"], focusAreas: ["Transtornos alimentares", "Autoestima e autoconhecimento"], approaches: ["Terapia de Aceitação e Compromisso – ACT"], city: "Belo Horizonte, MG", yearsOfExperience: 21 },
  { name: "Mila Norven", category: "Área de foco", primaryTerm: "Transtornos de personalidade", specialties: ["Psicologia Clínica"], focusAreas: ["Transtornos de personalidade", "Dependência emocional"], approaches: ["Terapia Comportamental Dialética – DBT"], city: "Porto Alegre, RS", yearsOfExperience: 19 },
  { name: "Aris Ventora", category: "Área de foco", primaryTerm: "Estresse e burnout", specialties: ["Psicologia Organizacional e do Trabalho", "Psicologia em Saúde"], focusAreas: ["Estresse e burnout", "Orientação profissional"], approaches: ["Terapia de Aceitação e Compromisso – ACT"], city: "São Paulo, SP", yearsOfExperience: 17 },
  { name: "Lina Maralto", category: "Área de foco", primaryTerm: "Transtorno de Déficit de Atenção e Hiperatividade – TDAH", specialties: ["Neuropsicologia", "Psicologia Escolar e Educacional"], focusAreas: ["Transtorno de Déficit de Atenção e Hiperatividade – TDAH", "Psicologia infantil"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "Curitiba, PR", yearsOfExperience: 18 },
  { name: "Caio Serev", category: "Área de foco", primaryTerm: "Transtorno do Espectro Autista – TEA", specialties: ["Neuropsicologia", "Psicologia Escolar e Educacional"], focusAreas: ["Transtorno do Espectro Autista – TEA", "Psicologia infantil"], approaches: ["Análise do Comportamento"], city: "Campinas, SP", yearsOfExperience: 16 },
  { name: "Nina Valmer", category: "Área de foco", primaryTerm: "Transtorno Obsessivo-Compulsivo – TOC", specialties: ["Psicologia Clínica", "Neuropsicologia"], focusAreas: ["Transtorno Obsessivo-Compulsivo – TOC", "Ansiedade e síndrome do pânico"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "Rio de Janeiro, RJ", yearsOfExperience: 20 },
  { name: "Davi Alvoran", category: "Área de foco", primaryTerm: "Transtornos do sono", specialties: ["Psicologia em Saúde"], focusAreas: ["Transtornos do sono", "Ansiedade e síndrome do pânico"], approaches: ["Terapia de Aceitação e Compromisso – ACT"], city: "Curitiba, PR", yearsOfExperience: 14 },
  { name: "Maya Serenor", category: "Área de foco", primaryTerm: "Orientação profissional", specialties: ["Psicologia Organizacional e do Trabalho"], focusAreas: ["Orientação profissional", "Autoestima e autoconhecimento"], approaches: ["Abordagem Centrada na Pessoa – ACP"], city: "Porto Alegre, RS", yearsOfExperience: 18 },
  { name: "Theo Valen", category: "Área de foco", primaryTerm: "Comportamento financeiro", specialties: ["Psicologia Clínica", "Psicologia Organizacional e do Trabalho"], focusAreas: ["Comportamento financeiro", "Estresse e burnout"], approaches: ["Terapia de Aceitação e Compromisso – ACT"], city: "São Paulo, SP", yearsOfExperience: 12 },
  { name: "Lira Solenne", category: "Área de foco", primaryTerm: "Psicologia perinatal e parentalidade", specialties: ["Psicologia em Saúde", "Psicologia Clínica"], focusAreas: ["Psicologia perinatal e parentalidade", "Terapia familiar"], approaches: ["Terapia Sistêmica"], city: "Recife, PE", yearsOfExperience: 13 },

  { name: "Noemi Arvello", category: "Abordagem", primaryTerm: "Terapia Cognitivo-Comportamental – TCC", specialties: ["Psicologia Clínica"], focusAreas: ["Ansiedade e síndrome do pânico", "Depressão", "Transtorno Obsessivo-Compulsivo – TOC"], approaches: ["Terapia Cognitivo-Comportamental – TCC"], city: "São Paulo, SP", yearsOfExperience: 20 },
  { name: "Cael Lior", category: "Abordagem", primaryTerm: "Psicanálise", specialties: ["Psicologia Clínica"], focusAreas: ["Traumas psicológicos", "Luto e perdas", "Relacionamentos amorosos"], approaches: ["Psicanálise"], city: "Porto Alegre, RS", yearsOfExperience: 24 },
  { name: "Lia Monteval", category: "Abordagem", primaryTerm: "Gestalt-terapia", specialties: ["Psicologia Clínica"], focusAreas: ["Autoestima e autoconhecimento", "Relacionamentos amorosos"], approaches: ["Gestalt-terapia"], city: "Rio de Janeiro, RJ", yearsOfExperience: 18 },
  { name: "Nilo Sereno", category: "Abordagem", primaryTerm: "Psicologia Analítica – Junguiana", specialties: ["Psicologia Clínica"], focusAreas: ["Luto e perdas", "Autoestima e autoconhecimento"], approaches: ["Psicologia Analítica – Junguiana"], city: "Belo Horizonte, MG", yearsOfExperience: 20 },
  { name: "Aira Nover", category: "Abordagem", primaryTerm: "Abordagem Centrada na Pessoa – ACP", specialties: ["Psicologia Clínica"], focusAreas: ["Autoestima e autoconhecimento", "Psicologia do adolescente"], approaches: ["Abordagem Centrada na Pessoa – ACP"], city: "Recife, PE", yearsOfExperience: 17 },
  { name: "Ivo Miral", category: "Abordagem", primaryTerm: "Terapia Sistêmica", specialties: ["Psicologia Clínica", "Psicologia Jurídica"], focusAreas: ["Terapia familiar", "Terapia de casal"], approaches: ["Terapia Sistêmica"], city: "São Paulo, SP", yearsOfExperience: 18 },
  { name: "Dara Solven", category: "Abordagem", primaryTerm: "Análise do Comportamento", specialties: ["Psicologia Escolar e Educacional", "Neuropsicologia"], focusAreas: ["Psicologia infantil", "Transtorno do Espectro Autista – TEA", "Transtorno de Déficit de Atenção e Hiperatividade – TDAH"], approaches: ["Análise do Comportamento"], city: "Curitiba, PR", yearsOfExperience: 21 },
  { name: "Elian Veral", category: "Abordagem", primaryTerm: "Terapia de Aceitação e Compromisso – ACT", specialties: ["Psicologia Clínica", "Psicologia em Saúde"], focusAreas: ["Estresse e burnout", "Ansiedade e síndrome do pânico", "Depressão"], approaches: ["Terapia de Aceitação e Compromisso – ACT"], city: "Campinas, SP", yearsOfExperience: 15 },
  { name: "Sora Almar", category: "Abordagem", primaryTerm: "Terapia Comportamental Dialética – DBT", specialties: ["Psicologia Clínica"], focusAreas: ["Transtornos de personalidade", "Dependência emocional", "Psicologia do adolescente"], approaches: ["Terapia Comportamental Dialética – DBT"], city: "São Paulo, SP", yearsOfExperience: 19 },
  { name: "Ciro Valora", category: "Abordagem", primaryTerm: "Terapia do Esquema", specialties: ["Psicologia Clínica"], focusAreas: ["Transtornos de personalidade", "Traumas psicológicos", "Dependência emocional"], approaches: ["Terapia do Esquema"], city: "Curitiba, PR", yearsOfExperience: 16 },
  { name: "Yara Norvel", category: "Abordagem", primaryTerm: "Logoterapia", specialties: ["Psicologia Clínica", "Psicologia Hospitalar"], focusAreas: ["Luto e perdas", "Autoestima e autoconhecimento"], approaches: ["Logoterapia"], city: "Porto Alegre, RS", yearsOfExperience: 22 },
  { name: "Milo Serev", category: "Abordagem", primaryTerm: "EMDR", specialties: ["Psicologia Clínica", "Psicologia Hospitalar"], focusAreas: ["Traumas psicológicos", "Ansiedade e síndrome do pânico"], approaches: ["EMDR"], city: "Rio de Janeiro, RJ", yearsOfExperience: 18 },
  { name: "Ada Ventral", category: "Abordagem", primaryTerm: "Terapia Existencial", specialties: ["Psicologia Clínica"], focusAreas: ["Autoestima e autoconhecimento", "Luto e perdas", "Relacionamentos amorosos"], approaches: ["Terapia Existencial"], city: "Florianópolis, SC", yearsOfExperience: 20 },
];

const number = (value: number) => String(value).padStart(4, "0");

export const EXTERNAL_SUPERVISORS: ExternalSupervisor[] = SUPERVISOR_SEEDS.map(
  (supervisor, index) => {
    const id = index + 1;
    const code = String(id).padStart(2, "0");
    return {
      ...supervisor,
      id: `supervisor-${code}`,
      email: `supervisor-${code}@supervisores.example`,
      phone: `+55 (00) 90000-${number(id)}`,
    };
  },
);

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .replace(/[–—-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function shouldShowExternalSupervisorsButton(patientId: string | null | undefined) {
  return Boolean(patientId?.trim());
}

export function filterExternalSupervisors(query: string) {
  const normalizedQuery = normalize(query);
  if (!normalizedQuery) return [];

  return EXTERNAL_SUPERVISORS.map((supervisor) => {
    const primaryTerm = normalize(supervisor.primaryTerm);
    const relatedTerms = [
      ...supervisor.specialties,
      ...supervisor.focusAreas,
      ...supervisor.approaches,
    ].map(normalize);
    const relevance = primaryTerm === normalizedQuery
      ? 4
      : primaryTerm.includes(normalizedQuery)
        ? 3
        : relatedTerms.some((term) => term === normalizedQuery)
          ? 2
          : relatedTerms.some((term) => term.includes(normalizedQuery))
            ? 1
            : 0;

    return { supervisor, relevance };
  })
    .filter((result) => result.relevance > 0)
    .sort(
      (left, right) =>
        right.relevance - left.relevance ||
        right.supervisor.yearsOfExperience - left.supervisor.yearsOfExperience ||
        left.supervisor.name.localeCompare(right.supervisor.name, "pt-BR"),
    )
    .map(({ supervisor }) => supervisor);
}
