"""Environnement Alembic -- lit DATABASE_URL depuis app.core.config, connait tous
les modeles MVP via app.models (Base.metadata).

IMPORTANT : l'URL n'est JAMAIS passee par `config.set_main_option`/`config.get_section`
(configparser). configparser applique une interpolation de style "%" par defaut, et
un mot de passe contenant un caractere "%" (frequent avec un mot de passe genere
contenant des caracteres pourcent-encodes, ex "%40") declenche une erreur
`ValueError: invalid interpolation syntax`. On construit donc l'engine directement
avec `create_engine(settings.database_url)`, sans jamais faire transiter l'URL par
configparser.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.core.db import Base
from app import models  # noqa: F401 -- assure l'enregistrement de tous les modeles MVP

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
