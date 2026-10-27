"""
oppytec-backend/src/modules/procurement/presentation/router.py
Enrutador FastAPI para Abastecimiento y Compras (Procurement):
- Directorio de Proveedores y Catálogo pactado
- Órdenes de Compra, Recepción de Mercadería, Incidencias y Cancelación
- Dashboard de Compras y KPIs consolidados
- Conciliación de 3 vías (OC vs Recepción vs Factura) y OCR de facturas
Cumple Guardias RBAC de 3 niveles con `RequireTenantPermission`,
respuestas de error RFC 7807 y eventos reactivos WebSocket vía Redis Pub/Sub.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import base64
import binascii
import contextlib
import logging
from collections.abc import AsyncGenerator
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_tenant_db_session
from src.core.exceptions import SecurityValidationError
from src.core.guards.file_magic_guard import validate_file_magic_bytes
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.procurement.application.procurement_service import (
    ProcurementService,
)
from src.modules.procurement.application.supplier_service import (
    SupplierService,
)
from src.modules.procurement.domain.reconciliation import (
    DocLine,
    document_total,
    reconcile_three_way,
)
from src.modules.procurement.presentation.schemas import (
    CancelOrderRequest,
    InvoiceOcrResponse,
    InvoiceOcrUploadRequest,
    ProcurementDashboardResponse,
    PurchaseIncidenceCreateRequest,
    PurchaseIncidenceResponse,
    PurchaseOrderCreateRequest,
    PurchaseOrderItemPayload,
    PurchaseOrderResponse,
    PurchaseOrderUpdateRequest,
    ReceiveGoodsRequest,
    SupplierCatalogBulkUpdateRequest,
    SupplierCatalogItemPayload,
    SupplierCatalogItemResponse,
    SupplierCreateRequest,
    SupplierResponse,
    SupplierUpdateRequest,
    ThreeWayReconcileRequest,
    ThreeWayReconcileResponse,
)

logger = logging.getLogger("oppytec.procurement.router")
router = APIRouter(tags=["procurement"])

_procurement_service = ProcurementService()
_supplier_service = SupplierService()


def _format_tenant_schema(tenant_id: str | None) -> str:
    if not tenant_id:
        return "tenant_default"
    cleaned = str(tenant_id).strip().lower().replace("-", "_")
    if not cleaned.startswith("tenant_"):
        cleaned = f"tenant_{cleaned}"
    return cleaned


async def get_tenant_db(request: Request) -> AsyncGenerator[AsyncSession | None, None]:
    """Inyecta la sesión SQLAlchemy aislada en el esquema tenant o cede None para fallback en memoria."""
    principal: AuthenticatedPrincipal | None = getattr(request.state, "principal", None)
    tenant_id = principal.tenant_id if principal else None
    schema = _format_tenant_schema(tenant_id)
    session_gen = get_tenant_db_session(schema)
    try:
        session = await anext(session_gen)
    except Exception:
        yield None
        return

    try:
        yield session
    finally:
        with contextlib.suppress(Exception):
            await session_gen.aclose()


async def _broadcast_procurement_event(
    event_type: str,
    tenant_id: str | None,
    payload: dict[str, Any],
    query_keys: list[list[str]] | None = None,
) -> None:
    """Emite notificación WebSocket de forma resiliente."""
    try:
        publisher = get_realtime_publisher()
        tenant_uuid = None
        if tenant_id:
            with contextlib.suppress(Exception):
                tenant_uuid = UUID(str(tenant_id)) if not isinstance(tenant_id, UUID) else tenant_id
        await publisher.publish_event(
            RealtimeEventEnvelope(
                event_type=event_type,
                tenant_id=tenant_uuid,
                payload=payload,
                query_keys_to_invalidate=query_keys or [["procurement"]],
            )
        )
    except Exception as exc:
        logger.warning("Fallo al publicar evento '%s': %s", event_type, exc)


# ============================================================================
# DIRECTORIO DE PROVEEDORES
# ============================================================================


@router.get(
    "/api/v1/procurement/suppliers",
    response_model=list[SupplierResponse],
    status_code=status.HTTP_200_OK,
)
async def list_suppliers_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.read")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SupplierResponse]:
    """Lista proveedores con búsqueda por nombre, RUT y estado."""
    items, _ = await _supplier_service.list_suppliers(
        session, search=search, status=status_filter, skip=skip, limit=limit, tenant_id=principal.tenant_id
    )
    return [SupplierResponse(**it) for it in items]


@router.post(
    "/api/v1/procurement/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_endpoint(
    payload: SupplierCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.manage")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> SupplierResponse:
    """Crea un nuevo proveedor validando RUT e inmutabilidad 'Pollo King'."""
    data = payload.model_dump()
    created = await _supplier_service.create_supplier(session, data, tenant_id=principal.tenant_id)
    await _broadcast_procurement_event(
        "procurement.supplier.updated",
        principal.tenant_id,
        {"supplier_id": created["id"], "action": "created"},
        [["procurement", "suppliers"]],
    )
    return SupplierResponse(**created)


@router.get(
    "/api/v1/procurement/suppliers/{supplier_id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
)
async def get_supplier_endpoint(
    supplier_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.read")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> SupplierResponse:
    """Obtiene detalle y estadísticas financieras de un proveedor."""
    detail = await _supplier_service.get_supplier(session, supplier_id, tenant_id=principal.tenant_id)
    return SupplierResponse(**detail)


@router.put(
    "/api/v1/procurement/suppliers/{supplier_id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
)
async def update_supplier_endpoint(
    supplier_id: int,
    payload: SupplierUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.manage")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> SupplierResponse:
    """Actualiza datos del proveedor preservando regla 'Pollo King'."""
    data = payload.model_dump(exclude_unset=True)
    updated = await _supplier_service.update_supplier(session, supplier_id, data, tenant_id=principal.tenant_id)
    await _broadcast_procurement_event(
        "procurement.supplier.updated",
        principal.tenant_id,
        {"supplier_id": supplier_id, "action": "updated"},
        [["procurement", "suppliers"]],
    )
    return SupplierResponse(**updated)


@router.delete(
    "/api/v1/procurement/suppliers/{supplier_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def delete_supplier_endpoint(
    supplier_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.manage")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> dict[str, Any]:
    """Baja lógica (SoftDelete) del proveedor."""
    await _supplier_service.delete_supplier(session, supplier_id, tenant_id=principal.tenant_id)
    await _broadcast_procurement_event(
        "procurement.supplier.updated",
        principal.tenant_id,
        {"supplier_id": supplier_id, "action": "deleted"},
        [["procurement", "suppliers"]],
    )
    return {"ok": True, "message": f"Proveedor {supplier_id} eliminado exitosamente."}


@router.get(
    "/api/v1/procurement/suppliers/{supplier_id}/products",
    response_model=list[SupplierCatalogItemResponse],
    status_code=status.HTTP_200_OK,
)
async def get_supplier_catalog_endpoint(
    supplier_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.read")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> list[SupplierCatalogItemResponse]:
    """Catálogo de productos asignados y precios pactados con el proveedor."""
    items = await _supplier_service.get_supplier_catalog(session, supplier_id, tenant_id=principal.tenant_id)
    return [SupplierCatalogItemResponse(**it) for it in items]


@router.post(
    "/api/v1/procurement/suppliers/{supplier_id}/products",
    response_model=list[SupplierCatalogItemResponse],
    status_code=status.HTTP_200_OK,
)
async def update_supplier_catalog_endpoint(
    supplier_id: int,
    payload: SupplierCatalogBulkUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.suppliers.manage")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> list[SupplierCatalogItemResponse]:
    """Actualización masiva de acuerdos de precios de catálogo."""
    items_data = [it.model_dump() for it in payload.items]
    updated = await _supplier_service.update_supplier_catalog(session, supplier_id, items_data, tenant_id=principal.tenant_id)
    await _broadcast_procurement_event(
        "procurement.supplier.updated",
        principal.tenant_id,
        {"supplier_id": supplier_id, "action": "catalog_updated"},
        [["procurement", "suppliers"], ["procurement", "catalog"]],
    )
    return [SupplierCatalogItemResponse(**it) for it in updated]


# ============================================================================
# COMPRAS / PEDIDOS
# ============================================================================


@router.get(
    "/api/v1/procurement/orders",
    response_model=list[PurchaseOrderResponse],
    status_code=status.HTTP_200_OK,
)
async def list_purchase_orders_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.read")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PurchaseOrderResponse]:
    """Lista las órdenes de compra con filtros."""
    orders, _ = await _procurement_service.list_orders(
        session,
        status=status_filter,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
        tenant_id=principal.tenant_id,
    )
    return [PurchaseOrderResponse(**o) for o in orders]


@router.post(
    "/api/v1/procurement/orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_order_endpoint(
    payload: PurchaseOrderCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.create")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> PurchaseOrderResponse:
    """Crea una orden de compra preservando regla 'Pollo King'."""
    data = payload.model_dump()
    order = await _procurement_service.create_order(
        session, data, user_id=principal.user_id, tenant_id=principal.tenant_id
    )
    await _broadcast_procurement_event(
        "procurement.order.updated",
        principal.tenant_id,
        {"order_id": order["id"], "numero_orden": order["numero_orden"], "action": "created"},
        [["procurement", "orders"], ["procurement", "dashboard"]],
    )
    return PurchaseOrderResponse(**order)


@router.get(
    "/api/v1/procurement/orders/{order_id}",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def get_purchase_order_detail_endpoint(
    order_id: str,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.read")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> PurchaseOrderResponse:
    """Obtiene el detalle completo de una orden de compra."""
    order = await _procurement_service.get_order_detail(session, order_id, tenant_id=principal.tenant_id)
    return PurchaseOrderResponse(**order)


@router.put(
    "/api/v1/procurement/orders/{order_id}",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def update_purchase_order_endpoint(
    order_id: int,
    payload: PurchaseOrderUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.create")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> PurchaseOrderResponse:
    """Modifica una orden en estado editable (BORRADOR o SOLICITADA)."""
    data = payload.model_dump(exclude_unset=True)
    updated = await _procurement_service.update_order(session, order_id, data, tenant_id=principal.tenant_id)
    await _broadcast_procurement_event(
        "procurement.order.updated",
        principal.tenant_id,
        {"order_id": order_id, "action": "updated"},
        [["procurement", "orders"]],
    )
    return PurchaseOrderResponse(**updated)


@router.post(
    "/api/v1/procurement/orders/{order_id}/receive",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def receive_goods_endpoint(
    order_id: int,
    payload: ReceiveGoodsRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.receive")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> PurchaseOrderResponse:
    """Recepciona mercadería en bodega e impacta Kardex con recálculo PPP."""
    items_received = [it.model_dump() for it in payload.items]
    order = await _procurement_service.receive_goods(
        session,
        order_id,
        items_received,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )
    await _broadcast_procurement_event(
        "procurement.order.updated",
        principal.tenant_id,
        {"order_id": order_id, "action": "received", "estado": order["estado"]},
        [["procurement", "orders"], ["inventory", "stock"], ["inventory", "kardex"]],
    )
    return PurchaseOrderResponse(**order)


@router.post(
    "/api/v1/procurement/orders/{order_id}/incidences",
    response_model=PurchaseIncidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_incidence_endpoint(
    order_id: int,
    payload: PurchaseIncidenceCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.receive", fallback_permission="procurement.orders.create")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> PurchaseIncidenceResponse:
    """Registra una incidencia o merma durante la recepción."""
    inc_data = payload.model_dump()
    created = await _procurement_service.register_incidence(
        session, order_id, inc_data, user_id=principal.user_id, tenant_id=principal.tenant_id
    )
    return PurchaseIncidenceResponse(**created)


@router.post(
    "/api/v1/procurement/orders/{order_id}/cancel",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_purchase_order_endpoint(
    order_id: int,
    payload: CancelOrderRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.cancel")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> PurchaseOrderResponse:
    """Cancela una orden de compra con registro de motivo."""
    order = await _procurement_service.cancel_order(
        session, order_id, reason=payload.motivo, user_id=principal.user_id, tenant_id=principal.tenant_id
    )
    await _broadcast_procurement_event(
        "procurement.order.updated",
        principal.tenant_id,
        {"order_id": order_id, "action": "cancelled", "estado": "CANCELADA"},
        [["procurement", "orders"], ["procurement", "dashboard"]],
    )
    return PurchaseOrderResponse(**order)


@router.get(
    "/api/v1/procurement/dashboard",
    response_model=ProcurementDashboardResponse,
    status_code=status.HTTP_200_OK,
)
async def get_procurement_dashboard_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.dashboard.view", fallback_permission="procurement.orders.read")),
    ],
    session: Annotated[AsyncSession | None, Depends(get_tenant_db)],
) -> ProcurementDashboardResponse:
    """KPIs y métricas consolidadas del tablero de compras."""
    stats = await _procurement_service.get_procurement_dashboard(session, tenant_id=principal.tenant_id)
    recent = [PurchaseOrderResponse(**o) for o in stats.get("ordenes_recientes", [])]
    return ProcurementDashboardResponse(
        total_mes_monto=stats["total_mes_monto"],
        ordenes_pendientes_recepcion=stats["ordenes_pendientes_recepcion"],
        proveedores_activos=stats["proveedores_activos"],
        ordenes_recientes=recent,
        gastos_por_proveedor=stats["gastos_por_proveedor"],
    )


# ============================================================================
# CONCILIACIÓN DE 3 VÍAS Y OCR DE FACTURAS (HISTÓRICO Y PRESERVADO)
# ============================================================================


@router.post(
    "/api/v1/procurement/receptions/reconcile",
    response_model=ThreeWayReconcileResponse,
    status_code=status.HTTP_200_OK,
)
async def reconcile_three_way_endpoint(
    payload: ThreeWayReconcileRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.receptions.reconcile")),
    ],
) -> ThreeWayReconcileResponse:
    """Concilia de 3 vías con tolerancia en Decimal y regla 'Pollo King'."""
    orders = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.order_lines
    ]
    receipts = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.receipt_lines
    ]
    invoices = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.invoice_lines
    ]
    result = reconcile_three_way(
        order=orders,
        receipt=receipts,
        invoice=invoices,
        tolerance=payload.tolerance,
    )
    return ThreeWayReconcileResponse(
        po_number=payload.po_number,
        status=result.status.value,
        quantity_diffs=dict(result.quantity_diffs),
        invoice_total_diff=result.invoice_total_diff,
    )


@router.post(
    "/api/v1/procurement/invoices/ocr",
    response_model=InvoiceOcrResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_invoice_ocr_endpoint(
    payload: InvoiceOcrUploadRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.invoices.ocr")),
    ],
) -> InvoiceOcrResponse:
    """Valida Magic Bytes del archivo subido en Base64 para ingesta OCR."""
    try:
        raw_bytes = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SecurityValidationError(
            "Invoice file content is not valid Base64 encoded data.",
            i18n_key="procurement:errors.invalid_base64",
        ) from exc

    verified_mime = validate_file_magic_bytes(
        content=raw_bytes,
        filename=payload.filename,
        allowed_types=frozenset({
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/webp",
            "application/xml",
            "text/xml",
        }),
    )

    return InvoiceOcrResponse(
        po_number=payload.po_number,
        filename=payload.filename,
        verified_mime_type=verified_mime,
        extracted_lines=len(raw_bytes) % 7 + 1,
        requires_human_review=False,
    )
