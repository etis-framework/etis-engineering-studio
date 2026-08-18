from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from apps.api.app.models import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(
        config.config_file_name,
        disable_existing_loggers=False,
    )


# SQLAlchemy model metadata is the authoritative schema definition used by
# Alembic autogeneration.
target_metadata = Base.metadata


def database_url() -> str:
    """
    Resolve the database URL used by Alembic.

    Explicit programmatic configuration wins first. This is important for
    migration contract tests, which inject an isolated temporary database.

    Otherwise ETIS_DATABASE_URL supplies the runtime/production database.
    """
    configured = config.get_main_option("sqlalchemy.url", "").strip()

    # The checked-in alembic.ini uses this sentinel rather than containing
    # environment-specific credentials.
    if configured and configured != "__ETIS_DATABASE_URL__":
        return configured

    runtime = os.getenv("ETIS_DATABASE_URL", "").strip()
    if runtime:
        return runtime

    raise RuntimeError(
        "Alembic database URL is not configured. "
        "Set ETIS_DATABASE_URL or provide sqlalchemy.url programmatically."
    )


def run_migrations_offline() -> None:
    url = database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = database_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
