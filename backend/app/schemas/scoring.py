"""Schemas Pydantic -- ParcelScore."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class ParcelScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    score_urbanisme: float
    score_geometrie: float
    score_surface: float
    score_acces: float
    score_reseaux: float
    score_risques: float
    score_densification: float
    score_complexite: float
    score_qualite_donnees: float
    score_global: float
    explanation_text: str | None
