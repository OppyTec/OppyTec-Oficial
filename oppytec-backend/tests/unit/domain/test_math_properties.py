"""Propiedades Hypothesis sobre la matemática Decimal del dominio (unidades, PPP, Kardex, escandallo, KPIs)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.core.exceptions import InsufficientStockError
from src.modules.analytics.domain.kpi_formulas import inventory_turnover, project_linear
from src.modules.catalog.domain.unit_conversion import (
    UnitLayers,
    purchase_to_recipe,
    purchase_to_storage,
    storage_to_recipe,
    weighted_average_cost,
)
from src.modules.inventory.domain.kardex_math import (
    StockLot,
    apply_movement,
    canonical_lock_order,
    fefo_allocate,
    waste_requires_approval,
)
from src.modules.operations.domain.pos_consumption import buffet_cost_per_pax
from src.modules.procurement.domain.reconciliation import DocLine, MatchStatus, reconcile_three_way
from src.modules.recipes.domain.escandallo_calculator import (
    Recipe,
    RecipeCycleError,
    RecipeLine,
    recipe_portion_cost,
    recipe_total_cost,
)

pytestmark = pytest.mark.unit

qty = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100000"), places=4)
factor = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000"), places=4)


@given(q=qty, f1=factor, f2=factor)
def test_unit_layers_compose(q: Decimal, f1: Decimal, f2: Decimal) -> None:
    """compra->receta equivale a compra->almacén->receta (tolerancia de cuantización)."""
    layers = UnitLayers(f1, f2)
    direct = purchase_to_recipe(q, layers)
    chained = storage_to_recipe(purchase_to_storage(q, layers), layers)
    assert abs(direct - chained) <= Decimal("0.0001") * f2 + Decimal("0.00000002")


@given(s=qty, c=qty, i=qty, ic=qty)
def test_ppp_bounded_by_costs(s: Decimal, c: Decimal, i: Decimal, ic: Decimal) -> None:
    """El PPP queda entre el costo actual y el de entrada."""
    r = weighted_average_cost(s, c, i, ic)
    assert min(c, ic) - Decimal("0.0001") <= r <= max(c, ic) + Decimal("0.0001")


@given(balance=qty, q=qty)
def test_kardex_never_negative(balance: Decimal, q: Decimal) -> None:
    """Una salida jamás deja saldo negativo."""
    if q > balance:
        with pytest.raises(InsufficientStockError):
            apply_movement(balance, "SALIDA", q)
    else:
        assert apply_movement(balance, "SALIDA", q) == balance - q
    assert apply_movement(balance, "ENTRADA", q) == balance + q


@given(ids=st.lists(st.integers(min_value=1, max_value=10_000)))
def test_lock_order_sorted_unique(ids: list[int]) -> None:
    """Orden canónico ascendente, sin duplicados e idempotente."""
    out = canonical_lock_order(ids)
    assert out == sorted(set(ids))
    assert canonical_lock_order(reversed(ids)) == out


@given(quantities=st.lists(qty, min_size=1, max_size=6), frac=st.decimals(min_value=Decimal("0.01"), max_value=Decimal(1), places=2))
def test_fefo_conserves_quantity_and_orders_by_expiry(quantities: list[Decimal], frac: Decimal) -> None:
    """FEFO asigna exactamente lo requerido y respeta el vencimiento."""
    lots = [StockLot(i, q, date(2030, 1, 1 + i)) for i, q in enumerate(quantities)]
    required = sum(quantities, Decimal(0)) * frac
    if required <= 0:
        return
    alloc = fefo_allocate(lots, required)
    assert sum((a.quantity for a in alloc), Decimal(0)) == required
    assert [a.lot_id for a in alloc] == sorted(a.lot_id for a in alloc)


@given(cost=qty, thr=qty)
def test_waste_threshold_strict(cost: Decimal, thr: Decimal) -> None:
    """Aprobación solo si supera estrictamente el umbral."""
    assert waste_requires_approval(cost, thr) is (cost > thr)


@given(price=qty, n=st.integers(min_value=1, max_value=500))
def test_recipe_cost_linear_in_quantity(price: Decimal, n: int) -> None:
    """El costo escala linealmente con la cantidad del insumo."""
    r = Recipe(1, [RecipeLine(Decimal(n), ingredient_id=1)])
    assert recipe_total_cost(1, {1: r}, {1: price}) == (price * n).quantize(Decimal("0.0001"))


def test_recipe_cycle_detected_and_sub_recipe_yield() -> None:
    """Ciclos son rechazados; sub-recetas dividen por yield."""
    a = Recipe(1, [RecipeLine(Decimal(1), sub_recipe_id=2)])
    b = Recipe(2, [RecipeLine(Decimal(1), sub_recipe_id=1)])
    with pytest.raises(RecipeCycleError):
        recipe_total_cost(1, {1: a, 2: b}, {})
    sub = Recipe(2, [RecipeLine(Decimal(10), ingredient_id=1)], yield_portions=Decimal(4))
    top = Recipe(1, [RecipeLine(Decimal(2), sub_recipe_id=2)])
    assert recipe_portion_cost(1, {1: top, 2: sub}, {1: Decimal(3)}) == Decimal("15.0000")


@given(q=qty, c=qty)
def test_reconciliation_matches_identical_docs(q: Decimal, c: Decimal) -> None:
    """Documentos idénticos concilian como MATCHED con diferencias cero."""
    docs = [DocLine(1, q, c)]
    res = reconcile_three_way(docs, docs, docs)
    assert res.status is MatchStatus.MATCHED
    assert res.invoice_total_diff == 0


@given(total=qty, pax=st.integers(min_value=1, max_value=1000))
def test_buffet_cost_per_pax_nonneg(total: Decimal, pax: int) -> None:
    """Costo por pax es no negativo y multiplicado por pax se aproxima al total."""
    c = buffet_cost_per_pax(total, pax)
    assert c >= 0
    assert abs(c * pax - total) <= Decimal("0.005") * pax


@given(cogs=qty, inv=qty)
def test_turnover_positive(cogs: Decimal, inv: Decimal) -> None:
    """Rotación positiva para inputs positivos."""
    assert inventory_turnover(cogs, inv) >= 0


def test_projection_linear() -> None:
    """Proyección lineal exacta."""
    assert project_linear([Decimal(10), Decimal(20), Decimal(30)], 2) == Decimal("50.00")
