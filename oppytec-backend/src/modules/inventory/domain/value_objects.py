"""
oppytec-backend/src/modules/inventory/domain/value_objects.py
Value Objects inmutables de dominio para el Módulo de Inventario.
Cumple Regla 02 (Clean Architecture), Regla 15 (i18n / DDD) y Certificación Decimal Estricta (0% float).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from src.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    InvalidMovementTypeError,
    NegativeStockNotAllowedError,
)

ZERO = Decimal(0)
QTY_QUANT = Decimal("0.0001")
MONEY_QUANT = Decimal("0.01")


class MovementType(StrEnum):
    """
    Tipos de movimiento de Kardex admitidos en el sistema multi-bodega.
    Totalmente compatible con cadenas y estrictamente tipado.
    """

    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    COMPRA = "COMPRA"
    CONSUMO = "CONSUMO"
    MERMA = "MERMA"
    TRASPASO_IN = "TRASPASO_IN"
    TRASPASO_OUT = "TRASPASO_OUT"
    AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
    AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"
    AJUSTE_AUDITORIA = "AJUSTE_AUDITORIA"

    @property
    def is_entry(self) -> bool:
        """Determina si el movimiento incrementa existencias de forma predeterminada."""
        return self in {
            MovementType.ENTRADA,
            MovementType.COMPRA,
            MovementType.TRASPASO_IN,
            MovementType.AJUSTE_POSITIVO,
        }

    @property
    def is_exit(self) -> bool:
        """Determina si el movimiento reduce existencias de forma predeterminada."""
        return self in {
            MovementType.SALIDA,
            MovementType.CONSUMO,
            MovementType.MERMA,
            MovementType.TRASPASO_OUT,
            MovementType.AJUSTE_NEGATIVO,
        }

    @classmethod
    def from_str(cls, value: str | MovementType) -> MovementType:
        """Parsea e interpreta de forma segura un tipo de movimiento."""
        if isinstance(value, MovementType):
            return value
        if not isinstance(value, str):
            raise InvalidMovementTypeError(
                f"Movement type must be a string or MovementType enum, received {type(value).__name__}",
                context={"value": str(value)},
            )
        normalized = value.strip().upper()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise InvalidMovementTypeError(
                f"Unknown movement type: '{value}'. Allowed: {[m.value for m in cls]}",
                context={"movement_type": value},
            ) from exc


ENTRY_MOVEMENTS: frozenset[str] = frozenset(
    {MovementType.ENTRADA.value, MovementType.COMPRA.value, MovementType.AJUSTE_POSITIVO.value, MovementType.TRASPASO_IN.value}
)
EXIT_MOVEMENTS: frozenset[str] = frozenset(
    {
        MovementType.SALIDA.value,
        MovementType.CONSUMO.value,
        MovementType.MERMA.value,
        MovementType.AJUSTE_NEGATIVO.value,
        MovementType.TRASPASO_OUT.value,
    }
)


@dataclass(frozen=True)
class StockQuantity:
    """
    Cantidad física de inventario inmutable, cuantizada a 4 decimales (`0.0001`).
    Prohíbe totalmente el uso de `float` (IEEE 754) para evitar errores de redondeo.
    """

    value: Decimal
    allow_negative: bool = False

    def __init__(self, value: Decimal | int | str | StockQuantity, allow_negative: bool = False) -> None:
        if type(value).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden for StockQuantity; use Decimal, int, or str")

        if isinstance(value, StockQuantity):
            dec_val = value.value
        elif isinstance(value, Decimal):
            dec_val = value
        elif isinstance(value, (int, str)):
            try:
                dec_val = Decimal(str(value))
            except Exception as exc:
                raise ValueError(f"Invalid decimal string for StockQuantity: {value}") from exc
        else:
            raise TypeError(f"Unsupported type for StockQuantity: {type(value).__name__}")

        if dec_val.is_nan() or dec_val.is_infinite():
            raise ValueError(f"StockQuantity cannot be NaN or infinite: {dec_val}")

        quantized = dec_val.quantize(QTY_QUANT, ROUND_HALF_UP)
        if not allow_negative and quantized < ZERO:
            raise NegativeStockNotAllowedError(
                f"Stock quantity cannot be negative ({quantized})",
                context={"quantity": str(quantized)},
            )

        object.__setattr__(self, "value", quantized)
        object.__setattr__(self, "allow_negative", allow_negative)

    @classmethod
    def zero(cls, allow_negative: bool = False) -> StockQuantity:
        """Retorna una cantidad cero."""
        return cls(ZERO, allow_negative=allow_negative)

    def to_decimal(self) -> Decimal:
        """Retorna el valor encapsulado en Decimal puro."""
        return self.value

    def is_zero(self) -> bool:
        """Verifica si la cantidad es exactamente 0.0000."""
        return self.value == ZERO

    def is_positive(self) -> bool:
        """Verifica si la cantidad es estrictamente mayor a 0."""
        return self.value > ZERO

    def is_negative(self) -> bool:
        """Verifica si la cantidad es estrictamente menor a 0."""
        return self.value < ZERO

    def __add__(self, other: StockQuantity | Decimal | int | str) -> StockQuantity:
        other_val = other.value if isinstance(other, StockQuantity) else StockQuantity(other, allow_negative=True).value
        new_val = self.value + other_val
        return StockQuantity(new_val, allow_negative=self.allow_negative)

    def __sub__(self, other: StockQuantity | Decimal | int | str) -> StockQuantity:
        other_val = other.value if isinstance(other, StockQuantity) else StockQuantity(other, allow_negative=True).value
        new_val = self.value - other_val
        if not self.allow_negative and new_val < ZERO:
            raise InsufficientStockError(
                f"Insufficient stock: current balance {self.value} is less than required {other_val}",
                context={"balance": str(self.value), "required": str(other_val)},
            )
        return StockQuantity(new_val, allow_negative=self.allow_negative)

    def __mul__(self, factor: Decimal | int | str) -> StockQuantity:
        if type(factor).__name__ == "float":
            raise TypeError("Float factor is strictly forbidden for StockQuantity; use Decimal, int, or str")
        dec_factor = Decimal(str(factor))
        new_val = self.value * dec_factor
        return StockQuantity(new_val, allow_negative=self.allow_negative)

    def __abs__(self) -> StockQuantity:
        return StockQuantity(abs(self.value), allow_negative=self.allow_negative)

    def __neg__(self) -> StockQuantity:
        return StockQuantity(-self.value, allow_negative=True)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StockQuantity):
            return self.value == other.value
        if isinstance(other, (Decimal, int, str)):
            try:
                return self.value == Decimal(str(other)).quantize(QTY_QUANT, ROUND_HALF_UP)
            except Exception:
                return False
        return False

    def __lt__(self, other: StockQuantity | Decimal | int | str) -> bool:
        other_val = other.value if isinstance(other, StockQuantity) else Decimal(str(other))
        return self.value < other_val

    def __le__(self, other: StockQuantity | Decimal | int | str) -> bool:
        other_val = other.value if isinstance(other, StockQuantity) else Decimal(str(other))
        return self.value <= other_val

    def __gt__(self, other: StockQuantity | Decimal | int | str) -> bool:
        other_val = other.value if isinstance(other, StockQuantity) else Decimal(str(other))
        return self.value > other_val

    def __ge__(self, other: StockQuantity | Decimal | int | str) -> bool:
        other_val = other.value if isinstance(other, StockQuantity) else Decimal(str(other))
        return self.value >= other_val

    def __str__(self) -> str:
        return f"{self.value:.4f}"

    def __repr__(self) -> str:
        return f"StockQuantity({self.value:.4f}, allow_negative={self.allow_negative})"


@dataclass(frozen=True)
class MoneyAmount:
    """
    Monto monetario inmutable con precisión fija de 2 decimales (`0.01`).
    Soporte multi-moneda ISO 4217 (CLP, USD, EUR, etc.) con rechazo estricto de floats.
    """

    amount: Decimal
    currency: str = "CLP"

    def __init__(self, amount: Decimal | int | str | MoneyAmount, currency: str = "CLP") -> None:
        if type(amount).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden for MoneyAmount; use Decimal, int, or str")

        if isinstance(amount, MoneyAmount):
            dec_amount = amount.amount
            currency = amount.currency
        elif isinstance(amount, Decimal):
            dec_amount = amount
        elif isinstance(amount, (int, str)):
            try:
                dec_amount = Decimal(str(amount))
            except Exception as exc:
                raise ValueError(f"Invalid decimal string for MoneyAmount: {amount}") from exc
        else:
            raise TypeError(f"Unsupported type for MoneyAmount: {type(amount).__name__}")

        if dec_amount.is_nan() or dec_amount.is_infinite():
            raise ValueError(f"MoneyAmount cannot be NaN or infinite: {dec_amount}")

        quantized = dec_amount.quantize(MONEY_QUANT, ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)
        object.__setattr__(self, "currency", currency.upper().strip())

    @classmethod
    def zero(cls, currency: str = "CLP") -> MoneyAmount:
        """Retorna un monto monetario en cero."""
        return cls(ZERO, currency=currency)

    def to_decimal(self) -> Decimal:
        """Retorna el monto Decimal con 2 decimales."""
        return self.amount

    def is_zero(self) -> bool:
        return self.amount == ZERO

    def is_positive(self) -> bool:
        return self.amount > ZERO

    def is_negative(self) -> bool:
        return self.amount < ZERO

    def _ensure_same_currency(self, other: MoneyAmount) -> None:
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch in operation: {self.currency} vs {other.currency}")

    def __add__(self, other: MoneyAmount) -> MoneyAmount:
        if not isinstance(other, MoneyAmount):
            raise TypeError(f"Can only add MoneyAmount to MoneyAmount, received {type(other).__name__}")
        self._ensure_same_currency(other)
        return MoneyAmount(self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: MoneyAmount) -> MoneyAmount:
        if not isinstance(other, MoneyAmount):
            raise TypeError(f"Can only subtract MoneyAmount from MoneyAmount, received {type(other).__name__}")
        self._ensure_same_currency(other)
        return MoneyAmount(self.amount - other.amount, currency=self.currency)

    def __mul__(self, factor: Decimal | int | str | StockQuantity) -> MoneyAmount:
        if type(factor).__name__ == "float":
            raise TypeError("Float factor is strictly forbidden for MoneyAmount; use Decimal, int, or str")
        dec_factor = factor.value if isinstance(factor, StockQuantity) else Decimal(str(factor))
        new_amount = self.amount * dec_factor
        return MoneyAmount(new_amount, currency=self.currency)

    def __abs__(self) -> MoneyAmount:
        return MoneyAmount(abs(self.amount), currency=self.currency)

    def __neg__(self) -> MoneyAmount:
        return MoneyAmount(-self.amount, currency=self.currency)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MoneyAmount):
            return self.amount == other.amount and self.currency == other.currency
        if isinstance(other, (Decimal, int, str)):
            try:
                return self.amount == Decimal(str(other)).quantize(MONEY_QUANT, ROUND_HALF_UP)
            except Exception:
                return False
        return False

    def __lt__(self, other: MoneyAmount) -> bool:
        if not isinstance(other, MoneyAmount):
            raise TypeError("Can only compare MoneyAmount with MoneyAmount")
        self._ensure_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: MoneyAmount) -> bool:
        if not isinstance(other, MoneyAmount):
            raise TypeError("Can only compare MoneyAmount with MoneyAmount")
        self._ensure_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: MoneyAmount) -> bool:
        if not isinstance(other, MoneyAmount):
            raise TypeError("Can only compare MoneyAmount with MoneyAmount")
        self._ensure_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: MoneyAmount) -> bool:
        if not isinstance(other, MoneyAmount):
            raise TypeError("Can only compare MoneyAmount with MoneyAmount")
        self._ensure_same_currency(other)
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def __repr__(self) -> str:
        return f"MoneyAmount({self.amount:.2f}, currency='{self.currency}')"


@dataclass(frozen=True)
class StorageLocation:
    """
    Ubicación física inmutable de un ítem en bodega (pasillo, estante, nivel).
    Longitud máxima por componente: 20 caracteres según esquema de base de datos.
    """

    pasillo: str | None = None
    estante: str | None = None
    nivel: str | None = None

    def __post_init__(self) -> None:
        def clean_field(name: str, val: str | None) -> str | None:
            if val is None:
                return None
            cleaned = str(val).strip()
            if not cleaned:
                return None
            if len(cleaned) > 20:
                raise ValueError(f"StorageLocation field '{name}' exceeds maximum length of 20 characters: '{cleaned}'")
            return cleaned

        object.__setattr__(self, "pasillo", clean_field("pasillo", self.pasillo))
        object.__setattr__(self, "estante", clean_field("estante", self.estante))
        object.__setattr__(self, "nivel", clean_field("nivel", self.nivel))

    @property
    def is_assigned(self) -> bool:
        """Determina si al menos uno de los tres componentes de ubicación está asignado."""
        return any(x is not None for x in (self.pasillo, self.estante, self.nivel))

    @property
    def code(self) -> str:
        """Genera el código formateado legible de ubicación (ej. 'P-A1 / E-02 / N-03')."""
        if not self.is_assigned:
            return "SIN_UBICACION"
        parts: list[str] = []
        if self.pasillo:
            parts.append(f"P-{self.pasillo}")
        if self.estante:
            parts.append(f"E-{self.estante}")
        if self.nivel:
            parts.append(f"N-{self.nivel}")
        return " / ".join(parts)

    def to_dict(self) -> dict[str, str | None]:
        """Serializa a diccionario compatible con modelos relacionales."""
        return {
            "pasillo": self.pasillo,
            "estante": self.estante,
            "nivel": self.nivel,
        }


__all__ = [
    "ENTRY_MOVEMENTS",
    "EXIT_MOVEMENTS",
    "MONEY_QUANT",
    "QTY_QUANT",
    "ZERO",
    "MoneyAmount",
    "MovementType",
    "StockQuantity",
    "StorageLocation",
]
