"""
oppytec-backend/alembic/env.py
Ejecutor de migraciones correlativas consciente de `migration_scope`:
- `migration_scope == "public"`: aplica DDL sobre `PublicBase.metadata` (`schema="public"`).
- `migration_scope == "tenant"`: aplica DDL sobre cada esquema `tenant_<slug>` activo usando `SET LOCAL search_path`.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Literal

from alembic import context
from sqlalchemy import MetaData, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import get_settings
from src.core.database import validate_tenant_schema_name
from src.modules.analytics.infrastructure import models as analytics_models
from src.modules.audit.infrastructure import models as audit_models
from src.modules.catalog.infrastructure import models as catalog_models
from src.modules.identity.infrastructure import models as identity_models
from src.modules.inventory.infrastructure import models as inventory_models
from src.modules.operations.infrastructure import models as operations_models
from src.modules.oppy_ai.infrastructure import models as oppy_ai_models
from src.modules.procurement.infrastructure import models as procurement_models
from src.modules.recipes.infrastructure import models as recipes_models
from src.modules.tenancy.infrastructure import models as tenancy_models
from src.shared.models_base import PublicBase, TenantBase

# Garantiza que todos los modelos queden registrados en PublicBase.metadata y TenantBase.metadata
REGISTERED_MODEL_MODULES = (
    identity_models,
    tenancy_models,
    audit_models,
    catalog_models,
    inventory_models,
    recipes_models,
    procurement_models,
    operations_models,
    analytics_models,
    oppy_ai_models,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

MigrationScope = Literal["public", "tenant"]


def get_metadata_for_scope(scope: MigrationScope) -> MetaData:
    """Devuelve el objeto `MetaData` correspondiente al `migration_scope` solicitado."""
    if scope == "public":
        return PublicBase.metadata
    return TenantBase.metadata


def should_execute_migration_for_target(
    migration_scope: str,
    target_schema: str,
) -> bool:
    """
    Determina si una migración con `migration_scope` (`"public"` | `"tenant"`)
    debe ejecutar su DDL sobre `target_schema` (`"public"` o `"tenant_<slug>"`).
    Impide que una migración `public` se ejecute repetidamente por cada inquilino.
    """
    if target_schema == "public":
        return migration_scope == "public"
    valid_tenant = validate_tenant_schema_name(target_schema)
    return bool(valid_tenant) and migration_scope == "tenant"


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo `'offline'` generando SQL determinista."""
    settings = get_settings()
    url = settings.DATABASE_URL.get_secret_value()
    context.configure(
        url=url,
        target_metadata=PublicBase.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations_for_schema(
    connection: Connection,
    target_schema: str,
) -> None:
    """Ejecuta las migraciones aplicables a `target_schema` (`public` o `tenant_<slug>`)."""
    if target_schema == "public":
        connection.execute(text("SET LOCAL search_path TO public"))
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS public.alembic_version "
                "(version_num VARCHAR(128) NOT NULL PRIMARY KEY);"
            )
        )
        connection.execute(
            text("ALTER TABLE public.alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);")
        )
        target_meta = PublicBase.metadata
    else:
        valid_schema = validate_tenant_schema_name(target_schema)
        connection.execute(text(f'SET search_path TO "{valid_schema}", public'))
        connection.execute(
            text(
                f'CREATE TABLE IF NOT EXISTS "{valid_schema}".alembic_version '
                "(version_num VARCHAR(128) NOT NULL PRIMARY KEY);"
            )
        )
        connection.execute(
            text(f'ALTER TABLE "{valid_schema}".alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);')
        )
        target_meta = TenantBase.metadata

    context.configure(
        connection=connection,
        target_metadata=target_meta,
        version_table="alembic_version",
        version_table_schema=target_schema,
        include_schemas=(target_schema == "public"),
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Conecta el `AsyncEngine` y ejecuta migraciones en `public` y en los esquemas `tenant_*` activos."""
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL.get_secret_value()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations_for_schema, "public")
        await connection.commit()

        def _get_tenant_schemas(conn: Connection) -> list[str]:
            res = conn.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name LIKE 'tenant_%' ORDER BY schema_name"
                )
            )
            return [row[0] for row in res.fetchall()]

        tenant_schemas = await connection.run_sync(_get_tenant_schemas)

    for schema_name in tenant_schemas:
        async with connectable.connect() as t_conn:
            await t_conn.run_sync(do_run_migrations_for_schema, schema_name)
            await t_conn.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    """Punto de entrada online invocado por el CLI de Alembic."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
elif getattr(context, "_proxy", None) is not None:
    # Solo ejecuta automáticamente cuando es invocado por el runner CLI de Alembic
    run_migrations_online()
else:
    run_migrations_online()
