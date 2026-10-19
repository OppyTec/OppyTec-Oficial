"""
Pruebas unitarias 1:1 para `src/modules/catalog/`.
Verifica las 3 capas de unidades (`Decimal`), `TranslatableI18nMixin` e inmutabilidad de `Marca`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.catalog.infrastructure.models import (
    Categoria,
    FamiliaProducto,
    Marca,
    Producto,
)
from src.shared.models_base import is_table_proper_noun_immutable

pytestmark = pytest.mark.unit


def test_producto_three_unit_layers_decimal_and_i18n_translation() -> None:
    """Verifica precisión `Decimal` en las 3 capas de unidades y traducción dinámica `es`/`en`."""
    prod = Producto(
        sku="HEL-CHOC-001",
        nombre="Cono Helado de Chocolate",
        categoria_id=1,
        unidad_compra="CAJA",
        unidad_almacen="LITRO",
        unidad_receta="ML",
        factor_compra_a_almacen=Decimal("10.0000"),
        factor_almacen_a_receta=Decimal("1000.0000"),
        costo_compra_neto=Decimal("25000.00"),
        costo_promedio_almacen=Decimal("2500.00"),
    )
    prod.set_localized_text("es", "Cono Helado de Chocolate", is_source=True)
    prod.set_localized_text("en", "Chocolate Ice Cream Cone")

    assert prod.get_localized_text("en", prod.nombre) == "Chocolate Ice Cream Cone"
    assert prod.get_localized_text("es", prod.nombre) == "Cono Helado de Chocolate"
    assert prod.i18n_source_hash is not None
    assert len(prod.i18n_source_hash) == 64

    total_recipe_units = prod.factor_compra_a_almacen * prod.factor_almacen_a_receta
    assert total_recipe_units == Decimal("10000.00000000")

    assert Marca.translatable is False
    assert is_table_proper_noun_immutable("marcas") is True
    assert Categoria.translatable is True
    assert FamiliaProducto.translatable is True
