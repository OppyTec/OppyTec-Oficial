"""
oppytec-backend/src/modules/events/domain/exceptions.py
Jerarquía de excepciones de dominio para el Módulo de Eventos y Salones.
Alineado con RFC 7807 (Problem Details) e internacionalización i18n canónica.
"""
from __future__ import annotations

from src.core.exceptions import OppyTecError


class EventsDomainError(OppyTecError):
    """Excepción base para violaciones de reglas de negocio en eventos y salones."""

    default_status_code = 400
    default_error_code = "EVENTS_DOMAIN_ERROR"
    default_i18n_key = "events:errors.domain_error"
    default_title = "Events Domain Rule Violation"


class EventNotFoundError(EventsDomainError):
    """El evento solicitado no existe en el inquilino."""

    default_status_code = 404
    default_error_code = "EVENT_NOT_FOUND"
    default_i18n_key = "events:errors.event_not_found"
    default_title = "Event Not Found"


class SalonNotFoundError(EventsDomainError):
    """El salón o espacio físico solicitado no existe en el inquilino."""

    default_status_code = 404
    default_error_code = "SALON_NOT_FOUND"
    default_i18n_key = "events:errors.salon_not_found"
    default_title = "Salon Not Found"


class EventOverbookingError(EventsDomainError):
    """Conflicto de sobreventa u overbooking temporal en un salón para la franja solicitada."""

    default_status_code = 409
    default_error_code = "EVENT_OVERBOOKING_ERROR"
    default_i18n_key = "events:errors.overbooking"
    default_title = "Salon Overbooking Conflict"


class SalonCapacityExceededError(EventsDomainError):
    """La cantidad de asistentes supera la capacidad máxima habilitada del salón."""

    default_status_code = 422
    default_error_code = "SALON_CAPACITY_EXCEEDED"
    default_i18n_key = "events:errors.capacity_exceeded"
    default_title = "Salon Capacity Exceeded"


class EventAlreadyExecutedError(EventsDomainError):
    """El evento ya fue ejecutado en Kardex y no admite modificaciones ni re-ejecución."""

    default_status_code = 409
    default_error_code = "EVENT_ALREADY_EXECUTED"
    default_i18n_key = "events:errors.already_executed"
    default_title = "Event Already Executed"


class EventAlreadyCancelledError(EventsDomainError):
    """El evento ya fue cancelado y no puede ser ejecutado ni reactivado sin autorización."""

    default_status_code = 409
    default_error_code = "EVENT_ALREADY_CANCELLED"
    default_i18n_key = "events:errors.already_cancelled"
    default_title = "Event Already Cancelled"


class InvalidEventTimeSlotError(EventsDomainError):
    """La franja horaria del evento es inconsistente (hora fin menor o igual a hora inicio)."""

    default_status_code = 422
    default_error_code = "INVALID_EVENT_TIME_SLOT"
    default_i18n_key = "events:errors.invalid_timeslot"
    default_title = "Invalid Event Time Slot"


class InvalidMoneyAmountError(EventsDomainError):
    """El monto monetario o arancel es inválido o negativo."""

    default_status_code = 422
    default_error_code = "INVALID_MONEY_AMOUNT"
    default_i18n_key = "events:errors.invalid_money"
    default_title = "Invalid Money Amount"


class EventStatusTransitionError(EventsDomainError):
    """Transición de estado del ciclo de vida del evento no permitida."""

    default_status_code = 422
    default_error_code = "INVALID_STATUS_TRANSITION"
    default_i18n_key = "events:errors.invalid_status_transition"
    default_title = "Invalid Status Transition"


class EventItemNotFoundError(EventsDomainError):
    """El ítem, receta o combo especificado no pertenece al evento."""

    default_status_code = 404
    default_error_code = "EVENT_ITEM_NOT_FOUND"
    default_i18n_key = "events:errors.item_not_found"
    default_title = "Event Item Not Found"


__all__ = [
    "EventAlreadyCancelledError",
    "EventAlreadyExecutedError",
    "EventItemNotFoundError",
    "EventNotFoundError",
    "EventOverbookingError",
    "EventStatusTransitionError",
    "EventsDomainError",
    "InvalidEventTimeSlotError",
    "InvalidMoneyAmountError",
    "SalonCapacityExceededError",
    "SalonNotFoundError",
]
