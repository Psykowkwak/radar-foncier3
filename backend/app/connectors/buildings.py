"""BuildingProvider -- source DEFENSIVE (Etalab cadastre.data.gouv.fr), voir
docs/DATA_SOURCES.md section A.1.

Statut : experimental / defensif. DATA_SOURCES.md documente le pattern verifie comme
etant une archive par commune :
    https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/{dep}/{code_insee}.json
avec des couches (dont "batiments") a l'interieur. Le cahier des charges MVP demande
en complement d'essayer un chemin par-couche direct :
    https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/{dep}/{code_insee}/{code_insee}-batiments.json.gz
Ce module essaie ce second chemin (fichier par couche, plus economique s'il existe
reellement) ; SI CE CHEMIN RENVOIE 404 (ou toute autre erreur), le connecteur ne
bloque JAMAIS le job -- il retourne un ProviderResult vide avec le warning explicite
"batiment non recupere". Le format exact observe en conditions reelles n'a PAS ete
teste avec un vrai appel reseau depuis cet environnement (pas d'acces reseau sortant
verifie en sandbox) : a confirmer avant mise en production, en documentant ici le
resultat une fois teste.

A verifier avant usage intensif :
- le chemin exact (fichier par couche vs archive complete par commune)
- le format de compression (.gz vs .json brut)
- la structure du GeoJSON de la couche batiments (proprietes disponibles)
"""
from __future__ import annotations

import gzip
import io
import json
import logging

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry
from app.services.insee_utils import department_from_insee

logger = logging.getLogger("radar_foncier.connectors.buildings")

BASE_URL = "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes"


class BuildingProvider:
    name = "BuildingProvider"

    def fetch(self, **params) -> ProviderResult:
        code_insee: str = params["code_insee"]
        dep = params.get("dep") or department_from_insee(code_insee)
        return self.fetch_batiments(code_insee, dep)

    def fetch_batiments(self, code_insee: str, dep: str) -> ProviderResult:
        url = f"{BASE_URL}/{dep}/{code_insee}/{code_insee}-batiments.json.gz"
        source = SourceRecord(
            source_name="Etalab cadastre.data.gouv.fr - batiments",
            source_url=url,
            reliability="OFFICIAL",
        )
        try:
            with get_http_client() as client:
                response = request_with_retry(client, "GET", url)
                raw = response.content
            try:
                decompressed = gzip.decompress(raw)
            except OSError:
                # Le serveur peut avoir renvoye du JSON non compresse malgre l'extension .gz
                decompressed = raw
            geojson = json.loads(decompressed)
            features = geojson.get("features", [])
            warnings: list[str] = []
            if not features:
                warnings.append(f"Bati non recupere (reponse vide) pour {code_insee}.")
            return ProviderResult(data=features, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001 -- defensif par conception, ne bloque jamais le job
            logger.warning("BuildingProvider: bati non recupere pour %s (%s) : %s", code_insee, url, exc)
            return empty_result(
                source.source_name,
                source.source_url,
                f"Bati non recupere pour {code_insee} (connecteur defensif, source Etalab) : {exc}",
                reliability="DERIVED",
            )
