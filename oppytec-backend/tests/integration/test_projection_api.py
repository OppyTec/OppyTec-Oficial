"""
oppytec-backend/tests/integration/test_projection_api.py
Pruebas de Integración End-to-End para los Endpoints REST de Proyección:
- `GET /api/v1/projection/snapshots` (Paginación server-side, filtros y ordenamiento).
- `POST /api/v1/projection/recompute` (Disparo de recálculo y bloqueo anti-concurrencia).
- `GET /api/v1/projection/products/{product_id}/curve` (Curva temporal Recharts).
- `GET /api/v1/projection/alerts` (Consola de alertas de quiebre y riesgos de stock).
- `GET /api/v1/projection/products/{product_id}/transfer-suggestions` (Traspasos preventivos).
- Control de acceso RBAC de 3 niveles y denegación RFC 7807 (HTTP 403).
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.core.guards import clear_revoked_sessions
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.integration

TENANT_ID = "tenant_test_procurement"
HOLDING_ID = "holding_projection_test"

_PROJECTION_GRANTS = [
    "projection.demand.read",
    "projection.recompute.execute",
    "projection.alerts.read",
    "projection.transfers.read",
    "inventory.kardex.read",
    "inventory.kardex.write",
]


@pytest.fixture(autouse=True)
def _clean_db_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.core.database as db_mod

    clear_revoked_sessions()
    monkeypatch.setenv("DB_POOL_CLASS", "NullPool")
    get_settings.cache_clear()
    db_mod._engine = None
    db_mod._session_factory = None
    yield
    db_mod._engine = None
    db_mod._session_factory = None
    get_settings.cache_clear()


def _make_headers(permissions: list[str], user_id: int = 501) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_ID,
        holding_id=HOLDING_ID,
        contracted_modules=["projection", "inventory", "catalog"],
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


def test_projection_rbac_forbidden_without_permission() -> None:
    """Verifica que sin los permisos requeridos el enrutador retorne HTTP 403 Forbidden RFC 7807."""
    clear_revoked_sessions()
    app = create_app()

    unauthorized_headers = _make_headers(["catalog.products.read"])  # Sin permisos de proyección

    with TestClient(app) as client:
        # 1. Snapshots endpoint
        resp = client.get("/api/v1/projection/snapshots", headers=unauthorized_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert data["status"] == 403
        assert data["error_code"] in ("MISSING_PERMISSION", "RBAC_PERMISSION_DENIED")

        # 2. Recompute endpoint
        recompute_resp = client.post("/api/v1/projection/recompute", headers=unauthorized_headers)
        assert recompute_resp.status_code == 403

        # 3. Curve endpoint
        curve_resp = client.get("/api/v1/projection/products/1/curve", headers=unauthorized_headers)
        assert curve_resp.status_code == 403

        # 4. Alerts endpoint
        alerts_resp = client.get("/api/v1/projection/alerts", headers=unauthorized_headers)
        assert alerts_resp.status_code == 403

        # 5. Transfer suggestions endpoint
        transfer_resp = client.get(
            "/api/v1/projection/products/1/transfer-suggestions?bodega_id=1",
            headers=unauthorized_headers,
        )
        assert transfer_resp.status_code == 403


def test_projection_recompute_and_snapshots_flow() -> None:
    """Verifica el flujo completo de recálculo de proyección y consulta paginada server-side."""
    clear_revoked_sessions()
    app = create_app()
    headers = _make_headers(_PROJECTION_GRANTS)

    with TestClient(app) as client:
        # 1. Disparar recálculo masivo
        recompute_resp = client.post(
            "/api/v1/projection/recompute",
            headers=headers,
            json={"horizon_days": 30},
        )
        assert recompute_resp.status_code == 200
        rec_data = recompute_resp.json()
        assert rec_data["status"] in ("completed", "locked")
        assert rec_data["horizon_days"] == 30

        # 2. Obtener listado paginado de snapshots
        snapshots_resp = client.get(
            "/api/v1/projection/snapshots?page=1&page_size=30&horizon_days=30",
            headers=headers,
        )
        assert snapshots_resp.status_code == 200
        snap_data = snapshots_resp.json()
        assert "items" in snap_data
        assert "total_items" in snap_data
        assert snap_data["page"] == 1
        assert snap_data["page_size"] == 30
        assert "has_next" in snap_data
        assert "has_prev" in snap_data

        # 3. Obtener alertas de proyección
        alerts_resp = client.get(
            "/api/v1/projection/alerts?horizon_days=30",
            headers=headers,
        )
        assert alerts_resp.status_code == 200
        alerts_data = alerts_resp.json()
        assert isinstance(alerts_data, list)


# ---------------------------------------------------------------------------
# Red Team (Agente 10) — Validación de entradas y aislamiento multi-tenant
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-5",
        "page_size=0",
        "page_size=101",
        "page_size=100000",
        "horizon_days=1000",
        "status=critical'%20OR%20'1'='1",
        "sort_by=id;DROP%20TABLE%20productos",
        "search=" + "a" * 101,
    ],
)
def test_projection_snapshots_rejects_out_of_bounds_and_non_whitelisted_params(query: str) -> None:
    """Paginación acotada (page>=1, page_size<=100) y listas blancas de status/sort_by/search."""
    clear_revoked_sessions()
    app = create_app()
    headers = _make_headers(_PROJECTION_GRANTS)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/projection/snapshots?{query}", headers=headers)
        assert resp.status_code == 422
        body = resp.text
        assert "Traceback" not in body
        assert "sqlalchemy" not in body.lower()


def test_projection_snapshots_accepts_max_page_size_and_sqli_search_literal() -> None:
    """`page_size=100` es válido y un payload SQLi en `search` se trata como literal."""
    clear_revoked_sessions()
    app = create_app()
    headers = _make_headers(_PROJECTION_GRANTS)
    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/projection/snapshots",
            params={"page_size": 100, "search": "' OR 1=1; --", "status": "CRITICAL", "sort_by": "name_asc"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_size"] == 100
        assert data["total_items"] == 0


def test_projection_cross_tenant_header_is_denied() -> None:
    """Un `X-Tenant-ID` ajeno al token se rechaza con 403 RFC 7807 (sin fallback a header crudo)."""
    clear_revoked_sessions()
    app = create_app()
    headers = _make_headers(_PROJECTION_GRANTS)
    headers["X-Tenant-ID"] = "tenant_otro_cliente"
    with TestClient(app) as client:
        for method, path in (
            ("GET", "/api/v1/projection/snapshots"),
            ("POST", "/api/v1/projection/recompute"),
            ("GET", "/api/v1/projection/alerts"),
            ("GET", "/api/v1/projection/products/1/curve"),
            ("GET", "/api/v1/projection/products/1/transfer-suggestions?bodega_id=1"),
        ):
            resp = client.request(method, path, headers=headers)
            assert resp.status_code == 403, path
            assert resp.json()["status"] == 403


@pytest.mark.asyncio
async def test_projection_tenant_db_dependency_fails_closed_without_principal() -> None:
    """Sin principal autenticado la dependencia no abre sesión (no usa X-Tenant-ID ni tenant_default)."""
    from types import SimpleNamespace

    from src.modules.projection.presentation.router import get_projection_tenant_db

    fake_request = SimpleNamespace(
        state=SimpleNamespace(),
        headers={"X-Tenant-ID": "tenant_victima"},
    )
    gen = get_projection_tenant_db(fake_request)  # type: ignore[arg-type]
    session = await anext(gen)
    assert session is None
    await gen.aclose()
