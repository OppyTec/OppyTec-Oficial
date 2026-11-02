"""
oppytec-backend/src/modules/events/presentation/router.py
Endpoints REST del Módulo de Eventos, Salones y Consumo de Inventario:
- Prefix `/api/v1/events` con tags `["Events", "Salones"]`
- Control de acceso RBAC de 3 niveles con `RequireTenantPermission`
- Respuestas normalizadas RFC 7807 (ProblemDetails para errores 400, 404, 409, 422)
- Integración transaccional con Kardex y eventos realtime vía Redis Pub/Sub
"""
from __future__ import annotations

import io
import logging
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.events.application.services import EventService, SalonService
from src.modules.events.presentation.schemas import (
    CommittedStockSummaryResponse,
    EventAlertOut,
    EventExecutionResultSchema,
    EventFaltantesResponse,
    EventoCancelRequest,
    EventoCreate,
    EventoExportMinutaRequest,
    EventoListItemOut,
    EventoOut,
    EventoReverseRequest,
    EventoReverseResultSchema,
    EventoUpdate,
    SalonCreate,
    SalonOut,
    SalonUpdate,
)

router = APIRouter(prefix="/api/v1/events", tags=["Events", "Salones"])
logger = logging.getLogger("oppytec.events.router")

# Instancias compartidas perezosas de los servicios de aplicación
_salon_service: SalonService | None = None
_event_service: EventService | None = None


def get_salon_service() -> SalonService:
    """Provee la instancia del servicio de salones."""
    global _salon_service
    if _salon_service is None:
        _salon_service = SalonService()
    return _salon_service


def get_event_service() -> EventService:
    """Provee la instancia del servicio de eventos con integración a inventario."""
    global _event_service
    if _event_service is None:
        from src.modules.inventory.presentation.router import _inventory_service
        _event_service = EventService(
            inventory=_inventory_service,
            salon_service=get_salon_service(),
        )
    return _event_service


# ============================================================================
# SALONES ENDPOINTS
# ============================================================================


@router.get(
    "/salones",
    response_model=list[SalonOut],
    status_code=status.HTTP_200_OK,
    summary="Listar salones físicos",
    description="Obtiene los salones y espacios de eventos del inquilino, filtrables por área operativa.",
)
async def list_salones_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.salones.read")),
    ],
    area_operativa_id: int | None = Query(None, description="Filtrar por área operativa vinculada"),
    salon_service: SalonService = Depends(get_salon_service),
) -> list[SalonOut]:
    """Lista todos los salones activos del tenant."""
    return salon_service.list_salones(
        tenant_id=principal.tenant_id,
        area_operativa_id=area_operativa_id,
    )


@router.post(
    "/salones",
    response_model=SalonOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo salón",
    description="Da de alta un nuevo espacio físico con cálculo automático de precio bruto con IVA.",
)
async def create_salon_endpoint(
    payload: SalonCreate,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.salones.manage")),
    ],
    salon_service: SalonService = Depends(get_salon_service),
) -> SalonOut:
    """Registra un nuevo salón."""
    return salon_service.create_salon(
        tenant_id=principal.tenant_id,
        data=payload,
    )


@router.get(
    "/salones/{salon_id}",
    response_model=SalonOut,
    status_code=status.HTTP_200_OK,
    summary="Detalle de un salón",
    description="Devuelve la información de un salón por su identificador UUID.",
)
async def get_salon_endpoint(
    salon_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.salones.read")),
    ],
    salon_service: SalonService = Depends(get_salon_service),
) -> SalonOut:
    """Obtiene el detalle de un salón específico."""
    return salon_service.get_salon_by_id(
        tenant_id=principal.tenant_id,
        salon_id=salon_id,
    )


@router.put(
    "/salones/{salon_id}",
    response_model=SalonOut,
    status_code=status.HTTP_200_OK,
    summary="Actualizar salón",
    description="Actualiza las propiedades de un salón y recalcula aranceles con IVA.",
)
async def update_salon_endpoint(
    salon_id: UUID,
    payload: SalonUpdate,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.salones.manage")),
    ],
    salon_service: SalonService = Depends(get_salon_service),
) -> SalonOut:
    """Actualiza datos de un salón existente."""
    return salon_service.update_salon(
        tenant_id=principal.tenant_id,
        salon_id=salon_id,
        data=payload,
    )


@router.delete(
    "/salones/{salon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar salón",
    description="Elimina un salón si no cuenta con eventos agendados activos.",
)
async def delete_salon_endpoint(
    salon_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.salones.manage")),
    ],
    salon_service: SalonService = Depends(get_salon_service),
) -> Response:
    """Elimina de forma segura un salón."""
    salon_service.delete_salon(
        tenant_id=principal.tenant_id,
        salon_id=salon_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# EVENTOS ENDPOINTS
# ============================================================================


@router.get(
    "",
    response_model=list[EventoListItemOut],
    status_code=status.HTTP_200_OK,
    summary="Listar eventos y banquetes",
    description="Lista los eventos registrados con filtros por estado, fechas y salón.",
)
async def list_events_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    estado: str | None = Query(
        None,
        description="Filtro de estado: PROXIMOS, FINALIZADOS, CANCELADOS o estado exacto",
    ),
    fecha_desde: date | None = Query(None, description="Fecha mínima"),
    fecha_hasta: date | None = Query(None, description="Fecha máxima"),
    salon_id: UUID | None = Query(None, description="Filtrar por salón"),
    area_operativa_id: int | None = Query(None, description="Filtrar por área operativa"),
    event_service: EventService = Depends(get_event_service),
) -> list[EventoListItemOut]:
    """Lista eventos del tenant."""
    return event_service.list_events(
        tenant_id=principal.tenant_id,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        salon_id=salon_id,
        area_operativa_id=area_operativa_id,
    )


@router.post(
    "",
    response_model=EventoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo evento",
    description="Agenda un evento con validación estricta de anti-overbooking y asignación de insumos y personal.",
)
async def create_event_endpoint(
    payload: EventoCreate,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.create")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> EventoOut:
    """Crea y agenda un nuevo evento."""
    return event_service.create_event(
        tenant_id=principal.tenant_id,
        data=payload,
        current_user_id=principal.user_id,
    )


@router.get(
    "/faltantes",
    response_model=EventFaltantesResponse,
    status_code=status.HTTP_200_OK,
    summary="Analítica predictiva de quiebre de stock",
    description="Compara la demanda consolidada de eventos futuros agendados vs existencias reales en bodegas.",
)
@router.get(
    "/analytics/faltantes",
    response_model=EventFaltantesResponse,
    status_code=status.HTTP_200_OK,
    summary="Analítica predictiva de quiebre de stock (alias)",
    description="Compara la demanda consolidada de eventos futuros agendados vs existencias reales en bodegas.",
)
async def get_event_faltantes_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    area_operativa_id: int | None = Query(None, description="Filtrar por área operativa"),
    event_service: EventService = Depends(get_event_service),
) -> EventFaltantesResponse:
    """Devuelve el reporte consolidado de faltantes de stock."""
    return event_service.get_faltantes_analytics(
        tenant_id=principal.tenant_id,
        area_operativa_id=area_operativa_id,
    )


@router.get(
    "/analytics/committed-stock",
    response_model=CommittedStockSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Resumen de existencias y stock comprometido",
    description=(
        "Calcula la demanda futura reservada por insumo y bodega para eventos agendados futuros, "
        "y determina el saldo libre disponible real: max(0, stock_actual - stock_comprometido)."
    ),
)
async def get_committed_stock_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    bodega_id: int | None = Query(None, description="Filtrar por bodega específica"),
    event_service: EventService = Depends(get_event_service),
) -> CommittedStockSummaryResponse:
    """Retorna el desglose de stock comprometido y saldo disponible real."""
    return event_service.get_committed_stock_summary(
        tenant_id=principal.tenant_id,
        bodega_id=bodega_id,
    )


@router.get(
    "/alerts",
    response_model=list[EventAlertOut],
    status_code=status.HTTP_200_OK,
    summary="Listar alertas operativas de eventos con déficit de stock",
    description=(
        "Retorna alertas de eventos clasificadas por severidad (CRITICAL < 48h con déficit, "
        "WARNING <= 14 días con quiebre proyectado) enriquecidas con insumos faltantes."
    ),
)
async def get_event_alerts_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> list[EventAlertOut]:
    """Retorna la lista de alertas de eventos con riesgo de desabastecimiento."""
    return event_service.get_event_alerts(
        tenant_id=principal.tenant_id,
    )


@router.post(
    "/export/minuta-excel",
    status_code=status.HTTP_200_OK,
    summary="Exportar minutas de producción y requisición",
    description="Genera un archivo CSV/Excel estructurado con las minutas de los eventos indicados o todos los programados.",
)
async def export_minutas_excel_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    payload: EventoExportMinutaRequest | None = None,
    event_service: EventService = Depends(get_event_service),
) -> StreamingResponse:
    """Exporta las minutas de producción y requisición de eventos en formato compatible con Excel."""
    event_ids = payload.event_ids if payload and payload.event_ids else None
    if payload and payload.event_id:
        event_ids = [payload.event_id]

    csv_content = event_service.generate_minutas_consolidated_csv(
        tenant_id=principal.tenant_id,
        event_ids=event_ids,
    )
    today_str = date.today().strftime("%Y%m%d")
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="minuta_produccion_eventos_{today_str}.csv"',
        },
    )


@router.get(
    "/{event_id}",
    response_model=EventoOut,
    status_code=status.HTTP_200_OK,
    summary="Detalle completo de evento",
    description="Obtiene toda la información del evento, incluyendo insumos, recetas, combos y brigada.",
)
async def get_event_endpoint(
    event_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> EventoOut:
    """Detalle completo del agregado raíz de evento."""
    return event_service.get_event_by_id(
        tenant_id=principal.tenant_id,
        event_id=event_id,
    )


@router.put(
    "/{event_id}",
    response_model=EventoOut,
    status_code=status.HTTP_200_OK,
    summary="Editar evento agendado",
    description="Modifica atributos y asignaciones de un evento que no ha sido ejecutado ni cancelado.",
)
async def update_event_endpoint(
    event_id: UUID,
    payload: EventoUpdate,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.edit")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> EventoOut:
    """Actualiza un evento existente."""
    return event_service.update_event(
        tenant_id=principal.tenant_id,
        event_id=event_id,
        data=payload,
        current_user_id=principal.user_id,
    )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar evento",
    description="Elimina un evento si no ha sido ejecutado en Kardex.",
)
async def delete_event_endpoint(
    event_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.delete")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> Response:
    """Elimina un evento agendado."""
    event_service.delete_event(
        tenant_id=principal.tenant_id,
        event_id=event_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{event_id}/execute",
    response_model=EventExecutionResultSchema,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar evento en Kardex",
    description="Rebaja atómicamente el inventario de insumos directos, recetas y combos, asentando la auditoría.",
)
async def execute_event_endpoint(
    event_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.execute")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> EventExecutionResultSchema:
    """Ejecuta el consumo de inventario del evento en Kardex."""
    return event_service.execute_event(
        tenant_id=principal.tenant_id,
        event_id=event_id,
        current_user_id=principal.user_id,
    )


@router.post(
    "/{event_id}/cancel",
    response_model=EventoOut,
    status_code=status.HTTP_200_OK,
    summary="Cancelar evento agendado",
    description="Marca el evento como cancelado liberando el espacio reservado del salón.",
)
async def cancel_event_endpoint(
    event_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.cancel")),
    ],
    payload: EventoCancelRequest | None = None,
    event_service: EventService = Depends(get_event_service),
) -> EventoOut:
    """Cancela un evento agendado."""
    motivo = payload.motivo if payload else None
    return event_service.cancel_event(
        tenant_id=principal.tenant_id,
        event_id=event_id,
        motivo=motivo,
        current_user_id=principal.user_id,
    )


@router.post(
    "/{event_id}/reactivate",
    response_model=EventoOut,
    status_code=status.HTTP_200_OK,
    summary="Reactivar evento cancelado",
    description="Reactiva un evento cancelado si su salón y franja horaria continúan disponibles.",
)
async def reactivate_event_endpoint(
    event_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.edit")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> EventoOut:
    """Reactiva un evento previamente cancelado."""
    return event_service.reactivate_event(
        tenant_id=principal.tenant_id,
        event_id=event_id,
        current_user_id=principal.user_id,
    )


@router.post(
    "/{event_id}/reverse",
    response_model=EventoReverseResultSchema,
    status_code=status.HTTP_200_OK,
    summary="Reversión compensatoria de evento ejecutado",
    description="Anula un evento ya ejecutado generando asientos compensatorios inmutables en Kardex para reingresar el stock.",
)
async def reverse_event_endpoint(
    event_id: UUID,
    payload: EventoReverseRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.cancel")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> EventoReverseResultSchema:
    """Revierte transaccionalmente un evento ejecutado reingresando existencias a Kardex."""
    return event_service.reverse_event(
        tenant_id=principal.tenant_id,
        event_id=event_id,
        motivo=payload.motivo,
        current_user_id=principal.user_id,
    )


@router.get(
    "/{event_id}/minuta",
    status_code=status.HTTP_200_OK,
    summary="Descargar minuta de producción técnica",
    description="Genera y descarga la minuta técnica de producción, recetas y requisición de bodegas en formato CSV/Excel.",
)
async def get_event_minuta_endpoint(
    event_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("events.events.read")),
    ],
    event_service: EventService = Depends(get_event_service),
) -> StreamingResponse:
    """Descarga la minuta técnica de producción y requisición del evento."""
    csv_content = event_service.generate_minuta_csv(
        tenant_id=principal.tenant_id,
        event_id=event_id,
    )
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="minuta_evento_{event_id}.csv"',
        },
    )


__all__ = [
    "get_event_service",
    "get_salon_service",
    "router",
]
