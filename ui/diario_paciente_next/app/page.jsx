import Link from "next/link";
import AuthForm from "./AuthForm";
import AuthShell from "./AuthShell";

// Login: desktop usa dois painéis; no iPhone e Android o cabeçalho fica acima do formulário rolável.
export default function LoginPage() {
  return (
    <AuthShell
      eyebrow="BOM TER VOCÊ POR AQUI"
      title="Acesse seu diário"
      description="Entre para continuar seu momento de cuidado e reflexão."
      footer={
        <>
          <p>
            Ainda não tem acesso? <Link href="/cadastro">Cadastre-se</Link>
          </p>
          <p style={{ marginTop: "6px", fontSize: "12px" }}>
            <Link href="/psicologa">Área Profissional · Painel da Psicóloga</Link>
          </p>
        </>
      }
    >
      <AuthForm mode="login" />
    </AuthShell>
  );
}
