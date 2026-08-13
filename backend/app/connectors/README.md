# Connecteurs (Providers)

Chaque connecteur implemente le Protocol `DataProvider` (`base.py`) : une methode
`fetch(**params) -> ProviderResult`. Un connecteur ne fait QUE collecter et mapper
vers des structures neutres (listes de features GeoJSON, dicts) -- aucun calcul
geometrique, aucune interpretation, aucun scoring (voir docs/ARCHITECTURE.md §4).

Regle commune a tous : timeout 10s, retry 2 tentatives (`request_with_retry`),
User-Agent `RadarFoncier/0.1 (usage personnel)`, et **aucune exception ne remonte
jamais** jusqu'a l'appelant -- tout est catche et transforme en `ProviderResult`
vide + warning explicite (voir `empty_result` dans `base.py`).

| Connecteur | Fichier | Source | Endpoint(s) | Statut | A verifier avant usage intensif |
|---|---|---|---|---|---|
| CadastreProvider | `cadastre.py` | API Carto IGN (cadastre) | `GET /api/cadastre/commune`, `GET /api/cadastre/parcelle` (pagination `_limit`/`_start`) | **REEL** | Stabilite du schema d'attributs, comportement sous forte charge (pas de SLA documente) |
| UrbanismProvider | `urbanism.py` | API Carto IGN (GPU, zone-urba) | `GET /api/gpu/zone-urba?partition=DU_{insee}` (+ mode geometrie en POST) | **REEL** (zonage seul) | Couverture GPU incomplete (avertissement officiel) -- ne jamais interpreter une reponse vide comme "hors PLU" |
| BuildingProvider | `buildings.py` | Etalab cadastre.data.gouv.fr | `GET .../communes/{dep}/{insee}/{insee}-batiments.json.gz` | **DEFENSIF / experimental** | Chemin exact non teste avec un vrai appel reseau depuis cet environnement ; DATA_SOURCES.md documente plutot une archive JSON par commune -- a confirmer, adapter si 404 systematique |
| RiskProvider | `risk.py` | Georisques API v1 | `GET /rga?code_insee=`, `GET /cavites?code_insee=` | **DEFENSIF / partiel** | Schema de reponse non confirme (doc-api Georisques est une SPA) ; niveau retourne = UNKNOWN si echec, jamais un niveau optimiste |
| GeocodingProvider | `geocoding.py` | Geoplateforme geocodage (BAN) | `GET /geocodage/search?q=&type=municipality` | **REEL** | Limite 50 req/s/IP a respecter cote frontend (debounce autocomplete) |

## Connecteurs explicitement hors MVP (voir docs/ROADMAP.md)

Non implementes dans ce depot : `ElectricityNetworkProvider` (Enedis, pattern
OpenDataSoft non verifie), `WaterProvider`/`SewerProvider` (aucune source nationale
fiable a la maille parcelle), `ElevationProvider` (RGE ALTI, noms de couches WMTS a
confirmer), `MarketProvider` (DVF, differe V1+). Le moteur de scoring (voir
`app/services/scoring.py`) traite ces axes comme `DONNEES_INSUFFISANTES` / valeur
neutre 50, jamais une valeur inventee.
