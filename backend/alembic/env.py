"""
alembic/env.py – Alembic migration environment.

Reads DATABASE_URL from app.config so it always stays in sync with .env.
Supports both SQLite (dev) and PostgreSQL (prod) via the sync URL.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make `app` importable ─────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parents[1]   # backend/
sys.path.insert(0, str(BACKEND_DIR))

# ── Load settings & all ORM models ───────────────────────────────────────────
from app.config import settings          # noqa: E402
from app.database import Base            # noqa: E402
import app.models                        # noqa: E402, F401  – registers all models

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url from our settings (supports .env)
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
