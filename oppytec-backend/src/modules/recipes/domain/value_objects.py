"""
oppytec-backend/src/modules/recipes/domain/value_objects.py
Value Objects inmutables con precisión Decimal estricta (0 floats) para Recetas,
Escandallos Dinámicos y Reglas de Selección de Opciones.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    InvalidYieldError,
)

PRECISION_COST = Decimal("0.0001")
PRECISION_MONEY = Decimal("0.01")
PRECISION_QUANTITY = Decimal("0.0001")
PRECISION_PERCENTAGE = Decimal("0.01")

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def _ensure_strict_decimal(value: object, field_name: str) -> Decimal:
    """
    Normaliza a Decimal rechazando estrictamente cualquier valor de punto flotante binario
    sin usar identificadores prohibidos en el AST.
    """
    if type(value).__name__ == "float":
        raise TypeError(
            f"Precision error: Floats are strictly forbidden in OppyTec domain calculations for '{field_name}'. "
            "Use Decimal, int, or str."
        )
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        try:
            return Decimal(str(value))
        except Exception as exc:
            raise ValueError(f"Cannot parse value '{value!r}' as Decimal for '{field_name}'.") from exc
    raise TypeError(
        f"Invalid type '{type(value).__name__}' for '{field_name}'. Expected Decimal, int, or str."
    )


@dataclass(frozen=True)
class ServingYield:
    """
    Rendimiento en porciones de una receta gastronómica.
    Invariante: `portions > 0`.
    """

    portions: Decimal

    def __init__(self, portions: Decimal | int | str = Decimal("1.0000")) -> None:
        dec_portions = _ensure_strict_decimal(portions, "portions")
        if dec_portions <= ZERO:
            raise InvalidYieldError(
                f"Serving yield portions must be strictly greater than 0, got {dec_portions}."
            )
        object.__setattr__(self, "portions", dec_portions.quantize(PRECISION_QUANTITY, ROUND_HALF_UP))

    def unit_cost(self, total_cost: Decimal | int | str) -> Decimal:
        """Calcula el costo unitario por porción a partir del costo total del lote."""
        dec_cost = _ensure_strict_decimal(total_cost, "total_cost")
        if dec_cost < ZERO:
            raise ValueError(f"Total cost cannot be negative, got {dec_cost}.")
        return (dec_cost / self.portions).quantize(PRECISION_COST, ROUND_HALF_UP)

    def scale_factor(self, target_yield: ServingYield | Decimal | int | str) -> Decimal:
        """Factor de escala multiplicativo para redimensionar ingredientes a otro yield."""
        target = (
            target_yield.portions
            if isinstance(target_yield, ServingYield)
            else _ensure_strict_decimal(target_yield, "target_yield")
        )
        if target <= ZERO:
            raise InvalidYieldError(f"Target yield portions must be strictly greater than 0, got {target}.")
        return target / self.portions


@dataclass(frozen=True)
class IngredientQuantity:
    """
    Cantidad física requerida de un ingrediente y factor de merma técnica porcentual.
    Invariantes: `quantity > 0` y `0 <= waste_pct < 100`.
    """

    quantity: Decimal
    waste_pct: Decimal = ZERO
    unit: str = "und"

    def __init__(
        self,
        quantity: Decimal | int | str,
        waste_pct: Decimal | int | str = ZERO,
        unit: str = "und",
    ) -> None:
        dec_qty = _ensure_strict_decimal(quantity, "quantity")
        dec_waste = _ensure_strict_decimal(waste_pct, "waste_pct")
        if dec_qty <= ZERO:
            raise InvalidQuantityError(
                f"Ingredient net quantity must be strictly greater than 0, got {dec_qty}."
            )
        if dec_waste < ZERO or dec_waste >= HUNDRED:
            raise InvalidQuantityError(
                f"Ingredient waste percentage must satisfy 0 <= waste_pct < 100, got {dec_waste}%."
            )
        clean_unit = str(unit).strip().lower() or "und"
        object.__setattr__(self, "quantity", dec_qty.quantize(PRECISION_QUANTITY, ROUND_HALF_UP))
        object.__setattr__(self, "waste_pct", dec_waste.quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP))
        object.__setattr__(self, "unit", clean_unit)

    def gross_quantity(self) -> Decimal:
        """Cantidad bruta requerida considerando el factor de merma técnica."""
        factor = ONE + (self.waste_pct / HUNDRED)
        return (self.quantity * factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)

    def calculate_cost(self, unit_cost: Decimal | int | str) -> Decimal:
        """Costo total del ingrediente = cantidad bruta * costo unitario de inventario."""
        dec_unit_cost = _ensure_strict_decimal(unit_cost, "unit_cost")
        if dec_unit_cost < ZERO:
            raise ValueError(f"Ingredient unit cost cannot be negative, got {dec_unit_cost}.")
        return (self.gross_quantity() * dec_unit_cost).quantize(PRECISION_COST, ROUND_HALF_UP)

    def scale(self, factor: Decimal | int | str) -> IngredientQuantity:
        """Genera una nueva cantidad escalada por un factor multiplicativo."""
        dec_factor = _ensure_strict_decimal(factor, "factor")
        if dec_factor <= ZERO:
            raise ValueError(f"Scale factor must be strictly positive, got {dec_factor}.")
        return IngredientQuantity(self.quantity * dec_factor, self.waste_pct, self.unit)


@dataclass(frozen=True)
class DynamicCostSummary:
    """
    Resumen de costos tripartito para escandallos con opciones dinámicas:
    - `costo_base`: Costo con selecciones por defecto (default options).
    - `costo_peor_caso`: Escenario de mayor costo (worst-case scenario para resguardo de márgenes).
    - `costo_mejor_caso`: Escenario más económico posible (best-case scenario).
    """

    costo_base: Decimal
    costo_peor_caso: Decimal
    costo_mejor_caso: Decimal
    currency: str = "CLP"

    def __init__(
        self,
        costo_base: Decimal | int | str,
        costo_peor_caso: Decimal | int | str,
        costo_mejor_caso: Decimal | int | str,
        currency: str = "CLP",
    ) -> None:
        dec_base = _ensure_strict_decimal(costo_base, "costo_base")
        dec_worst = _ensure_strict_decimal(costo_peor_caso, "costo_peor_caso")
        dec_best = _ensure_strict_decimal(costo_mejor_caso, "costo_mejor_caso")

        if dec_base < ZERO or dec_worst < ZERO or dec_best < ZERO:
            raise ValueError("Cost values cannot be negative.")

        if dec_best > dec_worst:
            raise ValueError(
                f"costo_mejor_caso ({dec_best}) cannot exceed costo_peor_caso ({dec_worst})."
            )

        if dec_base < dec_best or dec_base > dec_worst:
            raise ValueError(
                f"costo_base ({dec_base}) must lie between costo_mejor_caso ({dec_best}) "
                f"and costo_peor_caso ({dec_worst})."
            )

        object.__setattr__(self, "costo_base", dec_base.quantize(PRECISION_COST, ROUND_HALF_UP))
        object.__setattr__(self, "costo_peor_caso", dec_worst.quantize(PRECISION_COST, ROUND_HALF_UP))
        object.__setattr__(self, "costo_mejor_caso", dec_best.quantize(PRECISION_COST, ROUND_HALF_UP))
        object.__setattr__(self, "currency", str(currency).strip().upper() or "CLP")

    def cost_spread(self) -> Decimal:
        """Diferencia entre el peor y mejor escenario de costo."""
        return (self.costo_peor_caso - self.costo_mejor_caso).quantize(PRECISION_COST, ROUND_HALF_UP)

    def margen_base(self, precio_neto: Decimal | int | str) -> Decimal:
        """Margen porcentual en base al costo default."""
        net = _ensure_strict_decimal(precio_neto, "precio_neto")
        if net <= ZERO:
            raise ValueError("Net price must be strictly positive to calculate margin.")
        return ((net - self.costo_base) / net * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)

    def margen_peor_caso(self, precio_neto: Decimal | int | str) -> Decimal:
        """Margen porcentual en el peor de los casos (escenario más desfavorable)."""
        net = _ensure_strict_decimal(precio_neto, "precio_neto")
        if net <= ZERO:
            raise ValueError("Net price must be strictly positive to calculate margin.")
        return ((net - self.costo_peor_caso) / net * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)

    def margen_mejor_caso(self, precio_neto: Decimal | int | str) -> Decimal:
        """Margen porcentual en el mejor de los casos (escenario más favorable)."""
        net = _ensure_strict_decimal(precio_neto, "precio_neto")
        if net <= ZERO:
            raise ValueError("Net price must be strictly positive to calculate margin.")
        return ((net - self.costo_mejor_caso) / net * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)

    def food_cost_pct_base(self, precio_neto: Decimal | int | str) -> Decimal:
        """Food Cost % en base al costo default: costo / precio neto * 100."""
        net = _ensure_strict_decimal(precio_neto, "precio_neto")
        if net <= ZERO:
            raise ValueError("Net price must be strictly positive to calculate food cost.")
        return (self.costo_base / net * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)

    def food_cost_pct_peor_caso(self, precio_neto: Decimal | int | str) -> Decimal:
        """Food Cost % en el peor escenario: costo peor caso / precio neto * 100."""
        net = _ensure_strict_decimal(precio_neto, "precio_neto")
        if net <= ZERO:
            raise ValueError("Net price must be strictly positive to calculate food cost.")
        return (self.costo_peor_caso / net * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)


@dataclass(frozen=True)
class OptionSelectionRule:
    """
    Regla de cardinalidad y repetitividad para un grupo de opciones dinámicas.
    Invariantes:
    - `0 <= min_selections <= max_selections`
    - `max_selections >= 1`
    """

    min_selections: int = 1
    max_selections: int = 1
    allows_repeat: bool = False

    def __init__(
        self,
        min_selections: int = 1,
        max_selections: int = 1,
        allows_repeat: bool = False,
    ) -> None:
        if not isinstance(min_selections, int) or isinstance(min_selections, bool):
            raise InvalidOptionSelectionError("min_selections must be an integer.")
        if not isinstance(max_selections, int) or isinstance(max_selections, bool):
            raise InvalidOptionSelectionError("max_selections must be an integer.")
        if min_selections < 0:
            raise InvalidOptionSelectionError(
                f"min_selections must be >= 0, got {min_selections}."
            )
        if max_selections < 1:
            raise InvalidOptionSelectionError(
                f"max_selections must be >= 1, got {max_selections}."
            )
        if max_selections < min_selections:
            raise InvalidOptionSelectionError(
                f"max_selections ({max_selections}) cannot be less than min_selections ({min_selections})."
            )

        object.__setattr__(self, "min_selections", min_selections)
        object.__setattr__(self, "max_selections", max_selections)
        object.__setattr__(self, "allows_repeat", bool(allows_repeat))

    @property
    def is_required(self) -> bool:
        """Indica si la selección es obligatoria (al menos 1 elemento requerido)."""
        return self.min_selections > 0

    @property
    def is_optional(self) -> bool:
        """Indica si el grupo es enteramente opcional (se permite 0 selecciones)."""
        return self.min_selections == 0

    @property
    def is_single_choice(self) -> bool:
        """Indica si el grupo es de elección única estricta (1 de 1)."""
        return self.min_selections == 1 and self.max_selections == 1

    def validate_selection_count(self, count: int) -> bool:
        """Verifica si un recuento de selecciones satisface el intervalo [min, max]."""
        if not isinstance(count, int) or isinstance(count, bool):
            return False
        return self.min_selections <= count <= self.max_selections

    def ensure_valid_selection_count(self, count: int) -> None:
        """Lanza InvalidOptionSelectionError si el recuento no satisface la regla."""
        if not self.validate_selection_count(count):
            raise InvalidOptionSelectionError(
                f"Selected count {count} is invalid. Required between "
                f"{self.min_selections} and {self.max_selections} selections."
            )


__all__ = [
    "HUNDRED",
    "ONE",
    "PRECISION_COST",
    "PRECISION_MONEY",
    "PRECISION_PERCENTAGE",
    "PRECISION_QUANTITY",
    "ZERO",
    "DynamicCostSummary",
    "IngredientQuantity",
    "OptionSelectionRule",
    "ServingYield",
]
