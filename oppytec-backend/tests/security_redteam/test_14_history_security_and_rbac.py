"""
Vector Red Team 14 (`tests/security_redteam/test_14_history_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant y RBAC en Historial de Kardex (/historial):
1. Aislamiento Multi-Tenant Estricto: Confinamiento por tenant_id, bloqueo de salto de tenant vía X-Tenant-ID
   y verificación de que la purga no afecta a otros inquilinos (cross-tenant data destruction denial).
2. RBAC de 3 Niveles:
   - Verificación de permisos `inventory.history.read` con fallback a `inventory.kardex.read`.
   - Verificación de permisos `inventory.history.export` con fallback a `inventory.kardex.read`.
   - Purga histórica (`DELETE /api/v1/inventory/history/purge` y `/api/v1/inventory/history`) restringida
     estrictamente a rol Propietario (rank 0 / is_holding_owner / superuser_god); denegación 403 a roles estándar.
   - Denegaciones explícitas (`explicit_denies`) y revocación de sesión en tiempo real (kill-switch JTI).
3. Resiliencia contra Inyecciones SQL: Evasión y payloads políglotas en `bodega_id`, `producto_id`,
   `tipo_movimiento`, `fecha_desde`, `fecha_hasta` y `usuario_busqueda`.
4. Sanitización contra Inyección CSV en Servidor (CWE-1236 Formula Injection):
   - Prefijado determinista con comilla simple `'` ante prefijos `=`, `+`, `-`, `@`, `\t`, `\r`.
   - Emisión obligatoria de BOM UTF-8 (`\ufeff`) y cabeceras de Content-Disposition adecuadas.
5. Protección y Redacción Determinista de PII:
   - Anonimización a 'Operador Autorizado' en API paginada y CSV cuando falta `inventory.history.view_users`.
   - Redacción de correos y nombres de usuario (`scrub_audit_payload`, `[REDACTED]`).
   - Cero exposición de credenciales o campos no autorizados (Pydantic `extra="forbid"`).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from src.core.guards.rbac_dependencies import (
    clear_revoked_sessions,
    revoke_session_token,
)
from src.core.observability import REDACTED_MARKER
from src.core.security import create_access_token
from src.modules.inventory.application.history_service import (
    format_history_audit_log,
    scrub_audit_payload,
)
from src.modules.inventory.presentation.router import (
    _history_service,
    _inventory_service,
)
from src.modules.inventory.presentation.schemas import (
    KardexHistoryItemResponse,
    PaginatedKardexHistoryResponse,
)

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_alpha_santiago"
TENANT_BETA = "tenant_beta_valparaiso"
HOLDING_ID = "holding_pollogold"


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    *,
    hierarchy_rank: int = 20,
    is_holding_owner: bool = False,
    is_superuser_god: bool = False,
    explicit_denies: list[str] | None = None,
    accessible_tenants: list[str] | None = None,
    jti: str = "",
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=accessible_tenants or [tenant_id],
        is_holding_owner=is_holding_owner,
        is_superuser_god=is_superuser_god,
        jti=jti,
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_test_environment() -> None:
    clear_revoked_sessions()
    _inventory_service.reset()
    _history_service.reset()


# ============================================================================
# VECTOR 1: AISLAMIENTO MULTI-TENANT Y CONFINAMIENTO FÍSICO
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_isolation_in_paginated_history(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las consultas en `/api/v1/inventory/history/paginated` retornen
    exclusivamente movimientos pertenecientes al tenant del usuario autenticado,
    garantizando cero fuga cross-tenant.
    """
    # 1. Movimientos en Tenant Alpha
    _inventory_service.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("1500.00"),
        actor_user_id=101,
        tenant_id=TENANT_ALPHA,
    )
    _inventory_service.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="SALIDA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("1500.00"),
        actor_user_id=101,
        tenant_id=TENANT_ALPHA,
    )

    # 2. Movimiento confidencial en Tenant Beta
    _inventory_service.register_movement(
        producto_id=99,
        bodega_id=2,
        movement_type="AJUSTE_POSITIVO",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("9999.00"),
        actor_user_id=202,
        tenant_id=TENANT_BETA,
    )

    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
    )
    headers_alpha = _make_headers(token_alpha, TENANT_ALPHA)

    # Consulta Tenant Alpha
    res_alpha = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_alpha,
    )
    assert res_alpha.status_code == 200
    data_alpha = res_alpha.json()
    assert data_alpha["total"] == 2
    for item in data_alpha["items"]:
        assert item["producto_id"] == 10
        assert item["producto_id"] != 99

    # Consulta Tenant Beta
    token_beta = _create_token(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=["inventory.history.read"],
    )
    headers_beta = _make_headers(token_beta, TENANT_BETA)
    res_beta = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_beta,
    )
    assert res_beta.status_code == 200
    data_beta = res_beta.json()
    assert data_beta["total"] == 1
    assert data_beta["items"][0]["producto_id"] == 99


@pytest.mark.asyncio
async def test_cross_tenant_idor_header_spoofing_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un usuario de Tenant Alpha que intente suplantar `X-Tenant-ID: tenant_beta`
    sea bloqueado con 403 Forbidden por discrepancia de tenant en JWT.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
        accessible_tenants=[TENANT_ALPHA],
    )
    # Suplantación maliciosa en cabecera
    headers_spoofed = {
        "Authorization": f"Bearer {token_alpha}",
        "X-Tenant-ID": TENANT_BETA,
    }

    res = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_spoofed,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_purge_does_not_affect_other_tenants(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que cuando el Propietario de Tenant Alpha ejecuta una purga histórica,
    exclusivamente se destruyen los registros de Tenant Alpha, manteniendo los
    registros de Tenant Beta completamente intactos.
    """
    # 1. Asientos para Alpha
    _inventory_service.register_movement(
        producto_id=1,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("100.00"),
        actor_user_id=101,
        tenant_id=TENANT_ALPHA,
    )
    # 2. Asientos para Beta
    _inventory_service.register_movement(
        producto_id=2,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("200.00"),
        actor_user_id=202,
        tenant_id=TENANT_BETA,
    )

    token_owner_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.purge", "inventory.history.read"],
        is_holding_owner=True,
        hierarchy_rank=0,
    )
    headers_owner_alpha = _make_headers(token_owner_alpha, TENANT_ALPHA)

    # Purga en endpoint `/api/v1/inventory/history/purge`
    res_purge = await async_client.delete(
        "/api/v1/inventory/history/purge",
        headers=headers_owner_alpha,
    )
    assert res_purge.status_code == 204

    # Verificar que Alpha quedó vacío
    res_alpha = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_owner_alpha,
    )
    assert res_alpha.status_code == 200
    assert res_alpha.json()["total"] == 0

    # Verificar que Beta conserva sus registros
    token_beta = _create_token(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=["inventory.history.read"],
    )
    res_beta = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=_make_headers(token_beta, TENANT_BETA),
    )
    assert res_beta.status_code == 200
    assert res_beta.json()["total"] == 1
    assert res_beta.json()["items"][0]["producto_id"] == 2


# ============================================================================
# VECTOR 2: RBAC DE 3 NIVELES Y CONTROL DE ACCESO ESTRICTO
# ============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_requests_blocked_with_401(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que solicitudes sin token JWT sean rechazadas con 401 Unauthorized."""
    # Paginated
    res_page = await async_client.get("/api/v1/inventory/history/paginated")
    assert res_page.status_code == 401

    # Export CSV
    res_csv = await async_client.get("/api/v1/inventory/history/export-csv")
    assert res_csv.status_code == 401

    # Purge
    res_purge = await async_client.delete("/api/v1/inventory/history/purge")
    assert res_purge.status_code == 401


@pytest.mark.asyncio
async def test_paginated_history_rbac_and_fallback_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que /history/paginated requiera 'inventory.history.read',
    pero admita 'inventory.kardex.read' como fallback legítimo.
    """
    # 1. Sin permisos requeridos -> 403 Forbidden
    token_no_perm = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["catalog.products.read"],
    )
    res_no_perm = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=_make_headers(token_no_perm, TENANT_ALPHA),
    )
    assert res_no_perm.status_code == 403

    # 2. Con fallback 'inventory.kardex.read' -> 200 OK
    token_fallback = _create_token(
        user_id=102,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.kardex.read"],
    )
    res_fallback = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=_make_headers(token_fallback, TENANT_ALPHA),
    )
    assert res_fallback.status_code == 200

    # 3. Con permiso canónico 'inventory.history.read' -> 200 OK
    token_canonical = _create_token(
        user_id=103,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
    )
    res_canonical = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=_make_headers(token_canonical, TENANT_ALPHA),
    )
    assert res_canonical.status_code == 200


@pytest.mark.asyncio
async def test_export_csv_rbac_and_fallback_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que /history/export-csv requiera 'inventory.history.export'
    o admita 'inventory.kardex.read' como fallback.
    """
    # Sin permisos de exportación -> 403 Forbidden
    token_no_perm = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],  # Solo lectura, no exportación
    )
    res_no_perm = await async_client.get(
        "/api/v1/inventory/history/export-csv",
        headers=_make_headers(token_no_perm, TENANT_ALPHA),
    )
    assert res_no_perm.status_code == 403

    # Con permiso de exportación canónico -> 200 OK
    token_export = _create_token(
        user_id=102,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.export"],
    )
    res_export = await async_client.get(
        "/api/v1/inventory/history/export-csv",
        headers=_make_headers(token_export, TENANT_ALPHA),
    )
    assert res_export.status_code == 200


@pytest.mark.asyncio
async def test_purge_history_strictly_requires_owner_and_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la purga histórica requiera el permiso 'inventory.history.purge'
    Y estrictamente el rol de Propietario (is_holding_owner=True o hierarchy_rank=0
    o is_superuser_god=True). Roles operativos estándar son rechazados con 403.
    """
    # 1. Empleado estándar sin permiso de purge -> 403
    token_emp_no_purge = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
        hierarchy_rank=30,
        is_holding_owner=False,
    )
    res_no_perm = await async_client.delete(
        "/api/v1/inventory/history/purge",
        headers=_make_headers(token_emp_no_purge, TENANT_ALPHA),
    )
    assert res_no_perm.status_code == 403

    # 2. Empleado con permiso pero sin rango de Propietario (rank 30) -> 403
    token_emp_with_perm = _create_token(
        user_id=102,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.purge"],
        hierarchy_rank=30,
        is_holding_owner=False,
    )
    res_emp_blocked = await async_client.delete(
        "/api/v1/inventory/history/purge",
        headers=_make_headers(token_emp_with_perm, TENANT_ALPHA),
    )
    assert res_emp_blocked.status_code == 403
    assert "Solo el Propietario" in res_emp_blocked.json()["detail"]

    # 3. Administrador de local (rank 10) con permiso pero no Propietario -> 403
    token_mgr_blocked = _create_token(
        user_id=103,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.purge"],
        hierarchy_rank=10,
        is_holding_owner=False,
    )
    res_mgr_blocked = await async_client.delete(
        "/api/v1/inventory/history/purge",
        headers=_make_headers(token_mgr_blocked, TENANT_ALPHA),
    )
    assert res_mgr_blocked.status_code == 403

    # 4. Propietario del tenant (rank 0 / is_holding_owner=True) -> 204 No Content
    token_owner = _create_token(
        user_id=104,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.purge"],
        hierarchy_rank=0,
        is_holding_owner=True,
    )
    res_owner_purge = await async_client.delete(
        "/api/v1/inventory/history/purge",
        headers=_make_headers(token_owner, TENANT_ALPHA),
    )
    assert res_owner_purge.status_code == 204

    # 5. Soporte Superuser God -> 204 No Content en ruta `/api/v1/inventory/history`
    token_god = _create_token(
        user_id=999,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.purge"],
        hierarchy_rank=0,
        is_superuser_god=True,
    )
    res_god_purge = await async_client.delete(
        "/api/v1/inventory/history",
        headers=_make_headers(token_god, TENANT_ALPHA),
    )
    assert res_god_purge.status_code == 204


@pytest.mark.asyncio
async def test_explicit_deny_blocks_access_even_with_role_grants(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que un `explicit_denies` anule los permisos otorgados en el rol."""
    token_denied = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
        explicit_denies=["inventory.history.read"],
    )
    res = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=_make_headers(token_denied, TENANT_ALPHA),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_session_killswitch_revocation_blocks_history_access(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que revocar el JTI de sesión bloquee inmediatamente solicitudes con 401."""
    jti = "revoked_session_kardex_history_14"
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
        jti=jti,
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Funciona antes de revocación
    res_ok = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers,
    )
    assert res_ok.status_code == 200

    # 2. Kill-switch: revocar token
    revoke_session_token(jti=jti)

    # 3. Bloqueado tras revocación
    res_blocked = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers,
    )
    assert res_blocked.status_code == 401


# ============================================================================
# VECTOR 3: RESILIENCIA CONTRA INYECCIONES SQL Y VALIDACIÓN DE FILTROS
# ============================================================================


@pytest.mark.asyncio
async def test_sql_injection_payloads_in_filter_parameters_sanitized(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que parámetros de filtrado conteniendo inyecciones SQL (SQLi)
    no provoquen fallos de sintaxis, no escapen del filtro de tenant
    y retornen respuestas sanitizadas.
    """
    _inventory_service.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("15.0000"),
        unit_cost=Decimal("100.00"),
        actor_user_id=101,
        tenant_id=TENANT_ALPHA,
    )

    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read", "inventory.history.export"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # Vectores SQLi en bodega_id, producto_id, tipo_movimiento y usuario_busqueda
    sqli_params_list = [
        {"bodega_id": "1' OR '1'='1"},
        {"producto_id": "10; DROP TABLE registro_stock;--"},
        {"tipo_movimiento": "' UNION SELECT * FROM users--"},
        {"usuario_busqueda": "admin'--"},
        {"user_search": "'; EXEC xp_cmdshell('dir');--"},
    ]

    for params in sqli_params_list:
        # Prueba en endpoint paginado
        res_page = await async_client.get(
            "/api/v1/inventory/history/paginated",
            params=params,
            headers=headers,
        )
        assert res_page.status_code == 200
        # No debe colapsar el backend ni devolver registros no autorizados
        data = res_page.json()
        assert isinstance(data["items"], list)

        # Prueba en endpoint CSV
        res_csv = await async_client.get(
            "/api/v1/inventory/history/export-csv",
            params=params,
            headers=headers,
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["Content-Type"]


@pytest.mark.asyncio
async def test_date_range_validation_prevents_logical_anomalies(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que cuando fecha_desde sea posterior a fecha_hasta, el servicio
    lance validación de dominio normalizada RFC 7807 sin procesar datos.
    """
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read", "inventory.history.export"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    params = {
        "fecha_desde": "2026-12-31",
        "fecha_hasta": "2026-01-01",
    }

    # En endpoint paginado
    res_page = await async_client.get(
        "/api/v1/inventory/history/paginated",
        params=params,
        headers=headers,
    )
    assert res_page.status_code in (400, 422)

    # En endpoint CSV
    res_csv = await async_client.get(
        "/api/v1/inventory/history/export-csv",
        params=params,
        headers=headers,
    )
    assert res_csv.status_code in (400, 422)


@pytest.mark.asyncio
async def test_malicious_date_format_rejected_by_pydantic_validation(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que strings maliciosos en fechas sean interceptados con 422."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read"],
    )
    res = await async_client.get(
        "/api/v1/inventory/history/paginated?fecha_desde=not-a-date' OR 1=1--",
        headers=_make_headers(token, TENANT_ALPHA),
    )
    assert res.status_code == 422


# ============================================================================
# VECTOR 4: PREVENCIÓN DE INYECCIÓN CSV EN SERVIDOR (CWE-1236 FORMULA INJECTION)
# ============================================================================


@pytest.mark.asyncio
async def test_server_side_csv_injection_formula_neutralization(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la exportación streaming de CSV neutralice completamente vectores
    de Formula Injection (CWE-1236) anteponiendo comilla simple `'` ante prefijos
    peligrosos (`=`, `+`, `-`, `@`, `\\t`, `\\r`), e incluya UTF-8 BOM.
    """
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.export", "inventory.history.view_users"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # Registramos producto, bodega y usuario con payloads maliciosos de fórmulas DDE
    _history_service.set_product_info(88, "=cmd|'/C calc'!A0", "UN")
    _history_service.set_warehouse_info(1, "+BodegaExploit")
    _history_service.set_user_info(77, nombre_visible="@InjectedFormula")

    _inventory_service.register_movement(
        producto_id=88,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("5.0000"),
        unit_cost=Decimal("500.00"),
        actor_user_id=77,
        documento_referencia="-DDE_COMMAND_EXEC",
        tenant_id=TENANT_ALPHA,
    )

    res = await async_client.get(
        "/api/v1/inventory/history/export-csv",
        headers=headers,
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("Content-Type", "")
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert f"auditoria_inventario_{date.today().isoformat()}.csv" in res.headers.get("Content-Disposition", "")

    raw_bytes = res.content
    text_content = raw_bytes.decode("utf-8")

    # 1. UTF-8 BOM obligatorio
    assert text_content.startswith("\ufeff")
    assert raw_bytes[:3] == b"\xef\xbb\xbf"

    # 2. Comilla simple antepuesta en fórmulas
    assert "'=cmd|'/C calc'!A0" in text_content
    assert "'+BodegaExploit" in text_content
    assert "'@InjectedFormula" in text_content
    assert "'-DDE_COMMAND_EXEC" in text_content


# ============================================================================
# VECTOR 5: PRIVACIDAD DE DATOS, ANONIMIZACIÓN Y REDACCIÓN PII
# ============================================================================


@pytest.mark.asyncio
async def test_user_pii_anonymization_without_view_users_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que si el usuario carece del permiso 'inventory.history.view_users',
    tanto en la respuesta paginada como en el CSV la columna o campo de usuario
    sea anonimizado deterministamente a 'Operador Autorizado'.
    """
    _history_service.set_product_info(10, "Aceite de Oliva", "LT")
    _history_service.set_warehouse_info(1, "Bodega Principal")
    _history_service.set_user_info(
        55,
        nombre_visible="Juan Carlos Pérez",
        email="juan.perez@oppytec.cl",
    )

    _inventory_service.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("3500.00"),
        actor_user_id=55,
        tenant_id=TENANT_ALPHA,
    )

    # 1. Usuario SIN permiso 'inventory.history.view_users'
    token_anon = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.history.read", "inventory.history.export"],
        is_holding_owner=False,
    )
    headers_anon = _make_headers(token_anon, TENANT_ALPHA)

    # API Paginada anonimizada
    res_page_anon = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_anon,
    )
    assert res_page_anon.status_code == 200
    data_anon = res_page_anon.json()
    item_anon = data_anon["items"][0]
    assert item_anon["user_display_name"] == "Operador Autorizado"
    assert "Juan" not in item_anon["user_display_name"]
    assert "perez@oppytec.cl" not in str(data_anon)

    # CSV anonimizado
    res_csv_anon = await async_client.get(
        "/api/v1/inventory/history/export-csv",
        headers=headers_anon,
    )
    assert res_csv_anon.status_code == 200
    csv_text_anon = res_csv_anon.content.decode("utf-8")
    assert "Operador Autorizado" in csv_text_anon
    assert "Juan Carlos Pérez" not in csv_text_anon
    assert "juan.perez@oppytec.cl" not in csv_text_anon

    # 2. Usuario CON permiso 'inventory.history.view_users'
    token_identified = _create_token(
        user_id=102,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "inventory.history.read",
            "inventory.history.export",
            "inventory.history.view_users",
        ],
    )
    headers_ident = _make_headers(token_identified, TENANT_ALPHA)

    res_page_ident = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_ident,
    )
    assert res_page_ident.status_code == 200
    item_ident = res_page_ident.json()["items"][0]
    assert item_ident["user_display_name"] == "Juan Carlos Pérez"


def test_scrub_audit_payload_and_logs_pii_redaction() -> None:
    """
    Verifica que la función `scrub_audit_payload` y `format_history_audit_log`
    redacten correos electrónicos, nombres de usuario y secretos con `[REDACTED]`.
    """
    raw_payload = {
        "email": "confidential_admin@oppytec.cl",
        "username": "secret_user_99",
        "nested": {
            "mail": "employee@oppytec.com",
            "note": "Operador reportó merma desde contacto@dominio.cl",
        },
        "password": "SuperSecretPassword123!",
        "token": "bearer_jwt_secret_token",
    }

    scrubbed = scrub_audit_payload(raw_payload)
    assert scrubbed["email"] == REDACTED_MARKER
    assert scrubbed["username"] == REDACTED_MARKER
    assert scrubbed["password"] == REDACTED_MARKER
    assert scrubbed["token"] == REDACTED_MARKER

    nested = scrubbed["nested"]
    assert isinstance(nested, dict)
    assert nested["mail"] == REDACTED_MARKER
    assert REDACTED_MARKER in str(nested["note"])
    assert "contacto@dominio.cl" not in str(nested["note"])

    formatted_log = format_history_audit_log("INFO", "test_action", raw_payload)
    assert "confidential_admin@oppytec.cl" not in formatted_log
    assert "SuperSecretPassword123!" not in formatted_log


def test_kardex_history_schemas_reject_extra_attributes() -> None:
    """Verifica que los esquemas prohíban atributos no declarados (anti Mass Assignment)."""
    with pytest.raises(Exception):
        KardexHistoryItemResponse(
            id=1,
            created_at=date.today(),
            fecha_recuento=date.today(),
            producto_id=1,
            nombre_producto="Test",
            unidad_medida="UN",
            bodega_id=1,
            nombre_bodega="Central",
            tipo_movimiento="ENTRADA",
            cantidad=Decimal("1"),
            saldo_resultante=Decimal("1"),
            costo_unitario_ppp=Decimal("100"),
            costo_total_movimiento=Decimal("100"),
            actor_user_id=1,
            user_display_name="Operador",
            injected_admin_field="MALICIOUS_EXTRA_PAYLOAD",  # type: ignore[call-arg]
        )
