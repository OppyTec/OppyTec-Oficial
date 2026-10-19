"""
oppytec-backend/src/core/exceptions.py
Jerarquía de excepciones de dominio y aplicación mapeables a RFC 7807 (Problem Details for HTTP APIs),
con clave de internacionalización (`i18n_key`), código HTTP y correlación de `trace_id`.
Cumple Regla Inmutable 15 (i18n en el 100% de errores) y Regla 17 (Observabilidad).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rfc7807ProblemDetails:
    """Representación inmutable de RFC 7807 Problem Details con `i18n_key` y `trace_id`."""

    type: str
    title: str
    status: int
    detail: str
    i18n_key: str
    trace_id: str | None = None
    instance: str | None = None
    context: dict[str, str | int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serializa el problema a un diccionario estándar RFC 7807."""
        payload: dict[str, object] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "i18n_key": self.i18n_key,
            "context": dict(self.context),
        }
        if self.trace_id is not None:
            payload["trace_id"] = self.trace_id
        if self.instance is not None:
            payload["instance"] = self.instance
        return payload


class OppyTecError(Exception):
    """Excepción base transversal de OppyTec v2.0 mapeable a RFC 7807."""

    default_status_code: int = 400
    default_error_code: str = "OPPYTEC_DOMAIN_ERROR"
    default_i18n_key: str = "common:errors.domain_error"
    default_title: str = "Domain Rule Violation"

    def __init__(
        self,
        message: str,
        *,
        i18n_key: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        trace_id: str | None = None,
        context: dict[str, str | int] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.i18n_key: str = i18n_key or self.default_i18n_key
        self.status_code: int = status_code or self.default_status_code
        self.error_code: str = error_code or self.default_error_code
        self.trace_id: str | None = trace_id
        self.context: dict[str, str | int] = dict(context or {})

    def to_rfc7807(
        self,
        *,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> Rfc7807ProblemDetails:
        """Convierte la excepción en un objeto RFC 7807 `Rfc7807ProblemDetails`."""
        resolved_trace = trace_id if trace_id is not None else self.trace_id
        return Rfc7807ProblemDetails(
            type=f"https://oppytec.com/problems/{self.error_code.lower()}",
            title=self.default_title,
            status=self.status_code,
            detail=self.message,
            i18n_key=self.i18n_key,
            trace_id=resolved_trace,
            instance=instance,
            context=dict(self.context),
        )


class PermissionDeniedError(OppyTecError):
    """Denegación de acceso RBAC de 3 niveles, jerarquía de rangos o plan comercial."""

    default_status_code = 403
    default_error_code = "RBAC_PERMISSION_DENIED"
    default_i18n_key = "auth:errors.permission_denied"
    default_title = "RBAC Permission Denied"


class QuotaExceededError(OppyTecError):
    """Exceso de cupos de usuarios activos (`Seat Quotas`) contratados en el Plan."""

    default_status_code = 409
    default_error_code = "PLAN_SEAT_QUOTA_EXCEEDED"
    default_i18n_key = "tenancy:errors.seat_quota_exceeded"
    default_title = "Plan Seat Quota Exceeded"


class StorageQuotaExceededError(OppyTecError):
    """Exceso de cuota de memoria de imágenes/archivos (`max_storage_mb`) en Cloudflare R2."""

    default_status_code = 413
    default_error_code = "STORAGE_QUOTA_EXCEEDED"
    default_i18n_key = "storage:errors.plan_quota_exceeded"
    default_title = "Storage Quota Exceeded"


class InsufficientStockError(OppyTecError):
    """Saldo insuficiente en Kardex de bodega para completar una salida o consumo."""

    default_status_code = 409
    default_error_code = "INSUFFICIENT_STOCK"
    default_i18n_key = "inventory:errors.insufficient_stock"
    default_title = "Insufficient Warehouse Stock"


class ProperNounImmutabilityError(OppyTecError):
    """Intento de traducir un nombre propio comercial inmutable (regla 'Pollo King' / 'Savory')."""

    default_status_code = 422
    default_error_code = "PROPER_NOUN_IMMUTABILITY_VIOLATION"
    default_i18n_key = "i18n:errors.proper_noun_immutable"
    default_title = "Proper Noun Immutability Violation"


class CrossTenantAccessError(OppyTecError):
    """Intento de acceso transversal prohibido entre Holdings distintos o Tenant no autorizado."""

    default_status_code = 403
    default_error_code = "CROSS_TENANT_ACCESS_VIOLATION"
    default_i18n_key = "tenancy:errors.cross_tenant_forbidden"
    default_title = "Cross-Tenant Access Violation"
