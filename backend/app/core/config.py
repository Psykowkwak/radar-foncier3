"""Configuration de l'application, lue depuis les variables d'environnement (.env).

Voir docs/ARCHITECTURE.md §7-8 pour le contexte (LLM optionnel, déploiement docker-compose).
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de données
    database_url: str = Field(
        default="postgresql+psycopg://radar:radar@localhost:5432/radar_foncier",
        description="URL SQLAlchemy (driver psycopg v3) vers PostgreSQL/PostGIS",
    )

    # LLM (optionnel au MVP -- voir docs/ARCHITECTURE.md §7, pas utilisé au MVP,
    # interface prête pour la V1)
    llm_provider: str = Field(default="anthropic")
    anthropic_api_key: str | None = Field(default=None)

    # CORS
    frontend_origin: str = Field(default="http://localhost:3000")

    # Securite -- voir backend/app/core/security.py. Si non definie, l'API reste
    # ouverte (comportement local/dev par defaut) ; en production (Render), cette
    # variable DOIT etre definie et partagee uniquement avec le proxy frontend.
    internal_api_key: str | None = Field(default=None)

    # HTTP sortant (connecteurs)
    http_timeout_seconds: float = Field(default=10.0)
    http_retries: int = Field(default=2)
    http_user_agent: str = Field(default="RadarFoncier/0.1 (usage personnel)")

    # API
    api_v1_prefix: str = Field(default="/api")
    environment: str = Field(default="development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
