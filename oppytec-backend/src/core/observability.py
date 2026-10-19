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
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime

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
    record: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper(),
        "event": event,
        "trace_id": ctx.trace_id,
        "environment": ctx.environment,
        "env_namespace": ctx.env_namespace,
        "holding_id": ctx.holding_id,
        "tenant_id": ctx.tenant_id,
        "tenant_schema": ctx.tenant_schema,
        "data": safe_payload,
    }
    return json.dumps(record, ensure_ascii=False)


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
