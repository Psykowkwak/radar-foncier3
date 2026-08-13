"""Interface commune des connecteurs (Providers) -- voir docs/ARCHITECTURE.md §4.

Regle absolue : un connecteur qui echoue NE DOIT JAMAIS faire planter l'appelant.
Il catch large, logue, et retourne un ProviderResult vide avec un warning explicite.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger("radar_foncier.connectors")

Reliability = Literal["OFFICIAL", "DERIVED", "USER_IMPORTED"]


@dataclass
class SourceRecord:
    """Traçabilité d'une donnée importée -- miroir du modele DB app.models.source.SourceRecord."""

    source_name: str
    source_url: str
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_version: str | None = None
    reliability: Reliability = "OFFICIAL"


@dataclass
class ProviderResult:
    """Resultat uniforme retourne par tous les connecteurs, succes ou echec."""

    data: Any
    source: SourceRecord
    warnings: list[str] = field(default_factory=list)
    success: bool = True

    @property
    def is_empty(self) -> bool:
        return self.data is None or (hasattr(self.data, "__len__") and len(self.data) == 0)


class DataProvider(Protocol):
    name: str

    def fetch(self, **params: Any) -> ProviderResult: ...


def get_http_client() -> httpx.Client:
    """Client HTTP synchrone partage : timeout 10s, User-Agent identifiable.

    Le retry (2 tentatives) est gere par `request_with_retry`, pas par le client
    lui-meme, pour garder un controle explicite du logging a chaque tentative.
    """
    settings = get_settings()
    return httpx.Client(
        timeout=settings.http_timeout_seconds,
        headers={"User-Agent": settings.http_user_agent},
        follow_redirects=True,
    )


def request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    attempts: int | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Effectue une requete HTTP avec un retry simple (defaut : 2 tentatives).

    Leve la derniere exception rencontree si toutes les tentatives échouent --
    c'est au connecteur appelant de catcher et de transformer en ProviderResult
    (voir chaque module connectors/*.py, méthode `fetch`).
    """
    settings = get_settings()
    n_attempts = attempts if attempts is not None else settings.http_retries
    last_exc: Exception | None = None
    for attempt in range(1, n_attempts + 1):
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TransportError) as exc:
            last_exc = exc
            logger.warning(
                "Tentative %s/%s echouee pour %s %s : %s", attempt, n_attempts, method, url, exc
            )
    assert last_exc is not None
    raise last_exc


def empty_result(source_name: str, source_url: str, warning: str, reliability: Reliability = "OFFICIAL") -> ProviderResult:
    """Construit un ProviderResult vide en cas d'echec, jamais une exception qui remonte."""
    return ProviderResult(
        data=None,
        source=SourceRecord(source_name=source_name, source_url=source_url, reliability=reliability),
        warnings=[warning],
        success=False,
    )
