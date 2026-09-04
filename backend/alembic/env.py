"""Alembic environment configuration for HALOCAS.

Supports asynchronous PostgreSQL via asyncpg and local SQLite (sync & async)
with automatic batch mode rendering and runtime database selection.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve target connection URL
cmd_kwargs = context.get_x_argument(as_dictionary=True)
db_override = cmd_kwargs.get("db") or os.getenv("DATABASE_URL")

if db_override:
    target_url = db_override
else:
    settings = get_settings()
    target_url = settings.DATABASE_URL

config.set_main_option("sqlalchemy.url", target_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts directly without an active database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations in an active connection context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Execute migrations asynchronously using asyncpg or aiosqlite engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, auto-detecting async vs sync drivers."""
    url = config.get_main_option("sqlalchemy.url") or ""
    is_async = "+asyncpg" in url or "+aiosqlite" in url

    if is_async:
        asyncio.run(run_async_migrations())
    else:
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            do_run_migrations(connection)
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
