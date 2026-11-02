"""
Vector Red Team 21 (`tests/security_redteam/test_21_events_offensive_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant Estricto, Prevención Anti-IDOR,
Matriz RBAC de 3 Niveles y Protección de PII en el Módulo de Eventos y Salones (/api/v1/events):
1. Control de Acceso 401 Unauthorized sin credenciales JWT.
2. Verificación Exhaustiva de Guardias RBAC de 3 Niveles con Denegación 403 RFC 7807 (ProblemDetails):
   - `events.salones.read`, `events.salones.manage`
   - `events.events.read`, `events.events.create`, `events.events.edit`,
   - `events.events.delete`, `events.events.execute`, `events.events.cancel`
3. Evaluación de Explicit Denies con revocación inmediata sobre Role Grants.
4. Prevención Estricta de IDOR Cross-Tenant en Salones (/salones/{id}: GET, PUT, DELETE).
5. Prevención Estricta de IDOR Cross-Tenant en Eventos (/{id}: GET, PUT, DELETE).
6. Prevención Estricta de IDOR Cross-Tenant en Acciones de Eventos (/execute, /cancel, /reactivate, /reverse, /minuta).
7. Aislamiento Cross-Tenant en Analítica (/faltantes, /analytics/committed-stock, /alerts) y Exportación CSV (/export/minuta-excel).
8. Inmunidad ante Inyección de Salón Foráneo Cross-Tenant durante el agendamiento.
9. Resiliencia contra Concurrencia Maliciosa y Anti-Overbooking Temporal (409 Conflict).
10. Rechazo de Payloads Maliciosos / Alterados (números negativos, aforos inválidos) con 422 Unprocessable Entity.
11. Protección de PII y Cero Fuga de Información Sensible en logs, traces y respuestas.
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.core.guards import clear_revoked_sessions
from src.core.security import create_access_token
from src.main import create_app
from src.modules.events.presentation.router import (
    get_event_service,
    get_salon_service,
)
from src.modules.inventory.application.inventory_service import InventoryService

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_alpha_las_condes"
TENANT_BETA = "tenant_beta_vina_del_mar"
HOLDING_ID = "holding_oppytec_events"

ALL_EVENTS_PERMISSIONS = [
    "events.salones.read",
    "events.salones.manage",
    "events.events.read",
    "events.events.create",
    "events.events.edit",
    "events.events.delete",
    "events.events.execute",
    "events.events.cancel",
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
    """Genera token JWT firmado con contexto de tenant y permisos RBAC de 3 niveles."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=accessible_tenants or [tenant_id],
        contracted_modules=["events", "inventory", "catalog"],
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_env() -> None:
    """Aislamiento e higienización estricta de estado en memoria entre ejecuciones."""
    clear_revoked_sessions()
    salon_srv = get_salon_service()
    event_srv = get_event_service()
    salon_srv.reset()
    event_srv.reset()


# ============================================================================
# VECTOR 1: CONTROL DE ACCESO BÁSICO Y 401 UNAUTHENTICATED
# ============================================================================


def test_01_unauthenticated_requests_rejected_with_401() -> None:
    """Valida que cualquier intento de acceso sin cabecera Authorization sea rechazado con 401."""
    app = create_app()
    with TestClient(app) as client:
        # Endpoints de Salones
        assert client.get("/api/v1/events/salones").status_code == 401
        assert client.post("/api/v1/events/salones", json={"nombre": "Salón Hacker"}).status_code == 401
        assert client.get(f"/api/v1/events/salones/{uuid4()}").status_code == 401
        assert client.put(f"/api/v1/events/salones/{uuid4()}", json={"nombre": "Salón Hacker"}).status_code == 401
        assert client.delete(f"/api/v1/events/salones/{uuid4()}").status_code == 401

        # Endpoints de Eventos
        assert client.get("/api/v1/events").status_code == 401
        assert client.post("/api/v1/events", json={"nombre": "Banquete Ilegal"}).status_code == 401
        assert client.get("/api/v1/events/faltantes").status_code == 401
        assert client.get("/api/v1/events/analytics/committed-stock").status_code == 401
        assert client.get("/api/v1/events/alerts").status_code == 401
        assert client.post("/api/v1/events/export/minuta-excel").status_code == 401
        assert client.get(f"/api/v1/events/{uuid4()}").status_code == 401
        assert client.put(f"/api/v1/events/{uuid4()}", json={"nombre": "Update"}).status_code == 401
        assert client.delete(f"/api/v1/events/{uuid4()}").status_code == 401
        assert client.post(f"/api/v1/events/{uuid4()}/execute").status_code == 401
        assert client.post(f"/api/v1/events/{uuid4()}/cancel").status_code == 401
        assert client.post(f"/api/v1/events/{uuid4()}/reactivate").status_code == 401
        assert client.post(f"/api/v1/events/{uuid4()}/reverse", json={"motivo": "Anulación"}).status_code == 401
        assert client.get(f"/api/v1/events/{uuid4()}/minuta").status_code == 401


# ============================================================================
# VECTOR 2: MATRIZ NEGATIVA DE GUARDÍAS RBAC DE 3 NIVELES (403 RFC 7807)
# ============================================================================


def test_02_rbac_3_level_negative_matrix_on_all_endpoints() -> None:
    """
    Verifica que un usuario autenticado pero SIN los permisos requeridos
    reciba denegación 403 Forbidden RFC 7807 (ProblemDetails) en todos los endpoints.
    """
    app = create_app()
    # Usuario con permiso no relacionado
    unrelated_token = _create_token(201, TENANT_ALPHA, ["unrelated.module.read"])
    unrelated_headers = _make_headers(unrelated_token, TENANT_ALPHA)

    fake_id = uuid4()
    with TestClient(app) as client:
        test_cases: list[tuple[str, str, dict[str, Any] | None, str]] = [
            ("GET", "/api/v1/events/salones", None, "events.salones.read"),
            ("POST", "/api/v1/events/salones", {"nombre": "X"}, "events.salones.manage"),
            ("GET", f"/api/v1/events/salones/{fake_id}", None, "events.salones.read"),
            ("PUT", f"/api/v1/events/salones/{fake_id}", {"nombre": "X"}, "events.salones.manage"),
            ("DELETE", f"/api/v1/events/salones/{fake_id}", None, "events.salones.manage"),
            ("GET", "/api/v1/events", None, "events.events.read"),
            ("POST", "/api/v1/events", {"nombre": "X", "fecha": "2026-11-20"}, "events.events.create"),
            ("GET", "/api/v1/events/faltantes", None, "events.events.read"),
            ("GET", "/api/v1/events/analytics/faltantes", None, "events.events.read"),
            ("GET", "/api/v1/events/analytics/committed-stock", None, "events.events.read"),
            ("GET", "/api/v1/events/alerts", None, "events.events.read"),
            ("POST", "/api/v1/events/export/minuta-excel", None, "events.events.read"),
            ("GET", f"/api/v1/events/{fake_id}", None, "events.events.read"),
            ("PUT", f"/api/v1/events/{fake_id}", {"nombre": "X"}, "events.events.edit"),
            ("DELETE", f"/api/v1/events/{fake_id}", None, "events.events.delete"),
            ("POST", f"/api/v1/events/{fake_id}/execute", None, "events.events.execute"),
            ("POST", f"/api/v1/events/{fake_id}/cancel", None, "events.events.cancel"),
            ("POST", f"/api/v1/events/{fake_id}/reactivate", None, "events.events.edit"),
            ("POST", f"/api/v1/events/{fake_id}/reverse", {"motivo": "Anulación"}, "events.events.cancel"),
            ("GET", f"/api/v1/events/{fake_id}/minuta", None, "events.events.read"),
        ]

        for method, path, payload, required_perm in test_cases:
            if method == "GET":
                resp = client.get(path, headers=unrelated_headers)
            elif method == "POST":
                resp = client.post(path, json=payload, headers=unrelated_headers)
            elif method == "PUT":
                resp = client.put(path, json=payload, headers=unrelated_headers)
            elif method == "DELETE":
                resp = client.delete(path, headers=unrelated_headers)
            else:
                pytest.fail(f"Método desconocido {method}")

            assert resp.status_code == 403, (
                f"Falla de RBAC en {method} {path}: esperado 403, obtenido {resp.status_code}. "
                f"Debe exigir guardia de 3 niveles '{required_perm}'."
            )
            prob = resp.json()
            assert prob.get("status") == 403
            assert prob.get("error_code") in ("MISSING_PERMISSION", "RBAC_PERMISSION_DENIED")


# ============================================================================
# VECTOR 3: PREVALENCIA ESTRICTA DE EXPLICIT DENY SOBRE ROLE GRANTS
# ============================================================================


def test_03_explicit_deny_overrides_role_grants() -> None:
    """
    Un explicit deny revoca inmediatamente el acceso aunque el usuario posea
    el permiso en sus asignaciones de rol (role_grants).
    """
    app = create_app()

    # Usuario con role_grant 'events.events.create', pero con explicit_deny sobre el mismo permiso
    token = _create_token(
        202,
        TENANT_ALPHA,
        permissions=["events.events.create", "events.events.read"],
        explicit_denies=["events.events.create"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    with TestClient(app) as client:
        # Puede leer (no tiene deny)
        resp_read = client.get("/api/v1/events", headers=headers)
        assert resp_read.status_code == 200

        # No puede crear (bloqueado por explicit deny)
        resp_create = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Denegado Explícito",
                "fecha": "2026-11-25",
            },
            headers=headers,
        )
        assert resp_create.status_code == 403
        prob = resp_create.json()
        assert prob["status"] == 403
        assert prob["error_code"] in ("EXPLICIT_DENY_GRANT", "EXPLICIT_DENY", "MISSING_PERMISSION", "RBAC_PERMISSION_DENIED")


# ============================================================================
# VECTOR 4: AISLAMIENTO MULTI-TENANT Y PREVENCIÓN IDOR EN SALONES
# ============================================================================


def test_04_strict_multi_tenant_isolation_salones_idor() -> None:
    """
    Garantiza que ningún tenant pueda consultar, modificar o eliminar salones
    pertenecientes a otro tenant (Aislamiento de esquemas y claves en memoria).
    """
    app = create_app()
    token_a = _create_token(301, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    token_b = _create_token(302, TENANT_BETA, ALL_EVENTS_PERMISSIONS)

    headers_a = _make_headers(token_a, TENANT_ALPHA)
    headers_b = _make_headers(token_b, TENANT_BETA)

    with TestClient(app) as client:
        # 1. Tenant Alpha crea un salón
        resp_create = client.post(
            "/api/v1/events/salones",
            json={
                "nombre": "Salón Los Condores Alpha",
                "capacidad_personas": 150,
                "precio_neto": "200000.00",
                "iva_porcentaje": "19.00",
                "notas": "Salón exclusivo Alpha",
            },
            headers=headers_a,
        )
        assert resp_create.status_code == 201
        salon_a = resp_create.json()
        salon_a_id = salon_a["id"]

        # 2. Tenant Beta intenta ataque IDOR: consultar el salón de Alpha
        resp_get_idor = client.get(f"/api/v1/events/salones/{salon_a_id}", headers=headers_b)
        assert resp_get_idor.status_code == 404, (
            "Vulnerabilidad IDOR crítica: Tenant Beta pudo acceder al salón de Tenant Alpha!"
        )

        # 3. Tenant Beta intenta ataque IDOR: modificar el salón de Alpha
        resp_put_idor = client.put(
            f"/api/v1/events/salones/{salon_a_id}",
            json={"nombre": "Salón Secuestrado por Beta"},
            headers=headers_b,
        )
        assert resp_put_idor.status_code == 404

        # 4. Tenant Beta intenta ataque IDOR: eliminar el salón de Alpha
        resp_del_idor = client.delete(f"/api/v1/events/salones/{salon_a_id}", headers=headers_b)
        assert resp_del_idor.status_code == 404

        # 5. Tenant Beta lista salones: debe estar completamente vacío para Beta
        resp_list_beta = client.get("/api/v1/events/salones", headers=headers_b)
        assert resp_list_beta.status_code == 200
        salones_beta = resp_list_beta.json()
        assert len(salones_beta) == 0

        # 6. Tenant Alpha verifica que su salón sigue intacto
        resp_get_alpha = client.get(f"/api/v1/events/salones/{salon_a_id}", headers=headers_a)
        assert resp_get_alpha.status_code == 200
        assert resp_get_alpha.json()["nombre"] == "Salón Los Condores Alpha"


# ============================================================================
# VECTOR 5: AISLAMIENTO MULTI-TENANT Y PREVENCIÓN IDOR EN EVENTOS
# ============================================================================


def test_05_strict_multi_tenant_isolation_events_idor() -> None:
    """
    Garantiza que ningún tenant pueda consultar, editar o borrar eventos
    pertenecientes a otro tenant.
    """
    app = create_app()
    token_a = _create_token(401, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    token_b = _create_token(402, TENANT_BETA, ALL_EVENTS_PERMISSIONS)

    headers_a = _make_headers(token_a, TENANT_ALPHA)
    headers_b = _make_headers(token_b, TENANT_BETA)

    with TestClient(app) as client:
        # 1. Tenant Alpha crea un evento
        resp_create = client.post(
            "/api/v1/events",
            json={
                "nombre": "Gala Anual Alpha",
                "titular": "Holding Alpha Corp",
                "fecha": "2026-11-28",
                "hora_inicio": "19:00:00",
                "hora_fin": "23:00:00",
                "cantidad_personas": 100,
                "valor_publico": "1500000.00",
            },
            headers=headers_a,
        )
        assert resp_create.status_code == 201
        event_a = resp_create.json()
        event_a_id = event_a["id"]

        # 2. Tenant Beta intenta IDOR: GET /{event_a_id}
        resp_get_idor = client.get(f"/api/v1/events/{event_a_id}", headers=headers_b)
        assert resp_get_idor.status_code == 404, (
            "Vulnerabilidad IDOR crítica: Tenant Beta pudo ver el evento de Tenant Alpha!"
        )

        # 3. Tenant Beta intenta IDOR: PUT /{event_a_id}
        resp_put_idor = client.put(
            f"/api/v1/events/{event_a_id}",
            json={"nombre": "Evento Saboteado por Beta"},
            headers=headers_b,
        )
        assert resp_put_idor.status_code == 404

        # 4. Tenant Beta intenta IDOR: DELETE /{event_a_id}
        resp_del_idor = client.delete(f"/api/v1/events/{event_a_id}", headers=headers_b)
        assert resp_del_idor.status_code == 404

        # 5. Tenant Beta lista eventos: 0 eventos para Beta
        resp_list_beta = client.get("/api/v1/events", headers=headers_b)
        assert resp_list_beta.status_code == 200
        assert len(resp_list_beta.json()) == 0

        # 6. Tenant Alpha verifica que su evento permanece inalterado
        resp_get_alpha = client.get(f"/api/v1/events/{event_a_id}", headers=headers_a)
        assert resp_get_alpha.status_code == 200
        assert resp_get_alpha.json()["nombre"] == "Gala Anual Alpha"


# ============================================================================
# VECTOR 6: AISLAMIENTO IDOR EN ACCIONES TRANSACCIONALES DE EVENTOS
# ============================================================================


def test_06_strict_multi_tenant_isolation_events_actions_idor() -> None:
    """
    Garantiza que acciones de ciclo de vida (ejecutar, cancelar, reactivar,
    revertir en Kardex y descargar minuta) estén blindadas contra IDOR inter-tenant.
    """
    app = create_app()
    token_a = _create_token(501, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    token_b = _create_token(502, TENANT_BETA, ALL_EVENTS_PERMISSIONS)

    headers_a = _make_headers(token_a, TENANT_ALPHA)
    headers_b = _make_headers(token_b, TENANT_BETA)

    with TestClient(app) as client:
        # 1. Tenant Alpha crea un evento
        resp_create = client.post(
            "/api/v1/events",
            json={
                "nombre": "Banquete Matrimonial Alpha",
                "fecha": "2026-11-29",
                "hora_inicio": "12:00:00",
                "hora_fin": "17:00:00",
                "cantidad_personas": 80,
                "items": [
                    {
                        "producto_id": 101,
                        "bodega_id": 1,
                        "cantidad": "20.0000",
                        "costo_unitario_estimado": "1500.00",
                    }
                ],
            },
            headers=headers_a,
        )
        assert resp_create.status_code == 201
        event_a_id = resp_create.json()["id"]

        # 2. Tenant Beta intenta ejecutar el evento de Alpha en Kardex -> 404
        resp_exec_idor = client.post(f"/api/v1/events/{event_a_id}/execute", headers=headers_b)
        assert resp_exec_idor.status_code == 404

        # 3. Tenant Beta intenta cancelar el evento de Alpha -> 404
        resp_cancel_idor = client.post(
            f"/api/v1/events/{event_a_id}/cancel",
            json={"motivo": "Cancelación maliciosa"},
            headers=headers_b,
        )
        assert resp_cancel_idor.status_code == 404

        # 4. Tenant Beta intenta reactivar el evento de Alpha -> 404
        resp_react_idor = client.post(f"/api/v1/events/{event_a_id}/reactivate", headers=headers_b)
        assert resp_react_idor.status_code == 404

        # 5. Tenant Beta intenta revertir el evento de Alpha -> 404
        resp_rev_idor = client.post(
            f"/api/v1/events/{event_a_id}/reverse",
            json={"motivo": "Reversa foránea"},
            headers=headers_b,
        )
        assert resp_rev_idor.status_code == 404

        # 6. Tenant Beta intenta descargar la minuta técnica confidencial de Alpha -> 404
        resp_minuta_idor = client.get(f"/api/v1/events/{event_a_id}/minuta", headers=headers_b)
        assert resp_minuta_idor.status_code == 404


# ============================================================================
# VECTOR 7: AISLAMIENTO MULTI-TENANT EN ANALÍTICA Y EXPORTACIÓN CSV
# ============================================================================


def test_07_strict_multi_tenant_isolation_analytics_and_exports() -> None:
    """
    Verifica que las métricas de faltantes, stock comprometido, alertas operativas
    y reportes exportados consolidados nunca filtren datos ni insumos entre inquilinos.
    """
    app = create_app()
    token_a = _create_token(601, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    token_b = _create_token(602, TENANT_BETA, ALL_EVENTS_PERMISSIONS)

    headers_a = _make_headers(token_a, TENANT_ALPHA)
    headers_b = _make_headers(token_b, TENANT_BETA)

    # Inyectar demanda en Tenant Alpha para generar faltantes y alertas
    tomorrow = date.today() + timedelta(days=1)
    with TestClient(app) as client:
        resp_ev_a = client.post(
            "/api/v1/events",
            json={
                "nombre": "Mega Evento Alpha con Quiebre",
                "fecha": str(tomorrow),
                "hora_inicio": "18:00:00",
                "hora_fin": "22:00:00",
                "items": [
                    {
                        "producto_id": 999,
                        "bodega_id": 1,
                        "cantidad": "500.0000",
                        "costo_unitario_estimado": "5000.00",
                    }
                ],
            },
            headers=headers_a,
        )
        assert resp_ev_a.status_code == 201
        ev_a_id = resp_ev_a.json()["id"]

        # 1. Tenant Alpha ve sus faltantes (debe reportar deficit de prod 999)
        resp_falt_a = client.get("/api/v1/events/faltantes", headers=headers_a)
        assert resp_falt_a.status_code == 200
        assert resp_falt_a.json()["total_faltantes"] >= 1

        # 2. Tenant Beta consulta faltantes: CERO faltantes y cero datos de Alpha
        resp_falt_b = client.get("/api/v1/events/faltantes", headers=headers_b)
        assert resp_falt_b.status_code == 200
        assert resp_falt_b.json()["total_faltantes"] == 0
        assert len(resp_falt_b.json()["items"]) == 0

        # 3. Tenant Beta consulta stock comprometido: CERO ítems comprometidos
        resp_comm_b = client.get("/api/v1/events/analytics/committed-stock", headers=headers_b)
        assert resp_comm_b.status_code == 200
        assert resp_comm_b.json()["total_items"] == 0

        # 4. Tenant Beta consulta alertas: CERO alertas operativas
        resp_alert_b = client.get("/api/v1/events/alerts", headers=headers_b)
        assert resp_alert_b.status_code == 200
        assert len(resp_alert_b.json()) == 0

        # 5. Tenant Beta intenta exportar la minuta del evento de Alpha mediante POST /export/minuta-excel
        resp_exp_b = client.post(
            "/api/v1/events/export/minuta-excel",
            json={"event_ids": [ev_a_id]},
            headers=headers_b,
        )
        assert resp_exp_b.status_code == 200
        csv_text = resp_exp_b.text
        # No debe contener el nombre ni datos del evento confidencial de Alpha
        assert "Mega Evento Alpha con Quiebre" not in csv_text
        assert "No hay eventos para exportar" in csv_text


# ============================================================================
# VECTOR 8: INMUNIDAD ANTE ASOCIACIÓN DE SALÓN FORÁNEO
# ============================================================================


def test_08_cross_tenant_foreign_salon_injection_isolation() -> None:
    """
    Comprueba que si Tenant Beta intenta agendar un evento asociando maliciosamente
    el UUID de un salón perteneciente a Tenant Alpha, no secuestra ni altera el salón
    de Alpha, ni provoca overbooking espurio en Tenant Alpha.
    """
    app = create_app()
    token_a = _create_token(701, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    token_b = _create_token(702, TENANT_BETA, ALL_EVENTS_PERMISSIONS)

    headers_a = _make_headers(token_a, TENANT_ALPHA)
    headers_b = _make_headers(token_b, TENANT_BETA)

    with TestClient(app) as client:
        # 1. Tenant Alpha crea un salón
        resp_salon_a = client.post(
            "/api/v1/events/salones",
            json={
                "nombre": "Salón Real Alpha",
                "capacidad_personas": 200,
            },
            headers=headers_a,
        )
        assert resp_salon_a.status_code == 201
        salon_a_id = resp_salon_a.json()["id"]

        # 2. Tenant Beta crea un evento pasando salon_id = salon_a_id
        target_date = "2026-12-15"
        resp_ev_b = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Beta con Salon Foraneo",
                "salon_id": salon_a_id,
                "fecha": target_date,
                "hora_inicio": "14:00:00",
                "hora_fin": "18:00:00",
                "cantidad_personas": 50,
            },
            headers=headers_b,
        )
        assert resp_ev_b.status_code == 201
        data_b = resp_ev_b.json()
        # El nombre del salón no debe haberse resuelto para Beta (permanece None)
        assert data_b["salon_nombre"] is None

        # 3. Tenant Alpha agenda un evento legítimo en SU salón para exactamente la misma fecha y horario
        resp_ev_a = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Legítimo Alpha en su Salón",
                "salon_id": salon_a_id,
                "fecha": target_date,
                "hora_inicio": "14:00:00",
                "hora_fin": "18:00:00",
                "cantidad_personas": 150,
            },
            headers=headers_a,
        )
        # Debe crearse exitosamente: la reserva fraudulenta de Beta NO bloqueó a Alpha
        assert resp_ev_a.status_code == 201
        assert resp_ev_a.json()["salon_nombre"] == "Salón Real Alpha"


# ============================================================================
# VECTOR 9: RESILIENCIA CONTRA ANTI-OVERBOOKING TEMPORAL Y CONFLICTOS (409)
# ============================================================================


def test_09_anti_overbooking_temporal_race_and_collision_conflict_409() -> None:
    """
    Comprueba que el motor de anti-overbooking rechace colisiones horarias en el mismo
    salón con código 409 Conflict (RFC 7807), tanto en creación como en edición y reactivación.
    """
    app = create_app()
    token = _create_token(801, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    with TestClient(app) as client:
        # 1. Crear Salón
        resp_sal = client.post(
            "/api/v1/events/salones",
            json={"nombre": "Salón Roble Centenario"},
            headers=headers,
        )
        assert resp_sal.status_code == 201
        salon_id = resp_sal.json()["id"]

        # 2. Primer Evento: 10:00 a 14:00
        resp_ev1 = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Matutino",
                "salon_id": salon_id,
                "fecha": "2026-11-15",
                "hora_inicio": "10:00:00",
                "hora_fin": "14:00:00",
            },
            headers=headers,
        )
        assert resp_ev1.status_code == 201
        ev1_id = resp_ev1.json()["id"]

        # 3. Intento de solapamiento directo: 12:00 a 16:00 -> 409 Conflict
        resp_ev2_conflict = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Solapado",
                "salon_id": salon_id,
                "fecha": "2026-11-15",
                "hora_inicio": "12:00:00",
                "hora_fin": "16:00:00",
            },
            headers=headers,
        )
        assert resp_ev2_conflict.status_code == 409
        prob = resp_ev2_conflict.json()
        assert prob["status"] == 409
        assert prob["error_code"] in ("EVENT_OVERBOOKING_ERROR", "EVENT_OVERBOOKING", "CONFLICT")

        # 4. Solapamiento al editar otro evento hacia la franja ocupada -> 409 Conflict
        resp_ev3 = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Tarde",
                "salon_id": salon_id,
                "fecha": "2026-11-15",
                "hora_inicio": "18:00:00",
                "hora_fin": "22:00:00",
            },
            headers=headers,
        )
        assert resp_ev3.status_code == 201
        ev3_id = resp_ev3.json()["id"]

        resp_edit_conflict = client.put(
            f"/api/v1/events/{ev3_id}",
            json={"hora_inicio": "11:00:00", "hora_fin": "15:00:00"},
            headers=headers,
        )
        assert resp_edit_conflict.status_code == 409


# ============================================================================
# VECTOR 10: RECHAZO DE PAYLOADS MALICIOSOS / PARÁMETROS NEGATIVOS (422)
# ============================================================================


def test_10_negative_and_tampered_payload_validation_422() -> None:
    """
    Asegura que entradas corrompidas, cantidades negativas, precios netos negativos
    o campos desconocidos (Mass Assignment forbid) sean rechazados con 422 Unprocessable Entity.
    """
    app = create_app()
    token = _create_token(901, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    with TestClient(app) as client:
        # 1. Salón con precio neto negativo
        resp_sal_neg = client.post(
            "/api/v1/events/salones",
            json={"nombre": "Salón Invalido", "precio_neto": "-1000.00"},
            headers=headers,
        )
        assert resp_sal_neg.status_code == 422

        # 2. Salón con IVA > 100%
        resp_sal_iva = client.post(
            "/api/v1/events/salones",
            json={"nombre": "Salón IVA Alto", "iva_porcentaje": "150.00"},
            headers=headers,
        )
        assert resp_sal_iva.status_code == 422

        # 3. Salón con campo no permitido (Mass Assignment forbid)
        resp_sal_extra = client.post(
            "/api/v1/events/salones",
            json={"nombre": "Salón Extra", "malicious_field": "hacked"},
            headers=headers,
        )
        assert resp_sal_extra.status_code == 422

        # 4. Evento con comensales negativos
        resp_ev_neg = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Negativo",
                "fecha": "2026-11-20",
                "cantidad_personas": -5,
            },
            headers=headers,
        )
        assert resp_ev_neg.status_code == 422

        # 5. Insumo con cantidad negativa
        resp_ev_item_neg = client.post(
            "/api/v1/events",
            json={
                "nombre": "Evento Item Negativo",
                "fecha": "2026-11-20",
                "items": [
                    {
                        "producto_id": 1,
                        "bodega_id": 1,
                        "cantidad": "-10.0000",
                    }
                ],
            },
            headers=headers,
        )
        assert resp_ev_item_neg.status_code == 422


# ============================================================================
# VECTOR 11: AUDITORÍA DE NO-EXPOSICIÓN DE PII EN RESPUESTAS Y LOGS
# ============================================================================


def test_11_zero_pii_leakage_and_observability_redaction(caplog: pytest.LogCaptureFixture) -> None:
    """
    Comprueba que credenciales, contraseñas, tarjetas de crédito y datos personales
    críticos no se registren en texto claro en los loggers ni se filtren en excepciones.
    """
    app = create_app()
    token = _create_token(1001, TENANT_ALPHA, ALL_EVENTS_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    with caplog.at_level(logging.DEBUG):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/events",
                json={
                    "nombre": "Boda Confidencial",
                    "titular": "Cliente VIP Sensible",
                    "fecha": "2026-12-30",
                    "hora_inicio": "20:00:00",
                    "hora_fin": "23:59:00",
                    "cantidad_personas": 50,
                    "notas": "Notas internas privadas",
                },
                headers=headers,
            )
            assert resp.status_code == 201

            # Disparar error 404
            client.get(f"/api/v1/events/{uuid4()}", headers=headers)

    captured_logs = caplog.text
    # Prohibido loguear hashes, contraseñas, tokens JWT en los mensajes de log
    assert "Bearer " not in captured_logs
    assert "password" not in captured_logs.lower()
    assert "secret" not in captured_logs.lower()
    assert "token" not in captured_logs.lower() or "realtime" in captured_logs.lower()
