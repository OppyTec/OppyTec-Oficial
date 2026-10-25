"""
oppytec-backend/tests/modules/inventory/test_kardex_axioms.py
Certificación 5D de los 5 Axiomas Matemáticos del Kardex (Paridad OppyTec-Legacy):

1. Conservación de masa en transferencias: ΔOrigen + ΔDestino = 0.
2. Invariante de saldo no negativo en salidas normales.
3. Ordenamiento estricto FEFO (caducidad más próxima primero, sin fecha al final, desempate por id).
4. Cálculo exacto de PPP (Precio Promedio Ponderado por capas y WACC en recepciones).
5. Conciliación de inventario: Diferencia = Físico - Teórico, con signo y valorización monetaria precisa.

Cumple con Clean Architecture, Regla Inmutable 02 (cero floats, precisión Decimal estricta)
y testing basado en propiedades (Hypothesis).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.core.exceptions import (
    InsufficientStockError,
    TransferSameWarehouseError,
)
from src.modules.inventory.application import (
    CountItemInput,
    InventoryService,
    PhysicalCountService,
)
from src.modules.inventory.domain.entities import (
    PhysicalCountItem,
)
from src.modules.inventory.domain.kardex_math import (
    PurchaseLayer,
    StockLot,
    apply_movement,
    calculate_inventory_ppp,
    calculate_weighted_average_cost,
    fefo_allocate,
    fefo_sort,
)
from src.modules.inventory.domain.value_objects import (
    MoneyAmount,
    MovementType,
    StockQuantity,
)

pytestmark = [pytest.mark.unit]

dec_positive = st.decimals(min_value=Decimal("0.0100"), max_value=Decimal("10000.0000"), places=4)
dec_cost = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("500000.00"), places=2)


# ============================================================================
# AXIOMA 1: CONSERVACIÓN DE MASA EN TRANSFERENCIAS (ΔOrigen + ΔDestino = 0)
# ============================================================================


class TestAxiom1MassConservation:
    """Axioma 1: Toda transferencia conserva estrictamente la masa total del sistema."""

    def test_transfer_mass_conservation_single_product(self) -> None:
        service = InventoryService()
        pid = 101
        origin_wh = 1
        dest_wh = 2

        # Cargar stock inicial en bodega origen
        initial_stock = Decimal("150.0000")
        transfer_qty = Decimal("40.0000")

        service.register_movement(
            producto_id=pid,
            bodega_id=origin_wh,
            movement_type="ENTRADA",
            quantity=initial_stock,
            unit_cost=Decimal("1000.00"),
            actor_user_id=1,
            tenant_id="tenant_qa_axioms",
        )

        total_before = service.balance(pid, origin_wh) + service.balance(pid, dest_wh)
        assert total_before == initial_stock

        # Ejecutar transferencia masiva inter-bodega
        pairs = service.transfer_stock_bulk(
            bodega_origen_id=origin_wh,
            bodega_destino_id=dest_wh,
            items=[(pid, transfer_qty)],
            actor_user_id=1,
            tenant_id="tenant_qa_axioms",
        )
        assert len(pairs) == 1
        out_entry, in_entry = pairs[0]
        assert out_entry.quantity == transfer_qty
        assert in_entry.quantity == transfer_qty
        assert out_entry.transfer_id == in_entry.transfer_id

        delta_origin = service.balance(pid, origin_wh) - initial_stock  # -40
        delta_dest = service.balance(pid, dest_wh) - Decimal("0.0000")  # +40

        # Axioma: ΔOrigen + ΔDestino == 0
        assert delta_origin + delta_dest == Decimal("0.0000")
        assert delta_origin == -transfer_qty
        assert delta_dest == transfer_qty

        total_after = service.balance(pid, origin_wh) + service.balance(pid, dest_wh)
        assert total_before == total_after

    def test_transfer_to_same_warehouse_forbidden(self) -> None:
        service = InventoryService()
        with pytest.raises(TransferSameWarehouseError):
            service.transfer_stock_bulk(
                bodega_origen_id=1,
                bodega_destino_id=1,
                items=[(10, Decimal("5.0000"))],
                actor_user_id=1,
            )

    def test_transfer_insufficient_stock_fails_atomically(self) -> None:
        service = InventoryService()
        service.register_movement(
            producto_id=20,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("10.0000"),
            unit_cost=Decimal("500.00"),
            actor_user_id=1,
        )

        with pytest.raises(InsufficientStockError):
            service.transfer_stock_bulk(
                bodega_origen_id=1,
                bodega_destino_id=2,
                items=[(20, Decimal("10.0001"))],
                actor_user_id=1,
            )
        # Estado inalterado
        assert service.balance(20, 1) == Decimal("10.0000")
        assert service.balance(20, 2) == Decimal("0")

    @given(stock_init=dec_positive, fraction=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1.0"), places=2))
    def test_property_mass_conservation_invariant(self, stock_init: Decimal, fraction: Decimal) -> None:
        """Propiedad: El inventario global nunca se crea ni se destruye en transferencias."""
        qty_to_transfer = (stock_init * fraction).quantize(Decimal("0.0001"))
        if qty_to_transfer <= Decimal(0):
            return

        service = InventoryService()
        service.register_movement(
            producto_id=1,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=stock_init,
            unit_cost=Decimal("100.00"),
            actor_user_id=1,
        )

        initial_global = service.balance(1, 1) + service.balance(1, 2)
        service.transfer_stock_bulk(
            bodega_origen_id=1,
            bodega_destino_id=2,
            items=[(1, qty_to_transfer)],
            actor_user_id=1,
        )
        final_global = service.balance(1, 1) + service.balance(1, 2)

        assert initial_global == final_global


# ============================================================================
# AXIOMA 2: INVARIANTE DE SALDO NO NEGATIVO EN SALIDAS NORMALES
# ============================================================================


class TestAxiom2NonNegativeStockInvariant:
    """Axioma 2: Saldo resultante de cualquier salida normal >= 0."""

    @pytest.mark.parametrize(
        "mov_type",
        [
            MovementType.SALIDA,
            MovementType.CONSUMO,
            MovementType.MERMA,
            MovementType.TRASPASO_OUT,
            MovementType.AJUSTE_NEGATIVO,
        ],
    )
    def test_exit_movements_reject_negative_balance(self, mov_type: MovementType) -> None:
        cur_balance = Decimal("25.0000")
        excess_qty = Decimal("25.0001")

        with pytest.raises(InsufficientStockError):
            apply_movement(cur_balance, mov_type, excess_qty)

    def test_exact_depletion_allowed_zero_balance(self) -> None:
        cur_balance = Decimal("15.5000")
        new_balance = apply_movement(cur_balance, MovementType.SALIDA, cur_balance)
        assert new_balance == Decimal("0.0000")

    def test_stock_quantity_rejects_negative_value_object(self) -> None:
        from src.core.exceptions import NegativeStockNotAllowedError

        with pytest.raises(NegativeStockNotAllowedError):
            StockQuantity(Decimal("-0.0001"))

    @given(balance=dec_positive, delta=dec_positive)
    def test_property_exit_never_yields_negative(self, balance: Decimal, delta: Decimal) -> None:
        """Cualquier salida de stock resulta en >= 0 o lanza InsufficientStockError."""
        if delta > balance:
            with pytest.raises(InsufficientStockError):
                apply_movement(balance, MovementType.SALIDA, delta)
        else:
            resulting = apply_movement(balance, MovementType.SALIDA, delta)
            assert resulting >= Decimal(0)


# ============================================================================
# AXIOMA 3: ORDENAMIENTO ESTRICTO FEFO (FIRST-EXPIRED, FIRST-OUT)
# ============================================================================


class TestAxiom3StrictFefoOrdering:
    """Axioma 3: Lotes con expiración más próxima se consumen primero deterministamente."""

    def test_fefo_sort_strict_priority(self) -> None:
        today = date(2026, 10, 25)
        lot_in_3_days = StockLot(lot_id=10, quantity=Decimal("10"), expires_on=today + timedelta(days=3))
        lot_in_1_day = StockLot(lot_id=20, quantity=Decimal("10"), expires_on=today + timedelta(days=1))
        lot_in_10_days = StockLot(lot_id=30, quantity=Decimal("10"), expires_on=today + timedelta(days=10))
        lot_no_date_1 = StockLot(lot_id=40, quantity=Decimal("10"), expires_on=None)
        lot_in_1_day_tie = StockLot(lot_id=5, quantity=Decimal("10"), expires_on=today + timedelta(days=1))

        all_lots = [lot_no_date_1, lot_in_10_days, lot_in_3_days, lot_in_1_day, lot_in_1_day_tie]
        sorted_result = fefo_sort(all_lots)

        # 1. lot_in_1_day_tie (lot_id=5) y lot_in_1_day (lot_id=20) empatan en 1 día -> orden por id (5, 20)
        # 2. lot_in_3_days (lot_id=10)
        # 3. lot_in_10_days (lot_id=30)
        # 4. lot_no_date_1 (lot_id=40) al final
        expected_ids = [5, 20, 10, 30, 40]
        assert [lot.lot_id for lot in sorted_result] == expected_ids

    def test_fefo_allocation_exact_consumption(self) -> None:
        today = date(2026, 10, 25)
        lots = [
            StockLot(lot_id=1, quantity=Decimal("3.0000"), expires_on=today + timedelta(days=2)),
            StockLot(lot_id=2, quantity=Decimal("5.0000"), expires_on=today + timedelta(days=5)),
            StockLot(lot_id=3, quantity=Decimal("10.0000"), expires_on=None),
        ]

        # Consumo de 6 unidades: 3 del lote 1 + 3 del lote 2
        alloc = fefo_allocate(lots, Decimal("6.0000"))
        assert len(alloc) == 2
        assert alloc[0].lot_id == 1
        assert alloc[0].quantity == Decimal("3.0000")
        assert alloc[1].lot_id == 2
        assert alloc[1].quantity == Decimal("3.0000")


# ============================================================================
# AXIOMA 4: CÁLCULO EXACTO DE PPP (PRECIO PROMEDIO PONDERADO)
# ============================================================================


class TestAxiom4ExactWeightedAverageCost:
    """Axioma 4: Cálculo de PPP por capas dinámicas y recepción WACC con exactitud decimal."""

    def test_ppp_layered_valuation(self) -> None:
        """
        Stock total: 20 unidades.
        Compras disponibles:
          - Capa 1: 8 unidades a $1.200 = $9.600
          - Capa 2: 10 unidades a $1.000 = $10.000
          - Remanente: 2 unidades al costo base $800 = $1.600
        Total valor = $21.200
        PPP = $21.200 / 20 = $1.060,0000
        """
        layers = [
            PurchaseLayer(quantity=Decimal("8.0000"), unit_cost=Decimal("1200.00")),
            PurchaseLayer(quantity=Decimal("10.0000"), unit_cost=Decimal("1000.00")),
        ]
        val_inv, ppp = calculate_inventory_ppp(
            stock_actual=Decimal("20.0000"),
            purchases=layers,
            base_cost=Decimal("800.00"),
        )
        assert val_inv == Decimal("21200.00")
        assert ppp == Decimal("1060.0000")

    def test_ppp_reception_wacc(self) -> None:
        """
        Stock actual: 100 unidades a $500 = $50.000
        Recepción de compra: 50 unidades a $650 = $32.500
        Total: 150 unidades por $82.500
        PPP resultante = 82500 / 150 = $550,0000
        """
        new_ppp = calculate_weighted_average_cost(
            current_qty=Decimal("100.0000"),
            current_avg_cost=Decimal("500.0000"),
            incoming_qty=Decimal("50.0000"),
            incoming_unit_cost=Decimal("650.0000"),
        )
        assert new_ppp == Decimal("550.0000")

    def test_ppp_strict_decimal_no_float(self) -> None:
        layers = [PurchaseLayer(quantity=Decimal("5.0000"), unit_cost=Decimal("333.33"))]
        val_inv, ppp = calculate_inventory_ppp(Decimal("5.0000"), layers)
        assert isinstance(val_inv, Decimal)
        assert isinstance(ppp, Decimal)
        assert not isinstance(val_inv, float)
        assert not isinstance(ppp, float)


# ============================================================================
# AXIOMA 5: CONCILIACIÓN DE INVENTARIO (Diferencia = Físico - Teórico)
# ============================================================================


class TestAxiom5PhysicalReconciliation:
    """Axioma 5: Diferencia = Físico - Teórico, con signo y valorización monetaria precisa."""

    def test_surplus_and_shortage_signs_and_valuation(self) -> None:
        # 1. Sobrante (Físico > Teórico -> Diferencia > 0)
        item_surplus = PhysicalCountItem(
            producto_id=1,
            stock_teorico_sistema=StockQuantity("50.0000"),
            stock_fisico_contado=StockQuantity("55.0000"),
            costo_unitario_ppp=MoneyAmount("2000.00", currency="CLP"),
        )
        assert item_surplus.has_discrepancy is True
        assert item_surplus.is_surplus is True
        assert item_surplus.is_shortage is False
        assert item_surplus.diferencia_unidades.value == Decimal("5.0000")
        assert item_surplus.valorizacion_diferencia.amount == Decimal("10000.00")

        # 2. Faltante (Físico < Teórico -> Diferencia < 0)
        item_shortage = PhysicalCountItem(
            producto_id=2,
            stock_teorico_sistema=StockQuantity("100.0000"),
            stock_fisico_contado=StockQuantity("92.0000"),
            costo_unitario_ppp=MoneyAmount("1500.00", currency="CLP"),
        )
        assert item_shortage.has_discrepancy is True
        assert item_shortage.is_surplus is False
        assert item_shortage.is_shortage is True
        assert item_shortage.diferencia_unidades.value == Decimal("-8.0000")
        assert item_shortage.valorizacion_diferencia.amount == Decimal("-12000.00")

        # 3. Cuadrado exacto (Físico == Teórico -> Diferencia == 0)
        item_exact = PhysicalCountItem(
            producto_id=3,
            stock_teorico_sistema=StockQuantity("30.0000"),
            stock_fisico_contado=StockQuantity("30.0000"),
            costo_unitario_ppp=MoneyAmount("800.00", currency="CLP"),
        )
        assert item_exact.has_discrepancy is False
        assert item_exact.is_surplus is False
        assert item_exact.is_shortage is False
        assert item_exact.diferencia_unidades.value == Decimal("0.0000")
        assert item_exact.valorizacion_diferencia.amount == Decimal("0.00")

    def test_full_reconciliation_cycle_aligns_kardex_to_physical_count(self) -> None:
        """
        Ciclo completo de reconciliación en bodega:
        - Stock teórico previo: Producto A = 100, Producto B = 50.
        - Conteo físico: Producto A = 105 (sobra 5), Producto B = 47 (falta 3).
        - Tras approve_and_reconcile:
          El saldo final en Kardex es exactamente 105 y 47.
        """
        inventory_svc = InventoryService()
        count_svc = PhysicalCountService(inventory_svc)
        bodega_id = 1
        responsable_id = 99
        approver_id = 100

        # Cargar stocks teóricos iniciales
        inventory_svc.register_movement(
            producto_id=1,
            bodega_id=bodega_id,
            movement_type="ENTRADA",
            quantity=Decimal("100.0000"),
            unit_cost=Decimal("1000.00"),
            actor_user_id=1,
        )
        inventory_svc.register_movement(
            producto_id=2,
            bodega_id=bodega_id,
            movement_type="ENTRADA",
            quantity=Decimal("50.0000"),
            unit_cost=Decimal("2000.00"),
            actor_user_id=1,
        )

        session = count_svc.start_count_session(
            bodega_id=bodega_id,
            responsable_user_id=responsable_id,
            notas="Auditoría semestral bodega 1",
        )

        count_svc.save_count_items(
            conteo_id=session.id or 1,
            items=[
                CountItemInput(producto_id=1, stock_fisico_contado=Decimal("105.0000"), costo_unitario_ppp=Decimal("1000.00")),
                CountItemInput(producto_id=2, stock_fisico_contado=Decimal("47.0000"), costo_unitario_ppp=Decimal("2000.00")),
            ],
        )

        finalized = count_svc.finalize_count_session(conteo_id=session.id or 1)
        assert finalized.estado == "PENDIENTE_APROBACION"
        assert finalized.total_discrepancy_units().value == Decimal("2.0000")  # +5 - 3 = +2
        assert finalized.total_discrepancy_value().amount == Decimal("-1000.00")  # +5000 - 6000 = -1000

        approved = count_svc.approve_and_reconcile(
            conteo_id=session.id or 1,
            aprobador_user_id=approver_id,
        )
        assert approved.estado == "APROBADO"

        # Verificación estricta: Los saldos en Kardex ahora coinciden al 100% con el conteo físico
        assert inventory_svc.balance(1, bodega_id) == Decimal("105.0000")
        assert inventory_svc.balance(2, bodega_id) == Decimal("47.0000")
