"""
oppytec-backend/src/modules/inventory/application/alerts_service.py
Servicio de Aplicación Transaccional y Analítico para Alertas de Inventario (/alertas).
Orquesta la consulta agregada en PostgreSQL (< 20ms) y la emisión reactiva de eventos
WebSockets vía Redis Pub/Sub para invalidación en TanStack Query v5 sin polling.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from opentelemetry import trace

from src.core.exceptions import DomainValidationError
from src.core.observability import (
    get_tenant_telemetry_context,
    record_alert_operational_metric,
    scrub_telemetry_payload,
    trace_span,
)
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.inventory.domain.alerts import (
    AlertBadgeSummary,
    AlertsConsolidatedSummary,
    AlertsRepositoryInterface,
)
from src.modules.inventory.infrastructure.alerts_repository import (
    InMemoryAlertsRepository,
)

logger = logging.getLogger("oppytec.inventory.alerts_service")
tracer = trace.get_tracer("oppytec.inventory.alerts")


def _parse_optional_uuid(val: str | UUID | None) -> UUID | None:
    """Parsea de forma segura identificadores a UUID si corresponde."""
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception:
        return None


def _format_tenant_schema(tenant_id: str) -> str:
    """Normaliza un identificador de tenant al formato requerido de esquema tenant_*."""
    cleaned = str(tenant_id).strip().lower().replace("-", "_")
    if not cleaned.startswith("tenant_"):
        cleaned = f"tenant_{cleaned}"
    return cleaned


class InventoryAlertsService:
    """
    Servicio de aplicación para la gestión analítica y reactiva de alertas de inventario.
    """

    def __init__(self, repository: AlertsRepositoryInterface | None = None) -> None:
        self._repository: AlertsRepositoryInterface = repository or InMemoryAlertsRepository()

    @property
    def repository(self) -> AlertsRepositoryInterface:
        return self._repository

    def set_repository(self, repository: AlertsRepositoryInterface) -> None:
        """Inyecta un repositorio (ej. alternar entre Postgres e InMemory en tests)."""
        self._repository = repository

    def reset(self) -> None:
        """Reinicia el estado si el repositorio subyacente es InMemoryAlertsRepository."""
        if isinstance(self._repository, InMemoryAlertsRepository):
            self._repository.reset()

    async def get_alerts(
        self,
        tenant_id: str | None,
        bodega_ids: Sequence[int] | None = None,
        area_operativa_id: int | None = None,
        filter_type: str | None = None,
        upcoming_days: int = 30,
        reference_date: date | None = None,
    ) -> AlertsConsolidatedSummary:
        """
        Obtiene el consolidado analítico de alertas (quiebres, vencidos, próximos a vencer).
        Valida tipos y parámetros de consulta.
        Instrumentado con OpenTelemetry span 'inventory.alerts.fetch', logs estructurados y métricas.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        valid_filters = {"all", "stock", "upcoming", "expired", None, ""}
        norm_filter = (filter_type or "").lower().strip() or None

        initial_attrs: dict[str, object] = {
            "oppytec.tenant_id": str(resolved_tenant or ""),
            "tenant_id": str(resolved_tenant or ""),
            "filter_type": str(norm_filter or "all"),
            "bodega_ids": str(list(bodega_ids)) if bodega_ids is not None else "all",
            "area_operativa_id": area_operativa_id if area_operativa_id is not None else "all",
        }
        if bodega_ids is not None and len(bodega_ids) == 1:
            initial_attrs["bodega_id"] = bodega_ids[0]

        with trace_span(
            "inventory.alerts.fetch",
            attributes=initial_attrs,
            tracer_name="oppytec.inventory.alerts",
        ) as span_attrs:
            if not resolved_tenant:
                raise DomainValidationError(
                    "El identificador de tenant (tenant_id) es obligatorio",
                    i18n_key="common:errors.tenant_required",
                )
            if norm_filter and norm_filter not in valid_filters:
                raise DomainValidationError(
                    f"Tipo de filtro de alerta inválido: '{filter_type}'. Valores admitidos: all, stock, upcoming, expired",
                    i18n_key="inventory:alerts.invalid_filter_type",
                )

            if upcoming_days < 1:
                raise DomainValidationError(
                    f"La ventana de días FEFO debe ser >= 1, recibido: {upcoming_days}",
                    i18n_key="inventory:alerts.invalid_upcoming_days",
                )

            tenant_schema = _format_tenant_schema(resolved_tenant)

            summary = await self._repository.get_consolidated_alerts(
                tenant_schema=tenant_schema,
                bodega_ids=bodega_ids,
                area_operativa_id=area_operativa_id,
                tipo_filtro=norm_filter,
                dias_fefo_umbral=upcoming_days,
                reference_date=reference_date,
            )

            span_attrs["total_alerts_count"] = summary.total_count
            span_attrs["critical_count"] = summary.critical_count
            span_attrs["expired_count"] = summary.expired_count
            span_attrs["upcoming_count"] = summary.upcoming_count
            span_attrs["total_financial_risk"] = str(summary.total_financial_risk)
            span_attrs["has_critical"] = summary.has_critical

            record_alert_operational_metric(
                tenant_id=str(resolved_tenant),
                total_alerts_count=summary.total_count,
                critical_count=summary.critical_count,
                expired_count=summary.expired_count,
                upcoming_count=summary.upcoming_count,
                total_financial_risk=str(summary.total_financial_risk),
                has_critical=summary.has_critical,
            )

            return summary

    async def get_badge_summary(
        self,
        tenant_id: str | None,
        bodega_ids: Sequence[int] | None = None,
        area_operativa_id: int | None = None,
    ) -> AlertBadgeSummary:
        """
        Consulta ultraliviana para el Sidebar y la cabecera institucional (< 5ms).
        Instrumentado con OpenTelemetry span 'inventory.alerts.badge' y métricas operativas.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        initial_attrs: dict[str, object] = {
            "oppytec.tenant_id": str(resolved_tenant or ""),
            "tenant_id": str(resolved_tenant or ""),
            "bodega_ids": str(list(bodega_ids)) if bodega_ids is not None else "all",
            "area_operativa_id": area_operativa_id if area_operativa_id is not None else "all",
        }
        if bodega_ids is not None and len(bodega_ids) == 1:
            initial_attrs["bodega_id"] = bodega_ids[0]

        with trace_span(
            "inventory.alerts.badge",
            attributes=initial_attrs,
            tracer_name="oppytec.inventory.alerts",
        ) as span_attrs:
            if not resolved_tenant:
                raise DomainValidationError(
                    "El identificador de tenant (tenant_id) es obligatorio",
                    i18n_key="common:errors.tenant_required",
                )
            _ = area_operativa_id
            tenant_schema = _format_tenant_schema(resolved_tenant)

            badge = await self._repository.get_badge_summary(
                tenant_schema=tenant_schema,
                bodega_ids=bodega_ids,
            )
            span_attrs["total_count"] = badge.total_count
            span_attrs["has_critical"] = badge.has_critical
            span_attrs["critical_stock_count"] = badge.critical_stock_count
            span_attrs["expired_count"] = badge.expired_count
            span_attrs["upcoming_count"] = badge.upcoming_count
            return badge

    async def broadcast_alerts_changed(
        self,
        tenant_id: str | UUID,
        holding_id: str | UUID | None = None,
        target_bodega_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Emite una notificación reactiva WebSocket (Redis Pub/Sub) para informar cambios en el estado
        de alertas de inventario e invalidar inmediatamente las consultas en TanStack Query v5.
        Instrumentado con OpenTelemetry span 'inventory.alerts.broadcast' y redacción PII determinista.
        """
        resolved_tenant = str(tenant_id) if tenant_id else (get_tenant_telemetry_context().tenant_id or "")
        safe_payload = scrub_telemetry_payload(
            payload
            or {
                "action": "alerts_changed",
                "tenant_id": str(tenant_id),
                "bodega_id": target_bodega_id,
            }
        )
        initial_attrs: dict[str, object] = {
            "oppytec.tenant_id": resolved_tenant,
            "tenant_id": resolved_tenant,
            "event_type": "inventory.alerts.changed",
        }
        if holding_id:
            initial_attrs["holding_id"] = str(holding_id)
        if target_bodega_id is not None:
            initial_attrs["target_bodega_id"] = target_bodega_id
            initial_attrs["bodega_id"] = target_bodega_id

        with trace_span(
            "inventory.alerts.broadcast",
            attributes=initial_attrs,
            tracer_name="oppytec.inventory.alerts",
        ) as span_attrs:
            try:
                publisher = get_realtime_publisher()
                envelope = RealtimeEventEnvelope(
                    event_type="inventory.alerts.changed",
                    holding_id=_parse_optional_uuid(holding_id),
                    tenant_id=_parse_optional_uuid(tenant_id),
                    target_bodega_id=target_bodega_id,
                    required_permission="inventory.alerts.read",
                    query_keys_to_invalidate=[
                        ["inventory", "alerts"],
                        ["inventory", "alerts", "badge"],
                    ],
                    payload=safe_payload,
                )
                await publisher.publish_event(envelope)
                span_attrs["published"] = True
            except Exception as exc:
                logger.warning(
                    "No se pudo emitir evento WebSocket 'inventory.alerts.changed': %s",
                    str(exc),
                )
                span_attrs["published"] = False
                span_attrs["broadcast_warning"] = str(exc)


__all__ = [
    "InventoryAlertsService",
]
