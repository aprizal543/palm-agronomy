from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base
from app.models import block, farm, production, telegram, user  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Alembic stores this value through ConfigParser, where `%` enables interpolation.
# Escape percent-encoded URL credentials (for example `%40`) before setting the option;
# ConfigParser converts `%%` back to `%` when SQLAlchemy reads the URL.
migration_url = get_settings().migration_url
config.set_main_option("sqlalchemy.url", migration_url.replace("%", "%%"))
target_metadata = Base.metadata


def do_run_migrations(connection) -> None:
    # Alembic's version table lives in the private application schema.
    connection.exec_driver_sql("create schema if not exists palm")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
        version_table_schema="palm",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # begin() commits Alembic's version row and DDL after run_sync completes.
    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="palm",
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async_migrations())
