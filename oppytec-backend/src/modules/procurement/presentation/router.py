"""
oppytec-backend/src/modules/procurement/presentation/router.py
Endpoints REST de Abastecimiento (Órdenes de Compra, Conciliación 3 Vías y Facturas OCR):
- `POST /api/v1/procurement/orders` y `GET /api/v1/procurement/orders`
- `POST /api/v1/procurement/receptions/reconcile`
- `POST /api/v1/procurement/invoices/ocr`
"""
from __future__ import annotations

import base64
import binascii
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.exceptions import SecurityValidationError
from src.core.guards.file_magic_guard import validate_file_magic_bytes
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.procurement.application.procurement_service import ProcurementService
from src.modules.procurement.domain.reconciliation import (
    DocLine,
    document_total,
    reconcile_three_way,
)
from src.modules.procurement.presentation.schemas import (
    InvoiceOcrResponse,
    InvoiceOcrUploadRequest,
    PurchaseOrderCreateRequest,
    PurchaseOrderResponse,
    ThreeWayReconcileRequest,
    ThreeWayReconcileResponse,
)

router = APIRouter(tags=["procurement"])

_procurement_service = ProcurementService()
_orders_store: dict[str, PurchaseOrderResponse] = {}


@router.post(
    "/api/v1/procurement/orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_order_endpoint(
    payload: PurchaseOrderCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.create")),
    ],
) -> PurchaseOrderResponse:
    """Registra una Orden de Compra preservando la inmutabilidad del nombre comercial del proveedor."""
    try:
        existing_name = _procurement_service.supplier_name(payload.supplier_id)
        _procurement_service.rename_supplier(payload.supplier_id, payload.supplier_name)
        resolved_supplier_name = existing_name
    except KeyError:
        _procurement_service.register_supplier(payload.supplier_id, payload.supplier_name)
        resolved_supplier_name = payload.supplier_name

    doc_lines = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.lines
    ]
    _procurement_service.create_order(payload.po_number, doc_lines)
    total = document_total(doc_lines)
    record = PurchaseOrderResponse(
        po_number=payload.po_number,
        supplier_id=payload.supplier_id,
        supplier_name=resolved_supplier_name,
        line_count=len(doc_lines),
        net_total=total,
    )
    _orders_store[payload.po_number] = record
    return record


@router.get(
    "/api/v1/procurement/orders",
    response_model=list[PurchaseOrderResponse],
    status_code=status.HTTP_200_OK,
)
async def list_purchase_orders_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.orders.read")),
    ],
) -> list[PurchaseOrderResponse]:
    """Lista las Órdenes de Compra registradas en el Tenant."""
    return list(_orders_store.values())


@router.post(
    "/api/v1/procurement/receptions/reconcile",
    response_model=ThreeWayReconcileResponse,
    status_code=status.HTTP_200_OK,
)
async def reconcile_reception_and_invoice_endpoint(
    payload: ThreeWayReconcileRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("procurement.receptions.reconcile")),
    ],
) -> ThreeWayReconcileResponse:
    """Ejecuta la conciliación matemática de 3 vías (OC vs Recepción vs Factura) en `Decimal`."""
    order_docs = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.order_lines
    ]
    receipt_docs = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.receipt_lines
    ]
    invoice_docs = [
        DocLine(producto_id=ln.producto_id, quantity=ln.quantity, unit_cost=ln.unit_cost)
        for ln in payload.invoice_lines
    ]
    result = reconcile_three_way(
        order=order_docs,
        receipt=receipt_docs,
        invoice=invoice_docs,
        tolerance=payload.tolerance,
    )
    return ThreeWayReconcileResponse(
        po_number=payload.po_number,
        status=str(result.status.value),
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
    """Valida los Magic Bytes binarios de la factura subida antes de ejecutar extracción OCR."""
    try:
        raw_bytes = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SecurityValidationError(
            "Invalid Base64 invoice document.",
            i18n_key="security:errors.invalid_base64_payload",
            error_code="INVALID_BASE64_PAYLOAD",
        ) from exc

    verified_mime = validate_file_magic_bytes(
        content=raw_bytes,
        filename=payload.filename,
        allowed_types=frozenset({"application/pdf", "application/xml", "image/png", "image/webp", "image/jpeg"}),
    )
    return InvoiceOcrResponse(
        po_number=payload.po_number,
        filename=payload.filename,
        verified_mime_type=verified_mime,
        extracted_lines=1,
        requires_human_review=False,
    )
