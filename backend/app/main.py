"""Point d'entree FastAPI -- voir docs/ARCHITECTURE.md §2."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, municipalities, opportunities, parcels
from app.core.config import get_settings
from app.core.security import InternalKeyMiddleware

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="Radar Foncier Intelligent - API",
    description="Analyse de parcelles cadastrales francaises (MVP). Voir docs/ pour le cahier des charges.",
    version="0.1.0",
)

# Protection par cle partagee (voir app/core/security.py) -- active seulement si
# INTERNAL_API_KEY est definie (production/Render). Doit etre ajoutee avant CORS
# pour rejeter les requetes non autorisees le plus tot possible.
app.add_middleware(InternalKeyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(municipalities.router)
app.include_router(analysis.router)
app.include_router(opportunities.router)
app.include_router(parcels.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
