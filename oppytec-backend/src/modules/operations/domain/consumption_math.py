"""
oppytec-backend/src/modules/operations/domain/consumption_math.py
Matemática pura y Value Objects de consumo, explosión de recetas, FEFO y costeo de buffet.
Cumple Regla de Oro Inviolable:
- Cero float (IEEE 754 estrictamente prohibido, solo Decimal e int).
- Precisión Decimal(12, 4) para cantidades y Decimal(14, 2) para importes monetarios.
- Inmutabilidad estricta y Clean Architecture (cero dependencias de infraestructura).
- Errores canónicos RFC 7807 (InsufficientStockError, DomainValidationError).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.core.exceptions import DomainValidationError, InsufficientStockError

QTY_QUANT = Decimal("0.0001")
MONEY_QUANT = Decimal("0.01")
ZERO = Decimal(0)


# ============================================================================
# 1. VALUE OBJECTS INMUTABLES
# ============================================================================


@dataclass(frozen=True)
class ConsumptionQuantity:
    """
    Cantidad de consumo inmutable cuantizada a 4 decimales (0.0001).
    Prohíbe estrictamente el tipo float (IEEE 754) para evitar pérdida de precisión.
    """

    value: Decimal
    allow_negative: bool = False

    def __init__(
        self,
        value: Decimal | int | str | ConsumptionQuantity,
        allow_negative: bool = False,
    ) -> None:
        if isinstance(value, bool):
            raise TypeError("Boolean is forbidden for ConsumptionQuantity")
        if type(value).__name__ == "float":
            raise TypeError(
                "Float precision IEEE-754 is strictly forbidden for ConsumptionQuantity; use Decimal, int, or str"
            )

        if isinstance(value, ConsumptionQuantity):
            dec_val = value.value
        elif isinstance(value, Decimal):
            dec_val = value
        elif isinstance(value, (int, str)):
            try:
                dec_val = Decimal(str(value))
            except Exception as exc:
                raise ValueError(f"Invalid decimal representation for ConsumptionQuantity: {value}") from exc
        else:
            raise TypeError(f"Unsupported type for ConsumptionQuantity: {type(value).__name__}")

        if dec_val.is_nan() or dec_val.is_infinite():
            raise ValueError(f"ConsumptionQuantity cannot be NaN or infinite: {dec_val}")

        quantized = dec_val.quantize(QTY_QUANT, ROUND_HALF_UP)
        if not allow_negative and quantized < ZERO:
            raise DomainValidationError(
                f"ConsumptionQuantity cannot be negative: {quantized}",
                context={"quantity": str(quantized)},
            )

        object.__setattr__(self, "value", quantized)
        object.__setattr__(self, "allow_negative", allow_negative)

    @classmethod
    def zero(cls, allow_negative: bool = False) -> ConsumptionQuantity:
        """Crea una instancia con valor 0.0000."""
        return cls(ZERO, allow_negative=allow_negative)

    def to_decimal(self) -> Decimal:
        """Retorna el valor encapsulado en Decimal puro."""
        return self.value

    def is_zero(self) -> bool:
        """Indica si la cantidad es exactamente 0.0000."""
        return self.value == ZERO

    def is_positive(self) -> bool:
        """Indica si la cantidad es estrictamente mayor a 0."""
        return self.value > ZERO

    def is_negative(self) -> bool:
        """Indica si la cantidad es estrictamente menor a 0."""
        return self.value < ZERO

    def __repr__(self) -> str:
        return f"ConsumptionQuantity('{self.value}')"

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ConsumptionQuantity):
            return self.value == other.value
        if isinstance(other, (Decimal, int, str)) and not isinstance(other, bool):
            try:
                return self.value == ConsumptionQuantity(other, allow_negative=True).value
            except Exception:
                return False
        return False

    def __lt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else ConsumptionQuantity(other, allow_negative=True).value
        return self.value < other_val

    def __le__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else ConsumptionQuantity(other, allow_negative=True).value
        return self.value <= other_val

    def __gt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else ConsumptionQuantity(other, allow_negative=True).value
        return self.value > other_val

    def __ge__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else ConsumptionQuantity(other, allow_negative=True).value
        return self.value >= other_val

    def __add__(self, other: ConsumptionQuantity | Decimal | int | str) -> ConsumptionQuantity:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else ConsumptionQuantity(other, allow_negative=True).value
        return ConsumptionQuantity(self.value + other_val, allow_negative=self.allow_negative)

    def __radd__(self, other: ConsumptionQuantity | Decimal | int | str) -> ConsumptionQuantity:
        return self.__add__(other)

    def __sub__(self, other: ConsumptionQuantity | Decimal | int | str) -> ConsumptionQuantity:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else ConsumptionQuantity(other, allow_negative=True).value
        result = self.value - other_val
        if not self.allow_negative and result < ZERO:
            raise InsufficientStockError(
                f"Insufficient stock: current balance {self.value} is less than required {other_val}",
                context={"current": str(self.value), "required": str(other_val)},
            )
        return ConsumptionQuantity(result, allow_negative=self.allow_negative)

    def __mul__(self, other: ConsumptionQuantity | Decimal | int | str) -> ConsumptionQuantity:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else Decimal(str(other))
        return ConsumptionQuantity(self.value * other_val, allow_negative=self.allow_negative)

    def __rmul__(self, other: ConsumptionQuantity | Decimal | int | str) -> ConsumptionQuantity:
        return self.__mul__(other)

    def __truediv__(self, other: ConsumptionQuantity | Decimal | int | str) -> ConsumptionQuantity:
        other_val = other.value if isinstance(other, ConsumptionQuantity) else Decimal(str(other))
        if other_val == ZERO:
            raise ZeroDivisionError("Cannot divide ConsumptionQuantity by zero")
        return ConsumptionQuantity(self.value / other_val, allow_negative=self.allow_negative)


@dataclass(frozen=True)
class PaxCount:
    """
    Conteo inmutable de comensales en servicio de buffet o eventos (entero >= 0).
    """

    value: int

    def __init__(self, value: int | str | PaxCount) -> None:
        if isinstance(value, bool):
            raise TypeError("Boolean is forbidden for PaxCount")
        if type(value).__name__ == "float":
            raise TypeError("Float is forbidden for PaxCount; use int or integer str")

        if isinstance(value, PaxCount):
            int_val = value.value
        elif isinstance(value, int):
            int_val = value
        elif isinstance(value, str):
            try:
                int_val = int(value.strip())
            except Exception as exc:
                raise ValueError(f"Invalid integer representation for PaxCount: {value}") from exc
        else:
            raise TypeError(f"Unsupported type for PaxCount: {type(value).__name__}")

        if int_val < 0:
            raise ValueError(f"PaxCount cannot be negative: {int_val}")

        object.__setattr__(self, "value", int_val)

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f"PaxCount({self.value})"

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PaxCount):
            return self.value == other.value
        if isinstance(other, int) and not isinstance(other, bool):
            return self.value == other
        return False

    def __lt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PaxCount) else int(other)
        return self.value < other_val

    def __le__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PaxCount) else int(other)
        return self.value <= other_val

    def __gt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PaxCount) else int(other)
        return self.value > other_val

    def __ge__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PaxCount) else int(other)
        return self.value >= other_val

    def __add__(self, other: PaxCount | int) -> PaxCount:
        other_val = other.value if isinstance(other, PaxCount) else PaxCount(other).value
        return PaxCount(self.value + other_val)

    def __radd__(self, other: PaxCount | int) -> PaxCount:
        return self.__add__(other)

    def __sub__(self, other: PaxCount | int) -> PaxCount:
        other_val = other.value if isinstance(other, PaxCount) else PaxCount(other).value
        diff = self.value - other_val
        if diff < 0:
            raise ValueError(f"PaxCount subtraction would result in negative count: {diff}")
        return PaxCount(diff)


@dataclass(frozen=True)
class BuffetPaxCost:
    """
    Costo unitario por comensal (Pax) inmutable cuantizado a 2 decimales (0.01).
    Prohíbe estrictamente el tipo float.
    """

    value: Decimal

    def __init__(self, value: Decimal | int | str | BuffetPaxCost) -> None:
        if isinstance(value, bool):
            raise TypeError("Boolean is forbidden for BuffetPaxCost")
        if type(value).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden for BuffetPaxCost; use Decimal, int, or str")

        if isinstance(value, BuffetPaxCost):
            dec_val = value.value
        elif isinstance(value, Decimal):
            dec_val = value
        elif isinstance(value, (int, str)):
            try:
                dec_val = Decimal(str(value))
            except Exception as exc:
                raise ValueError(f"Invalid decimal string for BuffetPaxCost: {value}") from exc
        else:
            raise TypeError(f"Unsupported type for BuffetPaxCost: {type(value).__name__}")

        if dec_val.is_nan() or dec_val.is_infinite():
            raise ValueError(f"BuffetPaxCost cannot be NaN or infinite: {dec_val}")

        quantized = dec_val.quantize(MONEY_QUANT, ROUND_HALF_UP)
        if quantized < ZERO:
            raise ValueError(f"BuffetPaxCost cannot be negative: {quantized}")

        object.__setattr__(self, "value", quantized)

    @classmethod
    def zero(cls) -> BuffetPaxCost:
        """Crea una instancia con costo 0.00."""
        return cls(ZERO)

    def to_decimal(self) -> Decimal:
        """Retorna el valor encapsulado en Decimal puro."""
        return self.value

    def __repr__(self) -> str:
        return f"BuffetPaxCost('{self.value}')"

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BuffetPaxCost):
            return self.value == other.value
        if isinstance(other, (Decimal, int, str)) and not isinstance(other, bool):
            try:
                return self.value == BuffetPaxCost(other).value
            except Exception:
                return False
        return False

    def __lt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, BuffetPaxCost) else BuffetPaxCost(other).value
        return self.value < other_val

    def __le__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, BuffetPaxCost) else BuffetPaxCost(other).value
        return self.value <= other_val

    def __gt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, BuffetPaxCost) else BuffetPaxCost(other).value
        return self.value > other_val

    def __ge__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, BuffetPaxCost) else BuffetPaxCost(other).value
        return self.value >= other_val


# ============================================================================
# 2. EXPLOSIÓN DE RECETAS A INSUMOS
# ============================================================================


@dataclass(frozen=True)
class RecipeIngredientItem:
    """Línea de ingrediente de una receta base."""

    ingredient_id: int | str
    quantity: Decimal
    waste_pct: Decimal = ZERO

    def __post_init__(self) -> None:
        if type(self.quantity).__name__ == "float" or type(self.waste_pct).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden; use Decimal")
        if self.quantity < ZERO:
            raise ValueError("ingredient quantity cannot be negative")
        if self.waste_pct < ZERO:
            raise ValueError("waste_pct cannot be negative")


@dataclass(frozen=True)
class RecipeSpec:
    """Especificación de una receta con sus porciones (yield) e ingredientes."""

    recipe_id: int | str
    yield_portions: Decimal = Decimal(1)
    ingredients: Sequence[RecipeIngredientItem] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if type(self.yield_portions).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden; use Decimal")
        if self.yield_portions <= ZERO:
            raise ValueError("yield_portions must be strictly positive")


@dataclass(frozen=True)
class RecipeConsumptionItem:
    """Ítem a consumir: receta y cantidad de porciones a descontar."""

    recipe_id: int | str
    portions: Decimal

    def __post_init__(self) -> None:
        if type(self.portions).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden; use Decimal")
        if self.portions <= ZERO:
            raise ValueError("portions must be strictly positive")


def explode_recipe_consumption(
    items: Sequence[RecipeConsumptionItem] | Mapping[int | str, Decimal | ConsumptionQuantity],
    recipes: Mapping[int | str, RecipeSpec | Mapping[int | str, Decimal]],
) -> dict[int | str, ConsumptionQuantity]:
    """
    Axioma 1: Consumo por explosión de recetas.
    Por cada unidad de receta consumida, se descuenta:
    (insumo_qty * (1 + waste_pct / 100) * cantidad) / porciones.
    Retorna un diccionario de {ingredient_id: ConsumptionQuantity}.
    """
    totals: dict[int | str, ConsumptionQuantity] = {}

    # Normalizar items
    consumption_list: list[RecipeConsumptionItem] = []
    if isinstance(items, Mapping):
        for rec_id, portions in items.items():
            dec_portions = portions.value if isinstance(portions, ConsumptionQuantity) else Decimal(str(portions))
            consumption_list.append(RecipeConsumptionItem(rec_id, dec_portions))
    else:
        consumption_list = list(items)

    for item in consumption_list:
        if item.recipe_id not in recipes:
            raise KeyError(f"Recipe spec not found for recipe_id: {item.recipe_id}")

        spec = recipes[item.recipe_id]

        if isinstance(spec, RecipeSpec):
            yield_p = spec.yield_portions
            for ing in spec.ingredients:
                gross_factor = Decimal(1) + (ing.waste_pct / Decimal(100))
                unit_consumption = (ing.quantity * gross_factor) / yield_p
                total_line = unit_consumption * item.portions
                line_cq = ConsumptionQuantity(total_line)
                totals[ing.ingredient_id] = totals.get(ing.ingredient_id, ConsumptionQuantity.zero()) + line_cq
        elif isinstance(spec, Mapping):
            # Formato simple compatible con legacy {ingredient_id: Decimal_per_portion}
            for ing_id, qty in spec.items():
                dec_qty = Decimal(str(qty))
                if dec_qty < ZERO:
                    raise ValueError("ingredient quantity cannot be negative")
                line_cq = ConsumptionQuantity(dec_qty * item.portions)
                totals[ing_id] = totals.get(ing_id, ConsumptionQuantity.zero()) + line_cq
        else:
            raise TypeError(f"Unsupported recipe spec type: {type(spec).__name__}")

    return totals


# ============================================================================
# 3. DEDUCCIÓN ESTRICTA FEFO (First-Expired, First-Out)
# ============================================================================


@dataclass(frozen=True)
class ConsumptionLot:
    """Lote de inventario con fecha de caducidad para política FEFO."""

    lot_id: int | str
    quantity: Decimal
    expires_on: date | None = None

    def __post_init__(self) -> None:
        if type(self.quantity).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden; use Decimal")
        if self.quantity < ZERO:
            raise ValueError("lot quantity cannot be negative")


@dataclass(frozen=True)
class LotDeduction:
    """Asignación de deducción a un lote específico."""

    lot_id: int | str
    deducted_quantity: ConsumptionQuantity
    remaining_quantity: ConsumptionQuantity


def sort_lots_fefo(lots: Iterable[ConsumptionLot]) -> list[ConsumptionLot]:
    """
    Axioma 2: Ordenamiento determinista FEFO estricto:
    1. Lotes con fecha de caducidad más próxima primero (expires_on ASC).
    2. Lotes sin fecha de caducidad (expires_on is None) al final.
    3. Desempate determinista por lot_id ascendente.
    """
    return sorted(
        lots,
        key=lambda lot: (
            lot.expires_on is None,
            lot.expires_on or date.max,
            str(lot.lot_id),
        ),
    )


def deduct_lots_fefo(
    lots: Sequence[ConsumptionLot],
    required_quantity: Decimal | ConsumptionQuantity | str | int,
    *,
    allow_expired: bool = False,
    reference_date: date | None = None,
) -> tuple[list[LotDeduction], list[ConsumptionLot]]:
    """
    Deduce existencias de una lista de lotes bajo política FEFO.
    - Si allow_expired es False y se encuentra un lote vencido según reference_date,
      el lote vencido no se consume y se omite (o si no hay más stock, arroja InsufficientStockError).
    - Arroja InsufficientStockError si la suma disponible es inferior a required_quantity.
    - Retorna una tupla de (deducciones_realizadas, lotes_actualizados).
    """
    req_cq = (
        required_quantity
        if isinstance(required_quantity, ConsumptionQuantity)
        else ConsumptionQuantity(required_quantity)
    )

    if req_cq.is_zero() or req_cq.is_negative():
        raise ValueError("required quantity must be strictly positive")

    ref_date = reference_date or date.today()

    # Filtrar y ordenar
    available_lots: list[ConsumptionLot] = []
    for lot in lots:
        if lot.quantity <= ZERO:
            continue
        if not allow_expired and lot.expires_on is not None and lot.expires_on < ref_date:
            # Lote vencido omitido por regla de contingencia
            continue
        available_lots.append(lot)

    sorted_available = sort_lots_fefo(available_lots)

    remaining_needed = req_cq.value
    deductions: list[LotDeduction] = []
    updated_lots: list[ConsumptionLot] = []

    # Map para preservar lotes no afectados
    used_lot_ids = set()

    for lot in sorted_available:
        if remaining_needed <= ZERO:
            updated_lots.append(lot)
            used_lot_ids.add(lot.lot_id)
            continue

        take = min(lot.quantity, remaining_needed)
        new_qty = lot.quantity - take
        deduction = LotDeduction(
            lot_id=lot.lot_id,
            deducted_quantity=ConsumptionQuantity(take),
            remaining_quantity=ConsumptionQuantity(new_qty),
        )
        deductions.append(deduction)
        updated_lots.append(ConsumptionLot(lot_id=lot.lot_id, quantity=new_qty, expires_on=lot.expires_on))
        used_lot_ids.add(lot.lot_id)
        remaining_needed -= take

    if remaining_needed > ZERO:
        raise InsufficientStockError(
            f"Insufficient stock across lots: required {req_cq.value}, shortfall {remaining_needed}",
            context={"required": str(req_cq.value), "shortfall": str(remaining_needed)},
        )

    # Agregar lotes originales no tocados (ej. lotes con cantidad 0 o vencidos)
    for lot in lots:
        if lot.lot_id not in used_lot_ids:
            updated_lots.append(lot)

    return deductions, updated_lots


# ============================================================================
# 4. CONCILIACIÓN Y COSTEO POR PAX DE BUFFET
# ============================================================================


def calculate_buffet_pax_cost(
    total_montaje_cost: Decimal | BuffetPaxCost | str | int,
    pax: int | PaxCount | str,
    leftover_reusable_value: Decimal | BuffetPaxCost | str | int = ZERO,
) -> BuffetPaxCost:
    """
    Axioma 4: Conciliación de Buffet.
    costo_neto_pax = (costo_montaje - sobrante_reutilizable) / pax.
    - Cuantizado a 2 decimales (0.01) con ROUND_HALF_UP.
    - pax debe ser estrictamente > 0 (si pax == 0 arroja ValueError).
    - sobrante_reutilizable no puede exceder el costo de montaje ni ser negativo.
    """
    if type(total_montaje_cost).__name__ == "float" or type(leftover_reusable_value).__name__ == "float":
        raise TypeError("Float precision IEEE-754 is strictly forbidden for buffet cost calculation; use Decimal")

    cost_dec = (
        total_montaje_cost.value
        if isinstance(total_montaje_cost, BuffetPaxCost)
        else Decimal(str(total_montaje_cost))
    )
    leftover_dec = (
        leftover_reusable_value.value
        if isinstance(leftover_reusable_value, BuffetPaxCost)
        else Decimal(str(leftover_reusable_value))
    )

    if cost_dec < ZERO:
        raise ValueError("total_montaje_cost cannot be negative")
    if leftover_dec < ZERO:
        raise ValueError("leftover_reusable_value cannot be negative")
    if leftover_dec > cost_dec:
        raise ValueError(
            f"leftover_reusable_value ({leftover_dec}) cannot exceed total_montaje_cost ({cost_dec})"
        )

    pax_obj = pax if isinstance(pax, PaxCount) else PaxCount(pax)
    if pax_obj.value <= 0:
        raise ValueError("pax must be strictly positive for buffet cost calculation")

    net_cost = cost_dec - leftover_dec
    unit_cost = (net_cost / Decimal(pax_obj.value)).quantize(MONEY_QUANT, ROUND_HALF_UP)
    return BuffetPaxCost(unit_cost)
