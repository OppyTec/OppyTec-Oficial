"""
Vector Red Team 13 (`tests/security_redteam/test_13_alerts_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant y RBAC en Endpoints de Alertas:
1. Aislamiento Físico Multi-Tenant en PostgreSQL (`PostgresAlertsRepository` confinado a `tenant_*`).
2. Prevención de Cross-Tenant IDOR y suplantación de `X-Tenant-ID`.
3. RBAC Estricto de 3 Niveles (`inventory.alerts.read`), Denegaciones Explícitas y Kill-Switch.
4. Bloqueo de Inyección SQL y Manipulación en parámetros (`bodega_id`, `area_operativa_id`, `tipo`, `upcoming_days`).
5. Bloqueo de Mass Assignment (`extra="forbid"`) y Fuzzing de Métodos HTTP.
6. Redacción Determinista de PII (`[REDACTED_PII]`) y Cero Filtración de Stack Traces RFC 7807.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from src.core.database import validate_tenant_schema_name
from src.core.guards.rbac_dependencies import (
    clear_revoked_sessions,
    revoke_session_token,
)
from src.core.observability import REDACTED_MARKER, scrub_telemetry_payload
from src.core.security import create_access_token
from src.modules.inventory.domain.alerts import (
    CriticalStockAlert,
)
from src.modules.inventory.infrastructure.alerts_repository import (
    InMemoryAlertsRepository,
    PostgresAlertsRepository,
)
from src.modules.inventory.presentation.router import _alerts_service
from src.modules.inventory.presentation.schemas_alerts import (
    AlertsBadgeResponse,
    AlertsSummaryResponse,
    CriticalStockAlertResponse,
    ExpiredLotAlertResponse,
    StockHealthRatioResponse,
    UpcomingExpiryAlertResponse,
)

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_alpha_santiago"
TENANT_BETA = "tenant_beta_valparaiso"
HOLDING_ID = "holding_pollogold"


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    hierarchy_rank: int = 20,
    explicit_denies: list[str] | None = None,
    is_superuser_god: bool = False,
    jti: str = "",
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=[tenant_id],
        is_superuser_god=is_superuser_god,
        jti=jti,
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_test_environment() -> None:
    clear_revoked_sessions()
    in_memory_repo = InMemoryAlertsRepository()
    _alerts_service.set_repository(in_memory_repo)
    _alerts_service.reset()


# ============================================================================
# VECTOR 1: AISLAMIENTO MULTI-TENANT Y CONFINAMIENTO POSTGRESQL (tenant_*)
# ============================================================================


@pytest.mark.asyncio
async def test_postgres_alerts_repository_schema_isolation_and_parameterization() -> None:
    """
    Verifica que PostgresAlertsRepository confina estrictamente todas las tablas
    al esquema tenant_* validado y utiliza binding de parámetros para bodega_id y area_operativa_id.
    """
    mock_session = AsyncMock()
    mock_result_stock = MagicMock()
    mock_result_stock.fetchall.return_value = []
    mock_result_lots = MagicMock()
    mock_result_lots.fetchall.return_value = []
    mock_session.execute.side_effect = [mock_result_stock, mock_result_lots]

    repo = PostgresAlertsRepository(session_or_none=mock_session)

    # 1. Consulta consolidada para Tenant Alpha
    summary = await repo.get_consolidated_alerts(
        tenant_schema=TENANT_ALPHA,
        bodega_ids=[10, 20],
        area_operativa_id=5,
        tipo_filtro="all",
        dias_fefo_umbral=30,
    )
    assert summary.total_count == 0

    # 2. Auditar las consultas SQL emitidas
    assert mock_session.execute.call_count == 2
    for call_args in mock_session.execute.call_args_list:
        query_clause, bound_params = call_args[0]
        sql_text = str(query_clause)

        # Confinamiento de esquema: cada tabla debe estar calificada con "tenant_alpha_santiago"
        assert f'"{TENANT_ALPHA}"' in sql_text
        assert "public." not in sql_text
        assert "tenant_beta" not in sql_text

        # Enlace parametrizado estricto
        if "pb.bodega_id = ANY(:bodega_ids)" in sql_text or "rs.bodega_id = ANY(:bodega_ids)" in sql_text:
            assert bound_params["bodega_ids"] == [10, 20]
        if "ao.id = :area_operativa_id" in sql_text:
            assert bound_params["area_operativa_id"] == 5


def test_postgres_alerts_repository_rejects_malicious_schema_injection() -> None:
    """
    Verifica que cualquier intento de inyectar SQL en tenant_schema sea
    bloqueado de inmediato por validate_tenant_schema_name antes de llegar a PostgreSQL.
    """
    malicious_schemas = [
        "tenant_alpha; DROP TABLE productos; --",
        "public",
        "tenant_alpha' OR '1'='1",
        "tenant_alpha UNION SELECT * FROM users",
        "pg_catalog",
        "information_schema",
        "../../../etc/passwd",
    ]

    for evil_schema in malicious_schemas:
        with pytest.raises(ValueError) as excinfo:
            validate_tenant_schema_name(evil_schema)
        assert "TenantSchemaValidationError" in str(excinfo.value) or "Esquema inválido" in str(excinfo.value)


@pytest.mark.asyncio
async def test_cross_tenant_data_leakage_prevented_in_repository() -> None:
    """
    Verifica que datos de stock crítico y vencimientos cargados en Tenant Alpha
    sean completamente invisibles cuando se consulta bajo el esquema de Tenant Beta.
    """
    repo = _alerts_service.repository
    assert isinstance(repo, InMemoryAlertsRepository)

    # 1. Cargar insumo crítico exclusivo en Tenant Alpha
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=1,
            bodega_id=1,
            bodega_nombre="Bodega Central Alpha",
            producto_nombre="Insumo Secreto Alpha",
            stock_actual=Decimal("0.0000"),
            stock_minimo=Decimal("10.0000"),
            unidad_medida="UN",
        ),
        tenant_schema=TENANT_ALPHA,
    )

    # 2. Consultar Tenant Alpha -> 1 alerta
    alpha_summary = await _alerts_service.get_alerts(tenant_id=TENANT_ALPHA)
    assert alpha_summary.total_count == 1
    assert alpha_summary.critical_stock[0].producto_nombre == "Insumo Secreto Alpha"

    # 3. Consultar Tenant Beta -> 0 alertas (cero fuga cross-tenant)
    beta_summary = await _alerts_service.get_alerts(tenant_id=TENANT_BETA)
    assert beta_summary.total_count == 0
    assert len(beta_summary.critical_stock) == 0


@pytest.mark.asyncio
async def test_cross_tenant_idor_header_jump_blocked_with_403(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un usuario de Tenant Alpha que intente enviar cabecera X-Tenant-ID
    apuntando a Tenant Beta sea bloqueado con HTTP 403 CROSS_TENANT_ACCESS_VIOLATION.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )

    # Ataque IDOR: JWT de Tenant Alpha pero solicitando Tenant Beta en la cabecera
    headers_cross = {
        "Authorization": f"Bearer {token_alpha}",
        "X-Tenant-ID": TENANT_BETA,
    }

    # 1. Endpoint /alerts
    resp_alerts = await async_client.get(
        "/api/v1/inventory/alerts",
        headers=headers_cross,
    )
    assert resp_alerts.status_code == 403
    problem_alerts = resp_alerts.json()
    assert problem_alerts["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 2. Endpoint /alerts/badge
    resp_badge = await async_client.get(
        "/api/v1/inventory/alerts/badge",
        headers=headers_cross,
    )
    assert resp_badge.status_code == 403
    problem_badge = resp_badge.json()
    assert problem_badge["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


@pytest.mark.asyncio
async def test_cross_tenant_idor_unknown_tenant_blocked_with_403(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que enviar un X-Tenant-ID no perteneciente al token del usuario
    sea rechazado con HTTP 403.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers_evil = {
        "Authorization": f"Bearer {token_alpha}",
        "X-Tenant-ID": "tenant_hacker_unauthorized",
    }

    resp = await async_client.get(
        "/api/v1/inventory/alerts",
        headers=headers_evil,
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


# ============================================================================
# VECTOR 2: RBAC ESTRICTO DE 3 NIVELES (inventory.alerts.read)
# ============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_requests_blocked_with_401(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que solicitudes anónimas o sin token Bearer sean bloqueadas con HTTP 401."""
    # 1. /alerts sin Authorization
    r1 = await async_client.get("/api/v1/inventory/alerts")
    assert r1.status_code == 401
    assert "detail" in r1.json()

    # 2. /alerts/badge sin Authorization
    r2 = await async_client.get("/api/v1/inventory/alerts/badge")
    assert r2.status_code == 401
    assert "detail" in r2.json()

    # 3. Token malformado
    r3 = await async_client.get(
        "/api/v1/inventory/alerts",
        headers={"Authorization": "Bearer malformed.token.here", "X-Tenant-ID": TENANT_ALPHA},
    )
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_insufficient_permissions_blocked_with_403(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Comprueba que roles con permisos adyacentes de inventario pero sin
    'inventory.alerts.read' reciban HTTP 403 PERMISSION_DENIED.
    """
    adjacent_permissions = [
        ["inventory.stock.read"],
        ["inventory.kardex.read"],
        ["inventory.counts.read"],
        ["inventory.mermas.create"],
        ["inventory.stock.transfer"],
    ]

    for perms in adjacent_permissions:
        token = _create_token(
            user_id=202,
            tenant_id=TENANT_ALPHA,
            permissions=perms,
        )
        headers = _make_headers(token, TENANT_ALPHA)

        # GET /alerts
        resp = await async_client.get("/api/v1/inventory/alerts", headers=headers)
        assert resp.status_code == 403, f"Failed for permissions: {perms}"
        assert resp.json()["status"] == 403

        # GET /alerts/badge
        resp_b = await async_client.get("/api/v1/inventory/alerts/badge", headers=headers)
        assert resp_b.status_code == 403, f"Failed for permissions: {perms}"
        assert resp_b.json()["status"] == 403


@pytest.mark.asyncio
async def test_explicit_deny_blocks_access_even_with_role_grant(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Comprueba que un explicit_deny sobre 'inventory.alerts.read' sobreescriba
    cualquier concesión de rol y retorne HTTP 403.
    """
    token = _create_token(
        user_id=303,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
        explicit_denies=["inventory.alerts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    resp = await async_client.get("/api/v1/inventory/alerts", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error_code"] in ("EXPLICIT_DENY", "EXPLICIT_DENY_GRANT")


@pytest.mark.asyncio
async def test_session_killswitch_revocation_blocks_alerts(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que revocar el jti o user_id invalida de inmediato el acceso con HTTP 401."""
    test_jti = "jwt-killswitch-test-alerts-001"
    token = _create_token(
        user_id=404,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
        jti=test_jti,
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Acceso exitoso antes de revocar
    r_ok = await async_client.get("/api/v1/inventory/alerts", headers=headers)
    assert r_ok.status_code == 200

    # 2. Revocar sesión por jti
    revoke_session_token(jti=test_jti)

    # 3. Acceso denegado de inmediato con HTTP 401
    r_revoked = await async_client.get("/api/v1/inventory/alerts", headers=headers)
    assert r_revoked.status_code == 401


@pytest.mark.asyncio
async def test_authorized_user_and_superuser_god_success(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que usuarios con permiso legítimo o Superuser God obtienen HTTP 200 OK."""
    # 1. Usuario con inventory.alerts.read
    token_user = _create_token(
        user_id=505,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers_user = _make_headers(token_user, TENANT_ALPHA)

    r1 = await async_client.get("/api/v1/inventory/alerts", headers=headers_user)
    assert r1.status_code == 200

    r2 = await async_client.get("/api/v1/inventory/alerts/badge", headers=headers_user)
    assert r2.status_code == 200

    # 2. Superuser God
    token_god = _create_token(
        user_id=1,
        tenant_id=TENANT_ALPHA,
        permissions=[],
        is_superuser_god=True,
    )
    headers_god = _make_headers(token_god, TENANT_ALPHA)

    r_god1 = await async_client.get("/api/v1/inventory/alerts", headers=headers_god)
    assert r_god1.status_code == 200

    r_god2 = await async_client.get("/api/v1/inventory/alerts/badge", headers=headers_god)
    assert r_god2.status_code == 200


# ============================================================================
# VECTOR 3: BLOQUEO DE INYECCIÓN SQL Y SANITIZACIÓN DE PARÁMETROS
# ============================================================================


@pytest.mark.asyncio
async def test_sql_injection_in_bodega_id_blocked_with_422(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que vectores SQLi en bodega_id sean interceptados con HTTP 422 por FastAPI."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    sqli_payloads = [
        "1 OR 1=1",
        "1; DROP TABLE productos; --",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "NaN",
        "1.5",
    ]

    for payload in sqli_payloads:
        # GET /alerts?bodega_id=...
        r1 = await async_client.get(
            f"/api/v1/inventory/alerts?bodega_id={payload}",
            headers=headers,
        )
        assert r1.status_code == 422, f"Failed to reject bodega_id={payload}"

        # GET /alerts/badge?bodega_id=...
        r2 = await async_client.get(
            f"/api/v1/inventory/alerts/badge?bodega_id={payload}",
            headers=headers,
        )
        assert r2.status_code == 422, f"Failed to reject badge bodega_id={payload}"


@pytest.mark.asyncio
async def test_sql_injection_in_area_operativa_id_blocked_with_422(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que vectores SQLi en area_operativa_id sean interceptados con HTTP 422."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    sqli_payloads = [
        "1 OR 1=1",
        "1; DROP TABLE bodegas; --",
        "' OR '1'='1",
        "admin'--",
        "NaN",
    ]

    for payload in sqli_payloads:
        r1 = await async_client.get(
            f"/api/v1/inventory/alerts?area_operativa_id={payload}",
            headers=headers,
        )
        assert r1.status_code == 422

        r2 = await async_client.get(
            f"/api/v1/inventory/alerts/badge?area_operativa_id={payload}",
            headers=headers,
        )
        assert r2.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_and_enum_evasion_in_tipo_param(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que valores SQLi o no contemplados en 'tipo' sean bloqueados con HTTP 400 ProblemDetails."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    evil_types = [
        "' OR 1=1 --",
        "'; DROP TABLE registro_stock; --",
        "UNION SELECT null, null--",
        "admin'--",
        "non_existent_filter",
    ]

    for payload in evil_types:
        resp = await async_client.get(
            f"/api/v1/inventory/alerts?tipo={payload}",
            headers=headers,
        )
        assert resp.status_code == 400
        problem = resp.json()
        assert problem["status"] == 400
        assert "invalid_filter_type" in problem["detail"] or "Valores admitidos" in problem["detail"]


@pytest.mark.asyncio
async def test_parameter_tampering_upcoming_days_blocked_with_422(
    async_client: httpx.AsyncClient,
) -> None:
    """Comprueba que upcoming_days exija enteros >= 1 y rechace valores negativos o inyecciones."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    tampered_values = [
        "-1",
        "-30",
        "0",
        "30.5",
        "1 OR 1=1",
        "NaN",
    ]

    for val in tampered_values:
        resp = await async_client.get(
            f"/api/v1/inventory/alerts?upcoming_days={val}",
            headers=headers,
        )
        assert resp.status_code == 422, f"Failed to reject upcoming_days={val}"


# ============================================================================
# VECTOR 4: FUZZING OPENAPI Y MASS ASSIGNMENT (extra="forbid")
# ============================================================================


def test_mass_assignment_forbidden_on_all_alert_schemas() -> None:
    """
    Verifica que todos los esquemas Pydantic v2 de schemas_alerts.py tengan
    model_config extra='forbid' y rechacen cualquier atributo inyectado.
    """
    ratio = StockHealthRatioResponse(
        stock_actual=Decimal("10.00"),
        stock_minimo=Decimal("20.00"),
        raw_ratio=Decimal("50.00"),
        clamped_ratio=Decimal("50.00"),
        status="critical",
    )

    # 1. StockHealthRatioResponse
    with pytest.raises(ValidationError) as exc1:
        StockHealthRatioResponse(
            stock_actual=Decimal("10.00"),
            stock_minimo=Decimal("20.00"),
            raw_ratio=Decimal("50.00"),
            clamped_ratio=Decimal("50.00"),
            status="critical",
            injected_privilege=True,  # Mass Assignment
        )
    assert "extra_forbidden" in str(exc1.value)

    # 2. CriticalStockAlertResponse
    with pytest.raises(ValidationError) as exc2:
        CriticalStockAlertResponse(
            producto_id=1,
            bodega_id=1,
            bodega_nombre="Bodega 1",
            producto_nombre="Harina",
            stock_actual=Decimal("0.00"),
            stock_minimo=Decimal("10.00"),
            unidad_medida="KG",
            ratio=ratio,
            is_depleted=True,
            bypass_audit=1,  # Mass Assignment
        )
    assert "extra_forbidden" in str(exc2.value)

    # 3. ExpiredLotAlertResponse
    with pytest.raises(ValidationError) as exc3:
        ExpiredLotAlertResponse(
            producto_id=2,
            bodega_id=1,
            bodega_nombre="Bodega 1",
            producto_nombre="Yogurt",
            fecha_vencimiento=date.today(),
            cantidad_vencida=Decimal("5.00"),
            dias_vencido=1,
            costo_ppp=Decimal("100.00"),
            valor_total_riesgo=Decimal("500.00"),
            unidad_medida="UN",
            admin_flag=True,  # Mass Assignment
        )
    assert "extra_forbidden" in str(exc3.value)

    # 4. UpcomingExpiryAlertResponse
    with pytest.raises(ValidationError) as exc4:
        UpcomingExpiryAlertResponse(
            producto_id=3,
            bodega_id=1,
            bodega_nombre="Bodega 1",
            producto_nombre="Leche",
            fecha_vencimiento=date.today() + timedelta(days=5),
            cantidad_en_riesgo=Decimal("10.00"),
            dias_restantes=5,
            costo_ppp=Decimal("50.00"),
            valor_total_riesgo=Decimal("500.00"),
            unidad_medida="LT",
            fake_grant="superuser",  # Mass Assignment
        )
    assert "extra_forbidden" in str(exc4.value)

    # 5. AlertsSummaryResponse
    with pytest.raises(ValidationError) as exc5:
        AlertsSummaryResponse(
            total_count=0,
            critical_count=0,
            expired_count=0,
            upcoming_count=0,
            has_critical=False,
            total_financial_risk=Decimal("0.00"),
            injected_override=1,  # Mass Assignment
        )
    assert "extra_forbidden" in str(exc5.value)

    # 6. AlertsBadgeResponse
    with pytest.raises(ValidationError) as exc6:
        AlertsBadgeResponse(
            total_count=0,
            has_critical=False,
            critical_stock_count=0,
            expired_count=0,
            upcoming_count=0,
            shadow_token="xyz",  # Mass Assignment
        )
    assert "extra_forbidden" in str(exc6.value)


@pytest.mark.asyncio
async def test_http_methods_strictly_limited_to_get(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que POST, PUT, DELETE, PATCH retornen HTTP 405 Method Not Allowed."""
    token = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # Métodos prohibidos en /alerts
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        resp = await async_client.request(
            method,
            "/api/v1/inventory/alerts",
            headers=headers,
            content=b'{"data": "exploit"}',
        )
        assert resp.status_code == 405, f"Expected 405 for {method} /alerts"

    # Métodos prohibidos en /alerts/badge
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        resp = await async_client.request(
            method,
            "/api/v1/inventory/alerts/badge",
            headers=headers,
            content=b'{"data": "exploit"}',
        )
        assert resp.status_code == 405, f"Expected 405 for {method} /alerts/badge"


# ============================================================================
# VECTOR 5: FUGA DE PII Y OBSERVABILIDAD SEGURA
# ============================================================================


@pytest.mark.asyncio
async def test_pii_deterministic_scrubbing_in_alerts_broadcast() -> None:
    """
    Verifica que el método broadcast_alerts_changed redacte de forma recursiva
    y determinista cualquier dato sensible (password, token, rut, tarjeta)
    sustituyéndolo por '[REDACTED_PII]'.
    """
    raw_payload: dict[str, object] = {
        "action": "alerts_changed",
        "tenant_id": TENANT_ALPHA,
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy.sig",
        "authorization": "Bearer dummy_jwt",
        "user_profile": {
            "rut": "12.345.678-9",
            "credit_card": "4111-2222-3333-4444",
            "cvv": "999",
            "secret_key": SecretStr("encrypted_value"),
            "safe_counter": 12,
        },
    }

    scrubbed = scrub_telemetry_payload(raw_payload)

    assert scrubbed["password"] == REDACTED_MARKER
    assert scrubbed["access_token"] == REDACTED_MARKER
    assert scrubbed["authorization"] == REDACTED_MARKER

    profile = scrubbed["user_profile"]
    assert isinstance(profile, dict)
    assert profile["rut"] == REDACTED_MARKER
    assert profile["credit_card"] == REDACTED_MARKER
    assert profile["cvv"] == REDACTED_MARKER
    assert profile["secret_key"] == REDACTED_MARKER
    assert profile["safe_counter"] == 12

    # Verificar que el servicio ejecute el scrub sin excepciones
    await _alerts_service.broadcast_alerts_changed(
        tenant_id=TENANT_ALPHA,
        holding_id=HOLDING_ID,
        target_bodega_id=1,
        payload=raw_payload,
    )


@pytest.mark.asyncio
async def test_zero_stacktrace_disclosure_on_rfc7807_errors(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que errores 401, 403 y 422 cumplan RFC 7807 sin filtrar jamás
    rutas locales, trazas de depuración (tracebacks), ni versiones internas.
    """
    forbidden_leak_strings = (
        "Traceback (most recent call last)",
        "sqlalchemy.exc",
        "asyncpg",
        "/home/jcampillay",
        "site-packages",
        "Password",
    )

    # 1. Error 401
    r_401 = await async_client.get("/api/v1/inventory/alerts")
    assert r_401.status_code == 401
    for leak in forbidden_leak_strings:
        assert leak not in r_401.text

    # 2. Error 403
    token_unauth = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.kardex.read"],
    )
    headers = _make_headers(token_unauth, TENANT_ALPHA)
    r_403 = await async_client.get("/api/v1/inventory/alerts", headers=headers)
    assert r_403.status_code == 403
    for leak in forbidden_leak_strings:
        assert leak not in r_403.text

    # 3. Error 422
    token_auth = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.alerts.read"],
    )
    headers_auth = _make_headers(token_auth, TENANT_ALPHA)
    r_422 = await async_client.get(
        "/api/v1/inventory/alerts?upcoming_days=invalid_string",
        headers=headers_auth,
    )
    assert r_422.status_code == 422
    for leak in forbidden_leak_strings:
        assert leak not in r_422.text
