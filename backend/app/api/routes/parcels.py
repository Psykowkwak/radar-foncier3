"""Route : fiche parcelle complete.

GET /api/parcels/{parcel_id} -> identite, urbanisme, geometrie, bati, risques,
score detaille, sources.
"""
from __future__ import annotations

import uuid

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.analysis import AnalysisWarning, ParcelAnalysis
from app.models.municipality import Municipality
from app.models.parcel import Parcel
from app.models.scoring import ParcelScore
from app.models.source import SourceRecord
from app.models.urbanism import UrbanismZone
from app.schemas.parcel import ParcelAnalysisRead, ParcelDetail
from app.schemas.scoring import ParcelScoreRead
from app.services.geometry import reproject_to_wgs84

router = APIRouter(prefix="/api/parcels", tags=["parcels"])


@router.get("/{parcel_id}", response_model=ParcelDetail)
def get_parcel(parcel_id: uuid.UUID, db: Session = Depends(get_db)) -> ParcelDetail:
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcelle non trouvee")

    municipality = db.get(Municipality, parcel.municipality_id)

    analysis = db.execute(
        select(ParcelAnalysis)
        .where(ParcelAnalysis.parcel_id == parcel.id)
        .order_by(ParcelAnalysis.computed_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    score = None
    if analysis is not None:
        score = db.execute(select(ParcelScore).where(ParcelScore.analysis_id == analysis.id)).scalar_one_or_none()

    # Zone majoritaire recalculee a la demande (non persistee par parcelle au MVP,
    # voir docs/URBANISM_ENGINE.md -- une parcelle peut chevaucher plusieurs zones).
    typezone, zone_libelle = _majority_zone_for_parcel(db, parcel)

    warnings: list[str] = []
    warning_rows = db.execute(
        select(AnalysisWarning).where(AnalysisWarning.parcel_id == parcel.id)
    ).scalars().all()
    warnings.extend(w.message for w in warning_rows)
    if analysis is not None and analysis.job_id is not None:
        job_warning_rows = db.execute(
            select(AnalysisWarning).where(AnalysisWarning.job_id == analysis.job_id)
        ).scalars().all()
        warnings.extend(w.message for w in job_warning_rows)
    warnings = sorted(set(warnings))

    sources: list[str] = []
    if parcel.source_id is not None:
        src = db.get(SourceRecord, parcel.source_id)
        if src:
            sources.append(src.source_name)
    sources = sorted(set(sources))

    geom_wgs84 = reproject_to_wgs84(to_shape(parcel.geometry))

    return ParcelDetail(
        id=parcel.id,
        municipality_id=parcel.municipality_id,
        municipality_name=municipality.name if municipality else "",
        section=parcel.section,
        numero=parcel.numero,
        reference=parcel.reference,
        geometry=mapping(geom_wgs84),
        area_official=parcel.area_official,
        area_computed=parcel.area_computed,
        typezone=typezone,
        zone_libelle=zone_libelle,
        analysis=ParcelAnalysisRead.model_validate(analysis) if analysis else None,
        score=ParcelScoreRead.model_validate(score) if score else None,
        sources=sources,
        warnings=warnings,
    )


def _majority_zone_for_parcel(db: Session, parcel: Parcel) -> tuple[str | None, str | None]:
    zones = db.execute(
        select(UrbanismZone).where(UrbanismZone.municipality_id == parcel.municipality_id)
    ).scalars().all()
    if not zones:
        return None, None
    parcel_geom = to_shape(parcel.geometry)
    best_zone = None
    best_area = 0.0
    for zone in zones:
        zone_geom = to_shape(zone.geometry)
        try:
            inter_area = parcel_geom.intersection(zone_geom).area
        except Exception:  # noqa: BLE001
            continue
        if inter_area > best_area:
            best_area = inter_area
            best_zone = zone
    if best_zone is None:
        return None, None
    return best_zone.typezone, best_zone.libelle
