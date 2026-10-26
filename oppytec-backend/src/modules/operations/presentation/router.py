"""
oppytec-backend/src/modules/operations/presentation/router.py
Endpoints REST del Módulo de Operaciones, Consumo, Manos Libres y Buffet Inteligente:
- Consumo Directo:
  * `POST /api/v1/operations/consumption`
  * `GET /api/v1/operations/consumption/history`
  * `GET /api/v1/operations/consumption/{id}`
  * `PUT /api/v1/operations/consumption/{id}`
  * `DELETE /api/v1/operations/consumption/{id}`
  * `POST /api/v1/operations/consumption/merma-expired`
  * `GET /api/v1/operations/consumption/templates`
  * `POST /api/v1/operations/consumption/templates`
- Buffet Inteligente:
  * `POST /api/v1/operations/buffet/sessions/start`
  * `GET /api/v1/operations/buffet/sessions`
  * `GET /api/v1/operations/buffet/sessions/{id}`
  * `PUT /api/v1/operations/buffet/sessions/{id}/items`
  * `POST /api/v1/operations/buffet/sessions/{id}/finalize`
  * `GET /api/v1/operations/buffet/templates`
  * `POST /api/v1/operations/buffet/templates`
- Cocina por Voz / Manos Libres:
  * `GET /api/v1/operations/voice/stations`
  * `POST /api/v1/operations/voice/stations`
  * `POST /api/v1/operations/voice/orders`
  * `POST /api/v1/operations/voice/orders/{id}/confirm`
  * `POST /api/v1/operations/voice/orders/{id}/reject`
- Legacy / POS & Eventos:
  * `POST /api/v1/operations/sales`
  * `POST /api/v1/operations/buffet`
  * `POST /api/v1/operations/events`
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
from src.modules.inventory.presentation.router import _inventory_service
from src.modules.operations.application.buffet_service import BuffetService, BuffetSessionDTO
from src.modules.operations.application.consumption_service import (
    ConsumptionRecordDTO,
    ConsumptionRecordItemDTO,
    ConsumptionService,
    ConsumptionTemplateDTO,
)
from src.modules.operations.application.operations_service import OperationsService
from src.modules.operations.application.voice_kitchen_service import VoiceKitchenService
from src.modules.operations.domain.pos_consumption import (
    SaleItem,
    buffet_cost_per_pax,
    explode_sale_consumption,
)
from src.modules.operations.presentation.schemas import (
    BuffetCostRequest,
    BuffetCostResponse,
    BuffetFinalizeRequest,
    BuffetItemsUpdateRequest,
    BuffetSessionItemResponse,
    BuffetSessionResponse,
    BuffetSessionStartRequest,
    BuffetStationResponse,
    BuffetTemplateCreateRequest,
    BuffetTemplateResponse,
    CateringEventRequest,
    CateringEventResponse,
    ConsumptionHistoryResponse,
    ConsumptionRecordItemResponse,
    ConsumptionRecordResponse,
    ConsumptionRegisterRequest,
    ConsumptionTemplateCreateRequest,
    ConsumptionTemplateResponse,
    ConsumptionUpdateRequest,
    MermaExpiredStockRequest,
    MermaExpiredStockResponse,
    PosSaleProcessRequest,
    PosSaleProcessResponse,
    VoiceOrderConfirmRequest,
    VoiceOrderRegisterRequest,
    VoiceOrderResponse,
    VoiceStationCreateRequest,
    VoiceStationResponse,
)

router = APIRouter(tags=["operations"])

# Instancias compartidas del dominio de operaciones
_consumption_service = ConsumptionService(inventory=_inventory_service)
_buffet_service = BuffetService(inventory=_inventory_service)
_voice_kitchen_service = VoiceKitchenService(consumption_service=_consumption_service)
_operations_service = OperationsService(inventory=_inventory_service)


def _map_record_item_dto(dto: ConsumptionRecordItemDTO) -> ConsumptionRecordItemResponse:
    return ConsumptionRecordItemResponse(
        id=dto.id,
        consumption_record_id=dto.consumption_record_id,
        tipo_item=dto.tipo_item,
        item_id=dto.item_id,
        cantidad=dto.cantidad,
        unidad_medida=dto.unidad_medida,
        costo_unitario_ppp=dto.costo_unitario_ppp,
        costo_total=dto.costo_total,
        lote_codigo=dto.lote_codigo,
        fecha_vencimiento_lote=dto.fecha_vencimiento_lote,
        kardex_movement_id=dto.kardex_movement_id,
        opciones_seleccionadas=dto.opciones_seleccionadas,
    )


def _map_record_dto(dto: ConsumptionRecordDTO) -> ConsumptionRecordResponse:
    return ConsumptionRecordResponse(
        id=dto.id,
        codigo_folio=dto.codigo_folio,
        bodega_id=dto.bodega_id,
        usuario_id=dto.usuario_id,
        tipo_origen=dto.tipo_origen,
        costo_total=dto.costo_total,
        items=[_map_record_item_dto(it) for it in dto.items],
        folio_ticket=dto.folio_ticket,
        area_operativa_id=dto.area_operativa_id,
        notas=dto.notas,
        created_at=dto.created_at,
        is_undone=dto.is_undone,
    )


def _map_template_dto(dto: ConsumptionTemplateDTO) -> ConsumptionTemplateResponse:
    return ConsumptionTemplateResponse(
        id=dto.id,
        slug=dto.slug,
        nombre=dto.nombre,
        descripcion=dto.descripcion,
        usuario_creador_id=dto.usuario_creador_id,
        is_public=dto.is_public,
        columnas_count=dto.columnas_count,
        sort_mode=dto.sort_mode,
        product_ids=dto.product_ids,
        custom_product_order=dto.custom_product_order,
    )


# ============================================================================
# 1. ENDPOINTS DE REGISTRO DE CONSUMO DIRECTO
# ============================================================================


@router.post(
    "/api/v1/operations/consumption",
    response_model=ConsumptionRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_batch_consumption_endpoint(
    payload: ConsumptionRegisterRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.create")),
    ],
) -> ConsumptionRecordResponse:
    """Registra una transacción batch de consumo directo, descuenta inventario en Kardex y emite evento."""
    items_dicts = [item.model_dump() for item in payload.items]
    record = _consumption_service.process_batch_consumption(
        bodega_id=payload.bodega_id,
        usuario_id=principal.user_id,
        items=items_dicts,
        tipo_origen=payload.tipo_origen,
        area_operativa_id=payload.area_operativa_id,
        folio_ticket=payload.folio_ticket,
        notas=payload.notas,
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
        allow_expired=payload.allow_expired,
    )
    return _map_record_dto(record)


@router.get(
    "/api/v1/operations/consumption/history",
    response_model=ConsumptionHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_consumption_history_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.read")),
    ],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    bodega_id: int | None = Query(default=None),
    area_operativa_id: int | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    tipo_origen: str | None = Query(default=None),
) -> ConsumptionHistoryResponse:
    """Consulta cronológica paginada de registros de consumo con filtros por bodega, área y fecha."""
    records, total = _consumption_service.get_consumption_history(
        page=page,
        page_size=page_size,
        bodega_id=bodega_id,
        area_operativa_id=area_operativa_id,
        usuario_id=usuario_id,
        start_date=start_date,
        end_date=end_date,
        tipo_origen=tipo_origen,
        tenant_id=principal.tenant_id,
    )
    return ConsumptionHistoryResponse(
        items=[_map_record_dto(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/api/v1/operations/consumption/templates",
    response_model=list[ConsumptionTemplateResponse],
    status_code=status.HTTP_200_OK,
)
async def list_consumption_templates_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.read")),
    ],
) -> list[ConsumptionTemplateResponse]:
    """Lista plantillas de consumo rápido accesibles por el usuario."""
    tmpls = _consumption_service.list_templates(
        usuario_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )
    return [_map_template_dto(t) for t in tmpls]


@router.post(
    "/api/v1/operations/consumption/templates",
    response_model=ConsumptionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consumption_template_endpoint(
    payload: ConsumptionTemplateCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.create")),
    ],
) -> ConsumptionTemplateResponse:
    """Crea una nueva plantilla de catálogo de consumo."""
    tmpl = _consumption_service.create_template(
        slug=payload.slug,
        nombre=payload.nombre,
        usuario_creador_id=principal.user_id,
        descripcion=payload.descripcion,
        is_public=payload.is_public,
        columnas_count=payload.columnas_count,
        sort_mode=payload.sort_mode,
        product_ids=payload.product_ids,
        custom_product_order=payload.custom_product_order,
        tenant_id=principal.tenant_id,
    )
    return _map_template_dto(tmpl)


@router.post(
    "/api/v1/operations/consumption/merma-expired",
    response_model=MermaExpiredStockResponse,
    status_code=status.HTTP_201_CREATED,
)
async def merma_expired_stock_endpoint(
    payload: MermaExpiredStockRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.create")),
    ],
) -> MermaExpiredStockResponse:
    """Mermar directamente un lote vencido detectado en la vista de consumo."""
    entry = _consumption_service.merma_expired_stock(
        producto_id=payload.producto_id,
        bodega_id=payload.bodega_id,
        quantity=payload.quantity,
        lote_codigo=payload.lote_codigo,
        fecha_vencimiento=payload.fecha_vencimiento,
        actor_user_id=principal.user_id,
        motivo=payload.motivo,
        unit_cost=payload.unit_cost,
        descripcion=payload.descripcion,
        tenant_id=principal.tenant_id,
    )
    return MermaExpiredStockResponse(
        kardex_entry_id=entry.id,
        producto_id=entry.producto_id,
        bodega_id=entry.bodega_id,
        quantity=entry.quantity,
        movement_type=entry.movement_type,
        resulting_balance=entry.resulting_balance,
        lote_codigo=entry.lote_codigo,
    )


@router.get(
    "/api/v1/operations/consumption/{id}",
    response_model=ConsumptionRecordResponse,
    status_code=status.HTTP_200_OK,
)
async def get_consumption_detail_endpoint(
    id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.read")),
    ],
) -> ConsumptionRecordResponse:
    """Detalle completo de una transacción de consumo y sus insumos."""
    record = _consumption_service.get_consumption_detail(id, tenant_id=principal.tenant_id)
    return _map_record_dto(record)


@router.put(
    "/api/v1/operations/consumption/{id}",
    response_model=ConsumptionRecordResponse,
    status_code=status.HTTP_200_OK,
)
async def update_consumption_endpoint(
    id: int,
    payload: ConsumptionUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.update")),
    ],
) -> ConsumptionRecordResponse:
    """Modificación o corrección justificada de notas en un consumo registrado."""
    record = _consumption_service.update_consumption(
        id,
        notas=payload.notas,
        tenant_id=principal.tenant_id,
    )
    return _map_record_dto(record)


@router.delete(
    "/api/v1/operations/consumption/{id}",
    response_model=ConsumptionRecordResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_consumption_endpoint(
    id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.register.delete")),
    ],
    reason: str | None = Query(default=None),
) -> ConsumptionRecordResponse:
    """Anula y revierte transaccionalmente un consumo devolviendo los insumos a Kardex."""
    record = _consumption_service.delete_consumption(
        id,
        actor_user_id=principal.user_id,
        reason=reason,
        tenant_id=principal.tenant_id,
    )
    return _map_record_dto(record)


# ============================================================================
# 2. ENDPOINTS DE BUFFET INTELIGENTE
# ============================================================================


def _map_buffet_session_response(s: BuffetSessionDTO) -> BuffetSessionResponse:
    return BuffetSessionResponse(
        id=s.id,
        bodega_id=s.bodega_id,
        usuario_creador_id=s.usuario_creador_id,
        tipo_servicio=s.tipo_servicio,
        estado=s.estado,
        costo_total_montaje=s.costo_total_montaje,
        valor_sobrante_reutilizable=s.valor_sobrante_reutilizable,
        costo_neto_pax=s.costo_neto_pax,
        pax_comensales=s.pax_comensales,
        area_operativa_id=s.area_operativa_id,
        template_id=s.template_id,
        stations=[
            BuffetStationResponse(
                id=st.id,
                session_id=st.session_id,
                nombre=st.nombre,
                orden=st.orden,
                peso_inicial_kg=st.peso_inicial_kg,
                peso_sobrante_kg=st.peso_sobrante_kg,
                items=[
                    BuffetSessionItemResponse(
                        id=it.id,
                        station_id=it.station_id,
                        session_id=it.session_id,
                        tipo_item=it.tipo_item,
                        item_id=it.item_id,
                        cantidad_montada=it.cantidad_montada,
                        cantidad_sobrante=it.cantidad_sobrante,
                        cantidad_merma=it.cantidad_merma,
                        cantidad_neta_consumida=it.cantidad_neta_consumida,
                        costo_unitario_ppp=it.costo_unitario_ppp,
                        costo_total=it.costo_total,
                    )
                    for it in st.items
                ],
            )
            for st in s.stations
        ],
        created_at=s.created_at,
        closed_at=s.closed_at,
    )


@router.post(
    "/api/v1/operations/buffet/sessions/start",
    response_model=BuffetSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_buffet_session_endpoint(
    payload: BuffetSessionStartRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.manage")),
    ],
) -> BuffetSessionResponse:
    """Inicia una nueva sesión de buffet y monta las estaciones iniciales."""
    st_dicts = [st.model_dump() for st in payload.estaciones]
    session = _buffet_service.start_buffet_session(
        bodega_id=payload.bodega_id,
        usuario_creador_id=principal.user_id,
        tipo_servicio=payload.tipo_servicio,
        area_operativa_id=payload.area_operativa_id,
        template_id=payload.template_id,
        estaciones=st_dicts,
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
    )
    return _map_buffet_session_response(session)


@router.get(
    "/api/v1/operations/buffet/sessions",
    response_model=list[BuffetSessionResponse],
    status_code=status.HTTP_200_OK,
)
async def list_buffet_sessions_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.manage")),
    ],
    bodega_id: int | None = Query(default=None),
    estado: str | None = Query(default=None),
) -> list[BuffetSessionResponse]:
    """Lista sesiones de buffet activas o históricas."""
    sessions = _buffet_service.list_buffet_sessions(
        bodega_id=bodega_id,
        estado=estado,
        tenant_id=principal.tenant_id,
    )
    return [_map_buffet_session_response(s) for s in sessions]


@router.get(
    "/api/v1/operations/buffet/sessions/{id}",
    response_model=BuffetSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_buffet_session_endpoint(
    id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.manage")),
    ],
) -> BuffetSessionResponse:
    """Detalle completo de sesión de buffet, estaciones e ítems."""
    session = _buffet_service.get_buffet_session_detail(id, tenant_id=principal.tenant_id)
    return _map_buffet_session_response(session)


@router.put(
    "/api/v1/operations/buffet/sessions/{id}/items",
    response_model=BuffetSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_buffet_items_endpoint(
    id: int,
    payload: BuffetItemsUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.manage")),
    ],
) -> BuffetSessionResponse:
    """Actualiza en vivo los montajes, reposiciones y sobrantes por estación."""
    st_data = [st.model_dump() for st in payload.stations]
    session = _buffet_service.update_buffet_items(
        id,
        stations_data=st_data,
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
    )
    return _map_buffet_session_response(session)


@router.post(
    "/api/v1/operations/buffet/sessions/{id}/finalize",
    response_model=BuffetSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def finalize_buffet_session_endpoint(
    id: int,
    payload: BuffetFinalizeRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.approve")),
    ],
) -> BuffetSessionResponse:
    """Liquida y concilia la sesión de buffet, calcula costo por Pax e impacta Kardex."""
    session = _buffet_service.finalize_buffet_session(
        id,
        pax=payload.pax,
        leftover_reusable_value=payload.leftover_reusable_value,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
    )
    return _map_buffet_session_response(session)


@router.get(
    "/api/v1/operations/buffet/templates",
    response_model=list[BuffetTemplateResponse],
    status_code=status.HTTP_200_OK,
)
async def list_buffet_templates_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.manage")),
    ],
) -> list[BuffetTemplateResponse]:
    """Lista plantillas de montaje de estaciones de buffet."""
    tmpls = _buffet_service.list_buffet_templates(tenant_id=principal.tenant_id)
    return [
        BuffetTemplateResponse(
            id=t.id,
            nombre=t.nombre,
            descripcion=t.descripcion,
            comensales_estimados=t.comensales_estimados,
            estaciones_json=t.estaciones_json,
            is_system=t.is_system,
            is_public=t.is_public,
        )
        for t in tmpls
    ]


@router.post(
    "/api/v1/operations/buffet/templates",
    response_model=BuffetTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_buffet_template_endpoint(
    payload: BuffetTemplateCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.buffet.manage")),
    ],
) -> BuffetTemplateResponse:
    """Crea una nueva plantilla de estaciones de buffet."""
    tmpl = _buffet_service.create_buffet_template(
        nombre=payload.nombre,
        comensales_estimados=payload.comensales_estimados,
        descripcion=payload.descripcion,
        estaciones_json=payload.estaciones_json,
        is_system=payload.is_system,
        is_public=payload.is_public,
        tenant_id=principal.tenant_id,
    )
    return BuffetTemplateResponse(
        id=tmpl.id,
        nombre=tmpl.nombre,
        descripcion=tmpl.descripcion,
        comensales_estimados=tmpl.comensales_estimados,
        estaciones_json=tmpl.estaciones_json,
        is_system=tmpl.is_system,
        is_public=tmpl.is_public,
    )


# ============================================================================
# 3. ENDPOINTS DE MANOS LIBRES / COCINA POR VOZ
# ============================================================================


@router.get(
    "/api/v1/operations/voice/stations",
    response_model=list[VoiceStationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_voice_stations_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.handsfree.use")),
    ],
    area_operativa_id: int | None = Query(default=None),
) -> list[VoiceStationResponse]:
    """Lista estaciones de captura por voz operativas."""
    stations = _voice_kitchen_service.list_voice_stations(
        area_operativa_id=area_operativa_id,
        tenant_id=principal.tenant_id,
    )
    return [
        VoiceStationResponse(
            id=s.id,
            nombre_estacion=s.nombre_estacion,
            voice_command=s.voice_command,
            area_operativa_id=s.area_operativa_id,
            usuario_asignado_id=s.usuario_asignado_id,
            is_active=s.is_active,
        )
        for s in stations
    ]


@router.post(
    "/api/v1/operations/voice/stations",
    response_model=VoiceStationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_voice_station_endpoint(
    payload: VoiceStationCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.handsfree.manage")),
    ],
) -> VoiceStationResponse:
    """Configura y registra una estación de comandos por voz."""
    st = _voice_kitchen_service.create_voice_station(
        nombre_estacion=payload.nombre_estacion,
        voice_command=payload.voice_command,
        area_operativa_id=payload.area_operativa_id,
        usuario_asignado_id=payload.usuario_asignado_id,
        tenant_id=principal.tenant_id,
    )
    return VoiceStationResponse(
        id=st.id,
        nombre_estacion=st.nombre_estacion,
        voice_command=st.voice_command,
        area_operativa_id=st.area_operativa_id,
        usuario_asignado_id=st.usuario_asignado_id,
        is_active=st.is_active,
    )


@router.post(
    "/api/v1/operations/voice/orders",
    response_model=VoiceOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_voice_order_endpoint(
    payload: VoiceOrderRegisterRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.handsfree.use")),
    ],
) -> VoiceOrderResponse:
    """Registra una orden por voz capturada en terminal de cocina o barra."""
    items_dicts = [it.model_dump() for it in payload.items_interpretados]
    order = _voice_kitchen_service.register_voice_order(
        station_id=payload.station_id,
        texto_transcrito=payload.texto_transcrito,
        accion_detectada=payload.accion_detectada,
        confianza_ia=payload.confianza_ia,
        items_interpretados=items_dicts,
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
    )
    return VoiceOrderResponse(
        id=order.id,
        station_id=order.station_id,
        texto_transcrito=order.texto_transcrito,
        accion_detectada=order.accion_detectada,
        confianza_ia=order.confianza_ia,
        items_interpretados_json=order.items_interpretados_json,
        estado=order.estado,
        consumption_record_id=order.consumption_record_id,
        created_at=order.created_at,
    )


@router.post(
    "/api/v1/operations/voice/orders/{id}/confirm",
    response_model=VoiceOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_voice_order_endpoint(
    id: int,
    payload: VoiceOrderConfirmRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.handsfree.use")),
    ],
) -> VoiceOrderResponse:
    """Confirma la orden de voz, ejecutando el consumo a Kardex y descontando stock."""
    order = _voice_kitchen_service.confirm_voice_order(
        id,
        bodega_id=payload.bodega_id,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
    )
    return VoiceOrderResponse(
        id=order.id,
        station_id=order.station_id,
        texto_transcrito=order.texto_transcrito,
        accion_detectada=order.accion_detectada,
        confianza_ia=order.confianza_ia,
        items_interpretados_json=order.items_interpretados_json,
        estado=order.estado,
        consumption_record_id=order.consumption_record_id,
        created_at=order.created_at,
    )


@router.post(
    "/api/v1/operations/voice/orders/{id}/reject",
    response_model=VoiceOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def reject_voice_order_endpoint(
    id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("consumption.handsfree.use")),
    ],
) -> VoiceOrderResponse:
    """Descarta una orden verbal errónea o no reconocida."""
    order = _voice_kitchen_service.reject_voice_order(id, tenant_id=principal.tenant_id)
    return VoiceOrderResponse(
        id=order.id,
        station_id=order.station_id,
        texto_transcrito=order.texto_transcrito,
        accion_detectada=order.accion_detectada,
        confianza_ia=order.confianza_ia,
        items_interpretados_json=order.items_interpretados_json,
        estado=order.estado,
        consumption_record_id=order.consumption_record_id,
        created_at=order.created_at,
    )


# ============================================================================
# 4. ENDPOINTS PREVIOS: VENTAS POS, BUFFET COST Y EVENTOS
# ============================================================================


@router.post(
    "/api/v1/operations/sales",
    response_model=PosSaleProcessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_pos_sale_endpoint(
    payload: PosSaleProcessRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.sales.create")),
    ],
) -> PosSaleProcessResponse:
    """Explota la venta POS en consumo de insumos por receta."""
    sale_items = [
        SaleItem(recipe_id=it.recipe_id, portions=it.portions)
        for it in payload.items
    ]
    consumption = explode_sale_consumption(sale_items, payload.recipe_ingredients)
    return PosSaleProcessResponse(
        bodega_id=payload.bodega_id,
        movements_registered=len(consumption),
        consumed_by_ingredient=consumption,
    )


@router.post(
    "/api/v1/operations/buffet",
    response_model=BuffetCostResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_buffet_cost_endpoint(
    payload: BuffetCostRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.buffet.calculate")),
    ],
) -> BuffetCostResponse:
    """Calcula el costo neto por comensal (`pax`) de un servicio de Buffet descontando sobrante reutilizable."""
    pax_cost = buffet_cost_per_pax(
        total_buffet_cost=payload.total_buffet_cost,
        pax=payload.pax,
        leftover_value=payload.leftover_value,
    )
    return BuffetCostResponse(
        service_name=payload.service_name,
        pax=payload.pax,
        total_buffet_cost=payload.total_buffet_cost,
        leftover_value=payload.leftover_value,
        cost_per_pax=pax_cost,
    )


@router.post(
    "/api/v1/operations/events",
    response_model=CateringEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_catering_event_endpoint(
    payload: CateringEventRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.events.create")),
    ],
) -> CateringEventResponse:
    """Calcula ingresos, costo total y margen bruto de un evento gastronómico en `Decimal`."""
    total_revenue = payload.net_price_per_pax * payload.attendees_pax
    total_food_cost = payload.food_cost_per_pax * payload.attendees_pax
    gross_margin = total_revenue - total_food_cost
    return CateringEventResponse(
        event_name=payload.event_name,
        attendees_pax=payload.attendees_pax,
        total_food_cost=total_food_cost,
        total_net_revenue=total_revenue,
        gross_margin=gross_margin,
    )
