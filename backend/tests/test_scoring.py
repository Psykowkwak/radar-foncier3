"""Tests des penalites/exclusions du moteur de scoring -- voir
app/services/scoring.py et docs/SCORING_ENGINE.md."""
from __future__ import annotations

from app.models.enums import BuiltCategoryEnum, ConstructibilityStatusEnum, RiskLevelEnum
from app.services.scoring import ScoringInputs, compute_score


def _baseline_inputs(**overrides) -> ScoringInputs:
    defaults = dict(
        constructibility_status=ConstructibilityStatusEnum.FAVORABLE,
        compactness=0.75,
        width_estimated_m=20.0,
        unbuilt_area_m2=800.0,
        building_coverage_ratio=0.1,
        built_category=BuiltCategoryEnum.LIGHTLY_BUILT,
        risk_level=RiskLevelEnum.FAIBLE,
        road_frontage_length_m=None,
        known_fields_ratio=1.0,
    )
    defaults.update(overrides)
    return ScoringInputs(**defaults)


def test_favorable_case_is_not_excluded_and_has_high_score():
    result = compute_score(_baseline_inputs())
    assert result.excluded is False
    assert result.score_global > 70.0


def test_non_constructible_is_excluded():
    result = compute_score(_baseline_inputs(constructibility_status=ConstructibilityStatusEnum.A_PRIORI_NON_CONSTRUCTIBLE))
    assert result.excluded is True
    assert result.score_global == 0.0
    assert any("A_PRIORI_NON_CONSTRUCTIBLE" in reason for reason in result.exclusion_reasons)


def test_narrow_width_triggers_penalty():
    baseline = compute_score(_baseline_inputs())
    narrow = compute_score(_baseline_inputs(width_estimated_m=3.0))
    assert narrow.excluded is False
    assert narrow.score_global < baseline.score_global
    assert any("drapeau" in p for p in narrow.penalties_applied)


def test_high_coverage_ratio_triggers_penalty():
    baseline = compute_score(_baseline_inputs())
    high_coverage = compute_score(
        _baseline_inputs(building_coverage_ratio=0.95, built_category=BuiltCategoryEnum.REDEVELOPMENT_POTENTIAL)
    )
    assert high_coverage.score_global < baseline.score_global
    assert any("emprise batie" in p for p in high_coverage.penalties_applied)


def test_no_road_contact_triggers_major_penalty():
    baseline = compute_score(_baseline_inputs())
    no_contact = compute_score(_baseline_inputs(road_frontage_length_m=0.0))
    assert no_contact.score_global < baseline.score_global
    assert any("Aucun contact avec voie" in p for p in no_contact.penalties_applied)


def test_unknown_road_frontage_does_not_trigger_penalty():
    """Donnee inconnue (None) != contact confirme nul (0.0) -- ne doit JAMAIS etre
    penalisee comme si l'absence de contact etait prouvee (voir principe directeur
    ARCHITECTURE.md : ne jamais inventer une donnee manquante)."""
    result = compute_score(_baseline_inputs(road_frontage_length_m=None))
    assert not any("Aucun contact avec voie" in p for p in result.penalties_applied)


def test_donnees_insuffisantes_caps_score_at_50():
    result = compute_score(
        _baseline_inputs(
            constructibility_status=ConstructibilityStatusEnum.DONNEES_INSUFFISANTES,
            compactness=0.95,
            unbuilt_area_m2=2000.0,
            built_category=BuiltCategoryEnum.VACANT_LAND,
        )
    )
    assert result.excluded is False
    assert result.score_global <= 50.0


def test_score_is_never_negative_or_above_100():
    worst_case = compute_score(
        _baseline_inputs(
            width_estimated_m=1.0,
            building_coverage_ratio=0.99,
            built_category=BuiltCategoryEnum.REDEVELOPMENT_POTENTIAL,
            road_frontage_length_m=0.0,
        )
    )
    assert 0.0 <= worst_case.score_global <= 100.0
