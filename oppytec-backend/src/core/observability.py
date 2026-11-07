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
import sys
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
import re

from opentelemetry import metrics as otel_metrics
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import SecretStr
import structlog
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
    "card_number",
    "tarjeta",
    "cvv",
    "dsn",
    "private_key",
    "email_contacto",
    "email",
    "correo",
    "telefono",
    "phone",
    "direccion",
    "address",
    "bank_account",
    "account_number",
    "numero_cuenta",
    "cuenta_bancaria",
    "cta_cte",
    "cbu",
    "clabe",
    "iban",
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
_RUT_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:\d{1,2}\.\d{3}\.\d{3}-[\dkK]|\d{7,8}-[\dkK](?![0-9a-fA-F-]))\b"
)
_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(?:\+56\s*9?\s*\d{4}\s*\d{4})\b"
)
_CREDIT_CARD_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![0-9a-fA-F-])(?:\d{4}[-\s]?\d{6}[-\s]?\d{5}|(?:\d{4}[-\s]?){3}\d{4})(?![0-9a-fA-F-])"
)
_BEARER_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"
)
_INLINE_SECRET_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)\b(password|passwd|secret|token|api_key|apikey|cvv)\s*[:=]\s*[^\s,;]+"
)
_PAYMENT_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:tok|pay|card|cus|tbk|mp)_[a-zA-Z0-9_-]{12,}\b|\b(?:sk|pk)_(?:live|test)_[a-zA-Z0-9]{12,}\b"
)
_BANK_ACCOUNT_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)\b(?:cta(?:\.|\s+cte)?|cuenta(?:\s+corriente|\s+vista|\s+rut)?)\s*[:#]?\s*[\d\-]{6,20}\b"
)


def scrub_pii_text(text: str | None) -> str | None:
    """
    Enmascara de forma determinista patrones PII (correos electrónicos, RUT chileno,
    teléfonos, tarjetas de crédito, cuentas bancarias, tokens Bearer, tokens de pago y secretos inline) en textos libres, notas o metadatos.
    """
    if text is None or not text:
        return text
    result = _EMAIL_PATTERN.sub(REDACTED_MARKER, text)
    result = _RUT_PATTERN.sub(REDACTED_MARKER, result)
    result = _PHONE_PATTERN.sub(REDACTED_MARKER, result)
    result = _PAYMENT_TOKEN_PATTERN.sub(REDACTED_MARKER, result)
    result = _CREDIT_CARD_PATTERN.sub(REDACTED_MARKER, result)
    result = _BANK_ACCOUNT_PATTERN.sub(REDACTED_MARKER, result)
    result = _BEARER_PATTERN.sub(REDACTED_MARKER, result)
    result = _INLINE_SECRET_PATTERN.sub(rf"\1={REDACTED_MARKER}", result)
    return result


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
    user_role: str | None = None
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
        if self.user_role is not None:
            attrs["oppytec.user_role"] = self.user_role
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


@dataclass(frozen=True)
class RecipeOperationMetric:
    """Métrica determinista de operaciones de recetas, escandallos, fichas de cocina y combos."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    recipe_id: int | None = None
    combo_id: int | None = None
    is_dynamic: bool = False
    allergen_count: int = 0
    timestamp: str = ""


_in_memory_recipe_metrics: list[RecipeOperationMetric] = []


def get_in_memory_recipe_metrics() -> list[RecipeOperationMetric]:
    """Devuelve las métricas de operaciones de recetas y combos registradas en memoria."""
    return list(_in_memory_recipe_metrics)


def clear_in_memory_recipe_metrics() -> None:
    """Limpia las métricas de operaciones de recetas y combos en memoria."""
    _in_memory_recipe_metrics.clear()


@dataclass(frozen=True)
class OppyfyOperationMetric:
    """Métrica determinista de consultas, ruteo y ejecuciones operativas de OppyFy."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    user_id: str | None = None
    subdomain_slug: str | None = None
    tool_code: str | None = None
    tokens_total: int = 0
    credits_deducted: str = "0.00"
    timestamp: str = ""


_in_memory_oppyfy_metrics: list[OppyfyOperationMetric] = []


def get_in_memory_oppyfy_metrics() -> list[OppyfyOperationMetric]:
    """Devuelve las métricas operativas de OppyFy registradas en memoria."""
    return list(_in_memory_oppyfy_metrics)


def clear_in_memory_oppyfy_metrics() -> None:
    """Limpia las métricas operativas de OppyFy en memoria."""
    _in_memory_oppyfy_metrics.clear()


@dataclass(frozen=True)
class JevOperationMetric:
    """Métrica determinista de consultas, agregaciones y decisiones JEV."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    holding_id: str | None = None
    user_id: str | None = None
    total_decisions: int = 0
    avg_latency_ms: str = "0.00"
    trace_id: str = ""
    timestamp: str = ""


_in_memory_jev_metrics: list[JevOperationMetric] = []
MAX_IN_MEMORY_METRICS_CAPACITY: int = 1000


def get_in_memory_jev_metrics() -> list[JevOperationMetric]:
    """Devuelve las métricas operativas de JEV registradas en memoria."""
    return list(_in_memory_jev_metrics)


def clear_in_memory_jev_metrics() -> None:
    """Limpia las métricas operativas de JEV en memoria."""
    _in_memory_jev_metrics.clear()


@dataclass(frozen=True)
class ProjectionOperationMetric:
    """Métrica determinista de recálculos y consultas de proyección de demanda y snapshots."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    products_processed: int = 0
    bodega_id: int | None = None
    horizon_days: int = 30
    page: int = 1
    page_size: int = 30
    timestamp: str = ""


_in_memory_projection_metrics: list[ProjectionOperationMetric] = []


def get_in_memory_projection_metrics() -> list[ProjectionOperationMetric]:
    """Devuelve las métricas operativas de proyección registradas en memoria."""
    return list(_in_memory_projection_metrics)


def clear_in_memory_projection_metrics() -> None:
    """Limpia las métricas operativas de proyección en memoria."""
    _in_memory_projection_metrics.clear()


@dataclass(frozen=True)
class EventOperationMetric:
    """Métrica determinista de operaciones del módulo de Eventos, Salones y Consumos."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    event_id: str | None = None
    salon_id: str | None = None
    user_id: str | None = None
    timestamp: str = ""


_in_memory_events_metrics: list[EventOperationMetric] = []


def get_in_memory_events_metrics() -> list[EventOperationMetric]:
    """Devuelve las métricas de operaciones de eventos registradas en memoria."""
    return list(_in_memory_events_metrics)


def clear_in_memory_events_metrics() -> None:
    """Limpia las métricas de operaciones de eventos en memoria."""
    _in_memory_events_metrics.clear()


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


@dataclass(frozen=True)
class InvoiceOperationMetric:
    """Métrica determinista de operaciones de facturas y telemetría FinOps."""

    operation: str
    status: str
    duration_ms: float
    tenant_id: str | None = None
    invoice_id: str | None = None
    dte_type: str | int | None = None
    vendor_tax_id: str | None = None
    gemini_tokens_used: int = 0
    gemini_cost_usd: str = "0.000000"
    lines_count: int = 0
    timestamp: str = ""


_in_memory_invoice_metrics: list[InvoiceOperationMetric] = []


def get_in_memory_invoice_metrics() -> list[InvoiceOperationMetric]:
    """Devuelve las métricas de operaciones de facturación registradas en memoria."""
    return list(_in_memory_invoice_metrics)


def clear_in_memory_invoice_metrics() -> None:
    """Limpia las métricas de facturación en memoria."""
    _in_memory_invoice_metrics.clear()


@dataclass(frozen=True)
class HoldingHubOperationMetric:
    """Métrica determinista de operaciones consolidadas del Holding Hub Enterprise."""

    operation: str
    status: str
    duration_ms: float
    holding_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    user_role: str | None = None
    tenants_count: int = 0
    credits_total: int = 0
    credits_used: int = 0
    plan_tier: str | None = None
    timestamp: str = ""


_in_memory_holding_hub_metrics: list[HoldingHubOperationMetric] = []


def get_in_memory_holding_hub_metrics() -> list[HoldingHubOperationMetric]:
    """Devuelve las métricas operativas de Holding Hub registradas en memoria."""
    return list(_in_memory_holding_hub_metrics)


def clear_in_memory_holding_hub_metrics() -> None:
    """Limpia las métricas operativas de Holding Hub en memoria."""
    _in_memory_holding_hub_metrics.clear()



# Métricas FinOps OpenTelemetry / Prometheus
_invoice_meter = otel_metrics.get_meter("oppytec.invoices")
invoices_processed_counter = _invoice_meter.create_counter(
    name="invoices_processed_total",
    description="Total de facturas procesadas clasificadas por tenant y tipo DTE",
    unit="1",
)
invoice_ocr_duration_histogram = _invoice_meter.create_histogram(
    name="invoice_ocr_duration_seconds",
    description="Histograma de latencia de extracción OCR Gemini en segundos",
    unit="s",
)
invoice_ai_tokens_counter = _invoice_meter.create_counter(
    name="invoice_ai_tokens_consumed_total",
    description="Contador acumulado de tokens de IA consumidos por el OCR",
    unit="tokens",
)
invoice_ai_cost_usd_counter = _invoice_meter.create_counter(
    name="invoice_ai_cost_usd_total",
    description="Costo FinOps acumulado en USD por extracción de facturas",
    unit="USD",
)


def record_invoice_finops_metric(
    *,
    tenant_id: str,
    dte_type: str | int,
    status: str,
    duration_seconds: float = 0.0,
    tokens_consumed: int = 0,
    cost_usd: Decimal | float | str = 0.0,
    invoice_id: str | None = None,
) -> None:
    """Registra contadores e histogramas FinOps en OpenTelemetry/Prometheus."""
    _ = invoice_id
    labels = {
        "tenant_id": str(tenant_id),
        "dte_type": str(dte_type),
        "status": status.upper(),
    }
    with suppress(Exception):
        invoices_processed_counter.add(1, labels)
        if duration_seconds > 0:
            invoice_ocr_duration_histogram.record(duration_seconds, labels)
        if tokens_consumed > 0:
            invoice_ai_tokens_counter.add(tokens_consumed, labels)
        numeric_cost = float(Decimal(str(cost_usd))) if cost_usd else 0.0
        if numeric_cost > 0:
            invoice_ai_cost_usd_counter.add(numeric_cost, labels)


# Configuración de Structlog con Censura PII
def _structlog_pii_filter(_logger: object, _method_name: str, event_dict: dict[str, object]) -> dict[str, object]:
    """Procesador structlog que censura deterministamente campos PII y secretos."""
    return scrub_telemetry_payload(event_dict)


def configure_structlog() -> None:
    """Configura structlog con procesadores seguros y censura estricta de PII."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _structlog_pii_filter,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


configure_structlog()


def get_invoice_logger(
    tenant_id: str | None = None,
    invoice_id: str | None = None,
) -> structlog.BoundLogger:
    """Retorna un logger structlog enlazado a tenant_id e invoice_id con censura PII."""
    log = structlog.get_logger("oppytec.invoices")
    bindings: dict[str, object] = {}
    if tenant_id:
        bindings["tenant_id"] = str(tenant_id)
    if invoice_id:
        bindings["invoice_id"] = str(invoice_id)
    return log.bind(**bindings)


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
    user_role: str | None = None,
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
        user_role=user_role,
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


AI_METRIC_KEY_EXEMPTIONS: frozenset[str] = frozenset(
    {
        "tokens.total",
        "tokens.input",
        "tokens.output",
        "tokens.cached",
        "tokens_total",
        "input_tokens",
        "output_tokens",
        "cached_tokens",
        "total_tokens",
        "prior_thread_tokens",
    }
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if (
        key in AI_METRIC_KEY_EXEMPTIONS
        or normalized in AI_METRIC_KEY_EXEMPTIONS
        or normalized.startswith("tokens.")
    ):
        return False
    return any(token.replace("-", "_") in normalized for token in SENSITIVE_KEY_TOKENS)


def _scrub_string_patterns(text: str) -> str:
    """Redacta patrones PII embebidos en texto libre (correos, RUTs, teléfonos y secretos inline) preservando nombres propios."""
    return scrub_pii_text(text) or ""


def _scrub_value(value: object) -> object:
    if isinstance(value, SecretStr):
        return REDACTED_MARKER
    if isinstance(value, str):
        return _scrub_string_patterns(value)
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
    cookie, api_key, rut, tax_id, email_contacto, telefono, direccion, credit_card, cvv)
    o instancia de SecretStr, preservando nombres comerciales ('Pollo King').
    """
    scrubbed: dict[str, object] = {}
    for key, val in payload.items():
        if _is_sensitive_key(key) or isinstance(val, SecretStr):
            scrubbed[key] = REDACTED_MARKER
        else:
            scrubbed[key] = _scrub_value(val)
    return scrubbed


def enrich_sentry_telemetry_context(
    *,
    holding_id: str | None = None,
    tenant_id: str | None = None,
    user_role: str | None = None,
    user_id: str | None = None,
) -> dict[str, str]:
    """
    Enriquece el contexto y tags de Sentry / GlitchTip con tags obligatorios:
    `holding_id`, `tenant_id` y `user_role`.
    Garantiza tolerancia a fallos cuando sentry_sdk no está instalado o deshabilitado en local/CI.
    """
    tags: dict[str, str] = {}
    if holding_id:
        tags["holding_id"] = str(holding_id)
    if tenant_id:
        tags["tenant_id"] = str(tenant_id)
    if user_role:
        tags["user_role"] = str(user_role)
    if user_id:
        tags["user_id"] = str(user_id)

    with suppress(Exception):
        import sentry_sdk

        for k, v in tags.items():
            sentry_sdk.set_tag(k, v)
        if user_id or user_role:
            sentry_sdk.set_user({"id": str(user_id or ""), "role": str(user_role or "")})

    return tags


def scrub_sentry_event(
    event: dict[str, object],
    hint: dict[str, object] | None = None,
) -> dict[str, object]:
    """
    Hook determinista `before_send` para Sentry / GlitchTip que garantiza
    sanitización recursiva de PII (RUT, email_contacto, telefono, direccion,
    credenciales y SecretStr) sin alterar la razón social inmutable ('Pollo King')
    e inyecta o preserva las etiquetas obligatorias de multi-tenancy (holding_id, tenant_id, user_role).
    """
    _ = hint
    scrubbed = scrub_telemetry_payload(event)
    ctx = get_tenant_telemetry_context()
    raw_tags = scrubbed.get("tags")
    tags: dict[str, object] = dict(raw_tags) if isinstance(raw_tags, Mapping) else {}

    if ctx.holding_id and "holding_id" not in tags:
        tags["holding_id"] = ctx.holding_id
    if ctx.tenant_id and "tenant_id" not in tags:
        tags["tenant_id"] = ctx.tenant_id
    if ctx.user_role and "user_role" not in tags:
        tags["user_role"] = ctx.user_role

    scrubbed["tags"] = tags
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


class _NoOpSpan:
    """Implementación nula de Span de OTel para fallbacks seguros."""

    def set_attribute(self, key: str, value: object) -> None:
        pass

    def set_status(self, status: object) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass


@contextmanager
def _safe_start_span(tracer_name: str, span_name: str) -> Iterator[object]:
    """Inicia un span de OTel con fallback transparente a NoOp en caso de error o mock incompleto."""
    try:
        tracer = trace.get_tracer(tracer_name)
        span_cm = tracer.start_as_current_span(span_name)
        otel_span = span_cm.__enter__()
    except Exception:
        yield _NoOpSpan()
        return

    try:
        yield otel_span
    finally:
        span_cm.__exit__(*sys.exc_info())


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

    span_status_code = 200
    status_str = "SUCCESS"

    with _safe_start_span(tracer_name, name) as otel_span:
        initial_clean_attrs = scrub_telemetry_payload(dynamic_attrs)
        for k, v in initial_clean_attrs.items():
            if v is not None:
                with suppress(Exception):
                    otel_span.set_attribute(str(k), v if isinstance(v, (bool, str, int, float)) else str(v))

        try:
            yield dynamic_attrs
            with suppress(Exception):
                otel_span.set_status(Status(StatusCode.OK))
            safe_payload = scrub_telemetry_payload(dynamic_attrs)
            logging.getLogger(tracer_name).info(
                format_structured_log("INFO", name, safe_payload)
            )
        except Exception as exc:
            status_str = "ERROR"
            from src.core.exceptions import OppyTecError

            span_status_code = exc.status_code if isinstance(exc, OppyTecError) else 500
            with suppress(Exception):
                otel_span.record_exception(exc)
                otel_span.set_status(Status(StatusCode.ERROR, str(exc)))

            # Captura de contexto enriquecido en Sentry
            with suppress(Exception):
                import sentry_sdk

                h_id = str(dynamic_attrs.get("holding.id") or dynamic_attrs.get("holding_id") or ctx.holding_id or "")
                t_id = str(dynamic_attrs.get("tenant_id") or ctx.tenant_id or "")
                u_role = str(dynamic_attrs.get("user_role") or ctx.user_role or "")
                with sentry_sdk.push_scope() as scope:
                    if h_id:
                        scope.set_tag("holding_id", h_id)
                    if t_id:
                        scope.set_tag("tenant_id", t_id)
                    if u_role:
                        scope.set_tag("user_role", u_role)
                    sentry_sdk.capture_exception(exc)

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
                    with suppress(Exception):
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

            with suppress(Exception):
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

            if name.startswith("invoices.") or tracer_name.startswith("oppytec.invoices"):
                raw_inv_id = dynamic_attrs.get("invoice.id") or dynamic_attrs.get("invoice_id")
                if raw_inv_id:
                    merged_attrs["invoice.id"] = str(raw_inv_id)
                    with suppress(Exception):
                        otel_span.set_attribute("invoice.id", str(raw_inv_id))

                raw_dte = dynamic_attrs.get("invoice.dte_type") or dynamic_attrs.get("dte_type")
                if raw_dte:
                    merged_attrs["invoice.dte_type"] = str(raw_dte)
                    with suppress(Exception):
                        otel_span.set_attribute("invoice.dte_type", str(raw_dte))

                raw_tax_id = dynamic_attrs.get("invoice.vendor_tax_id") or dynamic_attrs.get("vendor_tax_id")
                if raw_tax_id:
                    scrubbed_tax = scrub_pii_text(str(raw_tax_id)) or str(raw_tax_id)
                    merged_attrs["invoice.vendor_tax_id"] = scrubbed_tax
                    with suppress(Exception):
                        otel_span.set_attribute("invoice.vendor_tax_id", scrubbed_tax)

                raw_tokens = dynamic_attrs.get("invoice.gemini_tokens_used") or dynamic_attrs.get("gemini_tokens_used", 0)
                try:
                    tok_val = int(str(raw_tokens))
                except (ValueError, TypeError):
                    tok_val = 0
                merged_attrs["invoice.gemini_tokens_used"] = tok_val
                with suppress(Exception):
                    otel_span.set_attribute("invoice.gemini_tokens_used", tok_val)

                raw_cost = dynamic_attrs.get("invoice.gemini_cost_usd") or dynamic_attrs.get("gemini_cost_usd", "0.000000")
                merged_attrs["invoice.gemini_cost_usd"] = str(raw_cost)
                with suppress(Exception):
                    otel_span.set_attribute("invoice.gemini_cost_usd", str(raw_cost))

                raw_lines = dynamic_attrs.get("invoice.lines_count") or dynamic_attrs.get("lines_count", 0)
                try:
                    lines_val = int(str(raw_lines))
                except (ValueError, TypeError):
                    lines_val = 0
                merged_attrs["invoice.lines_count"] = lines_val
                with suppress(Exception):
                    otel_span.set_attribute("invoice.lines_count", lines_val)

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

            if name.startswith(("recipe.", "combo.")) or tracer_name.startswith("oppytec.recipes"):
                raw_recipe_id = dynamic_attrs.get("recipe_id")
                metric_recipe_id: int | None = None
                if raw_recipe_id is not None:
                    try:
                        metric_recipe_id = int(str(raw_recipe_id))
                    except (ValueError, TypeError):
                        metric_recipe_id = None

                raw_combo_id = dynamic_attrs.get("combo_id")
                metric_combo_id: int | None = None
                if raw_combo_id is not None:
                    try:
                        metric_combo_id = int(str(raw_combo_id))
                    except (ValueError, TypeError):
                        metric_combo_id = None

                raw_allergen_count = dynamic_attrs.get("allergen_count", 0)
                try:
                    metric_allergens = int(str(raw_allergen_count)) if raw_allergen_count is not None else 0
                except (ValueError, TypeError):
                    metric_allergens = 0

                recipe_metric = RecipeOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    tenant_id=metric_tenant,
                    recipe_id=metric_recipe_id,
                    combo_id=metric_combo_id,
                    is_dynamic=bool(dynamic_attrs.get("is_dynamic", False)),
                    allergen_count=metric_allergens,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                _in_memory_recipe_metrics.append(recipe_metric)

            if name.startswith("oppyfy.") or tracer_name.startswith("oppytec.oppyfy"):
                raw_tokens = dynamic_attrs.get("tokens.total", dynamic_attrs.get("total_tokens", 0))
                try:
                    metric_tokens = int(str(raw_tokens))
                except (ValueError, TypeError):
                    metric_tokens = 0

                raw_credits = dynamic_attrs.get("credits.deducted", "0.00")
                metric_credits = str(raw_credits)

                oppy_metric = OppyfyOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    tenant_id=metric_tenant,
                    user_id=metric_user,
                    subdomain_slug=str(dynamic_attrs.get("subdomain_slug", "")) or None,
                    tool_code=str(dynamic_attrs.get("tool.selected", dynamic_attrs.get("tool_code", ""))) or None,
                    tokens_total=metric_tokens,
                    credits_deducted=metric_credits,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                _in_memory_oppyfy_metrics.append(oppy_metric)

            if name.startswith(("jev.", "platform_admin.jev")) or tracer_name.startswith("oppytec.tenancy.jev"):
                raw_decisions = dynamic_attrs.get("total_decisions_all", dynamic_attrs.get("total_decisions", 0))
                try:
                    metric_decisions = int(str(raw_decisions))
                except (ValueError, TypeError):
                    metric_decisions = 0

                raw_avg_lat = dynamic_attrs.get("avg_latency_ms_all", dynamic_attrs.get("avg_latency_ms", "0.00"))
                metric_avg_lat = str(raw_avg_lat)

                jev_metric = JevOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    tenant_id=metric_tenant,
                    holding_id=ctx.holding_id or (str(dynamic_attrs.get("holding_id", "")) if dynamic_attrs.get("holding_id") else None),
                    user_id=metric_user,
                    total_decisions=metric_decisions,
                    avg_latency_ms=metric_avg_lat,
                    trace_id=resolved_trace,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                if len(_in_memory_jev_metrics) >= MAX_IN_MEMORY_METRICS_CAPACITY:
                    del _in_memory_jev_metrics[0]
                _in_memory_jev_metrics.append(jev_metric)

            if name.startswith("projection.") or tracer_name.startswith("oppytec.projection"):
                raw_prods = dynamic_attrs.get("projection.products_processed", dynamic_attrs.get("products_processed", 0))
                try:
                    metric_prods = int(str(raw_prods))
                except (ValueError, TypeError):
                    metric_prods = 0

                raw_horizon = dynamic_attrs.get("horizon_days", 30)
                try:
                    metric_horizon = int(str(raw_horizon))
                except (ValueError, TypeError):
                    metric_horizon = 30

                raw_page = dynamic_attrs.get("page", 1)
                try:
                    metric_page = int(str(raw_page))
                except (ValueError, TypeError):
                    metric_page = 1

                raw_page_size = dynamic_attrs.get("page_size", 30)
                try:
                    metric_page_size = int(str(raw_page_size))
                except (ValueError, TypeError):
                    metric_page_size = 30

                proj_metric = ProjectionOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    tenant_id=metric_tenant,
                    products_processed=metric_prods,
                    bodega_id=metric_bodega,
                    horizon_days=metric_horizon,
                    page=metric_page,
                    page_size=metric_page_size,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                if len(_in_memory_projection_metrics) >= MAX_IN_MEMORY_METRICS_CAPACITY:
                    del _in_memory_projection_metrics[0]
                _in_memory_projection_metrics.append(proj_metric)

            if name.startswith("events.") or tracer_name.startswith("oppytec.events"):
                metric_event_id = str(dynamic_attrs.get("event_id")) if dynamic_attrs.get("event_id") else None
                metric_salon_id = str(dynamic_attrs.get("salon_id")) if dynamic_attrs.get("salon_id") else None
                event_metric = EventOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    tenant_id=metric_tenant,
                    event_id=metric_event_id,
                    salon_id=metric_salon_id,
                    user_id=metric_user,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                if len(_in_memory_events_metrics) >= MAX_IN_MEMORY_METRICS_CAPACITY:
                    del _in_memory_events_metrics[0]
                _in_memory_events_metrics.append(event_metric)

            if name.startswith("invoices.") or tracer_name.startswith("oppytec.invoices"):
                raw_inv_id = dynamic_attrs.get("invoice.id") or dynamic_attrs.get("invoice_id")
                metric_inv_id = str(raw_inv_id) if raw_inv_id else None

                raw_dte = dynamic_attrs.get("invoice.dte_type") or dynamic_attrs.get("dte_type")
                metric_dte = str(raw_dte) if raw_dte else "33"

                raw_tax_id = dynamic_attrs.get("invoice.vendor_tax_id") or dynamic_attrs.get("vendor_tax_id")
                metric_tax_id = str(raw_tax_id) if raw_tax_id else None

                raw_tokens = dynamic_attrs.get("invoice.gemini_tokens_used") or dynamic_attrs.get("gemini_tokens_used", 0)
                try:
                    metric_tokens = int(str(raw_tokens))
                except (ValueError, TypeError):
                    metric_tokens = 0

                raw_cost = dynamic_attrs.get("invoice.gemini_cost_usd") or dynamic_attrs.get("gemini_cost_usd", "0.000000")
                metric_cost = str(raw_cost)

                raw_lines = dynamic_attrs.get("invoice.lines_count") or dynamic_attrs.get("lines_count", 0)
                try:
                    metric_lines = int(str(raw_lines))
                except (ValueError, TypeError):
                    metric_lines = 0

                inv_metric = InvoiceOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    tenant_id=metric_tenant,
                    invoice_id=metric_inv_id,
                    dte_type=metric_dte,
                    vendor_tax_id=metric_tax_id,
                    gemini_tokens_used=metric_tokens,
                    gemini_cost_usd=metric_cost,
                    lines_count=metric_lines,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                if len(_in_memory_invoice_metrics) >= MAX_IN_MEMORY_METRICS_CAPACITY:
                    del _in_memory_invoice_metrics[0]
                _in_memory_invoice_metrics.append(inv_metric)

                record_invoice_finops_metric(
                    tenant_id=metric_tenant or "unknown",
                    dte_type=metric_dte,
                    status=status_str,
                    duration_seconds=round(duration_ms / 1000.0, 4),
                    tokens_consumed=metric_tokens,
                    cost_usd=Decimal(metric_cost) if metric_cost else Decimal("0"),
                    invoice_id=metric_inv_id,
                )

            if name.startswith(("holding_hub.", "holding.hub.")) or tracer_name.startswith("oppytec.tenancy.holding_hub"):
                raw_holding = dynamic_attrs.get("holding.id") or dynamic_attrs.get("holding_id") or ctx.holding_id
                metric_holding = str(raw_holding) if raw_holding else None
                if metric_holding:
                    merged_attrs["holding.id"] = metric_holding
                    merged_attrs["holding_id"] = metric_holding
                    with suppress(Exception):
                        otel_span.set_attribute("holding.id", metric_holding)
                        otel_span.set_attribute("holding_id", metric_holding)

                raw_tenants = dynamic_attrs.get("tenants.count") or dynamic_attrs.get("tenants_count", 0)
                try:
                    metric_tenants = int(str(raw_tenants))
                except (ValueError, TypeError):
                    metric_tenants = 0
                if metric_tenants > 0 or "tenants.count" in dynamic_attrs:
                    merged_attrs["tenants.count"] = metric_tenants
                    with suppress(Exception):
                        otel_span.set_attribute("tenants.count", metric_tenants)

                raw_c_total = dynamic_attrs.get("credits.total") or dynamic_attrs.get("credits_total", 0)
                try:
                    metric_c_total = int(str(raw_c_total))
                except (ValueError, TypeError):
                    metric_c_total = 0
                if metric_c_total > 0 or "credits.total" in dynamic_attrs:
                    merged_attrs["credits.total"] = metric_c_total
                    with suppress(Exception):
                        otel_span.set_attribute("credits.total", metric_c_total)

                raw_c_used = dynamic_attrs.get("credits.used") or dynamic_attrs.get("credits_used", 0)
                try:
                    metric_c_used = int(str(raw_c_used))
                except (ValueError, TypeError):
                    metric_c_used = 0
                if metric_c_used > 0 or "credits.used" in dynamic_attrs:
                    merged_attrs["credits.used"] = metric_c_used
                    with suppress(Exception):
                        otel_span.set_attribute("credits.used", metric_c_used)

                raw_plan_tier = dynamic_attrs.get("plan.tier") or dynamic_attrs.get("plan_tier")
                metric_plan_tier = str(raw_plan_tier) if raw_plan_tier else None
                if metric_plan_tier:
                    merged_attrs["plan.tier"] = metric_plan_tier
                    with suppress(Exception):
                        otel_span.set_attribute("plan.tier", metric_plan_tier)

                raw_role = dynamic_attrs.get("user_role") or ctx.user_role
                metric_role = str(raw_role) if raw_role else None
                if metric_role:
                    merged_attrs["user_role"] = metric_role
                    with suppress(Exception):
                        otel_span.set_attribute("user_role", metric_role)

                with suppress(Exception):
                    import sentry_sdk

                    if metric_holding:
                        sentry_sdk.set_tag("holding_id", metric_holding)
                    if metric_tenant:
                        sentry_sdk.set_tag("tenant_id", metric_tenant)
                    if metric_role:
                        sentry_sdk.set_tag("user_role", metric_role)

                hub_metric = HoldingHubOperationMetric(
                    operation=name,
                    status=status_str,
                    duration_ms=round(duration_ms, 3),
                    holding_id=metric_holding,
                    tenant_id=metric_tenant,
                    user_id=metric_user,
                    user_role=metric_role,
                    tenants_count=metric_tenants,
                    credits_total=metric_c_total,
                    credits_used=metric_c_used,
                    plan_tier=metric_plan_tier,
                    timestamp=datetime.now(UTC).isoformat(),
                )
                if len(_in_memory_holding_hub_metrics) >= MAX_IN_MEMORY_METRICS_CAPACITY:
                    del _in_memory_holding_hub_metrics[0]
                _in_memory_holding_hub_metrics.append(hub_metric)



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
        try:
            request.state.trace_id = trace_id
        except Exception:
            pass
        start_ns = time.perf_counter_ns()
        span_id = uuid.uuid4().hex[:16]
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            response.headers["X-Trace-ID"] = trace_id
            clean_trace_hex = trace_id.replace("-", "").ljust(32, "0")[:32]
            response.headers["traceparent"] = f"00-{clean_trace_hex}-{span_id}-01"

            if self._otel_exporter in ("memory", "otlp"):
                ctx = get_tenant_telemetry_context()
                span = SpanRecord(
                    name=f"{request.method} {request.url.path}",
                    trace_id=trace_id,
                    span_id=span_id,
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


def setup_observability(app: ASGIApp) -> None:
    """Configura la observabilidad 4-pilares registrando ObservabilityMiddleware."""
    env = "local"
    env_namespace = "default"
    otel_exporter = "none"
    with suppress(Exception):
        from src.core.config import get_settings

        settings = get_settings()
        env = settings.ENVIRONMENT
        env_namespace = settings.ENV_NAMESPACE
        otel_exporter = settings.OTEL_EXPORTER

    app.add_middleware(
        ObservabilityMiddleware,
        environment=env,
        env_namespace=env_namespace,
        otel_exporter=otel_exporter,
    )

