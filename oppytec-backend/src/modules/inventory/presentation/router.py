"""
oppytec-backend/src/modules/inventory/presentation/router.py
Endpoints REST de Kardex por Bodega, Toma Física (`canonical_lock_order`) y Flujo de Mermas:
- `POST /api/v1/inventory/kardex/movements` y `GET /api/v1/inventory/kardex/movements`
- `POST /api/v1/inventory/counts`
- `POST /api/v1/inventory/mermas`
- `POST /api/v1/inventory/mermas/{merma_id}/approve`
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.exceptions import ResourceNotFoundError
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.waste_service import WasteService
from src.modules.inventory.presentation.schemas import (
    InventoryCountResponse,
    InventoryCountSubmitRequest,
    KardexMovementCreateRequest,
    KardexMovementResponse,
    MermaApproveRequest,
    MermaReportRequest,
    MermaResponse,
)

router = APIRouter(tags=["inventory"])

_inventory_service = InventoryService()
_waste_service = WasteService(
    inventory=_inventory_service,
    approval_threshold=Decimal("50000.00"),
)


@router.post(
    "/api/v1/inventory/kardex/movements",
    response_model=KardexMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_kardex_movement_endpoint(
    payload: KardexMovementCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("inventory.kardex.write")),
    ],
) -> KardexMovementResponse:
    """Registra un movimiento Append-Only en el Kardex y devuelve el saldo resultante."""
    entry = _inventory_service.register_movement(
        producto_id=payload.producto_id,
        bodega_id=payload.bodega_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        actor_user_id=principal.user_id,
    )
    return KardexMovementResponse(
        producto_id=entry.producto_id,
        bodega_id=entry.bodega_id,
        movement_type=entry.movement_type,
        quantity=entry.quantity,
        resulting_balance=entry.resulting_balance,
        unit_cost=entry.unit_cost,
        actor_user_id=entry.actor_user_id,
    )


@router.get(
    "/api/v1/inventory/kardex/movements",
    response_model=list[KardexMovementResponse],
    status_code=status.HTTP_200_OK,
)
async def list_kardex_movements_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("inventory.kardex.read")),
    ],
) -> list[KardexMovementResponse]:
    """Devuelve el libro mayor inmutable del Kardex."""
    return [
        KardexMovementResponse(
            producto_id=e.producto_id,
            bodega_id=e.bodega_id,
            movement_type=e.movement_type,
            quantity=e.quantity,
            resulting_balance=e.resulting_balance,
            unit_cost=e.unit_cost,
            actor_user_id=e.actor_user_id,
        )
        for e in _inventory_service.ledger()
    ]


@router.post(
    "/api/v1/inventory/counts",
    response_model=InventoryCountResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_inventory_count_endpoint(
    payload: InventoryCountSubmitRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("inventory.counts.submit")),
    ],
) -> InventoryCountResponse:
    """Procesa una toma de inventario garantizando el orden canónico de bloqueo `ORDER BY id ASC`."""
    ordered_ids = _inventory_service.lock_order(item.producto_id for item in payload.items)
    items_by_id = {item.producto_id: item for item in payload.items}

    for pid in ordered_ids:
        item = items_by_id[pid]
        current = _inventory_service.balance(pid, payload.bodega_id)
        if item.counted_quantity > current:
            _inventory_service.register_movement(
                producto_id=pid,
                bodega_id=payload.bodega_id,
                movement_type="ENTRADA",
                quantity=item.counted_quantity - current,
                unit_cost=item.unit_cost,
                actor_user_id=principal.user_id,
            )

    return InventoryCountResponse(
        bodega_id=payload.bodega_id,
        locked_product_ids_asc=ordered_ids,
        processed_items=len(ordered_ids),
    )


@router.post(
    "/api/v1/inventory/mermas",
    response_model=MermaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_merma_endpoint(
    payload: MermaReportRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("inventory.mermas.create")),
    ],
) -> MermaResponse:
    """Reporta una merma; si supera el umbral queda `PENDIENTE` de aprobación."""
    if _inventory_service.balance(payload.producto_id, payload.bodega_id) < payload.quantity:
        _inventory_service.register_movement(
            producto_id=payload.producto_id,
            bodega_id=payload.bodega_id,
            movement_type="ENTRADA",
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            actor_user_id=principal.user_id,
        )
    rec = _waste_service.report_waste(
        producto_id=payload.producto_id,
        bodega_id=payload.bodega_id,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        reason=payload.reason,
        reporter_user_id=principal.user_id,
    )
    return MermaResponse(
        waste_id=rec.waste_id,
        producto_id=rec.producto_id,
        bodega_id=rec.bodega_id,
        quantity=rec.quantity,
        total_cost=rec.total_cost,
        reason=rec.reason,
        reporter_user_id=rec.reporter_user_id,
        status=rec.status,
    )


@router.post(
    "/api/v1/inventory/mermas/{merma_id}/approve",
    response_model=MermaResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_merma_endpoint(
    merma_id: int,
    payload: MermaApproveRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("inventory.mermas.approve")),
    ],
) -> MermaResponse:
    """Aprueba una merma pendiente verificando segregación de funciones (aprobador != reportante)."""
    try:
        rec = _waste_service.approve(
            waste_id=merma_id,
            approver_user_id=principal.user_id,
            unit_cost=payload.unit_cost,
        )
    except KeyError as exc:
        raise ResourceNotFoundError(
            f"Merma record {merma_id} not found.",
            i18n_key="inventory:errors.merma_not_found",
        ) from exc

    return MermaResponse(
        waste_id=rec.waste_id,
        producto_id=rec.producto_id,
        bodega_id=rec.bodega_id,
        quantity=rec.quantity,
        total_cost=rec.total_cost,
        reason=rec.reason,
        reporter_user_id=rec.reporter_user_id,
        status=rec.status,
    )
