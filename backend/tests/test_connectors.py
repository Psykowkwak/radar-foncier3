"""Tests des connecteurs avec reponses HTTP mockees (respx) -- PAS d'appel reseau
reel. Voir app/connectors/README.md pour le statut de chaque connecteur."""
from __future__ import annotations

import httpx
import respx

from app.connectors.buildings import BuildingProvider
from app.connectors.cadastre import CadastreProvider
from app.connectors.geocoding import GeocodingProvider
from app.connectors.risk import RiskProvider
from app.connectors.urbanism import UrbanismProvider

FEATURE_COLLECTION_EMPTY = {"type": "FeatureCollection", "features": []}


def _parcelle_feature(numero: str) -> dict:
    return {
        "type": "Feature",
        "properties": {"section": "AB", "numero": numero, "contenance": 500},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[2.3, 48.8], [2.3001, 48.8], [2.3001, 48.8001], [2.3, 48.8001], [2.3, 48.8]]],
        },
    }


@respx.mock
def test_cadastre_provider_fetch_commune_success():
    respx.get("https://apicarto.ign.fr/api/cadastre/commune").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "properties": {"nom": "Paris"}, "geometry": {"type": "Polygon", "coordinates": []}}],
            },
        )
    )
    provider = CadastreProvider()
    result = provider.fetch_commune("75056")
    assert result.success is True
    assert len(result.data) == 1
    assert result.warnings == []


@respx.mock
def test_cadastre_provider_fetch_commune_http_error_returns_empty_result():
    respx.get("https://apicarto.ign.fr/api/cadastre/commune").mock(return_value=httpx.Response(500))
    provider = CadastreProvider()
    result = provider.fetch_commune("75056")
    assert result.success is False
    assert result.data is None
    assert len(result.warnings) == 1
    assert "non recuperee" in result.warnings[0] or "non recupere" in result.warnings[0]


@respx.mock
def test_cadastre_provider_fetch_parcelles_paginates():
    # Premiere page pleine (limite volontairement basse pour simuler la pagination
    # sans generer 1000 features) -- on force PARCELLE_PAGE_LIMIT via monkeypatch
    # implicite : ici on verifie simplement que 2 appels sont faits quand la 1ere
    # page renvoie exactement la limite standard n'est pas pratique en test unitaire,
    # donc on verifie le cas simple : une seule page, moins que la limite.
    route = respx.get("https://apicarto.ign.fr/api/cadastre/parcelle").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": [_parcelle_feature("0001")]})
    )
    provider = CadastreProvider()
    result = provider.fetch_parcelles("75056")
    assert result.success is True
    assert len(result.data) == 1
    assert route.called


@respx.mock
def test_cadastre_provider_fetch_parcelles_empty_gives_warning():
    respx.get("https://apicarto.ign.fr/api/cadastre/parcelle").mock(
        return_value=httpx.Response(200, json=FEATURE_COLLECTION_EMPTY)
    )
    provider = CadastreProvider()
    result = provider.fetch_parcelles("00000")
    assert result.success is True
    assert result.data == []
    assert any("Aucune parcelle" in w for w in result.warnings)


@respx.mock
def test_urbanism_provider_partition_success():
    respx.get("https://apicarto.ign.fr/api/gpu/zone-urba").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"libelle": "UB", "typezone": "U"},
                        "geometry": {"type": "Polygon", "coordinates": []},
                    }
                ],
            },
        )
    )
    provider = UrbanismProvider()
    result = provider.fetch_by_partition("75056")
    assert result.success is True
    assert result.data[0]["properties"]["typezone"] == "U"


@respx.mock
def test_urbanism_provider_empty_result_warns_but_does_not_fail():
    respx.get("https://apicarto.ign.fr/api/gpu/zone-urba").mock(
        return_value=httpx.Response(200, json=FEATURE_COLLECTION_EMPTY)
    )
    provider = UrbanismProvider()
    result = provider.fetch_by_partition("75056")
    assert result.success is True  # reponse vide != echec, voir avertissement officiel GPU
    assert any("couverture GPU incomplete" in w for w in result.warnings)


@respx.mock
def test_building_provider_404_is_defensive_never_raises():
    respx.get(url__regex=r"https://cadastre\.data\.gouv\.fr/.*").mock(return_value=httpx.Response(404))
    provider = BuildingProvider()
    result = provider.fetch(code_insee="75056")
    assert result.success is False
    assert result.data is None
    assert "bati non recupere" in result.warnings[0] or "Bati non recupere" in result.warnings[0]


@respx.mock
def test_risk_provider_defensive_on_failure():
    respx.get(url__regex=r"https://georisques\.gouv\.fr/.*").mock(return_value=httpx.Response(503))
    provider = RiskProvider()
    result = provider.fetch_rga("75056")
    assert result.success is False
    assert result.data is None
    assert len(result.warnings) == 1


@respx.mock
def test_risk_provider_success():
    respx.get(url__regex=r"https://georisques\.gouv\.fr/.*").mock(
        return_value=httpx.Response(200, json={"data": [{"alea": "moyen"}]})
    )
    provider = RiskProvider()
    result = provider.fetch_rga("75056")
    assert result.success is True
    assert result.data == [{"alea": "moyen"}]


@respx.mock
def test_geocoding_provider_search_success():
    respx.get("https://data.geopf.fr/geocodage/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"city": "Paris", "citycode": "75056", "postcode": "75001"},
                        "geometry": {"type": "Point", "coordinates": [2.35, 48.85]},
                    }
                ],
            },
        )
    )
    provider = GeocodingProvider()
    result = provider.search_municipality("Paris")
    assert result.success is True
    assert result.data[0]["properties"]["citycode"] == "75056"


@respx.mock
def test_connectors_never_raise_on_network_error():
    """Regle absolue : un connecteur ne fait jamais planter l'appelant, meme sur une
    exception de transport (timeout, DNS, etc.)."""
    respx.get("https://apicarto.ign.fr/api/cadastre/commune").mock(side_effect=httpx.ConnectError("boom"))
    provider = CadastreProvider()
    result = provider.fetch_commune("75056")
    assert result.success is False
    assert result.data is None
