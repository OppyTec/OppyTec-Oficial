"""
oppytec-backend/tests/unit/modules/test_actividades_services.py
Suite de pruebas unitarias y de integración REST para el Panel de Actividades de OppyTec v2.0:
1. Notas de Equipo (bitácora compartida con menciones y lecturas idempotentes).
2. Notas Personales (privacidad estricta por colaborador).
3. Tareas Operativas, Checklists y Validación Inviolable de 'incompleta'.
4. Plantillas de Rutinas de Apertura/Cierre y su aplicación en lote.
5. Horarios, Turnos, Clonación Semanal (Lunes a Lunes) y Auditoría Laboral (12h descanso y Ley 40 Horas).
6. Endpoints REST FastAPI y Guardias RBAC de 3 Niveles.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest

from src.core.exceptions import DomainValidationError, ResourceNotFoundError
from src.core.security import create_access_token
from src.modules.operations.application.actividades_service import ActividadesService
from src.modules.operations.presentation.router_actividades import get_actividades_service

pytestmark = pytest.mark.unit

TENANT_ID = "tenant_actividades_test"
HOLDING_ID = "holding_actividades_test"


def _make_auth_headers(permissions: list[str], user_id: int = 101) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_ID,
        holding_id=HOLDING_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.fixture(autouse=True)
def _reset_actividades_state() -> None:
    """Aísla el estado en memoria antes de cada test."""
    service = get_actividades_service()
    service.reset()


# ==============================================================================
# 1. PRUEBAS DE DOMINIO: NOTAS DE EQUIPO Y PERSONALES
# ==============================================================================


def test_notas_equipo_lifecycle_and_idempotent_read() -> None:
    """Valida creación, menciones, filtros, lecturas idempotentes y soft-delete de notas de equipo."""
    service = ActividadesService(use_in_memory=True)

    # 1. Crear nota con menciones
    nota = service.create_nota_equipo(
        autor_user_id=10,
        titulo="Cambio de aceite freidora 1",
        contenido="Se procedió con el drenado y limpieza de freidora principal.",
        area_id="cocina",
        categoria="mantencion",
        menciones_user_ids=[11, 12, 11],  # duplicado intencional para verificar set()
    )
    assert nota.id == 1
    assert nota.titulo == "Cambio de aceite freidora 1"
    assert len(nota.menciones) == 2  # 11 y 12 únicos

    # 2. Consultar con filtros y verificación de leido_por_mi
    notas_cocina = service.get_notas_equipo(area_id="cocina", current_user_id=11)
    assert len(notas_cocina) == 1
    assert notas_cocina[0]["leido_por_mi"] is False
    assert notas_cocina[0]["total_lecturas"] == 0

    # 3. Marcar lectura por usuario 11
    lec1 = service.mark_nota_as_read(nota_id=nota.id, user_id=11)
    assert lec1.user_id == 11

    # 4. Idempotencia: Volver a marcar lectura no duplica ni falla
    lec2 = service.mark_nota_as_read(nota_id=nota.id, user_id=11)
    assert lec1.id == lec2.id

    # Verificar enriquecimiento actualizado
    notas_despues = service.get_notas_equipo(area_id="cocina", current_user_id=11)
    assert notas_despues[0]["leido_por_mi"] is True
    assert notas_despues[0]["total_lecturas"] == 1

    # 5. Filtrar por usuario mencionado
    mencionados = service.get_notas_equipo(user_id_mencionado=12)
    assert len(mencionados) == 1
    no_mencionados = service.get_notas_equipo(user_id_mencionado=99)
    assert len(no_mencionados) == 0

    # 6. Actualizar nota
    updated = service.update_nota_equipo(
        nota_id=nota.id,
        user_id=10,
        titulo="Cambio de aceite freidora 1 (Completado)",
    )
    assert updated.titulo == "Cambio de aceite freidora 1 (Completado)"

    # 7. Soft delete
    deleted = service.delete_nota_equipo(nota_id=nota.id, user_id=10)
    assert deleted is True
    assert len(service.get_notas_equipo(area_id="cocina")) == 0


def test_notas_personales_privacy() -> None:
    """Verifica que las notas personales sean estrictamente privadas por usuario."""
    service = ActividadesService(use_in_memory=True)

    # User 1 crea nota
    np1 = service.create_nota_personal(
        user_id=1,
        titulo="Revisar cámaras frías al llegar",
        contenido="Comprobar que no baje de 4 grados.",
    )
    assert np1.id == 1

    # User 2 no debe verla en sus notas
    notas_u2 = service.get_notas_personales(user_id=2)
    assert len(notas_u2) == 0

    # User 1 sí la ve
    notas_u1 = service.get_notas_personales(user_id=1)
    assert len(notas_u1) == 1
    assert notas_u1[0].titulo == "Revisar cámaras frías al llegar"

    # User 2 no puede modificar la nota de User 1
    with pytest.raises(DomainValidationError):
        service.update_nota_personal(
            nota_id=np1.id,
            user_id=2,
            titulo="Intento de sabotaje",
        )

    # User 2 no puede eliminar la nota de User 1
    with pytest.raises(DomainValidationError):
        service.delete_nota_personal(nota_id=np1.id, user_id=2)

    # User 1 sí puede eliminarla
    assert service.delete_nota_personal(nota_id=np1.id, user_id=1) is True
    assert len(service.get_notas_personales(user_id=1)) == 0


# ==============================================================================
# 2. PRUEBAS DE DOMINIO: TAREAS OPERATIVAS Y PLANTILLAS
# ==============================================================================


def test_tarea_lifecycle_and_incompleta_validation() -> None:
    """Verifica CRUD de tareas y valida estrictamente que pasar a 'incompleta' exige 'nota_incompleta'."""
    service = ActividadesService(use_in_memory=True)

    tarea = service.create_tarea(
        titulo="Sanitización mesón central",
        creador_user_id=10,
        asignado_a_user_id=20,
        area_id="cocina",
        urgencia="alta",
    )
    assert tarea.id == 1
    assert tarea.estado == "pendiente"
    assert tarea.completada is False

    # Transición a 'progreso'
    t_prog = service.update_tarea_estado(tarea_id=tarea.id, estado="progreso")
    assert t_prog.estado == "progreso"
    assert t_prog.completada is False

    # VALIDACIÓN OBLIGATORIA: Transición a 'incompleta' sin motivo debe lanzar DomainValidationError
    with pytest.raises(DomainValidationError) as exc_info:
        service.update_tarea_estado(tarea_id=tarea.id, estado="incompleta", nota_incompleta=None)
    assert "nota_incompleta" in exc_info.value.message

    with pytest.raises(DomainValidationError) as exc_info2:
        service.update_tarea_estado(tarea_id=tarea.id, estado="incompleta", nota_incompleta="   ")
    assert "nota_incompleta" in exc_info2.value.message

    # Con motivo válido, transiciona exitosamente
    t_inc = service.update_tarea_estado(
        tarea_id=tarea.id,
        estado="incompleta",
        nota_incompleta="Faltó líquido desinfectante amonio cuaternario.",
    )
    assert t_inc.estado == "incompleta"
    assert t_inc.nota_incompleta == "Faltó líquido desinfectante amonio cuaternario."

    # Transición a 'completada' sincroniza el flag 'completada' en True
    t_comp = service.update_tarea_estado(tarea_id=tarea.id, estado="completada")
    assert t_comp.estado == "completada"
    assert t_comp.completada is True


def test_plantillas_rutinas_and_aplicar() -> None:
    """Verifica la instanciación automática de checklists operacionales desde plantillas."""
    service = ActividadesService(use_in_memory=True)

    plantilla = service.create_plantilla_rutina(
        nombre="Apertura Salón Principal",
        descripcion="Checklist previo a las 11:30 AM",
        area_id="salon",
        tipo_rutina="APERTURA",
        items_json=[
            {"titulo": "Encender iluminación y aire acondicionado", "urgencia": "alta"},
            {"titulo": "Revisar servilleteros y saleros", "urgencia": "media"},
            {"titulo": "Imprimir menú del día", "urgencia": "baja"},
        ],
    )
    assert plantilla.id == 1

    # Aplicar la plantilla
    tareas_creadas = service.aplicar_plantilla_rutina(
        plantilla_id=plantilla.id,
        asignado_a_user_id=30,
        creador_user_id=5,
    )
    assert len(tareas_creadas) == 3
    assert tareas_creadas[0].titulo == "Encender iluminación y aire acondicionado"
    assert tareas_creadas[0].area_id == "salon"
    assert tareas_creadas[0].plantilla_id == 1
    assert tareas_creadas[0].asignado_a_user_id == 30


# ==============================================================================
# 3. PRUEBAS DE DOMINIO: HORARIOS, CLONACIÓN Y AUDITORÍA LABORAL
# ==============================================================================


def test_turnos_horarios_and_clonar_semana() -> None:
    """Verifica la clonación de grilla semanal de turnos desplazando fechas exactamente 7 días."""
    service = ActividadesService(use_in_memory=True)

    # Lunes origen: 2026-11-02 (es lunes)
    lunes_origen = date(2026, 11, 2)
    assert lunes_origen.weekday() == 0

    # Crear 2 turnos en la semana origen
    t1 = service.create_turno_horario(
        user_id=101,
        area_id="cocina",
        fecha_inicio=lunes_origen,
        hora_inicio=time(8, 0),
        hora_fin=time(16, 0),
        nota="Turno mañana",
    )
    miercoles_origen = lunes_origen + timedelta(days=2)
    t2 = service.create_turno_horario(
        user_id=102,
        area_id="cocina",
        fecha_inicio=miercoles_origen,
        hora_inicio=time(14, 0),
        hora_fin=time(22, 0),
        nota="Turno tarde",
    )

    # Clonar al lunes siguiente: 2026-11-09
    lunes_destino = date(2026, 11, 9)
    clonados = service.clonar_semana(
        fecha_lunes_origen=lunes_origen,
        fecha_lunes_destino=lunes_destino,
        area_id="cocina",
        creador_por=999,
    )

    assert len(clonados) == 2
    # El primer clonado debe ser para el 2026-11-09
    assert clonados[0].fecha_inicio == date(2026, 11, 9)
    assert clonados[0].user_id == 101
    assert clonados[0].nota == "Turno mañana"
    # El segundo debe ser para el miércoles siguiente (2026-11-11)
    assert clonados[1].fecha_inicio == date(2026, 11, 11)
    assert clonados[1].user_id == 102

    # Intentar clonar con fecha que no es lunes debe arrojar DomainValidationError
    with pytest.raises(DomainValidationError):
        service.clonar_semana(
            fecha_lunes_origen=date(2026, 11, 3),  # martes
            fecha_lunes_destino=lunes_destino,
        )


def test_validar_alertas_laborales_descanso_12h() -> None:
    """Verifica detección de descanso insuficiente (<12 horas) entre jornadas consecutivas."""
    service = ActividadesService(use_in_memory=True)

    # Turno 1: Lunes 2026-11-02 de 15:00 a 23:00
    service.create_turno_horario(
        user_id=50,
        fecha_inicio=date(2026, 11, 2),
        hora_inicio=time(15, 0),
        hora_fin=time(23, 0),
    )

    # Nuevo turno entrante: Martes 2026-11-03 a las 07:00 (descanso = 8h < 12h)
    turno_invalido = {
        "fecha_inicio": date(2026, 11, 3),
        "hora_inicio": time(7, 0),
        "hora_fin": time(15, 0),
    }

    auditoria = service.validar_alertas_laborales(usuario_id=50, nuevo_turno=turno_invalido)
    assert auditoria["tiene_alertas"] is True
    tipos_alertas = [a["tipo"] for a in auditoria["alertas"]]
    assert "DESCANSO_INSUFICIENTE" in tipos_alertas

    # Si en cambio entra a las 11:30 (descanso = 12.5h >= 12h), no debe haber alerta de descanso
    turno_valido = {
        "fecha_inicio": date(2026, 11, 3),
        "hora_inicio": time(11, 30),
        "hora_fin": time(19, 30),
    }
    auditoria_valida = service.validar_alertas_laborales(usuario_id=50, nuevo_turno=turno_valido)
    tipos_alertas_val = [a["tipo"] for a in auditoria_valida["alertas"]]
    assert "DESCANSO_INSUFICIENTE" not in tipos_alertas_val


def test_validar_alertas_laborales_exceso_40_horas() -> None:
    """Verifica detección de sobrecarga que supere el límite legal de 40 horas semanales."""
    service = ActividadesService(use_in_memory=True)

    # Registrar 4 jornadas de 9 horas en la misma semana = 36 horas acumuladas
    # Lunes 2026-11-02 a Jueves 2026-11-05
    for dia in range(2, 6):
        service.create_turno_horario(
            user_id=60,
            fecha_inicio=date(2026, 11, dia),
            hora_inicio=time(8, 0),
            hora_fin=time(17, 0),  # 9 horas
        )

    # Nuevo turno de 8 horas para el Viernes 2026-11-06 (36h + 8h = 44h > 40h)
    nuevo_turno = {
        "fecha_inicio": date(2026, 11, 6),
        "hora_inicio": time(8, 0),
        "hora_fin": time(16, 0),
    }

    auditoria = service.validar_alertas_laborales(usuario_id=60, nuevo_turno=nuevo_turno)
    assert auditoria["tiene_alertas"] is True
    assert auditoria["total_horas_semanales"] == Decimal("44.00")
    tipos = [a["tipo"] for a in auditoria["alertas"]]
    assert "EXCESO_40_HORAS" in tipos


# ==============================================================================
# 4. PRUEBAS REST API: FASTAPI ROUTER Y GUARDIAS RBAC DE 3 NIVELES
# ==============================================================================


@pytest.mark.asyncio
async def test_rest_api_notas_equipo_rbac(async_client: httpx.AsyncClient) -> None:
    """Valida endpoints de notas de equipo con control de permisos RBAC."""
    headers_view = _make_auth_headers(["actividades.notas.view"], user_id=101)
    headers_create = _make_auth_headers(
        ["actividades.notas.view", "actividades.notas.create"],
        user_id=101,
    )

    # 1. Intentar crear sin permiso -> 403 Forbidden
    resp_403 = await async_client.post(
        "/api/v1/actividades/notas/equipo",
        headers=headers_view,
        json={
            "titulo": "Prueba Denegada",
            "contenido": "Sin permiso de creación",
        },
    )
    assert resp_403.status_code == 403

    # 2. Crear con permiso -> 201 Created
    resp_201 = await async_client.post(
        "/api/v1/actividades/notas/equipo",
        headers=headers_create,
        json={
            "titulo": "Apertura sin incidentes",
            "contenido": "Turno mañana operando normalmente.",
            "categoria": "general",
            "area_id": "cocina",
            "menciones_user_ids": [102],
        },
    )
    assert resp_201.status_code == 201
    nota_data = resp_201.json()
    assert nota_data["id"] == 1
    assert nota_data["titulo"] == "Apertura sin incidentes"

    # 3. Listar notas -> 200 OK
    resp_get = await async_client.get(
        "/api/v1/actividades/notas/equipo?area_id=cocina",
        headers=headers_view,
    )
    assert resp_get.status_code == 200
    items = resp_get.json()
    assert len(items) == 1

    # 4. Confirmar lectura -> 200 OK
    resp_read = await async_client.post(
        f"/api/v1/actividades/notas/equipo/{nota_data['id']}/read",
        headers=headers_view,
    )
    assert resp_read.status_code == 200
    read_data = resp_read.json()
    assert read_data["nota_id"] == nota_data["id"]


@pytest.mark.asyncio
async def test_rest_api_tareas_rbac_and_incompleta_rule(async_client: httpx.AsyncClient) -> None:
    """Valida creación y transición de tareas con RBAC y regla de 'incompleta'."""
    headers_manage = _make_auth_headers(
        [
            "actividades.tareas.view",
            "actividades.tareas.create",
            "actividades.tareas.update",
        ],
        user_id=200,
    )

    # Crear tarea
    create_resp = await async_client.post(
        "/api/v1/actividades/tareas",
        headers=headers_manage,
        json={
            "titulo": "Limpieza de campana extractora",
            "area_id": "cocina",
            "urgencia": "alta",
        },
    )
    assert create_resp.status_code == 201
    t_id = create_resp.json()["id"]

    # PATCH a 'incompleta' sin motivo -> debe arrojar 400 ProblemDetails
    bad_patch = await async_client.patch(
        f"/api/v1/actividades/tareas/{t_id}/estado",
        headers=headers_manage,
        json={
            "estado": "incompleta",
            "nota_incompleta": "",
        },
    )
    assert bad_patch.status_code == 400
    assert "nota_incompleta" in bad_patch.json().get("detail", "")

    # PATCH a 'incompleta' con motivo -> 200 OK
    good_patch = await async_client.patch(
        f"/api/v1/actividades/tareas/{t_id}/estado",
        headers=headers_manage,
        json={
            "estado": "incompleta",
            "nota_incompleta": "Técnico no asistió a la mantención.",
        },
    )
    assert good_patch.status_code == 200
    assert good_patch.json()["estado"] == "incompleta"
    assert good_patch.json()["nota_incompleta"] == "Técnico no asistió a la mantención."


@pytest.mark.asyncio
async def test_rest_api_horarios_and_validar_alertas(async_client: httpx.AsyncClient) -> None:
    """Valida simulación de alertas laborales y alta de turnos en el enrutador REST."""
    headers = _make_auth_headers(
        [
            "actividades.horarios.view",
            "actividades.horarios.manage",
        ],
        user_id=300,
    )

    # 1. Simular alertas laborales antes de crear
    val_resp = await async_client.post(
        "/api/v1/actividades/horarios/validar-alertas",
        headers=headers,
        json={
            "user_id": 88,
            "fecha_inicio": "2026-11-02",
            "hora_inicio": "08:00:00",
            "hora_fin": "16:00:00",
        },
    )
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["tiene_alertas"] is False

    # 2. Registrar turno
    crear_resp = await async_client.post(
        "/api/v1/actividades/horarios",
        headers=headers,
        json={
            "user_id": 88,
            "area_id": "salon",
            "fecha_inicio": "2026-11-02",
            "hora_inicio": "08:00:00",
            "hora_fin": "16:00:00",
            "color": "#4caf50",
        },
    )
    assert crear_resp.status_code == 201
    assert crear_resp.json()["user_id"] == 88

    # 3. Listar turnos
    list_resp = await async_client.get(
        "/api/v1/actividades/horarios?area_id=salon",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


# ==============================================================================
# 5. PRUEBAS: SINERGIA OPPYFY AI (MINUTA DE TRASPASO DE TURNO)
# ==============================================================================


def test_generar_minuta_traspaso_domain() -> None:
    """Valida la recolección, síntesis ejecutiva y estructuración de 4 puntos clave para OppyFy."""
    service = ActividadesService(use_in_memory=True)
    hoy = date(2026, 11, 2)

    # 1. Crear notas del día (incidente, producción, general)
    service.create_nota_equipo(
        autor_user_id=10,
        titulo="Falla en quemador derecho cocina",
        contenido="Válvula de gas trabada. Se cerró llave de paso preventiva.",
        area_id="cocina",
        categoria="incidente",
        fecha=datetime(2026, 11, 2, 10, 30, tzinfo=UTC),
    )
    service.create_nota_equipo(
        autor_user_id=11,
        titulo="Mise en place de fondos",
        contenido="Quedan 20 litros de caldo de ave en cámara 2.",
        area_id="cocina",
        categoria="produccion",
        insumo_id="INS-CALDO-01",
        fecha=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
    )
    service.create_nota_equipo(
        autor_user_id=12,
        titulo="Reserva corporativa salón",
        contenido="Mesa 10 atendida sin novedades.",
        area_id="salon",
        categoria="servicio",
        fecha=datetime(2026, 11, 2, 14, 0, tzinfo=UTC),
    )

    # 2. Crear tareas (1 completada, 1 incompleta con justificación)
    t1 = service.create_tarea(
        titulo="Sanitización de mesones",
        area_id="cocina",
        fecha_limite=datetime(2026, 11, 2, 16, 0, tzinfo=UTC),
    )
    service.update_tarea_estado(tarea_id=t1.id, estado="completada")

    t2 = service.create_tarea(
        titulo="Descongelar salmón para cena",
        area_id="cocina",
        urgencia="alta",
        asignado_a_user_id=11,
        fecha_limite=datetime(2026, 11, 2, 16, 30, tzinfo=UTC),
    )
    service.update_tarea_estado(
        tarea_id=t2.id,
        estado="incompleta",
        nota_incompleta="Faltó tiempo por sobrecarga en despacho de almuerzos",
    )

    # 3. Crear turno de colaboradores
    service.create_turno_horario(
        user_id=10,
        area_id="cocina",
        fecha_inicio=hoy,
        hora_inicio=time(8, 0),
        hora_fin=time(16, 30),
    )
    service.create_turno_horario(
        user_id=11,
        area_id="cocina",
        fecha_inicio=hoy,
        hora_inicio=time(9, 0),
        hora_fin=time(17, 0),
    )

    # 4. Ejecutar generación de minuta para área 'cocina'
    minuta = service.generar_minuta_traspaso(fecha=hoy, area_id="cocina")

    assert minuta["fecha"] == hoy
    assert minuta["area_id"] == "cocina"
    assert "📋 Minuta Ejecutiva de Traspaso de Turno" in minuta["resumen_ejecutivo"]

    # Validar 4 puntos clave
    puntos = minuta["puntos_clave"]
    assert len(puntos["incidentes"]) == 1
    assert "Falla en quemador" in puntos["incidentes"][0]

    assert len(puntos["produccion"]) == 1
    assert "Mise en place de fondos" in puntos["produccion"][0]

    assert len(puntos["tareas_pendientes"]) == 1
    assert puntos["tareas_pendientes"][0]["titulo"] == "Descongelar salmón para cena"
    assert puntos["tareas_pendientes"][0]["urgencia"] == "alta"
    assert "sobrecarga en despacho" in puntos["tareas_pendientes"][0]["nota_incompleta"]

    assert puntos["dotacion"]["total_colaboradores"] == 2
    assert puntos["dotacion"]["colaboradores_ids"] == [10, 11]

    # Estadísticas cuantitativas
    stats = minuta["estadisticas"]
    assert stats["total_notas"] == 2
    assert stats["total_tareas"] == 2
    assert stats["tareas_completadas"] == 1
    assert stats["tareas_incompletas"] == 1
    assert stats["total_turnos"] == 2


@pytest.mark.asyncio
async def test_rest_api_minuta_traspaso_endpoint(async_client: httpx.AsyncClient) -> None:
    """Valida el endpoint POST /api/v1/actividades/minuta-traspaso con RBAC y respuesta estructurada."""
    headers_forbidden = _make_auth_headers(["inventario.stock.read"], user_id=101)
    headers_ok = _make_auth_headers(["actividades.notas.view"], user_id=101)

    # 1. Sin permiso -> 403 Forbidden
    resp_403 = await async_client.post(
        "/api/v1/actividades/minuta-traspaso",
        headers=headers_forbidden,
        json={"fecha": "2026-11-02", "area_id": "cocina"},
    )
    assert resp_403.status_code == 403

    # 2. Con permiso -> 200 OK
    resp_200 = await async_client.post(
        "/api/v1/actividades/minuta-traspaso",
        headers=headers_ok,
        json={"fecha": "2026-11-02", "area_id": "cocina"},
    )
    assert resp_200.status_code == 200
    data = resp_200.json()
    assert "resumen_ejecutivo" in data
    assert "puntos_clave" in data
    assert "incidentes" in data["puntos_clave"]
    assert "produccion" in data["puntos_clave"]
    assert "tareas_pendientes" in data["puntos_clave"]
    assert "dotacion" in data["puntos_clave"]
    assert "estadisticas" in data

