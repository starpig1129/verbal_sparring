"""Alembic environment configuration.

Configures Alembic to use the project's SQLAlchemy ``Base.metadata`` for
autogenerate support, and reads the database URL from the application
settings so that migrations always target the same database as the
application.

Usage::

    cd src/backend
    alembic revision --autogenerate -m "description"
    alembic upgrade head
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# ---------------------------------------------------------------------------
# Make sure src/backend (and its parent) are on sys.path so that imports
# like ``from src.backend.core.database import Base`` resolve correctly.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_HERE)          # src/backend
_SRC_DIR = os.path.dirname(_BACKEND_DIR)       # src
_REPO_ROOT = os.path.dirname(_SRC_DIR)         # repo root

for _path in (_REPO_ROOT, _SRC_DIR, _BACKEND_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in the .ini file.
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override the URL with the value from application settings so that the
# database targeted by migrations stays in sync with the app.
# The asyncpg driver prefix is replaced with the sync psycopg2/libpq
# equivalent that Alembic's standard (sync) engine requires.
# ---------------------------------------------------------------------------
from src.backend.core.config import settings  # noqa: E402

_sync_url = settings.database_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", _sync_url)

# ---------------------------------------------------------------------------
# Import all ORM models so that Base.metadata is fully populated.
# ---------------------------------------------------------------------------
from src.backend.core.database import Base, _import_models  # noqa: E402

_import_models()
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL rather than an Engine.  No DBAPI
    connection is required — SQL statements are emitted as strings.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates a synchronous engine from the configured URL and associates
    a live connection with the migration context.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
