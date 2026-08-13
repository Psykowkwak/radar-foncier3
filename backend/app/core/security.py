"""Protection de l'API par cle partagee.

Contexte : l'application est destinee a un usage strictement personnel (voir
docs/ROADMAP.md, docs/ARCHITECTURE.md). Une fois deployee sur internet (Render),
l'API ne doit repondre qu'aux requetes provenant du frontend (lui-meme protege
par Basic Auth cote Next.js -- voir frontend/middleware.ts et
frontend/app/api/backend/[...path]/route.ts).

Principe : le frontend Next.js (cote serveur uniquement, jamais expose au
navigateur) connait `INTERNAL_API_KEY` et l'ajoute a chaque requete proxyee vers
le backend via l'en-tete `X-Internal-Key`. Le backend refuse toute requete sans
cette cle des que `settings.internal_api_key` est definie. En local (dev, cle
absente), l'API reste ouverte pour ne pas compliquer le developpement.
"""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

# Chemins toujours accessibles sans cle (necessaires a Render pour les health checks,
# et a la doc OpenAPI qui ne fuite aucune donnee en elle-meme).
PUBLIC_PATHS = {"/health", "/", "/openapi.json", "/docs", "/redoc"}


class InternalKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.internal_api_key:
            # Pas de cle configuree (dev local) -> API ouverte.
            return await call_next(request)
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        provided = request.headers.get("x-internal-key")
        if provided != settings.internal_api_key:
            return JSONResponse(status_code=401, content={"detail": "Non autorise."})
        return await call_next(request)
