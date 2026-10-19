"""
Pruebas de Integración de Aislamiento Físico Multi-Tenant (`tests/integration/test_multi_tenant_schema_isolation.py`).

Verifica:
1. `validate_tenant_schema_name` rechaza payloads de SQL Injection / nombres inválidos y acepta `tenant_<slug>`.
2. Ciclo de vida `SET LOCAL search_path` y `RESET search_path` (incluyendo `asyncio.CancelledError` y checkin de pool).
3. Aislamiento HTTP Multi-Tenant extremo a extremo mediante `TestClient(app)` con cabeceras `X-Tenant-ID`
   entre `tenant_alpha` y `tenant_beta`.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.sql.elements import TextClause

import src.core.database as db_module
from src.core.database import (
    _on_pool_checkin,
    get_public_db_session,
    get_tenant_db_session,
    validate_tenant_schema_name,
)
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app
from src.modules.tenancy.application.schema_provisioner import TenantSchemaProvisioner

pytestmark = pytest.mark.integration


class _FakeDbapiCursor:
    """Cursor DBAPI instrumentado para auditar `RESET search_path;` en checkin de pool."""

    def __init__(self, executed_sql: list[str]) -> None:
        self._executed_sql = executed_sql
        self.closed: bool = False

    def execute(self, operation: str) -> object:
        self._executed_sql.append(operation)
        return None

    def close(self) -> object:
        self.closed = True
        return None


class _FakeDbapiConnection:
    """Conexión DBAPI instrumentada para verificar `_on_pool_checkin`."""

    def __init__(self) -> None:
        self.executed_sql: list[str] = []
        self.last_cursor: _FakeDbapiCursor | None = None

    def cursor(self) -> _FakeDbapiCursor:
        cur = _FakeDbapiCursor(self.executed_sql)
        self.last_cursor = cur
        return cur


class _InstrumentedAsyncSession:
    """Sesión asíncrona instrumentada para verificar `SET LOCAL search_path`, `rollback` y `RESET search_path`."""

    def __init__(self, sql_log: list[str]) -> None:
        self.sql_log = sql_log
        self.rolled_back: bool = False

    async def __aenter__(self) -> _InstrumentedAsyncSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        return None

    async def execute(self, statement: object) -> object:
        if isinstance(statement, TextClause):
            self.sql_log.append(str(statement.text))
        else:
            self.sql_log.append(str(statement))
        return None

    async def rollback(self) -> None:
        self.rolled_back = True
        self.sql_log.append("ROLLBACK")


def test_validate_tenant_schema_name_blocks_sqli_and_accepts_valid_slugs() -> None:
    """Verifica que `validate_tenant_schema_name` bloquee inyecciones SQL y valide `^tenant_[a-z0-9_]{1,63}$`."""
    assert validate_tenant_schema_name("tenant_alpha") == "tenant_alpha"
    assert validate_tenant_schema_name("  tenant_beta_01  ") == "tenant_beta_01"

    malicious_or_invalid_inputs = (
        "public",
        "tenant_",
        "Tenant_Upper",
        "tenant-hyphen",
        'tenant_alpha"; DROP SCHEMA public CASCADE; --',
        "tenant_alpha' OR '1'='1",
        "tenant_alpha; RESET ROLE;",
        "../tenant_alpha",
        "tenant_" + ("a" * 64),
        "",
    )
    for bad_input in malicious_or_invalid_inputs:
        with pytest.raises(ValueError, match="TenantSchemaValidationError"):
            validate_tenant_schema_name(bad_input)


async def test_search_path_lifecycle_and_cancelled_error_reset() -> None:
    """
    Verifica que `get_public_db_session` y `get_tenant_db_session` fijen `SET LOCAL search_path`
    y siempre ejecuten `RESET search_path` en `finally` (incluso ante `asyncio.CancelledError`),
    además del listener `_on_pool_checkin`.
    """
    sql_log: list[str] = []
    last_session: _InstrumentedAsyncSession | None = None

    def _fake_factory() -> _InstrumentedAsyncSession:
        nonlocal last_session
        last_session = _InstrumentedAsyncSession(sql_log)
        return last_session

    with patch.object(db_module, "get_session_factory", return_value=_fake_factory):
        # 1. Sesión en plano `public`
        gen_pub = get_public_db_session()
        await anext(gen_pub)
        assert sql_log == ["SET LOCAL search_path TO public"]
        with pytest.raises(StopAsyncIteration):
            await anext(gen_pub)
        assert sql_log == ["SET LOCAL search_path TO public", "RESET search_path"]

        # 2. Sesión aislada en `tenant_alpha`
        sql_log.clear()
        gen_tenant = get_tenant_db_session("tenant_alpha")
        await anext(gen_tenant)
        assert sql_log == ['SET LOCAL search_path TO "tenant_alpha", public']
        with pytest.raises(StopAsyncIteration):
            await anext(gen_tenant)
        assert sql_log == [
            'SET LOCAL search_path TO "tenant_alpha", public',
            "RESET search_path",
        ]

        # 3. Cancelación abrupta (`asyncio.CancelledError`) debe hacer ROLLBACK + RESET search_path
        sql_log.clear()
        gen_cancel = get_tenant_db_session("tenant_beta")
        await anext(gen_cancel)
        with pytest.raises(asyncio.CancelledError):
            await gen_cancel.athrow(asyncio.CancelledError())
        assert last_session is not None
        assert last_session.rolled_back is True
        assert sql_log == [
            'SET LOCAL search_path TO "tenant_beta", public',
            "ROLLBACK",
            "RESET search_path",
        ]

    # 4. Listener de devolución al pool (`_on_pool_checkin`)
    fake_conn = _FakeDbapiConnection()
    _on_pool_checkin(fake_conn, object())
    assert fake_conn.executed_sql == ["RESET search_path;"]
    assert fake_conn.last_cursor is not None
    assert fake_conn.last_cursor.closed is True


def test_http_multi_tenant_isolation_with_testclient_alpha_vs_beta() -> None:
    """
    Verifica con `TestClient(app)` que los tokens emitidos para `tenant_alpha` y `tenant_beta`
    operen aislados por `X-Tenant-ID`, bloqueando cualquier cruce con HTTP 403 (`CrossTenantAccessError`),
    y que `TenantSchemaProvisioner` impida colisiones de esquema o entidad legal.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    provisioner = TenantSchemaProvisioner()
    manifest_alpha = provisioner.provision_tenant_schema(
        holding_id="holding_alpha",
        legal_entity_id="le_alpha_1",
        tenant_id="tenant_alpha",
        schema_name="tenant_alpha",
    )
    manifest_beta = provisioner.provision_tenant_schema(
        holding_id="holding_beta",
        legal_entity_id="le_beta_1",
        tenant_id="tenant_beta",
        schema_name="tenant_beta",
    )
    assert manifest_alpha.ddl_statements == (
        'CREATE SCHEMA IF NOT EXISTS "tenant_alpha";',
        'SET LOCAL search_path TO "tenant_alpha", public;',
    )
    assert manifest_beta.ddl_statements == (
        'CREATE SCHEMA IF NOT EXISTS "tenant_beta";',
        'SET LOCAL search_path TO "tenant_beta", public;',
    )

    app = create_app()
    token_alpha = create_access_token(
        user_id=101,
        holding_id="holding_alpha",
        tenant_id="tenant_alpha",
        tenant_schema="tenant_alpha",
        hierarchy_rank=20,
        contracted_modules=["catalog", "tenancy"],
        role_grants=["catalog.products.create", "catalog.products.read", "tenancy.storage_quotas.read"],
        accessible_tenants=["tenant_alpha"],
    )
    token_beta = create_access_token(
        user_id=202,
        holding_id="holding_beta",
        tenant_id="tenant_beta",
        tenant_schema="tenant_beta",
        hierarchy_rank=20,
        contracted_modules=["catalog", "tenancy"],
        role_grants=["catalog.products.create", "catalog.products.read", "tenancy.storage_quotas.read"],
        accessible_tenants=["tenant_beta"],
    )

    with TestClient(app) as client:
        # 1. `tenant_alpha` opera válidamente en su propio contexto
        alpha_quota = client.get(
            "/api/v1/tenancy/quotas/storage",
            headers={
                "Authorization": f"Bearer {token_alpha}",
                "X-Tenant-ID": "tenant_alpha",
            },
        )
        assert alpha_quota.status_code == 200
        assert alpha_quota.json()["tenant_id"] == "tenant_alpha"

        # 2. `tenant_beta` opera válidamente en su propio contexto
        beta_quota = client.get(
            "/api/v1/tenancy/quotas/storage",
            headers={
                "Authorization": f"Bearer {token_beta}",
                "X-Tenant-ID": "tenant_beta",
            },
        )
        assert beta_quota.status_code == 200
        assert beta_quota.json()["tenant_id"] == "tenant_beta"

        # 3. `tenant_alpha` intentando operar sobre `tenant_beta` vía `X-Tenant-ID` -> HTTP 403
        cross_ab = client.get(
            "/api/v1/catalog/products",
            headers={
                "Authorization": f"Bearer {token_alpha}",
                "X-Tenant-ID": "tenant_beta",
            },
        )
        assert cross_ab.status_code == 403
        assert cross_ab.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

        # 4. `tenant_beta` intentando crear un producto en `tenant_alpha` -> HTTP 403
        cross_ba = client.post(
            "/api/v1/catalog/products",
            headers={
                "Authorization": f"Bearer {token_beta}",
                "X-Tenant-ID": "tenant_alpha",
            },
            json={
                "sku": "INTRUSION-01",
                "nombre": "Intento Cross Tenant",
                "marca_comercial": "Pollo King",
                "unidad_compra": "kg",
                "unidad_almacen": "kg",
                "unidad_receta": "g",
                "factor_compra_a_almacen": "1",
                "factor_almacen_a_receta": "1000",
                "costo_compra_neto": str(Decimal("5000.00")),
            },
        )
        assert cross_ba.status_code == 403
        assert cross_ba.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"
