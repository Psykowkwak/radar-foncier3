"""Classification built_category selon building_coverage_ratio -- voir docs/DATA_MODEL.md
(ParcelAnalysis.built_category) et docs/SCORING_ENGINE.md (score_densification).

Seuils par defaut, configurables (constantes ci-dessous, pas de valeur magique
eparpillee dans le code). Le seuil haut (0.85) est aligne avec la penalite
"building_coverage_ratio > 0.85 sans indice de renouvellement urbain" du moteur de
scoring (docs/SCORING_ENGINE.md) : au-dela, la parcelle est consideree comme un
potentiel de renouvellement urbain plutot que "pleinement developpee".
"""
from __future__ import annotations

from app.models.enums import BuiltCategoryEnum

# Seuils de ratio bati/parcelle (bornes hautes incluses)
THRESHOLD_VACANT = 0.0
THRESHOLD_LIGHTLY_BUILT = 0.10
THRESHOLD_PARTIALLY_BUILT = 0.40
THRESHOLD_HEAVILY_BUILT = 0.70
THRESHOLD_FULLY_DEVELOPED = 0.85
# Au-dela de THRESHOLD_FULLY_DEVELOPED => REDEVELOPMENT_POTENTIAL


def classify_built_category(building_coverage_ratio: float | None) -> BuiltCategoryEnum | None:
    """Retourne None si le ratio n'est pas connu (jamais une categorie par defaut
    optimiste ou pessimiste -- voir principe directeur ARCHITECTURE.md)."""
    if building_coverage_ratio is None:
        return None
    ratio = building_coverage_ratio
    if ratio <= THRESHOLD_VACANT:
        return BuiltCategoryEnum.VACANT_LAND
    if ratio <= THRESHOLD_LIGHTLY_BUILT:
        return BuiltCategoryEnum.LIGHTLY_BUILT
    if ratio <= THRESHOLD_PARTIALLY_BUILT:
        return BuiltCategoryEnum.PARTIALLY_BUILT
    if ratio <= THRESHOLD_HEAVILY_BUILT:
        return BuiltCategoryEnum.HEAVILY_BUILT
    if ratio <= THRESHOLD_FULLY_DEVELOPED:
        return BuiltCategoryEnum.FULLY_DEVELOPED
    return BuiltCategoryEnum.REDEVELOPMENT_POTENTIAL
