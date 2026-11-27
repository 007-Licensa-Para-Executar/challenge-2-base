export interface PatientChatRequest {
  patientId: string;
  question: string;
}

export async function requestPatientChatReply({ patientId, question }: PatientChatRequest) {
  if (!patientId.trim()) throw new Error("Não foi possível identificar o paciente selecionado.");
  if (!question.trim()) throw new Error("Digite uma pergunta para continuar.");

  await new Promise((resolve) => setTimeout(resolve, 450));

  return "A integração com IA ainda não está conectada. Nenhuma análise clínica foi realizada.";
}
