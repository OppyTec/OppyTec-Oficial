"""
oppytec-backend/tests/modules/inventory/test_history_endpoints.py
Pruebas de integración HTTP y seguridad RBAC para los endpoints de Historial y Auditoría de Kardex (Fase 2):
- `GET /api/v1/inventory/history/paginated`: Paginación server-side, orden determinista y filtros multi-criterio.
- Anonimización automática de identidad si falta `inventory.history.view_users` ('Operador Autorizado').
- `GET /api/v1/inventory/history/export-csv`: Streaming CSV con UTF-8 BOM (\uFEFF) y sanitización anti Formula Injection (CWE-1236).
- `DELETE /api/v1/inventory/history`: Purga restringida exclusivamente al Propietario (rank 0 / is_holding_owner).
- Respuestas de error normalizadas en RFC 7807 (ProblemDetails).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from src.core.security import create_access_token
from src.modules.inventory.presentation.router import (
    _history_service,
    _inventory_service,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant_inventory_test"
HOLDING_ID = "holding_inventory_test"


def _make_headers(
    permissions: list[str],
    user_id: int = 101,
    *,
    is_holding_owner: bool = False,
    hierarchy_rank: int = 30,
    is_superuser_god: bool = False,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_ID,
        holding_id=HOLDING_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
        is_holding_owner=is_holding_owner,
        hierarchy_rank=hierarchy_rank,
        is_superuser_god=is_superuser_god,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.fixture(autouse=True)
def _reset_history_and_inventory_state() -> None:
    """Limpia el ledger y servicios antes de cada prueba para aislamiento total."""
    _inventory_service.reset()
    _history_service.reset()


@pytest.mark.asyncio
async def test_history_paginated_and_deltas(async_client: httpx.AsyncClient) -> None:
    """
    Verifica que /inventory/history/paginated soporte paginación server-side (total, skip, limit, page, total_pages),
    ordenamiento determinista (más recientes primero) y cálculo algebraico de deltas before/after.
    """
    headers = _make_headers(["inventory.history.read", "inventory.history.view_users"])

    # Configuramos metadata enriquecida
    _history_service.set_product_info(10, "Carne Vacuno Posta", "KG")
    _history_service.set_warehouse_info(1, "Bodega Principal Frío")
    _history_service.set_user_info(101, nombre_visible="Mario Rossi", email="mario@oppytec.cl")

    # Registramos 7 movimientos
    for _i in range(1, 8):
        _inventory_service.register_movement(
            producto_id=10,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("10.0000"),
            unit_cost=Decimal("5000.00"),
            actor_user_id=101,
            tenant_id=TENANT_ID,
        )

    # 1. Página 1 con limit=3
    response_p1 = await async_client.get(
        "/api/v1/inventory/history/paginated?skip=0&limit=3",
        headers=headers,
    )
    assert response_p1.status_code == 200
    data_p1 = response_p1.json()
    assert data_p1["total"] == 7
    assert data_p1["skip"] == 0
    assert data_p1["limit"] == 3
    assert data_p1["page"] == 1
    assert data_p1["total_pages"] == 3
    assert len(data_p1["items"]) == 3

    # Verificamos campos enriquecidos y cálculo algebraico de deltas
    first_item = data_p1["items"][0]
    assert first_item["nombre_producto"] == "Carne Vacuno Posta"
    assert first_item["unidad_medida"] == "KG"
    assert first_item["nombre_bodega"] == "Bodega Principal Frío"
    assert first_item["user_display_name"] == "Mario Rossi"
    assert Decimal(str(first_item["saldo_resultante"])) == Decimal("70.0000")
    # Para entrada de 10: delta_before = 70 - 10 = 60, delta_after = 70
    assert Decimal(str(first_item["delta_before"])) == Decimal("60.0000")
    assert Decimal(str(first_item["delta_after"])) == Decimal("70.0000")

    # 2. Página 2 con limit=3
    response_p2 = await async_client.get(
        "/api/v1/inventory/history/paginated?skip=3&limit=3",
        headers=headers,
    )
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()
    assert data_p2["page"] == 2
    assert len(data_p2["items"]) == 3

    # 3. Página 3 con limit=3
    response_p3 = await async_client.get(
        "/api/v1/inventory/history/paginated?skip=6&limit=3",
        headers=headers,
    )
    assert response_p3.status_code == 200
    data_p3 = response_p3.json()
    assert data_p3["page"] == 3
    assert len(data_p3["items"]) == 1


@pytest.mark.asyncio
async def test_history_multi_criteria_filters(async_client: httpx.AsyncClient) -> None:
    """
    Verifica los filtros multi-criterio:
    - Por bodega (`bodega_id`)
    - Por producto (`producto_id`)
    - Por tipo de movimiento (`tipo_movimiento`)
    - Por rango de fechas (`fecha_desde`, `fecha_hasta`)
    - Por búsqueda predictiva de usuario (`user_search`)
    """
    headers = _make_headers(["inventory.history.read", "inventory.history.view_users"])

    _history_service.set_product_info(101, "Harina Selecta", "KG")
    _history_service.set_product_info(202, "Levadura Fresca", "UN")
    _history_service.set_warehouse_info(1, "Bodega Central")
    _history_service.set_warehouse_info(2, "Bodega Panadería")
    _history_service.set_user_info(50, nombre_visible="Carlos Cocinero", email="carlos@oppytec.cl")
    _history_service.set_user_info(60, nombre_visible="Ana Repostera", email="ana@oppytec.cl")

    today = date.today()
    past_date = today - timedelta(days=10)

    # Asiento 1: Harina en Bodega 1, Carlos, ENTRADA
    _inventory_service.register_movement(
        producto_id=101,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("1200.00"),
        actor_user_id=50,
        fecha_recuento=today,
        tenant_id=TENANT_ID,
    )

    # Asiento 2: Harina en Bodega 1, Carlos, MERMA
    _inventory_service.register_movement(
        producto_id=101,
        bodega_id=1,
        movement_type="MERMA",
        quantity=Decimal("5.0000"),
        unit_cost=Decimal("1200.00"),
        actor_user_id=50,
        motivo_merma="daño",
        descripcion_merma="Saco roto en traslado",
        fecha_recuento=today,
        tenant_id=TENANT_ID,
    )

    # Asiento 3: Levadura en Bodega 2, Ana, AJUSTE_POSITIVO, fecha pasada
    _inventory_service.register_movement(
        producto_id=202,
        bodega_id=2,
        movement_type="AJUSTE_POSITIVO",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("500.00"),
        actor_user_id=60,
        fecha_recuento=past_date,
        tenant_id=TENANT_ID,
    )

    # 1. Filtro por Bodega 2 -> solo Levadura
    res_b2 = await async_client.get(
        "/api/v1/inventory/history/paginated?bodega_id=2",
        headers=headers,
    )
    assert res_b2.status_code == 200
    data_b2 = res_b2.json()
    assert data_b2["total"] == 1
    assert data_b2["items"][0]["producto_id"] == 202

    # 2. Filtro por Producto 101 -> Harina (2 asientos)
    res_p101 = await async_client.get(
        "/api/v1/inventory/history/paginated?producto_id=101",
        headers=headers,
    )
    assert res_p101.status_code == 200
    assert res_p101.json()["total"] == 2

    # 3. Filtro por Tipo MERMA -> 1 asiento
    res_merma = await async_client.get(
        "/api/v1/inventory/history/paginated?tipo_movimiento=merma",
        headers=headers,
    )
    assert res_merma.status_code == 200
    data_merma = res_merma.json()
    assert data_merma["total"] == 1
    assert data_merma["items"][0]["motivo_merma"] == "daño"

    # 4. Filtro por Tipo 'ajuste' (debe capturar AJUSTE_POSITIVO)
    res_ajuste = await async_client.get(
        "/api/v1/inventory/history/paginated?tipo_movimiento=ajuste",
        headers=headers,
    )
    assert res_ajuste.status_code == 200
    assert res_ajuste.json()["total"] == 1

    # 5. Filtro por rango de fechas (excluyendo fecha pasada)
    res_dates = await async_client.get(
        f"/api/v1/inventory/history/paginated?fecha_desde={today.isoformat()}&fecha_hasta={today.isoformat()}",
        headers=headers,
    )
    assert res_dates.status_code == 200
    assert res_dates.json()["total"] == 2  # Asientos 1 y 2

    # 6. Búsqueda por usuario 'carlos'
    res_user = await async_client.get(
        "/api/v1/inventory/history/paginated?user_search=carlos",
        headers=headers,
    )
    assert res_user.status_code == 200
    assert res_user.json()["total"] == 2

    # 7. Búsqueda por usuario 'ana'
    res_ana = await async_client.get(
        "/api/v1/inventory/history/paginated?user_search=ana",
        headers=headers,
    )
    assert res_ana.status_code == 200
    assert res_ana.json()["total"] == 1
    assert res_ana.json()["items"][0]["user_display_name"] == "Ana Repostera"


@pytest.mark.asyncio
async def test_user_privacy_anonymization(async_client: httpx.AsyncClient) -> None:
    """
    Verifica que si el usuario autenticado no posee el permiso 'inventory.history.view_users',
    el campo `user_display_name` se anonimiza automáticamente a 'Operador Autorizado'.
    """
    _history_service.set_user_info(88, nombre_visible="Juan Confidencial", email="juan@oppytec.cl")

    _inventory_service.register_movement(
        producto_id=1,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("100.00"),
        actor_user_id=88,
        tenant_id=TENANT_ID,
    )

    # 1. Sin permiso 'inventory.history.view_users'
    headers_restricted = _make_headers(["inventory.history.read"])
    res_anon = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_restricted,
    )
    assert res_anon.status_code == 200
    items_anon = res_anon.json()["items"]
    assert len(items_anon) == 1
    assert items_anon[0]["user_display_name"] == "Operador Autorizado"

    # 2. Con permiso 'inventory.history.view_users'
    headers_authorized = _make_headers(["inventory.history.read", "inventory.history.view_users"])
    res_auth = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_authorized,
    )
    assert res_auth.status_code == 200
    items_auth = res_auth.json()["items"]
    assert len(items_auth) == 1
    assert items_auth[0]["user_display_name"] == "Juan Confidencial"


@pytest.mark.asyncio
async def test_csv_export_bom_and_formula_sanitization(async_client: httpx.AsyncClient) -> None:
    """
    Verifica que /inventory/history/export-csv:
    - Retorne HTTP 200 con cabecera Content-Disposition 'auditoria_inventario_{fecha}.csv'.
    - Inicie obligatoriamente con UTF-8 BOM (\uFEFF) para Microsoft Excel.
    - Neutralice vectores de Formula Injection (CWE-1236) anteponiendo comilla simple `'`
      si el texto inicia con '=', '+', '-', '@', '\t', '\r'.
    """
    headers = _make_headers(["inventory.history.export", "inventory.history.view_users"])

    # Registramos producto y asiento con payload DDE malicioso en notas y nombre
    _history_service.set_product_info(99, "=cmd|' /C calc'!A0", "UN")
    _history_service.set_warehouse_info(1, "+BodegaMaliciosa")
    _history_service.set_user_info(77, nombre_visible="@admin_root")

    _inventory_service.register_movement(
        producto_id=99,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("5.0000"),
        unit_cost=Decimal("1000.00"),
        actor_user_id=77,
        documento_referencia="-DDE_EXEC_INJECTION",
        tenant_id=TENANT_ID,
    )

    response = await async_client.get(
        "/api/v1/inventory/history/export-csv",
        headers=headers,
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("Content-Type", "")
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert f"auditoria_inventario_{date.today().isoformat()}.csv" in response.headers.get("Content-Disposition", "")

    raw_content = response.content
    text_content = raw_content.decode("utf-8")

    # 1. Verificación UTF-8 BOM (\uFEFF)
    assert text_content.startswith("\ufeff"), "El archivo CSV debe iniciar con UTF-8 BOM (\\uFEFF)"
    assert raw_content[:3] == b"\xef\xbb\xbf", "Los primeros 3 bytes deben ser el BOM UTF-8 exacto"

    # 2. Verificación de Sanitización Anti-Fórmulas CWE-1236
    # Producto que iniciaba con '=' debe estar prefijado con comilla simple: "'=cmd"
    assert "'=cmd|' /C calc'!A0" in text_content
    # Bodega que iniciaba con '+' debe estar prefijada con comilla simple: "'+BodegaMaliciosa"
    assert "'+BodegaMaliciosa" in text_content
    # Usuario que iniciaba con '@' debe estar prefijado con comilla simple: "'@admin_root"
    assert "'@admin_root" in text_content
    # Documento/nota que iniciaba con '-' debe estar prefijada con comilla simple: "'-DDE_EXEC_INJECTION"
    assert "'-DDE_EXEC_INJECTION" in text_content


@pytest.mark.asyncio
async def test_rbac_and_purge_history_authorization(async_client: httpx.AsyncClient) -> None:
    """
    Verifica las reglas de seguridad RBAC y la purga histórica:
    - 401 Unauthorized si no hay token Bearer (RFC 7807).
    - 403 Forbidden si falta 'inventory.history.read' o fallback 'inventory.kardex.read'.
    - Acceso exitoso mediante fallback con 'inventory.kardex.read'.
    - DELETE /inventory/history denegado si no es Propietario (403 Forbidden).
    - DELETE /inventory/history exitoso solo para rol Propietario con 'inventory.history.purge' (204 No Content).
    """
    # 1. Sin autenticación -> 401 Unauthorized RFC 7807
    res_no_auth = await async_client.get("/api/v1/inventory/history/paginated")
    assert res_no_auth.status_code == 401
    problem_401 = res_no_auth.json()
    assert problem_401["status"] == 401
    assert "detail" in problem_401

    # 2. Con permiso irrelevante -> 403 Forbidden RFC 7807
    headers_unauth = _make_headers(["procurement.orders.read"])
    res_forbidden = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_unauth,
    )
    assert res_forbidden.status_code == 403
    problem_403 = res_forbidden.json()
    assert problem_403["status"] == 403

    # 3. Acceso exitoso vía fallback con 'inventory.kardex.read'
    headers_fallback = _make_headers(["inventory.kardex.read"])
    res_fb = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_fallback,
    )
    assert res_fb.status_code == 200

    # 4. Registrar movimientos para probar purga
    _inventory_service.register_movement(
        producto_id=1,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("100.00"),
        actor_user_id=101,
        tenant_id=TENANT_ID,
    )

    # 5. DELETE sin permiso de purge -> 403 Forbidden
    headers_no_purge = _make_headers(["inventory.history.read"])
    res_del_no_perm = await async_client.delete(
        "/api/v1/inventory/history",
        headers=headers_no_purge,
    )
    assert res_del_no_perm.status_code == 403

    # 6. DELETE con 'inventory.history.purge' pero rol de empleado estándar (rank 30, no owner)
    headers_employee_with_perm = _make_headers(
        ["inventory.history.purge"],
        hierarchy_rank=30,
        is_holding_owner=False,
    )
    res_del_non_owner = await async_client.delete(
        "/api/v1/inventory/history",
        headers=headers_employee_with_perm,
    )
    assert res_del_non_owner.status_code == 403
    assert "Solo el Propietario" in res_del_non_owner.json()["detail"]

    # 7. DELETE con 'inventory.history.purge' y rol Propietario (is_holding_owner=True, rank 0) -> 204 No Content
    headers_owner = _make_headers(
        ["inventory.history.purge"],
        hierarchy_rank=0,
        is_holding_owner=True,
    )
    res_del_owner = await async_client.delete(
        "/api/v1/inventory/history",
        headers=headers_owner,
    )
    assert res_del_owner.status_code == 204

    # 8. Verificar que el historial quedó completamente purgado
    headers_read = _make_headers(["inventory.history.read"])
    res_after_purge = await async_client.get(
        "/api/v1/inventory/history/paginated",
        headers=headers_read,
    )
    assert res_after_purge.status_code == 200
    assert res_after_purge.json()["total"] == 0
    assert len(res_after_purge.json()["items"]) == 0
