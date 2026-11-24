import { getPsychologistProfilePhoto } from "../../../auth/_database";

export const runtime = "nodejs";

export async function GET() {
  if (process.env.NODE_ENV === "production") {
    return Response.json(
      { message: "A foto do perfil requer autenticação profissional." },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const photo = getPsychologistProfilePhoto();
    if (!photo) {
      return new Response(null, { status: 404, headers: { "Cache-Control": "no-store" } });
    }

    return new Response(photo.data, {
      headers: {
        "Content-Type": photo.mimeType,
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    console.error("Falha ao carregar foto da psicóloga:", error);
    return Response.json(
      { message: "Não foi possível carregar a foto da psicóloga." },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
