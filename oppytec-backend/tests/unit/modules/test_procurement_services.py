"""
Pruebas unitarias 1:1 para `src/modules/procurement/`.
Verifica la regla de inmutabilidad `"Pollo King"` en `Proveedor` (`translatable = False`), `Compra` e `Invoice`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.procurement.infrastructure.models import (
    Compra,
    CompraItem,
    Invoice,
    ProductoProveedor,
    Proveedor,
)
from src.shared.models_base import is_table_proper_noun_immutable

pytestmark = pytest.mark.unit


def test_proveedor_pollo_king_proper_noun_immutability_and_invoices() -> None:
    """Garantiza que `Proveedor` (`"Pollo King"`) tenga `translatable = False` y no tenga columna `i18n_data`."""
    assert Proveedor.translatable is False
    assert is_table_proper_noun_immutable(Proveedor.__tablename__) is True
    assert "i18n_data" not in Proveedor.__table__.c

    pollo_king = Proveedor(
        rut_tax_id="76.543.210-K",
        razon_social="Pollo King",
        nombre_fantasia="Pollo King",
        lead_time_dias=2,
    )
    assert pollo_king.razon_social == "Pollo King"

    compra = Compra(
        proveedor_id=1,
        bodega_destino_id=1,
        moneda="CLP",
        tasa_fx_aplicada=Decimal("1.00000000"),
        monto_neto=Decimal("100000.00"),
        monto_impuestos=Decimal("19000.00"),
        monto_total=Decimal("119000.00"),
    )
    detalle = CompraItem(
        compra_id=1,
        producto_id=5,
        cantidad_solicitada=Decimal("20.0000"),
        cantidad_recibida=Decimal("20.0000"),
        costo_unitario_neto=Decimal("5000.00"),
    )
    factura = Invoice(
        proveedor_id=1,
        compra_id=1,
        folio_factura="FAC-99881",
        moneda="CLP",
        monto_neto=compra.monto_neto,
        monto_iva=compra.monto_impuestos,
        monto_total=compra.monto_total,
    )
    acuerdo = ProductoProveedor(
        producto_id=5,
        proveedor_id=1,
        ultimo_costo_neto=Decimal("5000.00"),
    )
    assert factura.monto_total == Decimal("119000.00")
    assert detalle.costo_unitario_neto * detalle.cantidad_recibida == Decimal("100000.000000")
    assert acuerdo.ultimo_costo_neto == Decimal("5000.00")
