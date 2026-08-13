"""Moteur de scoring MVP -- voir docs/SCORING_ENGINE.md.

Calcule les 9 sous-scores (0-100), le score_global pondere, applique les
penalites/exclusions documentees, et genere un explanation_text deterministe
(AUCUN appel LLM au MVP -- voir docs/SCORING_ENGINE.md "Explication humaine du
score", etape 1 uniquement implementee ici).

Sous-scores reellement calcules a partir de donnees au MVP : score_urbanisme,
score_geometrie, score_surface, score_densification, score_qualite_donnees.
Sous-scores neutres/simplifies au MVP (documente explicitement, jamais invente) :
score_acces, score_reseaux, score_complexite toujours a 50 (DONNEES_INSUFFISANTES) ;
score_risques calcule si des donnees Georisques ont ete recuperees, sinon neutre 50.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import BuiltCategoryEnum, ConstructibilityStatusEnum, RiskLevelEnum

NEUTRAL_SCORE = 50.0  # valeur neutre documentee DONNEES_INSUFFISANTES, jamais 0 ni optimiste

DEFAULT_WEIGHTS: dict[str, float] = {
    "urbanisme": 0.20,
    "geometrie": 0.15,
    "surface": 0.15,
    "acces": 0.10,
    "reseaux": 0.05,
    "risques": 0.10,
    "densification": 0.15,
    "complexite": 0.05,
    "qualite_donnees": 0.05,
}

DEFAULT_PENALTIES: dict[str, dict] = {
    "zone_an_sans_secteur_constructible": {"exclude": True, "penalty": None},
    "risque_reglementaire_incompatible": {"exclude": True, "penalty": None},
    "aucun_contact_voie": {"exclude": False, "penalty": -40.0},
    "largeur_insuffisante": {"exclude": False, "penalty": -25.0, "threshold_m": 4.0},
    "coverage_ratio_eleve_sans_renouvellement": {"exclude": False, "penalty": -30.0, "threshold": 0.85},
    "non_constructible": {"exclude": True, "penalty": None},
    "donnees_insuffisantes_cap": {"exclude": False, "cap": 50.0},
}

# Score urbanisme (0-100) selon constructibility_status -- mapping deterministe
CONSTRUCTIBILITY_SCORE_MAP: dict[ConstructibilityStatusEnum, float] = {
    ConstructibilityStatusEnum.FAVORABLE: 90.0,
    ConstructibilityStatusEnum.FAVORABLE_SOUS_CONDITIONS: 70.0,
    ConstructibilityStatusEnum.COMPLEXE: 50.0,
    ConstructibilityStatusEnum.DEFAVORABLE: 20.0,
    ConstructibilityStatusEnum.A_PRIORI_NON_CONSTRUCTIBLE: 5.0,
    ConstructibilityStatusEnum.DONNEES_INSUFFISANTES: NEUTRAL_SCORE,
}

# Score densification (0-100) selon built_category -- vacant = potentiel maximal
BUILT_CATEGORY_SCORE_MAP: dict[BuiltCategoryEnum, float] = {
    BuiltCategoryEnum.VACANT_LAND: 100.0,
    BuiltCategoryEnum.LIGHTLY_BUILT: 85.0,
    BuiltCategoryEnum.PARTIALLY_BUILT: 65.0,
    BuiltCategoryEnum.REDEVELOPMENT_POTENTIAL: 55.0,
    BuiltCategoryEnum.HEAVILY_BUILT: 35.0,
    BuiltCategoryEnum.FULLY_DEVELOPED: 20.0,
}

RISK_LEVEL_SCORE_MAP: dict[RiskLevelEnum, float] = {
    RiskLevelEnum.FAIBLE: 90.0,
    RiskLevelEnum.MOYEN: 60.0,
    RiskLevelEnum.FORT: 15.0,
    RiskLevelEnum.UNKNOWN: NEUTRAL_SCORE,
}

# Seuils score_surface (m2 de surface libre / non batie) -- configurables
SURFACE_THRESHOLDS = [
    (1000.0, 95.0),
    (500.0, 80.0),
    (200.0, 60.0),
    (100.0, 40.0),
    (0.0, 20.0),
]


@dataclass
class ScoringInputs:
    """Toutes les donnees necessaires au scoring d'une parcelle -- assemblees par
    app/services/analysis_job.py a partir des connecteurs + calculs geometriques."""

    constructibility_status: ConstructibilityStatusEnum
    compactness: float | None  # 0-1, voir app/services/geometry.py
    width_estimated_m: float | None
    unbuilt_area_m2: float | None
    building_coverage_ratio: float | None
    built_category: BuiltCategoryEnum | None
    risk_level: RiskLevelEnum | None  # None si aucune donnee risque recuperee du tout
    road_frontage_length_m: float | None  # None = inconnu (pas de couche voirie au MVP)
    known_fields_ratio: float  # proportion de champs CONFIRMED/CALCULATED vs UNKNOWN, 0-1
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    penalties_config: dict[str, dict] = field(default_factory=lambda: dict(DEFAULT_PENALTIES))


@dataclass
class ScoringResult:
    score_urbanisme: float
    score_geometrie: float
    score_surface: float
    score_acces: float
    score_reseaux: float
    score_risques: float
    score_densification: float
    score_complexite: float
    score_qualite_donnees: float
    score_global: float
    excluded: bool
    exclusion_reasons: list[str]
    penalties_applied: list[str]
    explanation_text: str


def score_urbanisme(status: ConstructibilityStatusEnum) -> float:
    return CONSTRUCTIBILITY_SCORE_MAP.get(status, NEUTRAL_SCORE)


def score_geometrie(compactness: float | None, width_estimated_m: float | None) -> float:
    """Compacite (Polsby-Popper) x 100, penalisee si largeur estimee tres faible
    (indice de parcelle en drapeau) -- voir app/services/geometry.py."""
    if compactness is None:
        return NEUTRAL_SCORE
    base = max(0.0, min(100.0, compactness * 100.0))
    if width_estimated_m is not None and width_estimated_m < 4.0:
        base = max(0.0, base - 20.0)
    return base


def score_surface(unbuilt_area_m2: float | None) -> float:
    if unbuilt_area_m2 is None:
        return NEUTRAL_SCORE
    for threshold, value in SURFACE_THRESHOLDS:
        if unbuilt_area_m2 >= threshold:
            return value
    return SURFACE_THRESHOLDS[-1][1]


def score_densification(built_category: BuiltCategoryEnum | None) -> float:
    if built_category is None:
        return NEUTRAL_SCORE
    return BUILT_CATEGORY_SCORE_MAP.get(built_category, NEUTRAL_SCORE)


def score_risques(risk_level: RiskLevelEnum | None) -> float:
    """Neutre (50, DONNEES_INSUFFISANTES) si aucune donnee risque n'a ete recuperee
    du tout ; sinon mappe le niveau connu (potentiellement UNKNOWN => neutre aussi)."""
    if risk_level is None:
        return NEUTRAL_SCORE
    return RISK_LEVEL_SCORE_MAP.get(risk_level, NEUTRAL_SCORE)


def score_qualite_donnees(known_fields_ratio: float) -> float:
    return max(0.0, min(100.0, known_fields_ratio * 100.0))


def compute_score(inputs: ScoringInputs) -> ScoringResult:
    weights = inputs.weights
    penalties_config = inputs.penalties_config

    sub_scores = {
        "urbanisme": score_urbanisme(inputs.constructibility_status),
        "geometrie": score_geometrie(inputs.compactness, inputs.width_estimated_m),
        "surface": score_surface(inputs.unbuilt_area_m2),
        "acces": NEUTRAL_SCORE,  # DONNEES_INSUFFISANTES au MVP -- pas de couche voirie
        "reseaux": NEUTRAL_SCORE,  # DONNEES_INSUFFISANTES au MVP -- connecteurs reseaux = stub
        "risques": score_risques(inputs.risk_level),
        "densification": score_densification(inputs.built_category),
        "complexite": NEUTRAL_SCORE,  # DONNEES_INSUFFISANTES au MVP -- pas de UrbanismRuleSet
        "qualite_donnees": score_qualite_donnees(inputs.known_fields_ratio),
    }

    total_weight = sum(weights.values()) or 1.0
    weighted_score = sum(sub_scores[key] * weights.get(key, 0.0) for key in sub_scores) / total_weight

    excluded = False
    exclusion_reasons: list[str] = []
    penalties_applied: list[str] = []
    adjusted_score = weighted_score

    # Exclusion : zone A/N sans indice de secteur constructible.
    # Heuristique MVP : A_PRIORI_NON_CONSTRUCTIBLE couvre deja ce cas
    # (voir app/services/urbanism_classification.py) -- traite via la regle
    # "non_constructible" ci-dessous pour eviter la double comptabilisation.

    if inputs.constructibility_status == ConstructibilityStatusEnum.A_PRIORI_NON_CONSTRUCTIBLE:
        cfg = penalties_config.get("non_constructible", {"exclude": True})
        if cfg.get("exclude", True):
            excluded = True
            exclusion_reasons.append(
                "Statut de constructibilite A_PRIORI_NON_CONSTRUCTIBLE (zone A/N sans indice de secteur constructible)."
            )

    # Penalite forte : largeur estimee < seuil (parcelle en drapeau probable)
    largeur_cfg = penalties_config.get("largeur_insuffisante", DEFAULT_PENALTIES["largeur_insuffisante"])
    threshold_m = largeur_cfg.get("threshold_m", 4.0)
    if inputs.width_estimated_m is not None and inputs.width_estimated_m < threshold_m:
        adjusted_score += largeur_cfg.get("penalty", -25.0)
        penalties_applied.append(
            f"Largeur estimee ({inputs.width_estimated_m:.1f} m) < {threshold_m} m -- parcelle en drapeau probable."
        )

    # Penalite forte : building_coverage_ratio > seuil sans indice de renouvellement urbain.
    # "sans indice de renouvellement urbain" n'est pas mesure au MVP -- la penalite
    # s'applique donc systematiquement au-dela du seuil (hypothese documentee ici).
    coverage_cfg = penalties_config.get(
        "coverage_ratio_eleve_sans_renouvellement", DEFAULT_PENALTIES["coverage_ratio_eleve_sans_renouvellement"]
    )
    coverage_threshold = coverage_cfg.get("threshold", 0.85)
    if inputs.building_coverage_ratio is not None and inputs.building_coverage_ratio > coverage_threshold:
        adjusted_score += coverage_cfg.get("penalty", -30.0)
        penalties_applied.append(
            f"Taux d'emprise batie eleve ({inputs.building_coverage_ratio:.0%}) > {coverage_threshold:.0%}."
        )

    # Penalite majeure : aucun contact avec voie detecte ET aucune servitude connue.
    # Au MVP, road_frontage_length_m vaut quasi-toujours None (pas de couche voirie) --
    # cette penalite ne peut donc s'appliquer QUE si un contact nul a ete confirme
    # explicitement (0.0), jamais sur une simple absence de donnee.
    no_road_cfg = penalties_config.get("aucun_contact_voie", DEFAULT_PENALTIES["aucun_contact_voie"])
    if inputs.road_frontage_length_m is not None and inputs.road_frontage_length_m <= 0.0:
        adjusted_score += no_road_cfg.get("penalty", -40.0)
        penalties_applied.append("Aucun contact avec voie detecte (et aucune servitude de passage connue).")

    # Plafonnement : DONNEES_INSUFFISANTES => jamais classe "fort potentiel"
    if inputs.constructibility_status == ConstructibilityStatusEnum.DONNEES_INSUFFISANTES:
        cap = penalties_config.get("donnees_insuffisantes_cap", {"cap": 50.0}).get("cap", 50.0)
        if adjusted_score > cap:
            adjusted_score = cap
            penalties_applied.append(
                f"Score plafonne a {cap:.0f} : constructibilite DONNEES_INSUFFISANTES."
            )

    score_global = 0.0 if excluded else max(0.0, min(100.0, adjusted_score))

    explanation_text = _build_explanation_text(
        sub_scores=sub_scores,
        score_global=score_global,
        excluded=excluded,
        exclusion_reasons=exclusion_reasons,
        penalties_applied=penalties_applied,
        constructibility_status=inputs.constructibility_status,
        built_category=inputs.built_category,
    )

    return ScoringResult(
        score_urbanisme=sub_scores["urbanisme"],
        score_geometrie=sub_scores["geometrie"],
        score_surface=sub_scores["surface"],
        score_acces=sub_scores["acces"],
        score_reseaux=sub_scores["reseaux"],
        score_risques=sub_scores["risques"],
        score_densification=sub_scores["densification"],
        score_complexite=sub_scores["complexite"],
        score_qualite_donnees=sub_scores["qualite_donnees"],
        score_global=score_global,
        excluded=excluded,
        exclusion_reasons=exclusion_reasons,
        penalties_applied=penalties_applied,
        explanation_text=explanation_text,
    )


def _build_explanation_text(
    *,
    sub_scores: dict[str, float],
    score_global: float,
    excluded: bool,
    exclusion_reasons: list[str],
    penalties_applied: list[str],
    constructibility_status: ConstructibilityStatusEnum,
    built_category: BuiltCategoryEnum | None,
) -> str:
    """Assemble un texte deterministe (template Python, PAS de LLM) a partir des
    sous-scores reellement calcules -- voir docs/SCORING_ENGINE.md "Explication
    humaine du score", etape 1."""
    if excluded:
        reasons = " ".join(exclusion_reasons) or "Criteres d'exclusion atteints."
        return f"Parcelle exclue du classement. {reasons}"

    parts: list[str] = [f"Score global provisoire : {score_global:.0f}/100."]

    positive_labels = {
        "urbanisme": "urbanisme favorable",
        "geometrie": "geometrie compacte",
        "surface": "surface libre importante",
        "densification": "fort potentiel de densification",
        "qualite_donnees": "donnees de bonne qualite",
    }
    negative_labels = {
        "urbanisme": "urbanisme peu favorable ou incertain",
        "geometrie": "geometrie peu favorable (forme irreguliere)",
        "surface": "surface libre limitee",
        "densification": "potentiel de densification limite",
        "qualite_donnees": "donnees incompletes",
    }

    strengths = [label for key, label in positive_labels.items() if sub_scores.get(key, 0) >= 70]
    weaknesses = [label for key, label in negative_labels.items() if sub_scores.get(key, 0) < 40]

    if strengths:
        parts.append("Points forts : " + ", ".join(strengths) + ".")
    if weaknesses:
        parts.append("Points de vigilance : " + ", ".join(weaknesses) + ".")
    if penalties_applied:
        parts.append("Penalites appliquees : " + " ".join(penalties_applied))

    parts.append(f"Statut de constructibilite : {constructibility_status.value}.")
    if built_category is not None:
        parts.append(f"Categorie de bati : {built_category.value}.")

    parts.append(
        "Score provisoire MVP : score_acces, score_reseaux et score_complexite sont "
        "des valeurs neutres (donnees insuffisantes), pas encore alimentes par des "
        "connecteurs reels."
    )
    return " ".join(parts)
