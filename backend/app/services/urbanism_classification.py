"""constructibility_status MVP -- matrice deterministe simplifiee, voir
docs/URBANISM_ENGINE.md section "MVP reel" :

"Au MVP, seule la classification par zone (typezone/prefixe de libelle : U*, AU*,
A*, N*) est utilisee pour un constructibility_status de premier niveau, marque
urbanism_confidence_score plafonne a 60 tant que le reglement ecrit n'est pas
analyse. L'extraction PDF + interpretation IA est V1 -- elle n'est PAS simulee ni
approximee par des valeurs par defaut au MVP."

Aucun appel LLM ici (voir docs/URBANISM_ENGINE.md "Constructibilite -- matrice de
decision (deterministe, pas de LLM)").
"""
from __future__ import annotations

from app.models.enums import ConstructibilityStatusEnum

# Confiance plafonnee au MVP : le reglement ecrit (PDF) n'est pas analyse, seule la
# classification par prefixe de zone est disponible.
MVP_MAX_CONFIDENCE = 60.0
NO_DOCUMENT_CONFIDENCE = 20.0
ZONE_AN_CONFIDENCE = 50.0  # heuristique sur prefixe seul, pas de verification de "secteur constructible"

# Seuil de qualite geometrique en dessous duquel on retient FAVORABLE_SOUS_CONDITIONS
# plutot que FAVORABLE (geometrie douteuse -> prudence), voir app/services/geometry.py
GEOMETRY_QUALITY_THRESHOLD_FOR_FAVORABLE = 60.0


def classify_constructibility(
    typezone: str | None,
    gpu_zone_found: bool,
    geometry_quality_score: float | None,
) -> tuple[ConstructibilityStatusEnum, float]:
    """Applique la matrice MVP simplifiee.

    - gpu_zone_found=False : aucune zone GPU associee a la parcelle (ni la commune,
      ni par intersection) => DONNEES_INSUFFISANTES, JAMAIS FAVORABLE par defaut
      (voir avertissement officiel GPU dans docs/DATA_SOURCES.md : l'absence de
      resultat ne signifie pas l'absence de document).
    - typezone renseigne : on ne regarde que le premier caractere (U/AU/A/N),
      heuristique explicitement documentee comme MVP (pas de lecture du reglement).

    Retourne (status, confidence 0-100), confidence toujours <= MVP_MAX_CONFIDENCE.
    """
    if not gpu_zone_found or not typezone:
        return ConstructibilityStatusEnum.DONNEES_INSUFFISANTES, NO_DOCUMENT_CONFIDENCE

    normalized = typezone.strip().upper()
    prefix = normalized[:1]

    # IMPORTANT : tester "AU" avant le test generique du prefixe "A", sinon une zone
    # a urbaniser (AU) serait a tort classee comme agricole (A).
    if normalized.startswith("AU") or prefix == "U":
        confidence = MVP_MAX_CONFIDENCE
        if geometry_quality_score is None or geometry_quality_score < GEOMETRY_QUALITY_THRESHOLD_FOR_FAVORABLE:
            return ConstructibilityStatusEnum.FAVORABLE_SOUS_CONDITIONS, confidence
        return ConstructibilityStatusEnum.FAVORABLE, confidence

    if prefix in ("A", "N"):
        # Heuristique sur prefixe seul : pas de verification d'un "secteur
        # constructible" (STECAL etc.) au MVP -- confiance volontairement modeste.
        return ConstructibilityStatusEnum.A_PRIORI_NON_CONSTRUCTIBLE, ZONE_AN_CONFIDENCE

    # Prefixe non reconnu (zone speciale, typezone atypique) : on ne tranche pas.
    return ConstructibilityStatusEnum.DONNEES_INSUFFISANTES, NO_DOCUMENT_CONFIDENCE
