"""
oppytec-backend/src/modules/procurement/domain/exceptions.py
Excepciones de dominio puro para el Módulo de Procurement (Clean Architecture y RFC 7807).
Cumple Regla 02 (Clean Architecture: 0 imports de infraestructura) y Regla 15 (i18n).
"""
from __future__ import annotations

from src.core.exceptions import DomainValidationError, OppyTecError, ProperNounImmutabilityError


class ProcurementDomainError(OppyTecError):
    """Excepción base para violaciones de reglas de negocio en procurement."""

    default_status_code = 400
    default_error_code = "PROCUREMENT_DOMAIN_ERROR"
    default_i18n_key = "procurement:errors.domain_error"
    default_title = "Procurement Domain Error"


class InvalidRutError(ProcurementDomainError, ValueError):
    """RUT chileno o Tax ID tributario internacional con formato o dígito verificador inválido."""

    default_status_code = 422
    default_error_code = "INVALID_RUT_TAX_ID"
    default_i18n_key = "procurement:errors.invalid_rut"
    default_title = "Invalid RUT or Tax ID"


class InvalidPurchaseStatusTransitionError(ProcurementDomainError, ValueError):
    """Transición de estado de orden de compra prohibida por la máquina de estados de negocio."""

    default_status_code = 400
    default_error_code = "INVALID_PURCHASE_STATUS_TRANSITION"
    default_i18n_key = "procurement:errors.invalid_status_transition"
    default_title = "Invalid Purchase Status Transition"


class NegativeQuantityError(ProcurementDomainError, ValueError):
    """Cantidad de producto negativa no permitida en operaciones de compra o recepción."""

    default_status_code = 422
    default_error_code = "NEGATIVE_QUANTITY_NOT_ALLOWED"
    default_i18n_key = "procurement:errors.negative_quantity"
    default_title = "Negative Quantity Not Allowed"


class NegativeMoneyError(ProcurementDomainError, ValueError):
    """Monto monetario negativo no permitido en adquisiciones o acuerdos de precios."""

    default_status_code = 422
    default_error_code = "NEGATIVE_MONEY_NOT_ALLOWED"
    default_i18n_key = "procurement:errors.negative_money"
    default_title = "Negative Money Not Allowed"


class ZeroDivisionPPPError(ProcurementDomainError, ZeroDivisionError):
    """División por cero en el recálculo de Costo Promedio Ponderado (PPP) sin existencias ni recepción."""

    default_status_code = 400
    default_error_code = "PPP_ZERO_DIVISION"
    default_i18n_key = "procurement:errors.ppp_zero_division"
    default_title = "Zero Division in PPP Calculation"


__all__ = [
    "DomainValidationError",
    "InvalidPurchaseStatusTransitionError",
    "InvalidRutError",
    "NegativeMoneyError",
    "NegativeQuantityError",
    "OppyTecError",
    "ProcurementDomainError",
    "ProperNounImmutabilityError",
    "ZeroDivisionPPPError",
]
