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

from src.core.exceptions import OppyTecError, RateLimitExceededError
from src.core.realtime.router import router as realtime_router
from src.modules.analytics.presentation.router import router as analytics_router
from src.modules.audit.presentation.router import router as audit_router
from src.modules.catalog.presentation.router import router as catalog_router
from src.modules.identity.presentation.router import router as identity_router
from src.modules.inventory.presentation.router import router as inventory_router
from src.modules.operations.presentation.router import router as operations_router
from src.modules.operations.presentation.router_approvals import router as operations_approvals_router
from src.modules.oppy_ai.presentation.router import router as oppy_ai_router
from src.modules.procurement.presentation.router import router as procurement_router
from src.modules.recipes.presentation.router import router as recipes_router
from src.modules.tenancy.presentation.router import router as tenancy_router

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

    from fastapi.middleware.cors import CORSMiddleware

    raw_origins = getattr(settings, "ALLOWED_ORIGINS", None)
    allowed_origins = (
        list(raw_origins)
        if isinstance(raw_origins, (list, tuple, set))
        else ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    if "http://localhost:5173" not in allowed_origins:
        allowed_origins.append("http://localhost:5173")
    if "http://127.0.0.1:5173" not in allowed_origins:
        allowed_origins.append("http://127.0.0.1:5173")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    @app.exception_handler(OppyTecError)
    async def oppytec_domain_exception_handler(
        request: Request,
        exc: OppyTecError,
    ) -> Response:
        trace_id = str(
            getattr(request.state, "trace_id", "")
            or request.headers.get("X-Trace-ID", uuid.uuid4().hex)
        )
        problem = exc.to_rfc7807(trace_id=trace_id, instance=str(request.url.path))
        headers: dict[str, str] = {"X-Trace-ID": trace_id}
        if isinstance(exc, RateLimitExceededError):
            headers["Retry-After"] = str(exc.retry_after_seconds)
        return DefaultJSONResponse(
            status_code=exc.status_code,
            content=problem.to_dict(),
            headers=headers,
        )

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

    app.include_router(realtime_router)
    app.include_router(identity_router)
    app.include_router(tenancy_router)
    app.include_router(audit_router)
    app.include_router(catalog_router)
    app.include_router(inventory_router)
    app.include_router(recipes_router)
    app.include_router(procurement_router)
    app.include_router(operations_router)
    app.include_router(operations_approvals_router)
    app.include_router(analytics_router)
    app.include_router(oppy_ai_router)

    return app


app = create_app()
