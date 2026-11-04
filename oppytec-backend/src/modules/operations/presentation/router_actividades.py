"""
oppytec-backend/src/modules/operations/presentation/router_actividades.py
Enrutador REST FastAPI para el Panel de Actividades de OppyTec v2.0:
- Notas de Equipo y Personales (con menciones y confirmación de lectura idempotente).
- Tareas Operativas, Checklists y Plantillas de Rutinas de Apertura/Cierre.
- Horarios, Grilla Semanal de Turnos, Clonación y Auditoría Laboral (Ley 40 Horas / Descanso 12h).

Guardias RBAC de 3 Niveles:
- `actividades.notas.view` / `create` / `delete`
- `actividades.tareas.view` / `create` / `update`
- `actividades.horarios.view` / `manage`
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.operations.application.actividades_service import ActividadesService
from src.modules.operations.infrastructure.models import (
    NotaEquipoLectura,
    NotaPersonal,
    PlantillaRutina,
    Tarea,
    TurnoHorario,
)
from src.modules.operations.presentation.schemas_actividades import (
    AlertaLaboralItem,
    AplicarPlantillaRequest,
    ClonarSemanaRequest,
    NotaEquipoCreateRequest,
    NotaEquipoResponse,
    NotaEquipoUpdateRequest,
    NotaLecturaResponse,
    NotaMencionResponse,
    NotaPersonalCreateRequest,
    NotaPersonalResponse,
    NotaPersonalUpdateRequest,
    PlantillaRutinaCreateRequest,
    PlantillaRutinaResponse,
    TareaCreateRequest,
    TareaEstadoUpdateRequest,
    TareaResponse,
    TareaUpdateRequest,
    TurnoHorarioCreateRequest,
    TurnoHorarioResponse,
    TurnoHorarioUpdateRequest,
    ValidacionLaboralResponse,
    ValidarTurnoAlertaRequest,
    MinutaTraspasoRequest,
    MinutaTraspasoResponse,
)

router = APIRouter(prefix="/api/v1/actividades", tags=["operations-actividades"])

# Instancia singleton del servicio de actividades
_actividades_service = ActividadesService(use_in_memory=True)


def get_actividades_service() -> ActividadesService:
    """Proveedor inyectable del servicio de actividades."""
    return _actividades_service


def _to_nota_equipo_response(data: dict[str, Any]) -> NotaEquipoResponse:
    """Transforma el diccionario enriquecido en un schema Pydantic de respuesta."""
    raw_m = data.get("menciones", [])
    menciones = [
        m if isinstance(m, NotaMencionResponse) else NotaMencionResponse(**m)
        for m in raw_m
    ]
    raw_l = data.get("lecturas", [])
    lecturas = [
        l if isinstance(l, NotaLecturaResponse) else NotaLecturaResponse(**l)
        for l in raw_l
    ]
    return NotaEquipoResponse(
        id=data["id"],
        autor_user_id=data["autor_user_id"],
        titulo=data["titulo"],
        contenido=data["contenido"],
        area_id=data.get("area_id"),
        categoria=data.get("categoria", "general"),
        fecha=data.get("fecha"),
        insumo_id=data.get("insumo_id"),
        receta_id=data.get("receta_id"),
        foto_url=data.get("foto_url"),
        menciones=menciones,
        lecturas=lecturas,
        leido_por_mi=data.get("leido_por_mi", False),
        total_lecturas=data.get("total_lecturas", 0),
        created_at=data.get("created_at"),
    )


# ==============================================================================
# ENDPOINTS: NOTAS DE EQUIPO (BITÁCORA COMPARTIDA)
# ==============================================================================


@router.post(
    "/notas/equipo",
    response_model=NotaEquipoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_nota_equipo_endpoint(
    payload: NotaEquipoCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.create", fallback_permission="operations.notas.create")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> NotaEquipoResponse:
    """Crea una nueva nota de equipo en la bitácora del turno con menciones opcionales."""
    nota = service.create_nota_equipo(
        autor_user_id=principal.user_id,
        titulo=payload.titulo,
        contenido=payload.contenido,
        area_id=payload.area_id,
        categoria=payload.categoria,
        fecha=payload.fecha,
        insumo_id=payload.insumo_id,
        receta_id=payload.receta_id,
        foto_url=payload.foto_url,
        menciones_user_ids=payload.menciones_user_ids,
        tenant_id=principal.tenant_id,
    )
    items = service.get_notas_equipo(
        tenant_id=principal.tenant_id,
        current_user_id=principal.user_id,
        skip=0,
        limit=1,
    )
    for item in items:
        if item["id"] == nota.id:
            return _to_nota_equipo_response(item)
    return NotaEquipoResponse(
        id=nota.id,
        autor_user_id=nota.autor_user_id,
        titulo=nota.titulo,
        contenido=nota.contenido,
        area_id=nota.area_id,
        categoria=nota.categoria,
        fecha=nota.fecha,
        insumo_id=nota.insumo_id,
        receta_id=nota.receta_id,
        foto_url=nota.foto_url,
        menciones=[NotaMencionResponse(id=m.id, nota_id=m.nota_id, user_id=m.user_id) for m in nota.menciones],
        lecturas=[],
        leido_por_mi=False,
        total_lecturas=0,
        created_at=nota.created_at,
    )


@router.get(
    "/notas/equipo",
    response_model=list[NotaEquipoResponse],
    status_code=status.HTTP_200_OK,
)
async def list_notas_equipo_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.view", fallback_permission="operations.notas.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
    area_id: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    search: str | None = Query(default=None),
    user_id_mencionado: int | None = Query(default=None),
    leido_por_user_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotaEquipoResponse]:
    """Lista las notas de equipo filtradas por área, categoría, mención y lectura."""
    raw_list = service.get_notas_equipo(
        tenant_id=principal.tenant_id,
        area_id=area_id,
        categoria=categoria,
        search=search,
        user_id_mencionado=user_id_mencionado,
        leido_por_user_id=leido_por_user_id,
        current_user_id=principal.user_id,
        skip=skip,
        limit=limit,
    )
    return [_to_nota_equipo_response(d) for d in raw_list]


@router.post(
    "/notas/equipo/{nota_id}/read",
    response_model=NotaLecturaResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_nota_as_read_endpoint(
    nota_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.view", fallback_permission="operations.notas.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> NotaEquipoLectura:
    """Marca de forma idempotente la confirmación de lectura de una nota."""
    return service.mark_nota_as_read(
        nota_id=nota_id,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )


@router.put(
    "/notas/equipo/{nota_id}",
    response_model=NotaEquipoResponse,
    status_code=status.HTTP_200_OK,
)
async def update_nota_equipo_endpoint(
    nota_id: int,
    payload: NotaEquipoUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.create", fallback_permission="operations.notas.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> NotaEquipoResponse:
    """Modifica el contenido o menciones de una nota de equipo."""
    nota = service.update_nota_equipo(
        nota_id=nota_id,
        user_id=principal.user_id,
        titulo=payload.titulo,
        contenido=payload.contenido,
        area_id=payload.area_id,
        categoria=payload.categoria,
        insumo_id=payload.insumo_id,
        receta_id=payload.receta_id,
        foto_url=payload.foto_url,
        menciones_user_ids=payload.menciones_user_ids,
        tenant_id=principal.tenant_id,
    )
    items = service.get_notas_equipo(
        tenant_id=principal.tenant_id,
        current_user_id=principal.user_id,
    )
    for item in items:
        if item["id"] == nota.id:
            return _to_nota_equipo_response(item)
    return _to_nota_equipo_response({
        "id": nota.id,
        "autor_user_id": nota.autor_user_id,
        "titulo": nota.titulo,
        "contenido": nota.contenido,
        "area_id": nota.area_id,
        "categoria": nota.categoria,
        "fecha": nota.fecha,
        "insumo_id": nota.insumo_id,
        "receta_id": nota.receta_id,
        "foto_url": nota.foto_url,
        "menciones": [{"id": m.id, "nota_id": m.nota_id, "user_id": m.user_id} for m in nota.menciones],
        "lecturas": [{"id": l.id, "nota_id": l.nota_id, "user_id": l.user_id, "read_at": l.read_at} for l in nota.lecturas],
        "leido_por_mi": any(l.user_id == principal.user_id for l in nota.lecturas),
        "total_lecturas": len(nota.lecturas),
        "created_at": nota.created_at,
    })


@router.delete(
    "/notas/equipo/{nota_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_nota_equipo_endpoint(
    nota_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.delete", fallback_permission="operations.notas.delete")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> dict[str, Any]:
    """Elimina lógicamente una nota de equipo."""
    success = service.delete_nota_equipo(
        nota_id=nota_id,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )
    return {"success": success, "nota_id": nota_id}


# ==============================================================================
# ENDPOINTS: NOTAS PERSONALES
# ==============================================================================


@router.post(
    "/notas/personales",
    response_model=NotaPersonalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_nota_personal_endpoint(
    payload: NotaPersonalCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.create", fallback_permission="operations.notas.create")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> NotaPersonal:
    """Crea una nota privada individual para el usuario autenticado."""
    return service.create_nota_personal(
        user_id=principal.user_id,
        titulo=payload.titulo,
        contenido=payload.contenido,
        area_id=payload.area_id,
        fecha=payload.fecha,
        tenant_id=principal.tenant_id,
    )


@router.get(
    "/notas/personales",
    response_model=list[NotaPersonalResponse],
    status_code=status.HTTP_200_OK,
)
async def list_notas_personales_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.view", fallback_permission="operations.notas.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
    area_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotaPersonal]:
    """Lista exclusivamente las notas personales del usuario autenticado."""
    return service.get_notas_personales(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        area_id=area_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.put(
    "/notas/personales/{nota_id}",
    response_model=NotaPersonalResponse,
    status_code=status.HTTP_200_OK,
)
async def update_nota_personal_endpoint(
    nota_id: int,
    payload: NotaPersonalUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.create", fallback_permission="operations.notas.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> NotaPersonal:
    """Actualiza una nota personal privada del usuario."""
    return service.update_nota_personal(
        nota_id=nota_id,
        user_id=principal.user_id,
        titulo=payload.titulo,
        contenido=payload.contenido,
        area_id=payload.area_id,
        fecha=payload.fecha,
        tenant_id=principal.tenant_id,
    )


@router.delete(
    "/notas/personales/{nota_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_nota_personal_endpoint(
    nota_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.delete", fallback_permission="operations.notas.delete")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> dict[str, Any]:
    """Elimina una nota personal del usuario."""
    success = service.delete_nota_personal(
        nota_id=nota_id,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )
    return {"success": success, "nota_id": nota_id}


# ==============================================================================
# ENDPOINTS: TAREAS OPERATIVAS Y CHECKLISTS
# ==============================================================================


@router.post(
    "/tareas",
    response_model=TareaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tarea_endpoint(
    payload: TareaCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.create", fallback_permission="operations.tareas.create")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> Tarea:
    """Crea una nueva tarea operativa individual."""
    return service.create_tarea(
        titulo=payload.titulo,
        creador_user_id=principal.user_id,
        asignado_a_user_id=payload.asignado_a_user_id,
        area_id=payload.area_id,
        descripcion=payload.descripcion,
        estado=payload.estado,
        urgencia=payload.urgencia,
        fecha_limite=payload.fecha_limite,
        nota_incompleta=payload.nota_incompleta,
        compra_id=payload.compra_id,
        foto_evidencia_url=payload.foto_evidencia_url,
        plantilla_id=payload.plantilla_id,
        completada=payload.completada,
        tenant_id=principal.tenant_id,
    )


@router.get(
    "/tareas",
    response_model=list[TareaResponse],
    status_code=status.HTTP_200_OK,
)
async def list_tareas_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.view", fallback_permission="operations.tareas.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
    area_id: str | None = Query(default=None),
    asignado_a_user_id: int | None = Query(default=None),
    estado: str | None = Query(default=None),
    urgencia: str | None = Query(default=None),
    search: str | None = Query(default=None),
    plantilla_id: int | None = Query(default=None),
    completada: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Tarea]:
    """Lista tareas operativas con filtros por estado, área, responsable y urgencia."""
    return service.get_tareas(
        tenant_id=principal.tenant_id,
        area_id=area_id,
        asignado_a_user_id=asignado_a_user_id,
        estado=estado,
        urgencia=urgencia,
        search=search,
        plantilla_id=plantilla_id,
        completada=completada,
        skip=skip,
        limit=limit,
    )


@router.put(
    "/tareas/{tarea_id}",
    response_model=TareaResponse,
    status_code=status.HTTP_200_OK,
)
async def update_tarea_endpoint(
    tarea_id: int,
    payload: TareaUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.update", fallback_permission="operations.tareas.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> Tarea:
    """Actualiza campos de una tarea operativa."""
    return service.update_tarea(
        tarea_id=tarea_id,
        titulo=payload.titulo,
        descripcion=payload.descripcion,
        asignado_a_user_id=payload.asignado_a_user_id,
        area_id=payload.area_id,
        estado=payload.estado,
        urgencia=payload.urgencia,
        fecha_limite=payload.fecha_limite,
        nota_incompleta=payload.nota_incompleta,
        compra_id=payload.compra_id,
        foto_evidencia_url=payload.foto_evidencia_url,
        completada=payload.completada,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )


@router.patch(
    "/tareas/{tarea_id}/estado",
    response_model=TareaResponse,
    status_code=status.HTTP_200_OK,
)
async def update_tarea_estado_endpoint(
    tarea_id: int,
    payload: TareaEstadoUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.update", fallback_permission="operations.tareas.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> Tarea:
    """
    Transición de estado de tarea.
    VALIDACIÓN OBLIGATORIA: Si pasa a 'incompleta', 'nota_incompleta' es requerida.
    """
    return service.update_tarea_estado(
        tarea_id=tarea_id,
        estado=payload.estado,
        nota_incompleta=payload.nota_incompleta,
        foto_evidencia_url=payload.foto_evidencia_url,
        completada=payload.completada,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )


@router.delete(
    "/tareas/{tarea_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_tarea_endpoint(
    tarea_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.update", fallback_permission="operations.tareas.delete")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> dict[str, Any]:
    """Elimina lógicamente una tarea operativa."""
    success = service.delete_tarea(
        tarea_id=tarea_id,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )
    return {"success": success, "tarea_id": tarea_id}


# ==============================================================================
# ENDPOINTS: PLANTILLAS DE RUTINAS
# ==============================================================================


@router.post(
    "/rutinas/plantillas",
    response_model=PlantillaRutinaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_plantilla_rutina_endpoint(
    payload: PlantillaRutinaCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.create", fallback_permission="operations.rutinas.create")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> PlantillaRutina:
    """Crea una plantilla reutilizable de checklist (apertura/cierre/limpieza)."""
    return service.create_plantilla_rutina(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        area_id=payload.area_id,
        tipo_rutina=payload.tipo_rutina,
        frecuencia=payload.frecuencia,
        items_json=payload.items_json,
        is_active=payload.is_active,
        usuario_creador_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )


@router.get(
    "/rutinas/plantillas",
    response_model=list[PlantillaRutinaResponse],
    status_code=status.HTTP_200_OK,
)
async def list_plantillas_rutinas_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.view", fallback_permission="operations.rutinas.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
    area_id: str | None = Query(default=None),
    tipo_rutina: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> list[PlantillaRutina]:
    """Lista las plantillas de rutinas disponibles."""
    return service.get_plantillas_rutinas(
        tenant_id=principal.tenant_id,
        area_id=area_id,
        tipo_rutina=tipo_rutina,
        is_active=is_active,
    )


@router.post(
    "/rutinas/plantillas/{plantilla_id}/aplicar",
    response_model=list[TareaResponse],
    status_code=status.HTTP_201_CREATED,
)
async def aplicar_plantilla_rutina_endpoint(
    plantilla_id: int,
    payload: AplicarPlantillaRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.tareas.create", fallback_permission="operations.rutinas.create")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> list[Tarea]:
    """Genera automáticamente las tareas del turno basadas en los items de la plantilla."""
    return service.aplicar_plantilla_rutina(
        plantilla_id=plantilla_id,
        asignado_a_user_id=payload.asignado_a_user_id,
        creador_user_id=principal.user_id,
        fecha_limite=payload.fecha_limite,
        area_id=payload.area_id,
        tenant_id=principal.tenant_id,
    )


# ==============================================================================
# ENDPOINTS: HORARIOS, TURNOS, ALERTAS LABORALES Y CLONACIÓN
# ==============================================================================


@router.post(
    "/horarios",
    response_model=TurnoHorarioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_turno_horario_endpoint(
    payload: TurnoHorarioCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.horarios.manage", fallback_permission="operations.horarios.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> TurnoHorario:
    """Crea un turno horario para un colaborador."""
    return service.create_turno_horario(
        user_id=payload.user_id,
        usuario_id=payload.usuario_id,
        area_id=payload.area_id,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        hora_inicio=payload.hora_inicio,
        hora_fin=payload.hora_fin,
        inicio_turno=payload.inicio_turno,
        fin_turno=payload.fin_turno,
        nota=payload.nota,
        color=payload.color,
        creado_por=principal.user_id,
        tenant_id=principal.tenant_id,
    )


@router.get(
    "/horarios",
    response_model=list[TurnoHorarioResponse],
    status_code=status.HTTP_200_OK,
)
async def list_turnos_horarios_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.horarios.view", fallback_permission="operations.horarios.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    area_id: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[TurnoHorario]:
    """Lista la grilla de turnos horarios en un rango de fechas."""
    return service.get_turnos_horarios(
        tenant_id=principal.tenant_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        area_id=area_id,
        usuario_id=usuario_id,
        skip=skip,
        limit=limit,
    )


@router.put(
    "/horarios/{turno_id}",
    response_model=TurnoHorarioResponse,
    status_code=status.HTTP_200_OK,
)
async def update_turno_horario_endpoint(
    turno_id: int,
    payload: TurnoHorarioUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.horarios.manage", fallback_permission="operations.horarios.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> TurnoHorario:
    """Modifica un turno horario existente."""
    return service.update_turno_horario(
        turno_id=turno_id,
        user_id=payload.user_id,
        area_id=payload.area_id,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        hora_inicio=payload.hora_inicio,
        hora_fin=payload.hora_fin,
        inicio_turno=payload.inicio_turno,
        fin_turno=payload.fin_turno,
        nota=payload.nota,
        color=payload.color,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
    )


@router.delete(
    "/horarios/{turno_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_turno_horario_endpoint(
    turno_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.horarios.manage", fallback_permission="operations.horarios.delete")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> dict[str, Any]:
    """Elimina lógicamente un turno horario."""
    success = service.delete_turno_horario(
        turno_id=turno_id,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
    )
    return {"success": success, "turno_id": turno_id}


@router.post(
    "/horarios/clonar-semana",
    response_model=list[TurnoHorarioResponse],
    status_code=status.HTTP_201_CREATED,
)
async def clonar_semana_endpoint(
    payload: ClonarSemanaRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.horarios.manage", fallback_permission="operations.horarios.write")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> list[TurnoHorario]:
    """Clona en bloque la grilla semanal completa de turnos de un lunes a otro."""
    return service.clonar_semana(
        fecha_lunes_origen=payload.fecha_lunes_origen,
        fecha_lunes_destino=payload.fecha_lunes_destino,
        area_id=payload.area_id,
        creador_por=principal.user_id,
        tenant_id=principal.tenant_id,
    )


@router.post(
    "/horarios/validar-alertas",
    response_model=ValidacionLaboralResponse,
    status_code=status.HTTP_200_OK,
)
async def validar_alertas_laborales_endpoint(
    payload: ValidarTurnoAlertaRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.horarios.view", fallback_permission="operations.horarios.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
) -> ValidacionLaboralResponse:
    """Evalúa descansos de 12h y tope legal de 40 horas semanales antes de confirmar un turno."""
    res = service.validar_alertas_laborales(
        usuario_id=payload.user_id,
        nuevo_turno=payload.model_dump(),
        tenant_id=principal.tenant_id,
        turno_id_excluir=payload.turno_id_excluir,
    )
    return ValidacionLaboralResponse(
        tiene_alertas=res["tiene_alertas"],
        total_horas_semanales=res["total_horas_semanales"],
        alertas=[
            AlertaLaboralItem(
                tipo=a["tipo"],
                mensaje=a["mensaje"],
                severidad=a.get("severidad", "advertencia"),
                detalle=a.get("detalle", {}),
            )
            for a in res["alertas"]
        ],
    )


# ==============================================================================
# 5. SINERGIA OPPYFY AI: MINUTA DE TRASPASO DE TURNO
# ==============================================================================


@router.post(
    "/minuta-traspaso",
    response_model=MinutaTraspasoResponse,
    status_code=status.HTTP_200_OK,
)
async def generar_minuta_traspaso_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("actividades.notas.view", fallback_permission="operations.notas.read")),
    ],
    service: Annotated[ActividadesService, Depends(get_actividades_service)],
    payload: MinutaTraspasoRequest = MinutaTraspasoRequest(),
) -> MinutaTraspasoResponse:
    """
    Genera la minuta ejecutiva consolidada de traspaso de turno impulsada por OppyFy AI.
    Sintetiza incidentes, avances de producción/stock, tareas pendientes con justificación y dotación.
    """
    result = service.generar_minuta_traspaso(
        fecha=payload.fecha,
        area_id=payload.area_id,
        tenant_id=principal.tenant_id,
    )
    return MinutaTraspasoResponse(**result)


