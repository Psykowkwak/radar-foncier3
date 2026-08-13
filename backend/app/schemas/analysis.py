"""Schemas Pydantic -- AnalysisJob."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    municipality_id: uuid.UUID
    status: str
    progress_pct: int
    current_step: str | None
    started_at: datetime | None
    finished_at: datetime | None
    parcels_total: int | None
    parcels_selected: int | None
    parcels_excluded: int | None
    exclusion_reasons: dict | None
    error_log: dict | None


class AnalysisJobLaunched(BaseModel):
    job_id: uuid.UUID
    municipality_id: uuid.UUID
    status: str
