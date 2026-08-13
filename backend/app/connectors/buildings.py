"""BuildingProvider -- source REELLE (IGN BD TOPO batiments), voir
docs/DATA_SOURCES.md section A.1 (corrige le 2026-08-13).

Statut : PRINCIPAL, verifie par un appel reseau reel. L'ancien chemin Etalab
(cadastre.data.gouv.fr/.../{insee}-batiments.json.gz) renvoyait systematiquement
404 en production et neutralisait score_surface + score_densification (a 50/100,
DONNEES_INSUFFISANTES) pour TOUTES les parcelles de TOUTES les communes -- voir
incident du 2026-08-13. Remplace par le flux WFS BD TOPO V3 de la Geoplateforme
IGN, teste avec un vrai appel reseau depuis cet environnement (reponse GeoJSON
confirmee : proprietes "nombre_d_etages", "hauteur", "nombre_de_logements",
"usage_1", etc. -- exactement ce qu'il faut pour estimer le bati existant).

Endpoint :
GET https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
    &TYPENAME=BDTOPO_V3:batiment&SRSNAME=EPSG:4326
    &BBOX={minLon},{minLat},{maxLon},{maxLat},EPSG:4326
    &outputFormat=application/json&COUNT=1000&STARTINDEX={n}

Ce flux ne permet pas de filtrer par code INSEE directement : la requete se fait
par bbox (rectangle englobant de la geometrie communale, deja recuperee via le
connecteur cadastre en amont -- voir app/services/analysis_job.py). La bbox etant
rectangulaire, des batiments de communes voisines peuvent etre inclus dans la
reponse ; c'est sans consequence car app/services/analysis_job.py ne rattache un
batiment a une parcelle que par intersection geometrique reelle (STRtree), jamais
par simple appartenance a la reponse.

Pagination geree via STARTINDEX/COUNT (le flux limite le nombre d'entites par
reponse) avec un plafond de securite pour ne jamais boucler indefiniment.
"""
from __future__ import annotations

import logging

from shapely.geometry import shape

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry

logger = logging.getLogger("radar_foncier.connectors.buildings")

BASE_URL = "https://data.geopf.fr/wfs/ows"
PAGE_SIZE = 1000
MAX_PAGES = 30  # plafond de securite (jusqu'a 30000 batiments par commune)


class BuildingProvider:
    name = "BuildingProvider"

    def fetch(self, **params) -> ProviderResult:
        code_insee: str = params["code_insee"]
        commune_geometry: dict | None = params.get("commune_geometry")
        return self.fetch_by_commune_geometry(code_insee, commune_geometry)

    def fetch_by_commune_geometry(self, code_insee: str, commune_geometry: dict | None) -> ProviderResult:
        source = SourceRecord(
            source_name="IGN BD TOPO V3 (Geoplateforme WFS) - batiment",
            source_url=BASE_URL,
            reliability="OFFICIAL",
        )
        if not commune_geometry:
            return empty_result(
                source.source_name,
                source.source_url,
                f"Bati non recupere pour {code_insee} : geometrie communale indisponible "
                "(echec prealable du connecteur cadastre) -- impossible de construire la bbox.",
            )
        try:
            minx, miny, maxx, maxy = shape(commune_geometry).bounds
        except Exception as exc:  # noqa: BLE001
            return empty_result(
                source.source_name, source.source_url, f"Bati non recupere pour {code_insee} (bbox invalide) : {exc}"
            )

        bbox = f"{minx},{miny},{maxx},{maxy},EPSG:4326"
        all_features: list[dict] = []
        warnings: list[str] = []
        try:
            with get_http_client() as client:
                start_index = 0
                total_matched: int | None = None
                for _ in range(MAX_PAGES):
                    response = request_with_retry(
                        client,
                        "GET",
                        BASE_URL,
                        params={
                            "SERVICE": "WFS",
                            "VERSION": "2.0.0",
                            "REQUEST": "GetFeature",
                            "TYPENAME": "BDTOPO_V3:batiment",
                            "SRSNAME": "EPSG:4326",
                            "BBOX": bbox,
                            "outputFormat": "application/json",
                            "COUNT": PAGE_SIZE,
                            "STARTINDEX": start_index,
                        },
                    )
                    geojson = response.json()
                    features = geojson.get("features", [])
                    all_features.extend(features)
                    total_matched = geojson.get("totalFeatures") or geojson.get("numberMatched")
                    if len(features) < PAGE_SIZE:
                        break
                    start_index += PAGE_SIZE
                    if total_matched is not None and start_index >= total_matched:
                        break
            if not all_features:
                warnings.append(f"Aucun batiment BD TOPO trouve pour {code_insee} (bbox commune).")
            return ProviderResult(data=all_features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001 -- defensif par conception, ne bloque jamais le job
            logger.warning("BuildingProvider: bati non recupere pour %s : %s", code_insee, exc)
            return empty_result(
                source.source_name, source.source_url, f"Bati non recupere pour {code_insee} : {exc}"
            )
