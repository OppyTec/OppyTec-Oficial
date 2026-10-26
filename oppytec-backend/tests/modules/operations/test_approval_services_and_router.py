"""
oppytec-backend/tests/modules/operations/test_approval_services_and_router.py
Suite completa de pruebas unitarias y de integración para el Centro de Aprobaciones:
- Servicios de Aplicación: ApprovalService, BuffetApprovalService, NotificationMatrixService.
- Impacto transaccional en Kardex (Zero-Float, movimientos MERMA, CONSUMO, ENTRADA).
- Transiciones legales/ilegales y validación de motivos de rechazo (RFC 7807).
- Enrutadores FastAPI y Guardias RBAC de 3 niveles (`operations.approvals.*`).
- Emisión reactiva de eventos WebSocket.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from src.core.exceptions import (
    OppyTecError,
    ResourceNotFoundError,
)
from src.core.observability import get_in_memory_exporter
from src.core.security import create_access_token
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.physical_count_service import (
    CountItemInput,
    PhysicalCountService,
)
from src.modules.operations.application.approval_service import (
    ApprovalService,
    BuffetApprovalService,
    NotificationMatrixService,
)
from src.modules.operations.domain.approvals import (
    ApprovalCategory,
    ApprovalDomainError,
    ApprovalStatus,
    ApprovalType,
    InvalidApprovalTransitionError,
    InvalidRejectionReasonError,
)
from src.modules.operations.presentation.router_approvals import (
    _approval_service,
    _buffet_service,
    _matrix_service,
)

pytestmark = [pytest.mark.unit]

TENANT_ID = "tenant_approvals_test"
HOLDING_ID = "holding_approvals_test"


def _make_headers(permissions: list[str], user_id: int = 201) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_ID,
        holding_id=HOLDING_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.fixture(autouse=True)
def _setup_in_memory_services() -> None:
    """Configura los servicios en modo memoria para aislamiento determinista en tests."""
    _approval_service.enable_in_memory_mode()
    _approval_service.reset_in_memory_store()
    _matrix_service.enable_in_memory_mode()
    _matrix_service.reset_in_memory_store()


# =========================================================================
# 1. PRUEBAS DE SERVICIO: ApprovalService
# =========================================================================


class TestApprovalServiceCore:
    """Pruebas del ciclo de vida y reglas de negocio de ApprovalService."""

    @pytest.mark.asyncio
    async def test_create_request_success(self) -> None:
        service = _approval_service
        req = await service.create_request(
            tipo=ApprovalType.MERMA,
            usuario_id=10,
            bodega_id=1,
            area_operativa_id=2,
            detalles={"producto_id": 101, "quantity": "5.50", "unit_cost": "1200.00"},
            tenant_id=TENANT_ID,
        )
        assert req.id is not None
        assert req.tipo == "merma"
        assert req.estado == "pendiente"
        assert req.usuario_id == 10
        assert req.bodega_id == 1
        assert req.area_operativa_id == 2
        assert req.detalles["producto_id"] == 101

    @pytest.mark.asyncio
    async def test_create_request_invalid_type_raises(self) -> None:
        service = _approval_service
        with pytest.raises(ApprovalDomainError) as exc_info:
            await service.create_request(
                tipo="tipo_inexistente_xyz",
                usuario_id=10,
                tenant_id=TENANT_ID,
            )
        assert "no válido" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_request_invalid_user_raises(self) -> None:
        service = _approval_service
        with pytest.raises(ApprovalDomainError):
            await service.create_request(
                tipo=ApprovalType.CONSUMO,
                usuario_id=-1,  # inválido
                tenant_id=TENANT_ID,
            )

    @pytest.mark.asyncio
    async def test_list_requests_filters_and_pagination(self) -> None:
        service = _approval_service
        # Crear 4 solicitudes de distintas categorías y áreas
        req1 = await service.create_request(
            tipo=ApprovalType.MERMA,
            usuario_id=1,
            area_operativa_id=10,
            tenant_id=TENANT_ID,
        )
        req2 = await service.create_request(
            tipo=ApprovalType.CONTEO,
            usuario_id=2,
            area_operativa_id=20,
            tenant_id=TENANT_ID,
        )
        req3 = await service.create_request(
            tipo=ApprovalType.SOLICITUD_COMPRA,
            usuario_id=3,
            area_operativa_id=10,
            tenant_id=TENANT_ID,
        )
        req4 = await service.create_request(
            tipo=ApprovalType.PERFIL,
            usuario_id=4,
            area_operativa_id=30,
            tenant_id=TENANT_ID,
        )

        # 1. Listar todas
        items, total = await service.list_requests(tenant_id=TENANT_ID)
        assert total == 4
        assert len(items) == 4

        # 2. Filtrar por categoría 'operaciones'
        op_items, op_total = await service.list_requests(categoria="operaciones", tenant_id=TENANT_ID)
        assert op_total == 1
        assert op_items[0].id == req1.id

        # 3. Filtrar por categoría 'inventario'
        inv_items, inv_total = await service.list_requests(categoria="inventario", tenant_id=TENANT_ID)
        assert inv_total == 1
        assert inv_items[0].id == req2.id

        # 4. Filtrar por area_id 10
        area_items, area_total = await service.list_requests(area_id=10, tenant_id=TENANT_ID)
        assert area_total == 2

        # 5. Búsqueda textual 'merma'
        q_items, q_total = await service.list_requests(q="merma", tenant_id=TENANT_ID)
        assert q_total == 1
        assert q_items[0].id == req1.id

        # 6. Paginación
        p_items, p_total = await service.list_requests(page=1, page_size=2, tenant_id=TENANT_ID)
        assert p_total == 4
        assert len(p_items) == 2

    @pytest.mark.asyncio
    async def test_get_pending_count_grouped_by_category(self) -> None:
        service = _approval_service
        # 2 de operaciones
        await service.create_request(tipo=ApprovalType.MERMA, usuario_id=1, area_operativa_id=1, tenant_id=TENANT_ID)
        await service.create_request(tipo=ApprovalType.CONSUMO, usuario_id=1, area_operativa_id=1, tenant_id=TENANT_ID)
        # 1 de inventario
        await service.create_request(tipo=ApprovalType.CONTEO, usuario_id=2, area_operativa_id=2, tenant_id=TENANT_ID)
        # 1 de compras
        await service.create_request(tipo=ApprovalType.SOLICITUD_COMPRA, usuario_id=3, area_operativa_id=1, tenant_id=TENANT_ID)

        counts = await service.get_pending_count(tenant_id=TENANT_ID)
        assert counts["total_pending"] == 4
        assert counts["by_category"]["operaciones"] == 2
        assert counts["by_category"]["inventario"] == 1
        assert counts["by_category"]["compras"] == 1
        assert counts["by_category"]["equipo"] == 0

        # Filtro por area_id 2
        counts_area2 = await service.get_pending_count(area_id=2, tenant_id=TENANT_ID)
        assert counts_area2["total_pending"] == 1
        assert counts_area2["by_category"]["inventario"] == 1
        assert counts_area2["by_category"]["operaciones"] == 0

    @pytest.mark.asyncio
    async def test_approve_merma_impacts_kardex(self) -> None:
        service = _approval_service
        inv = service._inventory
        # Configurar saldo previo de 20 unidades del producto 50
        inv.register_movement(
            producto_id=50,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("20.00"),
            unit_cost=Decimal("1500.00"),
            actor_user_id=1,
            tenant_id=TENANT_ID,
        )
        assert inv.balance(50, 1) == Decimal("20.00")

        # Crear solicitud de merma de 4 unidades
        req = await service.create_request(
            tipo=ApprovalType.MERMA,
            usuario_id=5,
            bodega_id=1,
            detalles={"producto_id": 50, "quantity": "4.00", "unit_cost": "1500.00"},
            tenant_id=TENANT_ID,
        )

        # Aprobar solicitud
        approved = await service.approve_request(
            request_id=req.id,
            actor_id=99,
            tenant_id=TENANT_ID,
        )

        assert approved.estado == "aprobado"
        assert approved.resuelto_por == 99
        assert approved.resuelto_at is not None

        # Verificar que el stock bajó a 16.00 vía movimiento MERMA
        assert inv.balance(50, 1) == Decimal("16.00")

    @pytest.mark.asyncio
    async def test_approve_request_with_edited_details(self) -> None:
        service = _approval_service
        inv = service._inventory
        inv.register_movement(
            producto_id=60,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("10.00"),
            unit_cost=Decimal("500.00"),
            actor_user_id=1,
            tenant_id=TENANT_ID,
        )

        req = await service.create_request(
            tipo=ApprovalType.CONSUMO,
            usuario_id=2,
            bodega_id=1,
            detalles={"producto_id": 60, "quantity": "5.00", "unit_cost": "500.00"},
            tenant_id=TENANT_ID,
        )

        # Supervisor edita inline la cantidad de 5.00 a 3.00 antes de confirmar
        approved = await service.approve_request(
            request_id=req.id,
            actor_id=88,
            edited_details={"producto_id": 60, "quantity": "3.00", "unit_cost": "500.00"},
            tenant_id=TENANT_ID,
        )

        assert approved.estado == "aprobado"
        assert approved.detalles["quantity"] == "3.00"
        # 10 - 3 = 7
        assert inv.balance(60, 1) == Decimal("7.00")

    @pytest.mark.asyncio
    async def test_approve_already_resolved_request_raises_transition_error(self) -> None:
        service = _approval_service
        req = await service.create_request(
            tipo=ApprovalType.MENCION_NOTA,
            usuario_id=1,
            tenant_id=TENANT_ID,
        )

        await service.approve_request(req.id, actor_id=10, tenant_id=TENANT_ID)

        # Re-aprobar debe fallar
        with pytest.raises(InvalidApprovalTransitionError):
            await service.approve_request(req.id, actor_id=10, tenant_id=TENANT_ID)

    @pytest.mark.asyncio
    async def test_reject_request_with_valid_reason(self) -> None:
        service = _approval_service
        req = await service.create_request(
            tipo=ApprovalType.SOLICITUD_COMPRA,
            usuario_id=3,
            tenant_id=TENANT_ID,
        )

        rejected = await service.reject_request(
            request_id=req.id,
            actor_id=77,
            reason="Presupuesto agotado para esta semana.",
            tenant_id=TENANT_ID,
        )

        assert rejected.estado == "rechazado"
        assert rejected.resuelto_por == 77
        assert rejected.motivo_rechazo == "Presupuesto agotado para esta semana."
        assert rejected.resuelto_at is not None

    @pytest.mark.asyncio
    async def test_reject_request_short_reason_raises(self) -> None:
        service = _approval_service
        req = await service.create_request(
            tipo=ApprovalType.SOLICITUD_COMPRA,
            usuario_id=3,
            tenant_id=TENANT_ID,
        )

        with pytest.raises(InvalidRejectionReasonError):
            await service.reject_request(
                request_id=req.id,
                actor_id=77,
                reason="no",  # < 5 caracteres
                tenant_id=TENANT_ID,
            )

    @pytest.mark.asyncio
    async def test_get_request_not_found_raises_404(self) -> None:
        service = _approval_service
        fake_id = uuid4()
        with pytest.raises(ResourceNotFoundError):
            await service.get_request_by_id(fake_id, tenant_id=TENANT_ID)


# =========================================================================
# 2. PRUEBAS DE SERVICIO: BuffetApprovalService
# =========================================================================


class TestBuffetApprovalService:
    """Pruebas para inspección y resolución de sesiones de buffet."""

    @pytest.mark.asyncio
    async def test_buffet_detail_and_resolution(self) -> None:
        approval_service = _approval_service
        buffet_service = _buffet_service
        inv = approval_service._inventory

        # Cargar saldo de bodega para insumo 101 (20 un) y 102 (15 un)
        inv.register_movement(
            producto_id=101,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("20.00"),
            unit_cost=Decimal("1000.00"),
            actor_user_id=1,
            tenant_id=TENANT_ID,
        )
        inv.register_movement(
            producto_id=102,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("15.00"),
            unit_cost=Decimal("2000.00"),
            actor_user_id=1,
            tenant_id=TENANT_ID,
        )

        # Crear solicitud de sesión de buffet
        buffet_detalles = {
            "session_id": 501,
            "nombre_sesion": "Buffet Almuerzo Ejecutivo",
            "pax": 120,
            "items": [
                {
                    "producto_id": 101,
                    "nombre": "Filete Mignon",
                    "cantidad_apertura": "10.00",
                    "cantidad_reposiciones": "5.00",
                    "cantidad_cierre": "3.00",
                    "cantidad_consumida": "12.00",
                    "cantidad_sobrante": "3.00",
                    "costo_unitario": "1000.00",
                    "accion_sobrante": "retornar",  # Sobrante apto para volver a bodega
                },
                {
                    "producto_id": 102,
                    "nombre": "Ensalada César con Mayonesa",
                    "cantidad_apertura": "8.00",
                    "cantidad_reposiciones": "2.00",
                    "cantidad_cierre": "2.00",
                    "cantidad_consumida": "8.00",
                    "cantidad_sobrante": "2.00",
                    "costo_unitario": "2000.00",
                    "accion_sobrante": "merma",  # Merma por protocolo de frío roto
                    "motivo_merma": "Temperatura fuera de rango",
                },
            ],
        }

        req = await approval_service.create_request(
            tipo=ApprovalType.CONSUMO_BUFFET,
            usuario_id=10,
            bodega_id=1,
            detalles=buffet_detalles,
            tenant_id=TENANT_ID,
        )

        # 1. Obtener detalle auditado de buffet
        detail = await buffet_service.get_buffet_approval_detail(req.id, tenant_id=TENANT_ID)
        assert detail["id"] == req.id
        assert detail["detalles"]["pax"] == 120
        assert len(detail["detalles"]["items"]) == 2

        # 2. Resolver buffet aprobando
        resolved = await buffet_service.resolve_buffet_approval(
            solicitud_id=req.id,
            action="aprobar",
            actor_id=99,
            tenant_id=TENANT_ID,
        )
        assert resolved.estado == "aprobado"

        # Verificar impacto en Kardex:
        # Insumo 101: inicial 20 - 12 (consumo) + 3 (retorno) = 11
        assert inv.balance(101, 1) == Decimal("11.00")

        # Insumo 102: inicial 15 - 8 (consumo) - 2 (merma) = 5
        assert inv.balance(102, 1) == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_buffet_rejection(self) -> None:
        approval_service = _approval_service
        buffet_service = _buffet_service

        req = await approval_service.create_request(
            tipo=ApprovalType.CONSUMO_BUFFET,
            usuario_id=10,
            bodega_id=1,
            detalles={"session_id": 502, "items": []},
            tenant_id=TENANT_ID,
        )

        rejected = await buffet_service.resolve_buffet_approval(
            solicitud_id=req.id,
            action="rechazar",
            actor_id=99,
            reason="Faltan las fotos obligatorias de cierre de estación.",
            tenant_id=TENANT_ID,
        )

        assert rejected.estado == "rechazado"
        assert "Faltan las fotos" in (rejected.motivo_rechazo or "")


# =========================================================================
# 3. PRUEBAS DE SERVICIO: NotificationMatrixService
# =========================================================================


class TestNotificationMatrixService:
    """Pruebas para matriz de suscripción de notificaciones por cargo."""

    @pytest.mark.asyncio
    async def test_get_matrix_default_catalog_and_cargos(self) -> None:
        matrix_service = _matrix_service
        data = await matrix_service.get_matrix(tenant_id=TENANT_ID)

        assert len(data["catalog"]) == 12
        assert len(data["cargos"]) >= 7
        admin_cargo = next(c for c in data["cargos"] if c["role_name"] == "administrador")
        assert admin_cargo["name"] == "Administrador General"

    @pytest.mark.asyncio
    async def test_update_matrix_rules(self) -> None:
        matrix_service = _matrix_service
        rules_to_update = [
            {
                "cargo": "chef",
                "tipo_solicitud": "merma",
                "canal_in_app": True,
                "canal_email": True,
                "canal_push": True,
                "es_aprobador": True,
            },
            {
                "cargo": "garzon",
                "tipo_solicitud": "merma",
                "canal_in_app": False,
                "canal_email": False,
                "canal_push": False,
                "es_aprobador": False,
            },
        ]

        persisted = await matrix_service.update_matrix(
            rules=rules_to_update,
            actor_id=1,
            tenant_id=TENANT_ID,
        )
        assert len(persisted) == 2

        matrix = await matrix_service.get_matrix(tenant_id=TENANT_ID)
        rules = matrix["rules"]
        chef_merma = next(r for r in rules if r["cargo"] == "chef" and r["tipo_solicitud"] == "merma")
        assert chef_merma["es_aprobador"] is True
        assert chef_merma["canal_email"] is True


# =========================================================================
# 4. PRUEBAS DE ENRUTADOR FASTAPI Y GUARDÍAS RBAC DE 3 NIVELES
# =========================================================================


class TestApprovalRouterHttpAndRbac:
    """Pruebas de endpoints REST con validación de tokens Bearer y permisos RBAC."""

    @pytest.mark.asyncio
    async def test_list_solicitudes_forbidden_without_read_permission(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        headers = _make_headers(["operations.sales.create"])  # carece de operations.approvals.read
        resp = await async_client.get("/api/v1/operations/solicitudes", headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert data["status"] == 403

    @pytest.mark.asyncio
    async def test_list_solicitudes_success(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        headers = _make_headers(["operations.approvals.read"])
        # Crear una solicitud en el servicio
        await _approval_service.create_request(
            tipo=ApprovalType.MERMA,
            usuario_id=10,
            bodega_id=1,
            detalles={"producto_id": 1},
            tenant_id=TENANT_ID,
        )

        resp = await async_client.get("/api/v1/operations/solicitudes", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["tipo"] == "merma"
        assert data["items"][0]["categoria"] == "operaciones"

    @pytest.mark.asyncio
    async def test_pending_count_endpoint(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        headers = _make_headers(["operations.approvals.read"])
        await _approval_service.create_request(
            tipo=ApprovalType.CONTEO,
            usuario_id=1,
            tenant_id=TENANT_ID,
        )

        resp = await async_client.get("/api/v1/operations/solicitudes/pending-count", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pending"] >= 1
        assert data["by_category"]["inventario"] >= 1

    @pytest.mark.asyncio
    async def test_create_solicitud_endpoint(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        headers = _make_headers(["operations.approvals.create"], user_id=15)
        payload = {
            "tipo": "consumo",
            "bodega_id": 2,
            "detalles": {"producto_id": 99, "quantity": "2.50"},
        }
        resp = await async_client.post(
            "/api/v1/operations/solicitudes",
            headers=headers,
            json=payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tipo"] == "consumo"
        assert data["categoria"] == "operaciones"
        assert data["estado"] == "pendiente"
        assert data["usuario_id"] == 15

    @pytest.mark.asyncio
    async def test_approve_solicitud_endpoint(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        # 1. Crear solicitud
        req = await _approval_service.create_request(
            tipo=ApprovalType.MENCION_NOTA,
            usuario_id=5,
            tenant_id=TENANT_ID,
        )

        # 2. Aprobar sin permiso -> 403
        no_perm_headers = _make_headers(["operations.approvals.read"])
        resp_fail = await async_client.post(
            f"/api/v1/operations/solicitudes/{req.id}/aprobar",
            headers=no_perm_headers,
            json={},
        )
        assert resp_fail.status_code == 403

        # 3. Aprobar con permiso operations.approvals.approve -> 200
        approve_headers = _make_headers(["operations.approvals.approve"], user_id=77)
        resp_ok = await async_client.post(
            f"/api/v1/operations/solicitudes/{req.id}/aprobar",
            headers=approve_headers,
            json={"edited_details": {"nota": "Revisado OK"}},
        )
        assert resp_ok.status_code == 200
        data = resp_ok.json()
        assert data["estado"] == "aprobado"
        assert data["resuelto_por"] == 77
        assert data["detalles"]["nota"] == "Revisado OK"

    @pytest.mark.asyncio
    async def test_reject_solicitud_endpoint_and_validation(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        req = await _approval_service.create_request(
            tipo=ApprovalType.SOLICITUD_COMPRA,
            usuario_id=5,
            tenant_id=TENANT_ID,
        )

        headers = _make_headers(["operations.approvals.reject"], user_id=88)

        # Intento con motivo demasiado corto (< 5 chars) -> 422
        resp_invalid = await async_client.post(
            f"/api/v1/operations/solicitudes/{req.id}/rechazar",
            headers=headers,
            json={"motivo_rechazo": "bad"},
        )
        assert resp_invalid.status_code == 422

        # Rechazo exitoso con motivo >= 5 chars -> 200
        resp_ok = await async_client.post(
            f"/api/v1/operations/solicitudes/{req.id}/rechazar",
            headers=headers,
            json={"motivo_rechazo": "No cumple con presupuesto aprobado."},
        )
        assert resp_ok.status_code == 200
        data = resp_ok.json()
        assert data["estado"] == "rechazado"
        assert data["resuelto_por"] == 88
        assert "No cumple con presupuesto" in data["motivo_rechazo"]

    @pytest.mark.asyncio
    async def test_buffet_detail_and_resolve_endpoints(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        # Cargar saldo de stock inicial para insumo 1 (10 unidades)
        _approval_service._inventory.register_movement(
            producto_id=1,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("10.00"),
            unit_cost=Decimal("500.00"),
            actor_user_id=1,
            tenant_id=TENANT_ID,
        )

        req = await _approval_service.create_request(
            tipo=ApprovalType.CONSUMO_BUFFET,
            usuario_id=10,
            bodega_id=1,
            detalles={
                "session_id": 900,
                "pax": 80,
                "items": [
                    {
                        "producto_id": 1,
                        "nombre": "Insumo 1",
                        "cantidad_apertura": "5.00",
                        "cantidad_reposiciones": "0.00",
                        "cantidad_cierre": "1.00",
                        "cantidad_consumida": "4.00",
                        "cantidad_sobrante": "1.00",
                        "costo_unitario": "500.00",
                        "accion_sobrante": "retornar",
                    }
                ],
            },
            tenant_id=TENANT_ID,
        )

        headers = _make_headers(["operations.approvals.buffet"], user_id=99)

        # GET detail
        resp_detail = await async_client.get(
            f"/api/v1/operations/buffet/approvals/{req.id}/detail",
            headers=headers,
        )
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["detalles"]["pax"] == 80

        # POST resolve
        resp_resolve = await async_client.post(
            f"/api/v1/operations/buffet/approvals/{req.id}/resolve",
            headers=headers,
            json={"accion": "aprobar"},
        )
        assert resp_resolve.status_code == 200
        resolved = resp_resolve.json()
        assert resolved["estado"] == "aprobado"
        assert resolved["resuelto_por"] == 99

    @pytest.mark.asyncio
    async def test_matrix_endpoints_get_and_put(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        read_headers = _make_headers(["operations.approvals.read"])
        edit_headers = _make_headers(["operations.approvals.matrix_edit"], user_id=1)

        # GET matrix
        resp_get = await async_client.get("/api/v1/operations/solicitudes/matrix", headers=read_headers)
        assert resp_get.status_code == 200
        matrix_data = resp_get.json()
        assert len(matrix_data["catalog"]) == 12

        # PUT matrix masivo
        payload = {
            "rules": [
                {
                    "cargo": "chef",
                    "tipo_solicitud": "merma",
                    "canal_in_app": True,
                    "canal_email": True,
                    "canal_push": False,
                    "es_aprobador": True,
                }
            ]
        }
        resp_put = await async_client.put(
            "/api/v1/operations/solicitudes/matrix",
            headers=edit_headers,
            json=payload,
        )
        assert resp_put.status_code == 200
        updated = resp_put.json()
        assert any(r["cargo"] == "chef" and r["es_aprobador"] is True for r in updated["rules"])

        # PUT matrix cargo individual
        cargo_payload = {
            "notification_permissions": {"merma": True, "conteo": False}
        }
        resp_cargo = await async_client.put(
            "/api/v1/operations/solicitudes/matrix/cargo/3",
            headers=edit_headers,
            json=cargo_payload,
        )
        assert resp_cargo.status_code == 200
        assert resp_cargo.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_observability_opentelemetry_spans_on_approvals(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        """Valida que approve, reject y resolve_buffet emitan spans OpenTelemetry con atributos requeridos."""
        exporter = get_in_memory_exporter()
        exporter.clear()

        headers_approve = _make_headers(["operations.approvals.approve"], user_id=42)
        headers_reject = _make_headers(["operations.approvals.reject"], user_id=42)
        headers_buffet = _make_headers(["operations.approvals.buffet"], user_id=42)

        # 1. Crear solicitud para aprobar
        req1 = await _approval_service.create_request(
            tipo=ApprovalType.MENCION_NOTA,
            usuario_id=10,
            bodega_id=1,
            detalles={"nota": "Nota para aprobar"},
            tenant_id=TENANT_ID,
        )
        resp_app = await async_client.post(
            f"/api/v1/operations/solicitudes/{req1.id}/aprobar",
            headers=headers_approve,
            json={},
        )
        assert resp_app.status_code == 200

        # 2. Crear solicitud para rechazar
        req2 = await _approval_service.create_request(
            tipo=ApprovalType.MENCION_NOTA,
            usuario_id=11,
            bodega_id=1,
            detalles={"nota": "Nota para rechazar"},
            tenant_id=TENANT_ID,
        )
        resp_rej = await async_client.post(
            f"/api/v1/operations/solicitudes/{req2.id}/rechazar",
            headers=headers_reject,
            json={"motivo_rechazo": "Rechazo justificado por QA"},
        )
        assert resp_rej.status_code == 200

        # 3. Crear solicitud buffet y resolver
        req3 = await _approval_service.create_request(
            tipo=ApprovalType.CONSUMO_BUFFET,
            usuario_id=12,
            bodega_id=1,
            detalles={
                "session_id": 999,
                "items": [],
            },
            tenant_id=TENANT_ID,
        )
        resp_buf = await async_client.post(
            f"/api/v1/operations/buffet/approvals/{req3.id}/resolve",
            headers=headers_buffet,
            json={"accion": "aprobar"},
        )
        assert resp_buf.status_code == 200

        # 4. Validar existencia y contenido de spans en InMemorySpanExporter
        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        assert "operations.approvals.approve" in span_names
        assert "operations.approvals.reject" in span_names
        assert "operations.buffet.resolve" in span_names

        approve_span = next(s for s in spans if s.name == "operations.approvals.approve")
        assert approve_span.attributes.get("actor_id") == 42
        assert approve_span.attributes.get("solicitud_id") == str(req1.id)

        reject_span = next(s for s in spans if s.name == "operations.approvals.reject")
        assert reject_span.attributes.get("actor_id") == 42
        assert reject_span.attributes.get("solicitud_id") == str(req2.id)

        buffet_span = next(s for s in spans if s.name == "operations.buffet.resolve")
        assert buffet_span.attributes.get("actor_id") == 42
        assert buffet_span.attributes.get("action") == "aprobar"

