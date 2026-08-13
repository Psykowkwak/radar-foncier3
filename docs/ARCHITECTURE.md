# Architecture — Radar Foncier Intelligent

Statut : document vivant. Dernière révision : 2026-08-13 (démarrage projet, MVP en cours).

## 1. Principe directeur

> SI UNE INFORMATION PEUT ÊTRE CALCULÉE → LA CALCULER.
> SI ELLE PEUT ÊTRE LUE DANS UNE DONNÉE STRUCTURÉE → UTILISER LA DONNÉE.
> SI ELLE DOIT ÊTRE INTERPRÉTÉE → UTILISER L'IA.
> SI ELLE EST INCONNUE → L'INDIQUER (`UNKNOWN`), jamais l'inventer.

Le pipeline d'analyse suit toujours :

```
FILTRES SIG (PostGIS, peu coûteux, exécutés sur toutes les parcelles)
      ↓
ANALYSE RÉGLEMENTAIRE (règles structurées d'abord, texte ensuite)
      ↓
SCORING (fonction déterministe, pondérations configurables)
      ↓
IA (uniquement sur le sous-ensemble retenu, jamais sur la géométrie/les calculs)
      ↓
FAISABILITÉ (sur sélection manuelle d'une parcelle/regroupement)
```

Le LLM n'est jamais appelé sur des milliers de parcelles. Il intervient sur : (a) l'interprétation de texte réglementaire non structuré (une fois par zone/règlement, mis en cache), (b) la génération de synthèses humaines à partir de données déjà calculées, (c) éventuellement l'aide à l'implantation conceptuelle. Il n'exécute jamais un calcul géométrique ou une règle qui peut être codée.

## 2. Vue d'ensemble des composants

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND — Next.js (TypeScript) + MapLibre GL JS                │
│  - Sélection territoire, filtres, carte, liste, fiche parcelle   │
│  - Consomme uniquement l'API backend (jamais les APIs externes)  │
└───────────────────────────┬───────────────────────────────────────┘
                             │ REST/JSON (OpenAPI)
┌───────────────────────────▼───────────────────────────────────────┐
│  BACKEND — FastAPI (Python)                                        │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────────┐ │
│  │ API routes     │  │ Services       │  │ Connectors (Providers) │ │
│  │ municipalities │  │ geometry       │  │ CadastreProvider       │ │
│  │ parcels        │  │ urbanism_rules │  │ UrbanismProvider (GPU) │ │
│  │ analysis jobs  │  │ scoring        │  │ IGNProvider (Géoplat.) │ │
│  │ feasibility    │  │ feasibility    │  │ RiskProvider (Géoris.) │ │
│  │ opportunities  │  │ llm_interpret  │  │ ElectricityNetworkProv.│ │
│  └───────────────┘  └───────────────┘  │ WaterProvider (stub)    │ │
│                                          │ SewerProvider (stub)    │ │
│                                          │ MarketProvider (stub)   │ │
│                                          └────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────────┘
                             │ SQLAlchemy + GeoAlchemy2
┌───────────────────────────▼───────────────────────────────────────┐
│  PostgreSQL 16 + PostGIS 3.4                                       │
│  Géométries, cache des règlements, jobs, favoris, historique       │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Pourquoi cette stack

- **FastAPI** : typage Pydantic natif, async, génère l'OpenAPI utilisé par le frontend, écosystème géo Python mature (GeoPandas/Shapely/PyProj) directement appelable sans pont inter-langage.
- **PostgreSQL/PostGIS** : seule base réaliste pour des requêtes spatiales (contiguïté, intersection zonage/parcelle, buffers réseau) sur des dizaines de milliers de géométries.
- **Next.js + MapLibre GL** : MapLibre est open-source (fork de Mapbox GL, licence BSD), pas de dépendance à une clé commerciale pour le rendu carte ; Next.js donne SSR léger pour les pages non-carte (paramètres, opportunités).
- **Docker Compose** : usage personnel, doit tourner en local ou sur un petit serveur sans orchestrateur complexe.

## 4. Couche connecteurs (Providers)

Chaque connecteur implémente une interface commune et ne fait QUE : appeler la source externe, gérer pagination/retry/cache, et mapper vers le modèle interne. Aucun connecteur ne fait de scoring ni d'interprétation.

```python
class DataProvider(Protocol):
    name: str
    def fetch(self, **params) -> ProviderResult: ...

@dataclass
class SourceRecord:
    source_name: str          # ex: "IGN API Carto Cadastre"
    source_url: str
    retrieved_at: datetime
    dataset_version: str | None
    reliability: Literal["OFFICIAL", "DERIVED", "USER_IMPORTED"]

@dataclass
class ProviderResult:
    data: Any
    source: SourceRecord
    warnings: list[str]
```

Un connecteur qui échoue ne doit jamais faire planter le job d'analyse : il retourne un `ProviderResult` vide avec un warning, propagé jusqu'à l'UI (`"Document d'urbanisme non récupéré — analyse incomplète"`).

Voir `docs/DATA_SOURCES.md` pour le détail des sources réelles et endpoints vérifiés, et `backend/app/connectors/` pour l'implémentation.

## 5. Cache des règlements d'urbanisme

Le texte réglementaire (PDF) et sa classification (zone-urba GeoJSON) sont chers à traiter (téléchargement + extraction + interprétation IA). Principe : **un `UrbanismRuleSet` est calculé une fois par (commune, document, zone, version)**, puis appliqué à toutes les parcelles de cette zone.

```
UrbanismDocument (id, commune, type, date_approbation, source_url, version)
   └── UrbanismZone (libellé zone, geometry, typezone)
         └── UrbanismRuleSet (contraintes structurées + textuelles, calculé 1x, avec confiance)
```

Invalidation : quand `UrbanismDocument.version` change (détecté via `datappro`/hash du document GPU), le `RuleSet` est recalculé, l'ancien est conservé en historique (jamais supprimé, pour traçabilité).

## 6. Jobs d'analyse asynchrones

Une analyse communale (jusqu'à plusieurs milliers de parcelles) tourne en tâche de fond (au MVP : tâche FastAPI `BackgroundTasks` + table `AnalysisJob` en DB pour la progression ; en V1 si le volume l'exige : file de tâches type RQ/Celery avec Redis — décision différée, non nécessaire tant qu'une commune s'analyse en dessous de la minute).

Étapes et progression exposées telles que spécifiées dans le cahier des charges (§39) : préparation 5 %, cadastre 20 %, urbanisme 40 %, bâti 55 %, risques 65 %, réseaux 75 %, scoring 90 %, finalisation 100 %.

## 7. Couche IA (LLMProvider)

Interface indépendante du fournisseur :

```python
class LLMProvider(Protocol):
    def interpret_urbanism_text(self, extract: str, context: dict) -> InterpretedRule: ...
    def summarize_opportunity(self, parcel_analysis: dict) -> str: ...
```

Implémentation initiale : `AnthropicLLMProvider` (API Claude). Une implémentation `OpenAILLMProvider` pourra être ajoutée sans toucher au reste de l'application. Le choix du fournisseur est une variable d'environnement (`LLM_PROVIDER=anthropic`).

Règle stricte : le LLM ne reçoit jamais de mission de calcul géométrique ou d'invention de donnée manquante. Ses seules sorties possibles sont des interprétations tracées (source, extrait, confiance) ou des synthèses rédactionnelles de données déjà calculées.

## 8. Déploiement

`docker-compose.yml` avec 3 services : `db` (postgis/postgis:16-3.4), `backend` (uvicorn), `frontend` (next start). Migrations Alembic exécutées au démarrage du backend (`alembic upgrade head`) ou manuellement via `docker compose run backend alembic upgrade head`.

## 9. Ce que ce document n'est pas

Ce n'est pas une promesse de fonctionnalités déjà implémentées. Voir `docs/ROADMAP.md` pour l'état réel MVP / V1 / V2.
