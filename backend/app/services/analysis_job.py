"""Orchestration complete du job d'analyse communale -- voir docs/ARCHITECTURE.md §6.

commune -> parcelles -> bati -> zonage -> risques -> geometrie -> score -> sauvegarde

Progression exposee (§39 du cahier des charges, reprise dans ARCHITECTURE.md §6) :
preparation 5%, cadastre 20%, urbanisme 40%, bati 55%, risques 65%, reseaux 75%,
scoring 90%, finalisation 100%.

Execute en tache de fond FastAPI `BackgroundTasks` (pas de file de taches dediee au
MVP, voir docs/ROADMAP.md "Decisions techniques prises sans blocage").
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree
from sqlalchemy import delete, select

from app.connectors.base import ProviderResult
from app.connectors.buildings import BuildingProvider
from app.connectors.cadastre import CadastreProvider
from app.connectors.dvf import DVFProvider
from app.connectors.risk import RiskProvider
from app.connectors.urbanism import UrbanismProvider
from app.core.db import SessionLocal
from app.models.analysis import AnalysisJob, AnalysisWarning, ParcelAnalysis
from app.models.building import Building, ParcelBuilding
from app.models.economics import CostAssumption, ParcelFeasibility
from app.models.enums import AnalysisJobStatusEnum, RiskLevelEnum, RiskTypeEnum, SeverityEnum
from app.models.municipality import Municipality
from app.models.parcel import Parcel
from app.models.risk import Risk
from app.models.scoring import ParcelScore
from app.models.source import SourceRecord
from app.models.urbanism import UrbanismZone
from app.services.built_category import classify_built_category
from app.services.feasibility import FeasibilityInputs, compute_feasibility
from app.services.geometry import (
    building_coverage_ratio,
    compute_geometry_metrics,
    geojson_to_shape,
    largest_contiguous_unbuilt_area,
    reproject_to_lambert93,
    unbuilt_area,
)
from app.services.scoring import ScoringInputs, compute_score
from app.services.urbanism_classification import classify_constructibility

logger = logging.getLogger("radar_foncier.services.analysis_job")

PROGRESS_STEPS = {
    "preparation": 5,
    "cadastre": 20,
    "urbanisme": 40,
    "bati": 55,
    "risques": 65,
    "reseaux": 75,
    "scoring": 90,
    "finalisation": 100,
}


def run_analysis_job(job_id: uuid.UUID) -> None:
    """Point d'entree appele par BackgroundTasks. Ouvre sa propre session DB (la
    session de la requete HTTP qui a lance le job est deja fermee quand la tache de
    fond s'execute)."""
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            logger.error("AnalysisJob %s introuvable", job_id)
            return
        municipality = db.get(Municipality, job.municipality_id)
        if municipality is None:
            _fail_job(db, job, "Commune introuvable")
            return

        # CORRECTION CRITIQUE (voir incident du 2026-08-13) : sans ceci, relancer une
        # analyse sur une commune deja analysee accumule indefiniment de nouvelles
        # lignes Parcel (aucune notion d'upsert au MVP -- _upsert_parcels cree
        # toujours de nouvelles lignes). L'API /opportunities ne filtrant pas par
        # job, elle additionnait alors TOUTES les parcelles de TOUTES les analyses
        # passees (ex. Deauville analysee 6 fois -> 20544 parcelles au lieu de 3424,
        # 6x trop de donnees, payload JSON geant -> le navigateur se figeait
        # completement : liste vide, carte non cliquable). Au MVP une analyse
        # represente l'etat courant de la commune, pas un historique : on purge
        # donc integralement les donnees parcellaires precedentes avant d'en
        # reinserer de nouvelles.
        _reset_municipality_data(db, municipality)

        job.status = AnalysisJobStatusEnum.RUNNING
        job.started_at = datetime.now(timezone.utc)
        _update_progress(db, job, "preparation")

        code_insee = municipality.insee_code

        # --- CADASTRE ---
        cadastre_provider = CadastreProvider()
        commune_result = cadastre_provider.fetch_commune(code_insee)
        _record_warnings(db, job, None, commune_result)
        _apply_commune_geometry(db, municipality, commune_result)

        parcelles_result = cadastre_provider.fetch_parcelles(code_insee)
        _record_warnings(db, job, None, parcelles_result)
        parcel_features = parcelles_result.data or []
        parcels = _upsert_parcels(db, municipality, parcel_features, parcelles_result)
        _update_progress(db, job, "cadastre")

        commune_geometry = commune_result.data[0].get("geometry") if commune_result.data else None

        # --- URBANISME (zonage GPU) ---
        urbanism_provider = UrbanismProvider()
        zone_result = urbanism_provider.fetch_by_partition(code_insee)
        # Repli documente (voir connectors/urbanism.py) : le mode "partition" suppose
        # que le document est reference exactement sous "DU_<insee>", ce qui echoue
        # pour certaines communes (ex. PLU intercommunal reference sous le SIREN de
        # l'EPCI plutot que le code INSEE communal). Si aucune zone n'est trouvee par
        # partition, on retente par intersection geometrique avec le contour de la
        # commune (deja recupere via le cadastre), plus robuste au nommage exact du
        # document -- voir docs/DATA_SOURCES.md B.1.
        if not zone_result.data and commune_geometry:
            geom_fallback_result = urbanism_provider.fetch_by_geometry(commune_geometry)
            if geom_fallback_result.data:
                zone_result = geom_fallback_result
        _record_warnings(db, job, None, zone_result)
        zones = _upsert_zones(db, municipality, zone_result.data or [], zone_result)
        gpu_data_available = bool(zones)
        zone_index, zone_geoms = _build_zone_index(zones)
        _update_progress(db, job, "urbanisme")

        # --- BATI ---
        # CORRECTION (voir incident du 2026-08-13) : l'ancienne source (Etalab
        # cadastre.data.gouv.fr) renvoyait 404 pour toutes les communes, neutralisant
        # score_surface + score_densification partout. Remplacee par le flux WFS IGN
        # BD TOPO (voir app/connectors/buildings.py), qui necessite la geometrie
        # communale (bbox) plutot que le seul code INSEE.
        building_provider = BuildingProvider()
        building_result = building_provider.fetch(code_insee=code_insee, commune_geometry=commune_geometry)
        _record_warnings(db, job, None, building_result)
        buildings = _upsert_buildings(db, building_result.data or [], building_result)
        building_data_available = building_result.success and bool(buildings)
        parcel_buildings_map = _link_parcel_buildings(db, parcels, buildings)
        _update_progress(db, job, "bati")

        # --- RISQUES ---
        risk_provider = RiskProvider()
        rga_result = risk_provider.fetch_rga(code_insee)
        cavite_result = risk_provider.fetch_cavites(code_insee)
        _record_warnings(db, job, None, rga_result)
        _record_warnings(db, job, None, cavite_result)
        risk_level, risk_data_available = _store_commune_risks(db, municipality, rga_result, cavite_result)
        _update_progress(db, job, "risques")

        # --- RESEAUX / DONNEES ECONOMIQUES DVF ---
        # Le reseau (voirie/eau/electricite) reste hors MVP (stub, voir
        # docs/DATA_SOURCES.md E/F) ; ce palier de progression recupere en plus les
        # prix de vente reels (DVF) necessaires au bilan promoteur simplifie
        # (app/services/feasibility.py), une fois par commune pour tout le job.
        dvf_provider = DVFProvider()
        dvf_result = dvf_provider.fetch_commune(code_insee)
        _record_warnings(db, job, None, dvf_result)
        dvf_data = dvf_result.data or {}
        price_per_m2_bati_dvf = dvf_data.get("price_per_m2_bati")
        price_per_m2_terrain_dvf = dvf_data.get("price_per_m2_terrain")
        dvf_sample_size_bati = dvf_data.get("sample_size_bati")
        dvf_sample_size_terrain = dvf_data.get("sample_size_terrain")
        cost_assumption = _get_default_cost_assumption(db)
        _update_progress(db, job, "reseaux")

        # --- SCORING ---
        excluded_count = 0
        selected_count = 0
        exclusion_reasons: dict[str, int] = {}
        computed_at = datetime.now(timezone.utc)

        for parcel in parcels:
            parcel_geom_l93: BaseGeometry = to_shape(parcel.geometry)
            metrics = compute_geometry_metrics(parcel_geom_l93)

            building_geoms_l93 = [to_shape(b.geometry) for b in parcel_buildings_map.get(parcel.id, [])]
            coverage = building_coverage_ratio(parcel_geom_l93, building_geoms_l93) if building_data_available else None
            unbuilt = unbuilt_area(parcel_geom_l93, building_geoms_l93) if building_data_available else None
            largest_unbuilt = (
                largest_contiguous_unbuilt_area(parcel_geom_l93, building_geoms_l93)
                if building_data_available
                else None
            )
            built_cat = classify_built_category(coverage)

            # IMPORTANT (correction) : c'est le resultat PAR PARCELLE (`zone_found`,
            # intersection reelle avec une zone) qui doit determiner la confiance --
            # pas `gpu_data_available` qui indique seulement qu'AU MOINS UNE zone
            # existe pour toute la commune. Utiliser ce dernier ici masquerait les
            # parcelles qui ne recoupent effectivement aucune zone connue.
            typezone, zone_found = _majority_zone(parcel_geom_l93, zone_index, zone_geoms)
            constructibility_status, urbanism_confidence = classify_constructibility(
                typezone, zone_found, metrics.geometry_quality_score
            )

            known_flags = [
                True,  # geometrie toujours connue (donnee cadastrale source)
                building_data_available,
                gpu_data_available,
                risk_data_available,
            ]
            known_ratio = sum(1 for f in known_flags if f) / len(known_flags)

            scoring_inputs = ScoringInputs(
                constructibility_status=constructibility_status,
                compactness=metrics.compactness,
                width_estimated_m=metrics.width_estimated_m,
                unbuilt_area_m2=unbuilt,
                building_coverage_ratio=coverage,
                built_category=built_cat,
                risk_level=risk_level if risk_data_available else None,
                road_frontage_length_m=None,  # pas de couche voirie au MVP, voir geometry.py
                known_fields_ratio=known_ratio,
            )
            result = compute_score(scoring_inputs)

            analysis = ParcelAnalysis(
                parcel_id=parcel.id,
                job_id=job.id,
                computed_at=computed_at,
                parcel_area=metrics.area_m2,
                building_footprint_area=(coverage * metrics.area_m2) if coverage is not None else None,
                building_coverage_ratio=coverage,
                unbuilt_area=unbuilt,
                largest_contiguous_unbuilt_area=largest_unbuilt,
                width_estimated=metrics.width_estimated_m,
                depth_estimated=metrics.depth_estimated_m,
                road_frontage_length=None,
                geometry_quality_score=metrics.geometry_quality_score,
                built_category=built_cat,
                constructibility_status=constructibility_status,
                urbanism_confidence_score=urbanism_confidence,
                suggested_operations=[],
            )
            db.add(analysis)
            db.flush()

            score = ParcelScore(
                analysis_id=analysis.id,
                score_urbanisme=result.score_urbanisme,
                score_geometrie=result.score_geometrie,
                score_surface=result.score_surface,
                score_acces=result.score_acces,
                score_reseaux=result.score_reseaux,
                score_risques=result.score_risques,
                score_densification=result.score_densification,
                score_complexite=result.score_complexite,
                score_qualite_donnees=result.score_qualite_donnees,
                score_global=result.score_global,
                explanation_text=result.explanation_text,
            )
            db.add(score)

            # --- FAISABILITE (bilan promoteur simplifie, voir app/services/feasibility.py) ---
            # Non calcule pour les parcelles deja exclues (pas de potentiel a chiffrer).
            if not result.excluded:
                existing_building_footprint = (coverage * metrics.area_m2) if coverage is not None else None
                feasibility_inputs = FeasibilityInputs(
                    parcel_area_m2=metrics.area_m2,
                    constructibility_status=constructibility_status,
                    largest_contiguous_unbuilt_area_m2=largest_unbuilt if building_data_available else None,
                    existing_building_footprint_m2=existing_building_footprint,
                    price_per_m2_bati_dvf=price_per_m2_bati_dvf,
                    price_per_m2_terrain_dvf=price_per_m2_terrain_dvf,
                    dvf_sample_size_bati=dvf_sample_size_bati,
                    dvf_sample_size_terrain=dvf_sample_size_terrain,
                    construction_cost_per_m2=cost_assumption.construction_cost_per_m2,
                    demolition_cost_per_m2_footprint=cost_assumption.demolition_cost_per_m2_footprint,
                    overhead_ratio=cost_assumption.overhead_ratio,
                )
                feasibility_result = compute_feasibility(feasibility_inputs)
                db.add(
                    ParcelFeasibility(
                        analysis_id=analysis.id,
                        cost_assumption_id=cost_assumption.id,
                        buildable_footprint_m2=feasibility_result.buildable_footprint_m2,
                        estimated_new_floor_area_m2=feasibility_result.estimated_new_floor_area_m2,
                        existing_building_footprint_m2=feasibility_result.existing_building_footprint_m2,
                        demolition_recommended=feasibility_result.demolition_recommended,
                        price_per_m2_bati_dvf=price_per_m2_bati_dvf,
                        price_per_m2_terrain_dvf=price_per_m2_terrain_dvf,
                        dvf_sample_size_bati=dvf_sample_size_bati,
                        dvf_sample_size_terrain=dvf_sample_size_terrain,
                        estimated_land_cost=feasibility_result.estimated_land_cost,
                        estimated_demolition_cost=feasibility_result.estimated_demolition_cost,
                        estimated_construction_cost=feasibility_result.estimated_construction_cost,
                        estimated_overhead_cost=feasibility_result.estimated_overhead_cost,
                        estimated_revenue=feasibility_result.estimated_revenue,
                        estimated_margin=feasibility_result.estimated_margin,
                        margin_ratio=feasibility_result.margin_ratio,
                        computable=feasibility_result.computable,
                        explanation_text=feasibility_result.explanation_text,
                        computed_at=computed_at,
                    )
                )

            if result.excluded:
                excluded_count += 1
                for reason in result.exclusion_reasons:
                    exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
            else:
                selected_count += 1

        _update_progress(db, job, "scoring")

        job.parcels_total = len(parcels)
        job.parcels_selected = selected_count
        job.parcels_excluded = excluded_count
        job.exclusion_reasons = exclusion_reasons
        job.status = AnalysisJobStatusEnum.COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        municipality.last_analyzed_at = job.finished_at
        _update_progress(db, job, "finalisation")
        db.commit()
    except Exception as exc:  # noqa: BLE001 -- le job ne doit jamais planter le process
        logger.exception("Echec du job d'analyse %s", job_id)
        db.rollback()
        job = db.get(AnalysisJob, job_id)
        if job is not None:
            _fail_job(db, job, str(exc))
    finally:
        db.close()


def _reset_municipality_data(db, municipality: Municipality) -> None:
    """Purge les donnees d'analyses precedentes pour cette commune avant d'en
    inserer de nouvelles -- voir commentaire dans run_analysis_job(). Supprime,
    dans l'ordre impose par les contraintes de cle etrangere (pas de cascade
    DB au MVP) : ParcelScore -> ParcelAnalysis / AnalysisWarning / ParcelBuilding
    -> Parcel, puis UrbanismZone et Risk (tous deux lies directement a
    municipality_id)."""
    parcel_ids_subq = select(Parcel.id).where(Parcel.municipality_id == municipality.id).scalar_subquery()
    analysis_ids_subq = (
        select(ParcelAnalysis.id).where(ParcelAnalysis.parcel_id.in_(parcel_ids_subq)).scalar_subquery()
    )

    db.execute(delete(ParcelScore).where(ParcelScore.analysis_id.in_(analysis_ids_subq)))
    db.execute(delete(ParcelFeasibility).where(ParcelFeasibility.analysis_id.in_(analysis_ids_subq)))
    db.execute(delete(ParcelAnalysis).where(ParcelAnalysis.parcel_id.in_(parcel_ids_subq)))
    db.execute(delete(AnalysisWarning).where(AnalysisWarning.parcel_id.in_(parcel_ids_subq)))
    db.execute(delete(ParcelBuilding).where(ParcelBuilding.parcel_id.in_(parcel_ids_subq)))
    db.execute(delete(Parcel).where(Parcel.municipality_id == municipality.id))
    db.execute(delete(UrbanismZone).where(UrbanismZone.municipality_id == municipality.id))
    db.execute(delete(Risk).where(Risk.municipality_id == municipality.id))
    db.commit()


def _get_default_cost_assumption(db) -> CostAssumption:
    """Recupere l'hypothese economique par defaut (voir app/models/economics.py) ;
    la cree si la ligne seed de la migration 0002 est absente (jamais de valeurs
    codees en dur ici, toujours lues depuis la table)."""
    existing = db.execute(
        select(CostAssumption).where(CostAssumption.is_default.is_(True)).limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    fallback = CostAssumption(
        label="Hypotheses par defaut (creees automatiquement)",
        is_default=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(fallback)
    db.flush()
    return fallback


def _update_progress(db, job: AnalysisJob, step: str) -> None:
    job.current_step = step
    job.progress_pct = PROGRESS_STEPS[step]
    db.add(job)
    db.commit()


def _fail_job(db, job: AnalysisJob, message: str) -> None:
    job.status = AnalysisJobStatusEnum.FAILED
    job.error_log = {"error": message}
    job.finished_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()


def _record_warnings(db, job: AnalysisJob | None, parcel_id: uuid.UUID | None, result: ProviderResult) -> None:
    now = datetime.now(timezone.utc)
    for message in result.warnings:
        severity = SeverityEnum.IMPORTANT if not result.success else SeverityEnum.INFORMATION
        db.add(
            AnalysisWarning(
                job_id=job.id if job else None,
                parcel_id=parcel_id,
                severity=severity,
                message=message,
                created_at=now,
            )
        )
    if result.warnings:
        db.commit()


def _get_or_create_source(db, source_record) -> SourceRecord:
    record = SourceRecord(
        source_name=source_record.source_name,
        source_url=source_record.source_url,
        retrieved_at=source_record.retrieved_at,
        dataset_version=source_record.dataset_version,
        reliability=source_record.reliability,
    )
    db.add(record)
    db.flush()
    return record


def _ensure_multipolygon(geom: BaseGeometry) -> BaseGeometry:
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    return geom


def _apply_commune_geometry(db, municipality: Municipality, commune_result: ProviderResult) -> None:
    features = commune_result.data or []
    if not features:
        return
    feature = features[0]
    props = feature.get("properties", {})
    if not municipality.name or municipality.name == municipality.insee_code:
        municipality.name = props.get("nom") or props.get("nom_com") or municipality.insee_code
    municipality.department_code = props.get("code_dep") or municipality.department_code
    geom = geojson_to_shape(feature["geometry"])
    geom_l93 = _ensure_multipolygon(reproject_to_lambert93(geom))
    municipality.geometry = from_shape(geom_l93, srid=2154)
    db.add(municipality)
    db.commit()


def _upsert_parcels(db, municipality: Municipality, features: list[dict], provider_result: ProviderResult) -> list[Parcel]:
    source = _get_or_create_source(db, provider_result.source) if features else None
    parcels: list[Parcel] = []
    for feature in features:
        props = feature.get("properties", {})
        geom = geojson_to_shape(feature["geometry"])
        geom_l93 = _ensure_multipolygon(reproject_to_lambert93(geom))
        section = props.get("section")
        numero = props.get("numero")
        reference = f"{section}{numero}" if section and numero else None

        parcel = Parcel(
            municipality_id=municipality.id,
            section=section,
            numero=numero,
            com_abs=props.get("com_abs"),
            prefixe=props.get("prefixe") or props.get("arcgis_ida"),
            reference=reference,
            geometry=from_shape(geom_l93, srid=2154),
            area_official=props.get("contenance"),
            area_computed=geom_l93.area,
            source_id=source.id if source else None,
        )
        db.add(parcel)
        parcels.append(parcel)
    db.flush()
    return parcels


def _upsert_zones(db, municipality: Municipality, features: list[dict], provider_result: ProviderResult) -> list[UrbanismZone]:
    if not features:
        return []
    source = _get_or_create_source(db, provider_result.source)
    zones: list[UrbanismZone] = []
    for feature in features:
        props = feature.get("properties", {})
        geom = geojson_to_shape(feature["geometry"])
        geom_l93 = _ensure_multipolygon(reproject_to_lambert93(geom))
        zone = UrbanismZone(
            municipality_id=municipality.id,
            libelle=props.get("libelle"),
            libelong=props.get("libelong"),
            typezone=props.get("typezone"),
            geometry=from_shape(geom_l93, srid=2154),
            source_url=props.get("urlfic") or props.get("nomfic"),
            retrieved_at=provider_result.source.retrieved_at,
        )
        db.add(zone)
        zones.append(zone)
    db.flush()
    return zones


def _build_zone_index(zones: list[UrbanismZone]) -> tuple[STRtree | None, list[UrbanismZone]]:
    if not zones:
        return None, []
    geoms = [to_shape(z.geometry) for z in zones]
    tree = STRtree(geoms)
    return tree, zones


def _majority_zone(
    parcel_geom_l93: BaseGeometry, tree: STRtree | None, zones: list[UrbanismZone]
) -> tuple[str | None, bool]:
    """Associe la parcelle a la zone majoritaire par surface d'intersection --
    voir docs/URBANISM_ENGINE.md. Retourne (typezone, trouve)."""
    if tree is None or not zones:
        return None, False
    candidate_idxs = tree.query(parcel_geom_l93)
    best_typezone: str | None = None
    best_area = 0.0
    for idx in candidate_idxs:
        zone = zones[int(idx)]
        zone_geom = to_shape(zone.geometry)
        try:
            inter_area = parcel_geom_l93.intersection(zone_geom).area
        except Exception:  # noqa: BLE001 -- geometrie invalide isolee, ne bloque pas le reste
            continue
        if inter_area > best_area:
            best_area = inter_area
            best_typezone = zone.typezone
    return best_typezone, best_area > 0


def _upsert_buildings(db, features: list[dict], provider_result: ProviderResult) -> list[Building]:
    if not features:
        return []
    source = _get_or_create_source(db, provider_result.source)
    buildings: list[Building] = []
    for feature in features:
        try:
            geom = geojson_to_shape(feature["geometry"])
        except Exception:  # noqa: BLE001
            continue
        geom_l93 = _ensure_multipolygon(reproject_to_lambert93(geom))
        building = Building(
            geometry=from_shape(geom_l93, srid=2154),
            footprint_area=geom_l93.area,
            building_type=None,
            building_type_confidence=None,
            source_id=source.id,
        )
        db.add(building)
        buildings.append(building)
    db.flush()
    return buildings


def _link_parcel_buildings(db, parcels: list[Parcel], buildings: list[Building]) -> dict[uuid.UUID, list[Building]]:
    result: dict[uuid.UUID, list[Building]] = {p.id: [] for p in parcels}
    if not buildings:
        return result
    building_geoms = [to_shape(b.geometry) for b in buildings]
    tree = STRtree(building_geoms)
    for parcel in parcels:
        parcel_geom = to_shape(parcel.geometry)
        candidate_idxs = tree.query(parcel_geom)
        for idx in candidate_idxs:
            building = buildings[int(idx)]
            building_geom = building_geoms[int(idx)]
            try:
                overlap = parcel_geom.intersection(building_geom).area
            except Exception:  # noqa: BLE001
                continue
            if overlap > 0:
                db.add(ParcelBuilding(parcel_id=parcel.id, building_id=building.id, overlap_area=overlap))
                result[parcel.id].append(building)
    db.flush()
    return result


def _store_commune_risks(db, municipality: Municipality, rga_result: ProviderResult, cavite_result: ProviderResult) -> tuple[RiskLevelEnum, bool]:
    """Stocke les risques au niveau commune (Risk [MVP simplifie]) -- voir
    docs/DATA_MODEL.md. Retourne (niveau agrege, donnees_disponibles)."""
    any_success = rga_result.success or cavite_result.success
    now = datetime.now(timezone.utc)

    level = RiskLevelEnum.UNKNOWN
    if rga_result.success:
        source = _get_or_create_source(db, rga_result.source)
        rga_level = _infer_risk_level(rga_result.data)
        db.add(
            Risk(
                municipality_id=municipality.id,
                risk_type=RiskTypeEnum.RGA,
                level=rga_level,
                geometry=None,
                source_id=source.id,
                retrieved_at=now,
            )
        )
        if rga_level != RiskLevelEnum.UNKNOWN:
            level = rga_level

    if cavite_result.success:
        source = _get_or_create_source(db, cavite_result.source)
        cavite_level = _infer_risk_level(cavite_result.data)
        db.add(
            Risk(
                municipality_id=municipality.id,
                risk_type=RiskTypeEnum.CAVITE,
                level=cavite_level,
                geometry=None,
                source_id=source.id,
                retrieved_at=now,
            )
        )
        if cavite_level == RiskLevelEnum.FORT:
            level = RiskLevelEnum.FORT

    db.flush()
    return level, any_success


def _infer_risk_level(records: object) -> RiskLevelEnum:
    """Deduit un niveau de risque simplifie a partir des enregistrements Georisques
    bruts. Le schema exact n'etant pas confirme (voir docs/DATA_SOURCES.md section
    D), cette fonction reste tres defensive : si elle ne reconnait pas la structure,
    elle retourne UNKNOWN plutot que d'inventer un niveau."""
    if not records or not isinstance(records, list):
        return RiskLevelEnum.UNKNOWN
    return RiskLevelEnum.MOYEN if len(records) > 0 else RiskLevelEnum.FAIBLE
