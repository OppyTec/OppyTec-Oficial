"""
Global Pytest Fixtures for OppyTec SaaS v2.0 Backend (`tests/conftest.py`).

Provides:
- Repository root and backend root path fixtures.
- Default safe test environment variables so tests run isolated from host state.
- FastAPI `app` and `AsyncClient` (`httpx.ASGITransport`) fixtures.
"""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from src.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def backend_root() -> Path:
    """Returns the absolute path to `oppytec-backend/`."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def monorepo_root(backend_root: Path) -> Path:
    """Returns the absolute path to the monorepo root."""
    return backend_root.parent


@pytest.fixture(autouse=True)
def default_test_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Sets deterministic baseline environment variables for each test."""
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("ENV_NAMESPACE", "wt_p1_2")
    monkeypatch.setenv(
        "SECRET_KEY",
        "K9v#mP2$xL8@qR5!wZ3^nT7&yB4*cF6_hJ1+dG0-sA9=uE2~pW",
    )
    monkeypatch.setenv(
        "JWT_ACCESS_SECRET_KEY",
        "A1b#cD2$eF3@gH4!iJ5^kL6&mN7*oP8_qR9+sT0-uV1=wX2~yZ",
    )
    monkeypatch.setenv(
        "JWT_REFRESH_SECRET_KEY",
        "Z9y#xW8$vU7@tS6!rQ5^pO4&nM3*lK2_jI1+hG0-fE9=dC8~bA",
    )
    monkeypatch.setenv(
        "SUPERUSER_GENESIS_PASSWORD",
        "OppyTec_Genesis_Local_Safe_Pass_2026!",
    )
    monkeypatch.setenv("OTEL_EXPORTER", "none")
    from src.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app() -> FastAPI:
    """Creates a fresh FastAPI application instance."""
    return create_app()


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Provides an async HTTPX client wired directly to the ASGI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client
