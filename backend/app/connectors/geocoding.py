"""GeocodingProvider -- source REELLE, voir docs/DATA_SOURCES.md section C.1.

Statut : implemente. Utilise le geocodage Geoplateforme (BAN), remplacant confirme
de api-adresse.data.gouv.fr (deprecie).

Endpoint : GET https://data.geopf.fr/geocodage/search?q={query}&type=municipality
Limite documentee : 50 req/s/IP.
"""
from __future__ import annotations

import logging
from typing import Any

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry

logger = logging.getLogger("radar_foncier.connectors.geocoding")

BASE_URL = "https://data.geopf.fr/geocodage/search"


class GeocodingProvider:
    name = "GeocodingProvider"

    def fetch(self, **params: Any) -> ProviderResult:
        query = params["q"]
        return self.search_municipality(query)

    def search_municipality(self, query: str, limit: int = 10) -> ProviderResult:
        source = SourceRecord(
            source_name="Geoplateforme geocodage (BAN)",
            source_url=f"{BASE_URL}?q={query}&type=municipality",
            reliability="OFFICIAL",
        )
        try:
            with get_http_client() as client:
                response = request_with_retry(
                    client, "GET", BASE_URL, params={"q": query, "type": "municipality", "limit": limit}
                )
                geojson = response.json()
            features = geojson.get("features", [])
            warnings: list[str] = []
            if not features:
                warnings.append(f"Aucune commune trouvee pour la recherche '{query}'.")
            return ProviderResult(data=features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Echec GeocodingProvider.search_municipality(%s)", query)
            return empty_result(
                source.source_name, source.source_url, f"Recherche commune '{query}' echouee : {exc}"
            )
