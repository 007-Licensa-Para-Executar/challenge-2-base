import { NextResponse } from "next/server";
import { encerrarSessao } from "../_backend";

export async function POST(request) {
  const { cookie } = encerrarSessao(request);
  return NextResponse.json(
    { ok: true, message: "Sessão encerrada com segurança." },
    { status: 200, headers: { "Set-Cookie": cookie, "Cache-Control": "no-store" } },
  );
}
