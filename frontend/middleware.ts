import { NextRequest, NextResponse } from "next/server";

/**
 * Protection Basic Auth de l'ensemble du site (usage personnel -- voir
 * docs/ROADMAP.md). Actif uniquement si BASIC_AUTH_USER et BASIC_AUTH_PASSWORD
 * sont definies (en local/dev, si absentes, le site reste ouvert pour ne pas
 * gener le developpement).
 *
 * Le proxy `/api/backend/*` (voir app/api/backend/[...path]/route.ts) est
 * couvert par ce middleware comme le reste du site : un navigateur non
 * authentifie ne peut donc jamais atteindre le backend, meme indirectement.
 */
export function middleware(request: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const password = process.env.BASIC_AUTH_PASSWORD;

  if (!user || !password) {
    return NextResponse.next();
  }

  const authHeader = request.headers.get("authorization");

  if (authHeader) {
    const [scheme, encoded] = authHeader.split(" ");
    if (scheme === "Basic" && encoded) {
      const decoded = Buffer.from(encoded, "base64").toString("utf-8");
      const separatorIndex = decoded.indexOf(":");
      const providedUser = decoded.slice(0, separatorIndex);
      const providedPassword = decoded.slice(separatorIndex + 1);
      if (providedUser === user && providedPassword === password) {
        return NextResponse.next();
      }
    }
  }

  return new NextResponse("Authentification requise.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Radar Foncier"' },
  });
}

export const config = {
  // Applique a tout sauf les assets statiques Next internes.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
