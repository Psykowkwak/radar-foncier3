"""Calculs geometriques (Shapely) -- voir docs/ARCHITECTURE.md principe directeur
("SI UNE INFORMATION PEUT ETRE CALCULEE -> LA CALCULER") et docs/DATA_MODEL.md.

IMPORTANT : tout calcul de surface/distance est fait en Lambert-93 (EPSG:2154,
metrique), jamais en WGS84 (EPSG:4326, degres) -- voir contrainte impérative n°3 du
cahier des charges. Les geometries recues des connecteurs (GeoJSON IGN) sont en
EPSG:4326 ; ce module reprojette systematiquement avant tout calcul.
"""
from __future__ import annotations

from dataclasses import dataclass

import pyproj
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform, unary_union

WGS84 = "EPSG:4326"
LAMBERT93 = "EPSG:2154"

_to_l93 = pyproj.Transformer.from_crs(WGS84, LAMBERT93, always_xy=True).transform
_to_wgs84 = pyproj.Transformer.from_crs(LAMBERT93, WGS84, always_xy=True).transform


def reproject_to_lambert93(geometry: BaseGeometry) -> BaseGeometry:
    """Reprojette une geometrie Shapely de EPSG:4326 vers EPSG:2154."""
    return transform(_to_l93, geometry)


def reproject_to_wgs84(geometry: BaseGeometry) -> BaseGeometry:
    """Reprojette une geometrie Shapely de EPSG:2154 vers EPSG:4326 (export API/carte)."""
    return transform(_to_wgs84, geometry)


def geojson_to_shape(geojson_geometry: dict) -> BaseGeometry:
    """Convertit une geometrie GeoJSON (dict) en objet Shapely."""
    return shape(geojson_geometry)


# --- Seuils de qualite geometrique (documentes, configurables) ---
MIN_PLAUSIBLE_AREA_M2 = 5.0  # en dessous : geometrie suspecte (bruit numerique / erreur source)
MAX_PLAUSIBLE_AREA_M2 = 5_000_000.0  # au dessus : parcelle atypique (bois, grand domaine)


@dataclass
class GeometryMetrics:
    """Resultat des calculs geometriques pour une parcelle, en Lambert-93."""

    area_m2: float
    perimeter_m: float
    compactness: float  # indice de Polsby-Popper : 4*pi*aire/perimetre^2, 1 = cercle parfait
    width_estimated_m: float
    depth_estimated_m: float
    geometry_quality_score: float  # 0-100, voir _compute_quality_score


def compute_area(geometry_l93: BaseGeometry) -> float:
    """Surface en m2 (geometrie deja en Lambert-93)."""
    return float(geometry_l93.area)


def compute_perimeter(geometry_l93: BaseGeometry) -> float:
    """Perimetre en m (geometrie deja en Lambert-93)."""
    return float(geometry_l93.length)


def compute_compactness(area_m2: float, perimeter_m: float) -> float:
    """Indice de Polsby-Popper (0 a 1) : 4*pi*aire / perimetre^2.

    1.0 = cercle parfait (forme la plus compacte). Une parcelle en L ou en drapeau
    aura un indice nettement plus bas -- utilise par score_geometrie.
    """
    if perimeter_m <= 0:
        return 0.0
    import math

    return float(4 * math.pi * area_m2 / (perimeter_m**2))


def estimate_width_depth(geometry_l93: BaseGeometry) -> tuple[float, float]:
    """Estime largeur/profondeur via le rectangle englobant oriente minimal
    (`minimum_rotated_rectangle`). Ce n'est qu'une approximation -- une parcelle en
    L n'a pas de largeur/profondeur "vraies", voir docs/URBANISM_ENGINE.md et
    FEASIBILITY_ENGINE.md pour les limites assumees de cette methode au MVP.

    Retourne (min_side, max_side) du rectangle englobant, en metres.
    """
    mrr = geometry_l93.minimum_rotated_rectangle
    coords = list(mrr.exterior.coords)
    if len(coords) < 4:
        return (0.0, 0.0)
    side_lengths = []
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        side_lengths.append(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    # Un rectangle a 4 cotes distincts dans coords (5 points, dont le dernier = premier) :
    # les cotes opposes sont egaux deux a deux -- on garde les deux longueurs uniques.
    unique_sides = sorted(set(round(s, 3) for s in side_lengths[:4]))
    if len(unique_sides) == 1:
        return (unique_sides[0], unique_sides[0])
    return (unique_sides[0], unique_sides[-1])


def _compute_quality_score(geometry_l93: BaseGeometry, area_m2: float) -> float:
    """Score de qualite geometrique 0-100 : penalise les geometries invalides,
    vides, ou de surface suspecte. Purement technique (pas d'urbanisme ici)."""
    score = 100.0
    if not geometry_l93.is_valid:
        score -= 40.0
    if geometry_l93.is_empty:
        return 0.0
    if area_m2 < MIN_PLAUSIBLE_AREA_M2:
        score -= 30.0
    if area_m2 > MAX_PLAUSIBLE_AREA_M2:
        score -= 10.0
    return max(0.0, min(100.0, score))


def compute_geometry_metrics(geometry_l93: BaseGeometry) -> GeometryMetrics:
    """Calcule l'ensemble des metriques geometriques de base d'une parcelle (Lambert-93)."""
    area = compute_area(geometry_l93)
    perimeter = compute_perimeter(geometry_l93)
    compactness = compute_compactness(area, perimeter)
    width, depth = estimate_width_depth(geometry_l93)
    quality = _compute_quality_score(geometry_l93, area)
    return GeometryMetrics(
        area_m2=area,
        perimeter_m=perimeter,
        compactness=compactness,
        width_estimated_m=width,
        depth_estimated_m=depth,
        geometry_quality_score=quality,
    )


def building_coverage_ratio(parcel_geometry_l93: BaseGeometry, building_geometries_l93: list[BaseGeometry]) -> float:
    """Ratio emprise batie / surface parcelle, borne [0, 1]."""
    parcel_area = compute_area(parcel_geometry_l93)
    if parcel_area <= 0:
        return 0.0
    if not building_geometries_l93:
        return 0.0
    buildings_union = unary_union(building_geometries_l93)
    intersection = parcel_geometry_l93.intersection(buildings_union)
    footprint = compute_area(intersection)
    return max(0.0, min(1.0, footprint / parcel_area))


def unbuilt_area(parcel_geometry_l93: BaseGeometry, building_geometries_l93: list[BaseGeometry]) -> float:
    """Surface non batie de la parcelle (m2)."""
    if not building_geometries_l93:
        return compute_area(parcel_geometry_l93)
    buildings_union = unary_union(building_geometries_l93)
    remainder = parcel_geometry_l93.difference(buildings_union)
    return compute_area(remainder)


def largest_contiguous_unbuilt_area(parcel_geometry_l93: BaseGeometry, building_geometries_l93: list[BaseGeometry]) -> float:
    """Plus grande surface non batie d'un seul tenant (m2) -- utile pour juger de la
    faisabilite d'une extension/construction neuve meme sur une parcelle partiellement
    batie (built_category PARTIALLY_BUILT / REDEVELOPMENT_POTENTIAL)."""
    if not building_geometries_l93:
        return compute_area(parcel_geometry_l93)
    buildings_union = unary_union(building_geometries_l93)
    remainder = parcel_geometry_l93.difference(buildings_union)
    if remainder.is_empty:
        return 0.0
    geoms = list(remainder.geoms) if hasattr(remainder, "geoms") else [remainder]
    return max((compute_area(g) for g in geoms), default=0.0)


def road_frontage_length(parcel_geometry_l93: BaseGeometry, road_geometries_l93: list[BaseGeometry] | None) -> float | None:
    """Longueur de contact avec une voie (m). Retourne None (jamais 0 ni une valeur
    optimiste) tant que la couche voirie n'est pas disponible -- explicitement HORS
    MVP (docs/DATA_MODEL.md, table Road [V1]). Voir docs/SCORING_ENGINE.md :
    score_acces reste alors calcule en version simplifiee (documentee separement).
    """
    if not road_geometries_l93:
        return None
    roads_union = unary_union(road_geometries_l93)
    boundary = parcel_geometry_l93.boundary
    intersection = boundary.intersection(roads_union)
    if intersection.is_empty:
        return 0.0
    return float(intersection.length)
