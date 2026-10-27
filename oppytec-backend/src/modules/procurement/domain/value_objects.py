"""
oppytec-backend/src/modules/procurement/domain/value_objects.py
Value Objects inmutables de dominio para el Módulo de Procurement (Abastecimiento y Compras).
Cumple Regla 02 (Clean Architecture: 0 imports de infraestructura), Regla 15 (i18n / DDD)
y Certificación Decimal Estricta (0% float).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from src.modules.procurement.domain.exceptions import (
    DomainValidationError,
    InvalidPurchaseStatusTransitionError,
    InvalidRutError,
    NegativeMoneyError,
    NegativeQuantityError,
)

ZERO = Decimal(0)
MONEY_QUANT = Decimal("0.01")
MAX_MONEY_AMOUNT = Decimal("999999999999.99")
CHILEAN_RUT_FACTORS = (2, 3, 4, 5, 6, 7)
INTL_TAX_ID_PATTERN = re.compile(r"^[A-Za-z0-9.\-_]{3,64}$")


def calculate_chilean_dv(body: str | int) -> str:
    """
    Calcula el dígito verificador chileno para un cuerpo de RUT mediante el algoritmo Módulo 11.
    Retorna '0'-'9' o 'K'.
    """
    body_str = str(body).strip()
    if not body_str.isdigit():
        raise InvalidRutError(f"RUT body must contain only digits, received: '{body_str}'")

    total = sum(
        int(digit) * CHILEAN_RUT_FACTORS[idx % len(CHILEAN_RUT_FACTORS)]
        for idx, digit in enumerate(reversed(body_str))
    )
    remainder = total % 11
    dv_val = 11 - remainder
    if dv_val == 11:
        return "0"
    if dv_val == 10:
        return "K"
    return str(dv_val)


@dataclass(frozen=True)
class RutTaxId:
    """
    Value Object inmutable que representa un identificador tributario.
    - Soporta RUT chileno con verificación de integridad algorítmica Módulo 11 y formato estándar.
    - Soporta TAX ID internacional (US EIN, EU VAT, RFC, etc.) con validación de sintaxis segura.
    """

    value: str
    country: str = "CL"

    def __init__(self, raw_value: str, country: str = "CL") -> None:
        if not isinstance(raw_value, str):
            raise InvalidRutError(f"RUT/Tax ID must be a string, got {type(raw_value).__name__}")

        stripped = raw_value.strip()
        if not stripped:
            raise InvalidRutError("RUT/Tax ID cannot be empty or whitespace")

        norm_country = country.strip().upper()

        if norm_country == "CL":
            clean_str = stripped.replace(".", "").replace(" ", "").upper()
            if "-" in clean_str:
                parts = clean_str.rsplit("-", 1)
                body_candidate, dv_candidate = parts[0], parts[1]
            else:
                if len(clean_str) < 2:
                    raise InvalidRutError(f"Chilean RUT '{raw_value}' is too short")
                body_candidate, dv_candidate = clean_str[:-1], clean_str[-1]

            if not body_candidate.isdigit():
                raise InvalidRutError(
                    f"Chilean RUT body must contain only digits: '{body_candidate}' from '{raw_value}'"
                )

            if not (1 <= len(body_candidate) <= 9):
                raise InvalidRutError(
                    f"Chilean RUT body length must be between 1 and 9 digits, got {len(body_candidate)}"
                )

            expected_dv = calculate_chilean_dv(body_candidate)
            if dv_candidate != expected_dv:
                raise InvalidRutError(
                    f"Invalid Chilean RUT check digit for '{raw_value}': expected '{expected_dv}', got '{dv_candidate}'"
                )

            formatted_body = f"{int(body_candidate):,}".replace(",", ".")
            canonical_value = f"{formatted_body}-{dv_candidate}"
        else:
            if not INTL_TAX_ID_PATTERN.match(stripped):
                raise InvalidRutError(
                    f"Invalid international Tax ID format for '{stripped}' (country: {norm_country})"
                )
            canonical_value = stripped.upper()

        object.__setattr__(self, "value", canonical_value)
        object.__setattr__(self, "country", norm_country)

    @classmethod
    def from_chilean(cls, rut: str) -> RutTaxId:
        """Fabrica un RutTaxId chileno validando módulo 11."""
        return cls(raw_value=rut, country="CL")

    @classmethod
    def from_international(cls, tax_id: str, country: str = "INT") -> RutTaxId:
        """Fabrica un RutTaxId internacional validando longitud y caracteres permitidos."""
        return cls(raw_value=tax_id, country=country)

    @property
    def is_chilean(self) -> bool:
        """Indica si el identificador corresponde a un RUT de Chile."""
        return self.country == "CL"

    @property
    def clean(self) -> str:
        """Retorna el RUT chileno sin puntos (ej. '76543210-3') o el TAX ID sin modificaciones."""
        if self.is_chilean:
            return self.value.replace(".", "")
        return self.value

    @property
    def formatted(self) -> str:
        """Retorna la representación canónica con formato."""
        return self.value

    @property
    def body(self) -> str:
        """Cuerpo numérico del RUT chileno o identificador base."""
        if self.is_chilean and "-" in self.value:
            return self.value.rsplit("-", 1)[0].replace(".", "")
        return self.value

    @property
    def dv(self) -> str:
        """Dígito verificador para RUT chileno, o cadena vacía si es internacional."""
        if self.is_chilean and "-" in self.value:
            return self.value.rsplit("-", 1)[1]
        return ""

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"RutTaxId('{self.value}', country='{self.country}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RutTaxId):
            return self.clean == other.clean and self.country == other.country
        if isinstance(other, str):
            other_clean = other.strip().replace(".", "").upper()
            return self.clean == other_clean
        return False


class PurchaseStatus(StrEnum):
    """
    Máquina de estados estricta para el ciclo de vida de una orden de compra:
    BORRADOR -> SOLICITADA -> EN_CAMINO -> RECIBIDA_PARCIAL / RECIBIDA_TOTAL
    o CANCELADA en estados no terminales.
    """

    BORRADOR = "BORRADOR"
    SOLICITADA = "SOLICITADA"
    EN_CAMINO = "EN_CAMINO"
    RECIBIDA_PARCIAL = "RECIBIDA_PARCIAL"
    RECIBIDA_TOTAL = "RECIBIDA_TOTAL"
    CANCELADA = "CANCELADA"

    @property
    def is_terminal(self) -> bool:
        """Indica si la compra está en un estado final irreversible."""
        return self in (PurchaseStatus.RECIBIDA_TOTAL, PurchaseStatus.CANCELADA)

    @property
    def is_receivable(self) -> bool:
        """Indica si la compra admite recepción física de mercadería en bodega."""
        return self in (PurchaseStatus.EN_CAMINO, PurchaseStatus.RECIBIDA_PARCIAL)

    def can_transition_to(self, target: PurchaseStatus) -> bool:
        """Valida si la transición hacia el estado destino es admisible."""
        valid_transitions: dict[PurchaseStatus, frozenset[PurchaseStatus]] = {
            PurchaseStatus.BORRADOR: frozenset(
                {PurchaseStatus.SOLICITADA, PurchaseStatus.CANCELADA}
            ),
            PurchaseStatus.SOLICITADA: frozenset(
                {PurchaseStatus.EN_CAMINO, PurchaseStatus.CANCELADA}
            ),
            PurchaseStatus.EN_CAMINO: frozenset(
                {
                    PurchaseStatus.RECIBIDA_PARCIAL,
                    PurchaseStatus.RECIBIDA_TOTAL,
                    PurchaseStatus.CANCELADA,
                }
            ),
            PurchaseStatus.RECIBIDA_PARCIAL: frozenset(
                {
                    PurchaseStatus.RECIBIDA_PARCIAL,
                    PurchaseStatus.RECIBIDA_TOTAL,
                    PurchaseStatus.CANCELADA,
                }
            ),
            PurchaseStatus.RECIBIDA_TOTAL: frozenset(),
            PurchaseStatus.CANCELADA: frozenset(),
        }
        return target in valid_transitions.get(self, frozenset())

    def validate_transition(self, target: PurchaseStatus) -> None:
        """Exige que la transición sea válida según la máquina de estados; levanta error de lo contrario."""
        if not self.can_transition_to(target):
            raise InvalidPurchaseStatusTransitionError(
                f"Cannot transition purchase order from '{self.value}' to '{target.value}'"
            )


class IncidenceType(StrEnum):
    """Tipos canónicos de incidencias y discrepancias en recepción de compras."""

    DIFERENCIA_CANTIDAD = "DIFERENCIA_CANTIDAD"
    PRODUCTO_DANADO = "PRODUCTO_DANADO"
    FECHA_CADUCADA = "FECHA_CADUCADA"
    PRODUCTO_EQUIVOCADO = "PRODUCTO_EQUIVOCADO"
    OTRO = "OTRO"


class IncidenceResolution(StrEnum):
    """Resoluciones administrativas de incidencias de compras."""

    PENDIENTE = "PENDIENTE"
    NOTA_CREDITO = "NOTA_CREDITO"
    REEMPLAZO = "REEMPLAZO"
    ACEPTADO_CON_DESCUENTO = "ACEPTADO_CON_DESCUENTO"
    DESESTIMADO = "DESESTIMADO"


@dataclass(frozen=True)
class MoneyAmount:
    """
    Monto monetario inmutable de adquisición con precisión exacta Decimal(14, 2).
    Invariante de dominio: montos no-negativos por defecto y 0% tipos float.
    """

    amount: Decimal
    currency: str = "CLP"

    def __init__(
        self,
        amount: Decimal | int | str | MoneyAmount,
        currency: str = "CLP",
        *,
        allow_negative: bool = False,
    ) -> None:
        if isinstance(amount, bool):
            raise TypeError("Boolean values cannot be converted to MoneyAmount")

        if isinstance(amount, MoneyAmount):
            dec_amount = amount.amount
            currency = amount.currency
        elif isinstance(amount, Decimal):
            dec_amount = amount
        elif isinstance(amount, (int, str)):
            try:
                dec_amount = Decimal(str(amount))
            except Exception as exc:
                raise ValueError(f"Invalid decimal string for MoneyAmount: '{amount}'") from exc
        else:
            raise TypeError(
                f"Unsupported type for MoneyAmount: {type(amount).__name__}. IEEE-754 float is strictly forbidden."
            )

        if dec_amount.is_nan() or dec_amount.is_infinite():
            raise ValueError(f"MoneyAmount cannot be NaN or infinite: {dec_amount}")

        if not allow_negative and dec_amount < ZERO:
            raise NegativeMoneyError(
                f"MoneyAmount cannot be negative: {dec_amount} {currency}"
            )

        quantized = dec_amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        if abs(quantized) > MAX_MONEY_AMOUNT:
            raise DomainValidationError(
                f"MoneyAmount '{quantized}' exceeds maximum supported precision Decimal(14, 2) (limit: {MAX_MONEY_AMOUNT})"
            )

        object.__setattr__(self, "amount", quantized)
        object.__setattr__(self, "currency", currency.strip().upper())

    @classmethod
    def zero(cls, currency: str = "CLP") -> MoneyAmount:
        """Retorna un monto en cero para la divisa dada."""
        return cls(amount=ZERO, currency=currency)

    def to_decimal(self) -> Decimal:
        """Retorna el monto subyacente en Decimal."""
        return self.amount

    def is_zero(self) -> bool:
        """Determina si el monto es exactamente 0.00."""
        return self.amount == ZERO

    def is_positive(self) -> bool:
        """Determina si el monto es estrictamente mayor a 0.00."""
        return self.amount > ZERO

    def _ensure_same_currency(self, other: MoneyAmount) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: cannot operate between '{self.currency}' and '{other.currency}'"
            )

    def __add__(self, other: MoneyAmount) -> MoneyAmount:
        if not isinstance(other, MoneyAmount):
            raise TypeError(f"Cannot add {type(other).__name__} to MoneyAmount")
        self._ensure_same_currency(other)
        return MoneyAmount(self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: MoneyAmount) -> MoneyAmount:
        if not isinstance(other, MoneyAmount):
            raise TypeError(f"Cannot subtract {type(other).__name__} from MoneyAmount")
        self._ensure_same_currency(other)
        result = self.amount - other.amount
        if result < ZERO:
            raise NegativeMoneyError(
                f"Subtraction results in negative MoneyAmount: {result} {self.currency}"
            )
        return MoneyAmount(result, currency=self.currency)

    def __mul__(self, factor: Decimal | int | str) -> MoneyAmount:
        if isinstance(factor, bool):
            raise TypeError("Cannot multiply MoneyAmount by boolean factor")
        if not isinstance(factor, (Decimal, int, str)):
            raise TypeError(
                f"Unsupported factor type for MoneyAmount multiplication: {type(factor).__name__}"
            )
        dec_factor = Decimal(str(factor))
        result = self.amount * dec_factor
        return MoneyAmount(result, currency=self.currency)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MoneyAmount):
            return self.amount == other.amount and self.currency == other.currency
        if isinstance(other, (Decimal, int, str)) and not isinstance(other, bool):
            try:
                return self.amount == Decimal(str(other)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            except Exception:
                return False
        return False

    def __lt__(self, other: MoneyAmount | Decimal | int | str) -> bool:
        other_amount = other.amount if isinstance(other, MoneyAmount) else Decimal(str(other))
        return self.amount < other_amount

    def __le__(self, other: MoneyAmount | Decimal | int | str) -> bool:
        other_amount = other.amount if isinstance(other, MoneyAmount) else Decimal(str(other))
        return self.amount <= other_amount

    def __gt__(self, other: MoneyAmount | Decimal | int | str) -> bool:
        other_amount = other.amount if isinstance(other, MoneyAmount) else Decimal(str(other))
        return self.amount > other_amount

    def __ge__(self, other: MoneyAmount | Decimal | int | str) -> bool:
        other_amount = other.amount if isinstance(other, MoneyAmount) else Decimal(str(other))
        return self.amount >= other_amount

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def __repr__(self) -> str:
        return f"MoneyAmount(Decimal('{self.amount:.2f}'), currency='{self.currency}')"


def _cast_to_decimal(value: Decimal | int | str, param_name: str) -> Decimal:
    """Valida y convierte un operando numérico a Decimal, prohibiendo booleans y floats."""
    if isinstance(value, bool):
        raise TypeError(f"Parameter '{param_name}' cannot be a boolean")
    if isinstance(value, (Decimal, int, str)):
        try:
            dec = Decimal(str(value))
            if dec.is_nan() or dec.is_infinite():
                raise ValueError(f"Parameter '{param_name}' cannot be NaN or infinite")
            return dec
        except Exception as exc:
            raise ValueError(f"Invalid decimal value for '{param_name}': '{value}'") from exc
    raise TypeError(
        f"Parameter '{param_name}' must be Decimal, int, or numeric str, got {type(value).__name__}"
    )


def calculate_reception_ppp(
    stock_actual: Decimal | int | str,
    costo_ppp_ant: Decimal | int | str,
    cant_recibida: Decimal | int | str,
    precio_compra: Decimal | int | str,
    *,
    quantize_to: Decimal = Decimal("0.01"),
    allow_negative_stock: bool = False,
) -> Decimal:
    """
    Recalcula de forma determinista e inmutable el Costo Promedio Ponderado (PPP / WACC)
    tras la recepción de mercadería en bodega.

    Fórmula matemática inmutable:
        PPP_nuevo = ((Stock_actual * PPP_ant) + (Cant_recibida * Precio_compra)) / (Stock_actual + Cant_recibida)

    Reglas de negocio:
    1. `cant_recibida` no puede ser negativa.
    2. `precio_compra` no puede ser negativo.
    3. `costo_ppp_ant` no puede ser negativo.
    4. Si `stock_actual` < 0:
       - Si `allow_negative_stock=False`, rechaza con `NegativeQuantityError`.
       - Si `allow_negative_stock=True`, el inventario previo se trunca a 0 para ponderación.
    5. División por cero:
       - Si `Stock_actual + Cant_recibida == 0`:
         Retorna `costo_ppp_ant` (o `precio_compra` si `costo_ppp_ant == 0`), evitando `ZeroDivisionError`.
    6. Precisión: cálculo puro en `Decimal` con redondeo estándar bancario (`ROUND_HALF_UP`).
    """
    stock_dec = _cast_to_decimal(stock_actual, "stock_actual")
    costo_ant_dec = _cast_to_decimal(costo_ppp_ant, "costo_ppp_ant")
    cant_recibida_dec = _cast_to_decimal(cant_recibida, "cant_recibida")
    precio_compra_dec = _cast_to_decimal(precio_compra, "precio_compra")

    if cant_recibida_dec < ZERO:
        raise NegativeQuantityError(
            f"Received quantity cannot be negative, got: {cant_recibida_dec}"
        )

    if precio_compra_dec < ZERO:
        raise NegativeMoneyError(
            f"Purchase price cannot be negative, got: {precio_compra_dec}"
        )

    if costo_ant_dec < ZERO:
        raise NegativeMoneyError(
            f"Previous PPP cost cannot be negative, got: {costo_ant_dec}"
        )

    if stock_dec < ZERO:
        if not allow_negative_stock:
            raise NegativeQuantityError(
                f"Current stock cannot be negative in strict PPP recalculation: {stock_dec}"
            )
        base_stock = ZERO
    else:
        base_stock = stock_dec

    total_qty = base_stock + cant_recibida_dec

    if total_qty == ZERO:
        if costo_ant_dec > ZERO:
            return costo_ant_dec.quantize(quantize_to, rounding=ROUND_HALF_UP)
        return precio_compra_dec.quantize(quantize_to, rounding=ROUND_HALF_UP)

    total_inventory_value = (base_stock * costo_ant_dec) + (cant_recibida_dec * precio_compra_dec)
    ppp_result = total_inventory_value / total_qty
    return ppp_result.quantize(quantize_to, rounding=ROUND_HALF_UP)


__all__ = [
    "CHILEAN_RUT_FACTORS",
    "INTL_TAX_ID_PATTERN",
    "MAX_MONEY_AMOUNT",
    "MONEY_QUANT",
    "IncidenceResolution",
    "IncidenceType",
    "MoneyAmount",
    "PurchaseStatus",
    "RutTaxId",
    "calculate_chilean_dv",
    "calculate_reception_ppp",
]
