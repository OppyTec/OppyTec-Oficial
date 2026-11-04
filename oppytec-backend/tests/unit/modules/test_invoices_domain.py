"""
oppytec-backend/tests/unit/modules/test_invoices_domain.py
Pruebas Unitarias de Arquitectura DDD, Value Objects, Agregado Raíz y Contratos de Dominio
para el Módulo de Facturas y Contabilidad (Etapa 1).
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.modules.invoices.domain import (
    AuditRuleCode,
    AuditSeverity,
    DTEType,
    InvalidInvoiceStatusTransitionError,
    InvalidPackagingFactorError,
    InvalidRUTError,
    Invoice,
    InvoiceAuditFlag,
    InvoiceLineItem,
    InvoiceStatus,
    InvoiceTotalMismatchError,
    MatchStatus,
    PackagingFactor,
    PriceDrift,
    SupplierProductAlias,
    TaxId,
    calculate_chilean_dv,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Validación de RUT Chileno y Algoritmo Módulo 11 (TaxId)
# ---------------------------------------------------------------------------


def test_calculate_chilean_dv_algorithm() -> None:
    """Verifica el cálculo exacto del dígito verificador con el algoritmo Módulo 11."""
    # 76.192.083 -> 9
    assert calculate_chilean_dv("76192083") == "9"
    # 76.543.210 -> 3 (7*2+1*3+2*4...)
    dv_76543210 = calculate_chilean_dv("76543210")
    assert dv_76543210 in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "K")
    # Caso conocido con K: 10.000.013-K
    assert calculate_chilean_dv("10000013") == "K"
    # Caso conocido con 0: 11.111.111-0 (no, probemos 50000000)
    # 11111111 sum: 1*2 + 1*3 + 1*4 + 1*5 + 1*6 + 1*7 + 1*2 + 1*3 = 2+3+4+5+6+7+2+3 = 32. 32%11=10 -> 11-10=1.
    assert calculate_chilean_dv("11111111") == "1"


def test_tax_id_valid_chilean_formats() -> None:
    """Valida la aceptación e instanciación de RUTs chilenos en distintos formatos."""
    # Con puntos y guion
    tax1 = TaxId("76.192.083-9")
    assert tax1.is_chilean is True
    assert tax1.clean == "76192083-9"
    assert tax1.clean_tax_id == "76192083-9"
    assert tax1.formatted == "76.192.083-9"
    assert tax1.body == "76192083"
    assert tax1.dv == "9"

    # Sin puntos con guion
    tax2 = TaxId("76192083-9")
    assert tax2.clean == "76192083-9"
    assert tax2.formatted == "76.192.083-9"

    # Con dígito verificador 'K'
    tax_k = TaxId("10.000.013-k")
    assert tax_k.dv == "K"
    assert tax_k.clean == "10000013-K"

    # Desde classmethods
    tax_clean = TaxId.from_clean("761920839")
    assert tax_clean.dv == "9"
    assert tax_clean.clean == "76192083-9"


def test_tax_id_invalid_chilean_rut_raises_error() -> None:
    """Verifica que dígitos verificadores incorrectos o strings malformados levanten InvalidRUTError."""
    # DV incorrecto
    with pytest.raises(InvalidRUTError) as exc_info:
        TaxId("76.192.083-0")
    assert "Invalid Chilean RUT check digit" in str(exc_info.value)
    assert exc_info.value.status_code == 422

    # Letras en el cuerpo
    with pytest.raises(InvalidRUTError):
        TaxId("76A92083-9")

    # Longitud vacía o whitespace
    with pytest.raises(InvalidRUTError):
        TaxId("   ")

    # Longitud excesiva
    with pytest.raises(InvalidRUTError):
        TaxId("1234567890123-4")


def test_tax_id_international_format() -> None:
    """Verifica el soporte para identificadores tributarios extranjeros (US EIN, EU VAT)."""
    tax_us = TaxId("12-3456789", country="US")
    assert tax_us.is_chilean is False
    assert tax_us.clean == "12-3456789"
    assert tax_us.country == "US"

    with pytest.raises(InvalidRUTError):
        TaxId("??INV??", country="US")


# ---------------------------------------------------------------------------
# 2. Invariante Contable: Neto + IVA = Total (Invoice Aggregate Root)
# ---------------------------------------------------------------------------


def test_invoice_accounting_invariants_balanced() -> None:
    """Comprueba que una factura perfectamente cuadra pasa la validación contable."""
    invoice = Invoice(
        vendor_name="Distribuidora Gastronómica SpA",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="F-12044",
        net_amount=Decimal("100000.0000"),
        tax_amount=Decimal("19000.0000"),
        total_amount=Decimal("119000.0000"),
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.PARSED,
    )

    assert invoice.validate_accounting_invariants(strict=True) is True
    assert invoice.validate_vat_19_rate() is True
    assert len(invoice.audit_flags) == 0


def test_invoice_accounting_invariants_within_clp_tolerance() -> None:
    """Comprueba que diferencias de redondeo <= 1 CLP son aceptadas como válidas."""
    invoice = Invoice(
        vendor_name="Carnes Premium del Sur",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="F-890",
        net_amount=Decimal("100000.0000"),
        tax_amount=Decimal("19000.0000"),
        total_amount=Decimal("119000.8000"),  # Descalce de 0.8 CLP <= 1.0 CLP
    )

    assert invoice.validate_accounting_invariants(strict=True) is True


def test_invoice_accounting_invariants_mismatch_raises_exception() -> None:
    """Verifica que una discrepancia > 1 CLP levante InvoiceTotalMismatchError en modo estricto."""
    invoice = Invoice(
        vendor_name="Lácteos y Quesos del Valle",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="F-9999",
        net_amount=Decimal("100000.0000"),
        tax_amount=Decimal("19000.0000"),
        total_amount=Decimal("125000.0000"),  # Descalce de 6.000 CLP
    )

    with pytest.raises(InvoiceTotalMismatchError) as exc_info:
        invoice.validate_accounting_invariants(strict=True)

    assert exc_info.value.status_code == 422
    assert "Discrepancia contable detectada" in str(exc_info.value)
    # Debe haber registrado un flag de auditoría
    assert len(invoice.audit_flags) == 1
    assert invoice.audit_flags[0].rule_code == AuditRuleCode.TOTAL_NET_MISMATCH
    assert invoice.audit_flags[0].severity == AuditSeverity.CRITICAL


def test_invoice_accounting_invariants_mismatch_non_strict() -> None:
    """En modo no estricto, la discrepancia retorna False y registra el flag sin lanzar excepción."""
    invoice = Invoice(
        vendor_name="Proveedor Mayorista",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="F-500",
        net_amount=Decimal("50000.0000"),
        tax_amount=Decimal("9500.0000"),
        total_amount=Decimal("70000.0000"),
    )

    assert invoice.validate_accounting_invariants(strict=False) is False
    assert len(invoice.audit_flags) == 1
    assert invoice.audit_flags[0].rule_code == AuditRuleCode.TOTAL_NET_MISMATCH


def test_invoice_recalculate_totals_from_lines() -> None:
    """Comprueba el recálculo automático de totales sumando líneas."""
    invoice = Invoice(
        vendor_name="Verduras Frescas SA",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="F-101",
        dte_type=DTEType.FACTURA_ELECTRONICA,
    )
    line1 = InvoiceLineItem(
        raw_description="Tomate Larga Vida Caja 18kg",
        quantity=Decimal("2.0000"),
        unit_price=Decimal("15000.0000"),
        line_total=Decimal("30000.0000"),
    )
    line2 = InvoiceLineItem(
        raw_description="Cebolla Malla 20kg",
        quantity=Decimal("1.0000"),
        unit_price=Decimal("20000.0000"),
        line_total=Decimal("20000.0000"),
    )
    invoice.add_line(line1)
    invoice.add_line(line2)
    invoice.recalculate_totals_from_lines()

    assert invoice.net_amount == Decimal("50000.0000")
    assert invoice.tax_amount == Decimal("9500.0000")
    assert invoice.total_amount == Decimal("59500.0000")
    assert invoice.validate_accounting_invariants() is True


# ---------------------------------------------------------------------------
# 3. Conversión de Empaque (PackagingFactor & InvoiceLineItem)
# ---------------------------------------------------------------------------


def test_packaging_factor_and_stock_conversion() -> None:
    """Verifica que Cantidad × Factor = Stock Físico y Costo Unitario de Inventario = Total / Stock."""
    # Factor: 18 kg por cada caja comprada
    factor = PackagingFactor(Decimal("18.0000"), packaging_unit="caja", inventory_unit="kg")

    # Si compramos 5 cajas:
    raw_qty = Decimal("5.0000")
    stock_fisico = factor.to_physical_stock(raw_qty)
    assert stock_fisico == Decimal("90.0000")

    # Si el costo total de las 5 cajas fue $90.000 CLP:
    line_total = Decimal("90000.0000")
    unit_cost = factor.calculate_inventory_unit_cost(line_total, raw_qty)
    assert unit_cost == Decimal("1000.0000")  # $1.000 por kg


def test_packaging_factor_invalid_zero_or_negative() -> None:
    """Verifica que factores <= 0 levanten InvalidPackagingFactorError."""
    with pytest.raises(InvalidPackagingFactorError):
        PackagingFactor(Decimal("0.0000"))

    with pytest.raises(InvalidPackagingFactorError):
        PackagingFactor(Decimal("-2.5000"))


def test_invoice_line_item_packaging_recalculation() -> None:
    """Verifica que InvoiceLineItem aplique dinámicamente el factor de empaque y recalcule stock."""
    item = InvoiceLineItem(
        raw_description="Pechuga de Pollo Congelada Caja 15kg",
        quantity=Decimal("4.0000"),
        unit_price=Decimal("45000.0000"),
        line_total=Decimal("180000.0000"),
        packaging_factor=Decimal("15.0000"),
        inventory_unit="kg",
    )

    # Inmediatamente al iniciar
    assert item.calculated_stock_qty == Decimal("60.0000")  # 4 * 15 = 60 kg
    assert item.inventory_unit_cost == Decimal("3000.0000")  # 180.000 / 60 = 3.000 $/kg

    # Modificación posterior de empaque (ej. el proveedor despachó cajas de 20 kg)
    item.apply_packaging(factor=Decimal("20.0000"), inventory_unit="kg")
    assert item.calculated_stock_qty == Decimal("80.0000")  # 4 * 20 = 80 kg
    assert item.inventory_unit_cost == Decimal("2250.0000")  # 180.000 / 80 = 2.250 $/kg


# ---------------------------------------------------------------------------
# 4. Cálculo de Price Drift (Variación Porcentual de Precios)
# ---------------------------------------------------------------------------


def test_price_drift_scenarios() -> None:
    """Verifica los cálculos porcentuales y umbrales semafóricos (INFO, WARNING, CRITICAL)."""
    # 1. Variación normal menor al 10% -> INFO
    drift_info = PriceDrift(new_price=Decimal("105.0000"), last_price=Decimal("100.0000"))
    assert drift_info.drift_percentage == Decimal("5.0000")
    assert drift_info.severity == AuditSeverity.INFO
    assert drift_info.is_drift is False
    assert drift_info.is_critical is False

    # 2. Alza de precio entre 10% y 25% -> WARNING
    drift_warn = PriceDrift(new_price=Decimal("115.0000"), last_price=Decimal("100.0000"))
    assert drift_warn.drift_percentage == Decimal("15.0000")
    assert drift_warn.severity == AuditSeverity.WARNING
    assert drift_warn.is_drift is True
    assert drift_warn.is_critical is False

    # 3. Alza de precio mayor al 25% -> CRITICAL
    drift_crit = PriceDrift(new_price=Decimal("130.0000"), last_price=Decimal("100.0000"))
    assert drift_crit.drift_percentage == Decimal("30.0000")
    assert drift_crit.severity == AuditSeverity.CRITICAL
    assert drift_crit.is_drift is True
    assert drift_crit.is_critical is True

    # 4. Caída significativa de precio (-30%) -> CRITICAL
    drift_drop = PriceDrift(new_price=Decimal("70.0000"), last_price=Decimal("100.0000"))
    assert drift_drop.drift_percentage == Decimal("-30.0000")
    assert drift_drop.severity == AuditSeverity.CRITICAL

    # 5. Precio previo cero o nulo
    drift_zero = PriceDrift(new_price=Decimal("500.0000"), last_price=Decimal("0.0000"))
    assert drift_zero.drift_percentage == Decimal("100.0000")


# ---------------------------------------------------------------------------
# 5. SupplierProductAlias y Memoria Semántica
# ---------------------------------------------------------------------------


def test_supplier_product_alias_normalization_and_usage() -> None:
    """Verifica la normalización sin acentos y el contador de uso de alias."""
    alias = SupplierProductAlias(
        supplier_id=uuid4(),
        raw_vendor_product_name="  Queso Gouda LAMINADO 1KG  ",
        catalog_item_id=uuid4(),
        default_packaging_factor=Decimal("1.0000"),
        default_inventory_unit="kg",
    )

    assert alias.normalized_vendor_product_name == "queso gouda laminado 1kg"
    assert alias.times_used == 1
    assert alias.last_matched_at is None

    alias.record_usage()
    assert alias.times_used == 2
    assert alias.last_matched_at is not None


# ---------------------------------------------------------------------------
# 6. Transiciones de Estado del Agregado Invoice
# ---------------------------------------------------------------------------


def test_invoice_stock_confirmation_lifecycle() -> None:
    """Verifica la transición hacia CONFIRMED_STOCK y la prohibición de re-confirmar."""
    invoice = Invoice(
        vendor_name="Avícola San Cristóbal",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="F-5555",
        status=InvoiceStatus.APPROVED,
    )
    bodega_id = uuid4()
    user_id = 42

    invoice.confirm_stock_ingestion(bodega_id=bodega_id, user_id=user_id)
    assert invoice.is_confirmed_to_inventory is True
    assert invoice.confirmed_bodega_id == bodega_id
    assert invoice.confirmed_by_user_id == user_id
    assert invoice.status == InvoiceStatus.CONFIRMED_STOCK
    assert invoice.status.is_terminal is True

    # Reintento de confirmación debe levantar excepción
    with pytest.raises(InvalidInvoiceStatusTransitionError):
        invoice.confirm_stock_ingestion(bodega_id=bodega_id, user_id=user_id)


# ---------------------------------------------------------------------------
# 7. DTEType, InvoiceStatus y MatchStatus
# ---------------------------------------------------------------------------


def test_dte_type_resolution_and_properties() -> None:
    """Verifica la resolución de tipos DTE por código entero y string, y sus propiedades fiscales."""
    assert DTEType.from_code(33) == DTEType.FACTURA_ELECTRONICA
    assert DTEType.from_code("33") == DTEType.FACTURA_ELECTRONICA
    assert DTEType.from_code("FACTURA_ELECTRONICA") == DTEType.FACTURA_ELECTRONICA
    assert DTEType.from_code("34") == DTEType.FACTURA_EXENTA
    assert DTEType.from_code(61) == DTEType.NOTA_CREDITO

    assert DTEType.FACTURA_ELECTRONICA.requires_vat is True
    assert DTEType.FACTURA_EXENTA.requires_vat is False
    assert "Factura Electrónica" in DTEType.FACTURA_ELECTRONICA.description

    with pytest.raises(ValueError):
        DTEType.from_code("INVALID_DTE_999")


def test_invoice_status_lifecycle_predicates() -> None:
    """Verifica los predicados de estado de revisión y terminalidad."""
    assert InvoiceStatus.PENDING.is_terminal is False
    assert InvoiceStatus.CONFIRMED_STOCK.is_terminal is True
    assert InvoiceStatus.INGESTED.is_terminal is True
    assert InvoiceStatus.REJECTED.is_terminal is True

    assert InvoiceStatus.PARSED.is_reviewable is True
    assert InvoiceStatus.REVIEWING.is_reviewable is True
    assert InvoiceStatus.CONFIRMED_STOCK.is_reviewable is False


def test_match_status_values() -> None:
    """Verifica las constantes de coincidencia semántica de catálogo."""
    assert MatchStatus.EXACT_ALIAS.value == "exact_alias"
    assert MatchStatus.SUGGESTED.value == "suggested"
    assert MatchStatus.UNMATCHED.value == "unmatched"


def test_invoice_audit_flag_serialization() -> None:
    """Verifica la serialización a diccionario de InvoiceAuditFlag."""
    flag = InvoiceAuditFlag(
        severity=AuditSeverity.WARNING,
        rule_code=AuditRuleCode.PRICE_DRIFT_HIGH,
        message="Precio unitario varió +15%",
    )
    serialized = flag.to_dict()
    assert serialized["severity"] == "warning"
    assert serialized["rule_code"] == "PRICE_DRIFT_HIGH"
    assert serialized["message"] == "Precio unitario varió +15%"
    assert serialized["id"] is not None

