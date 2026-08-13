"""Tests unitaires de la classification built_category -- voir
app/services/built_category.py et docs/DATA_MODEL.md."""
from __future__ import annotations

from app.models.enums import BuiltCategoryEnum
from app.services.built_category import classify_built_category


def test_none_ratio_returns_none():
    assert classify_built_category(None) is None


def test_zero_ratio_is_vacant_land():
    assert classify_built_category(0.0) == BuiltCategoryEnum.VACANT_LAND


def test_low_ratio_is_lightly_built():
    assert classify_built_category(0.05) == BuiltCategoryEnum.LIGHTLY_BUILT


def test_mid_ratio_is_partially_built():
    assert classify_built_category(0.25) == BuiltCategoryEnum.PARTIALLY_BUILT


def test_high_ratio_is_heavily_built():
    assert classify_built_category(0.5) == BuiltCategoryEnum.HEAVILY_BUILT


def test_very_high_ratio_is_fully_developed():
    assert classify_built_category(0.8) == BuiltCategoryEnum.FULLY_DEVELOPED


def test_extreme_ratio_is_redevelopment_potential():
    assert classify_built_category(0.9) == BuiltCategoryEnum.REDEVELOPMENT_POTENTIAL


def test_boundary_values_are_inclusive_on_upper_bound():
    assert classify_built_category(0.10) == BuiltCategoryEnum.LIGHTLY_BUILT
    assert classify_built_category(0.40) == BuiltCategoryEnum.PARTIALLY_BUILT
    assert classify_built_category(0.70) == BuiltCategoryEnum.HEAVILY_BUILT
    assert classify_built_category(0.85) == BuiltCategoryEnum.FULLY_DEVELOPED
