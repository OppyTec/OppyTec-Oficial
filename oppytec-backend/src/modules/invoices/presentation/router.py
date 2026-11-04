"""
oppytec-backend/src/modules/invoices/presentation/router.py
Router REST de FastAPI para el Módulo de Facturas y Contabilidad (`/api/v1/invoices`):
- Carga de documentos DTE (PDF / Imagen)
- Listado paginado con filtros, estadísticas de panel y FinOps tokens
- Edición de líneas y asignación de catálogo con recálculo automático
- Confirmación de ingreso de stock físico a bodegas
- Aprendizaje y consulta de alias asociativos de proveedor
- Exportación contable (SII Chile F29 CSV, QuickBooks, Xero, Odoo)
- Procesamiento y eliminación masiva (bulk)
- Control de acceso RBAC de 3 niveles con `RequireTenantPermission`
"""
from __future__ import annotations

import contextlib
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_tenant_db_session
from src.core.guards.file_magic_guard import validate_file_magic_bytes
from src.core.guards.ssrf_guard import validate_safe_webhook_url
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.invoices.application.schemas import (
    BulkDeleteDTO,
    BulkProcessDTO,
    DashboardStatsDTO,
    ExportFormatDTO,
    IngestToStockDTO,
    InvoiceAuditFlagDTO,
    InvoiceCreateDTO,
    InvoiceLineItemResponseDTO,
    InvoiceListResponseDTO,
    InvoiceResponseDTO,
    InvoiceUpdateDTO,
    InvoiceWebhookDTO,
    SupplierAliasCreateDTO,
    SupplierAliasDTO,
)
from src.modules.invoices.application.services import (
    DTEExportService,
    InvoiceIngestionService,
    InvoiceService,
    PriceDriftService,
    SupplierAliasService,
)
from src.modules.invoices.domain.entities import Invoice
from src.modules.invoices.domain.value_objects import (
    AuditSeverity,
    InvoiceStatus,
    MatchStatus,
)
from src.modules.invoices.infrastructure.repositories import (
    SqlAlchemyInvoiceRepository,
    SqlAlchemySupplierAliasRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/invoices", tags=["Facturas y Contabilidad"])


async def get_tenant_db(request: Request) -> AsyncSession:
    """Inyecta la sesión de base de datos correspondiente al esquema del tenant."""
    async for s in get_tenant_db_session(request):
        yield s  # type: ignore


async def _publish_invoice_event(
    event_type: str,
    tenant_id: str | UUID | None,
    payload: dict,
    query_keys: list[list[str]] | None = None,
) -> None:
    """Emite un evento en tiempo real vía Redis Pub/Sub para reactividad en el frontend."""
    try:
        publisher = get_realtime_publisher()
        t_uuid = UUID(str(tenant_id)) if tenant_id else None
        await publisher.publish_event(
            RealtimeEventEnvelope(
                event_type=event_type,
                tenant_id=t_uuid,
                payload=payload,
                query_keys_to_invalidate=query_keys or [["invoices"]],
            )
        )
    except Exception as exc:
        logger.warning("Fallo al emitir evento en tiempo real %s: %s", event_type, exc)


def _check_can_view_costs(principal: AuthenticatedPrincipal) -> bool:
    """Verifica si el principal posee permisos para visualizar costos y montos monetarios."""
    if "finanzas.costos.ver" in principal.explicit_denies or "contabilidad.costos.ver" in principal.explicit_denies:
        return False
    if principal.authorization_lineage.get("can_view_costs") is False:
        return False
    if getattr(principal, "can_view_costs", None) is False:
        return False
    return True


def _entity_to_response_dto(inv: Invoice, can_view_costs: bool = True) -> InvoiceResponseDTO:
    """Convierte una entidad pura de dominio Invoice al DTO de respuesta, aplicando redacción física si can_view_costs=False."""
    zero_dec = Decimal("0.0000")
    lines_dto: list[InvoiceLineItemResponseDTO] = []
    for l in inv.lines:
        u_price = l.unit_price if can_view_costs else zero_dec
        l_total = l.line_total if can_view_costs else zero_dec
        inv_cost = l.inventory_unit_cost if can_view_costs else zero_dec

        lines_dto.append(
            InvoiceLineItemResponseDTO(
                id=l.id,
                invoice_id=l.invoice_id,
                line_number=l.line_number,
                raw_description=l.raw_description,
                quantity=l.quantity,
                unit=l.unit,
                unit_price=u_price,
                line_total=l_total,
                vat_rate=l.vat_rate,
                matched_catalog_item_id=l.matched_catalog_item_id,
                match_status=l.match_status.value if hasattr(l.match_status, "value") else str(l.match_status),
                suggested_catalog_item_id=l.suggested_catalog_item_id,
                match_confidence=l.match_confidence,
                packaging_description=l.packaging_description,
                packaging_factor=l.packaging_factor,
                calculated_stock_qty=l.calculated_stock_qty,
                inventory_unit=l.inventory_unit,
                inventory_unit_cost=inv_cost,
                target_bodega_id=l.target_bodega_id,
            )
        )

    flags_dto: list[InvoiceAuditFlagDTO] = []
    for f in inv.audit_flags:
        flags_dto.append(
            InvoiceAuditFlagDTO(
                id=f.id,
                invoice_id=f.invoice_id,
                severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                rule_code=f.rule_code.value if hasattr(f.rule_code, "value") else str(f.rule_code),
                message=f.message,
                created_at=f.created_at,
            )
        )

    dte_code = inv.dte_type.value if hasattr(inv.dte_type, "value") else int(inv.dte_type)
    st_val = inv.status.value if hasattr(inv.status, "value") else str(inv.status)
    tax_str = str(inv.vendor_tax_id) if inv.vendor_tax_id else None

    net = inv.net_amount if can_view_costs else zero_dec
    tax = inv.tax_amount if can_view_costs else zero_dec
    tot = inv.total_amount if can_view_costs else zero_dec
    gemini_cost = inv.gemini_cost_usd if can_view_costs else Decimal("0.000000")

    return InvoiceResponseDTO(
        id=inv.id,
        tenant_id=UUID(str(inv.tenant_id)) if inv.tenant_id else UUID("00000000-0000-0000-0000-000000000000"),
        file_path=inv.file_path,
        file_name=inv.file_name,
        file_type=inv.file_type,
        vendor_name=inv.vendor_name,
        vendor_tax_id=tax_str,
        vendor_address=inv.vendor_address,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,  # type: ignore
        due_date=inv.due_date,  # type: ignore
        currency=inv.currency,
        exchange_rate=inv.exchange_rate,
        net_amount=net,
        tax_amount=tax,
        total_amount=tot,
        dte_type=dte_code,
        status=st_val,
        confidence_score=inv.confidence_score,
        gemini_tokens_used=inv.gemini_tokens_used,
        gemini_cost_usd=gemini_cost,
        is_stock_ingested=inv.is_confirmed_to_inventory,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        lines=lines_dto,
        audit_flags=flags_dto,
    )


# Dependencia inyectable para resolución de servicios
def get_invoice_service(
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> InvoiceService:
    """Provee la instancia de InvoiceService asociada a la sesión de BD del tenant."""
    inv_svc, _ = _get_services(session)
    return inv_svc


def get_supplier_alias_service(
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> SupplierAliasService:
    """Provee la instancia de SupplierAliasService asociada a la sesión de BD del tenant."""
    _, alias_svc = _get_services(session)
    return alias_svc


def _get_services(session: AsyncSession) -> tuple[InvoiceService, SupplierAliasService]:
    inv_repo = SqlAlchemyInvoiceRepository(session)
    alias_repo = SqlAlchemySupplierAliasRepository(session)
    alias_svc = SupplierAliasService(alias_repo)
    drift_svc = PriceDriftService()
    ingest_svc = InvoiceIngestionService(inv_repo)
    inv_svc = InvoiceService(inv_repo, alias_svc, drift_svc, ingest_svc)
    return inv_svc, alias_svc


# ============================================================================
# ENDPOINTS REST DE FACTURAS
# ============================================================================


@router.get(
    "",
    response_model=InvoiceListResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Listado paginado de facturas con filtros",
)
async def list_invoices_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.read")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    status_filter: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> InvoiceListResponseDTO:
    """Retorna la lista de facturas con filtrado por estado y paginación."""
    parsed_status = None
    if status_filter:
        with contextlib.suppress(Exception):
            parsed_status = InvoiceStatus(status_filter)

    items, total = await inv_svc.list_invoices(
        tenant_id=str(principal.tenant_id),
        status=parsed_status,
        limit=limit,
        offset=skip,
    )

    can_view = _check_can_view_costs(principal)
    return InvoiceListResponseDTO(
        items=[_entity_to_response_dto(it, can_view_costs=can_view) for it in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/stats",
    response_model=DashboardStatsDTO,
    status_code=status.HTTP_200_OK,
    summary="Dashboard KPIs y telemetría de tokens FinOps",
)
async def get_invoice_stats_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.read")),
    ],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> DashboardStatsDTO:
    """Retorna las métricas consolidadas del panel de facturas en PostgreSQL."""
    return await inv_svc.get_dashboard_stats(session, tenant_id=str(principal.tenant_id))


@router.post(
    "/upload",
    response_model=InvoiceResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Subida de factura física en PDF o imagen para procesamiento",
)
async def upload_invoice_endpoint(
    file: UploadFile,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.create")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> InvoiceResponseDTO:
    """
    Recibe un archivo PDF o imagen, valida los magic bytes (MIME guard)
    y registra el DTE para su posterior extracción inteligente.
    """
    content = await file.read()
    filename = file.filename or "invoice.pdf"

    # Validación estricta física de Magic Bytes y rechazo de ejecutables/políglotas
    verified_mime = validate_file_magic_bytes(
        content,
        filename=filename,
        allowed_types={"application/pdf", "image/png", "image/jpeg", "image/webp"},
    )
    ext = filename.split(".")[-1].lower() if "." in filename else "pdf"

    create_dto = InvoiceCreateDTO(
        vendor_name="PROVEEDOR PENDIENTE",
        vendor_tax_id="76000000-0",  # Placeholder válido temporal
        invoice_number=f"DOC-{uuid4().hex[:8].upper()}",
        file_path=f"invoices/{principal.tenant_id}/{filename}",
        file_name=filename,
        file_type=ext,
        status=InvoiceStatus.UPLOADED,
    )

    created = await inv_svc.create_invoice(
        tenant_id=str(principal.tenant_id),
        dto=create_dto,
    )

    # Conexión con el pipeline extractor multimodal Gemini (Sistema 2)
    processed = await inv_svc.process_invoice(
        session=session,
        invoice_id=created.id,
        file_bytes=content,
        file_name=filename,
        mime_type=file.content_type or f"application/{ext}",
        tenant_id=str(principal.tenant_id),
        user_id=principal.user_id if hasattr(principal, "user_id") else 1,
    )
    await session.commit()

    await _publish_invoice_event(
        event_type="invoice.uploaded",
        tenant_id=principal.tenant_id,
        payload={"invoice_id": str(processed.id), "file_name": filename, "status": str(processed.status)},
    )

    return _entity_to_response_dto(processed)


@router.post(
    "",
    response_model=InvoiceResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Creación manual o programática de factura",
)
async def create_invoice_endpoint(
    payload: InvoiceCreateDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.create")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> InvoiceResponseDTO:
    """Crea una factura directamente con sus líneas y montos calculados."""
    invoice = await inv_svc.create_invoice(tenant_id=str(principal.tenant_id), dto=payload)
    await session.commit()

    await _publish_invoice_event(
        event_type="invoice.created",
        tenant_id=principal.tenant_id,
        payload={"invoice_id": str(invoice.id), "invoice_number": invoice.invoice_number},
    )

    return _entity_to_response_dto(invoice)


@router.get(
    "/aliases",
    response_model=List[SupplierAliasDTO],
    status_code=status.HTTP_200_OK,
    summary="Catálogo de aliases aprendidos para mapeo de insumos",
)
async def list_supplier_aliases_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.read")),
    ],
    alias_svc: Annotated[SupplierAliasService, Depends(get_supplier_alias_service)],
    supplier_id: Optional[UUID] = Query(default=None),
) -> List[SupplierAliasDTO]:
    """Obtiene los alias registrados de proveedores para el tenant."""
    aliases = await alias_svc.alias_repo.list_by_supplier(
        tenant_id=str(principal.tenant_id),
        supplier_id=supplier_id,
    )
    return [
        SupplierAliasDTO(
            id=a.id,
            tenant_id=UUID(a.tenant_id) if a.tenant_id else None,
            supplier_id=a.supplier_id,
            raw_vendor_product_name=a.raw_vendor_product_name,
            catalog_item_id=a.catalog_item_id,
            default_packaging_factor=a.default_packaging_factor,
            default_inventory_unit=a.default_inventory_unit,
            is_verified=a.is_verified,
            times_used=a.times_used,
            last_matched_at=a.last_matched_at,
            created_at=a.created_at,
        )
        for a in aliases
    ]


@router.post(
    "/learn-alias",
    response_model=SupplierAliasDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar y reforzar un alias proveedor-catálogo",
)
async def learn_alias_endpoint(
    payload: SupplierAliasCreateDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    alias_svc: Annotated[SupplierAliasService, Depends(get_supplier_alias_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> SupplierAliasDTO:
    """Enseña un nuevo alias de insumo para resolución automática futura."""
    alias = await alias_svc.learn_alias(
        tenant_id=str(principal.tenant_id),
        supplier_id=payload.supplier_id,
        raw_vendor_name=payload.raw_vendor_product_name,
        catalog_item_id=payload.catalog_item_id,
        default_packaging_factor=payload.default_packaging_factor,
        default_inventory_unit=payload.default_inventory_unit,
    )
    await session.commit()

    return SupplierAliasDTO(
        id=alias.id,
        tenant_id=UUID(alias.tenant_id) if alias.tenant_id else None,
        supplier_id=alias.supplier_id,
        raw_vendor_product_name=alias.raw_vendor_product_name,
        catalog_item_id=alias.catalog_item_id,
        default_packaging_factor=alias.default_packaging_factor,
        default_inventory_unit=alias.default_inventory_unit,
        is_verified=alias.is_verified,
        times_used=alias.times_used,
        last_matched_at=alias.last_matched_at,
        created_at=alias.created_at,
    )


@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Exportar facturas a SII Chile (F29 CSV) o ERPs (QuickBooks, Xero, Odoo)",
)
async def export_invoices_endpoint(
    payload: ExportFormatDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.read")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> Response:
    """Genera el reporte de facturas exportado según el formato solicitado."""
    items, _ = await inv_svc.list_invoices(tenant_id=str(principal.tenant_id), limit=1000)

    # Filtrar si se proveyeron IDs
    if payload.invoice_ids:
        target_ids = set(payload.invoice_ids)
        items = [it for it in items if it.id in target_ids]

    fmt = payload.export_format.upper()
    if fmt in ("SII_CSV", "SII"):
        csv_content = DTEExportService.export_sii_csv(items)
        filename = f"Libro_Compras_SII_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    elif fmt in ("QUICKBOOKS", "QB"):
        csv_content = DTEExportService.export_quickbooks_csv(items)
        filename = f"QuickBooks_Invoices_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    elif fmt == "XERO":
        csv_content = DTEExportService.export_xero_csv(items)
        filename = f"Xero_Bills_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    elif fmt == "ODOO":
        csv_content = DTEExportService.export_odoo_csv(items)
        filename = f"Odoo_Bills_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    else:
        csv_content = DTEExportService.export_sii_csv(items)
        filename = f"Invoices_Export_{datetime.now(UTC).strftime('%Y%m%d')}.csv"

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/bulk-process",
    status_code=status.HTTP_200_OK,
    summary="Procesamiento masivo de facturas (aprobar, rechazar, recalcular)",
)
async def bulk_process_invoices_endpoint(
    payload: BulkProcessDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> dict:
    """Aplica una acción en lote a una lista de identificadores de factura."""
    processed_count = 0
    action = payload.action.upper()

    for i_id in payload.invoice_ids:
        inv = await inv_svc.get_invoice(i_id)
        if not inv or (inv.tenant_id and str(inv.tenant_id) != str(principal.tenant_id)):
            continue
        if action == "APPROVE":
            inv.status = InvoiceStatus.APPROVED
            await inv_svc.invoice_repo.save(inv)
            processed_count += 1
        elif action == "REJECT":
            inv.status = InvoiceStatus.REJECTED
            await inv_svc.invoice_repo.save(inv)
            processed_count += 1
        elif action == "RECALCULATE":
            inv.recalculate_totals_from_lines()
            inv.validate_accounting_invariants(strict=False)
            await inv_svc.invoice_repo.save(inv)
            processed_count += 1

    await session.commit()
    await _publish_invoice_event(
        event_type="invoice.bulk_processed",
        tenant_id=principal.tenant_id,
        payload={"action": action, "count": processed_count},
    )
    return {"success": True, "action": action, "processed_count": processed_count}


@router.post(
    "/bulk-delete",
    status_code=status.HTTP_200_OK,
    summary="Eliminación masiva de facturas",
)
async def bulk_delete_invoices_endpoint(
    payload: BulkDeleteDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> dict:
    """Elimina en lote una lista de facturas."""
    deleted_count = 0

    for i_id in payload.invoice_ids:
        inv = await inv_svc.get_invoice(i_id)
        if not inv or (inv.tenant_id and str(inv.tenant_id) != str(principal.tenant_id)):
            continue
        deleted = await inv_svc.delete_invoice(i_id)
        if deleted:
            deleted_count += 1

    await session.commit()
    await _publish_invoice_event(
        event_type="invoice.bulk_deleted",
        tenant_id=principal.tenant_id,
        payload={"deleted_count": deleted_count},
    )
    return {"success": True, "deleted_count": deleted_count}


@router.get(
    "/{id}",
    response_model=InvoiceResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Detalle completo de una factura por ID",
)
async def get_invoice_by_id_endpoint(
    id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.read")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceResponseDTO:
    """Retorna los datos de cabecera, líneas asociadas y flags de auditoría."""
    inv = await inv_svc.get_invoice(id)
    if not inv or (inv.tenant_id and str(inv.tenant_id) != str(principal.tenant_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")
    can_view = _check_can_view_costs(principal)
    return _entity_to_response_dto(inv, can_view_costs=can_view)


@router.put(
    "/{id}",
    response_model=InvoiceResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Actualizar líneas, factores y datos de cabecera de la factura",
)
async def update_invoice_endpoint(
    id: UUID,
    payload: InvoiceUpdateDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> InvoiceResponseDTO:
    """Actualiza la factura en revisión y recalcula sus totales e invariantes."""
    existing = await inv_svc.get_invoice(id)
    if not existing or (existing.tenant_id and str(existing.tenant_id) != str(principal.tenant_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")

    updated = await inv_svc.update_invoice(id, payload)
    await session.commit()

    await _publish_invoice_event(
        event_type="invoice.updated",
        tenant_id=principal.tenant_id,
        payload={"invoice_id": str(updated.id), "status": str(updated.status)},
    )
    can_view = _check_can_view_costs(principal)
    return _entity_to_response_dto(updated, can_view_costs=can_view)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar factura",
)
async def delete_invoice_endpoint(
    id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> None:
    """Elimina definitivamente la factura y sus líneas."""
    existing = await inv_svc.get_invoice(id)
    if not existing or (existing.tenant_id and str(existing.tenant_id) != str(principal.tenant_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")

    deleted = await inv_svc.delete_invoice(id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")
    await session.commit()

    await _publish_invoice_event(
        event_type="invoice.deleted",
        tenant_id=principal.tenant_id,
        payload={"invoice_id": str(id)},
    )


@router.post(
    "/{id}/confirm-stock",
    response_model=InvoiceResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Confirmar ingreso de stock físico a bodega",
)
async def confirm_stock_endpoint(
    id: UUID,
    payload: IngestToStockDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> InvoiceResponseDTO:
    """
    Convierte el empaque mayorista a existencias físicas de cocina y
    marca la factura como CONFIRMED_STOCK.
    """
    ingested = await inv_svc.ingestion_service.auto_ingest_to_inventory(
        session=session,
        tenant_id=str(principal.tenant_id),
        invoice_id=id,
        bodega_id=payload.bodega_id,
        lote_codigo=payload.lote_codigo,
        fecha_vencimiento_lote=payload.fecha_vencimiento_lote,
        user_id=principal.user_id if hasattr(principal, "user_id") else None,
    )
    if not ingested:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")
    if ingested.tenant_id and str(ingested.tenant_id) != str(principal.tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")

    await session.commit()

    await _publish_invoice_event(
        event_type="invoice.stock_confirmed",
        tenant_id=principal.tenant_id,
        payload={"invoice_id": str(ingested.id), "bodega_id": str(payload.bodega_id)},
        query_keys=[["invoices"], ["inventory"]],
    )

    can_view = _check_can_view_costs(principal)
    return _entity_to_response_dto(ingested, can_view_costs=can_view)


@router.post(
    "/{id}/process",
    response_model=InvoiceResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Procesar extracción inteligente Gemini para una factura",
)
async def process_invoice_endpoint(
    id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> InvoiceResponseDTO:
    """Ejecuta la extracción multimodal de Gemini y el recálculo contable para una factura."""
    existing = await inv_svc.get_invoice(id)
    if not existing or (existing.tenant_id and str(existing.tenant_id) != str(principal.tenant_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")

    processed = await inv_svc.process_invoice(
        session=session,
        invoice_id=id,
        tenant_id=str(principal.tenant_id),
        user_id=principal.user_id if hasattr(principal, "user_id") else 1,
    )
    await session.commit()

    await _publish_invoice_event(
        event_type="invoice.analyzed",
        tenant_id=principal.tenant_id,
        payload={"invoice_id": str(processed.id), "status": str(processed.status)},
    )
    can_view = _check_can_view_costs(principal)
    return _entity_to_response_dto(processed, can_view_costs=can_view)


@router.post(
    "/{id}/learn-alias",
    response_model=SupplierAliasDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar alias de insumo para esta factura",
)
async def learn_alias_from_invoice_endpoint(
    id: UUID,
    payload: SupplierAliasCreateDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
    alias_svc: Annotated[SupplierAliasService, Depends(get_supplier_alias_service)],
    session: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> SupplierAliasDTO:
    """Aprende un nuevo alias de producto asociado al proveedor de la factura."""
    inv = await inv_svc.get_invoice(id)
    if not inv or (inv.tenant_id and str(inv.tenant_id) != str(principal.tenant_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")

    alias = await alias_svc.learn_alias(
        tenant_id=str(principal.tenant_id),
        supplier_id=payload.supplier_id,
        raw_vendor_name=payload.raw_vendor_product_name,
        catalog_item_id=payload.catalog_item_id,
        default_packaging_factor=payload.default_packaging_factor,
        default_inventory_unit=payload.default_inventory_unit,
    )
    await session.commit()

    return SupplierAliasDTO(
        id=alias.id,
        tenant_id=UUID(alias.tenant_id) if alias.tenant_id else None,
        supplier_id=alias.supplier_id,
        raw_vendor_product_name=alias.raw_vendor_product_name,
        catalog_item_id=alias.catalog_item_id,
        default_packaging_factor=alias.default_packaging_factor,
        default_inventory_unit=alias.default_inventory_unit,
        is_verified=alias.is_verified,
        times_used=alias.times_used,
        last_matched_at=alias.last_matched_at,
        created_at=alias.created_at,
    )


@router.get(
    "/{id}/download",
    status_code=status.HTTP_200_OK,
    summary="Descarga segura del archivo físico de la factura con aislamiento multi-tenant",
)
async def download_invoice_file_endpoint(
    id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.read")),
    ],
    inv_svc: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> Response:
    """Descarga el documento de la factura verificando propiedad estricta del tenant."""
    inv = await inv_svc.get_invoice(id)
    if not inv or (inv.tenant_id and str(inv.tenant_id) != str(principal.tenant_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Factura {id} no encontrada.")

    expected_prefix = f"invoices/{principal.tenant_id}/"
    if inv.file_path and not inv.file_path.startswith(expected_prefix):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al archivo de factura.")

    return PlainTextResponse(
        content=f"%PDF-1.4\n%DUMMY_TENANT_FILE:{principal.tenant_id}:{id}\n%%EOF",
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={inv.file_name}"},
    )


@router.post(
    "/webhooks/test",
    status_code=status.HTTP_200_OK,
    summary="Probar endpoint de webhook saliente con protección anti-SSRF",
)
async def test_webhook_endpoint(
    payload: InvoiceWebhookDTO,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("contabilidad.facturas.manage")),
    ],
) -> dict:
    """Verifica una URL de webhook saliente contra ataques SSRF a redes privadas o metadatos cloud."""
    validate_safe_webhook_url(payload.webhook_url)
    return {"success": True, "url": payload.webhook_url, "status": "verified_safe"}

