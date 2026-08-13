# Sources de données — état vérifié au 2026-08-13

Légende fiabilité : **Vérifié** = documentation officielle lue directement. **Indirect** = mention trouvée via recherche, non lue sur la source elle-même. **Incertain** = à confirmer avant implémentation.

Aucun endpoint listé ci-dessous n'a été inventé. Quand une information n'a pas pu être vérifiée, c'est indiqué explicitement — le connecteur correspondant doit être traité comme expérimental tant que la vérification n'est pas faite (voir colonne "Statut connecteur").

## A. Cadastre

### A.1 cadastre.data.gouv.fr (Etalab, source DGFiP PCI Vecteur) — **Vérifié**

- Téléchargement en masse, sans authentification, Licence Ouverte Etalab 2.0.
- Endpoints (millésime `latest` ou `AAAA-MM-JJ`) :
  - `https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/{dep}/{code_insee}.json`
  - Couches par commune dans une archive : `communes`, `sections`, `parcelles`, `subdivisions_fiscales`, `batiments`, `lieux_dits`, `feuilles`, `prefixes_sections`
  - Aussi disponible : GeoParquet et MBTiles France entière.
- Couverture : 100 % des communes (PCI Vecteur) depuis le 1er septembre 2025.
- Mise à jour trimestrielle.
- **Statut connecteur MVP : source de secours / usage batch (téléchargement complet d'une commune), pas utilisée en requête interactive au MVP.**

### A.2 API Carto — module Cadastre (IGN) — **Vérifié**

- Base : `https://apicarto.ign.fr/api/cadastre/`
- Endpoints : `/commune`, `/feuille` (PCI Express), `/division` (BD Parcellaire, déprécié), `/parcelle`, `/localisant`
- Filtres : `code_insee`, `code_dep`, `section`, `numero`, `com_abs`, `code_arr`, `source_ign`, géométrie GeoJSON (`geom`), pagination `_limit`/`_start`
- Aucune authentification requise.
- Limite : 1000 objets/réponse (500 pour `/commune`)
- Format : GeoJSON, WGS84 (EPSG:4326)
- Exemple vérifié : `GET https://apicarto.ign.fr/api/cadastre/parcelle?code_insee=94067`
- **Statut connecteur MVP : PRINCIPAL. `CadastreProvider` interroge cet endpoint en direct pour parcelles + communes.**
- Note : cette API ne retourne pas les bâtiments cadastraux (couche `batiments`) — pour le bâti, MVP utilise le téléchargement Etalab (A.1) en fallback, ou BD TOPO bâti (C) en V1.

## B. Géoportail de l'Urbanisme (GPU)

### B.1 API Carto — module GPU (IGN) — **Vérifié**

- Base : `https://apicarto.ign.fr/api/gpu/`
- Couches : `municipality`, `document`, `zone-urba`, `secteur-cc`, `prescription-pct`, `prescription-lin`, `prescription-surf`, `info-pct`, `info-lin`, `info-surf`, `acte-sup`, `assiette-sup-{p,l,s}`, `generateur-sup-{p,l,s}`
- Requêtage par géométrie GeoJSON, par `partition` (`DU_<insee>` document communal, `DU_<siren>` PLUi, `PSMV_<insee>`, `<idGest>_SUP_<codeGeo>_<categorie>` pour SUP), ou `insee` (uniquement `municipality`)
- Exemples vérifiés : `/gpu/document?partition=DU_77443`, `/gpu/zone-urba` filtré par géométrie
- Attributs clés `zone-urba` : `libelle` (ex "Uc"), `libelong`, `typezone`, `destdomi`, `nomfic`/`urlfic` (PDF du règlement), `insee`, `datappro`, `idurba`
- **⚠️ Couverture incomplète, avertissement officiel** : "l'absence de résultat ne signifie pas l'absence de document" — ne jamais interpréter un résultat vide comme "hors PLU"/"non réglementé".
- Aucune authentification requise.
- **Statut connecteur MVP : PRINCIPAL pour le zonage (`zone-urba`). Le texte réglementaire (`nomfic`/`urlfic`) reste un PDF non structuré — hors MVP, prévu V1 avec la couche IA d'extraction.**

### B.2 geoportail-urbanisme.gouv.fr — détail document — **Indirect (partiel)**

- `GET https://www.geoportail-urbanisme.gouv.fr/api/document/{id}/details` → métadonnées (type, statut, dates, `writingMaterials` = URLs PDF du règlement, `archiveUrl` = zip complet)
- Swagger existe (`/api/swagger.yaml`) mais non parsé en détail.
- **Statut connecteur : V1, pour récupérer le PDF du règlement écrit à donner à la couche IA d'interprétation.**

## C. IGN Géoplateforme (data.geopf.fr / cartes.gouv.fr)

- **Migration confirmée** : l'ancien Géoportail (`geoservices.ign.fr`, clés "essentiels"/"applicative", domaines `wxs.ign.fr`) est obsolète. Doc actuelle : `https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/`
- Endpoints confirmés :
  - WMTS : `https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetCapabilities`
  - WFS 2.0.0 (limite 30 req/s) : `https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities`
  - WMS-Raster/Vecteur, TMS : existent, paramètres non vérifiés en détail
- **Incertain** : noms exacts des couches WMTS (BD ORTHO, Plan IGN, BD TOPO, RGE ALTI, LiDAR HD) — à confirmer via un vrai `GetCapabilities` avant intégration (probable reprise des noms historiques `ORTHOIMAGERY.ORTHOPHOTOS`, `GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2`, mais NON vérifié directement).
- Auth : couches "essentielles" accessibles sans clé nominative sur `data.geopf.fr` (comportement historique, à reconfirmer).
- **Statut connecteur MVP : fond de carte "Plan" et "Orthophoto" affichés en frontend directement via tuiles WMTS `data.geopf.fr` (pas de traitement backend nécessaire pour le simple affichage). Bâti/BD TOPO en V1.**

### C.1 Géocodage / BAN — **Vérifié**

- `https://data.geopf.fr/geocodage/search`, `/reverse`, `/openapi` (swagger)
- Remplace `api-adresse.data.gouv.fr` (déprécié — confirmé sur la fiche officielle : 100 % dispo affiché sur la nouvelle URL).
- Limite 50 req/s/IP.
- **Statut connecteur MVP : utilisé pour la recherche de commune / adresse approximative.**

## D. Géorisques — **Vérifié (base), Indirect (détail endpoints)**

- Base : `https://georisques.gouv.fr/api/v1/`
- Limite : 1000 req/min/IP, gratuit, sans authentification.
- Endpoints officiels listés (fiche data.gouv.fr) : AZI, CATNAT, cavités souterraines, DICRIM, PPR (états, familles), Installations Classées, MVT, OLD, PAPI, RADON, rapport PDF, retrait-gonflement des argiles (RGA), SIS (pollution des sols), TIM, TRI, zonage sismique.
- Doc interactive `/doc-api` est une SPA non lisible par simple fetch — schéma exact des réponses **à confirmer au premier appel réel**.
- Exemple de pattern (Indirect, non re-testé) : `GET /gaspar/catnat?longitude=...&latitude=...&rayon=...`
- Licence etalab-2.0.
- **Statut connecteur MVP : `RiskProvider` implémenté pour RGA et cavités a minima (interrogation par commune/point), avec warning explicite si un appel échoue. Autres risques ajoutés en V1.**

## E. Enedis Open Data — **Indirect (détail API non confirmé)**

- Portails : `opendata.enedis.fr` / `data.enedis.fr`, plateforme OpenDataSoft.
- Jeux pertinents : réseau BT aérien (`reseau-bt`), HTA souterrain (`reseau-souterrain-hta`), HTA aérien (`reseau-hta`).
- Pattern générique OpenDataSoft Explore API v2.1 : `https://{portail}/api/explore/v2.1/catalog/datasets/{dataset_id}/records` — **non testé sur le portail Enedis précis, à vérifier avant implémentation**.
- Licence ODbL v1.0 (Indirect).
- **Statut connecteur : STUB en MVP et V1 initial. `ElectricityNetworkProvider` retourne `UNKNOWN` tant que le pattern d'appel n'est pas vérifié manuellement. Ne jamais afficher "raccordement possible" — au mieux "réseau identifié à proximité" une fois le connecteur validé.**

## F. Eau potable et assainissement — **Vérifié, angle mort confirmé**

- L'API Hub'eau "Indicateurs des services" (SISPEA) est **en cours de décommissionnement, arrêt prévu le 10/09/2026**. Ne pas construire de dépendance dessus.
- Aucune donnée nationale structurée à la maille parcelle : le niveau le plus fin est le périmètre du service public (souvent intercommunal), pas le branchement.
- Successeur officiel : téléchargement sur `services.eaufrance.fr/pro/telechargement`, pas d'API confirmée.
- **Statut connecteur MVP/V1 : `WaterProvider`/`SewerProvider` retournent systématiquement `UNKNOWN` sauf import manuel d'une couche locale (GeoJSON/SHP/GPKG) par l'utilisateur — mécanisme d'import prévu V1, pas de connecteur national fiable disponible.**

## G. Sources complémentaires (architecture prête, intégration différée)

- **DVF+ (Cerema/Etalab)**, accès libre, GeoJSON, via `data.gouv.fr/dataservices/api-donnees-foncieres` (Géomutations, Mutations) — **Vérifié**. Attention légale : pas d'indexation moteur de recherche, pas de réidentification.
- **Fichiers fonciers/DV3F (Cerema)** : accès restreint aux missions de service public, hors périmètre usage personnel — non intégré.
- **INSEE** : nouveau portail centralisé `portail-api.insee.fr/catalog/all` depuis le 17/10/2024, API Sirene/Melodi/BDM/données locales — auth par souscription, endpoints précis non extraits (**Indirect**).
- **BAN** : voir C.1.

## Récapitulatif — statut par connecteur au MVP

| Connecteur | Source | Statut MVP |
|---|---|---|
| CadastreProvider | API Carto IGN (cadastre) | Implémenté, appel réel |
| UrbanismProvider | API Carto IGN (gpu, zone-urba) | Implémenté, zonage seul (pas le texte réglementaire) |
| BuildingProvider | Etalab cadastre (batiments) | Implémenté, fallback téléchargement commune |
| RiskProvider | Géorisques API v1 | Implémenté partiel (RGA, cavités), reste en V1 |
| ElectricityNetworkProvider | Enedis Open Data | Stub — retourne UNKNOWN |
| WaterProvider / SewerProvider | Aucune source nationale fiable | Stub — retourne UNKNOWN, import manuel prévu V1 |
| ElevationProvider | IGN Géoplateforme RGE ALTI | Stub V1 (noms de couches à vérifier) |
| MarketProvider (DVF) | DVF+ Etalab/Cerema | Différé V1+ |
| GeocodingProvider | Géoplateforme /geocodage | Implémenté |

## Mise à jour des données

Chaque enregistrement importé conserve `source_name`, `source_url`, `retrieved_at`, `dataset_version` (quand disponible), `reliability`. Une commande `POST /api/municipalities/{insee}/refresh` relance les connecteurs pour une commune et versionne les nouveaux résultats sans écraser l'historique (voir DATA_MODEL.md, `SourceRecord`).
