"""Schemas Pydantic -- Parcel, ParcelAnalysis, ParcelDetail, Opportunity."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.scoring import ParcelScoreRead


class ParcelGeoFeature(BaseModel):
    """Une parcelle representee comme feature GeoJSON (geometrie en WGS84 pour
    l'affichage carte), avec le score global attache pour la coloration."""

    id: uuid.UUID
    reference: str | None
    geometry: dict[str, Any]
    score_global: float | None = None
    excluded: bool = False


class ParcelAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parcel_area: float | None
    building_footprint_area: float | None
    building_coverage_ratio: float | None
    unbuilt_area: float | None
    largest_contiguous_unbuilt_area: float | None
    width_estimated: float | None
    depth_estimated: float | None
    road_frontage_length: float | None
    geometry_quality_score: float | None
    built_category: str | None
    constructibility_status: str
    urbanism_confidence_score: float | None
    suggested_operations: list | None


class ParcelDetail(BaseModel):
    """Fiche parcelle complete : identite/urbanisme/terrain/bati/risques/score/sources."""

    id: uuid.UUID
    municipality_id: uuid.UUID
    municipality_name: str
    section: str | None
    numero: str | None
    reference: str | None
    geometry: dict[str, Any]
    area_official: float | None
    area_computed: float | None
    typezone: str | None
    zone_libelle: str | None
    analysis: ParcelAnalysisRead | None
    score: ParcelScoreRead | None
    sources: list[str]
    warnings: list[str]


class OpportunityItem(BaseModel):
    parcel_id: uuid.UUID
    reference: str | None
    geometry: dict[str, Any]
    parcel_area: float | None
    score_global: float
    built_category: str | None
    constructibility_status: str
    # Bilan promoteur simplifie (voir app/services/feasibility.py) -- None tant que
    # non calculable (donnees insuffisantes), jamais une valeur inventee.
    estimated_margin: float | None = None
    margin_ratio: float | None = None
    feasibility_computable: bool = False
    feasibility_explanation: str | None = None
