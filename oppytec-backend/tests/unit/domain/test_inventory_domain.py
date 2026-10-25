"""
oppytec-backend/tests/unit/domain/test_inventory_domain.py
Pruebas unitarias de dominio DDD para el Módulo de Inventario.
Verifica Value Objects, Entidades puras, FEFO, Locks canónicos y Excepciones RFC 7807.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.core.exceptions import (
    InsufficientStockError,
    InvalidMovementTypeError,
    NegativeStockNotAllowedError,
    TransferSameWarehouseError,
)
from src.modules.inventory.domain import (
    KardexMovement,
    LotAllocation,
    MoneyAmount,
    MovementType,
    PhysicalCountItem,
    PhysicalCountSession,
    StockItem,
    StockLot,
    StockQuantity,
    StockTransfer,
    StorageLocation,
    apply_movement,
    canonical_lock_order,
    fefo_allocate,
    fefo_sort,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 1. VALUE OBJECT: StockQuantity
# ============================================================================


class TestStockQuantity:
    """Validación exhaustiva del Value Object StockQuantity."""

    def test_creation_from_decimal_int_str(self) -> None:
        sq1 = StockQuantity(Decimal("10.5000"))
        sq2 = StockQuantity(10)
        sq3 = StockQuantity("10.5")
        sq4 = StockQuantity(sq1)

        assert sq1.value == Decimal("10.5000")
        assert sq2.value == Decimal("10.0000")
        assert sq3.value == Decimal("10.5000")
        assert sq4.value == Decimal("10.5000")

    def test_float_is_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            StockQuantity(10.5)  # type: ignore[arg-type]

    def test_nan_and_inf_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            StockQuantity(Decimal("NaN"))
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            StockQuantity(Decimal("Infinity"))

    def test_quantization_to_four_decimals(self) -> None:
        sq = StockQuantity(Decimal("12.34567"))
        assert sq.value == Decimal("12.3457")  # ROUND_HALF_UP

    def test_negative_quantity_raises_error_by_default(self) -> None:
        with pytest.raises(NegativeStockNotAllowedError) as exc_info:
            StockQuantity(Decimal("-0.0001"))
        assert exc_info.value.default_error_code == "NEGATIVE_STOCK_NOT_ALLOWED"

    def test_allow_negative_flag(self) -> None:
        sq = StockQuantity(Decimal("-5.2500"), allow_negative=True)
        assert sq.value == Decimal("-5.2500")
        assert sq.is_negative()
        assert not sq.is_positive()

    def test_arithmetic_operations(self) -> None:
        q1 = StockQuantity("10.0000")
        q2 = StockQuantity("4.5000")

        # Suma
        assert (q1 + q2).value == Decimal("14.5000")
        assert (q1 + Decimal("2.0000")).value == Decimal("12.0000")

        # Resta
        assert (q1 - q2).value == Decimal("5.5000")

        # Resta insuficiente
        with pytest.raises(InsufficientStockError):
            _ = q2 - q1

        # Multiplicación
        assert (q2 * 2).value == Decimal("9.0000")
        assert (q2 * Decimal("0.5")).value == Decimal("2.2500")
        with pytest.raises(TypeError):
            _ = q2 * 1.5  # type: ignore[operator]

        # Absoluto y negación
        neg_q = StockQuantity("-3.0000", allow_negative=True)
        assert abs(neg_q).value == Decimal("3.0000")
        assert (-q1).value == Decimal("-10.0000")

    def test_comparisons(self) -> None:
        q1 = StockQuantity("10.0000")
        q2 = StockQuantity("20.0000")
        q3 = StockQuantity("10.0000")

        assert q1 < q2
        assert q1 <= q3
        assert q2 > q1
        assert q1 >= q3
        assert q1 == q3
        assert q1 == Decimal("10.0000")
        assert q1 != q2

    def test_string_representations(self) -> None:
        q = StockQuantity("15.5")
        assert str(q) == "15.5000"
        assert repr(q) == "StockQuantity(15.5000, allow_negative=False)"


# ============================================================================
# 2. VALUE OBJECT: MoneyAmount
# ============================================================================


class TestMoneyAmount:
    """Validación del Value Object MoneyAmount."""

    def test_creation_and_precision(self) -> None:
        m1 = MoneyAmount(Decimal("1500.555"))
        assert m1.amount == Decimal("1500.56")  # 2 decimales ROUND_HALF_UP
        assert m1.currency == "CLP"

        m2 = MoneyAmount(5000, currency="USD")
        assert m2.amount == Decimal("5000.00")
        assert m2.currency == "USD"

    def test_float_is_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            MoneyAmount(99.99)  # type: ignore[arg-type]

    def test_nan_and_inf_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            MoneyAmount(Decimal("NaN"))

    def test_currency_isolation(self) -> None:
        m_clp = MoneyAmount(1000, currency="CLP")
        m_usd = MoneyAmount(1000, currency="USD")

        with pytest.raises(ValueError, match="Currency mismatch"):
            _ = m_clp + m_usd

        with pytest.raises(ValueError, match="Currency mismatch"):
            _ = m_clp - m_usd

    def test_arithmetic_with_stock_quantity(self) -> None:
        unit_price = MoneyAmount("150.00", currency="CLP")
        qty = StockQuantity("4.0000")

        total = unit_price * qty
        assert total.amount == Decimal("600.00")
        assert total.currency == "CLP"

    def test_comparisons(self) -> None:
        m1 = MoneyAmount(100, currency="CLP")
        m2 = MoneyAmount(200, currency="CLP")
        assert m1 < m2
        assert m2 > m1
        assert m1 == MoneyAmount(100, currency="CLP")


# ============================================================================
# 3. ENUM: MovementType
# ============================================================================


class TestMovementType:
    """Validación del Enum estricto MovementType."""

    def test_all_10_movement_types_defined(self) -> None:
        expected = {
            "ENTRADA",
            "SALIDA",
            "COMPRA",
            "CONSUMO",
            "MERMA",
            "TRASPASO_IN",
            "TRASPASO_OUT",
            "AJUSTE_POSITIVO",
            "AJUSTE_NEGATIVO",
            "AJUSTE_AUDITORIA",
        }
        actual = {m.value for m in MovementType}
        assert actual == expected

    def test_entry_and_exit_properties(self) -> None:
        assert MovementType.ENTRADA.is_entry is True
        assert MovementType.COMPRA.is_entry is True
        assert MovementType.TRASPASO_IN.is_entry is True
        assert MovementType.AJUSTE_POSITIVO.is_entry is True

        assert MovementType.SALIDA.is_exit is True
        assert MovementType.CONSUMO.is_exit is True
        assert MovementType.MERMA.is_exit is True
        assert MovementType.TRASPASO_OUT.is_exit is True
        assert MovementType.AJUSTE_NEGATIVO.is_exit is True

        # AJUSTE_AUDITORIA no es entry ni exit por defecto (depende de discrepancia)
        assert MovementType.AJUSTE_AUDITORIA.is_entry is False
        assert MovementType.AJUSTE_AUDITORIA.is_exit is False

    def test_from_str_case_insensitive(self) -> None:
        assert MovementType.from_str("entrada") == MovementType.ENTRADA
        assert MovementType.from_str("  Traspaso_Out  ") == MovementType.TRASPASO_OUT

    def test_from_str_invalid_raises_domain_exception(self) -> None:
        with pytest.raises(InvalidMovementTypeError) as exc_info:
            MovementType.from_str("INVALIDO_TOTAL")
        assert exc_info.value.status_code == 400
        assert issubclass(InvalidMovementTypeError, ValueError)


# ============================================================================
# 4. VALUE OBJECT: StorageLocation
# ============================================================================


class TestStorageLocation:
    """Validación del Value Object StorageLocation."""

    def test_normalization_and_formatting(self) -> None:
        loc = StorageLocation(pasillo="  A1  ", estante=" 02 ", nivel=" 03 ")
        assert loc.pasillo == "A1"
        assert loc.estante == "02"
        assert loc.nivel == "03"
        assert loc.is_assigned is True
        assert loc.code == "P-A1 / E-02 / N-03"

    def test_unassigned_location(self) -> None:
        loc = StorageLocation()
        assert loc.is_assigned is False
        assert loc.code == "SIN_UBICACION"

    def test_max_20_chars_constraint(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length of 20 characters"):
            StorageLocation(pasillo="X" * 21)


# ============================================================================
# 5. CANONICAL LOCK ORDER & ANTI-DEADLOCK
# ============================================================================


class TestCanonicalLockOrder:
    """Validación de ordenamiento determinista para prevenir deadlocks."""

    def test_ascending_and_deduplication(self) -> None:
        input_ids = [42, 5, 100, 5, 12, 100, 1]
        ordered = canonical_lock_order(input_ids)
        assert ordered == [1, 5, 12, 42, 100]

    def test_empty_iterable(self) -> None:
        assert canonical_lock_order([]) == []

    def test_already_sorted(self) -> None:
        assert canonical_lock_order([1, 2, 3]) == [1, 2, 3]


# ============================================================================
# 6. FEFO RULES: First-Expired, First-Out
# ============================================================================


class TestFefoRules:
    """Validación estricta de ordenamiento y consumo FEFO."""

    def test_fefo_sort_orders_by_nearest_expiration_date(self) -> None:
        today = date(2026, 10, 25)
        lot_soon = StockLot(lot_id=1, quantity=Decimal("10"), expires_on=today + timedelta(days=2))
        lot_later = StockLot(lot_id=2, quantity=Decimal("10"), expires_on=today + timedelta(days=10))
        lot_no_date = StockLot(lot_id=3, quantity=Decimal("10"), expires_on=None)
        lot_tie_breaker = StockLot(lot_id=4, quantity=Decimal("10"), expires_on=today + timedelta(days=2))

        lots = [lot_no_date, lot_later, lot_tie_breaker, lot_soon]
        sorted_lots = fefo_sort(lots)

        # Lote 1 y 4 vencen en 2 días, desempata por lot_id (1 < 4)
        # Luego Lote 2 (10 días)
        # Al final Lote 3 (sin fecha)
        assert [lot.lot_id for lot in sorted_lots] == [1, 4, 2, 3]

    def test_fefo_allocate_partial_and_full(self) -> None:
        today = date(2026, 10, 25)
        lots = [
            StockLot(lot_id=1, quantity=Decimal("5.0000"), expires_on=today + timedelta(days=5)),
            StockLot(lot_id=2, quantity=Decimal("10.0000"), expires_on=today + timedelta(days=15)),
        ]

        # Consumo de 8 unidades: 5 del lote 1 + 3 del lote 2
        alloc = fefo_allocate(lots, required=StockQuantity("8.0000"))
        assert len(alloc) == 2
        assert alloc[0] == LotAllocation(lot_id=1, quantity=Decimal("5.0000"))
        assert alloc[1] == LotAllocation(lot_id=2, quantity=Decimal("3.0000"))

    def test_fefo_allocate_insufficient_stock(self) -> None:
        lots = [
            StockLot(lot_id=1, quantity=Decimal("2.0000"), expires_on=date(2026, 11, 1)),
        ]
        with pytest.raises(InsufficientStockError):
            fefo_allocate(lots, required=Decimal("5.0000"))

    def test_fefo_allocate_zero_or_negative_raises_error(self) -> None:
        lots = [StockLot(lot_id=1, quantity=Decimal("10"), expires_on=None)]
        with pytest.raises(ValueError, match="must be strictly positive"):
            fefo_allocate(lots, required=Decimal("0"))


# ============================================================================
# 7. DOMAIN ENTITIES: StockItem, KardexMovement, PhysicalCount, StockTransfer
# ============================================================================


class TestDomainEntities:
    """Validación de comportamiento de las entidades de dominio."""

    def test_stock_item_semaphores_and_movement(self) -> None:
        item = StockItem(
            producto_id=101,
            bodega_id=1,
            stock_actual=StockQuantity("10.0000"),
            stock_minimo=StockQuantity("5.0000"),
            punto_reorden=StockQuantity("8.0000"),
        )

        assert not item.is_below_minimum()
        assert not item.is_critical()
        assert not item.needs_reorder()

        # Consumo que lleva el stock a 7.0000 (necesita reorden porque <= 8.0000)
        item.apply_movement(MovementType.CONSUMO, "3.0000")
        assert item.stock_actual == StockQuantity("7.0000")
        assert item.needs_reorder()
        assert not item.is_below_minimum()

        # Consumo que lleva a 2.0000 (bajo mínimo y crítico pues <= 2.5)
        item.apply_movement(MovementType.CONSUMO, "5.0000")
        assert item.stock_actual == StockQuantity("2.0000")
        assert item.is_below_minimum()
        assert item.is_critical()

        # Intento de salida mayor a existencias
        with pytest.raises(InsufficientStockError):
            item.apply_movement(MovementType.SALIDA, "3.0000")

    def test_physical_count_item_discrepancy_and_session(self) -> None:
        # Stock teórico: 10, Físico contado: 8 (Faltante de 2 unidades)
        item1 = PhysicalCountItem(
            producto_id=10,
            stock_teorico_sistema=StockQuantity("10.0000"),
            stock_fisico_contado=StockQuantity("8.0000"),
            costo_unitario_ppp=MoneyAmount("1000.00", currency="CLP"),
        )
        assert item1.has_discrepancy is True
        assert item1.is_shortage is True
        assert item1.is_surplus is False
        assert item1.diferencia_unidades.value == Decimal("-2.0000")
        assert item1.valorizacion_diferencia.amount == Decimal("-2000.00")

        # Stock teórico: 5, Físico contado: 7 (Sobrante de 2 unidades)
        item2 = PhysicalCountItem(
            producto_id=20,
            stock_teorico_sistema=StockQuantity("5.0000"),
            stock_fisico_contado=StockQuantity("7.0000"),
            costo_unitario_ppp=MoneyAmount("500.00", currency="CLP"),
        )
        assert item2.is_surplus is True
        assert item2.diferencia_unidades.value == Decimal("2.0000")
        assert item2.valorizacion_diferencia.amount == Decimal("1000.00")

        # Sesión de conteo
        session = PhysicalCountSession(
            bodega_id=1,
            responsable_user_id=99,
            items=[item1, item2],
        )
        assert session.total_discrepancy_units().value == Decimal("0.0000")  # -2 + 2 = 0
        assert session.total_discrepancy_value().amount == Decimal("-1000.00")  # -2000 + 1000 = -1000

        # Transición a APROBADO
        session.transition_to("APROBADO", user_id=100)
        assert session.estado == "APROBADO"
        assert session.aprobador_user_id == 100

    def test_stock_transfer_anti_same_warehouse(self) -> None:
        # Transferencia válida
        transfer = StockTransfer(
            transfer_uuid=uuid4(),
            bodega_origen_id=1,
            bodega_destino_id=2,
            solicitante_user_id=10,
        )
        assert transfer.bodega_origen_id == 1
        assert transfer.bodega_destino_id == 2

        # Transferencia a la misma bodega prohibida
        with pytest.raises(TransferSameWarehouseError) as exc_info:
            StockTransfer(
                transfer_uuid=uuid4(),
                bodega_origen_id=1,
                bodega_destino_id=1,
                solicitante_user_id=10,
            )
        assert exc_info.value.default_error_code == "TRANSFER_SAME_WAREHOUSE_FORBIDDEN"

    def test_kardex_movement_entity_validation(self) -> None:
        movement = KardexMovement(
            producto_id=1,
            bodega_id=2,
            tipo_movimiento=MovementType.COMPRA,
            cantidad=StockQuantity("100.0000"),
            saldo_resultante=StockQuantity("150.0000"),
            costo_unitario_ppp=MoneyAmount("250.00", currency="CLP"),
            costo_total_movimiento=MoneyAmount("25000.00", currency="CLP"),
            actor_user_id=42,
        )
        assert movement.tipo_movimiento == MovementType.COMPRA
        assert movement.cantidad == StockQuantity("100.0000")

        # Fallos de validación en KardexMovement
        with pytest.raises(ValueError, match="Invalid producto_id"):
            KardexMovement(
                producto_id=0,
                bodega_id=1,
                tipo_movimiento=MovementType.ENTRADA,
                cantidad=StockQuantity("1.0000"),
                saldo_resultante=StockQuantity("1.0000"),
                costo_unitario_ppp=MoneyAmount(10),
                costo_total_movimiento=MoneyAmount(10),
                actor_user_id=1,
            )

    def test_apply_movement_function(self) -> None:
        balance = StockQuantity("50.0000")

        # Entrada
        new_bal = apply_movement(balance, MovementType.ENTRADA, "25.0000")
        assert new_bal == Decimal("75.0000")

        # Salida
        new_bal = apply_movement(balance, MovementType.SALIDA, "20.0000")
        assert new_bal == Decimal("30.0000")

        # Salida insuficiente
        with pytest.raises(InsufficientStockError):
            apply_movement(balance, MovementType.CONSUMO, "60.0000")

        # Movimiento inválido
        with pytest.raises(InvalidMovementTypeError):
            apply_movement(balance, "MOVIMIENTO_FALSO", "10.0000")

