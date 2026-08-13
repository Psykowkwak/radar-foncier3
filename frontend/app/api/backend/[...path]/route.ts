import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy server-side vers le backend FastAPI. Le navigateur n'appelle jamais le
 * backend directement (voir lib/api.ts, qui appelle uniquement `/api/backend/*`
 * en meme origine) -- ce proxy est le seul endroit ou `BACKEND_URL` et
 * `INTERNAL_API_KEY` sont lus, tous deux des variables d'environnement
 * server-only (pas de prefixe NEXT_PUBLIC_, donc jamais envoyees au client).
 *
 * Ce fichier est aussi couvert par middleware.ts (Basic Auth) : un appel direct
 * a `/api/backend/...` sans etre authentifie sur le site est deja bloque avant
 * meme d'arriver ici.
 */

// IMPORTANT : sans ceci, Next.js App Router met en cache par defaut les reponses
// GET des route handlers (Full Route Cache). Une premiere requete lancee juste
// apres la fin d'une analyse (avant que le job precedent n'ait fini d'ecrire ses
// resultats) pouvait donc rester "figee" en cache et etre reservie a l'identique
// indefiniment, meme apres que les vraies donnees existent en base -- symptome
// observe : "opportunites (0)" qui ne se met jamais a jour. `force-dynamic`
// desactive tout cache sur cette route, chaque requete est reexecutee.
export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || "";

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  // `path` reprend deja le prefixe "api" (lib/api.ts appelle
  // "/api/backend" + "/api/municipalities/..." -> path = ["api","municipalities",...]),
  // donc pas de prefixe supplementaire ici.
  const targetUrl = new URL(`/${path.join("/")}`, BACKEND_URL);
  targetUrl.search = request.nextUrl.search;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const body = hasBody ? await request.text() : undefined;

  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers,
    body: body || undefined,
    cache: "no-store",
  });

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") || "application/json" },
  });
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}
