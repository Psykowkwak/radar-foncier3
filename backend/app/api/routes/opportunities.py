"""Route : liste des opportunites (parcelles scorees) d'une commune, triee par score.

GET /api/municipalities/{insee}/opportunities?min_score=&min_area=&max_area=&operation_type=&vacant_only=
"""
from __future__ import annotations

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.analysis import ParcelAnalysis
from app.models.economics import ParcelFeasibility
from app.models.enums import BuiltCategoryEnum
from app.models.municipality import Municipality
from app.models.parcel import Parcel
from app.models.scoring import ParcelScore
from app.schemas.parcel import OpportunityItem
from app.services.geometry import reproject_to_wgs84

router = APIRouter(tags=["opportunities"])


def _to_item(parcel: Parcel, analysis: ParcelAnalysis, score: ParcelScore, feasibility: ParcelFeasibility | None) -> OpportunityItem:
    geom_wgs84 = reproject_to_wgs84(to_shape(parcel.geometry))
    return OpportunityItem(
        parcel_id=parcel.id,
        reference=parcel.reference,
        geometry=mapping(geom_wgs84),
        parcel_area=analysis.parcel_area,
        score_global=score.score_global,
        built_category=analysis.built_category.value if analysis.built_category else None,
        constructibility_status=analysis.constructibility_status.value,
        estimated_margin=feasibility.estimated_margin if feasibility else None,
        margin_ratio=feasibility.margin_ratio if feasibility else None,
        feasibility_computable=bool(feasibility.computable) if feasibility else False,
        feasibility_explanation=feasibility.explanation_text if feasibility else None,
    )


@router.get("/api/municipalities/{insee}/opportunities", response_model=list[OpportunityItem])
def list_opportunities(
    insee: str,
    min_score: float | None = Query(default=None, ge=0, le=100),
    min_area: float | None = Query(default=None, ge=0),
    max_area: float | None = Query(default=None, ge=0),
    operation_type: str | None = Query(default=None),
    vacant_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[OpportunityItem]:
    municipality = db.execute(select(Municipality).where(Municipality.insee_code == insee)).scalar_one_or_none()
    if municipality is None:
        raise HTTPException(status_code=404, detail="Commune non trouvee -- lancez une analyse d'abord.")

    # Derniere analyse par parcelle (ParcelAnalysis n'est jamais ecrasee, voir DATA_MODEL.md)
    latest_subq = (
        select(ParcelAnalysis.parcel_id, func.max(ParcelAnalysis.computed_at).label("max_computed_at"))
        .group_by(ParcelAnalysis.parcel_id)
        .subquery()
    )

    stmt = (
        select(Parcel, ParcelAnalysis, ParcelScore, ParcelFeasibility)
        .join(ParcelAnalysis, ParcelAnalysis.parcel_id == Parcel.id)
        .join(
            latest_subq,
            (ParcelAnalysis.parcel_id == latest_subq.c.parcel_id)
            & (ParcelAnalysis.computed_at == latest_subq.c.max_computed_at),
        )
        .join(ParcelScore, ParcelScore.analysis_id == ParcelAnalysis.id)
        .outerjoin(ParcelFeasibility, ParcelFeasibility.analysis_id == ParcelAnalysis.id)
        .where(Parcel.municipality_id == municipality.id)
    )

    if min_score is not None:
        stmt = stmt.where(ParcelScore.score_global >= min_score)
    if min_area is not None:
        stmt = stmt.where(ParcelAnalysis.parcel_area >= min_area)
    if max_area is not None:
        stmt = stmt.where(ParcelAnalysis.parcel_area <= max_area)
    if vacant_only:
        stmt = stmt.where(ParcelAnalysis.built_category == BuiltCategoryEnum.VACANT_LAND)
    if operation_type is not None:
        # suggested_operations n'est pas encore alimente au MVP (voir docs/ROADMAP.md) --
        # ce filtre est accepte pour compatibilite API mais ne peut rien retourner tant
        # que ce champ n'est pas peuple (documente explicitement, pas simule).
        stmt = stmt.where(ParcelAnalysis.suggested_operations.contains([operation_type]))

    stmt = stmt.order_by(ParcelScore.score_global.desc())

    rows = db.execute(stmt).all()
    return [_to_item(parcel, analysis, score, feasibility) for parcel, analysis, score, feasibility in rows]


@router.get("/api/municipalities/{insee}/top-opportunities", response_model=list[OpportunityItem])
def list_top_opportunities(
    insee: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[OpportunityItem]:
    """Classement par marge apparente estimee (bilan promoteur simplifie, voir
    app/services/feasibility.py), pas par score d'urbanisme -- repond au besoin
    "les N parcelles les plus prometteuses en tenant compte du bati existant et de
    la rentabilite reelle, pas juste de la constructibilite". Ne renvoie que les
    parcelles ou l'estimation a pu etre calculee (donnees bati IGN + prix DVF
    reels disponibles) -- jamais une marge inventee pour completer la liste."""
    municipality = db.execute(select(Municipality).where(Municipality.insee_code == insee)).scalar_one_or_none()
    if municipality is None:
        raise HTTPException(status_code=404, detail="Commune non trouvee -- lancez une analyse d'abord.")

    latest_subq = (
        select(ParcelAnalysis.parcel_id, func.max(ParcelAnalysis.computed_at).label("max_computed_at"))
        .group_by(ParcelAnalysis.parcel_id)
        .subquery()
    )

    stmt = (
        select(Parcel, ParcelAnalysis, ParcelScore, ParcelFeasibility)
        .join(ParcelAnalysis, ParcelAnalysis.parcel_id == Parcel.id)
        .join(
            latest_subq,
            (ParcelAnalysis.parcel_id == latest_subq.c.parcel_id)
            & (ParcelAnalysis.computed_at == latest_subq.c.max_computed_at),
        )
        .join(ParcelScore, ParcelScore.analysis_id == ParcelAnalysis.id)
        .join(ParcelFeasibility, ParcelFeasibility.analysis_id == ParcelAnalysis.id)
        .where(Parcel.municipality_id == municipality.id)
        .where(ParcelFeasibility.computable.is_(True))
        .order_by(ParcelFeasibility.estimated_margin.desc())
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    return [_to_item(parcel, analysis, score, feasibility) for parcel, analysis, score, feasibility in rows]
