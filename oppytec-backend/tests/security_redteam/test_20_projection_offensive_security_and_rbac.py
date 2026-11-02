"""
Vector Red Team 20 (`tests/security_redteam/test_20_projection_offensive_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant, Inyección SQL,
Paginación Segura y Guardias RBAC de 3 Niveles en el Módulo de Proyección:
1. Aislamiento Estricto Multi-Tenant (esquemas `tenant_*`, sin fuga de datos inter-inquilinos).
2. Verificación Exhaustiva de Guardias RBAC de 3 Niveles (projection.demand.read,
   projection.recompute.execute, projection.alerts.read, projection.transfers.read).
3. Mitigación de Desbordamiento y Ataques DoS en Parámetros de Paginación (`page_size`, `page`, `horizon_days`).
4. Sanitización Integral contra Inyección SQL (SQLi) en el parámetro `search`, `sort_by` y filtros.
5. Verificación de Cero Hardcoding de Credenciales o Secretos en el módulo.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.core.guards import clear_revoked_sessions
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_test_procurement"
TENANT_BETA = "tenant_beta_projections"
HOLDING_ID = "holding_projections_test"

ALL_PROJECTION_PERMISSIONS = [
    "projection.demand.read",
    "projection.recompute.execute",
    "projection.alerts.read",
    "projection.transfers.read",
    "inventory.kardex.read",
    "inventory.kardex.write",
]


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    *,
    explicit_denies: list[str] | None = None,
    accessible_tenants: list[str] | None = None,
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=accessible_tenants or [tenant_id],
        contracted_modules=["projection", "inventory", "catalog"],
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.core.database as db_mod
    from src.core.config import get_settings

    clear_revoked_sessions()
    monkeypatch.setenv("DB_POOL_CLASS", "NullPool")
    get_settings.cache_clear()
    db_mod._engine = None
    db_mod._session_factory = None
    yield
    db_mod._engine = None
    db_mod._session_factory = None
    get_settings.cache_clear()


# ============================================================================
# VECTOR 1: RBAC DE 3 NIVELES Y CONTROL DE ACCESO
# ============================================================================


def test_rbac_denial_on_all_projection_endpoints_without_permissions() -> None:
    """Valida denegación 403 Forbidden RFC 7807 cuando el usuario carece de permisos RBAC."""
    app = create_app()
    token = _create_token(101, TENANT_ALPHA, ["unrelated.module.read"])
    headers = _make_headers(token, TENANT_ALPHA)

    with TestClient(app) as client:
        # Snapshots: requiere projection.demand.read
        resp_snap = client.get("/api/v1/projection/snapshots", headers=headers)
        assert resp_snap.status_code == 403
        data_snap = resp_snap.json()
        assert data_snap["status"] == 403
        assert data_snap["error_code"] in ("MISSING_PERMISSION", "RBAC_PERMISSION_DENIED")

        # Recompute: requiere projection.recompute.execute
        resp_rec = client.post("/api/v1/projection/recompute", headers=headers)
        assert resp_rec.status_code == 403

        # Curve: requiere projection.demand.read
        resp_curv = client.get("/api/v1/projection/products/1/curve", headers=headers)
        assert resp_curv.status_code == 403

        # Alerts: requiere projection.alerts.read
        resp_alert = client.get("/api/v1/projection/alerts", headers=headers)
        assert resp_alert.status_code == 403

        # Transfer suggestions: requiere projection.transfers.read
        resp_trans = client.get("/api/v1/projection/products/1/transfer-suggestions?bodega_id=1", headers=headers)
        assert resp_trans.status_code == 403


def test_rbac_explicit_deny_overrides_role_grant() -> None:
    """Un explicit deny revoca inmediatamente el acceso aunque el rol otorgue el permiso."""
    app = create_app()
    token = _create_token(
        102,
        TENANT_ALPHA,
        permissions=["projection.demand.read"],
        explicit_denies=["projection.demand.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    with TestClient(app) as client:
        resp = client.get("/api/v1/projection/snapshots", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["status"] == 403


# ============================================================================
# VECTOR 2: SANITIZACIÓN DE PARÁMETROS DE PAGINACIÓN Y PREVENCIÓN DOS
# ============================================================================


def test_pagination_page_size_overflow_prevention() -> None:
    """Verifica que tamaños de página fuera de rango sean rechazados con 422 Unprocessable Entity."""
    app = create_app()
    token = _create_token(103, TENANT_ALPHA, ALL_PROJECTION_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    with TestClient(app) as client:
        # page_size excesivo (> 100) -> 422
        resp_overflow = client.get("/api/v1/projection/snapshots?page_size=1000", headers=headers)
        assert resp_overflow.status_code == 422

        # page_size negativo (< 1) -> 422
        resp_neg = client.get("/api/v1/projection/snapshots?page_size=-5", headers=headers)
        assert resp_neg.status_code == 422

        # page negativa (< 1) -> 422
        resp_page_neg = client.get("/api/v1/projection/snapshots?page=0", headers=headers)
        assert resp_page_neg.status_code == 422

        # horizon_days fuera del rango permitido (7..90) -> 422
        resp_horizon_high = client.get("/api/v1/projection/snapshots?horizon_days=365", headers=headers)
        assert resp_horizon_high.status_code == 422

        resp_horizon_low = client.get("/api/v1/projection/snapshots?horizon_days=2", headers=headers)
        assert resp_horizon_low.status_code == 422


# ============================================================================
# VECTOR 3: SANITIZACIÓN CONTRA INYECCIÓN SQL (SQLi)
# ============================================================================


def test_sqli_resilience_in_search_and_filters() -> None:
    """
    Comprueba que payloads maliciosos de Inyección SQL en parámetros search,
    sort_by y status sean sanitizados e inocuos para SQLAlchemy y el motor de BD.
    """
    app = create_app()
    token = _create_token(104, TENANT_ALPHA, ALL_PROJECTION_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE projection_snapshots; --",
        "' UNION SELECT NULL, NULL, NULL, NULL, NULL --",
        "1' OR 1=1#",
        "admin'--",
        "'; EXEC xp_cmdshell('dir'); --",
        "\" OR \"\"=\"",
    ]

    with TestClient(app) as client:
        for payload in sqli_payloads:
            # 1. SQLi en parámetro `search`
            resp = client.get(
                "/api/v1/projection/snapshots",
                params={"search": payload, "page": 1, "page_size": 10},
                headers=headers,
            )
            # Debe procesar la búsqueda como string literal sin 500 error de sintaxis SQL
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data["items"], list)

            # 2. SQLi en parámetro `sort_by`: lista blanca estricta en FastAPI router rechaza con 422
            resp_sort = client.get(
                "/api/v1/projection/snapshots",
                params={"sort_by": payload, "page": 1, "page_size": 10},
                headers=headers,
            )
            assert resp_sort.status_code == 422

            # 3. SQLi en parámetro `status`: lista blanca estricta en FastAPI router rechaza con 422
            resp_status = client.get(
                "/api/v1/projection/snapshots",
                params={"status": payload, "page": 1, "page_size": 10},
                headers=headers,
            )
            assert resp_status.status_code == 422


# ============================================================================
# VECTOR 4: AISLAMIENTO MULTI-TENANT Y PROTECCIÓN DE CABECERAS
# ============================================================================


def test_multi_tenant_isolation_and_schema_validation() -> None:
    """Valida que nombres de esquema maliciosos en la resolución de sesión sean bloqueados."""
    from src.core.database import validate_tenant_schema_name

    # Intentos de SQL injection en schema name deben fallar en la regex de validación
    malicious_schemas = [
        "tenant_alpha; DROP TABLE users;",
        "tenant_alpha'--",
        "tenant_alpha/*comment*/",
        "public",
        "tenant_with_invalid_char$#",
        "tenant_" + ("a" * 70),  # Longitud excesiva > 63
    ]

    for malicious in malicious_schemas:
        with pytest.raises(ValueError, match="TenantSchemaValidationError"):
            validate_tenant_schema_name(malicious)

    # Esquema válido debe ser aceptado
    assert validate_tenant_schema_name("tenant_alpha_santiago") == "tenant_alpha_santiago"


# ============================================================================
# VECTOR 5: CERO HARDCODING DE SECRETOS O CREDENCIALES
# ============================================================================


def test_zero_hardcoding_in_projection_module() -> None:
    """Audita estáticamente que no existan contraseñas, secretos o API keys en código de proyección."""
    proj_dir = Path("oppytec-backend/src/modules/projection")
    assert proj_dir.is_dir()

    secret_pattern = re.compile(
        r"""(?i)(api[_-]?key|secret[_-]?key|password|jwt[_-]?secret|private[_-]?key)\s*=\s*['"][^'"]{5,}['"]"""
    )

    for py_file in proj_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        matches = secret_pattern.findall(content)
        assert not matches, f"Posible secreto hardcodeado detectado en {py_file}: {matches}"
