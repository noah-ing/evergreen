"""
Alembic environment configuration.

Handles async database migrations.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import our models so Alembic can detect them
from evergreen.db import Base
from evergreen.db.models import Tenant, User, Connection as DBConnection, SyncJob, AuditLog

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = Base.metadata

# Get database URL directly from env var (Railway provides DATABASE_URL)
# Convert postgres:// to postgresql+asyncpg:// for async SQLAlchemy
def get_async_database_url() -> str:
    raw_url = os.environ.get("DATABASE_URL", "")
    print(f"[DEBUG] Raw DATABASE_URL: {raw_url[:50]}..." if len(raw_url) > 50 else f"[DEBUG] Raw DATABASE_URL: {raw_url}")
    
    if not raw_url:
        print("[DEBUG] DATABASE_URL not set, using default")
        raw_url = "postgresql://evergreen:evergreen@localhost:5432/evergreen"
    
    url = raw_url
    # Railway uses postgres:// but SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # Fix malformed URLs with empty port (e.g., @host:/db -> @host:5432/db)
    import re
    url = re.sub(r'(@[^/:]+):(\d*)/', lambda m: f'{m.group(1)}:{m.group(2) or "5432"}/', url)
    # Convert to async
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    print(f"[DEBUG] Processed URL: {url[:60]}..." if len(url) > 60 else f"[DEBUG] Processed URL: {url}")
    return url

db_url = get_async_database_url()


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    Generates SQL script without connecting to database.
    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = db_url
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
