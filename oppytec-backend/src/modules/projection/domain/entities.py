"""
oppytec-backend/src/modules/projection/domain/entities.py
Entidades de Dominio, Value Objects y Primitivas Matemáticas de Proyección.
Cumple estrictamente con Clean Architecture (DDD), 0 dependencias de infraestructura/DB,
100% Decimal con cuantización a 4 decimales (0.0001) y Cero Floats IEEE-754.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

ZERO_QTY = Decimal("0.0000")
QTY_QUANT = Decimal("0.0001")


def _ensure_decimal(val: Any, field_name: str) -> Decimal:
    """Valida y convierte a Decimal con política anti-float estricta."""
    if type(val).__name__ == "float":
        raise TypeError(
            f"Float IEEE-754 is strictly forbidden for '{field_name}' in domain layer; "
            f"use Decimal, int or str instead."
        )
    if isinstance(val, Decimal):
        return val.quantize(QTY_QUANT, ROUND_HALF_UP)
    if isinstance(val, (int, str)):
        return Decimal(str(val)).quantize(QTY_QUANT, ROUND_HALF_UP)
    raise TypeError(f"Invalid type for '{field_name}': {type(val).__name__}")


class UrgencyStatus(str, Enum):
    """
    Niveles de urgencia operativa para productos en simulación de proyección.
    Paridad 1:1 con OppyTec-Legacy frontend & backend.
    """

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def is_normal(self) -> bool:
        return self == UrgencyStatus.NORMAL

    @property
    def is_warning(self) -> bool:
        return self == UrgencyStatus.WARNING

    @property
    def is_critical(self) -> bool:
        return self == UrgencyStatus.CRITICAL

    @property
    def severity_rank(self) -> int:
        """Orden de severidad: CRITICAL (3) > WARNING (2) > NORMAL (1)."""
        ranks = {
            UrgencyStatus.NORMAL: 1,
            UrgencyStatus.WARNING: 2,
            UrgencyStatus.CRITICAL: 3,
        }
        return ranks[self]


class ProjectionHorizon(int, Enum):
    """
    Horizontes estándar de proyección temporal en días.
    """

    DAYS_7 = 7
    DAYS_15 = 15
    DAYS_30 = 30
    DAYS_60 = 60
    DAYS_90 = 90

    @classmethod
    def from_int(cls, val: int) -> ProjectionHorizon:
        for horizon in cls:
            if horizon.value == val:
                return horizon
        raise ValueError(
            f"Invalid projection horizon: {val}. Allowed: {[h.value for h in cls]}"
        )


@dataclass(frozen=True)
class DaySimulationPoint:
    """
    Punto de simulación temporal para el día `day_index` dentro del horizonte de proyección.
    Value Object inmutable con paridad matemática exacta respecto a Recharts y OppyTec-Legacy.
    """

    date: date
    day_index: int
    qty: Decimal
    status: UrgencyStatus
    status_label: str
    expiring_qty: Decimal = Decimal("0")
    event_deduction: Decimal = Decimal("0")
    events: list[dict[str, Any]] = field(default_factory=list)
    expiring_lots: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "qty", _ensure_decimal(self.qty, "qty"))
        object.__setattr__(
            self, "expiring_qty", _ensure_decimal(self.expiring_qty, "expiring_qty")
        )
        object.__setattr__(
            self,
            "event_deduction",
            _ensure_decimal(self.event_deduction, "event_deduction"),
        )
        if not isinstance(self.status, UrgencyStatus):
            object.__setattr__(self, "status", UrgencyStatus(self.status))
        if self.day_index < 0:
            raise ValueError(f"day_index must be >= 0, got {self.day_index}")

    def to_dict(self) -> dict[str, Any]:
        """Serialización canónica para JSONB persistente o payloads REST."""
        return {
            "date": self.date.isoformat(),
            "day_index": self.day_index,
            "qty": str(self.qty),
            "status": self.status.value,
            "status_label": self.status_label,
            "expiring_qty": str(self.expiring_qty),
            "event_deduction": str(self.event_deduction),
            "events": self.events,
            "expiring_lots": self.expiring_lots,
        }


@dataclass(frozen=True)
class TransferRecommendation:
    """
    Recomendación estructurada de traspaso preventivo entre bodegas para mitigar quiebres futuros.
    """

    producto_id: int
    bodega_origen_id: int
    bodega_destino_id: int
    cantidad_sugerida: Decimal
    dias_cobertura_restante_origen: int
    urgencia: UrgencyStatus

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cantidad_sugerida",
            _ensure_decimal(self.cantidad_sugerida, "cantidad_sugerida"),
        )
        if not isinstance(self.urgencia, UrgencyStatus):
            object.__setattr__(self, "urgencia", UrgencyStatus(self.urgencia))
        if self.bodega_origen_id == self.bodega_destino_id:
            raise ValueError("bodega_origen_id cannot equal bodega_destino_id")
        if self.cantidad_sugerida <= Decimal("0"):
            raise ValueError("cantidad_sugerida must be strictly positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "producto_id": self.producto_id,
            "bodega_origen_id": self.bodega_origen_id,
            "bodega_destino_id": self.bodega_destino_id,
            "cantidad_sugerida": str(self.cantidad_sugerida),
            "dias_cobertura_restante_origen": self.dias_cobertura_restante_origen,
            "urgencia": self.urgencia.value,
        }


@dataclass(frozen=True)
class SimulationResult:
    """
    Resultado global inmutable de la simulación de proyección temporal para un producto y bodega.
    """

    producto_id: int
    bodega_id: int | None
    horizon_days: int
    current_stock: Decimal
    projected_stock: Decimal
    depletion_date: date | None
    worst_status: UrgencyStatus
    worst_status_label: str
    worst_day: int | None
    daily_consumption_rate: Decimal
    curve: list[DaySimulationPoint]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "current_stock", _ensure_decimal(self.current_stock, "current_stock")
        )
        object.__setattr__(
            self,
            "projected_stock",
            _ensure_decimal(self.projected_stock, "projected_stock"),
        )
        object.__setattr__(
            self,
            "daily_consumption_rate",
            _ensure_decimal(
                self.daily_consumption_rate, "daily_consumption_rate"
            ),
        )
        if not isinstance(self.worst_status, UrgencyStatus):
            object.__setattr__(self, "worst_status", UrgencyStatus(self.worst_status))
        if self.horizon_days <= 0:
            raise ValueError(f"horizon_days must be > 0, got {self.horizon_days}")

    def to_snapshot_dict(self) -> dict[str, Any]:
        """Estructura preparada para persistencia en tabla projection_snapshots."""
        return {
            "producto_id": self.producto_id,
            "bodega_id": self.bodega_id,
            "horizon_days": self.horizon_days,
            "current_stock": str(self.current_stock),
            "projected_stock": str(self.projected_stock),
            "depletion_date": self.depletion_date.isoformat()
            if self.depletion_date
            else None,
            "worst_status": self.worst_status.value,
            "worst_status_label": self.worst_status_label,
            "worst_day": self.worst_day,
            "daily_consumption_rate": str(self.daily_consumption_rate),
            "projection_curve": [p.to_dict() for p in self.curve],
        }


@dataclass(frozen=True)
class SimulatedLot:
    """
    Representación inmutable de un lote físico para la simulación temporal FEFO.
    """

    lot_id: int | str
    quantity: Decimal
    fecha_vencimiento: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "quantity", _ensure_decimal(self.quantity, "quantity")
        )
        if self.quantity < Decimal("0"):
            raise ValueError(f"Lot quantity cannot be negative, got {self.quantity}")


@dataclass(frozen=True)
class ScheduledEventRequirement:
    """
    Requisito de consumo programado proveniente de banquetes, eventos agendados o recetas.
    """

    event_id: int | str
    event_name: str
    event_date: date
    quantity: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "quantity", _ensure_decimal(self.quantity, "quantity")
        )
        if self.quantity <= Decimal("0"):
            raise ValueError(
                f"Scheduled event requirement quantity must be positive, got {self.quantity}"
            )


@dataclass(frozen=True)
class WarehouseStockCandidate:
    """
    Candidata de bodega alternativa para la evaluación de traspasos preventivos.
    """

    bodega_id: int
    bodega_nombre: str
    available_stock: Decimal
    stock_minimo: Decimal = Decimal("0")
    daily_consumption_rate: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "available_stock",
            _ensure_decimal(self.available_stock, "available_stock"),
        )
        object.__setattr__(
            self, "stock_minimo", _ensure_decimal(self.stock_minimo, "stock_minimo")
        )
        object.__setattr__(
            self,
            "daily_consumption_rate",
            _ensure_decimal(
                self.daily_consumption_rate, "daily_consumption_rate"
            ),
        )
