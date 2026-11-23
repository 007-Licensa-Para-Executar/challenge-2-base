import PatientManagement from "./PatientManagement";

export const metadata = {
  title: "Pacientes | Meu Diário",
  description: "Acompanhamento de pacientes e registros do diário.",
};

// A página fica no servidor; a interação da lista e dos painéis roda no cliente.
export default function PsychologistPage() {
  return <PatientManagement />;
}
