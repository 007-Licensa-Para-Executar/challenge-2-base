import { criarPaciente } from "../_backend";

export const runtime = "nodejs";

// POST /api/auth/cadastro valida os dados básicos do novo paciente.
export async function POST(request) {
  const corpo = await request.json().catch(() => null);
  const nome = typeof corpo?.nome === "string" ? corpo.nome.trim() : "";
  const email = typeof corpo?.email === "string" ? corpo.email.trim().toLowerCase() : "";
  const senha = typeof corpo?.senha === "string" ? corpo.senha : "";

  if (nome.length < 2 || nome.length > 120) {
    return Response.json(
      { message: "Informe um nome entre 2 e 120 caracteres." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) {
    return Response.json(
      { message: "Confira se o e-mail foi digitado corretamente." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (senha.length < 8 || senha.length > 128) {
    return Response.json(
      { message: "Escolha uma senha entre 8 e 128 caracteres." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const resultado = await criarPaciente({ nome, email, senha });
    if (!resultado.ok) {
      return Response.json(
        { message: "Este e-mail já está cadastrado. Tente entrar com ele." },
        { status: 409, headers: { "Cache-Control": "no-store" } },
      );
    }

    return Response.json(
      { message: "Cadastro criado. Agora você já pode entrar com seus dados." },
      { status: 201, headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return Response.json(
      { message: "Não foi possível criar seu acesso agora." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
