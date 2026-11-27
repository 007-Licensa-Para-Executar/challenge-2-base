import { redirect } from "next/navigation";

export const metadata = {
  title: "Painel Clínico | Meu Diário",
  description: "Exploração de temas e subtemas dos registros do diário.",
};

export default function ImpactBenchPage() {
  redirect("/psicologa?secao=explorar");
}
