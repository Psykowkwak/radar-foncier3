"""DVFProvider -- source REELLE (DVF geolocalisees, Etalab/DGFiP), voir
docs/DATA_SOURCES.md et docs/FEASIBILITY_ENGINE.md "Bilan promoteur".

Fournit un ordre de grandeur du prix de vente reel au m2 (bati et terrain nu) par
commune, a partir de vraies transactions immobilieres recentes (jeu de donnees
officiel "Demandes de valeurs foncieres geolocalisees", data.gouv.fr, licence
ouverte, alimente par la DGFiP). Jamais invente : si l'echantillon de transactions
est trop faible (< MIN_SAMPLE_SIZE) pour un type donne, le prix correspondant reste
None -- toute estimation economique en aval devient alors non calculable plutot
que basee sur une supposition.

Endpoint (fichier CSV par commune, projet officiel "geo-dvf") :
GET https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/communes/{dep}/{code_insee}.csv

Plusieurs millesimes recents sont agreges (par defaut les 3 dernieres annees
disponibles) pour obtenir un echantillon suffisant sur les communes peu
transactionnees, sans remonter trop loin dans le temps (prix perimes). Un
millesime manquant pour une commune (fichier absent) n'est pas bloquant, les
autres annees sont utilisees.

A verifier avant usage intensif : ce chemin (fichiers par commune, dataset
"geo-dvf") n'a pas pu etre confirme par un appel reseau reel depuis cet
environnement (pas d'acces sortant verifie vers files.data.gouv.fr en sandbox --
meme limite deja documentee et confirmee sans consequence pour les autres
connecteurs du projet, qui fonctionnent correctement une fois deployes). Son
existence et sa structure de colonnes (id_mutation, valeur_fonciere, type_local,
surface_reelle_bati, surface_terrain, nature_mutation, code_commune, etc.) sont en
revanche confirmees par la documentation officielle du jeu de donnees sur
data.gouv.fr et par le code source public du projet geo-dvf. A confirmer en
conditions reelles au premier deploiement, comme les autres connecteurs du MVP.
"""
from __future__ import annotations

import csv
import io
import logging
import statistics

from app.connectors.base import ProviderResult, SourceRecord, empty_result, get_http_client, request_with_retry
from app.services.insee_utils import department_from_insee

logger = logging.getLogger("radar_foncier.connectors.dvf")

BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv"
YEARS_TO_TRY = ["2025", "2024", "2023"]  # agregation multi-annees pour un echantillon suffisant
MIN_SAMPLE_SIZE = 5  # sous ce seuil, le prix n'est pas calcule (echantillon non representatif)
BATI_TYPES = {"Maison", "Appartement"}
# Filtre defensif anti-aberrations de saisie (pas un filtre esthetique sur la
# distribution reelle des prix) : ecarte les valeurs manifestement erronees.
PLAUSIBLE_PRICE_PER_M2_RANGE = (50.0, 20000.0)


class DVFProvider:
    name = "DVFProvider"

    def fetch(self, **params) -> ProviderResult:
        return self.fetch_commune(params["code_insee"])

    def fetch_commune(self, code_insee: str) -> ProviderResult:
        dep = department_from_insee(code_insee)
        source = SourceRecord(
            source_name="DVF geolocalisees (Etalab/DGFiP, projet geo-dvf)",
            source_url=f"{BASE_URL}/<annee>/communes/{dep}/{code_insee}.csv",
            reliability="OFFICIAL",
        )
        rows: list[dict] = []
        fetched_years: list[str] = []
        try:
            with get_http_client() as client:
                for year in YEARS_TO_TRY:
                    url = f"{BASE_URL}/{year}/communes/{dep}/{code_insee}.csv"
                    try:
                        response = request_with_retry(client, "GET", url)
                        rows.extend(csv.DictReader(io.StringIO(response.text)))
                        fetched_years.append(year)
                    except Exception as exc:  # noqa: BLE001 -- un millesime manquant n'est pas bloquant
                        logger.info("DVFProvider: millesime %s indisponible pour %s : %s", year, code_insee, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("DVFProvider: echec general pour %s : %s", code_insee, exc)
            return empty_result(
                source.source_name, source.source_url, f"DVF non recupere pour {code_insee} : {exc}"
            )

        if not rows:
            return ProviderResult(
                data=None,
                source=source,
                warnings=[
                    f"Aucune transaction DVF recuperee pour {code_insee} sur {YEARS_TO_TRY} -- "
                    "prix de reference indisponibles, estimation economique non calculable."
                ],
                success=False,
            )

        price_bati, n_bati = _median_price_per_m2(
            rows,
            surface_field="surface_reelle_bati",
            type_filter=lambda r: r.get("type_local") in BATI_TYPES and _to_float(r.get("nombre_lots")) in (None, 0.0, 1.0),
        )
        price_terrain, n_terrain = _median_price_per_m2(
            rows,
            surface_field="surface_terrain",
            type_filter=lambda r: not r.get("type_local") and _to_float(r.get("surface_terrain")),
        )

        warnings: list[str] = []
        if n_bati < MIN_SAMPLE_SIZE:
            warnings.append(
                f"Echantillon DVF insuffisant pour un prix bati fiable a {code_insee} "
                f"({n_bati} transaction(s), seuil {MIN_SAMPLE_SIZE})."
            )
            price_bati = None
        if n_terrain < MIN_SAMPLE_SIZE:
            warnings.append(
                f"Echantillon DVF insuffisant pour un prix terrain fiable a {code_insee} "
                f"({n_terrain} transaction(s), seuil {MIN_SAMPLE_SIZE})."
            )
            price_terrain = None

        data = {
            "price_per_m2_bati": price_bati,
            "sample_size_bati": n_bati,
            "price_per_m2_terrain": price_terrain,
            "sample_size_terrain": n_terrain,
            "years": fetched_years,
        }
        return ProviderResult(data=data, source=source, warnings=warnings, success=True)


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _median_price_per_m2(rows: list[dict], *, surface_field: str, type_filter) -> tuple[float | None, int]:
    prices: list[float] = []
    for row in rows:
        if row.get("nature_mutation") != "Vente":
            continue
        if not type_filter(row):
            continue
        value = _to_float(row.get("valeur_fonciere"))
        surface = _to_float(row.get(surface_field))
        if value is None or not surface or surface <= 0:
            continue
        price_per_m2 = value / surface
        low, high = PLAUSIBLE_PRICE_PER_M2_RANGE
        if low <= price_per_m2 <= high:
            prices.append(price_per_m2)
    if not prices:
        return None, 0
    return statistics.median(prices), len(prices)
