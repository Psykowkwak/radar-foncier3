"""Tests unitaires des calculs geometriques -- valeurs attendues calculees a la main
pour des formes simples (voir tests/conftest.py pour le detail des fixtures)."""
from __future__ import annotations

import math

import pytest

from app.services.geometry import (
    building_coverage_ratio,
    compute_area,
    compute_compactness,
    compute_perimeter,
    estimate_width_depth,
    largest_contiguous_unbuilt_area,
    unbuilt_area,
)


def test_rectangle_area(rectangular_parcel):
    assert compute_area(rectangular_parcel) == pytest.approx(600.0)


def test_rectangle_perimeter(rectangular_parcel):
    assert compute_perimeter(rectangular_parcel) == pytest.approx(100.0)


def test_rectangle_compactness(rectangular_parcel):
    area = compute_area(rectangular_parcel)
    perimeter = compute_perimeter(rectangular_parcel)
    expected = 4 * math.pi * 600.0 / (100.0**2)
    assert compute_compactness(area, perimeter) == pytest.approx(expected)
    assert compute_compactness(area, perimeter) == pytest.approx(0.753982, rel=1e-4)


def test_rectangle_width_depth(rectangular_parcel):
    width, depth = estimate_width_depth(rectangular_parcel)
    assert width == pytest.approx(20.0)
    assert depth == pytest.approx(30.0)


def test_l_shape_area(l_shaped_parcel):
    # 30x15 (bas) + 15x15 (haut-gauche) = 450 + 225 = 675
    assert compute_area(l_shaped_parcel) == pytest.approx(675.0)


def test_l_shape_perimeter(l_shaped_parcel):
    assert compute_perimeter(l_shaped_parcel) == pytest.approx(120.0)


def test_l_shape_less_compact_than_rectangle(rectangular_parcel, l_shaped_parcel):
    rect_compactness = compute_compactness(compute_area(rectangular_parcel), compute_perimeter(rectangular_parcel))
    l_compactness = compute_compactness(compute_area(l_shaped_parcel), compute_perimeter(l_shaped_parcel))
    assert l_compactness == pytest.approx(0.58905, rel=1e-3)
    assert l_compactness < rect_compactness


def test_narrow_strip_width_below_threshold(narrow_strip_parcel):
    width, depth = estimate_width_depth(narrow_strip_parcel)
    assert width == pytest.approx(3.0)
    assert depth == pytest.approx(50.0)
    assert width < 4.0  # seuil "parcelle en drapeau probable", voir docs/SCORING_ENGINE.md


def test_narrow_strip_area_and_compactness(narrow_strip_parcel):
    area = compute_area(narrow_strip_parcel)
    perimeter = compute_perimeter(narrow_strip_parcel)
    assert area == pytest.approx(150.0)
    assert perimeter == pytest.approx(106.0)
    compactness = compute_compactness(area, perimeter)
    expected = 4 * math.pi * 150.0 / (106.0**2)
    assert compactness == pytest.approx(expected)


def test_building_coverage_ratio(rectangular_parcel, small_building_inside_rectangle):
    ratio = building_coverage_ratio(rectangular_parcel, [small_building_inside_rectangle])
    assert ratio == pytest.approx(100.0 / 600.0)


def test_building_coverage_ratio_no_buildings(rectangular_parcel):
    assert building_coverage_ratio(rectangular_parcel, []) == 0.0


def test_unbuilt_area(rectangular_parcel, small_building_inside_rectangle):
    assert unbuilt_area(rectangular_parcel, [small_building_inside_rectangle]) == pytest.approx(500.0)


def test_unbuilt_area_no_buildings(rectangular_parcel):
    assert unbuilt_area(rectangular_parcel, []) == pytest.approx(600.0)


def test_largest_contiguous_unbuilt_area(rectangular_parcel, small_building_inside_rectangle):
    # Le batiment est entierement a l'interieur : le reste forme une seule region
    # (polygone avec un trou), donc la plus grande surface contigue = 600 - 100 = 500
    largest = largest_contiguous_unbuilt_area(rectangular_parcel, [small_building_inside_rectangle])
    assert largest == pytest.approx(500.0)
