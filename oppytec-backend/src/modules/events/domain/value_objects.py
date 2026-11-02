"""
oppytec-backend/src/modules/events/domain/value_objects.py
Value Objects inmutables del dominio de Eventos, Salones y Banquetes.
Garantiza validación estricta, semántica de negocio y precisión monetaria con Decimal.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from src.modules.events.domain.exceptions import (
    InvalidEventTimeSlotError,
    InvalidMoneyAmountError,
    SalonCapacityExceededError,
)


class EventStatus(str, Enum):
    """Estados del ciclo de vida de un evento agendado."""

    AGENDADO = "AGENDADO"
    CONFIRMADO = "CONFIRMADO"
    EN_CURSO = "EN_CURSO"
    EJECUTADO = "EJECUTADO"
    CANCELADO = "CANCELADO"

    @classmethod
    def from_str(cls, value: str) -> EventStatus:
        """Parsea strings flexibles (case-insensitive) a `EventStatus`."""
        cleaned = value.strip().upper()
        # Aliases comunes legacy
        mapping: dict[str, EventStatus] = {
            "AGENDADO": cls.AGENDADO,
            "CONFIRMADO": cls.CONFIRMADO,
            "EN_CURSO": cls.EN_CURSO,
            "EN CURSO": cls.EN_CURSO,
            "EJECUTADO": cls.EJECUTADO,
            "FINALIZADO": cls.EJECUTADO,
            "CANCELADO": cls.CANCELADO,
        }
        if cleaned in mapping:
            return mapping[cleaned]
        try:
            return cls(cleaned)
        except ValueError:
            raise ValueError(f"Estado de evento desconocido: '{value}'")


class SalonState(str, Enum):
    """Estado operativo o higiénico del salón / espacio físico."""

    LIMPIO = "limpio"
    EN_USO = "en_uso"
    MANTENIMIENTO = "mantenimiento"
    SUCIO = "sucio"

    @classmethod
    def from_str(cls, value: str) -> SalonState:
        """Parsea strings flexibles a `SalonState`."""
        cleaned = value.strip().lower()
        if cleaned in ("limpio", "activo", "disponible"):
            return cls.LIMPIO
        if cleaned in ("en_uso", "ocupado", "en curso"):
            return cls.EN_USO
        if cleaned in ("mantenimiento", "reparacion"):
            return cls.MANTENIMIENTO
        if cleaned in ("sucio", "por_limpiar"):
            return cls.SUCIO
        try:
            return cls(cleaned)
        except ValueError:
            return cls.LIMPIO


@dataclass(frozen=True)
class EventTimeSlot:
    """
    Franja temporal inmutable de un evento.
    Valida que `hora_fin > hora_inicio` si ambas horas son especificadas.
    Calcula solapamiento temporal exacto (`overlaps`).
    """

    fecha: date
    hora_inicio: time | None = None
    hora_fin: time | None = None

    def __post_init__(self) -> None:
        if self.hora_inicio is not None and self.hora_fin is not None:
            if self.hora_fin <= self.hora_inicio:
                raise InvalidEventTimeSlotError(
                    f"Hora de fin ({self.hora_fin}) debe ser posterior a hora de inicio ({self.hora_inicio}).",
                    context={
                        "hora_inicio": str(self.hora_inicio),
                        "hora_fin": str(self.hora_fin),
                        "fecha": str(self.fecha),
                    },
                )

    def overlaps(self, other: EventTimeSlot) -> bool:
        """
        Determina si dos franjas temporales colisionan.
        Si las fechas difieren, nunca colisionan.
        Si la fecha coincide:
        - Si ambas franjas tienen horario definido: colisionan si [inicioA, finA) solapa con [inicioB, finB).
        - Si alguna de las franjas carece de hora (reserva de día completo): colisionan todo el día.
        """
        if self.fecha != other.fecha:
            return False

        # Si alguna de las dos no tiene horarios definidos, colisiona el día completo
        if self.hora_inicio is None or self.hora_fin is None:
            return True
        if other.hora_inicio is None or other.hora_fin is None:
            return True

        # Intervalos semiabiertos [hora_inicio, hora_fin)
        return self.hora_inicio < other.hora_fin and other.hora_inicio < self.hora_fin


@dataclass(frozen=True)
class SalonCapacity:
    """Capacidad máxima de comensales/asistentes permitidos en un salón."""

    max_personas: int

    def __post_init__(self) -> None:
        if self.max_personas < 0:
            raise ValueError("La capacidad del salón no puede ser negativa.")

    def can_accommodate(self, attendees: int) -> bool:
        """Verifica si la cantidad de comensales cabe en el salón (0 significa sin límite configurado)."""
        if self.max_personas == 0:
            return True
        return attendees <= self.max_personas

    def assert_can_accommodate(self, attendees: int) -> None:
        """Lanza `SalonCapacityExceededError` si los asistentes superan el aforo."""
        if not self.can_accommodate(attendees):
            raise SalonCapacityExceededError(
                f"La cantidad de comensales ({attendees}) supera el aforo máximo del salón ({self.max_personas}).",
                context={
                    "attendees": attendees,
                    "max_personas": self.max_personas,
                },
            )


@dataclass(frozen=True)
class MoneyAmount:
    """
    Importe monetario inmutable con redondeo a 2 decimales (`Decimal(14, 2)`).
    Prohíbe flotantes e importes negativos en aranceles y precios.
    """

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        rounded = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if rounded < Decimal("0.00"):
            raise InvalidMoneyAmountError(
                f"El monto monetario no puede ser negativo: {rounded}",
                context={"amount": str(rounded)},
            )
        object.__setattr__(self, "amount", rounded)

    @classmethod
    def zero(cls) -> MoneyAmount:
        """Genera un monto cero."""
        return cls(Decimal("0.00"))

    def with_vat(self, vat_percentage: Decimal = Decimal("19.00")) -> MoneyAmount:
        """Calcula el valor bruto agregando el porcentaje de IVA."""
        factor = Decimal("1.00") + (vat_percentage / Decimal("100.00"))
        bruto = (self.amount * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return MoneyAmount(bruto)

    def without_vat(self, vat_percentage: Decimal = Decimal("19.00")) -> MoneyAmount:
        """Calcula el valor neto descontando el porcentaje de IVA."""
        factor = Decimal("1.00") + (vat_percentage / Decimal("100.00"))
        neto = (self.amount / factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return MoneyAmount(neto)

    def __add__(self, other: MoneyAmount) -> MoneyAmount:
        return MoneyAmount(self.amount + other.amount)

    def __sub__(self, other: MoneyAmount) -> MoneyAmount:
        diff = self.amount - other.amount
        if diff < Decimal("0.00"):
            raise InvalidMoneyAmountError(f"Resta monetaria arroja saldo negativo: {diff}")
        return MoneyAmount(diff)

    def __mul__(self, factor: Decimal | int) -> MoneyAmount:
        fac = Decimal(str(factor))
        return MoneyAmount(self.amount * fac)


@dataclass(frozen=True)
class ItemQuantity:
    """Cantidad de insumo o materia prima con 4 decimales (`Decimal(12, 4)`)."""

    quantity: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, Decimal):
            object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        rounded = self.quantity.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if rounded <= Decimal("0.0000"):
            raise ValueError(f"La cantidad requerida debe ser estrictamente mayor a cero: {rounded}")
        object.__setattr__(self, "quantity", rounded)


__all__ = [
    "EventStatus",
    "EventTimeSlot",
    "ItemQuantity",
    "MoneyAmount",
    "SalonCapacity",
    "SalonState",
]
