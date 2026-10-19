"""
Pruebas unitarias 1:1 para `src/modules/inventory/`.
Verifica `Bodega`, `ProductoBodega`, Kardex Append-Only (`RegistroStock`) y `Merma` con `Decimal`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.inventory.infrastructure.models import (
    AreaOperativa,
    Bodega,
    ConteoItem,
    Merma,
    ProductoBodega,
    RegistroStock,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = pytest.mark.unit


def test_inventory_kardex_append_only_and_decimal_stock() -> None:
    """Verifica que `RegistroStock` sea inmutable (sin `SoftDeleteMixin`) y opere con `Decimal`."""
    assert not issubclass(RegistroStock, SoftDeleteMixin)
    assert "is_deleted" not in RegistroStock.__table__.c

    bodega = Bodega(nombre="Bodega Frío", es_principal=True)
    bodega.set_localized_text("en", "Cold Storage Warehouse")
    assert bodega.get_localized_text("en", bodega.nombre) == "Cold Storage Warehouse"

    pb = ProductoBodega(producto_id=1, bodega_id=1, stock_actual=Decimal("42.5000"))
    mov = RegistroStock(
        producto_id=1,
        bodega_id=1,
        tipo_movimiento="ENTRADA_COMPRA",
        cantidad=Decimal("10.0000"),
        saldo_resultante=pb.stock_actual + Decimal("10.0000"),
        costo_unitario=Decimal("1850.00"),
        actor_user_id=5,
    )
    assert mov.saldo_resultante == Decimal("52.5000")

    merma = Merma(
        producto_id=1,
        bodega_id=1,
        cantidad=Decimal("2.5000"),
        costo_total=Decimal("4625.00"),
        motivo="Corte de cadena de frío",
        reportado_por_user_id=5,
    )
    assert merma.costo_total == Decimal("4625.00")
    assert AreaOperativa.translatable is True
    assert ConteoItem.__tablename__ == "conteo_items"
