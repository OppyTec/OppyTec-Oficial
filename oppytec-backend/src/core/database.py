"""
oppytec-backend/src/core/database.py
Motor asíncrono SQLAlchemy 2.0 y aislamiento físico de sesiones PostgreSQL (`public` vs `tenant_*`).
Implementa validación estricta de `schema_name`, `SET LOCAL search_path` y `RESET search_path` en checkin/finally.
"""
from __future__ import annotations

import asyncio
import contextlib
import re
from collections.abc import AsyncGenerator
from typing import Protocol

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from src.core.config import Settings, get_settings

TENANT_SCHEMA_REGEX: re.Pattern[str] = re.compile(r"^tenant_[a-z0-9_]{1,63}$")


class RawDbapiCursor(Protocol):
    """Protocolo tipado para cursor DBAPI en eventos de pool de SQLAlchemy."""

    def execute(self, operation: str) -> object: ...
    def close(self) -> object: ...


class RawDbapiConnection(Protocol):
    """Protocolo tipado para conexión DBAPI en eventos de checkin/reset."""

    def cursor(self) -> RawDbapiCursor: ...


def validate_tenant_schema_name(schema_name: str) -> str:
    """
    Valida que el nombre de esquema de inquilino cumpla estrictamente `^tenant_[a-z0-9_]{1,63}$`.
    Impide cualquier intento de SQL Injection antes de interpolar en `SET LOCAL search_path`.
    """
    cleaned = schema_name.strip()
    if not TENANT_SCHEMA_REGEX.match(cleaned):
        raise ValueError(
            f"TenantSchemaValidationError: Esquema inválido '{schema_name}'. "
            "Debe cumplir el patrón estricto '^tenant_[a-z0-9_]{1,63}$'."
        )
    return cleaned


def build_engine_kwargs(settings: Settings) -> dict[str, object]:
    """Construye los argumentos de `create_async_engine` según `DB_POOL_CLASS` (`QueuePool` vs `NullPool`)."""
    connect_args: dict[str, object] = {
        "statement_cache_size": settings.DB_STATEMENT_CACHE_SIZE,
    }
    if settings.DB_POOL_CLASS == "NullPool":
        connect_args["statement_cache_size"] = 0
        return {
            "poolclass": NullPool,
            "pool_pre_ping": False,
            "connect_args": connect_args,
        }
    return {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }


def _on_pool_checkin(
    dbapi_connection: RawDbapiConnection | None,
    _connection_record: object,
) -> None:
    """
    Listener de seguridad en devolución al pool: garantiza `RESET search_path;`
    incluso si una corrutina fue abortada abruptamente (`asyncio.CancelledError`).
    """
    if dbapi_connection is None:
        return
    with contextlib.suppress(Exception):
        cursor = dbapi_connection.cursor()
        cursor.execute("RESET search_path;")
        cursor.close()


def create_db_engine(settings: Settings | None = None) -> AsyncEngine:
    """Crea y configura el `AsyncEngine` con listener de `RESET search_path` en checkin."""
    resolved = settings or get_settings()
    engine_kwargs = build_engine_kwargs(resolved)
    engine = create_async_engine(
        resolved.DATABASE_URL.get_secret_value(),
        **engine_kwargs,
    )
    event.listen(engine.sync_engine, "checkin", _on_pool_checkin)
    return engine


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Devuelve la instancia singleton de `AsyncEngine`."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Devuelve la fábrica asíncrona de sesiones SQLAlchemy 2.0 (`expire_on_commit=False`)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_public_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Generador de sesión exclusivo para el Plano de Control Global (`public`).
    Fija `SET LOCAL search_path TO public` dentro de la transacción y limpia al salir.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            await session.execute(text("SET LOCAL search_path TO public"))
            yield session
        except asyncio.CancelledError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            with contextlib.suppress(Exception):
                await session.execute(text("RESET search_path"))


async def get_tenant_db_session(tenant_schema: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Generador de sesión aislado para una sucursal cliente (`tenant_<slug>`).
    1. Valida `tenant_schema` con regex estricto.
    2. Ejecuta `SET LOCAL search_path TO "<tenant_schema>", public`.
    3. Garantiza `RESET search_path` en el bloque `finally` incluso ante `asyncio.CancelledError`.
    """
    valid_schema = validate_tenant_schema_name(tenant_schema)
    factory = get_session_factory()
    async with factory() as session:
        try:
            await session.execute(
                text(f'SET LOCAL search_path TO "{valid_schema}", public')
            )
            yield session
        except asyncio.CancelledError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            with contextlib.suppress(Exception):
                await session.execute(text("RESET search_path"))
