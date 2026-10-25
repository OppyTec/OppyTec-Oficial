"""
oppytec-backend/src/modules/inventory/domain/kardex_math.py
Matemática pura del Kardex: orden canónico de locks (ORDER BY id ASC FOR UPDATE), saldo atómico,
FEFO y umbral de aprobación de mermas. Solo `Decimal`.
Cumple Regla Inmutable 02 (Clean Architecture: 0 imports de infraestructura).
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from src.modules.inventory.domain.entities import (
    KardexMovement,
    PhysicalCountItem,
    PhysicalCountSession,
    StockItem,
    StockTransfer,
)
from src.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    InvalidMovementTypeError,
    InventoryDomainError,
    NegativeStockNotAllowedError,
    TransferSameWarehouseError,
)
from src.modules.inventory.domain.value_objects import (
    ENTRY_MOVEMENTS,
    EXIT_MOVEMENTS,
    MONEY_QUANT,
    QTY_QUANT,
    MoneyAmount,
    MovementType,
    StockQuantity,
    StorageLocation,
)

ZERO = Decimal(0)
HUNDRED = Decimal(100)
DEFAULT_IVA_PCT = Decimal(19)

COST_QUANT = Decimal("0.0001")
PERCENT_QUANT = Decimal("0.01")
INTEGER_QUANT = Decimal("1")
TURNOVER_QUANT = Decimal("0.1")


def canonical_lock_order(ids: Iterable[int]) -> list[int]:
    """Orden determinista `ORDER BY id ASC` (sin duplicados) para evitar deadlocks en FOR UPDATE."""
    return sorted(set(ids))


def apply_movement(
    balance: Decimal | StockQuantity,
    movement_type: MovementType | str,
    quantity: Decimal | StockQuantity | str | int,
) -> Decimal:
    """Calcula el saldo resultante; las salidas no pueden dejar saldo negativo."""
    dec_balance = balance.value if isinstance(balance, StockQuantity) else Decimal(str(balance))
    dec_qty = quantity.value if isinstance(quantity, StockQuantity) else Decimal(str(quantity))

    if dec_qty <= ZERO:
        raise ValueError("movement quantity must be strictly positive")

    parsed_type = (
        MovementType.from_str(movement_type)
        if not isinstance(movement_type, MovementType)
        else movement_type
    )

    if parsed_type.value in ENTRY_MOVEMENTS:
        return dec_balance + dec_qty
    if parsed_type.value in EXIT_MOVEMENTS:
        result = dec_balance - dec_qty
        if result < ZERO:
            raise InsufficientStockError(
                "Insufficient stock for movement",
                context={"movement": parsed_type.value},
            )
        return result
    raise InvalidMovementTypeError(f"unknown movement type: {movement_type}")


@dataclass(frozen=True)
class StockLot:
    """Lote con vencimiento para política FEFO."""

    lot_id: int
    quantity: Decimal
    expires_on: date | None


@dataclass(frozen=True)
class LotAllocation:
    """Cantidad tomada de un lote."""

    lot_id: int
    quantity: Decimal


def fefo_sort(lots: Iterable[StockLot]) -> list[StockLot]:
    """
    Ordena lotes bajo política FEFO estricta:
    1. Lotes con fecha de caducidad más próxima primero.
    2. Lotes sin caducidad (`expires_on is None`) al final.
    3. Desempate determinista por `lot_id` ascendente.
    """
    return sorted(
        lots,
        key=lambda lot: (lot.expires_on is None, lot.expires_on or date.max, lot.lot_id),
    )


def fefo_allocate(lots: Sequence[StockLot], required: Decimal | StockQuantity) -> list[LotAllocation]:
    """First-Expired-First-Out: consume primero los lotes que vencen antes (sin fecha al final)."""
    req_dec = required.value if isinstance(required, StockQuantity) else required
    if req_dec <= ZERO:
        raise ValueError("required quantity must be strictly positive")
    ordered = fefo_sort(lot for lot in lots if lot.quantity > ZERO)
    remaining = req_dec
    out: list[LotAllocation] = []
    for lot in ordered:
        if remaining <= ZERO:
            break
        take = min(lot.quantity, remaining)
        out.append(LotAllocation(lot.lot_id, take))
        remaining -= take
    if remaining > ZERO:
        raise InsufficientStockError("Insufficient lots for FEFO allocation")
    return out


def waste_requires_approval(total_cost: Decimal, threshold: Decimal) -> bool:
    """Una merma cuyo costo total supera estrictamente el umbral exige aprobación."""
    return total_cost > threshold


def waste_total_cost(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    """Valoración financiera de una merma."""
    return (quantity * unit_cost).quantize(MONEY_QUANT, ROUND_HALF_UP)


# ============================================================================
# FÓRMULAS OFICIALES DE PARIDAD CON LEGACY (GESTIÓN, CATÁLOGO Y KARDEX)
# ============================================================================


@dataclass(frozen=True)
class PurchaseLayer:
    """Capa de compra histórica para valorización dinámica FIFO/FEFO y PPP."""

    quantity: Decimal
    unit_cost: Decimal

    def __post_init__(self) -> None:
        if self.quantity < ZERO:
            raise ValueError("purchase quantity must be non-negative")
        if self.unit_cost < ZERO:
            raise ValueError("purchase unit cost must be non-negative")


def calculate_inventory_ppp(
    stock_actual: Decimal,
    purchases: Sequence[PurchaseLayer],
    base_cost: Decimal = ZERO,
    last_cost: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """
    Valorización de inventario neto y Costo PPP Unitario por capas dinámicas (FIFO/FEFO).
    Paridad 1:1 con `catalog_service.py` y `PRODUCTOS_Y_COSTOS_SPEC.md` de OppyTec-Legacy:
    - Retorna tupla (valor_inventario_neto, costo_unitario_ppp).
    - Si stock_actual <= 0: (0.00, last_cost o base_cost).
    - Si no hay compras: (stock_actual * base_cost, base_cost).
    - Con compras: consume capas recientes hasta cubrir stock_actual (y base_cost para remanente).
    """
    if stock_actual <= ZERO:
        effective_cost = last_cost if last_cost is not None else base_cost
        return (ZERO.quantize(MONEY_QUANT), effective_cost.quantize(COST_QUANT, ROUND_HALF_UP))

    if not purchases:
        val_inv = (stock_actual * base_cost).quantize(MONEY_QUANT, ROUND_HALF_UP)
        return (val_inv, base_cost.quantize(COST_QUANT, ROUND_HALF_UP))

    remaining = stock_actual
    val_total = ZERO
    units_covered = ZERO

    for item in purchases:
        if remaining <= ZERO:
            break
        if item.quantity <= ZERO or item.unit_cost <= ZERO:
            continue
        take = min(remaining, item.quantity)
        val_total += take * item.unit_cost
        units_covered += take
        remaining -= take

    if remaining > ZERO:
        val_total += remaining * base_cost
        units_covered += remaining

    costo_ppp = (
        (val_total / units_covered).quantize(COST_QUANT, ROUND_HALF_UP)
        if units_covered > ZERO
        else base_cost.quantize(COST_QUANT, ROUND_HALF_UP)
    )
    valor_inv = val_total.quantize(MONEY_QUANT, ROUND_HALF_UP)
    return (valor_inv, costo_ppp)


def calculate_weighted_average_cost(
    current_qty: Decimal,
    current_avg_cost: Decimal,
    incoming_qty: Decimal,
    incoming_unit_cost: Decimal,
) -> Decimal:
    """
    Costo Promedio Ponderado (PPP / WACC) tras recepción de compra:
    (stock * costo_actual + entrada * costo_entrada) / (stock + entrada).
    """
    if incoming_qty < ZERO:
        raise ValueError("incoming quantity must be non-negative")
    base_qty = max(current_qty, ZERO)
    total_qty = base_qty + incoming_qty
    if total_qty == ZERO:
        return current_avg_cost.quantize(COST_QUANT, ROUND_HALF_UP)
    total_value = base_qty * current_avg_cost + incoming_qty * incoming_unit_cost
    return (total_value / total_qty).quantize(COST_QUANT, ROUND_HALF_UP)


def calculate_moving_average_10(
    purchase_unit_costs: Sequence[Decimal],
    fallback_cost: Decimal = ZERO,
) -> Decimal:
    """
    Costo Promedio Histórico de las últimas 10 compras (o las existentes si < 10).
    Paridad 1:1 con `avg_10_stmt` de OppyTec-Legacy.
    """
    valid_costs = [c for c in purchase_unit_costs[:10] if c > ZERO]
    if not valid_costs:
        return fallback_cost.quantize(COST_QUANT, ROUND_HALF_UP)
    avg = sum(valid_costs, ZERO) / Decimal(len(valid_costs))
    return avg.quantize(COST_QUANT, ROUND_HALF_UP)


def calculate_food_cost_pct(
    costo_bruto: Decimal,
    precio_venta_bruto: Decimal,
) -> Decimal:
    """
    Food Cost % oficial: (costo_bruto / precio_venta_bruto) * 100.
    """
    if precio_venta_bruto <= ZERO:
        raise ValueError("precio_venta_bruto must be strictly positive")
    return ((costo_bruto / precio_venta_bruto) * HUNDRED).quantize(PERCENT_QUANT, ROUND_HALF_UP)


def calculate_gross_margin_pct(
    precio_venta_bruto: Decimal,
    costo_bruto: Decimal,
) -> Decimal:
    """
    Margen Bruto % oficial: ((precio_venta_bruto - costo_bruto) / precio_venta_bruto) * 100.
    Invariante: Margen Bruto % + Food Cost % = 100%.
    """
    if precio_venta_bruto <= ZERO:
        raise ValueError("precio_venta_bruto must be strictly positive")
    return (((precio_venta_bruto - costo_bruto) / precio_venta_bruto) * HUNDRED).quantize(
        PERCENT_QUANT, ROUND_HALF_UP
    )


def calculate_net_margin_pct(
    precio_venta_neto: Decimal,
    costo_neto: Decimal,
) -> Decimal:
    """
    Margen Neto % oficial: ((precio_venta_neto - costo_neto) / precio_venta_neto) * 100.
    """
    if precio_venta_neto <= ZERO:
        raise ValueError("precio_venta_neto must be strictly positive")
    return (((precio_venta_neto - costo_neto) / precio_venta_neto) * HUNDRED).quantize(
        PERCENT_QUANT, ROUND_HALF_UP
    )


def calculate_inflation_variance_pct(
    ultimo_costo: Decimal,
    penultimo_costo: Decimal,
) -> Decimal:
    """
    Variación Inflacionaria % oficial: ((ultimo_costo - penultimo_costo) / penultimo_costo) * 100.
    Exige penultimo_costo estrictamente positivo.
    """
    if penultimo_costo <= ZERO:
        raise ValueError("penultimo_costo must be strictly positive")
    return (((ultimo_costo - penultimo_costo) / penultimo_costo) * HUNDRED).quantize(
        PERCENT_QUANT, ROUND_HALF_UP
    )


def calculate_days_of_coverage(
    stock_actual: Decimal,
    consumo_diario_promedio: Decimal,
) -> Decimal:
    """
    Días de Cobertura oficial:
    - Si consumo_diario_promedio > 0: round(stock_actual / consumo_diario_promedio).
    - Si consumo_diario_promedio <= 0 y stock_actual > 0: 30 días (fallback estándar legacy).
    - En cualquier otro caso: 0 días.
    """
    if consumo_diario_promedio > ZERO:
        return (stock_actual / consumo_diario_promedio).quantize(INTEGER_QUANT, ROUND_HALF_UP)
    if stock_actual > ZERO:
        return Decimal(30)
    return ZERO


def calculate_monthly_turnover_index(
    unidades_vendidas_mes: Decimal,
    stock_actual: Decimal,
) -> Decimal:
    """
    Índice de Rotación Mensual oficial:
    unidades_vendidas_mes / max(stock_actual, 1).
    """
    divisor = stock_actual if stock_actual > ZERO else Decimal(1)
    return (unidades_vendidas_mes / divisor).quantize(TURNOVER_QUANT, ROUND_HALF_UP)


def gross_from_net(
    net_amount: Decimal,
    iva_pct: Decimal = DEFAULT_IVA_PCT,
    as_clp_integer: bool = False,
) -> Decimal:
    """
    Conversión Neto a Bruto con IVA: neto * (1 + iva/100).
    Si as_clp_integer=True, redondea al peso entero más cercano (moneda legal CLP).
    """
    multiplier = Decimal(1) + (iva_pct / HUNDRED)
    gross = net_amount * multiplier
    if as_clp_integer:
        return gross.quantize(INTEGER_QUANT, ROUND_HALF_UP)
    return gross.quantize(MONEY_QUANT, ROUND_HALF_UP)


def net_from_gross(
    gross_amount: Decimal,
    iva_pct: Decimal = DEFAULT_IVA_PCT,
    as_clp_integer: bool = False,
) -> Decimal:
    """
    Conversión Bruto a Neto con IVA: bruto / (1 + iva/100).
    Si as_clp_integer=True, redondea al peso entero más cercano.
    """
    multiplier = Decimal(1) + (iva_pct / HUNDRED)
    net = gross_amount / multiplier
    if as_clp_integer:
        return net.quantize(INTEGER_QUANT, ROUND_HALF_UP)
    return net.quantize(MONEY_QUANT, ROUND_HALF_UP)


def packaging_cost(
    unit_cost: Decimal,
    units_per_package: Decimal,
) -> Decimal:
    """
    Costo de embalaje = unit_cost * units_per_package.
    """
    if units_per_package <= ZERO:
        raise ValueError("units_per_package must be strictly positive")
    return (unit_cost * units_per_package).quantize(COST_QUANT, ROUND_HALF_UP)


calculate_gross_amount = gross_from_net
calculate_net_amount = net_from_gross
calculate_packaging_cost = packaging_cost

__all__ = [
    "COST_QUANT",
    "DEFAULT_IVA_PCT",
    "ENTRY_MOVEMENTS",
    "EXIT_MOVEMENTS",
    "HUNDRED",
    "INTEGER_QUANT",
    "MONEY_QUANT",
    "PERCENT_QUANT",
    "QTY_QUANT",
    "TURNOVER_QUANT",
    "ZERO",
    "InsufficientStockError",
    "InvalidMovementTypeError",
    "InventoryDomainError",
    "KardexMovement",
    "LotAllocation",
    "MoneyAmount",
    "MovementType",
    "NegativeStockNotAllowedError",
    "PhysicalCountItem",
    "PhysicalCountSession",
    "PurchaseLayer",
    "StockItem",
    "StockLot",
    "StockQuantity",
    "StockTransfer",
    "StorageLocation",
    "TransferSameWarehouseError",
    "apply_movement",
    "calculate_days_of_coverage",
    "calculate_food_cost_pct",
    "calculate_gross_amount",
    "calculate_gross_margin_pct",
    "calculate_inflation_variance_pct",
    "calculate_inventory_ppp",
    "calculate_monthly_turnover_index",
    "calculate_moving_average_10",
    "calculate_net_amount",
    "calculate_net_margin_pct",
    "calculate_packaging_cost",
    "calculate_weighted_average_cost",
    "canonical_lock_order",
    "fefo_allocate",
    "fefo_sort",
    "gross_from_net",
    "net_from_gross",
    "packaging_cost",
    "waste_requires_approval",
    "waste_total_cost",
]
