"""
OppyTec SaaS v2.0 — FastAPI Application Factory (`src/main.py`).

Enforces:
- `ORJSONResponse` default response class (with graceful fallback to `JSONResponse`).
- OpenAPI / Swagger / ReDoc disabled (`None`) when `ENVIRONMENT == "production"` or `not settings.is_openapi_enabled`.
- `X-Trace-ID` distributed correlation header injection and observability setup (`src.core.observability`).
- Health endpoint `/api/v1/health` returning status, environment, env_namespace, version, and `X-Trace-ID`.
"""
from __future__ import annotations

import importlib
import uuid
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Protocol

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import orjson as _orjson  # noqa: F401
    from fastapi.responses import ORJSONResponse as DefaultJSONResponse
except ImportError:  # pragma: no cover
    DefaultJSONResponse = JSONResponse  # type: ignore[misc,assignment]


class RuntimeSettingsProtocol(Protocol):
    """Protocol for runtime configuration injected by `src.core.config`."""

    @property
    def is_openapi_enabled(self) -> bool: ...


class _FallbackBootstrapSettings(BaseSettings):  # type: ignore[explicit-any]
    """Fallback Pydantic settings used only before `src.core.config` is merged."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "local"
    ENV_NAMESPACE: str = "default"
    AI_ASSISTANT_BRAND_NAME: str = "OppyFy"

    @property
    def environment(self) -> str:
        return self.ENVIRONMENT.strip().lower()

    @property
    def env_namespace(self) -> str:
        return self.ENV_NAMESPACE.strip()

    @property
    def is_openapi_enabled(self) -> bool:
        return self.environment != "production"


def _load_runtime_settings() -> object:
    """Loads settings from `src.core.config.get_settings` if present, with fallback."""
    fallback: object = _FallbackBootstrapSettings()
    with suppress(Exception):
        core_config = importlib.import_module("src.core.config")
        get_settings_fn = getattr(core_config, "get_settings", None)
        if callable(get_settings_fn):
            if hasattr(get_settings_fn, "cache_clear"):
                get_settings_fn.cache_clear()
            loaded: object = get_settings_fn()
            return loaded
    return fallback


def _resolve_environment(settings: object, fallback: _FallbackBootstrapSettings) -> str:
    """Extracts the active environment name in lowercase."""
    raw = getattr(settings, "environment", getattr(settings, "ENVIRONMENT", fallback.environment))
    env_str = str(raw).strip().lower()
    if fallback.environment != env_str and fallback.environment == "production":
        return "production"
    return env_str


def _resolve_env_namespace(settings: object, fallback: _FallbackBootstrapSettings) -> str:
    """Extracts the active `ENV_NAMESPACE`."""
    raw = getattr(
        settings,
        "env_namespace",
        getattr(settings, "ENV_NAMESPACE", fallback.env_namespace),
    )
    return str(raw).strip()


def _resolve_openapi_enabled(
    settings: object,
    environment: str,
) -> bool:
    """Determines whether `/docs`, `/redoc`, and `/openapi.json` are enabled."""
    if environment == "production":
        return False
    explicit = getattr(settings, "is_openapi_enabled", None)
    if isinstance(explicit, bool):
        return explicit
    return True


def create_app() -> FastAPI:
    """FastAPI Application Factory for OppyTec SaaS v2.0."""
    fallback = _FallbackBootstrapSettings()
    settings = _load_runtime_settings()
    environment = _resolve_environment(settings, fallback)
    env_namespace = _resolve_env_namespace(settings, fallback)
    openapi_enabled = _resolve_openapi_enabled(settings, environment)

    app = FastAPI(
        title="OppyTec SaaS v2.0 API",
        version="2.0.0",
        default_response_class=DefaultJSONResponse,
        docs_url="/docs" if openapi_enabled else None,
        redoc_url="/redoc" if openapi_enabled else None,
        openapi_url="/openapi.json" if openapi_enabled else None,
    )

    with suppress(Exception):
        core_observability = importlib.import_module("src.core.observability")
        setup_fn = getattr(core_observability, "setup_observability", None)
        if callable(setup_fn):
            setup_fn(app)

    @app.middleware("http")
    async def trace_id_and_security_headers_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming_trace_id = request.headers.get("X-Trace-ID", "").strip()
        trace_id = incoming_trace_id if incoming_trace_id else uuid.uuid4().hex
        request.state.trace_id = trace_id

        response = await call_next(request)
        if "X-Trace-ID" not in response.headers:
            response.headers["X-Trace-ID"] = trace_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

    @app.get("/api/v1/health", tags=["system"])
    async def health_check(request: Request, response: Response) -> dict[str, str]:
        trace_id = getattr(request.state, "trace_id", "") or request.headers.get(
            "X-Trace-ID", uuid.uuid4().hex
        )
        response.headers["X-Trace-ID"] = str(trace_id)
        return {
            "status": "ok",
            "environment": environment,
            "env_namespace": env_namespace,
            "version": "2.0.0",
            "trace_id": str(trace_id),
        }

    return app


app = create_app()
