# Modèle de données

Toutes les tables utilisent des UUID (`gen_random_uuid()`, extension `pgcrypto`) comme clé primaire, sauf codes métier naturels (code INSEE) utilisés comme clé secondaire indexée. Migrations gérées par Alembic (`backend/alembic/versions/`). Géométries en `SRID=2154` (Lambert-93, mètres — indispensable pour tout calcul de surface/distance) avec reprojection à la volée en 4326 pour l'API/le frontend.

Ce document liste le modèle cible complet (§41 du cahier des charges). Les tables marquées **[MVP]** existent dès la migration initiale ; les autres sont ajoutées en V1/V2 (voir ROADMAP.md).

## Entités cœur

### Municipality **[MVP]**
`id, insee_code (unique), name, department_code, region_code, geometry(MultiPolygon,2154), population, last_analyzed_at`

### Parcel **[MVP]**
`id, municipality_id FK, section, numero, com_abs, prefixe, reference (section+numero, ex "AB0142"), geometry(MultiPolygon,2154), area_official (surface DGFiP si dispo), area_computed (ST_Area), source_id FK SourceRecord`

### Building **[MVP]**
`id, parcel_id FK (nullable, un bâtiment peut chevaucher plusieurs parcelles → table de jointure ParcelBuilding), geometry(MultiPolygon,2154), footprint_area, building_type (probable, texte libre + confiance), source_id FK`

### ParcelBuilding **[MVP]** (table d'association, gère chevauchement bâtiment/parcelle)
`parcel_id FK, building_id FK, overlap_area`

## Urbanisme

### UrbanismDocument **[V1, stub MVP]**
`id, municipality_id FK, type (PLU/PLUi/CC/POS), status, approval_date, source_document_id (id GPU), archive_url, version_hash`

### UrbanismZone **[MVP simplifié]**
`id, document_id FK (nullable au MVP si document non résolu), municipality_id FK, libelle (ex "UB"), libelong, typezone, geometry(MultiPolygon,2154), source_url (nomfic/urlfic), retrieved_at`

### UrbanismRuleSet **[V1]**
`id, zone_id FK, version, computed_at, constraints_structured (JSONB), constraints_textual (JSONB: [{rule, extract, source_document, article, page, interpretation, confidence}]), overall_confidence, needs_human_review (bool)`

### UrbanismConstraint **[V1]** (dénormalisation interrogeable des contraintes structurées)
`id, ruleset_id FK, key (ex "max_height_m"), value_numeric, value_text, unit, confidence, source_reference`

### Prescription **[V1]** — `id, municipality_id FK, geometry, category, label, source_id FK`
### Servitude **[V1]** — `id, municipality_id FK, geometry, category (nomenclature SUP nationale, ex "PM1"), label, gestionnaire, source_id FK`
### Risk **[MVP simplifié : niveau commune uniquement]** — `id, municipality_id FK, risk_type (RGA/cavite/PPR/...), level, geometry (nullable si donnée non spatialisée), source_id FK, retrieved_at`

## Voirie et réseaux

### Road **[V1]** — `id, geometry(LineString,2154), road_type, width_estimated, source_id FK`
### NetworkElement **[V1, stub MVP]** — `id, network_type (electricity_bt/electricity_hta/water/sewer), geometry, status (CONFIRMED/PROBABLE/UNKNOWN), source_id FK`

## Analyse et scoring

### ParcelAnalysis **[MVP]**
`id, parcel_id FK, job_id FK AnalysisJob, computed_at,`
`parcel_area, building_footprint_area, building_coverage_ratio, unbuilt_area, largest_contiguous_unbuilt_area,`
`width_estimated, depth_estimated, road_frontage_length, geometry_quality_score,`
`built_category (VACANT_LAND/LIGHTLY_BUILT/PARTIALLY_BUILT/HEAVILY_BUILT/FULLY_DEVELOPED/REDEVELOPMENT_POTENTIAL),`
`constructibility_status (FAVORABLE/FAVORABLE_SOUS_CONDITIONS/COMPLEXE/DEFAVORABLE/A_PRIORI_NON_CONSTRUCTIBLE/DONNEES_INSUFFISANTES),`
`urbanism_confidence_score, suggested_operations (JSONB, liste des 9 types §1)`

### ParcelScore **[MVP simplifié]**
`id, analysis_id FK, score_urbanisme, score_geometrie, score_surface, score_acces, score_reseaux, score_risques, score_densification, score_complexite, score_qualite_donnees, score_global, explanation_text, weights_version_id FK`

### ScoringWeights **[MVP]** (config utilisateur, voir §14/§45)
`id, name, weights (JSONB), penalties (JSONB), is_active, created_at`

### LandAssembly **[V1]** — `id, municipality_id FK, parcel_ids (array FK), combined_geometry, combined_area, score_id FK`

### AnalysisJob **[MVP]**
`id, municipality_id FK, status, progress_pct, current_step, started_at, finished_at, parcels_total, parcels_selected, parcels_excluded, exclusion_reasons (JSONB), error_log (JSONB)`

## Faisabilité (V2)

### FeasibilityStudy **[V2]** — `id, parcel_id FK (ou land_assembly_id), created_at, buildable_envelope (geometry)`
### FeasibilityScenario **[V2]** — `id, study_id FK, name (PRUDENT/CENTRAL/OPTIMISE), operation_type, program (JSONB), budget_id FK, feasibility_score`
### ConceptualBuilding **[V2]** — `id, scenario_id FK, geometry, levels, footprint_area, floor_area`
### ConceptualLot **[V2]** — `id, scenario_id FK, geometry, area`
### ParkingLayout **[V2]** — `id, scenario_id FK, spaces_required, spaces_placed, geometry (emplacements), mode (exterior/underground)`
### CostAssumption **[V2]** (config, voir §30/§45) — `id, category, unit, value_low, value_central, value_high, updated_at`
### DevelopmentBudget **[V2]** — `id, scenario_id FK, revenue_breakdown (JSONB), cost_breakdown (JSONB), margin_target_pct, max_land_price`

## Transverse

### SourceRecord **[MVP]** — `id, source_name, source_url, retrieved_at, dataset_version, reliability (OFFICIAL/DERIVED/USER_IMPORTED), checksum`
### AnalysisWarning **[MVP]** — `id, job_id FK (nullable), parcel_id FK (nullable), severity (BLOQUANT/IMPORTANT/INFORMATION), message, source_id FK`
### UserOpportunity **[V1]** (favoris/statuts, §19/§43) — `id, parcel_id FK ou land_assembly_id FK, status (A_ETUDIER/INTERESSANT/TRES_INTERESSANT/CONTACT_A_TROUVER/CONTACTE/EN_ETUDE/ABANDONNE), notes, owner_price_estimate, asking_price, contact_info (JSONB), updated_at`
### AnalysisHistory **[V1]** — `id, parcel_id FK, analysis_id FK, score_at_time, recorded_at` (permet de tracer l'évolution du score dans le temps, §42)

## Notes d'implémentation

- Toute table géométrique a un index `GIST` sur la colonne géométrie.
- `ParcelAnalysis` n'écrase jamais un enregistrement précédent : nouvelle ligne à chaque job, `AnalysisHistory` garde la trace, la fiche parcelle affiche la plus récente par défaut.
- Les scores et statuts de constructibilité utilisent des `Enum` Python + `CHECK constraint` PostgreSQL, jamais des chaînes libres, pour éviter la dérive de valeurs.
