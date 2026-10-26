"""
oppytec-backend/src/core/observability.py
Instrumentación Central de los 4 Pilares de Observabilidad de OppyTec v2.0:
1. OpenTelemetry (X-Trace-ID / W3C traceparent, Spans con InMemorySpanExporter para CI/Tests).
2. Grafana LGTM (Logs estructurados JSON con contexto Multi-Tenant).
3. Sentry / GlitchTip (Filtro determinista de redacción PII / SecretStr: scrub_telemetry_payload).
4. Umami Analytics (Gobernanza de analítica de producto sin cookies por entorno).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
import re

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import SecretStr
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

REDACTED_MARKER: str = "[REDACTED_PII]"

SENSITIVE_KEY_TOKENS: tuple[str, ...] = (
    "password",
    "hashed_password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "x-api-key",
    "rut",
    "tax_id",
    "credit_card",
    "cvv",
    "dsn",
    "private_key",
)

AUDIT_USER_PII_TOKENS: tuple[str, ...] = (
    "email",
    "mail",
    "correo",
    "username",
    "user_name",
    "nombre_usuario",
    "user_display_name",
    "nombre_visible",
)

_EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


@dataclass(frozen=True)
class TenantTelemetryContext:
    """Contexto inmutable de trazabilidad Multi-Tenant inyectado en logs JSON y spans OTel."""

    trace_id: str
    environment: str = "local"
    env_namespace: str = "default"
    holding_id: str | None = None
    tenant_id: str | None = None
    tenant_schema: str | None = None
    user_id: str | None = None
    role_rank: int | None = None
    ui_language: str = "es"
    display_currency: str = "CLP"

    def to_attributes(self) -> dict[str, str | int]:
        """Convierte el contexto en atributos estándar de OpenTelemetry y Loki."""
        attrs: dict[str, str | int] = {
            "oppytec.trace_id": self.trace_id,
            "service.environment": self.environment,
            "service.namespace": self.env_namespace,
            "oppytec.ui_language": self.ui_language,
            "oppytec.display_currency": self.display_currency,
        }
        if self.holding_id is not None:
            attrs["oppytec.holding_id"] = self.holding_id
        if self.tenant_id is not None:
            attrs["oppytec.tenant_id"] = self.tenant_id
        if self.tenant_schema is not None:
            attrs["oppytec.tenant_schema"] = self.tenant_schema
        if self.user_id is not None:
            attrs["oppytec.user_id"] = self.user_id
        if self.role_rank is not None:
            attrs["oppytec.role_rank"] = self.role_rank
        return attrs


@dataclass(frozen=True)
class SpanRecord:
    """Registro de span determinista para inspección en memoria (CI / Tests de Arquitectura)."""

    name: str
    trace_id: str
    span_id: str
    duration_ms: float
    status_code: int
    attributes: dict[str, str | int | float | bool] = field(default_factory=dict)


class InMemorySpanExporter:
    """Exportador de spans en memoria RAM para ENVIRONMENT='ci' y pruebas de observabilidad."""

    def __init__(self) -> None:
        self._spans: list[SpanRecord] = []

    def export(self, span: SpanRecord) -> None:
        self._spans.append(span)

    def get_finished_spans(self) -> list[SpanRecord]:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()


@dataclass(frozen=True)
class QuotaSemaphoreMetric:
    """Métrica determinista del semáforo preventivo de cuota (NORMAL, WARNING, CRITICAL, OVER_QUOTA)."""

    resource_type: str
    status: str
    usage_percentage: float
    active_count: int
    effective_max_limit: int
    tenant_id: str | None = None
    holding_id: str | None = None
    trace_id: str = ""
    timestamp: str = ""


_in_memory_quota_metrics: list[QuotaSemaphoreMetric] = []


def get_in_memory_quota_metrics() -> list[QuotaSemaphoreMetric]:
    """Devuelve las métricas de semáforo de cuota registradas en memoria."""
    return list(_in_memory_quota_metrics)


def clear_in_memory_quota_metrics() -> None:
    """Limpia las métricas de semáforo de cuota en memoria."""
    _in_memory_quota_metrics.clear()


@dataclass(frozen=True)
class InventoryOperationMetric:
    """Métrica determinista de operaciones de inventario y Kardex."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    bodega_id: int | None = None
    user_id: str | None = None
    timestamp: str = ""


_in_memory_inventory_metrics: list[InventoryOperationMetric] = []


def get_in_memory_inventory_metrics() -> list[InventoryOperationMetric]:
    """Devuelve las métricas de operaciones de inventario registradas en memoria."""
    return list(_in_memory_inventory_metrics)


def clear_in_memory_inventory_metrics() -> None:
    """Limpia las métricas de inventario en memoria."""
    _in_memory_inventory_metrics.clear()


@dataclass(frozen=True)
class AlertOperationalMetric:
    """Métrica determinista del consolidado y salud de alertas de inventario."""

    tenant_id: str
    total_alerts_count: int
    critical_count: int
    expired_count: int
    upcoming_count: int
    total_financial_risk: str
    has_critical: bool
    timestamp: str = ""


_in_memory_alerts_metrics: list[AlertOperationalMetric] = []


def get_in_memory_alerts_metrics() -> list[AlertOperationalMetric]:
    """Devuelve las métricas operativas de alertas registradas en memoria."""
    return list(_in_memory_alerts_metrics)


def clear_in_memory_alerts_metrics() -> None:
    """Limpia las métricas operativas de alertas en memoria."""
    _in_memory_alerts_metrics.clear()


def record_alert_operational_metric(
    *,
    tenant_id: str,
    total_alerts_count: int,
    critical_count: int,
    expired_count: int,
    upcoming_count: int,
    total_financial_risk: str,
    has_critical: bool,
) -> AlertOperationalMetric:
    """Registra una métrica operativa de alertas en memoria."""
    metric = AlertOperationalMetric(
        tenant_id=tenant_id,
        total_alerts_count=total_alerts_count,
        critical_count=critical_count,
        expired_count=expired_count,
        upcoming_count=upcoming_count,
        total_financial_risk=total_financial_risk,
        has_critical=has_critical,
        timestamp=datetime.now(UTC).isoformat(),
    )
    _in_memory_alerts_metrics.append(metric)
    return metric


_current_trace_id_var: ContextVar[str] = ContextVar("oppytec_trace_id", default="")
_current_tenant_ctx_var: ContextVar[TenantTelemetryContext | None] = ContextVar(
    "oppytec_tenant_telemetry_ctx", default=None
)
_in_memory_exporter = InMemorySpanExporter()


def get_in_memory_exporter() -> InMemorySpanExporter:
    """Devuelve el exportador de spans en memoria."""
    return _in_memory_exporter


def get_current_trace_id() -> str:
    """Obtiene el X-Trace-ID activo en el contexto asíncrono actual o genera uno nuevo."""
    trace_id = _current_trace_id_var.get()
    if not trace_id:
        trace_id = uuid.uuid4().hex
        _current_trace_id_var.set(trace_id)
    return trace_id


def get_tenant_telemetry_context() -> TenantTelemetryContext:
    """Obtiene el contexto de telemetría multi-tenant activo."""
    ctx = _current_tenant_ctx_var.get()
    if ctx is not None:
        return ctx
    return TenantTelemetryContext(trace_id=get_current_trace_id())


def bind_tenant_telemetry_context(
    *,
    trace_id: str | None = None,
    environment: str = "local",
    env_namespace: str = "default",
    holding_id: str | None = None,
    tenant_id: str | None = None,
    tenant_schema: str | None = None,
    user_id: str | None = None,
    role_rank: int | None = None,
    ui_language: str = "es",
    display_currency: str = "CLP",
) -> tuple[Token[str], Token[TenantTelemetryContext | None]]:
    """Asocia el contexto del Tenant e idioma/moneda al ContextVar de la petición actual."""
    resolved_trace = trace_id or get_current_trace_id()
    trace_token = _current_trace_id_var.set(resolved_trace)
    ctx = TenantTelemetryContext(
        trace_id=resolved_trace,
        environment=environment,
        env_namespace=env_namespace,
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema=tenant_schema,
        user_id=user_id,
        role_rank=role_rank,
        ui_language=ui_language,
        display_currency=display_currency,
    )
    ctx_token = _current_tenant_ctx_var.set(ctx)
    return trace_token, ctx_token


def reset_tenant_telemetry_context(
    tokens: tuple[Token[str], Token[TenantTelemetryContext | None]],
) -> None:
    """Restaura los ContextVars al finalizar la petición."""
    trace_token, ctx_token = tokens
    _current_trace_id_var.reset(trace_token)
    _current_tenant_ctx_var.reset(ctx_token)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(token.replace("-", "_") in normalized for token in SENSITIVE_KEY_TOKENS)


def _scrub_value(value: object) -> object:
    if isinstance(value, SecretStr):
        return REDACTED_MARKER
    if isinstance(value, Mapping):
        return {
            str(k): (
                REDACTED_MARKER if _is_sensitive_key(str(k)) else _scrub_value(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(item) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_scrub_value(item) for item in value]
    return value


def scrub_telemetry_payload(payload: dict[str, object]) -> dict[str, object]:
    """
    Función pura y determinista que redacta recursivamente con '[REDACTED_PII]'
    cualquier clave sensible (password, hashed_password, secret, token, authorization,
    cookie, api_key, rut, tax_id, credit_card, cvv) o instancia de SecretStr.
    """
    scrubbed: dict[str, object] = {}
    for key, val in payload.items():
        if _is_sensitive_key(key) or isinstance(val, SecretStr):
            scrubbed[key] = REDACTED_MARKER
        else:
            scrubbed[key] = _scrub_value(val)
    return scrubbed


def format_structured_log(
    level: str,
    event: str,
    payload: dict[str, object] | None = None,
) -> str:
    """Genera una línea JSON estructurada con contexto multi-tenant y redacción PII."""
    ctx = get_tenant_telemetry_context()
    safe_payload = scrub_telemetry_payload(payload or {})
    resolved_tenant = ctx.tenant_id or (
        str(safe_payload["tenant_id"])
        if "tenant_id" in safe_payload and safe_payload["tenant_id"] is not None
        else None
    )
    resolved_holding = ctx.holding_id or (
        str(safe_payload["holding_id"])
        if "holding_id" in safe_payload and safe_payload["holding_id"] is not None
        else None
    )
    record: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper(),
        "event": event,
        "trace_id": ctx.trace_id,
        "environment": ctx.environment,
        "env_namespace": ctx.env_namespace,
        "holding_id": resolved_holding,
        "tenant_id": resolved_tenant,
        "tenant_schema": ctx.tenant_schema,
        "data": safe_payload,
    }
    return json.dumps(record, ensure_ascii=False)


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, object] | None = None,
    tracer_name: str = "oppytec.inventory",
) -> Iterator[dict[str, object]]:
    """
    Context manager de observabilidad 4-pilares para operaciones críticas:
    1. Inicia un span con OpenTelemetry (opentelemetry.trace.get_tracer).
    2. Enlaza atributos enriquecidos (tenant_id, bodega_id, user_id, items_count, transfer_uuid, etc.).
    3. Redacta PII/SecretStr de forma determinista usando scrub_telemetry_payload.
    4. Registra métrica e inyecta SpanRecord en InMemorySpanExporter.
    5. Captura excepciones limpiamente, registra status ERROR en OTel y emite log estructurado JSON.
    """
    start_ns = time.perf_counter_ns()
    ctx = get_tenant_telemetry_context()
    resolved_trace = ctx.trace_id or get_current_trace_id()
    span_id = uuid.uuid4().hex[:16]

    dynamic_attrs: dict[str, object] = dict(attributes or {})
    if ctx.tenant_id and "tenant_id" not in dynamic_attrs:
        dynamic_attrs["tenant_id"] = ctx.tenant_id
    if ctx.user_id and "user_id" not in dynamic_attrs:
        dynamic_attrs["user_id"] = ctx.user_id

    tracer = trace.get_tracer(tracer_name)
    span_status_code = 200
    status_str = "SUCCESS"

    with tracer.start_as_current_span(name) as otel_span:
        for k, v in dynamic_attrs.items():
            if v is not None:
                otel_span.set_attribute(str(k), v if isinstance(v, (bool, str, int, float)) else str(v))

        try:
            yield dynamic_attrs
            otel_span.set_status(Status(StatusCode.OK))
            safe_payload = scrub_telemetry_payload(dynamic_attrs)
            logging.getLogger(tracer_name).info(
                format_structured_log("INFO", name, safe_payload)
            )
        except Exception as exc:
            status_str = "ERROR"
            from src.core.exceptions import OppyTecError

            span_status_code = exc.status_code if isinstance(exc, OppyTecError) else 500
            otel_span.record_exception(exc)
            otel_span.set_status(Status(StatusCode.ERROR, str(exc)))
            err_payload = scrub_telemetry_payload(
                {
                    **dynamic_attrs,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            logging.getLogger(tracer_name).error(
                format_structured_log("ERROR", name, err_payload)
            )
            raise
        finally:
            duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            clean_attrs = scrub_telemetry_payload(dynamic_attrs)
            for k, v in clean_attrs.items():
                if v is not None:
                    otel_span.set_attribute(str(k), v if isinstance(v, (bool, str, int, float)) else str(v))

            raw_bodega = dynamic_attrs.get("bodega_id")
            metric_bodega: int | None = None
            if raw_bodega is not None:
                try:
                    metric_bodega = int(str(raw_bodega))
                except (ValueError, TypeError):
                    metric_bodega = None

            raw_tenant = dynamic_attrs.get("tenant_id")
            metric_tenant = str(raw_tenant) if raw_tenant is not None else ctx.tenant_id

            raw_user = dynamic_attrs.get("user_id")
            metric_user = str(raw_user) if raw_user is not None else ctx.user_id

            if metric_tenant is not None:
                otel_span.set_attribute("oppytec.tenant_id", metric_tenant)
            if metric_user is not None:
                otel_span.set_attribute("oppytec.user_id", metric_user)

            merged_attrs: dict[str, str | int | float | bool] = {
                **ctx.to_attributes(),
                **{
                    str(k): (v if isinstance(v, (str, int, float, bool)) else str(v))
                    for k, v in clean_attrs.items()
                    if v is not None
                },
            }
            if metric_tenant is not None:
                merged_attrs["oppytec.tenant_id"] = metric_tenant
                merged_attrs["tenant_id"] = metric_tenant
            if metric_user is not None:
                merged_attrs["oppytec.user_id"] = metric_user
                merged_attrs["user_id"] = metric_user

            record = SpanRecord(
                name=name,
                trace_id=resolved_trace,
                span_id=span_id,
                duration_ms=round(duration_ms, 3),
                status_code=span_status_code,
                attributes=merged_attrs,
            )
            _in_memory_exporter.export(record)

            metric = InventoryOperationMetric(
                operation=name,
                status=status_str,
                duration_ms=round(duration_ms, 3),
                tenant_id=metric_tenant,
                bodega_id=metric_bodega,
                user_id=metric_user,
                timestamp=datetime.now(UTC).isoformat(),
            )
            _in_memory_inventory_metrics.append(metric)


def record_quota_semaphore_metric(
    *,
    resource_type: str,
    status: str,
    usage_percentage: float | Decimal,
    active_count: int,
    effective_max_limit: int,
    tenant_id: str | None = None,
    holding_id: str | None = None,
    details: dict[str, object] | None = None,
) -> QuotaSemaphoreMetric:
    """
    Registra una métrica de semáforo de cuota (NORMAL <80%, WARNING >=80%, CRITICAL >=95%, OVER_QUOTA 100%):
    - Exporta un Span a InMemorySpanExporter para trazabilidad en cascada OTel.
    - Genera log estructurado JSON si el estado es WARNING, CRITICAL u OVER_QUOTA.
    - Aplica scrub_telemetry_payload garantizando CERO fuga de PII o SecretStr.
    """
    ctx = get_tenant_telemetry_context()
    resolved_tenant = tenant_id or ctx.tenant_id
    resolved_holding = holding_id or ctx.holding_id
    resolved_trace = ctx.trace_id or get_current_trace_id()
    pct_float = float(usage_percentage)

    metric = QuotaSemaphoreMetric(
        resource_type=resource_type,
        status=status.upper(),
        usage_percentage=round(pct_float, 2),
        active_count=active_count,
        effective_max_limit=effective_max_limit,
        tenant_id=resolved_tenant,
        holding_id=resolved_holding,
        trace_id=resolved_trace,
        timestamp=datetime.now(UTC).isoformat(),
    )
    _in_memory_quota_metrics.append(metric)

    span = SpanRecord(
        name=f"quota.semaphore.{resource_type}",
        trace_id=resolved_trace,
        span_id=uuid.uuid4().hex[:16],
        duration_ms=0.0,
        status_code=429 if status.upper() == "OVER_QUOTA" else 200,
        attributes={
            "oppytec.quota.resource_type": resource_type,
            "oppytec.quota.status": status.upper(),
            "oppytec.quota.usage_pct": round(pct_float, 2),
            "oppytec.quota.active_count": active_count,
            "oppytec.quota.effective_limit": effective_max_limit,
            "oppytec.tenant_id": resolved_tenant or "",
            "oppytec.holding_id": resolved_holding or "",
            **ctx.to_attributes(),
        },
    )
    _in_memory_exporter.export(span)

    if status.upper() in ("WARNING", "CRITICAL", "OVER_QUOTA"):
        log_level = (
            "WARNING"
            if status.upper() == "WARNING"
            else ("ERROR" if status.upper() == "CRITICAL" else "CRITICAL")
        )
        safe_details = scrub_telemetry_payload(details or {})
        payload: dict[str, object] = {
            "resource_type": resource_type,
            "status": status.upper(),
            "usage_pct": round(pct_float, 2),
            "active_count": active_count,
            "effective_limit": effective_max_limit,
            **safe_details,
        }
        format_structured_log(log_level, f"quota.semaphore.{status.lower()}", payload)

    return metric


def emit_plan_audit_log(
    action: str,
    plan_slug: str,
    details: dict[str, object] | None = None,
) -> str:
    """Emite log estructurado JSON de auditoría de planes con redacción PII determinista."""
    payload: dict[str, object] = {"plan_slug": plan_slug, **(details or {})}
    return format_structured_log("INFO", f"plan.audit.{action}", payload)


def emit_tenant_provisioning_audit_log(
    action: str,
    tenant_id: str,
    holding_id: str,
    schema_name: str,
    details: dict[str, object] | None = None,
) -> str:
    """Emite log estructurado JSON de aprovisionamiento de tenants con redacción PII determinista."""
    payload: dict[str, object] = {
        "tenant_id": tenant_id,
        "holding_id": holding_id,
        "schema_name": schema_name,
        **(details or {}),
    }
    return format_structured_log("INFO", f"tenant.provisioning.{action}", payload)


def emit_quota_audit_log(
    action: str,
    resource_type: str,
    status: str,
    details: dict[str, object] | None = None,
) -> str:
    """Emite log estructurado JSON de auditoría de cuotas con redacción PII determinista."""
    payload: dict[str, object] = {
        "resource_type": resource_type,
        "status": status.upper(),
        **(details or {}),
    }
    level = (
        "WARNING"
        if status.upper() in ("WARNING", "CRITICAL")
        else ("CRITICAL" if status.upper() == "OVER_QUOTA" else "INFO")
    )
    return format_structured_log(level, f"quota.audit.{action}", payload)


def extract_trace_id_from_headers(headers: Mapping[str, str]) -> str:
    """Extrae el trace_id desde X-Trace-ID o cabecera W3C traceparent, o genera un UUID4."""
    lower_headers = {k.lower(): v.strip() for k, v in headers.items()}
    explicit_trace = lower_headers.get("x-trace-id", "")
    if explicit_trace and 8 <= len(explicit_trace) <= 64:
        return explicit_trace

    traceparent = lower_headers.get("traceparent", "")
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) == 4 and len(parts[1]) == 32:
            return parts[1]

    return uuid.uuid4().hex


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware ASGI/FastAPI que:
    1. Extrae o genera el X-Trace-ID (compatible con W3C traceparent).
    2. Inyecta el contexto Multi-Tenant (tenant_id, holding_id, environment, env_namespace).
    3. Registra el Span en InMemorySpanExporter cuando corresponde y añade la cabecera X-Trace-ID.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        environment: str = "local",
        env_namespace: str = "default",
        otel_exporter: str = "none",
    ) -> None:
        super().__init__(app)
        self._environment = environment
        self._env_namespace = env_namespace
        self._otel_exporter = otel_exporter
        self._logger = logging.getLogger("oppytec.observability")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = extract_trace_id_from_headers(request.headers)
        holding_id = request.headers.get("x-holding-id")
        tenant_id = request.headers.get("x-tenant-id")
        tenant_schema = request.headers.get("x-tenant-schema")
        ui_lang = request.headers.get("accept-language", "es")[:2].lower() or "es"
        display_currency = request.headers.get("x-display-currency", "CLP").upper()

        tokens = bind_tenant_telemetry_context(
            trace_id=trace_id,
            environment=self._environment,
            env_namespace=self._env_namespace,
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            ui_language=ui_lang,
            display_currency=display_currency,
        )
        start_ns = time.perf_counter_ns()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            response.headers["X-Trace-ID"] = trace_id

            if self._otel_exporter in ("memory", "otlp"):
                ctx = get_tenant_telemetry_context()
                span = SpanRecord(
                    name=f"{request.method} {request.url.path}",
                    trace_id=trace_id,
                    span_id=uuid.uuid4().hex[:16],
                    duration_ms=round(duration_ms, 3),
                    status_code=response.status_code,
                    attributes={
                        "http.method": request.method,
                        "http.route": request.url.path,
                        "http.status_code": response.status_code,
                        **ctx.to_attributes(),
                    },
                )
                _in_memory_exporter.export(span)

            return response
        finally:
            reset_tenant_telemetry_context(tokens)
