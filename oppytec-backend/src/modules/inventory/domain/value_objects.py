"""
oppytec-backend/src/modules/inventory/domain/value_objects.py
Value Objects inmutables de dominio para el Módulo de Inventario.
Cumple Regla 02 (Clean Architecture), Regla 15 (i18n / DDD) y Certificación Decimal Estricta (0% float).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from src.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    InvalidMovementTypeError,
    NegativeStockNotAllowedError,
)

ZERO = Decimal(0)
QTY_QUANT = Decimal("0.0001")
MONEY_QUANT = Decimal("0.01")
SANTIAGO_TZ = ZoneInfo("America/Santiago")
UTC_TZ = ZoneInfo("UTC")


class MovementSign(StrEnum):
    """
    Value Object semántico que modela la dirección de impacto de un movimiento en Kardex:
    - POSITIVE (+): Movimientos de entrada, compras o adiciones.
    - NEGATIVE (-): Movimientos de salida, consumo, merma o reducciones.
    - NEUTRAL (0): Movimientos sin variación física o discrepancia neutra de auditoría.
    """

    POSITIVE = "+"
    NEGATIVE = "-"
    NEUTRAL = "0"

    @property
    def is_positive(self) -> bool:
        return self == MovementSign.POSITIVE

    @property
    def is_negative(self) -> bool:
        return self == MovementSign.NEGATIVE

    @property
    def is_neutral(self) -> bool:
        return self == MovementSign.NEUTRAL

    @property
    def multiplier(self) -> Decimal:
        """Multiplicador algebraico canónico: +1, -1, o 0."""
        if self == MovementSign.POSITIVE:
            return Decimal(1)
        if self == MovementSign.NEGATIVE:
            return Decimal(-1)
        return Decimal(0)

    @classmethod
    def from_movement_type(
        cls,
        movement_type: MovementType | str,
        quantity: Decimal | StockQuantity | int | str | None = None,
    ) -> MovementSign:
        """
        Determina de forma pura el signo del movimiento según el tipo y/o la discrepancia auditada.
        Compatible con los 12 tipos canónicos de OppyTec v2.0 + 'AJUSTE_AUDITORIA'.
        """
        raw_str = movement_type.value if isinstance(movement_type, MovementType) else str(movement_type)
        normalized = raw_str.strip().upper()

        # Tipos siempre positivos (entradas/adiciones)
        if normalized in {
            "ENTRADA",
            "COMPRA",
            "AJUSTE_POSITIVO",
            "TRASPASO_IN",
        }:
            return cls.POSITIVE

        # Tipos siempre negativos (salidas/consumos/mermas)
        if normalized in {
            "SALIDA",
            "CONSUMO",
            "MERMA",
            "VENTA",
            "AJUSTE_NEGATIVO",
            "TRASPASO_OUT",
        }:
            return cls.NEGATIVE

        # Tipos dependientes de la discrepancia o dirección contextual
        # ("CONTEO", "AJUSTE_AUDITORIA", "AJUSTE", "TRANSFERENCIA", "REVERSION", "REDO")
        if quantity is not None:
            if type(quantity).__name__ == "float":
                raise TypeError("Float precision IEEE-754 is strictly forbidden for MovementSign; use Decimal, int, or str")
            dec_qty = quantity.value if isinstance(quantity, StockQuantity) else Decimal(str(quantity))
            if dec_qty > ZERO:
                return cls.POSITIVE
            if dec_qty < ZERO:
                return cls.NEGATIVE
            return cls.NEUTRAL

        return cls.NEUTRAL

    def apply_to(self, quantity: Decimal | StockQuantity | int | str) -> Decimal:
        """Aplica la regla de signo a una magnitud numérica absoluta."""
        if type(quantity).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden for MovementSign; use Decimal, int, or str")
        dec_qty = quantity.value if isinstance(quantity, StockQuantity) else Decimal(str(quantity))
        abs_qty = abs(dec_qty)
        if self == MovementSign.POSITIVE:
            return abs_qty
        if self == MovementSign.NEGATIVE:
            return -abs_qty
        return ZERO


@dataclass(frozen=True)
class AuditDelta:
    """
    Value Object inmutable que encapsula la transición de estados de stock (Before / After / Delta)
    para trazabilidad en el visor de auditoría y reportes del Kardex.
    Cumple Certificación Decimal Estricta (0% float).
    """

    before: Decimal
    after: Decimal
    delta: Decimal
    unit: str = ""

    def __init__(
        self,
        before: Decimal | int | str | StockQuantity,
        after: Decimal | int | str | StockQuantity,
        delta: Decimal | int | str | StockQuantity | None = None,
        unit: str = "",
    ) -> None:
        if type(before).__name__ == "float" or type(after).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden for AuditDelta; use Decimal, int, or str")
        if delta is not None and type(delta).__name__ == "float":
            raise TypeError("Float precision IEEE-754 is strictly forbidden for AuditDelta; use Decimal, int, or str")

        def _to_dec(v: Decimal | int | str | StockQuantity) -> Decimal:
            if isinstance(v, StockQuantity):
                return v.value
            if isinstance(v, Decimal):
                return v
            try:
                return Decimal(str(v))
            except Exception as exc:
                raise ValueError(f"Invalid decimal value for AuditDelta: {v}") from exc

        dec_before = _to_dec(before).quantize(QTY_QUANT, ROUND_HALF_UP)
        dec_after = _to_dec(after).quantize(QTY_QUANT, ROUND_HALF_UP)

        if delta is not None:
            dec_delta = _to_dec(delta).quantize(QTY_QUANT, ROUND_HALF_UP)
        else:
            dec_delta = (dec_after - dec_before).quantize(QTY_QUANT, ROUND_HALF_UP)

        object.__setattr__(self, "before", dec_before)
        object.__setattr__(self, "after", dec_after)
        object.__setattr__(self, "delta", dec_delta)
        object.__setattr__(self, "unit", str(unit).strip())

    @property
    def has_change(self) -> bool:
        """Indica si hubo variación entre el saldo anterior y el resultante."""
        return self.before != self.after

    @property
    def is_positive(self) -> bool:
        """Indica si el delta representa un incremento neto de existencias."""
        return self.delta > ZERO

    @property
    def is_negative(self) -> bool:
        """Indica si el delta representa una reducción neta de existencias."""
        return self.delta < ZERO

    @property
    def is_neutral(self) -> bool:
        """Indica si el delta es exactamente cero."""
        return self.delta == ZERO

    def format_transition(self) -> str:
        """Retorna la representación legible de transición 'before -> after unit'."""
        suffix = f" {self.unit}" if self.unit else ""
        return f"{self.before:.4f}{suffix} -> {self.after:.4f}{suffix}".strip()

    def to_dict(self) -> dict[str, str | Decimal]:
        """Serializa los deltas numéricos preservando tipo Decimal."""
        return {
            "before": self.before,
            "after": self.after,
            "delta": self.delta,
            "unit": self.unit,
        }

    def __str__(self) -> str:
        suffix = f" {self.unit}" if self.unit else ""
        return f"{self.before:.4f}{suffix} -> {self.after:.4f}{suffix} (Δ {self.delta:+.4f})"

    def __repr__(self) -> str:
        return (
            f"AuditDelta(before={self.before:.4f}, after={self.after:.4f}, "
            f"delta={self.delta:.4f}, unit='{self.unit}')"
        )


class TimezoneConverter:
    """
    Conversor y proyector determinista de huso horario para trazabilidad de auditoría.
    Garantiza consistencia entre UTC persistido en PostgreSQL y la visualización
    operativa oficial en Chile (America/Santiago).
    Clean Architecture pura: sin dependencias de frameworks ni infraestructura.
    """

    @staticmethod
    def to_chile(dt: datetime) -> datetime:
        """Convierte un objeto datetime a la zona horaria 'America/Santiago'."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TZ)
        return dt.astimezone(SANTIAGO_TZ)

    @staticmethod
    def format_chile_datetime(dt: datetime) -> str:
        """Formatea fecha y hora en formato legible 'DD/MM/YYYY HH:mm:ss' (America/Santiago)."""
        chile_dt = TimezoneConverter.to_chile(dt)
        return chile_dt.strftime("%d/%m/%Y %H:%M:%S")

    @staticmethod
    def format_chile_date(dt: datetime) -> str:
        """Formatea fecha en formato 'DD/MM/YYYY' (America/Santiago)."""
        chile_dt = TimezoneConverter.to_chile(dt)
        return chile_dt.strftime("%d/%m/%Y")


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
    "SANTIAGO_TZ",
    "UTC_TZ",
    "ZERO",
    "AuditDelta",
    "MoneyAmount",
    "MovementSign",
    "MovementType",
    "StockQuantity",
    "StorageLocation",
    "TimezoneConverter",
]
