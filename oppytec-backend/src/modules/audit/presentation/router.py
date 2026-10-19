"""
oppytec-backend/src/modules/audit/presentation/router.py
Endpoints REST del Doble Libro de Auditoría Forense Append-Only:
- `GET /api/v1/audit/rbac` y `POST /api/v1/audit/rbac`
- `GET /api/v1/audit/activity` y `POST /api/v1/audit/activity`
- `DELETE /api/v1/audit/activity/{event_uuid}` (bloqueo explícito HTTP 403 `AUDIT_APPEND_ONLY_VIOLATION`)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.audit.application.audit_service import AppendOnlyAuditService
from src.modules.audit.presentation.schemas import (
    ActivityAuditCreateRequest,
    ActivityAuditResponse,
    RbacAuditCreateRequest,
    RbacAuditResponse,
)

router = APIRouter(tags=["audit"])

_audit_service = AppendOnlyAuditService()


@router.get(
    "/api/v1/audit/rbac",
    response_model=list[RbacAuditResponse],
    status_code=status.HTTP_200_OK,
)
async def list_rbac_audit_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("audit.rbac_ledger.read")),
    ],
) -> list[RbacAuditResponse]:
    """Consulta la bitácora inmutable de cambios de roles y permisos (`audit_rbac_changes`)."""
    entries = _audit_service.list_rbac_entries()
    return [
        RbacAuditResponse(
            event_uuid=e.event_uuid,
            scope=e.scope,
            actor_user_id=e.actor_user_id,
            target_user_id=e.target_user_id,
            action_type=e.action_type,
            permission_or_role=e.permission_or_role,
            occurred_at_iso=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.post(
    "/api/v1/audit/rbac",
    response_model=RbacAuditResponse,
    status_code=status.HTTP_201_CREATED,
)
async def append_rbac_audit_endpoint(
    payload: RbacAuditCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("audit.rbac_ledger.append")),
    ],
) -> RbacAuditResponse:
    """Agrega un evento Append-Only al libro `audit_rbac_changes`."""
    entry = _audit_service.append_rbac_change(
        actor_user_id=principal.user_id,
        target_user_id=payload.target_user_id,
        action_type=payload.action_type,
        permission_or_role=payload.permission_or_role,
        before_state=dict(payload.before_state),
        after_state=dict(payload.after_state),
        scope=payload.scope,
    )
    return RbacAuditResponse(
        event_uuid=entry.event_uuid,
        scope=entry.scope,
        actor_user_id=entry.actor_user_id,
        target_user_id=entry.target_user_id,
        action_type=entry.action_type,
        permission_or_role=entry.permission_or_role,
        occurred_at_iso=entry.created_at.isoformat(),
    )


@router.get(
    "/api/v1/audit/activity",
    response_model=list[ActivityAuditResponse],
    status_code=status.HTTP_200_OK,
)
async def list_activity_audit_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("audit.activity_ledger.read")),
    ],
) -> list[ActivityAuditResponse]:
    """Consulta la bitácora inmutable de actividad operativa (`audit_activity_log`)."""
    entries = _audit_service.list_activity_entries()
    return [
        ActivityAuditResponse(
            event_uuid=e.event_uuid,
            scope=e.scope,
            actor_user_id=e.actor_user_id,
            action_code=e.action_code,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            authorization_lineage=dict(e.authorization_lineage),
            occurred_at_iso=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.post(
    "/api/v1/audit/activity",
    response_model=ActivityAuditResponse,
    status_code=status.HTTP_201_CREATED,
)
async def append_activity_audit_endpoint(
    payload: ActivityAuditCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("audit.activity_ledger.append")),
    ],
) -> ActivityAuditResponse:
    """Agrega un evento Append-Only con `authorization_lineage` al libro `audit_activity_log`."""
    entry = _audit_service.append_activity_event(
        actor_user_id=principal.user_id,
        action_code=payload.action_code,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        before_state=dict(payload.before_state),
        after_state=dict(payload.after_state),
        authorization_lineage=dict(principal.authorization_lineage),
        scope=payload.scope,
    )
    return ActivityAuditResponse(
        event_uuid=entry.event_uuid,
        scope=entry.scope,
        actor_user_id=entry.actor_user_id,
        action_code=entry.action_code,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        authorization_lineage=dict(entry.authorization_lineage),
        occurred_at_iso=entry.created_at.isoformat(),
    )


@router.delete(
    "/api/v1/audit/activity/{event_uuid}",
    status_code=status.HTTP_403_FORBIDDEN,
)
async def delete_activity_audit_endpoint(
    event_uuid: str,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("audit.activity_ledger.read")),
    ],
) -> None:
    """Rechaza cualquier intento de eliminar un registro de auditoría (Append-Only estricto)."""
    _audit_service.delete_entry(event_uuid)
