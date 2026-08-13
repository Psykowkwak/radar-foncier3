"""UrbanismProvider -- source REELLE (zonage seul), voir docs/DATA_SOURCES.md section B.1.

Statut : PRINCIPAL pour le zonage. Le texte reglementaire (nomfic/urlfic, PDF) n'est
PAS traite ici -- hors MVP, prevu V1 avec la couche IA d'extraction (voir
docs/URBANISM_ENGINE.md).

Endpoint utilise :
GET https://apicarto.ign.fr/api/gpu/zone-urba?partition=DU_{code_insee}
(alternative documentee : filtrage par geometrie GeoJSON via le parametre `geom`,
en GET ou POST -- utilise ici en secondaire si le mode partition ne suffit pas).

Attributs cles recuperes : libelle (ex "Uc"), libelong, typezone, insee.

AVERTISSEMENT OFFICIEL (repris de docs/DATA_SOURCES.md) : la couverture de cette API
est incomplete. L'absence de resultat NE SIGNIFIE PAS l'absence de document
d'urbanisme -- ne jamais interpreter un resultat vide comme "hors PLU"/"non
reglemente". Le service appelant (analysis_job / urbanism_classification) doit
traiter une reponse vide comme DONNEES_INSUFFISANTES, jamais comme "non
constructible" ni "constructible".

A verifier avant usage intensif : stabilite du parametre `partition`, limite de
volume par reponse (non documentee explicitement pour ce endpoint).
"""
from __future__ import annotations

import logging
from typing import Any

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry

logger = logging.getLogger("radar_foncier.connectors.urbanism")

BASE_URL = "https://apicarto.ign.fr/api/gpu/zone-urba"


class UrbanismProvider:
    name = "UrbanismProvider"

    def fetch(self, **params: Any) -> ProviderResult:
        """params attendus : code_insee=str (mode partition, par defaut)
        ou geometry=dict (GeoJSON geometry, mode geom)."""
        if "geometry" in params:
            return self.fetch_by_geometry(params["geometry"])
        return self.fetch_by_partition(params["code_insee"])

    def fetch_by_partition(self, code_insee: str) -> ProviderResult:
        partition = f"DU_{code_insee}"
        source = SourceRecord(
            source_name="IGN API Carto GPU - zone-urba (partition)",
            source_url=f"{BASE_URL}?partition={partition}",
            reliability="OFFICIAL",
        )
        try:
            with get_http_client() as client:
                response = request_with_retry(client, "GET", BASE_URL, params={"partition": partition})
                geojson = response.json()
            features = geojson.get("features", [])
            warnings: list[str] = []
            if not features:
                warnings.append(
                    "Aucune zone de document d'urbanisme trouvee (GPU) pour "
                    f"{code_insee} -- NE PAS interpreter comme 'hors PLU', l'API GPU a "
                    "une couverture incomplete (avertissement officiel)."
                )
            return ProviderResult(data=features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Echec UrbanismProvider.fetch_by_partition(%s)", code_insee)
            return empty_result(
                source.source_name,
                source.source_url,
                f"Zonage GPU non recupere pour {code_insee} : {exc}",
            )

    def fetch_by_geometry(self, geometry: dict) -> ProviderResult:
        """Filtrage par geometrie GeoJSON (utilise en POST, la geometrie pouvant etre
        volumineuse pour tenir dans une query string GET)."""
        source = SourceRecord(
            source_name="IGN API Carto GPU - zone-urba (geom)",
            source_url=BASE_URL,
            reliability="OFFICIAL",
        )
        try:
            with get_http_client() as client:
                response = request_with_retry(client, "POST", BASE_URL, json={"geom": geometry})
                geojson = response.json()
            features = geojson.get("features", [])
            warnings: list[str] = []
            if not features:
                warnings.append(
                    "Aucune zone GPU trouvee pour cette geometrie -- couverture GPU incomplete, "
                    "ne pas interpreter comme 'non reglemente'."
                )
            return ProviderResult(data=features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Echec UrbanismProvider.fetch_by_geometry")
            return empty_result(
                source.source_name, source.source_url, f"Zonage GPU non recupere (geom) : {exc}"
            )
