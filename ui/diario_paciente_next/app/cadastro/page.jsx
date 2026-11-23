import Link from "next/link";
import AuthForm from "../AuthForm";
import AuthShell from "../AuthShell";

// Cadastro: compartilha o layout; no celular os campos extras continuam acessíveis com o teclado aberto.
export default function CadastroPage() {
  return (
    <AuthShell
      eyebrow="SEU ESPAÇO COMEÇA AQUI"
      title="Vamos começar com calma"
      description="Crie seu acesso para registrar seus pensamentos no seu próprio ritmo."
      footer={
        <p>
          Já tem uma conta? <Link href="/">Entre por aqui</Link>
        </p>
      }
    >
      <AuthForm mode="cadastro" />
    </AuthShell>
  );
}
