"""RiskProvider -- source PARTIELLEMENT REELLE / defensive (Georisques), voir
docs/DATA_SOURCES.md section D.

Statut : implemente partiel pour RGA (retrait-gonflement des argiles) et cavites
souterraines, interrogation par commune (code INSEE). DATA_SOURCES.md indique que le
schema exact des reponses Georisques est "a confirmer au premier appel reel" (doc
interactive non parsee). Ce connecteur est donc ecrit en mode DEFENSIF STRICT :
toute erreur HTTP, tout schema de reponse inattendu => ProviderResult vide avec
warning, niveau de risque renvoye a l'appelant = UNKNOWN, JAMAIS un niveau optimiste
par defaut (voir docs/ARCHITECTURE.md, principe directeur).

Endpoints utilises (base verifiee, chemins exacts non re-testes -- Indirect) :
- RGA (retrait-gonflement des argiles) : GET {base}/rga?code_insee={insee}
- Cavites souterraines                : GET {base}/cavites?code_insee={insee}
Base : https://georisques.gouv.fr/api/v1/

A verifier avant usage intensif : noms exacts des parametres de requete et forme
du JSON retourne (non confirmes -- doc-api Georisques est une SPA non lisible par
simple fetch, voir DATA_SOURCES.md). Si les chemins ci-dessus different en
production, adapter ICI uniquement (le reste du code ne depend que de
ProviderResult / niveau UNKNOWN par defaut).
"""
from __future__ import annotations

import logging
from typing import Any

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry

logger = logging.getLogger("radar_foncier.connectors.risk")

BASE_URL = "https://georisques.gouv.fr/api/v1"


class RiskProvider:
    name = "RiskProvider"

    def fetch(self, **params: Any) -> ProviderResult:
        """params attendus : code_insee=str, risk_type='RGA'|'CAVITE' (defaut RGA)."""
        code_insee = params["code_insee"]
        risk_type = params.get("risk_type", "RGA")
        if risk_type == "CAVITE":
            return self.fetch_cavites(code_insee)
        return self.fetch_rga(code_insee)

    def fetch_rga(self, code_insee: str) -> ProviderResult:
        return self._fetch_endpoint("rga", code_insee, "RGA (retrait-gonflement des argiles)")

    def fetch_cavites(self, code_insee: str) -> ProviderResult:
        return self._fetch_endpoint("cavites", code_insee, "cavites souterraines")

    def _fetch_endpoint(self, path: str, code_insee: str, label: str) -> ProviderResult:
        url = f"{BASE_URL}/{path}"
        source = SourceRecord(
            source_name=f"Georisques API v1 - {label}",
            source_url=f"{url}?code_insee={code_insee}",
            reliability="OFFICIAL",
        )
        try:
            with get_http_client() as client:
                response = request_with_retry(client, "GET", url, params={"code_insee": code_insee})
                payload = response.json()
            records = payload.get("data", payload if isinstance(payload, list) else [])
            warnings: list[str] = []
            if not records:
                warnings.append(f"Aucune donnee {label} trouvee pour {code_insee} -- niveau UNKNOWN.")
            return ProviderResult(data=records, source=source, warnings=warnings, success=True)
        except Exception as exc:  # noqa: BLE001 -- defensif : jamais bloquant, niveau retourne = UNKNOWN
            logger.warning("RiskProvider: %s non recupere pour %s : %s", label, code_insee, exc)
            return empty_result(
                source.source_name,
                source.source_url,
                f"Risque {label} non recupere pour {code_insee} (niveau UNKNOWN) : {exc}",
                reliability="DERIVED",
            )
