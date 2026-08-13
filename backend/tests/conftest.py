"""Fixtures partagees -- geometries de test reutilisables (Lambert-93, coordonnees
metriques simples pour permettre des calculs a la main).

Pas de fixture DB reelle ici : les tests unitaires (geometrie, categorie, scoring,
connecteurs) ne necessitent aucune base de donnees. Pour des tests d'integration
avec une vraie base PostGIS, utiliser `docker compose exec backend pytest` avec
DATABASE_URL pointant vers le service `db` (voir README.md).
"""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon


@pytest.fixture
def rectangular_parcel() -> Polygon:
    """Rectangle simple 20m x 30m = 600 m2, perimetre 100 m."""
    return Polygon([(0, 0), (20, 0), (20, 30), (0, 30), (0, 0)])


@pytest.fixture
def l_shaped_parcel() -> Polygon:
    """Parcelle en L : 30x15 (bas) + 15x15 (haut-gauche) = 675 m2, perimetre 120 m."""
    return Polygon([(0, 0), (30, 0), (30, 15), (15, 15), (15, 30), (0, 30), (0, 0)])


@pytest.fixture
def narrow_strip_parcel() -> Polygon:
    """Bande etroite type 'drapeau' : 3m x 50m = 150 m2, largeur 3m (< seuil 4m)."""
    return Polygon([(0, 0), (3, 0), (3, 50), (0, 50), (0, 0)])


@pytest.fixture
def small_building_inside_rectangle() -> Polygon:
    """Batiment 10m x 10m = 100 m2, entierement a l'interieur de rectangular_parcel."""
    return Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])
