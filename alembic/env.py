from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool

from alembic import context

# add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# import your application's metadata
from backend.models.base import Base  # noqa: E402
target_metadata = Base.metadata


def _get_url() -> str:
    """
    Return a synchronous psycopg2 DATABASE_URL for Alembic.

    Priority:
      1. DATABASE_URL env var (set automatically by Railway Postgres plugin).
      2. sqlalchemy.url from alembic.ini (local fallback).

    Railway provides 'postgres://' or 'postgresql://' — both are rewritten to
    'postgresql+psycopg2://' so that the synchronous Alembic engine can connect.
    """
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or ""
    # Normalise scheme for psycopg2 (Alembic is synchronous)
    for prefix in ("postgres://", "postgresql+asyncpg://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
            break
    return url


def run_migrations_offline():
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(_get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
