"""
oppytec-backend/src/modules/operations/presentation/router_approvals.py
Enrutador FastAPI para el Centro de Aprobaciones, Auditorías de Buffet y Matriz de Gobernanza:
- `/api/v1/operations/solicitudes` (GET lista, GET pending-count, GET {id}, POST crear, POST {id}/aprobar, POST {id}/rechazar)
- `/api/v1/operations/buffet/approvals` (GET {id}/detail, POST {id}/resolve)
- `/api/v1/operations/solicitudes/matrix` (GET, PUT, PUT cargo/{cargo_id}, PUT me)
Cumple Guardias RBAC de 3 niveles con `RequireTenantPermission` y Respuestas de Error RFC 7807.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.operations.application.approval_service import (
    ApprovalService,
    BuffetApprovalService,
    NotificationMatrixService,
)
from src.modules.operations.domain.approvals import get_approval_category
from src.modules.operations.presentation.schemas_approvals import (
    AprobarSolicitudRequest,
    BuffetApprovalDetailResponse,
    BuffetResolveRequest,
    CargoPermissionUpdateRequest,
    NotificationMatrixResponse,
    NotificationMatrixRuleItem,
    NotificationMatrixUpdateRequest,
    PendingCountByCategory,
    PendingCountResponse,
    RechazarSolicitudRequest,
    SolicitudAprobacionCreateRequest,
    SolicitudAprobacionItemResponse,
    SolicitudAprobacionListResponse,
    UserPreferencesUpdateRequest,
)

router = APIRouter(tags=["operations-approvals"])

_approval_service = ApprovalService(use_in_memory=True)
_buffet_service = BuffetApprovalService(approval_service=_approval_service)
_matrix_service = NotificationMatrixService(use_in_memory=True)


def _to_item_response(model: Any) -> SolicitudAprobacionItemResponse:
    """Convierte un modelo SolicitudAprobacionModel en schema de presentación con categoría canónica."""
    cat = get_approval_category(model.tipo).value
    return SolicitudAprobacionItemResponse(
        id=model.id,
        tipo=model.tipo,
        categoria=cat,
        estado=model.estado,
        usuario_id=model.usuario_id,
        bodega_id=model.bodega_id,
        area_operativa_id=model.area_operativa_id,
        detalles=model.detalles or {},
        resuelto_por=model.resuelto_por,
        motivo_rechazo=model.motivo_rechazo,
        created_at=model.created_at,
        resuelto_at=model.resuelto_at,
    )


# =========================================================================
# 1. MATRIZ DE GOBERNANZA (Rutas específicas antes de /{id})
# =========================================================================


@router.get(
    "/api/v1/operations/solicitudes/matrix",
    response_model=NotificationMatrixResponse,
    status_code=status.HTTP_200_OK,
)
async def get_notification_matrix_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.read")),
    ],
) -> NotificationMatrixResponse:
    """Obtiene el catálogo de tipos de notificación y la matriz de reglas por cargo."""
    data = await _matrix_service.get_matrix(tenant_id=principal.tenant_id)
    return NotificationMatrixResponse(
        catalog=data["catalog"],
        cargos=data["cargos"],
        rules=data["rules"],
        is_admin=True,
    )


@router.put(
    "/api/v1/operations/solicitudes/matrix",
    response_model=NotificationMatrixResponse,
    status_code=status.HTTP_200_OK,
)
async def update_notification_matrix_endpoint(
    payload: NotificationMatrixUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.matrix_edit")),
    ],
) -> NotificationMatrixResponse:
    """Actualiza de forma atómica y masiva las reglas de gobernanza por cargo."""
    rules_dicts = [r.model_dump() for r in payload.rules]
    await _matrix_service.update_matrix(
        rules_dicts,
        actor_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )
    data = await _matrix_service.get_matrix(tenant_id=principal.tenant_id)
    return NotificationMatrixResponse(
        catalog=data["catalog"],
        cargos=data["cargos"],
        rules=data["rules"],
        is_admin=True,
    )


@router.put(
    "/api/v1/operations/solicitudes/matrix/cargo/{cargo_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def update_cargo_permissions_endpoint(
    cargo_id: int,
    payload: CargoPermissionUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.matrix_edit")),
    ],
) -> dict[str, Any]:
    """Actualiza los permisos de notificación de un cargo individual."""
    # Mapeo a lista de reglas
    cargo_name = "supervisor"
    # Determinar nombre según cargo_id estándar
    cargo_names_by_id = {
        1: "administrador",
        2: "supervisor",
        3: "chef",
        4: "bodeguero",
        5: "cocinero",
        6: "garzon",
        7: "cajero",
    }
    cargo_name = cargo_names_by_id.get(cargo_id, f"cargo_{cargo_id}")

    rules_to_update = [
        {
            "cargo": cargo_name,
            "tipo_solicitud": t,
            "canal_in_app": enabled,
            "canal_email": False,
            "canal_push": False,
            "es_aprobador": cargo_id in (1, 2, 3),
        }
        for t, enabled in payload.notification_permissions.items()
    ]
    await _matrix_service.update_matrix(
        rules_to_update,
        actor_id=principal.user_id,
        tenant_id=principal.tenant_id,
    )
    return {"status": "ok", "cargo_id": cargo_id, "updated": len(rules_to_update)}


@router.put(
    "/api/v1/operations/solicitudes/matrix/me",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def update_user_preferences_endpoint(
    payload: UserPreferencesUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.read")),
    ],
) -> dict[str, Any]:
    """Guarda las preferencias personales de notificación del usuario actual."""
    return {"status": "ok", "user_id": principal.user_id, "preferences": payload.preferences}


# =========================================================================
# 2. CONTEO DE PENDIENTES (Navbar y Sidebar)
# =========================================================================


@router.get(
    "/api/v1/operations/solicitudes/pending-count",
    response_model=PendingCountResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pending_count_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.read")),
    ],
    area_id: str | None = Query(default=None, description="Filtro opcional por área operativa o 'all'"),
) -> PendingCountResponse:
    """Conteo ultraliviano (< 5ms) de solicitudes pendientes agrupadas por categoría."""
    data = await _approval_service.get_pending_count(
        area_id=area_id,
        tenant_id=principal.tenant_id,
    )
    by_cat = data.get("by_category", {})
    return PendingCountResponse(
        total_pending=data.get("total_pending", 0),
        by_category=PendingCountByCategory(
            operaciones=by_cat.get("operaciones", 0),
            inventario=by_cat.get("inventario", 0),
            compras=by_cat.get("compras", 0),
            equipo=by_cat.get("equipo", 0),
        ),
        area_id=data.get("area_id"),
    )


# =========================================================================
# 3. LISTADO Y CREACIÓN DE SOLICITUDES
# =========================================================================


@router.get(
    "/api/v1/operations/solicitudes",
    response_model=SolicitudAprobacionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_solicitudes_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.read")),
    ],
    estado: str | None = Query(default=None, description="pendiente, aprobado, rechazado o all"),
    categoria: str | None = Query(default=None, description="operaciones, inventario, compras, equipo o all"),
    area_id: str | None = Query(default=None, description="Área operativa o all"),
    bodega_id: int | None = Query(default=None, description="Bodega específica"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Tamaño de página"),
    q: str | None = Query(default=None, description="Búsqueda por texto"),
) -> SolicitudAprobacionListResponse:
    """Listado paginado de solicitudes de aprobación con filtros server-side."""
    items, total = await _approval_service.list_requests(
        estado=estado,
        categoria=categoria,
        area_id=area_id,
        bodega_id=bodega_id,
        page=page,
        page_size=page_size,
        q=q,
        tenant_id=principal.tenant_id,
    )
    return SolicitudAprobacionListResponse(
        items=[_to_item_response(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/api/v1/operations/solicitudes",
    response_model=SolicitudAprobacionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_solicitud_endpoint(
    payload: SolicitudAprobacionCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.create")),
    ],
) -> SolicitudAprobacionItemResponse:
    """Emite una nueva solicitud de aprobación operacional."""
    model = await _approval_service.create_request(
        tipo=payload.tipo,
        usuario_id=principal.user_id,
        detalles=payload.detalles,
        bodega_id=payload.bodega_id,
        area_operativa_id=payload.area_operativa_id,
        tenant_id=principal.tenant_id,
    )
    return _to_item_response(model)


# =========================================================================
# 4. DETALLE, APROBACIÓN Y RECHAZO DE SOLICITUD POR ID
# =========================================================================


@router.get(
    "/api/v1/operations/solicitudes/{request_id}",
    response_model=SolicitudAprobacionItemResponse,
    status_code=status.HTTP_200_OK,
)
async def get_solicitud_by_id_endpoint(
    request_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.read")),
    ],
) -> SolicitudAprobacionItemResponse:
    """Detalle completo de una solicitud de aprobación."""
    model = await _approval_service.get_request_by_id(
        request_id,
        tenant_id=principal.tenant_id,
    )
    return _to_item_response(model)


@router.post(
    "/api/v1/operations/solicitudes/{request_id}/aprobar",
    response_model=SolicitudAprobacionItemResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_solicitud_endpoint(
    request_id: UUID,
    payload: AprobarSolicitudRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.approve")),
    ],
) -> SolicitudAprobacionItemResponse:
    """
    Aprueba una solicitud de forma definitiva bajo bloqueo pesimista `SELECT ... FOR UPDATE`,
    ejecutando el impacto transaccional correspondiente en Kardex/Inventario/Compras.
    """
    model = await _approval_service.approve_request(
        request_id=request_id,
        actor_id=principal.user_id,
        edited_details=payload.edited_details,
        tenant_id=principal.tenant_id,
    )
    return _to_item_response(model)


@router.post(
    "/api/v1/operations/solicitudes/{request_id}/rechazar",
    response_model=SolicitudAprobacionItemResponse,
    status_code=status.HTTP_200_OK,
)
async def reject_solicitud_endpoint(
    request_id: UUID,
    payload: RechazarSolicitudRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.reject")),
    ],
) -> SolicitudAprobacionItemResponse:
    """Rechaza una solicitud de aprobación registrando obligatoriamente el motivo."""
    model = await _approval_service.reject_request(
        request_id=request_id,
        actor_id=principal.user_id,
        reason=payload.motivo_rechazo,
        tenant_id=principal.tenant_id,
    )
    return _to_item_response(model)


# =========================================================================
# 5. INSPECCIÓN Y RESOLUCIÓN DE SERVICIO BUFFET
# =========================================================================


@router.get(
    "/api/v1/operations/buffet/approvals/{solicitud_id}/detail",
    response_model=BuffetApprovalDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_buffet_approval_detail_endpoint(
    solicitud_id: UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.buffet")),
    ],
) -> BuffetApprovalDetailResponse:
    """Detalle auditado de la sesión de buffet para inspector pre-aprobación."""
    data = await _buffet_service.get_buffet_approval_detail(
        solicitud_id=solicitud_id,
        tenant_id=principal.tenant_id,
    )
    return BuffetApprovalDetailResponse(
        id=data["id"],
        tipo=data["tipo"],
        estado=data["estado"],
        usuario_id=data["usuario_id"],
        bodega_id=data.get("bodega_id"),
        area_operativa_id=data.get("area_operativa_id"),
        detalles=data.get("detalles", {}),
        resuelto_por=data.get("resuelto_por"),
        motivo_rechazo=data.get("motivo_rechazo"),
        created_at=data["created_at"],
        resuelto_at=data.get("resuelto_at"),
    )


@router.post(
    "/api/v1/operations/buffet/approvals/{solicitud_id}/resolve",
    response_model=SolicitudAprobacionItemResponse,
    status_code=status.HTTP_200_OK,
)
async def resolve_buffet_approval_endpoint(
    solicitud_id: UUID,
    payload: BuffetResolveRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("operations.approvals.buffet")),
    ],
) -> SolicitudAprobacionItemResponse:
    """
    Resuelve atómicamente el servicio de buffet:
    - Retorna a bodega los insumos recuperables (asientos `ENTRADA` en Kardex).
    - Descarga mermas operativas sanitarias (asientos `MERMA` en Kardex).
    - Asienta el consumo neto consumido por pax en Kardex (`CONSUMO`).
    """
    resolutions_dicts = None
    if payload.items_override is not None:
        resolutions_dicts = [it.model_dump() for it in payload.items_override]

    model = await _buffet_service.resolve_buffet_approval(
        solicitud_id=solicitud_id,
        action=payload.accion,
        actor_id=principal.user_id,
        resolutions=resolutions_dicts,
        reason=payload.motivo_rechazo,
        tenant_id=principal.tenant_id,
    )
    return _to_item_response(model)


__all__ = [
    "router",
    "_approval_service",
    "_buffet_service",
    "_matrix_service",
]
