"""Routes : recherche/lecture commune -- voir docs/ARCHITECTURE.md, cahier des charges §.

GET /api/municipalities/search?q=   autocomplete via Geoplateforme geocodage
GET /api/municipalities/{insee}     lecture (cree la commune en base si absente)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.geocoding import GeocodingProvider
from app.core.db import get_db
from app.models.municipality import Municipality
from app.schemas.municipality import MunicipalityRead, MunicipalitySearchResult

router = APIRouter(prefix="/api/municipalities", tags=["municipalities"])


@router.get("/search", response_model=list[MunicipalitySearchResult])
def search_municipalities(q: str = Query(min_length=1)) -> list[MunicipalitySearchResult]:
    provider = GeocodingProvider()
    result = provider.search_municipality(q)
    results: list[MunicipalitySearchResult] = []
    for feature in result.data or []:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        results.append(
            MunicipalitySearchResult(
                insee_code=props.get("citycode") or props.get("insee") or "",
                name=props.get("city") or props.get("label") or "",
                postcode=props.get("postcode"),
                centroid_lon=coords[0] if len(coords) > 0 else None,
                centroid_lat=coords[1] if len(coords) > 1 else None,
            )
        )
    return results


@router.get("/{insee}", response_model=MunicipalityRead)
def get_municipality(insee: str, db: Session = Depends(get_db)) -> Municipality:
    municipality = db.execute(select(Municipality).where(Municipality.insee_code == insee)).scalar_one_or_none()
    if municipality is None:
        raise HTTPException(status_code=404, detail="Commune non trouvee en base -- lancez une analyse d'abord.")
    return municipality
