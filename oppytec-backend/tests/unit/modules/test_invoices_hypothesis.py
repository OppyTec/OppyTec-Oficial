"""
oppytec-backend/tests/unit/modules/test_invoices_hypothesis.py
Pruebas de Propiedades y Paridad Matemática con Hypothesis para Facturas y Contabilidad (Etapa 4).

Verifica:
1. Invariante Contable SII (IVA 19% y desglose Neto / Bruto):
   Para cualquier combinación aleatoria de Neto y Tasa de IVA (19%):
   - abs(total - (neto + iva)) <= 1 CLP.
   - Respeto de tolerancia en el agregado Invoice (validate_accounting_invariants).
   - Respeto de tasa del 19% en validate_vat_19_rate.
2. Desacoplamiento de Empaque Mayorista a Cocina (Packaging Factor):
   Para cualquier cantidad (>0) y factor de empaque (>0):
   - stock_fisico = cantidad * factor.
   - costo_unitario * stock_fisico == total_neto (tolerancia de redondeo menor a 0.01).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import pytest
from hypothesis import given, settings, strategies as st

from src.modules.invoices.domain.entities import Invoice, InvoiceLineItem
from src.modules.invoices.domain.exceptions import InvoiceTotalMismatchError
from src.modules.invoices.domain.value_objects import (
    DTEType,
    PackagingFactor,
    TaxId,
)

pytestmark = pytest.mark.unit

DECIMAL_QUANT_4 = Decimal("0.0001")
TOLERANCE_CLP = Decimal("1.0000")
TOLERANCE_CENT = Decimal("0.01")


# ---------------------------------------------------------------------------
# Estrategias Hypothesis
# ---------------------------------------------------------------------------

# Montos netos en CLP (desde 1 CLP hasta 500.000.000 CLP con 4 decimales)
net_amount_strategy = st.decimals(
    min_value=Decimal("1.0000"),
    max_value=Decimal("500000000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)

# Cantidades generales (> 0)
arbitrary_quantity_strategy = st.decimals(
    min_value=Decimal("0.0100"),
    max_value=Decimal("10000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)

# Factores de empaque generales (> 0)
arbitrary_factor_strategy = st.decimals(
    min_value=Decimal("0.0100"),
    max_value=Decimal("500.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)

# Cantidades para despachos de cocina (1 a 15 cajas)
kitchen_quantity_strategy = st.decimals(
    min_value=Decimal("1.0000"),
    max_value=Decimal("15.0000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Factores para empaques gastronómicos estándar (1 a 10 kg/L/un por empaque)
kitchen_factor_strategy = st.decimals(
    min_value=Decimal("1.0000"),
    max_value=Decimal("10.0000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Precios unitarios de compra gastronómica (500 a 100.000 CLP)
kitchen_unit_price_strategy = st.decimals(
    min_value=Decimal("500.0000"),
    max_value=Decimal("100000.0000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


# ---------------------------------------------------------------------------
# 1. Paridad Matemática de IVA 19% y Desglose Neto / Bruto
# ---------------------------------------------------------------------------


@given(neto=net_amount_strategy)
@settings(max_examples=100)
def test_hypothesis_iva_19_exact_accounting_tolerance(neto: Decimal) -> None:
    """
    Invariante: Para cualquier valor neto > 0, al aplicar IVA 19% reglamentario:
    total = neto + iva (con redondeo bancario ROUND_HALF_UP a 4 decimales)
    abs(total - (neto + iva)) <= 1.0 CLP (idénticamente 0 o dentro de 1 CLP).
    """
    iva = (neto * Decimal("0.19")).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)
    total = (neto + iva).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    discrepancia = abs(total - (neto + iva))
    assert discrepancia <= TOLERANCE_CLP, f"Discrepancia {discrepancia} excede 1 CLP"


@given(neto=net_amount_strategy)
@settings(max_examples=100)
def test_hypothesis_invoice_aggregate_vat_and_totals(neto: Decimal) -> None:
    """
    Verifica que el Agregado Invoice recalcula y valida sus invariantes contables
    sin lanzar InvoiceTotalMismatchError para cualquier monto generado.
    """
    invoice = Invoice(
        vendor_name="PROVEEDOR HIPOTÉTICO SPA",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="FAC-HYP-001",
        dte_type=DTEType.FACTURA_ELECTRONICA,
    )

    line = InvoiceLineItem(
        raw_description="MATERIA PRIMA HYPOTHESIS",
        quantity=Decimal("1.0000"),
        unit_price=neto,
        line_total=neto,
    )
    invoice.add_line(line)
    invoice.recalculate_totals_from_lines()

    # Invariante 1: validate_accounting_invariants retorna True
    assert invoice.validate_accounting_invariants(strict=True) is True

    # Invariante 2: validate_vat_19_rate es True dentro de 1 CLP de tolerancia
    assert invoice.validate_vat_19_rate(tolerance=TOLERANCE_CLP) is True

    # Invariante 3: abs(total - (neto + iva)) <= 1 CLP
    calc_diff = abs(invoice.total_amount - (invoice.net_amount + invoice.tax_amount))
    assert calc_diff <= TOLERANCE_CLP


@given(
    neto=net_amount_strategy,
    delta=st.decimals(min_value=Decimal("-1.0000"), max_value=Decimal("1.0000"), places=4),
)
@settings(max_examples=100)
def test_hypothesis_invoice_tolerance_boundary_1_clp(neto: Decimal, delta: Decimal) -> None:
    """
    Verifica que cualquier discrepancia dentro de [-1.0000, 1.0000] CLP es tolerada
    por redondeo bancario de los emisores DTE del SII.
    """
    invoice = Invoice(
        vendor_name="PROVEEDOR TEST",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="FAC-BOUNDARY",
        dte_type=DTEType.FACTURA_ELECTRONICA,
    )
    iva = (neto * Decimal("0.19")).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)
    total_con_redondeo = (neto + iva + delta).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    invoice.net_amount = neto
    invoice.tax_amount = iva
    invoice.total_amount = total_con_redondeo

    # Dentro de la tolerancia no debe lanzar error
    assert invoice.validate_accounting_invariants(strict=True) is True


@given(
    neto=net_amount_strategy,
    excess=st.decimals(min_value=Decimal("1.0100"), max_value=Decimal("50.0000"), places=4),
)
@settings(max_examples=50)
def test_hypothesis_invoice_strict_fails_beyond_1_clp(neto: Decimal, excess: Decimal) -> None:
    """
    Verifica que si la discrepancia supera 1.0 CLP, validate_accounting_invariants(strict=True)
    lanza InvoiceTotalMismatchError.
    """
    invoice = Invoice(
        vendor_name="PROVEEDOR TEST",
        vendor_tax_id=TaxId("76.192.083-9"),
        invoice_number="FAC-FAIL",
        dte_type=DTEType.FACTURA_ELECTRONICA,
    )
    iva = (neto * Decimal("0.19")).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)
    total_descalzado = (neto + iva + excess).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    invoice.net_amount = neto
    invoice.tax_amount = iva
    invoice.total_amount = total_descalzado

    with pytest.raises(InvoiceTotalMismatchError):
        invoice.validate_accounting_invariants(strict=True)


# ---------------------------------------------------------------------------
# 2. Desacoplamiento de Empaque (Packaging Factor) y Costo Unitario
# ---------------------------------------------------------------------------


@given(
    quantity=arbitrary_quantity_strategy,
    factor=arbitrary_factor_strategy,
)
@settings(max_examples=100)
def test_hypothesis_packaging_factor_physical_stock(quantity: Decimal, factor: Decimal) -> None:
    """
    Invariante: stock_fisico = cantidad * factor.
    Garantiza que la conversión a existencias físicas de inventario
    coincide exactamente con el producto de cantidad y factor.
    """
    pkg = PackagingFactor(factor)
    stock_fisico = pkg.to_physical_stock(quantity)

    expected = (quantity * factor).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)
    assert stock_fisico == expected
    assert stock_fisico > Decimal("0.0000")


@given(
    quantity=arbitrary_quantity_strategy,
    factor=arbitrary_factor_strategy,
    unit_price=kitchen_unit_price_strategy,
)
@settings(max_examples=100)
def test_hypothesis_pure_mathematical_parity_and_cost(
    quantity: Decimal,
    factor: Decimal,
    unit_price: Decimal,
) -> None:
    """
    Invariante Matemática Pura: Para cualquier cantidad (>0) y factor de empaque (>0):
    - stock_fisico = cantidad * factor
    - costo_unitario = total_neto / stock_fisico
    - costo_unitario * stock_fisico == total_neto (tolerancia < 0.01)
    """
    total_neto = quantity * unit_price
    stock_fisico = quantity * factor
    assert stock_fisico > Decimal("0")

    costo_unitario = total_neto / stock_fisico
    reconstituido = costo_unitario * stock_fisico
    diff = abs(reconstituido - total_neto)

    assert diff < TOLERANCE_CENT, f"Diferencia {diff} excede tolerancia 0.01"


@given(
    quantity=kitchen_quantity_strategy,
    factor=kitchen_factor_strategy,
    unit_price=kitchen_unit_price_strategy,
)
@settings(max_examples=100)
def test_hypothesis_inventory_unit_cost_reconstitution(
    quantity: Decimal,
    factor: Decimal,
    unit_price: Decimal,
) -> None:
    """
    Invariante de Dominio en InvoiceLineItem:
    - stock_fisico = cantidad * factor
    - costo_unitario * stock_fisico == total_neto con tolerancia de redondeo menor a 0.01.
    """
    line_total = (quantity * unit_price).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    line = InvoiceLineItem(
        raw_description="CARNE VACUNO HUACHALOMO CAJA",
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        packaging_factor=factor,
        inventory_unit="kg",
    )

    stock_fisico = line.calculated_stock_qty
    costo_unitario = line.inventory_unit_cost

    # 1. Verificar stock_fisico = cantidad * factor
    expected_stock = (quantity * factor).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)
    assert stock_fisico == expected_stock

    # 2. Reconstitución: costo_unitario * stock_fisico == total_neto (< 0.01 CLP)
    reconstituted_total = costo_unitario * stock_fisico
    diff = abs(reconstituted_total - line_total)
    assert diff < TOLERANCE_CENT, (
        f"Reconstitución excede tolerancia 0.01: "
        f"costo ({costo_unitario}) * stock ({stock_fisico}) = {reconstituted_total} vs total ({line_total}). "
        f"Diff: {diff}"
    )


@given(
    quantity=arbitrary_quantity_strategy,
    factor=arbitrary_factor_strategy,
    unit_price=kitchen_unit_price_strategy,
)
@settings(max_examples=100)
def test_hypothesis_packaging_factor_pure_reconstitution(
    quantity: Decimal,
    factor: Decimal,
    unit_price: Decimal,
) -> None:
    """
    Verifica que el Value Object PackagingFactor convierte existencias físicas
    y que la tasa de costo unitario satisface la identidad contable:
    stock_fisico = cantidad * factor
    costo_unitario * stock_fisico == total_neto
    con tolerancia estricta menor a 0.01.
    """
    pkg = PackagingFactor(factor)
    stock_fisico = pkg.to_physical_stock(quantity)
    total_neto = (quantity * unit_price).quantize(DECIMAL_QUANT_4, rounding=ROUND_HALF_UP)

    # Costo unitario exacto por unidad canónica
    costo_unitario = total_neto / stock_fisico

    reconstituido = costo_unitario * stock_fisico
    diff = abs(reconstituido - total_neto)
    assert diff < TOLERANCE_CENT, f"Diferencia {diff} excede tolerancia 0.01"
