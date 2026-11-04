"""
oppytec-backend/src/modules/invoices/domain/entities.py
Entidades y Agregados puros de dominio para el Módulo de Facturas y Contabilidad (Clean Architecture).
Aislados de SQLAlchemy, Pydantic y frameworks externos.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from src.modules.invoices.domain.exceptions import (
    InvoiceDomainError,
    InvoiceTotalMismatchError,
    InvalidInvoiceStatusTransitionError,
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

DECIMAL_ZERO = Decimal("0.0000")
DECIMAL_QUANT_4 = Decimal("0.0001")
TOLERANCE_CLP = Decimal("1.0000")


@dataclass
class InvoiceAuditFlag:
    """
    Entidad que representa una advertencia o hallazgo de auditoría tributaria/matemática
    detectada durante el análisis de la factura.
    """

    severity: AuditSeverity | str
    rule_code: AuditRuleCode | str
    message: str
    id: UUID = field(default_factory=uuid4)
    invoice_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, str | None]:
        """Serializa el flag para almacenamiento o presentación."""
        sev_val = self.severity.value if isinstance(self.severity, AuditSeverity) else str(self.severity)
        rule_val = self.rule_code.value if isinstance(self.rule_code, AuditRuleCode) else str(self.rule_code)
        return {
            "id": str(self.id) if self.id else None,
            "invoice_id": str(self.invoice_id) if self.invoice_id else None,
            "severity": sev_val,
            "rule_code": rule_val,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class InvoiceLineItem:
    """
    Línea individual de detalle de una factura.
    Incluye lógica de desacoplamiento de empaque mayorista a existencias físicas de cocina.
    """

    raw_description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    id: UUID = field(default_factory=uuid4)
    invoice_id: UUID | None = None
    line_number: int = 1
    unit: str = "unidad"
    vat_rate: Decimal = Decimal("19.00")
    matched_catalog_item_id: UUID | None = None
    match_status: MatchStatus = MatchStatus.UNMATCHED
    suggested_catalog_item_id: UUID | None = None
    match_confidence: Decimal = Decimal("0.0000")
    packaging_description: str | None = None
    packaging_factor: Decimal = Decimal("1.0000")
    calculated_stock_qty: Decimal = Decimal("0.0000")
    inventory_unit: str = "unidad"
    inventory_unit_cost: Decimal = Decimal("0.0000")
    target_bodega_id: int | None = None

    def __post_init__(self) -> None:
        """Garantiza la normalización inicial de cantidades y costos de inventario."""
        if self.calculated_stock_qty == DECIMAL_ZERO and self.quantity > DECIMAL_ZERO:
            self.calculate_stock_and_unit_cost()

    def calculate_stock_and_unit_cost(self) -> tuple[Decimal, Decimal]:
        """
        Ejecuta la conversión de empaque:
        - stock_fisico = quantity * packaging_factor
        - inventory_unit_cost = line_total / stock_fisico (evitando división por 0)
        """
        stock_fisico = (self.quantity * self.packaging_factor).quantize(
            DECIMAL_QUANT_4, rounding=ROUND_HALF_UP
        )
        self.calculated_stock_qty = stock_fisico

        if stock_fisico > DECIMAL_ZERO:
            self.inventory_unit_cost = (self.line_total / stock_fisico).quantize(
                DECIMAL_QUANT_4, rounding=ROUND_HALF_UP
            )
        else:
            self.inventory_unit_cost = DECIMAL_ZERO

        return (self.calculated_stock_qty, self.inventory_unit_cost)

    def apply_packaging(
        self,
        factor: Decimal | PackagingFactor,
        inventory_unit: str | None = None,
        description: str | None = None,
    ) -> None:
        """Actualiza el factor de empaque y recalcula el stock físico y costo unitario."""
        if isinstance(factor, PackagingFactor):
            self.packaging_factor = factor.value
            self.inventory_unit = factor.inventory_unit
        else:
            self.packaging_factor = factor

        if inventory_unit:
            self.inventory_unit = inventory_unit
        if description:
            self.packaging_description = description

        self.calculate_stock_and_unit_cost()


@dataclass
class SupplierProductAlias:
    """
    Entidad que modela el mapeo de memoria semántica entre el nombre de producto
    que usa el proveedor en su factura y el producto registrado en el catálogo maestro.
    """

    supplier_id: UUID | None
    raw_vendor_product_name: str
    catalog_item_id: UUID
    id: UUID = field(default_factory=uuid4)
    tenant_id: str | None = None
    default_packaging_factor: Decimal = Decimal("1.0000")
    default_inventory_unit: str = "unidad"
    is_verified: bool = False
    times_used: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_matched_at: datetime | None = None

    @staticmethod
    def normalize_name(text: str) -> str:
        """Normaliza una cadena a minúsculas, sin tildes ni caracteres redundantes para búsqueda difusa."""
        if not text:
            return ""
        norm = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
        return " ".join(norm.strip().lower().split())

    @property
    def normalized_vendor_product_name(self) -> str:
        """Nombre normalizado del producto del proveedor."""
        return self.normalize_name(self.raw_vendor_product_name)

    def record_usage(self) -> None:
        """Incrementa el contador de uso y actualiza la fecha de coincidencia."""
        self.times_used += 1
        self.last_matched_at = datetime.now(timezone.utc)


@dataclass
class Invoice:
    """
    Agregado Raíz del Módulo de Facturas y Contabilidad.
    Controla el ciclo de vida del documento, la auditoría tributaria y la reconciliación con inventario.
    """

    vendor_name: str
    vendor_tax_id: TaxId | str
    invoice_number: str
    file_path: str = ""
    file_name: str = ""
    file_type: str = "pdf"
    id: UUID = field(default_factory=uuid4)
    tenant_id: str | None = None
    vendor_address: str | None = None
    invoice_date: date | datetime | None = None
    due_date: date | datetime | None = None
    currency: str = "CLP"
    exchange_rate: Decimal = Decimal("1.0000")
    net_amount: Decimal = Decimal("0.0000")
    tax_amount: Decimal = Decimal("0.0000")
    total_amount: Decimal = Decimal("0.0000")
    dte_type: DTEType = DTEType.FACTURA_ELECTRONICA
    status: InvoiceStatus = InvoiceStatus.PENDING
    confidence_score: Decimal = Decimal("1.0000")
    audit_flags: list[InvoiceAuditFlag] = field(default_factory=list)
    lines: list[InvoiceLineItem] = field(default_factory=list)
    gemini_tokens_used: int = 0
    gemini_cost_usd: Decimal = Decimal("0.000000")
    is_confirmed_to_inventory: bool = False
    confirmed_bodega_id: int | UUID | None = None
    confirmed_at: datetime | None = None
    confirmed_by_user_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Normalización defensiva de tipos de TaxId y DTEType."""
        if isinstance(self.vendor_tax_id, str) and self.vendor_tax_id:
            try:
                self.vendor_tax_id = TaxId(self.vendor_tax_id)
            except Exception:
                pass

        if not isinstance(self.dte_type, DTEType):
            try:
                self.dte_type = DTEType.from_code(self.dte_type)
            except Exception:
                pass

    def validate_accounting_invariants(self, strict: bool = True) -> bool:
        """
        Verifica la invariante contable fundamental:
        abs(total_amount - (net_amount + tax_amount)) <= 1.0 CLP (tolerancia por redondeo).
        Si la discrepancia excede el umbral:
        - Si strict=True, lanza InvoiceTotalMismatchError.
        - Registra un flag de auditoría TOTAL_NET_MISMATCH.
        """
        expected_total = self.net_amount + self.tax_amount
        discrepancy = abs(self.total_amount - expected_total)

        if discrepancy > TOLERANCE_CLP:
            msg = (
                f"Discrepancia contable detectada: Total ({self.total_amount}) != "
                f"Neto ({self.net_amount}) + IVA ({self.tax_amount}). "
                f"Descalce de {discrepancy} {self.currency} excede la tolerancia permitida ({TOLERANCE_CLP})."
            )
            self.add_audit_flag(
                severity=AuditSeverity.CRITICAL,
                rule_code=AuditRuleCode.TOTAL_NET_MISMATCH,
                message=msg,
            )
            if strict:
                raise InvoiceTotalMismatchError(
                    msg,
                    context={
                        "total": str(self.total_amount),
                        "net": str(self.net_amount),
                        "tax": str(self.tax_amount),
                        "discrepancy": str(discrepancy),
                    },
                )
            return False

        return True

    def validate_vat_19_rate(self, tolerance: Decimal = TOLERANCE_CLP) -> bool:
        """
        Verifica que para DTE afecto (Factura Electrónica 33), el IVA corresponda al 19% del neto.
        """
        if self.dte_type.requires_vat and self.net_amount > DECIMAL_ZERO:
            expected_vat = (self.net_amount * Decimal("0.19")).quantize(
                DECIMAL_QUANT_4, rounding=ROUND_HALF_UP
            )
            vat_diff = abs(self.tax_amount - expected_vat)
            if vat_diff > tolerance:
                self.add_audit_flag(
                    severity=AuditSeverity.WARNING,
                    rule_code=AuditRuleCode.VAT_19_DISCREPANCY,
                    message=(
                        f"Discrepancia de IVA 19%: Declarado ({self.tax_amount}) vs "
                        f"Teórico ({expected_vat}). Diferencia: {vat_diff}."
                    ),
                )
                return False
        return True

    def add_line(self, line: InvoiceLineItem) -> None:
        """Agrega una línea de detalle asegurando la correlación de invoice_id."""
        line.invoice_id = self.id
        self.lines.append(line)

    def add_audit_flag(
        self,
        severity: AuditSeverity | str,
        rule_code: AuditRuleCode | str,
        message: str,
    ) -> InvoiceAuditFlag:
        """Registra un flag de auditoría asociado al agregado."""
        flag = InvoiceAuditFlag(
            invoice_id=self.id,
            severity=severity,
            rule_code=rule_code,
            message=message,
        )
        self.audit_flags.append(flag)
        return flag

    def recalculate_totals_from_lines(self) -> None:
        """Recalcula neto, IVA y total sumando los totales de cada línea."""
        sum_net = sum((line.line_total for line in self.lines), DECIMAL_ZERO)
        self.net_amount = sum_net.quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

        if self.dte_type.requires_vat:
            self.tax_amount = (self.net_amount * Decimal("0.19")).quantize(
                DECIMAL_QUANT_4, rounding=ROUND_HALF_UP
            )
        else:
            self.tax_amount = DECIMAL_ZERO

        self.total_amount = (self.net_amount + self.tax_amount).quantize(
            DECIMAL_QUANT_4, rounding=ROUND_HALF_UP
        )
        self.updated_at = datetime.now(timezone.utc)

    def confirm_stock_ingestion(self, bodega_id: int | UUID, user_id: int | None = None) -> None:
        """
        Marca la factura como ingresada en existencias físicas tras la revisión.
        Actualiza el estado a CONFIRMED_STOCK y fija la bodega de destino.
        """
        if self.status == InvoiceStatus.CONFIRMED_STOCK:
            raise InvalidInvoiceStatusTransitionError(
                "Invoice stock has already been confirmed and ingested into inventory."
            )

        self.is_confirmed_to_inventory = True
        self.confirmed_bodega_id = bodega_id
        self.confirmed_by_user_id = user_id
        self.confirmed_at = datetime.now(timezone.utc)
        self.status = InvoiceStatus.CONFIRMED_STOCK
        self.updated_at = datetime.now(timezone.utc)
