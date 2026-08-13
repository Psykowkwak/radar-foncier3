"""Schemas Pydantic -- Municipality."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MunicipalitySearchResult(BaseModel):
    insee_code: str
    name: str
    postcode: str | None = None
    centroid_lon: float | None = None
    centroid_lat: float | None = None


class MunicipalityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    insee_code: str
    name: str
    department_code: str | None
    region_code: str | None
    population: int | None
    last_analyzed_at: datetime | None
