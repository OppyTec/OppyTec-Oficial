"""
oppytec-backend/src/modules/invoices/domain/exceptions.py
Excepciones puras de dominio para el Módulo de Facturas y Contabilidad (Clean Architecture).
Aisladas de frameworks HTTP y de infraestructura; mapeables a RFC 7807 mediante OppyTecError.
"""
from __future__ import annotations

from typing import Any

from src.core.exceptions import OppyTecError


class InvoiceDomainError(OppyTecError):
    """Excepción base para violaciones de reglas de negocio en el módulo de facturas."""

    default_status_code = 400
    default_error_code = "INVOICE_DOMAIN_ERROR"
    default_i18n_key = "invoices:errors.domain_error"
    default_title = "Invoice Domain Error"


class InvalidRUTError(InvoiceDomainError, ValueError):
    """Identificador tributario chileno (RUT) o extranjero con formato o dígito verificador inválido."""

    default_status_code = 422
    default_error_code = "INVALID_RUT_TAX_ID"
    default_i18n_key = "invoices:errors.invalid_rut"
    default_title = "Invalid RUT Tax ID"


class InvoiceTotalMismatchError(InvoiceDomainError, ValueError):
    """Invariante contable violada: El total del documento difiere de la suma de neto + IVA."""

    default_status_code = 422
    default_error_code = "INVOICE_TOTAL_MISMATCH"
    default_i18n_key = "invoices:errors.total_mismatch"
    default_title = "Invoice Accounting Total Mismatch"


class InvalidPackagingFactorError(InvoiceDomainError, ValueError):
    """Factor de conversión de empaque inválido (debe ser estrictamente mayor a 0)."""

    default_status_code = 422
    default_error_code = "INVALID_PACKAGING_FACTOR"
    default_i18n_key = "invoices:errors.invalid_packaging_factor"
    default_title = "Invalid Packaging Factor"


class SupplierAliasAlreadyExistsError(InvoiceDomainError):
    """El alias del proveedor para el producto ya existe en el catálogo del tenant."""

    default_status_code = 409
    default_error_code = "SUPPLIER_ALIAS_ALREADY_EXISTS"
    default_i18n_key = "invoices:errors.alias_already_exists"
    default_title = "Supplier Product Alias Already Exists"


class InvalidInvoiceStatusTransitionError(InvoiceDomainError, ValueError):
    """Transición de estado de la factura no permitida por el ciclo de vida de negocio."""

    default_status_code = 400
    default_error_code = "INVALID_INVOICE_STATUS_TRANSITION"
    default_i18n_key = "invoices:errors.invalid_status_transition"
    default_title = "Invalid Invoice Status Transition"


class PriceDriftThresholdExceededError(InvoiceDomainError):
    """Alerta de variación abrupta de precio de compra por sobre el umbral tolerado."""

    default_status_code = 422
    default_error_code = "PRICE_DRIFT_THRESHOLD_EXCEEDED"
    default_i18n_key = "invoices:errors.price_drift_exceeded"
    default_title = "Price Drift Threshold Exceeded"
