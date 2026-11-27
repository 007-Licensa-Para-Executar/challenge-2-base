import PatientManagement from "./PatientManagement";

export const metadata = {
  title: "Painel profissional | Meu Diário",
  description: "Gestão de pacientes, exploração da Roda, relatórios e copiloto clínico.",
};

// A página fica no servidor; a interação da lista e dos painéis roda no cliente.
export default async function PsychologistPage({
  searchParams,
}: {
  searchParams: Promise<{ secao?: string | string[] }>;
}) {
  const section = (await searchParams).secao;
  const initialSection = Array.isArray(section) ? section[0] : section;
  return <PatientManagement initialSection={initialSection} />;
}
