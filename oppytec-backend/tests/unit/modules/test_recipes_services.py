"""
Pruebas unitarias 1:1 para `src/modules/recipes/`.
Verifica `Receta`, `RecetaIngrediente`, `Combo` y `GrupoOpciones` con precisión `Decimal`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.recipes.infrastructure.models import (
    Combo,
    ComboItem,
    GrupoOpciones,
    GrupoOpcionesItem,
    Receta,
    RecetaIngrediente,
)

pytestmark = pytest.mark.unit


def test_recipes_and_combos_decimal_costing_and_i18n() -> None:
    """Verifica que escandallos y combos operen con `Decimal` y soporten traducción `i18n_data`."""
    receta = Receta(
        codigo="REC-LOMO-01",
        nombre="Lomo Saltado Clásico",
        es_subreceta=False,
        porciones_rendimiento=Decimal("1.0000"),
        costo_total_calculado=Decimal("3450.75"),
        precio_venta_bruto=Decimal("12900.00"),
    )
    receta.set_localized_text("en", "Classic Lomo Saltado")
    assert receta.get_localized_text("en", receta.nombre) == "Classic Lomo Saltado"

    ing = RecetaIngrediente(
        receta_id=1,
        producto_id=10,
        cantidad_receta=Decimal("220.0000"),
        porcentaje_merma=Decimal("8.50"),
    )
    assert ing.cantidad_receta == Decimal("220.0000")

    combo = Combo(nombre="Menú Ejecutivo", precio_venta_bruto=Decimal("15900.00"))
    item = ComboItem(combo_id=1, receta_id=1, cantidad=Decimal("1.0000"))
    grupo = GrupoOpciones(nombre="Punto de Cocción", min_selecciones=1, max_selecciones=1)
    op_item = GrupoOpcionesItem(grupo_id=1, producto_id=10, recargo_precio=Decimal("1500.00"))

    assert combo.precio_venta_bruto + op_item.recargo_precio == Decimal("17400.00")
    assert item.cantidad == Decimal("1.0000")
    assert grupo.max_selecciones == 1
