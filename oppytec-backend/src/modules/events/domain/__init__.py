"""
oppytec-backend/src/modules/events/domain/__init__.py
Capa de Dominio Puro para el Módulo de Eventos, Salones y Banquetes.
"""
from src.modules.events.domain.entities import (
    Evento,
    EventoCombo,
    EventoConsumoKardex,
    EventoItem,
    EventoReceta,
    EventoTrabajador,
    Salon,
)
from src.modules.events.domain.exceptions import (
    EventAlreadyCancelledError,
    EventAlreadyExecutedError,
    EventItemNotFoundError,
    EventNotFoundError,
    EventOverbookingError,
    EventsDomainError,
    EventStatusTransitionError,
    InvalidEventTimeSlotError,
    InvalidMoneyAmountError,
    SalonCapacityExceededError,
    SalonNotFoundError,
)
from src.modules.events.domain.repositories import (
    EventRepositoryProtocol,
    SalonRepositoryProtocol,
)
from src.modules.events.domain.value_objects import (
    EventStatus,
    EventTimeSlot,
    ItemQuantity,
    MoneyAmount,
    SalonCapacity,
    SalonState,
)

__all__ = [
    "EventAlreadyCancelledError",
    "EventAlreadyExecutedError",
    "EventItemNotFoundError",
    "EventNotFoundError",
    "EventOverbookingError",
    "EventRepositoryProtocol",
    "EventStatus",
    "EventStatusTransitionError",
    "EventTimeSlot",
    "Evento",
    "EventoCombo",
    "EventoConsumoKardex",
    "EventoItem",
    "EventoReceta",
    "EventoTrabajador",
    "EventsDomainError",
    "InvalidEventTimeSlotError",
    "InvalidMoneyAmountError",
    "ItemQuantity",
    "MoneyAmount",
    "Salon",
    "SalonCapacity",
    "SalonCapacityExceededError",
    "SalonNotFoundError",
    "SalonRepositoryProtocol",
    "SalonState",
]
