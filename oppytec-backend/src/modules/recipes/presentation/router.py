"""
oppytec-backend/src/modules/recipes/presentation/router.py
Endpoints REST de Escandallos Recursivos y Simulador de Margen/Food Cost %:
- `POST /api/v1/recipes/escandallos` y `GET /api/v1/recipes/escandallos`
- `POST /api/v1/recipes/simulate-margin`
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.exceptions import OppyTecError
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.recipes.application.recipe_costing_service import RecipeCostingService
from src.modules.recipes.domain.escandallo_calculator import (
    Recipe,
    RecipeCycleError,
    RecipeLine,
    food_cost_pct,
    margin_amount,
    margin_pct,
)
from src.modules.recipes.presentation.schemas import (
    EscandalloCostResponse,
    EscandalloCreateRequest,
    MarginSimulationRequest,
    MarginSimulationResponse,
)

router = APIRouter(tags=["recipes"])

_costing_service = RecipeCostingService()
_escandallos_store: dict[int, EscandalloCostResponse] = {}


@router.post(
    "/api/v1/recipes/escandallos",
    response_model=EscandalloCostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_escandallo_endpoint(
    payload: EscandalloCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("recipes.escandallos.write")),
    ],
) -> EscandalloCostResponse:
    """Registra una receta/escandallo y calcula recursivamente su costo por porción y Food Cost %."""
    domain_lines: list[RecipeLine] = []
    for ln in payload.lines:
        if ln.ingredient_id is not None:
            _costing_service.set_ingredient_cost(ln.ingredient_id, ln.unit_cost)
        domain_lines.append(
            RecipeLine(
                quantity=ln.quantity,
                ingredient_id=ln.ingredient_id,
                sub_recipe_id=ln.sub_recipe_id,
                waste_pct=ln.waste_pct,
            )
        )

    recipe = Recipe(
        recipe_id=payload.recipe_id,
        lines=tuple(domain_lines),
        yield_portions=payload.yield_portions,
    )
    _costing_service.upsert_recipe(recipe)

    try:
        report = _costing_service.cost_report(payload.recipe_id, payload.net_price)
    except (RecipeCycleError, KeyError, ValueError) as exc:
        raise OppyTecError(
            f"Invalid escandallo definition: {exc}",
            i18n_key="recipes:errors.invalid_escandallo",
            status_code=422,
            error_code="ESCANDALLO_VALIDATION_ERROR",
        ) from exc

    resp = EscandalloCostResponse(
        recipe_id=report.recipe_id,
        name=payload.name,
        portion_cost=report.portion_cost,
        net_price=report.net_price,
        food_cost_pct=report.food_cost_pct,
        margin_amount=report.margin_amount,
        margin_pct=report.margin_pct,
    )
    _escandallos_store[payload.recipe_id] = resp
    return resp


@router.get(
    "/api/v1/recipes/escandallos",
    response_model=list[EscandalloCostResponse],
    status_code=status.HTTP_200_OK,
)
async def list_escandallos_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("recipes.escandallos.read")),
    ],
) -> list[EscandalloCostResponse]:
    """Lista los escandallos costeados del Tenant."""
    return list(_escandallos_store.values())


@router.post(
    "/api/v1/recipes/simulate-margin",
    response_model=MarginSimulationResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_margin_endpoint(
    payload: MarginSimulationRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("recipes.margins.simulate")),
    ],
) -> MarginSimulationResponse:
    """Simula Food Cost % y margen bruto en `Decimal` sin alterar las recetas persistidas."""
    return MarginSimulationResponse(
        portion_cost=payload.portion_cost,
        proposed_net_price=payload.proposed_net_price,
        food_cost_pct=food_cost_pct(payload.portion_cost, payload.proposed_net_price),
        margin_amount=margin_amount(payload.portion_cost, payload.proposed_net_price),
        margin_pct=margin_pct(payload.portion_cost, payload.proposed_net_price),
    )
