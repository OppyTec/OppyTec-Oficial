"""
oppytec-backend/src/modules/operations/presentation/router.py
Endpoints REST de Operaciones Gastronómicas (Ventas POS, Buffet por Pax y Eventos/Banquetería):
- `POST /api/v1/operations/sales`
- `POST /api/v1/operations/buffet`
- `POST /api/v1/operations/events`
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.operations.domain.pos_consumption import (
    SaleItem,
    buffet_cost_per_pax,
    explode_sale_consumption,
)
from src.modules.operations.presentation.schemas import (
    BuffetCostRequest,
    BuffetCostResponse,
    CateringEventRequest,
    CateringEventResponse,
    PosSaleProcessRequest,
    PosSaleProcessResponse,
)

router = APIRouter(tags=["operations"])


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
    pax_dec = Decimal(payload.attendees_pax)
    total_cost = (payload.food_cost_per_pax * pax_dec).quantize(Decimal("0.01"))
    total_rev = (payload.net_price_per_pax * pax_dec).quantize(Decimal("0.01"))
    margin = (total_rev - total_cost).quantize(Decimal("0.01"))
    return CateringEventResponse(
        event_name=payload.event_name,
        attendees_pax=payload.attendees_pax,
        total_food_cost=total_cost,
        total_net_revenue=total_rev,
        gross_margin=margin,
    )
