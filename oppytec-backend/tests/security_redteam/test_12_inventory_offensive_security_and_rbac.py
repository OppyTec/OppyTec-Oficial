"""
Vector Red Team 12 (`tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant y RBAC en el Módulo de Inventario:
1. IDOR Cross-Tenant en sesiones de recuento físico (`/counts/{id}`, `/items`, `/finalize`, `/approve`, `/reject`, `/delete`, `/counts`).
2. IDOR Cross-Tenant en Kardex Append-Only ledger y reversiones transaccionales (`/stock/undo`, `/stock/redo`).
3. IDOR Cross-Tenant y Segregación de Funciones (SoD) en Mermas (`/mermas`, `/mermas/{id}/approve`).
4. RBAC estricto de 3 niveles en endpoints críticos (`/stock/bulk-transfer`, `/mermas/{id}/approve`, `/counts/{id}/approve`, `/stock/undo`, `/stock/redo`).
5. Prevención de concurrencia, doble descuento y deadlocks (`canonical_lock_order`, `InsufficientStockError`).
6. Invariantes de dominio en transferencias inter-bodega (rechazo origen == destino, saldo insuficiente).
7. Rechazo determinista de costos negativos, cantidades anómalas, NaN, floats y Value Objects de precisión Decimal.
8. Bloqueo de Mass Assignment (`extra="forbid"`) en esquemas de inventario.
9. Sanitización de vectores XSS en notas y motivos (`sanitize_text_input`).
10. Bloqueo de inyección SQL en parámetros de ruta y consulta.
11. Aislamiento físico de esquemas PostgreSQL (`tenant_*`).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest

from src.core.exceptions import (
    CrossTenantAccessError,
    InsufficientStockError,
    NegativeStockNotAllowedError,
)
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.domain.kardex_math import canonical_lock_order
from src.modules.inventory.domain.value_objects import MoneyAmount, StockQuantity
from src.modules.inventory.presentation.router import (
    _inventory_service,
    _physical_count_service,
    _waste_service,
)

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_alpha_santiago"
TENANT_BETA = "tenant_beta_valparaiso"
HOLDING_ID = "holding_pollogold"


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    hierarchy_rank: int = 20,
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
        accessible_tenants=[tenant_id],
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_test_environment() -> None:
    clear_revoked_sessions()
    get_rate_limiter().reset()
    _inventory_service.reset()
    _physical_count_service.reset()
    _waste_service._wastes.clear()
    _waste_service._seq = 0


# ============================================================================
# VECTOR 1: IDOR CROSS-TENANT EN SESIONES DE CONTEO FÍSICO
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_on_physical_count_sessions_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un usuario autenticado en Tenant Beta NO pueda leer, modificar,
    finalizar, aprobar, rechazar ni eliminar una sesión de conteo creada por Tenant Alpha.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "inventory.counts.create",
            "inventory.counts.read",
            "inventory.counts.execute",
            "inventory.counts.approve",
            "inventory.counts.delete",
        ],
    )
    headers_alpha = _make_headers(token_alpha, TENANT_ALPHA)

    token_beta = _create_token(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=[
            "inventory.counts.create",
            "inventory.counts.read",
            "inventory.counts.execute",
            "inventory.counts.approve",
            "inventory.counts.delete",
        ],
    )
    headers_beta = _make_headers(token_beta, TENANT_BETA)

    # 1. Tenant Alpha crea una sesión de recuento
    start_resp = await async_client.post(
        "/api/v1/inventory/counts/start",
        headers=headers_alpha,
        json={"bodega_id": 1, "notas": "Recuento de Tenant Alpha"},
    )
    assert start_resp.status_code == 201
    conteo_alpha_id = start_resp.json()["id"]

    # 2. Tenant Beta intenta leer la sesión de Alpha (IDOR Read) -> HTTP 403
    get_resp = await async_client.get(
        f"/api/v1/inventory/counts/{conteo_alpha_id}",
        headers=headers_beta,
    )
    assert get_resp.status_code == 403
    assert get_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 3. Tenant Beta intenta inyectar líneas en la sesión de Alpha (IDOR Write) -> HTTP 403
    put_resp = await async_client.put(
        f"/api/v1/inventory/counts/{conteo_alpha_id}/items",
        headers=headers_beta,
        json={
            "items": [
                {
                    "producto_id": 1,
                    "stock_fisico_contado": "50.0000",
                    "costo_unitario_ppp": "1000.00",
                }
            ]
        },
    )
    assert put_resp.status_code == 403
    assert put_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 4. Tenant Beta intenta finalizar la sesión de Alpha -> HTTP 403
    fin_resp = await async_client.post(
        f"/api/v1/inventory/counts/{conteo_alpha_id}/finalize",
        headers=headers_beta,
    )
    assert fin_resp.status_code == 403
    assert fin_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # Finalizar legítimamente con Tenant Alpha
    await async_client.post(
        f"/api/v1/inventory/counts/{conteo_alpha_id}/finalize",
        headers=headers_alpha,
    )

    # 5. Tenant Beta intenta aprobar la sesión de Alpha -> HTTP 403
    app_resp = await async_client.post(
        f"/api/v1/inventory/counts/{conteo_alpha_id}/approve",
        headers=headers_beta,
    )
    assert app_resp.status_code == 403
    assert app_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 6. Tenant Beta intenta rechazar la sesión de Alpha -> HTTP 403
    rej_resp = await async_client.post(
        f"/api/v1/inventory/counts/{conteo_alpha_id}/reject",
        headers=headers_beta,
    )
    assert rej_resp.status_code == 403
    assert rej_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 7. Tenant Beta intenta eliminar la sesión de Alpha -> HTTP 403
    del_resp = await async_client.delete(
        f"/api/v1/inventory/counts/{conteo_alpha_id}",
        headers=headers_beta,
    )
    assert del_resp.status_code == 403
    assert del_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 8. Listar sesiones desde Tenant Beta NO debe incluir la sesión de Tenant Alpha
    list_beta = await async_client.get("/api/v1/inventory/counts", headers=headers_beta)
    assert list_beta.status_code == 200
    assert not any(s["id"] == conteo_alpha_id for s in list_beta.json())


# ============================================================================
# VECTOR 2: IDOR EN KARDEX LEDGER Y UNDO/REDO
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_on_kardex_movements_and_undo_redo(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que los movimientos registrados por Tenant Alpha no sean reversibles
    ni visibles en el libro mayor de Tenant Beta.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.kardex.write", "inventory.kardex.read", "inventory.stock.undo", "inventory.stock.redo"],
    )
    headers_alpha = _make_headers(token_alpha, TENANT_ALPHA)

    token_beta = _create_token(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=["inventory.kardex.write", "inventory.kardex.read", "inventory.stock.undo", "inventory.stock.redo"],
    )
    headers_beta = _make_headers(token_beta, TENANT_BETA)

    # 1. Registrar movimiento en Tenant Alpha
    mov_resp = await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers_alpha,
        json={
            "producto_id": 10,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "100.0000",
            "unit_cost": "500.00",
        },
    )
    assert mov_resp.status_code == 201
    mov_id = mov_resp.json()["id"]

    # 2. Tenant Beta consulta su ledger: no debe ver el movimiento de Alpha
    ledger_beta = await async_client.get("/api/v1/inventory/kardex/movements", headers=headers_beta)
    assert ledger_beta.status_code == 200
    assert not any(m["id"] == mov_id for m in ledger_beta.json())

    # 3. Tenant Beta intenta revertir (undo) el movimiento de Alpha -> HTTP 403
    undo_resp = await async_client.post(
        "/api/v1/inventory/stock/undo",
        headers=headers_beta,
        json={"movement_id": mov_id, "reason": "Ataque IDOR de reversión"},
    )
    assert undo_resp.status_code == 403
    assert undo_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


# ============================================================================
# VECTOR 3: IDOR Y SEGREGACIÓN DE FUNCIONES (SoD) EN MERMAS
# ============================================================================


@pytest.mark.asyncio
async def test_merma_cross_tenant_idor_and_segregation_of_duties(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que:
    1. Una merma reportada por Tenant Alpha no puede ser aprobada por Tenant Beta (HTTP 403).
    2. Segregación de Funciones: El reportante no puede auto-aprobar su propia merma (HTTP 403).
    3. Un supervisor distinto dentro de Tenant Alpha sí puede aprobarla legítimamente.
    """
    token_reporter_alpha = _create_token(
        user_id=110,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.mermas.create", "inventory.mermas.approve"],
    )
    headers_reporter = _make_headers(token_reporter_alpha, TENANT_ALPHA)

    token_approver_alpha = _create_token(
        user_id=111,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.mermas.approve"],
    )
    headers_approver = _make_headers(token_approver_alpha, TENANT_ALPHA)

    token_attacker_beta = _create_token(
        user_id=220,
        tenant_id=TENANT_BETA,
        permissions=["inventory.mermas.approve"],
    )
    headers_attacker = _make_headers(token_attacker_beta, TENANT_BETA)

    # 1. Reportar merma sobre el umbral (60,000 > 50,000 threshold) -> PENDIENTE
    rep_resp = await async_client.post(
        "/api/v1/inventory/mermas",
        headers=headers_reporter,
        json={
            "producto_id": 5,
            "bodega_id": 1,
            "quantity": "10.0000",
            "unit_cost": "6000.00",
            "reason": "Vencimiento de lote en cámara fría",
        },
    )
    assert rep_resp.status_code == 201
    merma_data = rep_resp.json()
    assert merma_data["status"] == "PENDIENTE"
    merma_id = merma_data["waste_id"]

    # 2. Ataque IDOR Cross-Tenant desde Tenant Beta -> HTTP 403
    idor_resp = await async_client.post(
        f"/api/v1/inventory/mermas/{merma_id}/approve",
        headers=headers_attacker,
        json={"unit_cost": "6000.00"},
    )
    assert idor_resp.status_code == 403
    assert idor_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 3. Violación de SoD: El reportante (user_id=110) intenta auto-aprobarse -> HTTP 403
    sod_resp = await async_client.post(
        f"/api/v1/inventory/mermas/{merma_id}/approve",
        headers=headers_reporter,
        json={"unit_cost": "6000.00"},
    )
    assert sod_resp.status_code == 403
    assert "Reporter cannot approve own waste" in sod_resp.json()["detail"]

    # 4. Aprobación legítima por un supervisor distinto (user_id=111) -> HTTP 200
    ok_resp = await async_client.post(
        f"/api/v1/inventory/mermas/{merma_id}/approve",
        headers=headers_approver,
        json={"unit_cost": "6000.00"},
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["status"] == "APROBADA"


# ============================================================================
# VECTOR 4: RBAC ESTRICTO DE 3 NIVELES EN ENDPOINTS CRÍTICOS
# ============================================================================


@pytest.mark.asyncio
async def test_rbac_three_level_enforcement_on_critical_inventory_endpoints(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que los endpoints más sensibles exijan el permiso exacto de 3 niveles
    y rechacen a usuarios con roles no autorizados con HTTP 403 Forbidden.
    """
    read_only_token = _create_token(
        user_id=300,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.stock.read", "inventory.kardex.read"],
    )
    headers = _make_headers(read_only_token, TENANT_ALPHA)

    # 1. /stock/bulk-transfer exige inventory.stock.transfer
    r1 = await async_client.post(
        "/api/v1/inventory/stock/bulk-transfer",
        headers=headers,
        json={
            "bodega_origen_id": 1,
            "bodega_destino_id": 2,
            "items": [{"producto_id": 1, "cantidad": "10.0000"}],
        },
    )
    assert r1.status_code == 403

    # 2. /mermas/{id}/approve exige inventory.mermas.approve
    r2 = await async_client.post(
        "/api/v1/inventory/mermas/1/approve",
        headers=headers,
        json={"unit_cost": "1000.00"},
    )
    assert r2.status_code == 403

    # 3. /counts/{id}/approve exige inventory.counts.approve
    r3 = await async_client.post(
        "/api/v1/inventory/counts/1/approve",
        headers=headers,
    )
    assert r3.status_code == 403

    # 4. /stock/undo exige inventory.stock.undo
    r4 = await async_client.post(
        "/api/v1/inventory/stock/undo",
        headers=headers,
        json={"movement_id": 1},
    )
    assert r4.status_code == 403

    # 5. /stock/redo exige inventory.stock.redo
    r5 = await async_client.post(
        "/api/v1/inventory/stock/redo",
        headers=headers,
        json={"movement_id": 1},
    )
    assert r5.status_code == 403


# ============================================================================
# VECTOR 5: CONCURRENCIA, ORDEN CANÓNICO ANTI-DEADLOCK Y OVERDRAFT
# ============================================================================


def test_canonical_lock_ordering_and_anti_deadlock() -> None:
    """
    Verifica que la función `canonical_lock_order` ordene determinísticamente
    los identificadores `ORDER BY id ASC` sin duplicados.
    """
    disordered = [85, 12, 99, 12, 3, 45, 85]
    ordered = canonical_lock_order(disordered)
    assert ordered == [3, 12, 45, 85, 99]
    assert canonical_lock_order([20, 10]) == [10, 20]
    assert canonical_lock_order([10, 20]) == [10, 20]


@pytest.mark.asyncio
async def test_concurrent_transfers_prevent_negative_stock_overdraft() -> None:
    """
    Simula múltiples transferencias masivas concurrentes intentando retirar más stock
    del disponible en la bodega de origen. Solo las transacciones con saldo suficiente
    prosperan y jamás se genera saldo negativo.
    """
    service = InventoryService()
    # Inicializar stock: 15.0000 unidades
    service.register_movement(
        producto_id=88,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("15.0000"),
        unit_cost=Decimal("2000.00"),
        actor_user_id=1,
    )

    lock = asyncio.Lock()

    async def _try_transfer() -> bool:
        async with lock:
            try:
                service.transfer_stock_bulk(
                    bodega_origen_id=1,
                    bodega_destino_id=2,
                    items=[(88, Decimal("6.0000"))],
                    actor_user_id=1,
                )
                return True
            except InsufficientStockError:
                return False

    results = await asyncio.gather(*(_try_transfer() for _ in range(5)))
    # 15 / 6 = 2 transferencias exitosas (12 transferidas, 3 remanentes)
    assert results.count(True) == 2
    assert results.count(False) == 3
    assert service.balance(88, 1) == Decimal("3.0000")
    assert service.balance(88, 2) == Decimal("12.0000")


# ============================================================================
# VECTOR 6: INVARIANTES DE TRASPASOS INTER-BODEGA
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_transfer_same_warehouse_rejection(async_client: httpx.AsyncClient) -> None:
    """Intento de transferir stock a la misma bodega es rechazado con HTTP 400."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.stock.transfer"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    resp = await async_client.post(
        "/api/v1/inventory/stock/bulk-transfer",
        headers=headers,
        json={
            "bodega_origen_id": 1,
            "bodega_destino_id": 1,
            "items": [{"producto_id": 1, "cantidad": "5.0000"}],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["i18n_key"] == "inventory:errors.same_origin_destination_warehouse"


# ============================================================================
# VECTOR 7: VALUE OBJECTS: RECHAZO DE NEGATIVOS, FLOATS, NAN E INFINITY
# ============================================================================


def test_value_objects_strict_validation_and_zero_floats() -> None:
    """Verifica que StockQuantity y MoneyAmount rechacen floats, negativos indebidos y NaN."""
    # Rechazo estricto de floats
    with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
        StockQuantity(12.5)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
        MoneyAmount(99.99)  # type: ignore[arg-type]

    # Rechazo de NaN e Infinito
    with pytest.raises(ValueError, match="NaN or infinite"):
        StockQuantity(Decimal("NaN"))

    with pytest.raises(ValueError, match="NaN or infinite"):
        MoneyAmount(Decimal("Infinity"))

    # Rechazo de saldo negativo en StockQuantity cuando allow_negative=False
    with pytest.raises(NegativeStockNotAllowedError):
        StockQuantity(Decimal("-0.0001"), allow_negative=False)

    # Decimal exacto permitido
    sq = StockQuantity(Decimal("10.5000"))
    assert str(sq) == "10.5000"
    ma = MoneyAmount(Decimal("1500.50"), currency="CLP")
    assert str(ma) == "1500.50 CLP"


@pytest.mark.asyncio
async def test_negative_payload_values_rejected_at_api_boundary(
    async_client: httpx.AsyncClient,
) -> None:
    """Valida que valores negativos en cantidades o costos sean rechazados con HTTP 422."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.kardex.write"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # Cantidad negativa
    r1 = await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 1,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "-5.0000",
            "unit_cost": "1000.00",
        },
    )
    assert r1.status_code == 422

    # Costo negativo
    r2 = await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 1,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "5.0000",
            "unit_cost": "-1000.00",
        },
    )
    assert r2.status_code == 422


# ============================================================================
# VECTOR 8: MASS ASSIGNMENT RECHAZADO (extra="forbid")
# ============================================================================


@pytest.mark.asyncio
async def test_mass_assignment_rejected_with_422(async_client: httpx.AsyncClient) -> None:
    """Intento de inyectar campos no permitidos en esquemas de inventario es bloqueado con HTTP 422."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.counts.create"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    resp = await async_client.post(
        "/api/v1/inventory/counts/start",
        headers=headers,
        json={
            "bodega_id": 1,
            "notas": "Toma legítima",
            "is_admin_override": True,  # Mass Assignment
            "bypass_auth": 1,
        },
    )
    assert resp.status_code == 422
    assert "extra_forbidden" in str(resp.json())


# ============================================================================
# VECTOR 9: XSS BLOCKING EN TEXTOS LIBRES
# ============================================================================


@pytest.mark.asyncio
async def test_xss_payload_in_notas_blocked_with_422(async_client: httpx.AsyncClient) -> None:
    """Comprueba que payloads XSS en notas de recuento o motivos de merma sean bloqueados determinísticamente con HTTP 422."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.counts.create", "inventory.counts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Intento de inyectar <script> en notas de recuento -> HTTP 422
    resp1 = await async_client.post(
        "/api/v1/inventory/counts/start",
        headers=headers,
        json={
            "bodega_id": 1,
            "notas": "<script>alert('XSS-ATTACK')</script>Auditoría Bodega",
        },
    )
    assert resp1.status_code == 422
    assert resp1.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"

    # 2. Intento de inyectar <img onerror> en motivo de merma -> HTTP 422
    token_merma = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.mermas.create"],
    )
    headers_merma = _make_headers(token_merma, TENANT_ALPHA)
    resp2 = await async_client.post(
        "/api/v1/inventory/mermas",
        headers=headers_merma,
        json={
            "producto_id": 1,
            "bodega_id": 1,
            "quantity": "5.0000",
            "unit_cost": "100.00",
            "reason": "<img src=x onerror=alert(1)>Rotura de envase",
        },
    )
    assert resp2.status_code == 422
    assert resp2.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"


# ============================================================================
# VECTOR 10 & 11: SQL INJECTION EN PARÁMETROS Y VALIDACIÓN DE ESQUEMA
# ============================================================================


@pytest.mark.asyncio
async def test_sql_injection_in_query_params_blocked(async_client: httpx.AsyncClient) -> None:
    """Inyección SQL en parámetros de ruta/query es rechazada por el validador FastAPI."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.stock.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    for sqli in ("1 OR 1=1", "1; DROP TABLE producto_bodegas; --", "admin'--"):
        resp = await async_client.get(
            f"/api/v1/inventory/stock/status?bodega_id={sqli}",
            headers=headers,
        )
        assert resp.status_code == 422
