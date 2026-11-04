"""
oppytec-backend/src/modules/invoices/infrastructure/repositories.py
Implementación de Repositorios SQLAlchemy 2.0 Async para el agregado Invoice y SupplierProductAlias.
Implementa InvoiceRepositoryPort y SupplierAliasRepositoryPort con soporte dinámico de esquemas multi-tenant.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.invoices.domain.entities import (
    Invoice,
    InvoiceAuditFlag,
    InvoiceLineItem,
    SupplierProductAlias,
)
from src.modules.invoices.domain.ports import (
    InvoiceRepositoryPort,
    SupplierAliasRepositoryPort,
)
from src.modules.invoices.domain.value_objects import (
    DTEType,
    InvoiceStatus,
    MatchStatus,
    TaxId,
)
from src.modules.invoices.infrastructure.models import (
    InvoiceAuditFlagModel,
    InvoiceLineItemModel,
    InvoiceModel,
    SupplierProductAliasModel,
)

logger = logging.getLogger(__name__)


def _model_to_entity(model: InvoiceModel) -> Invoice:
    """Convierte un InvoiceModel de SQLAlchemy en una entidad de dominio pura Invoice."""
    lines_entities: list[InvoiceLineItem] = []
    for l_mod in model.lines or []:
        m_status = MatchStatus.UNMATCHED
        try:
            m_status = MatchStatus(l_mod.match_status)
        except Exception:
            pass

        lines_entities.append(
            InvoiceLineItem(
                id=l_mod.id,
                invoice_id=l_mod.invoice_id,
                line_number=l_mod.line_number,
                raw_description=l_mod.raw_description,
                quantity=l_mod.quantity,
                unit=l_mod.unit,
                unit_price=l_mod.unit_price,
                line_total=l_mod.line_total,
                vat_rate=l_mod.vat_rate,
                matched_catalog_item_id=l_mod.matched_catalog_item_id,
                match_status=m_status,
                suggested_catalog_item_id=l_mod.suggested_catalog_item_id,
                match_confidence=l_mod.match_confidence or 0,  # type: ignore
                packaging_description=l_mod.packaging_description,
                packaging_factor=l_mod.packaging_factor,
                calculated_stock_qty=l_mod.calculated_stock_qty,
                inventory_unit=l_mod.inventory_unit,
                inventory_unit_cost=l_mod.inventory_unit_cost,
                target_bodega_id=l_mod.target_bodega_id,
            )
        )

    flags_entities: list[InvoiceAuditFlag] = []
    for f_mod in model.audit_flags or []:
        flags_entities.append(
            InvoiceAuditFlag(
                id=f_mod.id,
                invoice_id=f_mod.invoice_id,
                severity=f_mod.severity,
                rule_code=f_mod.rule_code,
                message=f_mod.message,
                created_at=f_mod.created_at,
            )
        )

    dte = DTEType.FACTURA_ELECTRONICA
    try:
        dte = DTEType.from_code(model.dte_type)
    except Exception:
        pass

    inv_status = InvoiceStatus.PENDING
    try:
        inv_status = InvoiceStatus(model.status)
    except Exception:
        pass

    tax_id = model.vendor_tax_id or ""
    try:
        tax_id = TaxId(model.vendor_tax_id)  # type: ignore
    except Exception:
        pass

    return Invoice(
        id=model.id,
        tenant_id=str(model.tenant_id) if model.tenant_id else None,
        file_path=model.file_path or "",
        file_name=model.file_name,
        file_type=model.file_type,
        vendor_name=model.vendor_name or "",
        vendor_tax_id=tax_id,
        vendor_address=model.vendor_address,
        invoice_number=model.invoice_number or "",
        invoice_date=model.invoice_date,
        due_date=model.due_date,
        currency=model.currency,
        exchange_rate=model.exchange_rate,
        net_amount=model.net_amount,
        tax_amount=model.tax_amount,
        total_amount=model.total_amount,
        dte_type=dte,
        status=inv_status,
        confidence_score=model.confidence_score or 1,  # type: ignore
        gemini_tokens_used=model.gemini_tokens_used,
        gemini_cost_usd=model.gemini_cost_usd,
        is_confirmed_to_inventory=model.is_stock_ingested,
        created_at=model.created_at,
        updated_at=model.updated_at,
        lines=lines_entities,
        audit_flags=flags_entities,
    )


class SqlAlchemyInvoiceRepository(InvoiceRepositoryPort):
    """
    Repositorio SQLAlchemy 2.0 Async para el agregado Invoice.
    Gestiona la persistencia de cabecera, líneas y flags de auditoría en la BD del tenant.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Obtiene una factura por su identificador único junto con sus líneas y flags."""
        stmt = (
            select(InvoiceModel)
            .options(
                selectinload(InvoiceModel.lines),
                selectinload(InvoiceModel.audit_flags),
            )
            .where(InvoiceModel.id == invoice_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return _model_to_entity(model)

    async def get_by_file_hash(self, tenant_id: str, file_hash_sha256: str) -> Invoice | None:
        """Busca una factura por el hash SHA-256 o ruta que contenga el hash."""
        stmt = (
            select(InvoiceModel)
            .options(
                selectinload(InvoiceModel.lines),
                selectinload(InvoiceModel.audit_flags),
            )
            .where(
                InvoiceModel.tenant_id == UUID(tenant_id),
                InvoiceModel.file_path.ilike(f"%{file_hash_sha256}%"),
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return _model_to_entity(model)

    async def save(self, invoice: Invoice) -> Invoice:
        """Persiste una factura nueva o sincroniza las modificaciones de una existente."""
        stmt = (
            select(InvoiceModel)
            .options(
                selectinload(InvoiceModel.lines),
                selectinload(InvoiceModel.audit_flags),
            )
            .where(InvoiceModel.id == invoice.id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        tax_id_val = str(invoice.vendor_tax_id) if invoice.vendor_tax_id else None
        dte_code = invoice.dte_type.value if hasattr(invoice.dte_type, "value") else int(invoice.dte_type)
        status_val = invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status)
        tenant_uuid = UUID(str(invoice.tenant_id)) if invoice.tenant_id else UUID("00000000-0000-0000-0000-000000000000")

        if not model:
            model = InvoiceModel(
                id=invoice.id,
                tenant_id=tenant_uuid,
                file_path=invoice.file_path,
                file_name=invoice.file_name,
                file_type=invoice.file_type,
                vendor_name=invoice.vendor_name,
                vendor_tax_id=tax_id_val,
                vendor_address=invoice.vendor_address,
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                currency=invoice.currency,
                exchange_rate=invoice.exchange_rate,
                net_amount=invoice.net_amount,
                tax_amount=invoice.tax_amount,
                total_amount=invoice.total_amount,
                dte_type=dte_code,
                status=status_val,
                confidence_score=invoice.confidence_score,
                gemini_tokens_used=invoice.gemini_tokens_used,
                gemini_cost_usd=invoice.gemini_cost_usd,
                is_stock_ingested=invoice.is_confirmed_to_inventory,
                created_at=invoice.created_at,
                updated_at=invoice.updated_at,
            )
            self.session.add(model)
        else:
            model.file_path = invoice.file_path
            model.file_name = invoice.file_name
            model.file_type = invoice.file_type
            model.vendor_name = invoice.vendor_name
            model.vendor_tax_id = tax_id_val
            model.vendor_address = invoice.vendor_address
            model.invoice_number = invoice.invoice_number
            model.invoice_date = invoice.invoice_date
            model.due_date = invoice.due_date
            model.currency = invoice.currency
            model.exchange_rate = invoice.exchange_rate
            model.net_amount = invoice.net_amount
            model.tax_amount = invoice.tax_amount
            model.total_amount = invoice.total_amount
            model.dte_type = dte_code
            model.status = status_val
            model.confidence_score = invoice.confidence_score
            model.gemini_tokens_used = invoice.gemini_tokens_used
            model.gemini_cost_usd = invoice.gemini_cost_usd
            model.is_stock_ingested = invoice.is_confirmed_to_inventory
            model.updated_at = invoice.updated_at

        # Sincronización de líneas (reemplazo defensivo de líneas)
        model.lines.clear()
        for l in invoice.lines:
            m_status_val = l.match_status.value if hasattr(l.match_status, "value") else str(l.match_status)
            line_mod = InvoiceLineItemModel(
                id=l.id,
                invoice_id=invoice.id,
                line_number=l.line_number,
                raw_description=l.raw_description,
                quantity=l.quantity,
                unit=l.unit,
                unit_price=l.unit_price,
                line_total=l.line_total,
                vat_rate=l.vat_rate,
                matched_catalog_item_id=l.matched_catalog_item_id,
                match_status=m_status_val,
                suggested_catalog_item_id=l.suggested_catalog_item_id,
                match_confidence=l.match_confidence,
                packaging_description=l.packaging_description,
                packaging_factor=l.packaging_factor,
                calculated_stock_qty=l.calculated_stock_qty,
                inventory_unit=l.inventory_unit,
                inventory_unit_cost=l.inventory_unit_cost,
                target_bodega_id=l.target_bodega_id,
            )
            model.lines.append(line_mod)

        # Sincronización de audit flags
        model.audit_flags.clear()
        for f in invoice.audit_flags:
            sev_val = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            rule_val = f.rule_code.value if hasattr(f.rule_code, "value") else str(f.rule_code)
            flag_mod = InvoiceAuditFlagModel(
                id=f.id,
                invoice_id=invoice.id,
                severity=sev_val,
                rule_code=rule_val,
                message=f.message,
                created_at=f.created_at,
            )
            model.audit_flags.append(flag_mod)

        await self.session.flush()
        return _model_to_entity(model)

    async def list(
        self,
        tenant_id: str,
        status: InvoiceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invoice]:
        """Obtiene el listado paginado de facturas filtradas por tenant y estado."""
        stmt = (
            select(InvoiceModel)
            .options(
                selectinload(InvoiceModel.lines),
                selectinload(InvoiceModel.audit_flags),
            )
            .where(InvoiceModel.tenant_id == UUID(tenant_id))
            .order_by(InvoiceModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            status_val = status.value if hasattr(status, "value") else str(status)
            stmt = stmt.where(InvoiceModel.status == status_val)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_model_to_entity(m) for m in models]

    async def count(
        self,
        tenant_id: str,
        status: InvoiceStatus | None = None,
    ) -> int:
        """Cuenta el total de facturas para paginación."""
        stmt = (
            select(func.count(InvoiceModel.id))
            .where(InvoiceModel.tenant_id == UUID(tenant_id))
        )
        if status is not None:
            status_val = status.value if hasattr(status, "value") else str(status)
            stmt = stmt.where(InvoiceModel.status == status_val)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete(self, invoice_id: UUID) -> bool:
        """Elimina una factura del repositorio."""
        stmt = delete(InvoiceModel).where(InvoiceModel.id == invoice_id)
        res = await self.session.execute(stmt)
        await self.session.flush()
        return bool(res.rowcount and res.rowcount > 0)


class SqlAlchemySupplierAliasRepository(SupplierAliasRepositoryPort):
    """
    Repositorio SQLAlchemy 2.0 Async para la memoria de aliases de proveedor (`SupplierProductAlias`).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_vendor_name(
        self,
        tenant_id: str,
        supplier_id: UUID | None,
        raw_vendor_product_name: str,
    ) -> SupplierProductAlias | None:
        """Busca un alias exacto para el tenant y nombre crudo del producto."""
        stmt = (
            select(SupplierProductAliasModel)
            .where(
                SupplierProductAliasModel.tenant_id == UUID(tenant_id),
                func.lower(SupplierProductAliasModel.raw_vendor_product_name) == func.lower(raw_vendor_product_name.strip()),
            )
        )
        if supplier_id is not None:
            stmt = stmt.where(SupplierProductAliasModel.supplier_id == supplier_id)

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        return SupplierProductAlias(
            id=model.id,
            tenant_id=str(model.tenant_id),
            supplier_id=model.supplier_id,
            raw_vendor_product_name=model.raw_vendor_product_name,
            catalog_item_id=model.catalog_item_id,
            default_packaging_factor=model.default_packaging_factor,
            default_inventory_unit=model.default_inventory_unit,
            is_verified=model.is_verified,
            times_used=model.times_used,
            last_matched_at=model.last_matched_at,
            created_at=model.created_at,
        )

    async def save_alias(self, alias: SupplierProductAlias) -> SupplierProductAlias:
        """Guarda o actualiza un alias de proveedor."""
        stmt = select(SupplierProductAliasModel).where(SupplierProductAliasModel.id == alias.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        tenant_uuid = UUID(str(alias.tenant_id)) if alias.tenant_id else UUID("00000000-0000-0000-0000-000000000000")

        if not model:
            model = SupplierProductAliasModel(
                id=alias.id,
                tenant_id=tenant_uuid,
                supplier_id=alias.supplier_id,
                raw_vendor_product_name=alias.raw_vendor_product_name,
                catalog_item_id=alias.catalog_item_id,
                default_packaging_factor=alias.default_packaging_factor,
                default_inventory_unit=alias.default_inventory_unit,
                is_verified=alias.is_verified,
                times_used=alias.times_used,
                last_matched_at=alias.last_matched_at or func.now(),
                created_at=alias.created_at,
            )
            self.session.add(model)
        else:
            model.raw_vendor_product_name = alias.raw_vendor_product_name
            model.catalog_item_id = alias.catalog_item_id
            model.default_packaging_factor = alias.default_packaging_factor
            model.default_inventory_unit = alias.default_inventory_unit
            model.is_verified = alias.is_verified
            model.times_used = alias.times_used
            model.last_matched_at = alias.last_matched_at or func.now()

        await self.session.flush()
        return SupplierProductAlias(
            id=model.id,
            tenant_id=str(model.tenant_id),
            supplier_id=model.supplier_id,
            raw_vendor_product_name=model.raw_vendor_product_name,
            catalog_item_id=model.catalog_item_id,
            default_packaging_factor=model.default_packaging_factor,
            default_inventory_unit=model.default_inventory_unit,
            is_verified=model.is_verified,
            times_used=model.times_used,
            last_matched_at=model.last_matched_at,
            created_at=model.created_at,
        )

    async def list_by_supplier(
        self,
        tenant_id: str,
        supplier_id: UUID | None = None,
    ) -> list[SupplierProductAlias]:
        """Obtiene todos los alias conocidos para un proveedor o para todo el tenant."""
        stmt = (
            select(SupplierProductAliasModel)
            .where(SupplierProductAliasModel.tenant_id == UUID(tenant_id))
            .order_by(SupplierProductAliasModel.times_used.desc())
        )
        if supplier_id is not None:
            stmt = stmt.where(SupplierProductAliasModel.supplier_id == supplier_id)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [
            SupplierProductAlias(
                id=m.id,
                tenant_id=str(m.tenant_id),
                supplier_id=m.supplier_id,
                raw_vendor_product_name=m.raw_vendor_product_name,
                catalog_item_id=m.catalog_item_id,
                default_packaging_factor=m.default_packaging_factor,
                default_inventory_unit=m.default_inventory_unit,
                is_verified=m.is_verified,
                times_used=m.times_used,
                last_matched_at=m.last_matched_at,
                created_at=m.created_at,
            )
            for m in models
        ]
