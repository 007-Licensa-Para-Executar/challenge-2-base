import { NextResponse } from "next/server";
import { literatureHttpResult, literatureRequest, runLiteratureSearch } from "../../../lib/literatureBridge.js";

export const runtime = "nodejs";

export async function POST(request) {
  const payload = await request.json().catch(() => null);
  const blocked = literatureRequest(payload);
  if (blocked) {
    return NextResponse.json(blocked.body, {
      status: blocked.status,
      headers: { "Cache-Control": "no-store" },
    });
  }

  try {
    const result = await runLiteratureSearch({
      query: payload.query,
      top_k: payload.top_k ?? 5,
    });
    const httpResult = literatureHttpResult(result);
    return NextResponse.json(httpResult.body, {
      status: httpResult.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    console.error("Falha na consulta científica.");
    return NextResponse.json(
      { message: "Falha ao consultar a literatura." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
