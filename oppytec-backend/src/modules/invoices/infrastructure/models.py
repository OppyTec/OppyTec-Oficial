"""
oppytec-backend/src/modules/invoices/infrastructure/models.py
Modelos de Persistencia SQLAlchemy 2.0 Async para el Módulo de Facturas y Contabilidad (`TenantBase`).
Esquemas dinámicos tenant_* con tipos exactos Numeric(14, 4) y Numeric(12, 2), UUIDs y trazabilidad completa.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models_base import AuditTimestampsMixin, TenantBase

# Alias canónico de Base compatible con la arquitectura del backend
Base = TenantBase


class InvoiceModel(TenantBase):
    """
    Modelo ORM de Facturas Tributarias y DTE (`invoices`).
    Almacena metadatos del documento, montos tributarios, resultado de extracción Gemini y estado de ingesta.
    """

    __tablename__ = "invoices"
    __table_args__ = (
        Index(
            "ix_invoices_vendor_name_trgm",
            "vendor_name",
            postgresql_using="gin",
            postgresql_ops={"vendor_name": "gin_trgm_ops"},
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    vendor_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    vendor_tax_id: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        default=None,
        index=True,
    )
    vendor_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    invoice_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        index=True,
    )
    invoice_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="CLP",
    )
    exchange_rate: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("1.0000"),
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    dte_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=33,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True,
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        default=None,
    )
    gemini_tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    gemini_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=Decimal("0.000000"),
    )
    is_stock_ingested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relaciones en cascada
    lines: Mapped[List[InvoiceLineItemModel]] = relationship(
        "InvoiceLineItemModel",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_flags: Mapped[List[InvoiceAuditFlagModel]] = relationship(
        "InvoiceAuditFlagModel",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("currency", "CLP")
        kwargs.setdefault("exchange_rate", Decimal("1.0000"))
        kwargs.setdefault("net_amount", Decimal("0.0000"))
        kwargs.setdefault("tax_amount", Decimal("0.0000"))
        kwargs.setdefault("total_amount", Decimal("0.0000"))
        kwargs.setdefault("dte_type", 33)
        kwargs.setdefault("status", "PENDING")
        kwargs.setdefault("gemini_tokens_used", 0)
        kwargs.setdefault("gemini_cost_usd", Decimal("0.000000"))
        kwargs.setdefault("is_stock_ingested", False)
        kwargs.setdefault("created_at", datetime.now(UTC))
        kwargs.setdefault("updated_at", datetime.now(UTC))
        super().__init__(**kwargs)


class InvoiceLineItemModel(TenantBase):
    """
    Modelo ORM de Líneas de Detalle de Factura (`invoice_lines`).
    Desacopla empaque mayorista a existencias físicas de cocina con referencias a catalog_items y bodegas.
    """

    __tablename__ = "invoice_lines"
    __table_args__ = (
        Index(
            "ix_invoice_lines_raw_description_trgm",
            "raw_description",
            postgresql_using="gin",
            postgresql_ops={"raw_description": "gin_trgm_ops"},
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    raw_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("1.0000"),
    )
    unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="un",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("19.00"),
    )
    matched_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )
    match_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="UNMATCHED",
    )
    suggested_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        default=None,
    )
    match_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        default=None,
    )
    packaging_description: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )
    packaging_factor: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("1.0000"),
    )
    calculated_stock_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    inventory_unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="un",
    )
    inventory_unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    target_bodega_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relación inversa
    invoice: Mapped[InvoiceModel] = relationship(
        "InvoiceModel",
        back_populates="lines",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("line_number", 1)
        kwargs.setdefault("quantity", Decimal("1.0000"))
        kwargs.setdefault("unit", "un")
        kwargs.setdefault("unit_price", Decimal("0.0000"))
        kwargs.setdefault("line_total", Decimal("0.0000"))
        kwargs.setdefault("vat_rate", Decimal("19.00"))
        kwargs.setdefault("match_status", "UNMATCHED")
        kwargs.setdefault("packaging_factor", Decimal("1.0000"))
        kwargs.setdefault("calculated_stock_qty", Decimal("0.0000"))
        kwargs.setdefault("inventory_unit", "un")
        kwargs.setdefault("inventory_unit_cost", Decimal("0.0000"))
        kwargs.setdefault("created_at", datetime.now(UTC))
        super().__init__(**kwargs)


class SupplierProductAliasModel(TenantBase):
    """
    Modelo ORM de Alias de Proveedores (`supplier_product_aliases`).
    Memoria de aprendizaje asociativa entre nombres de proveedor en factura y catálogo interno.
    """

    __tablename__ = "supplier_product_aliases"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "supplier_id",
            "raw_vendor_product_name",
            name="uq_supplier_product_aliases_tenant_supplier_name",
        ),
        Index(
            "ix_supplier_product_aliases_vendor_name_trgm",
            "raw_vendor_product_name",
            postgresql_using="gin",
            postgresql_ops={"raw_vendor_product_name": "gin_trgm_ops"},
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
        index=True,
    )
    raw_vendor_product_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    default_packaging_factor: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("1.0000"),
    )
    default_inventory_unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="un",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    times_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    last_matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("default_packaging_factor", Decimal("1.0000"))
        kwargs.setdefault("default_inventory_unit", "un")
        kwargs.setdefault("is_verified", True)
        kwargs.setdefault("times_used", 1)
        kwargs.setdefault("last_matched_at", datetime.now(UTC))
        kwargs.setdefault("created_at", datetime.now(UTC))
        kwargs.setdefault("updated_at", datetime.now(UTC))
        super().__init__(**kwargs)


class InvoiceAuditFlagModel(TenantBase):
    """
    Modelo ORM de Flags de Auditoría Tributaria y Matemática (`invoice_audit_flags`).
    Registra alertas de discrepancias, descalces de IVA y advertencias normativas.
    """

    __tablename__ = "invoice_audit_flags"
    __table_args__ = (
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    rule_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relación inversa
    invoice: Mapped[InvoiceModel] = relationship(
        "InvoiceModel",
        back_populates="audit_flags",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("created_at", datetime.now(UTC))
        super().__init__(**kwargs)
