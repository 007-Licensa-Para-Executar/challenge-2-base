import { autenticarPaciente } from "../_backend";

export const runtime = "nodejs";

// POST /api/auth/login confere o cadastro local e cria uma sessão.
export async function POST(request) {
  const corpo = await request.json().catch(() => null);
  const email = typeof corpo?.email === "string" ? corpo.email.trim().toLowerCase() : "";
  const senha = typeof corpo?.senha === "string" ? corpo.senha : "";

  if (
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ||
    email.length > 254 ||
    !senha ||
    senha.length > 128
  ) {
    return Response.json(
      { message: "Informe um e-mail válido e sua senha." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const sessao = await autenticarPaciente(email, senha);
    if (!sessao) {
      return Response.json(
        { message: "E-mail ou senha não conferem." },
        { status: 401, headers: { "Cache-Control": "no-store" } },
      );
    }

    return Response.json(
      { message: "Acesso realizado com sucesso." },
      {
        headers: {
          "Cache-Control": "no-store",
          "Set-Cookie": sessao.cookie,
        },
      },
    );
  } catch {
    return Response.json(
      { message: "Não foi possível acessar sua conta agora." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
