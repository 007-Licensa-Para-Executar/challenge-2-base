// Tipos compartilhados pela tela profissional e pela fonte mockada.
export const DASHBOARD_THEMES = [
  "Relacionamentos",
  "Saúde e Sono",
  "Finanças",
  "Outros / Indeterminado",
  "Trabalho",
  "Autoestima",
  "Luto",
  "Família",
  "Estudos",
] as const;

export type DashboardTheme = (typeof DASHBOARD_THEMES)[number];
export type LinkStatus = "vinculado" | "aguardando_vinculo";
export type HistoryType = "relatorio" | "diario" | "consulta";
export type ReportStatus = "enviando" | "concluido";

export type ThemeDistribution = Record<DashboardTheme, number>;

export interface WeeklyDiaryCount {
  label: string;
  entries: number;
}

// Formato enxuto retornado pela rota local de cadastros.
export interface PortalPatientRecord {
  id: string;
  name: string;
  email: string;
  createdAt: string;
  address: string;
  age: number | null;
  treatmentDurationMonths: number | null;
  psychiatricTreatment: boolean;
  isDemo?: boolean;
}

export interface EditablePatientProfile {
  id: string;
  name: string;
  address: string;
  age: number | null;
  treatmentDurationMonths: number | null;
  psychiatricTreatment: boolean;
}

export interface UploadedReport {
  id: string;
  fileName: string;
  uploadedAt: string;
  status: ReportStatus;
  progress: number;
}

export interface PatientHistoryItem {
  id: string;
  type: HistoryType;
  title: string;
  description: string;
  date: string;
  theme?: DashboardTheme;
  reportId?: string;
}

// A origem e a data do cadastro permitem substituir o mock pela API do portal.
export interface PortalPatient {
  id: string;
  portalUserId: string;
  fullName: string;
  email: string;
  address: string;
  age: number | null;
  treatmentDurationMonths: number | null;
  psychiatricTreatment: boolean;
  initials: string;
  registeredAt: string;
  source: "portal_cadastro";
  linkStatus: LinkStatus;
  psychologistId: string | null;
  reports: UploadedReport[];
  history: PatientHistoryItem[];
  weeklyDiaryCounts: WeeklyDiaryCount[];
  themeDistribution: ThemeDistribution;
  isDemo?: boolean;
}
