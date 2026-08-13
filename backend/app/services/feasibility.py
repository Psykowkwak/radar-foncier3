"""Moteur de faisabilite simplifie (bilan promoteur) -- voir docs/FEASIBILITY_ENGINE.md.

Ce module N'EST PAS le moteur de faisabilite complet documente pour la V2 (pas
d'algorithme d'implantation de batiment sur plusieurs orientations, pas de
placement reel du stationnement, pas de plan de masse, pas de 3 scenarios
PRUDENT/CENTRAL/OPTIMISE). C'est une estimation d'ordre de grandeur de la marge
apparente d'une operation, construite pour repondre a un besoin concret : classer
les parcelles par potentiel economique REEL plutot que par simple score
d'urbanisme, pour eviter de faire remonter des parcelles ou une maison existante
couteuse a demolir ne laisse qu'un gain marginal.

Principe (voir docs/FEASIBILITY_ENGINE.md "Bilan promoteur" et "Garde-fous non
negociables") :

1. Surface constructible = le minimum entre la plus grande surface libre d'un seul
   tenant REELLEMENT mesuree (largest_contiguous_unbuilt_area, calculee a partir du
   bati IGN reel) et une hypothese GENERIQUE d'emprise au sol maximale par statut de
   constructibilite (faute de reglement PLU structure disponible a l'echelle
   nationale -- le "reglement ecrit" du PLU n'est diffuse qu'en PDF, non exploitable
   en masse ; voir docs/URBANISM_ENGINE.md). Cette hypothese est deliberement
   prudente et clairement etiquetee comme telle, jamais presentee comme le droit a
   construire reel de la parcelle.
2. Cout de demolition = emprise au sol du bati existant (IGN reel) x cout/m2
   parametrable (CostAssumption).
3. Cout de construction = surface de plancher neuve estimee x cout/m2 parametrable.
4. Recettes = surface de plancher neuve estimee x prix de vente reel au m2 (median
   des transactions DVF locales recentes, type Maison/Appartement).
5. Charge fonciere = surface totale de la parcelle x prix terrain reel au m2 (median
   DVF terrains nus locaux). Si aucun prix DVF terrain fiable n'existe (echantillon
   insuffisant), la charge fonciere est estimee via le prix bati DVF affecte d'un
   ratio prudent (les terrains valent typiquement une fraction du bati) -- toujours
   avec confidence marquee "estimee", jamais confondue avec une donnee mesuree.
6. Marge apparente = recettes - (charge fonciere + demolition + construction +
   overhead[VRD/honoraires/frais financiers/alea/marge cible]).

Si les donnees necessaires manquent (pas de bati IGN, pas de prix DVF exploitable),
`computable=False` : AUCUNE valeur n'est inventee, la parcelle sort du classement
"Top opportunites" plutot que d'afficher un chiffre fictif.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import ConstructibilityStatusEnum

# Hypothese GENERIQUE d'emprise au sol maximale par statut de constructibilite,
# faute de reglement PLU structure disponible nationalement -- volontairement
# prudente. A affiner commune par commune si un jour le reglement ecrit est
# exploite (voir docs/URBANISM_ENGINE.md, hors MVP).
MAX_FOOTPRINT_RATIO_BY_STATUS: dict[ConstructibilityStatusEnum, float] = {
    ConstructibilityStatusEnum.FAVORABLE: 0.35,
    ConstructibilityStatusEnum.FAVORABLE_SOUS_CONDITIONS: 0.25,
    ConstructibilityStatusEnum.COMPLEXE: 0.15,
    ConstructibilityStatusEnum.DEFAVORABLE: 0.0,
    ConstructibilityStatusEnum.A_PRIORI_NON_CONSTRUCTIBLE: 0.0,
    ConstructibilityStatusEnum.DONNEES_INSUFFISANTES: 0.15,  # prudent, jamais optimiste
}

# Hypothese GENERIQUE de nombre de niveaux (R+n) par statut -- meme reserve que
# ci-dessus. 1 niveau = plain-pied.
ASSUMED_FLOORS_BY_STATUS: dict[ConstructibilityStatusEnum, float] = {
    ConstructibilityStatusEnum.FAVORABLE: 2.0,
    ConstructibilityStatusEnum.FAVORABLE_SOUS_CONDITIONS: 1.5,
    ConstructibilityStatusEnum.COMPLEXE: 1.0,
    ConstructibilityStatusEnum.DEFAVORABLE: 0.0,
    ConstructibilityStatusEnum.A_PRIORI_NON_CONSTRUCTIBLE: 0.0,
    ConstructibilityStatusEnum.DONNEES_INSUFFISANTES: 1.0,
}

# Efficacite surface de plancher / emprise x niveaux (circulation, murs, etc.).
FLOOR_EFFICIENCY_RATIO = 0.85

# Ratio prudent prix terrain / prix bati quand aucun echantillon DVF terrain
# suffisant n'existe localement -- estimation degradee, toujours marquee comme
# telle (jamais confondue avec une donnee DVF mesuree).
FALLBACK_LAND_TO_BUILT_RATIO = 0.30

MIN_DEMOLITION_TRIGGER_RATIO = 0.10  # en dessous, la demolition n'est pas jugee necessaire


@dataclass
class FeasibilityInputs:
    parcel_area_m2: float
    constructibility_status: ConstructibilityStatusEnum
    largest_contiguous_unbuilt_area_m2: float | None  # None si bati non disponible
    existing_building_footprint_m2: float | None  # None si bati non disponible
    price_per_m2_bati_dvf: float | None
    price_per_m2_terrain_dvf: float | None
    dvf_sample_size_bati: int | None
    dvf_sample_size_terrain: int | None
    construction_cost_per_m2: float
    demolition_cost_per_m2_footprint: float
    overhead_ratio: float


@dataclass
class FeasibilityResult:
    computable: bool
    buildable_footprint_m2: float | None = None
    estimated_new_floor_area_m2: float | None = None
    existing_building_footprint_m2: float | None = None
    demolition_recommended: bool = False
    estimated_land_cost: float | None = None
    estimated_demolition_cost: float | None = None
    estimated_construction_cost: float | None = None
    estimated_overhead_cost: float | None = None
    estimated_revenue: float | None = None
    estimated_margin: float | None = None
    margin_ratio: float | None = None
    explanation_text: str = ""


def compute_feasibility(inputs: FeasibilityInputs) -> FeasibilityResult:
    max_ratio = MAX_FOOTPRINT_RATIO_BY_STATUS.get(inputs.constructibility_status, 0.0)
    assumed_floors = ASSUMED_FLOORS_BY_STATUS.get(inputs.constructibility_status, 0.0)

    if (
        max_ratio <= 0.0
        or inputs.largest_contiguous_unbuilt_area_m2 is None
        or inputs.price_per_m2_bati_dvf is None
    ):
        reasons = []
        if max_ratio <= 0.0:
            reasons.append("statut de constructibilite defavorable ou non constructible")
        if inputs.largest_contiguous_unbuilt_area_m2 is None:
            reasons.append("donnees bati (IGN BD TOPO) indisponibles pour cette commune")
        if inputs.price_per_m2_bati_dvf is None:
            reasons.append("aucun prix de vente DVF local suffisamment fiable")
        return FeasibilityResult(
            computable=False,
            explanation_text=(
                "Estimation economique non calculable : " + ", ".join(reasons) + "."
            ),
        )

    max_footprint_by_zone = inputs.parcel_area_m2 * max_ratio
    buildable_footprint = min(inputs.largest_contiguous_unbuilt_area_m2, max_footprint_by_zone)
    new_floor_area = buildable_footprint * assumed_floors * FLOOR_EFFICIENCY_RATIO

    if new_floor_area <= 0:
        return FeasibilityResult(
            computable=False,
            buildable_footprint_m2=buildable_footprint,
            explanation_text=(
                "Estimation economique non calculable : aucune surface constructible nette "
                "significative apres application de l'hypothese d'emprise generique."
            ),
        )

    existing_footprint = inputs.existing_building_footprint_m2 or 0.0
    demolition_recommended = existing_footprint > (inputs.parcel_area_m2 * MIN_DEMOLITION_TRIGGER_RATIO)
    demolition_cost = (
        existing_footprint * inputs.demolition_cost_per_m2_footprint if demolition_recommended else 0.0
    )

    construction_cost = new_floor_area * inputs.construction_cost_per_m2

    land_price_estimated = False
    if inputs.price_per_m2_terrain_dvf is not None:
        price_per_m2_terrain = inputs.price_per_m2_terrain_dvf
    else:
        price_per_m2_terrain = inputs.price_per_m2_bati_dvf * FALLBACK_LAND_TO_BUILT_RATIO
        land_price_estimated = True
    land_cost = inputs.parcel_area_m2 * price_per_m2_terrain

    revenue = new_floor_area * inputs.price_per_m2_bati_dvf
    overhead_cost = revenue * inputs.overhead_ratio

    total_cost = land_cost + demolition_cost + construction_cost + overhead_cost
    margin = revenue - total_cost
    margin_ratio = (margin / revenue) if revenue > 0 else None

    parts = [
        f"Surface constructible estimee : {buildable_footprint:.0f} m2 au sol "
        f"(hypothese generique d'emprise, statut {inputs.constructibility_status.value}), "
        f"soit {new_floor_area:.0f} m2 de plancher neuf sur {assumed_floors:.1f} niveau(x) estime(s)."
    ]
    if demolition_recommended:
        parts.append(f"Demolition de l'existant ({existing_footprint:.0f} m2 au sol) integree au cout.")
    parts.append(
        f"Prix de vente retenu : {inputs.price_per_m2_bati_dvf:.0f} EUR/m2 "
        f"(median DVF, {inputs.dvf_sample_size_bati or 0} transaction(s) locale(s))."
    )
    if land_price_estimated:
        parts.append(
            f"Charge fonciere estimee via un ratio prudent (echantillon DVF terrain insuffisant), "
            f"pas une donnee DVF mesuree."
        )
    else:
        parts.append(
            f"Charge fonciere basee sur {inputs.dvf_sample_size_terrain or 0} transaction(s) DVF terrain locale(s)."
        )
    parts.append(f"Marge apparente estimee : {margin:,.0f} EUR (hors financement, hors alea specifique).")
    parts.append(
        "Estimation d'ordre de grandeur, PAS un bilan promoteur bancable -- ne remplace pas une "
        "etude de faisabilite, un certificat d'urbanisme ou l'avis d'un architecte/geometre."
    )

    return FeasibilityResult(
        computable=True,
        buildable_footprint_m2=buildable_footprint,
        estimated_new_floor_area_m2=new_floor_area,
        existing_building_footprint_m2=existing_footprint if inputs.existing_building_footprint_m2 is not None else None,
        demolition_recommended=demolition_recommended,
        estimated_land_cost=land_cost,
        estimated_demolition_cost=demolition_cost,
        estimated_construction_cost=construction_cost,
        estimated_overhead_cost=overhead_cost,
        estimated_revenue=revenue,
        estimated_margin=margin,
        margin_ratio=margin_ratio,
        explanation_text=" ".join(parts),
    )
