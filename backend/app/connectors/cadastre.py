"""CadastreProvider -- source REELLE, voir docs/DATA_SOURCES.md section A.2.

Statut : PRINCIPAL. Implemente et appelle en direct l'API Carto IGN (module cadastre),
sans authentification.

Endpoints utilises (verifies dans docs/DATA_SOURCES.md) :
- Communes  : GET https://apicarto.ign.fr/api/cadastre/commune?code_insee={insee}
- Parcelles : GET https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={insee}
              pagination _limit/_start, max 1000 objets/reponse (500 pour /commune)

Format retourne : GeoJSON en WGS84 (EPSG:4326). La reprojection vers Lambert-93
(EPSG:2154) pour les calculs est faite en aval, dans app/services/geometry.py --
ce connecteur ne fait AUCUN calcul geometrique, uniquement la collecte + pagination.

A verifier avant usage intensif : le comportement exact de l'API sous forte charge
(pas de garantie de SLA documentee), et la stabilite du schema d'attributs GeoJSON
(section/numero/contenance) qui n'a ete observe qu'a travers l'exemple officiel.
"""
from __future__ import annotations

import logging
from typing import Any

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry

logger = logging.getLogger("radar_foncier.connectors.cadastre")

BASE_URL = "https://apicarto.ign.fr/api/cadastre"
PARCELLE_PAGE_LIMIT = 1000
COMMUNE_PAGE_LIMIT = 500


class CadastreProvider:
    name = "CadastreProvider"

    def fetch(self, **params: Any) -> ProviderResult:
        """Point d'entree generique du Protocol DataProvider.

        params attendus : kind="commune"|"parcelles", code_insee=str
        """
        kind = params.get("kind", "parcelles")
        code_insee = params["code_insee"]
        if kind == "commune":
            return self.fetch_commune(code_insee)
        return self.fetch_parcelles(code_insee)

    def fetch_commune(self, code_insee: str) -> ProviderResult:
        url = f"{BASE_URL}/commune"
        source = SourceRecord(
            source_name="IGN API Carto Cadastre - commune",
            source_url=f"{url}?code_insee={code_insee}",
            reliability="OFFICIAL",
        )
        try:
            with get_http_client() as client:
                response = request_with_retry(
                    client, "GET", url, params={"code_insee": code_insee, "_limit": COMMUNE_PAGE_LIMIT}
                )
                geojson = response.json()
            features = geojson.get("features", [])
            warnings: list[str] = []
            if not features:
                warnings.append(f"Aucune commune trouvee pour le code INSEE {code_insee}.")
            return ProviderResult(data=features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001 -- connecteur jamais bloquant, voir docs/ARCHITECTURE.md §4
            logger.exception("Echec CadastreProvider.fetch_commune(%s)", code_insee)
            return empty_result(
                source.source_name,
                source.source_url,
                f"Commune non recuperee (API Carto Cadastre) pour {code_insee} : {exc}",
            )

    def fetch_parcelles(self, code_insee: str) -> ProviderResult:
        """Recupere toutes les parcelles d'une commune, en paginant _limit/_start."""
        url = f"{BASE_URL}/parcelle"
        source = SourceRecord(
            source_name="IGN API Carto Cadastre - parcelle",
            source_url=f"{url}?code_insee={code_insee}",
            reliability="OFFICIAL",
        )
        all_features: list[dict] = []
        warnings: list[str] = []
        start = 0
        try:
            with get_http_client() as client:
                while True:
                    response = request_with_retry(
                        client,
                        "GET",
                        url,
                        params={"code_insee": code_insee, "_limit": PARCELLE_PAGE_LIMIT, "_start": start},
                    )
                    geojson = response.json()
                    features = geojson.get("features", [])
                    all_features.extend(features)
                    if len(features) < PARCELLE_PAGE_LIMIT:
                        break
                    start += PARCELLE_PAGE_LIMIT
                    if start > 200_000:  # garde-fou anti boucle infinie
                        warnings.append("Pagination interrompue (limite de securite 200000 atteinte).")
                        break
            if not all_features:
                warnings.append(f"Aucune parcelle trouvee pour le code INSEE {code_insee}.")
            return ProviderResult(data=all_features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Echec CadastreProvider.fetch_parcelles(%s)", code_insee)
            return empty_result(
                source.source_name,
                source.source_url,
                f"Parcelles non recuperees (API Carto Cadastre) pour {code_insee} : {exc}",
            )
