"""
oppytec-backend/src/modules/invoices/application/services.py
Servicios de aplicación para el Módulo de Facturas y Contabilidad:
- InvoiceService: CRUD, recálculos, auditoría e ingesta de facturas.
- SupplierAliasService: Memoria asociativa de productos con catálogo y resolución difusa.
- InvoiceIngestionService: Traspaso a inventario físico (Kardex, lotes y bodegas).
- PriceDriftService: Detección y semaforización de sobreprecios contra historial.
- DTEExportService: Generación de libros contables para SII Chile (F29 CSV), QuickBooks, Xero, Odoo.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.fx.fx_service import FXService
from src.core.guards.file_magic_guard import sanitize_spreadsheet_export_value
from src.core.observability import get_invoice_logger, trace_span

from src.modules.invoices.application.schemas import (
    DashboardStatsDTO,
    InvoiceCreateDTO,
    InvoiceLineItemCreateDTO,
    InvoiceLineItemUpdateDTO,
    InvoiceUpdateDTO,
)
from src.modules.invoices.application.gemini_extractor import (
    ExtractedInvoiceData,
    GeminiInvoiceExtractor,
)
from src.modules.invoices.domain.entities import (
    Invoice,
    InvoiceAuditFlag,
    InvoiceLineItem,
    SupplierProductAlias,
)
from src.modules.invoices.domain.exceptions import (
    InvalidInvoiceStatusTransitionError,
    InvoiceDomainError,
    PriceDriftThresholdExceededError,
)
from src.modules.invoices.domain.value_objects import (
    AuditRuleCode,
    AuditSeverity,
    DTEType,
    InvoiceStatus,
    MatchStatus,
    PackagingFactor,
    PriceDrift,
    TaxId,
)
from src.modules.invoices.infrastructure.models import (
    InvoiceLineItemModel,
    InvoiceModel,
    SupplierProductAliasModel,
)
from src.modules.invoices.infrastructure.repositories import (
    SqlAlchemyInvoiceRepository,
    SqlAlchemySupplierAliasRepository,
)

logger = logging.getLogger(__name__)

DECIMAL_ZERO = Decimal("0.0000")
DECIMAL_QUANT_4 = Decimal("0.0001")


class SupplierAliasService:
    """
    Servicio de resolución de alias y memoria semántica de productos.
    Mapea descripciones crudas de facturas de proveedores contra el catálogo interno.
    """

    def __init__(self, alias_repo: SqlAlchemySupplierAliasRepository) -> None:
        self.alias_repo = alias_repo

    async def resolve_line_match(
        self,
        session: AsyncSession,
        tenant_id: str,
        supplier_id: Optional[UUID],
        raw_description: str,
    ) -> Tuple[MatchStatus, Optional[UUID], Decimal, Decimal, str]:
        """
        Resuelve si la descripción cruda coincide con un alias existente o sugiere uno.
        Retorna: (match_status, catalog_item_id, match_confidence, packaging_factor, inventory_unit)
        """
        with trace_span(
            "invoices.resolve_aliases",
            attributes={
                "tenant_id": tenant_id,
                "supplier_id": str(supplier_id) if supplier_id else None,
                "raw_description": raw_description,
            },
            tracer_name="oppytec.invoices",
        ) as span_attrs:
            # 1. Búsqueda exacta de alias en base de datos
            alias = await self.alias_repo.find_by_vendor_name(
                tenant_id=tenant_id,
                supplier_id=supplier_id,
                raw_vendor_product_name=raw_description,
            )

            if alias:
                alias.record_usage()
                await self.alias_repo.save_alias(alias)
                span_attrs["match_status"] = MatchStatus.EXACT_ALIAS.value
                span_attrs["catalog_item_id"] = str(alias.catalog_item_id)
                span_attrs["match_confidence"] = 1.0
                return (
                    MatchStatus.EXACT_ALIAS,
                    alias.catalog_item_id,
                    Decimal("1.0000"),
                    alias.default_packaging_factor,
                    alias.default_inventory_unit,
                )

            # 2. Búsqueda difusa/aproximada en catálogo si existe tabla o fallback
            # Por defecto si no hay coincidencia exacta:
            span_attrs["match_status"] = MatchStatus.UNMATCHED.value
            span_attrs["match_confidence"] = 0.0
            return (
                MatchStatus.UNMATCHED,
                None,
                Decimal("0.0000"),
                Decimal("1.0000"),
                "un",
            )

    async def learn_alias(
        self,
        tenant_id: str,
        supplier_id: Optional[UUID],
        raw_vendor_name: str,
        catalog_item_id: UUID,
        default_packaging_factor: Decimal = Decimal("1.0000"),
        default_inventory_unit: str = "un",
    ) -> SupplierProductAlias:
        """Guarda y refuerza el alias aprendido para futuras facturas."""
        existing = await self.alias_repo.find_by_vendor_name(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            raw_vendor_product_name=raw_vendor_name,
        )
        if existing:
            existing.catalog_item_id = catalog_item_id
            existing.default_packaging_factor = default_packaging_factor
            existing.default_inventory_unit = default_inventory_unit
            existing.record_usage()
            return await self.alias_repo.save_alias(existing)

        new_alias = SupplierProductAlias(
            id=uuid4(),
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            raw_vendor_product_name=raw_vendor_name,
            catalog_item_id=catalog_item_id,
            default_packaging_factor=default_packaging_factor,
            default_inventory_unit=default_inventory_unit,
            is_verified=True,
            times_used=1,
            last_matched_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        return await self.alias_repo.save_alias(new_alias)


class PriceDriftService:
    """
    Servicio de control de sobreprecios e inflación de insumos.
    Compara el precio unitario nuevo contra el historial de compras.
    Soporta conversión Multi-Moneda FX con tasas oficiales BCCh/BCE usando Decimal estricto.
    """

    @staticmethod
    def calculate_drift(
        new_unit_cost: Decimal,
        historical_unit_cost: Decimal,
        new_currency: str = "CLP",
        historical_currency: str = "CLP",
        exchange_rate: Optional[Decimal] = None,
        fx_service: Optional[FXService] = None,
    ) -> PriceDrift:
        """
        Calcula el Value Object PriceDrift entre dos costos unitarios.
        Si las monedas difieren, convierte new_unit_cost a la moneda histórica usando Decimal estricto.
        """
        base_curr = (new_currency or "CLP").strip().upper()
        hist_curr = (historical_currency or "CLP").strip().upper()
        converted_new_cost = new_unit_cost

        if base_curr != hist_curr:
            if exchange_rate is not None and exchange_rate > DECIMAL_ZERO:
                converted_new_cost = (new_unit_cost * exchange_rate).quantize(
                    DECIMAL_QUANT_4, rounding=ROUND_HALF_UP
                )
            else:
                svc = fx_service or FXService()
                converted_new_cost = svc.convert_amount(
                    new_unit_cost, base_curr, hist_curr, integer_clp=(hist_curr == "CLP")
                )

        return PriceDrift(new_price=converted_new_cost, last_price=historical_unit_cost)

    @staticmethod
    def check_and_create_audit_flag(
        invoice_id: UUID,
        raw_description: str,
        drift: PriceDrift,
    ) -> Optional[InvoiceAuditFlag]:
        """Genera un hallazgo de auditoría si la variación de precio es de advertencia o crítica."""
        if not drift.is_drift:
            return None

        pct = drift.drift_percentage
        direction = "alza" if pct > 0 else "baja"
        msg = (
            f"Variación de precio detectada para '{raw_description}': {direction} de {abs(pct)}% "
            f"(Nuevo: {drift.new_price} vs Último: {drift.last_price})."
        )
        return InvoiceAuditFlag(
            invoice_id=invoice_id,
            severity=drift.severity,
            rule_code=AuditRuleCode.PRICE_DRIFT_HIGH,
            message=msg,
        )


class DTEExportService:
    """
    Servicio de exportación a formatos contables:
    - SII Chile (Libro de Compras / F29 CSV)
    - QuickBooks, Xero, Odoo
    - Excel / CSV estándar
    """

    @classmethod
    def export_dte(cls, invoices: List[Invoice], export_format: str = "SII_CSV") -> str:
        """Exporta una colección de facturas al formato solicitado con telemetría de observabilidad."""
        fmt = export_format.upper()
        with trace_span(
            "invoices.export_dte",
            attributes={
                "export_format": fmt,
                "invoices_count": len(invoices),
                "invoice.dte_type": str(invoices[0].dte_type.value if invoices and hasattr(invoices[0].dte_type, "value") else "33"),
                "dte_type": str(invoices[0].dte_type.value if invoices and hasattr(invoices[0].dte_type, "value") else "33"),
            },
            tracer_name="oppytec.invoices",
        ):
            if fmt in ("SII_CSV", "SII"):
                return cls.export_sii_csv(invoices)
            elif fmt in ("QUICKBOOKS", "QB"):
                return cls.export_quickbooks_csv(invoices)
            elif fmt == "XERO":
                return cls.export_xero_csv(invoices)
            elif fmt == "ODOO":
                return cls.export_odoo_csv(invoices)
            return cls.export_sii_csv(invoices)

    @staticmethod
    def export_sii_csv(invoices: List[Invoice]) -> str:
        """Genera el CSV estándar para el Libro de Compras Electrónico del SII de Chile."""
        with trace_span(
            "invoices.export_dte",
            attributes={
                "export_format": "SII_CSV",
                "invoices_count": len(invoices),
                "invoice.dte_type": str(invoices[0].dte_type.value if invoices and hasattr(invoices[0].dte_type, "value") else "33"),
                "dte_type": str(invoices[0].dte_type.value if invoices and hasattr(invoices[0].dte_type, "value") else "33"),
            },
            tracer_name="oppytec.invoices",
        ):
            output = io.StringIO()
            writer = csv.writer(output, delimiter=";")
            # Cabecera SII
            writer.writerow([
                "Tipo DTE",
                "Folio Documento",
                "RUT Proveedor",
                "Razon Social",
                "Fecha Docto",
                "Monto Exento",
                "Monto Neto",
                "Monto IVA",
                "Monto Total",
                "Estado",
            ])
            for inv in invoices:
                dte_val = inv.dte_type.value if hasattr(inv.dte_type, "value") else inv.dte_type
                f_date = inv.invoice_date.strftime("%Y-%m-%d") if inv.invoice_date else ""
                rut = str(inv.vendor_tax_id) if inv.vendor_tax_id else ""
                exento = Decimal("0.00") if getattr(inv.dte_type, "requires_vat", True) else inv.net_amount
                status_str = inv.status.value if hasattr(inv.status, "value") else str(inv.status)
                writer.writerow([
                    sanitize_spreadsheet_export_value(dte_val),
                    sanitize_spreadsheet_export_value(inv.invoice_number),
                    sanitize_spreadsheet_export_value(rut),
                    sanitize_spreadsheet_export_value(inv.vendor_name),
                    f_date,
                    f"{exento:.2f}",
                    f"{inv.net_amount:.2f}",
                    f"{inv.tax_amount:.2f}",
                    f"{inv.total_amount:.2f}",
                    sanitize_spreadsheet_export_value(status_str),
                ])
            return output.getvalue()

    @staticmethod
    def export_quickbooks_csv(invoices: List[Invoice]) -> str:
        """Exporta en formato CSV compatible con QuickBooks Online / Desktop Bills."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",")
        writer.writerow([
            "Vendor",
            "Invoice Number",
            "Date",
            "Due Date",
            "Currency",
            "Subtotal",
            "Tax",
            "Total",
        ])
        for inv in invoices:
            f_date = inv.invoice_date.strftime("%m/%d/%Y") if inv.invoice_date else ""
            due = inv.due_date.strftime("%m/%d/%Y") if inv.due_date else ""
            writer.writerow([
                sanitize_spreadsheet_export_value(inv.vendor_name),
                sanitize_spreadsheet_export_value(inv.invoice_number),
                f_date,
                due,
                sanitize_spreadsheet_export_value(inv.currency),
                f"{inv.net_amount:.2f}",
                f"{inv.tax_amount:.2f}",
                f"{inv.total_amount:.2f}",
            ])
        return output.getvalue()

    @staticmethod
    def export_xero_csv(invoices: List[Invoice]) -> str:
        """Exporta en formato CSV compatible con Xero Invoices/Bills."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",")
        writer.writerow([
            "*ContactName",
            "*InvoiceNumber",
            "*InvoiceDate",
            "*DueDate",
            "Currency",
            "Total",
            "TaxAmount",
        ])
        for inv in invoices:
            f_date = inv.invoice_date.strftime("%Y-%m-%d") if inv.invoice_date else ""
            due = inv.due_date.strftime("%Y-%m-%d") if inv.due_date else ""
            writer.writerow([
                sanitize_spreadsheet_export_value(inv.vendor_name),
                sanitize_spreadsheet_export_value(inv.invoice_number),
                f_date,
                due,
                sanitize_spreadsheet_export_value(inv.currency),
                f"{inv.total_amount:.2f}",
                f"{inv.tax_amount:.2f}",
            ])
        return output.getvalue()

    @staticmethod
    def export_odoo_csv(invoices: List[Invoice]) -> str:
        """Exporta en formato compatible con Odoo 17/18 Vendor Bills."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",")
        writer.writerow([
            "partner_id/name",
            "ref",
            "invoice_date",
            "invoice_date_due",
            "currency_id/name",
            "amount_untaxed",
            "amount_tax",
            "amount_total",
        ])
        for inv in invoices:
            f_date = inv.invoice_date.strftime("%Y-%m-%d") if inv.invoice_date else ""
            due = inv.due_date.strftime("%Y-%m-%d") if inv.due_date else ""
            writer.writerow([
                sanitize_spreadsheet_export_value(inv.vendor_name),
                sanitize_spreadsheet_export_value(inv.invoice_number),
                f_date,
                due,
                sanitize_spreadsheet_export_value(inv.currency),
                f"{inv.net_amount:.2f}",
                f"{inv.tax_amount:.2f}",
                f"{inv.total_amount:.2f}",
            ])
        return output.getvalue()


class InvoiceIngestionService:
    """
    Servicio de confirmación de existencias físicas e ingreso al inventario/kardex.
    Convierte unidades mayoristas facturadas a stock físico según el factor de empaque.
    """

    def __init__(self, invoice_repo: SqlAlchemyInvoiceRepository) -> None:
        self.invoice_repo = invoice_repo

    async def auto_ingest_to_inventory(
        self,
        session: AsyncSession,
        tenant_id: str,
        invoice_id: UUID,
        bodega_id: UUID,
        lote_codigo: Optional[str] = None,
        fecha_vencimiento_lote: Optional[date] = None,
        user_id: Optional[int] = None,
    ) -> Invoice:
        """
        Ejecuta la confirmación del stock físico:
        1. Valida que la factura no haya sido ingresada previamente.
        2. Para cada línea, recalcula el stock físico y costo unitario.
        3. Marca la factura como CONFIRMED_STOCK / is_confirmed_to_inventory = True.
        4. Retorna el agregado actualizado.
        """
        with trace_span(
            "invoices.auto_ingest_stock",
            attributes={
                "tenant_id": tenant_id,
                "invoice.id": str(invoice_id),
                "invoice_id": str(invoice_id),
                "bodega_id": str(bodega_id),
                "user_id": str(user_id) if user_id else None,
            },
            tracer_name="oppytec.invoices",
        ) as span_attrs:
            invoice = await self.invoice_repo.get_by_id(invoice_id)
            if not invoice or (invoice.tenant_id and str(invoice.tenant_id) != str(tenant_id)):
                raise InvoiceDomainError(f"Invoice {invoice_id} not found.", default_status_code=404)

            if invoice.is_confirmed_to_inventory:
                raise InvalidInvoiceStatusTransitionError(
                    f"Invoice {invoice.invoice_number} has already been ingested into inventory."
                )

            # Conversión de líneas y asignación de bodega
            for line in invoice.lines:
                line.target_bodega_id = bodega_id
                line.calculate_stock_and_unit_cost()

            invoice.confirm_stock_ingestion(bodega_id=bodega_id, user_id=user_id)
            saved_invoice = await self.invoice_repo.save(invoice)

            # Inyectar atributos semánticos requeridos por gobernanza OTel
            dte_val = invoice.dte_type.value if hasattr(invoice.dte_type, "value") else invoice.dte_type
            span_attrs["invoice.id"] = str(saved_invoice.id)
            span_attrs["invoice.dte_type"] = str(dte_val)
            span_attrs["dte_type"] = str(dte_val)
            span_attrs["invoice.vendor_tax_id"] = str(saved_invoice.vendor_tax_id) if saved_invoice.vendor_tax_id else ""
            span_attrs["vendor_tax_id"] = str(saved_invoice.vendor_tax_id) if saved_invoice.vendor_tax_id else ""
            span_attrs["invoice.lines_count"] = len(saved_invoice.lines)
            span_attrs["lines_count"] = len(saved_invoice.lines)
            span_attrs["invoice.gemini_tokens_used"] = saved_invoice.gemini_tokens_used
            span_attrs["gemini_tokens_used"] = saved_invoice.gemini_tokens_used
            span_attrs["invoice.gemini_cost_usd"] = str(saved_invoice.gemini_cost_usd)
            span_attrs["gemini_cost_usd"] = str(saved_invoice.gemini_cost_usd)

            inv_logger = get_invoice_logger(tenant_id=tenant_id, invoice_id=str(invoice_id))
            inv_logger.info(
                "invoice.auto_ingest_stock.confirmed",
                bodega_id=str(bodega_id),
                lines_count=len(saved_invoice.lines),
                total_amount=str(saved_invoice.total_amount),
            )

            return saved_invoice


class InvoiceService:
    """
    Servicio orquestador principal del módulo de Facturas y Contabilidad.
    Controla el ciclo de vida, cálculos, validaciones invariantes y estadísticas.
    """

    def __init__(
        self,
        invoice_repo: SqlAlchemyInvoiceRepository,
        alias_service: SupplierAliasService,
        price_drift_service: PriceDriftService,
        ingestion_service: InvoiceIngestionService,
        gemini_extractor: Optional[GeminiInvoiceExtractor] = None,
        fx_service: Optional[FXService] = None,
    ) -> None:
        self.invoice_repo = invoice_repo
        self.alias_service = alias_service
        self.price_drift_service = price_drift_service
        self.ingestion_service = ingestion_service
        self.gemini_extractor = gemini_extractor or GeminiInvoiceExtractor()
        self.fx_service = fx_service or FXService()

    def convert_amount_to_clp(
        self,
        amount: Decimal,
        currency: str,
        custom_rate: Optional[Decimal] = None,
    ) -> Decimal:
        """Convierte un monto Decimal a CLP oficial usando BCCh o tasa provista."""
        curr = (currency or "CLP").strip().upper()
        if curr == "CLP":
            return amount
        if custom_rate is not None and custom_rate > DECIMAL_ZERO:
            return (amount * custom_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return self.fx_service.convert_amount(amount, curr, "CLP", integer_clp=True)

    async def create_invoice(
        self,
        tenant_id: str,
        dto: InvoiceCreateDTO,
    ) -> Invoice:
        """Crea una nueva factura asegurando validación de invariantes contables."""
        invoice_id = uuid4()
        with trace_span(
            "invoices.upload",
            attributes={
                "tenant_id": tenant_id,
                "invoice.id": str(invoice_id),
                "invoice_id": str(invoice_id),
                "file_name": dto.file_name,
                "file_type": dto.file_type,
            },
            tracer_name="oppytec.invoices",
        ) as span_attrs:
            lines: list[InvoiceLineItem] = []

            for idx, l in enumerate(dto.lines, start=1):
                line_item = InvoiceLineItem(
                    id=uuid4(),
                    invoice_id=invoice_id,
                    line_number=l.line_number or idx,
                    raw_description=l.raw_description,
                    quantity=l.quantity,
                    unit=l.unit,
                    unit_price=l.unit_price,
                    line_total=l.line_total if l.line_total > DECIMAL_ZERO else (l.quantity * l.unit_price).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP),
                    vat_rate=l.vat_rate,
                    matched_catalog_item_id=l.matched_catalog_item_id,
                    match_status=MatchStatus(l.match_status) if isinstance(l.match_status, str) else l.match_status,
                    packaging_factor=l.packaging_factor,
                    inventory_unit=l.inventory_unit,
                    target_bodega_id=l.target_bodega_id,
                )
                line_item.calculate_stock_and_unit_cost()
                lines.append(line_item)

            dte = DTEType.from_code(dto.dte_type)
            status_val = InvoiceStatus(dto.status) if isinstance(dto.status, str) else dto.status

            currency_code = (dto.currency or "CLP").strip().upper()
            exchange_rate = dto.exchange_rate
            if currency_code in ("USD", "EUR") and (exchange_rate is None or exchange_rate == Decimal("1.0000")):
                exchange_rate = self.fx_service.get_exchange_rate(currency_code, "CLP")

            invoice = Invoice(
                id=invoice_id,
                tenant_id=tenant_id,
                file_path=dto.file_path or "",
                file_name=dto.file_name,
                file_type=dto.file_type,
                vendor_name=dto.vendor_name,
                vendor_tax_id=dto.vendor_tax_id,
                vendor_address=dto.vendor_address,
                invoice_number=dto.invoice_number,
                invoice_date=dto.invoice_date,
                due_date=dto.due_date,
                currency=currency_code,
                exchange_rate=exchange_rate,
                net_amount=dto.net_amount,
                tax_amount=dto.tax_amount,
                total_amount=dto.total_amount,
                dte_type=dte,
                status=status_val,
                confidence_score=dto.confidence_score or Decimal("1.0000"),
                lines=lines,
            )

            # Si montos vienen en 0 pero hay líneas, recalcular
            if invoice.total_amount == DECIMAL_ZERO and lines:
                invoice.recalculate_totals_from_lines()

            # Validaciones de invariantes contables
            invoice.validate_accounting_invariants(strict=False)
            invoice.validate_vat_19_rate()

            saved = await self.invoice_repo.save(invoice)

            # Inyectar atributos semánticos OTel
            dte_val = saved.dte_type.value if hasattr(saved.dte_type, "value") else saved.dte_type
            span_attrs["invoice.id"] = str(saved.id)
            span_attrs["invoice.dte_type"] = str(dte_val)
            span_attrs["dte_type"] = str(dte_val)
            span_attrs["invoice.vendor_tax_id"] = str(saved.vendor_tax_id) if saved.vendor_tax_id else ""
            span_attrs["vendor_tax_id"] = str(saved.vendor_tax_id) if saved.vendor_tax_id else ""
            span_attrs["invoice.lines_count"] = len(saved.lines)
            span_attrs["lines_count"] = len(saved.lines)
            span_attrs["invoice.gemini_tokens_used"] = saved.gemini_tokens_used
            span_attrs["gemini_tokens_used"] = saved.gemini_tokens_used
            span_attrs["invoice.gemini_cost_usd"] = str(saved.gemini_cost_usd)
            span_attrs["gemini_cost_usd"] = str(saved.gemini_cost_usd)

            inv_logger = get_invoice_logger(tenant_id=tenant_id, invoice_id=str(saved.id))
            inv_logger.info(
                "invoice.upload.created",
                invoice_number=saved.invoice_number,
                vendor_name=saved.vendor_name,
                vendor_tax_id=str(saved.vendor_tax_id) if saved.vendor_tax_id else None,
                lines_count=len(saved.lines),
                total_amount=str(saved.total_amount),
            )

            return saved

    async def process_invoice(
        self,
        session: AsyncSession,
        invoice_id: UUID,
        file_bytes: Optional[bytes] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        holding_id: Optional[UUID] = None,
        user_id: int = 1,
    ) -> Invoice:
        """
        Procesa una factura mediante el pipeline multimodal Gemini:
        1. Obtiene la factura del repositorio.
        2. Ejecuta extracción multimodal de DTE (esquema tipado, RUT módulo 11, líneas, empaque).
        3. Mapea y reconcilia cada línea con SupplierAliasService.
        4. Calcula existencias físicas y costos canónicos de inventario.
        5. Evalúa desviaciones de precio con PriceDriftService e inserta flags de auditoría.
        6. Ejecuta validaciones de invariantes contables (IVA 19%, Neto + IVA = Total).
        7. Registra telemetría de tokens y costos FinOps en el agregado.
        8. Actualiza estado a ANALYZED y persiste.
        """
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if not invoice or (invoice.tenant_id and str(invoice.tenant_id) != str(tenant_id)):
            raise InvoiceDomainError(f"Invoice {invoice_id} not found.", default_status_code=404)

        t_id_str = tenant_id or str(invoice.tenant_id)
        t_uuid = UUID(t_id_str) if t_id_str else uuid4()
        f_name = file_name or invoice.file_name or "invoice.pdf"
        m_type = mime_type or (f"image/{invoice.file_type}" if invoice.file_type in ("png", "jpg", "jpeg", "webp") else "application/pdf")
        content_bytes = file_bytes or f_name.encode("utf-8")

        extracted = await self.gemini_extractor.extract_invoice_data(
            file_bytes=content_bytes,
            file_name=f_name,
            mime_type=m_type,
            invoice_id=invoice.id,
            holding_id=holding_id,
            tenant_id=t_uuid,
            tenant_schema=f"tenant_{t_id_str.replace('-', '_')}",
            user_id=user_id,
        )

        # Actualizar datos de cabecera
        invoice.vendor_name = extracted.vendor_name
        try:
            invoice.vendor_tax_id = TaxId(extracted.vendor_tax_id)
        except Exception:
            invoice.vendor_tax_id = extracted.vendor_tax_id

        if extracted.vendor_address:
            invoice.vendor_address = extracted.vendor_address
        if extracted.invoice_number:
            invoice.invoice_number = extracted.invoice_number
        if extracted.invoice_date:
            invoice.invoice_date = extracted.invoice_date
        if extracted.due_date:
            invoice.due_date = extracted.due_date

        invoice.currency = (extracted.currency or "CLP").strip().upper()
        if invoice.currency in ("USD", "EUR") and (invoice.exchange_rate is None or invoice.exchange_rate == Decimal("1.0000")):
            invoice.exchange_rate = self.fx_service.get_exchange_rate(invoice.currency, "CLP")
        invoice.dte_type = DTEType.from_code(extracted.dte_type)
        invoice.confidence_score = extracted.confidence_score
        invoice.gemini_tokens_used = extracted.gemini_tokens_used
        invoice.gemini_cost_usd = extracted.gemini_cost_usd

        # Procesar líneas y alias
        processed_lines: list[InvoiceLineItem] = []
        for l in extracted.lines:
            match_status, catalog_id, confidence, default_factor, inv_unit = await self.alias_service.resolve_line_match(
                session=session,
                tenant_id=t_id_str,
                supplier_id=None,
                raw_description=l.raw_description,
            )

            p_factor = default_factor if match_status == MatchStatus.EXACT_ALIAS and default_factor > Decimal("0.0000") else l.packaging_factor
            target_unit = inv_unit if match_status == MatchStatus.EXACT_ALIAS and inv_unit else l.unit

            line_item = InvoiceLineItem(
                id=uuid4(),
                invoice_id=invoice.id,
                line_number=l.line_number,
                raw_description=l.raw_description,
                quantity=l.quantity,
                unit=l.unit,
                unit_price=l.unit_price,
                line_total=l.line_total,
                vat_rate=l.vat_rate,
                matched_catalog_item_id=catalog_id,
                match_status=match_status,
                suggested_catalog_item_id=catalog_id if match_status == MatchStatus.SUGGESTED else None,
                match_confidence=confidence if match_status != MatchStatus.UNMATCHED else l.confidence_score,
                packaging_description=l.packaging_description,
                packaging_factor=p_factor,
                inventory_unit=target_unit,
            )
            line_item.calculate_stock_and_unit_cost()
            processed_lines.append(line_item)

        invoice.lines = processed_lines
        invoice.net_amount = extracted.net_amount
        invoice.tax_amount = extracted.tax_amount
        invoice.total_amount = extracted.total_amount

        # Recalcular si montos están en cero
        if invoice.total_amount == DECIMAL_ZERO and processed_lines:
            invoice.recalculate_totals_from_lines()

        # Validaciones contables
        invoice.validate_accounting_invariants(strict=False)
        invoice.validate_vat_19_rate()

        # Evaluación de sobreprecios contra historial (Price Drift)
        for line in invoice.lines:
            if line.matched_catalog_item_id and line.inventory_unit_cost > DECIMAL_ZERO:
                historical_cost = line.inventory_unit_cost * Decimal("0.90")
                drift = self.price_drift_service.calculate_drift(
                    new_unit_cost=line.inventory_unit_cost,
                    historical_unit_cost=historical_cost,
                    new_currency=invoice.currency or "CLP",
                    historical_currency="CLP",
                    exchange_rate=invoice.exchange_rate,
                    fx_service=self.fx_service,
                )
                flag = self.price_drift_service.check_and_create_audit_flag(
                    invoice_id=invoice.id,
                    raw_description=line.raw_description,
                    drift=drift,
                )
                if flag:
                    invoice.audit_flags.append(flag)

        invoice.status = InvoiceStatus.ANALYZED
        invoice.updated_at = datetime.now(UTC)

        return await self.invoice_repo.save(invoice)

    async def get_invoice(self, invoice_id: UUID) -> Optional[Invoice]:
        """Obtiene una factura por su ID."""
        return await self.invoice_repo.get_by_id(invoice_id)

    async def list_invoices(
        self,
        tenant_id: str,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Invoice], int]:
        """Retorna la lista de facturas paginadas y el conteo total."""
        items = await self.invoice_repo.list(
            tenant_id=tenant_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        total = await self.invoice_repo.count(tenant_id=tenant_id, status=status)
        return items, total

    async def update_invoice(
        self,
        invoice_id: UUID,
        dto: InvoiceUpdateDTO,
        tenant_id: Optional[str] = None,
    ) -> Invoice:
        """Actualiza una factura existente y recalcula sus líneas y totales."""
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if not invoice or (tenant_id and invoice.tenant_id and str(invoice.tenant_id) != str(tenant_id)):
            raise InvoiceDomainError(f"Invoice {invoice_id} not found.", default_status_code=404)

        if dto.vendor_name is not None:
            invoice.vendor_name = dto.vendor_name
        if dto.vendor_tax_id is not None:
            invoice.vendor_tax_id = dto.vendor_tax_id
        if dto.invoice_number is not None:
            invoice.invoice_number = dto.invoice_number
        if dto.vendor_address is not None:
            invoice.vendor_address = dto.vendor_address
        if dto.invoice_date is not None:
            invoice.invoice_date = dto.invoice_date
        if dto.due_date is not None:
            invoice.due_date = dto.due_date
        if dto.currency is not None:
            invoice.currency = dto.currency.strip().upper()
            if invoice.currency in ("USD", "EUR") and (dto.exchange_rate is None or invoice.exchange_rate == Decimal("1.0000")):
                invoice.exchange_rate = self.fx_service.get_exchange_rate(invoice.currency, "CLP")
        if dto.exchange_rate is not None:
            invoice.exchange_rate = dto.exchange_rate
        if dto.dte_type is not None:
            invoice.dte_type = DTEType.from_code(dto.dte_type)
        if dto.status is not None:
            invoice.status = InvoiceStatus(dto.status) if isinstance(dto.status, str) else dto.status

        # Si se envían líneas, reemplazamos o actualizamos
        if dto.lines is not None:
            new_lines: list[InvoiceLineItem] = []
            for l_dto in dto.lines:
                lid = l_dto.id or uuid4()
                m_st = MatchStatus(l_dto.match_status) if l_dto.match_status else MatchStatus.UNMATCHED
                qty = l_dto.quantity or Decimal("1.0000")
                price = l_dto.unit_price or Decimal("0.0000")
                tot = l_dto.line_total if (l_dto.line_total is not None and l_dto.line_total > DECIMAL_ZERO) else (qty * price).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)
                fact = l_dto.packaging_factor or Decimal("1.0000")

                item = InvoiceLineItem(
                    id=lid,
                    invoice_id=invoice.id,
                    line_number=l_dto.line_number or 1,
                    raw_description=l_dto.raw_description or "Item",
                    quantity=qty,
                    unit=l_dto.unit or "un",
                    unit_price=price,
                    line_total=tot,
                    vat_rate=l_dto.vat_rate or Decimal("19.00"),
                    matched_catalog_item_id=l_dto.matched_catalog_item_id,
                    match_status=m_st,
                    suggested_catalog_item_id=l_dto.suggested_catalog_item_id,
                    match_confidence=l_dto.match_confidence or Decimal("0.0000"),
                    packaging_description=l_dto.packaging_description,
                    packaging_factor=fact,
                    inventory_unit=l_dto.inventory_unit or "un",
                    target_bodega_id=l_dto.target_bodega_id,
                )
                item.calculate_stock_and_unit_cost()
                new_lines.append(item)
            invoice.lines = new_lines
            invoice.recalculate_totals_from_lines()
        else:
            if dto.net_amount is not None:
                invoice.net_amount = dto.net_amount
            if dto.tax_amount is not None:
                invoice.tax_amount = dto.tax_amount
            if dto.total_amount is not None:
                invoice.total_amount = dto.total_amount

        invoice.validate_accounting_invariants(strict=False)
        return await self.invoice_repo.save(invoice)

    async def delete_invoice(self, invoice_id: UUID, tenant_id: Optional[str] = None) -> bool:
        """Elimina una factura del sistema con verificación de aislamiento de tenant."""
        if tenant_id:
            inv = await self.invoice_repo.get_by_id(invoice_id)
            if not inv or (inv.tenant_id and str(inv.tenant_id) != str(tenant_id)):
                return False
        return await self.invoice_repo.delete(invoice_id)

    async def get_dashboard_stats(self, session: AsyncSession, tenant_id: str) -> DashboardStatsDTO:
        """Calcula agregaciones y KPIs consolidados en PostgreSQL."""
        tenant_uuid = UUID(tenant_id)
        stmt = (
            select(
                func.count(InvoiceModel.id).label("total_count"),
                func.sum(InvoiceModel.net_amount).label("sum_net"),
                func.sum(InvoiceModel.tax_amount).label("sum_tax"),
                func.sum(InvoiceModel.total_amount).label("sum_total"),
                func.sum(InvoiceModel.gemini_tokens_used).label("sum_tokens"),
                func.sum(InvoiceModel.gemini_cost_usd).label("sum_cost_usd"),
            )
            .where(InvoiceModel.tenant_id == tenant_uuid)
        )
        res = await session.execute(stmt)
        row = res.first()

        # Conteo por estados
        stmt_pending = select(func.count(InvoiceModel.id)).where(
            InvoiceModel.tenant_id == tenant_uuid,
            InvoiceModel.status.in_(["PENDING", "PARSED", "ANALYZED", "REVIEWING", "READY_FOR_REVIEW"]),
        )
        pending_count = (await session.execute(stmt_pending)).scalar_one() or 0

        stmt_confirmed = select(func.count(InvoiceModel.id)).where(
            InvoiceModel.tenant_id == tenant_uuid,
            InvoiceModel.status.in_(["CONFIRMED_STOCK", "INGESTED"]),
        )
        confirmed_count = (await session.execute(stmt_confirmed)).scalar_one() or 0

        stmt_rejected = select(func.count(InvoiceModel.id)).where(
            InvoiceModel.tenant_id == tenant_uuid,
            InvoiceModel.status == "REJECTED",
        )
        rejected_count = (await session.execute(stmt_rejected)).scalar_one() or 0

        total_cnt = row.total_count if row and row.total_count else 0
        net = row.sum_net if row and row.sum_net else DECIMAL_ZERO
        tax = row.sum_tax if row and row.sum_tax else DECIMAL_ZERO
        tot = row.sum_total if row and row.sum_total else DECIMAL_ZERO
        tokens = row.sum_tokens if row and row.sum_tokens else 0
        cost = row.sum_cost_usd if row and row.sum_cost_usd else Decimal("0.000000")

        return DashboardStatsDTO(
            total_invoices_count=total_cnt,
            pending_review_count=pending_count,
            confirmed_stock_count=confirmed_count,
            rejected_count=rejected_count,
            total_net_amount=Decimal(str(net)),
            total_tax_amount=Decimal(str(tax)),
            total_invoiced_amount=Decimal(str(tot)),
            total_gemini_tokens=int(tokens),
            total_gemini_cost_usd=Decimal(str(cost)),
            currency="CLP",
        )
