"""
oppytec-backend/src/modules/recipes/presentation/router.py
Routers FastAPI para Gestión Integral de Recetas, Escandallos Dinámicos, Combos y Opciones Polimórficas:
- Biblioteca de Grupos de Opciones e Ítems (`/api/v1/recipes/option-groups`)
- Fichas Técnicas de Recetas y Escandallos (`/api/v1/recipes`)
- Simulación en Vivo de Costos ante Opciones (`/api/v1/recipes/{id}/simulate-cost`)
- Combos Comerciales y Menús Promocionales (`/api/v1/combos`)
- Categorías Clasificatorias (`/api/v1/recipes/categories`, `/api/v1/combos/categories`)
- Compatibilidad Retroactiva con Escandallos Básicos (`/api/v1/recipes/escandallos`, `/api/v1/recipes/simulate-margin`)
- Respuestas RFC 7807 (`ProblemDetails`), Guardias RBAC de 3 niveles y Emisión Realtime WebSocket.
"""
from __future__ import annotations

from contextlib import suppress
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.exceptions import OppyTecError
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.recipes.application.combo_service import (
    ComboCategoryDTO,
    ComboDTO,
    ComboItemDTO,
    ComboOptionGroupLinkDTO,
    ComboService,
)
from src.modules.recipes.application.option_group_service import (
    OptionGroupDTO,
    OptionGroupService,
    OptionItemDTO,
)
from src.modules.recipes.application.recipe_cost_simulator_service import (
    RecipeCostSimulatorService,
    SimulationResult,
)
from src.modules.recipes.application.recipe_costing_service import RecipeCostingService
from src.modules.recipes.application.recipe_service import (
    KitchenSheetDTO,
    KitchenSheetItemDTO,
    KitchenSheetOptionGroupDTO,
    KitchenSheetOptionItemDTO,
    RecipeCategoryDTO,
    RecipeDTO,
    RecipeIngredientDTO,
    RecipeOptionGroupLinkDTO,
    RecipeService,
)
from src.modules.recipes.domain.allergens import AllergenDefinition
from src.modules.recipes.domain.escandallo_calculator import (
    Recipe as DomainLegacyRecipe,
    RecipeCycleError,
    RecipeLine as DomainLegacyRecipeLine,
    food_cost_pct as legacy_food_cost_pct,
    margin_amount as legacy_margin_amount,
    margin_pct as legacy_margin_pct,
)
from src.modules.recipes.presentation.schemas import (
    AllergenInfo,
    ComboCategoryCreateRequest,
    ComboCategoryResponse,
    ComboCategoryUpdateRequest,
    ComboCreateRequest,
    ComboDetailResponse,
    ComboItemCreate,
    ComboItemResponse,
    ComboOptionGroupLinkRequest,
    ComboOptionGroupLinkResponse,
    ComboSummaryResponse,
    ComboUpdateRequest,
    EscandalloCostResponse,
    EscandalloCreateRequest,
    KitchenSheetItem,
    KitchenSheetOptionGroupResponse,
    KitchenSheetOptionItemResponse,
    KitchenSheetResponse,
    MarginSimulationRequest,
    MarginSimulationResponse,
    OptionGroupCreateRequest,
    OptionGroupItemCreate,
    OptionGroupItemResponse,
    OptionGroupResponse,
    OptionGroupUpdateRequest,
    RecipeCategoryCreateRequest,
    RecipeCategoryResponse,
    RecipeCategoryUpdateRequest,
    RecipeCostSimulationRequest,
    RecipeCostSimulationResponse,
    RecipeCreateRequest,
    RecipeDetailResponse,
    RecipeIngredientCreate,
    RecipeIngredientResponse,
    RecipeOptionGroupLinkRequest,
    RecipeOptionGroupLinkResponse,
    RecipeSummaryResponse,
    RecipeUpdateRequest,
    SimulatedOptionResponse,
)

router = APIRouter(tags=["recipes"])

# Instancias de Servicios de Aplicación (ciclo de vida de la aplicación)
_option_group_service = OptionGroupService()
_recipe_service = RecipeService(option_group_service=_option_group_service)
_combo_service = ComboService(recipe_service=_recipe_service, option_group_service=_option_group_service)
_simulator_service = RecipeCostSimulatorService(recipe_service=_recipe_service)

# Estado retroactivo legacy
_legacy_costing_service = RecipeCostingService()
_legacy_escandallos_store: dict[int, EscandalloCostResponse] = {}


def get_recipe_service() -> RecipeService:
    return _recipe_service


def get_combo_service() -> ComboService:
    return _combo_service


def get_option_group_service() -> OptionGroupService:
    return _option_group_service


def get_recipe_cost_simulator_service() -> RecipeCostSimulatorService:
    return _simulator_service


def _parse_optional_uuid(val: str | None) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(str(val))
    except Exception:
        return None


async def _publish_realtime_event(
    event_type: str,
    principal: AuthenticatedPrincipal,
    required_permission: str,
    query_key: str,
    payload: dict[str, object],
) -> None:
    """Emite evento de mutación a los clientes WebSocket suscritos a través de Redis Pub/Sub."""
    with suppress(Exception):
        publisher = get_realtime_publisher()
        await publisher.publish_event(
            RealtimeEventEnvelope(
                event_type=event_type,
                holding_id=_parse_optional_uuid(principal.holding_id),
                tenant_id=_parse_optional_uuid(principal.tenant_id),
                required_permission=required_permission,
                query_keys_to_invalidate=[[query_key]],
                payload=payload,
            )
        )


# ============================================================================
# FUNCIONES AUXILIARES DE CONVERSIÓN DTO -> SCHEMA
# ============================================================================


def _to_option_group_response(group: OptionGroupDTO) -> OptionGroupResponse:
    items_resp = [
        OptionGroupItemResponse(
            id=it.id or 0,
            producto_id=it.producto_id,
            receta_id=it.receta_id,
            nombre=it.nombre,
            target_type="receta" if it.receta_id is not None else "producto",
            cantidad=it.cantidad,
            es_opcion_default=it.es_opcion_default,
            recargo_precio=it.recargo_precio,
            orden=it.orden,
            costo_referencial=it.costo_referencial,
        )
        for it in group.items
    ]
    return OptionGroupResponse(
        id=group.id or 0,
        nombre=group.nombre,
        descripcion=group.descripcion,
        seleccion_minima=group.seleccion_minima,
        seleccion_maxima=group.seleccion_maxima,
        min_selecciones=group.seleccion_minima,
        max_selecciones=group.seleccion_maxima,
        permite_repetir=group.permite_repetir,
        items=items_resp,
    )


def _to_recipe_summary_response(r: RecipeDTO) -> RecipeSummaryResponse:
    return RecipeSummaryResponse(
        id=r.id,
        codigo=r.codigo,
        nombre=r.nombre,
        descripcion=r.descripcion,
        categoria_receta_id=r.categoria_receta_id,
        categoria_nombre=r.categoria_nombre,
        es_subreceta=r.es_subreceta,
        es_dinamica=r.es_dinamica,
        porciones_rendimiento=r.porciones_rendimiento,
        costo_total_calculado=r.costo_total_calculado,
        costo_porcion=r.costo_porcion,
        costo_peor_caso=r.costo_peor_caso,
        costo_mejor_caso=r.costo_mejor_caso,
        precio_venta_neto=r.precio_venta_neto,
        precio_venta_bruto=r.precio_venta_bruto,
        margen_neto=r.margen_neto,
        margen_bruto=r.margen_bruto,
        margen_pct=r.margen_pct,
        food_cost_pct=r.food_cost_pct,
        imagen_url=r.imagen_url,
    )


def _to_allergen_info(a: AllergenDefinition) -> AllergenInfo:
    return AllergenInfo(
        code=a.code,
        nombre=a.nombre,
        nombre_en=a.nombre_en,
        icono=a.icono,
        descripcion=a.descripcion,
    )


def _to_kitchen_sheet_item_response(it: KitchenSheetItemDTO) -> KitchenSheetItem:
    return KitchenSheetItem(
        ingrediente_id=it.ingrediente_id,
        producto_id=it.producto_id,
        subreceta_id=it.subreceta_id,
        nombre=it.nombre,
        target_type=it.target_type,
        unidad=it.unidad,
        cantidad_neta_base=it.cantidad_neta_base,
        cantidad_neta_escalada=it.cantidad_neta_escalada,
        porcentaje_merma=it.porcentaje_merma,
        cantidad_bruta_escalada=it.cantidad_bruta_escalada,
        notas=it.notas,
        alergenos=[_to_allergen_info(a) for a in it.alergenos],
        subreceta_desglose=[_to_kitchen_sheet_item_response(sub) for sub in it.subreceta_desglose],
    )


def _to_kitchen_sheet_response(sheet: KitchenSheetDTO) -> KitchenSheetResponse:
    items_resp = [_to_kitchen_sheet_item_response(it) for it in sheet.ingredientes_fijos]
    groups_resp = [
        KitchenSheetOptionGroupResponse(
            grupo_id=grp.grupo_id,
            grupo_nombre=grp.grupo_nombre,
            seleccion_minima=grp.seleccion_minima,
            seleccion_maxima=grp.seleccion_maxima,
            es_requerido=grp.es_requerido,
            opciones=[
                KitchenSheetOptionItemResponse(
                    item_id=opt.item_id,
                    producto_id=opt.producto_id,
                    receta_id=opt.receta_id,
                    nombre=opt.nombre,
                    target_type=opt.target_type,
                    cantidad_base=opt.cantidad_base,
                    cantidad_escalada=opt.cantidad_escalada,
                    unidad=opt.unidad,
                    es_opcion_default=opt.es_opcion_default,
                    recargo_precio=opt.recargo_precio,
                    alergenos=[_to_allergen_info(a) for a in opt.alergenos],
                )
                for opt in grp.opciones
            ],
        )
        for grp in sheet.grupos_opciones
    ]
    allergens_resp = [_to_allergen_info(a) for a in sheet.alergenos_consolidados]
    return KitchenSheetResponse(
        recipe_id=sheet.recipe_id,
        codigo=sheet.codigo,
        nombre=sheet.nombre,
        descripcion=sheet.descripcion,
        categoria_nombre=sheet.categoria_nombre,
        porciones_base=sheet.porciones_base,
        porciones_solicitadas=sheet.porciones_solicitadas,
        factor_escalamiento=sheet.factor_escalamiento,
        tiempo_preparacion_minutos=sheet.tiempo_preparacion_minutos,
        preparacion=sheet.preparacion,
        video_url=sheet.video_url,
        documento_url=sheet.documento_url,
        ingredientes_fijos=items_resp,
        grupos_opciones=groups_resp,
        alergenos_consolidados=allergens_resp,
        allergens=allergens_resp,
    )


def _to_recipe_detail_response(r: RecipeDTO, tree: list[dict[str, Any]]) -> RecipeDetailResponse:
    ingredientes_resp = [
        RecipeIngredientResponse(
            id=ing.id or 0,
            producto_id=ing.producto_id,
            subreceta_id=ing.subreceta_id,
            nombre=ing.nombre,
            target_type=ing.target_type,
            unidad=ing.unidad,
            cantidad_receta=ing.cantidad_receta,
            porcentaje_merma=ing.porcentaje_merma,
            costo_unitario=ing.costo_unitario,
            costo_total=ing.costo_total,
            bodega_consumo_id=ing.bodega_consumo_id,
            notas=ing.notas,
        )
        for ing in r.ingredientes_fijos
    ]
    grupos_resp = [
        RecipeOptionGroupLinkResponse(
            grupo_id=link.grupo_id,
            orden=link.orden,
            es_requerido=link.es_requerido,
            grupo=_to_option_group_response(link.grupo) if link.grupo else None,
        )
        for link in r.grupos_opciones
    ]
    allergens_list = [_to_allergen_info(a) for a in r.alergenos]
    return RecipeDetailResponse(
        id=r.id,
        codigo=r.codigo,
        nombre=r.nombre,
        descripcion=r.descripcion,
        categoria_receta_id=r.categoria_receta_id,
        categoria_nombre=r.categoria_nombre,
        es_subreceta=r.es_subreceta,
        es_dinamica=r.es_dinamica,
        porciones_rendimiento=r.porciones_rendimiento,
        costo_total_calculado=r.costo_total_calculado,
        costo_porcion=r.costo_porcion,
        costo_peor_caso=r.costo_peor_caso,
        costo_mejor_caso=r.costo_mejor_caso,
        precio_venta_neto=r.precio_venta_neto,
        precio_venta_bruto=r.precio_venta_bruto,
        margen_neto=r.margen_neto,
        margen_bruto=r.margen_bruto,
        margen_pct=r.margen_pct,
        food_cost_pct=r.food_cost_pct,
        imagen_url=r.imagen_url,
        iva_porcentaje=r.iva_porcentaje,
        iva_incluido=r.iva_incluido,
        preparacion=r.preparacion,
        video_url=r.video_url,
        documento_url=r.documento_url,
        tiempo_preparacion_minutos=r.tiempo_preparacion_minutos,
        ingredientes_fijos=ingredientes_resp,
        grupos_opciones=grupos_resp,
        subrecetas_tree=tree,
        alergenos=allergens_list,
        allergens=allergens_list,
    )


def _to_combo_summary_response(c: ComboDTO) -> ComboSummaryResponse:
    return ComboSummaryResponse(
        id=c.id,
        codigo=c.codigo,
        nombre=c.nombre,
        descripcion=c.descripcion,
        categoria_combo_id=c.categoria_combo_id,
        categoria_nombre=c.categoria_nombre,
        es_dinamico=c.es_dinamico,
        precio_venta_neto=c.precio_venta_neto,
        precio_venta_bruto=c.precio_venta_bruto,
        costo_total_calculado=c.costo_total_calculado,
        margen_amount=c.margen_amount,
        margen_pct=c.margen_pct,
        food_cost_pct=c.food_cost_pct,
        disponibilidad_stock_porciones=c.disponibilidad_stock_porciones,
        esta_disponible=c.esta_disponible,
        imagen_url=c.imagen_url,
    )


def _to_combo_detail_response(c: ComboDTO) -> ComboDetailResponse:
    items_resp = [
        ComboItemResponse(
            id=it.id or 0,
            producto_id=it.producto_id,
            receta_id=it.receta_id,
            nombre=it.nombre,
            target_type=it.target_type,
            cantidad=it.cantidad,
            costo_unitario=it.costo_unitario,
            costo_total=it.costo_total,
        )
        for it in c.items_fijos
    ]
    grupos_resp = [
        ComboOptionGroupLinkResponse(
            grupo_id=link.grupo_id,
            orden=link.orden,
            es_requerido=link.es_requerido,
            grupo=_to_option_group_response(link.grupo) if link.grupo else None,
        )
        for link in c.grupos_opciones
    ]
    return ComboDetailResponse(
        id=c.id,
        codigo=c.codigo,
        nombre=c.nombre,
        descripcion=c.descripcion,
        categoria_combo_id=c.categoria_combo_id,
        categoria_nombre=c.categoria_nombre,
        es_dinamico=c.es_dinamico,
        precio_venta_neto=c.precio_venta_neto,
        precio_venta_bruto=c.precio_venta_bruto,
        costo_total_calculado=c.costo_total_calculado,
        margen_amount=c.margen_amount,
        margen_pct=c.margen_pct,
        food_cost_pct=c.food_cost_pct,
        disponibilidad_stock_porciones=c.disponibilidad_stock_porciones,
        esta_disponible=c.esta_disponible,
        imagen_url=c.imagen_url,
        iva_porcentaje=c.iva_porcentaje,
        iva_incluido=c.iva_incluido,
        items_fijos=items_resp,
        grupos_opciones=grupos_resp,
    )


# ============================================================================
# 1. BIBLIOTECA DE GRUPOS DE OPCIONES (`/api/v1/recipes/option-groups`)
# ============================================================================


@router.get(
    "/api/v1/recipes/option-groups",
    response_model=list[OptionGroupResponse],
    status_code=status.HTTP_200_OK,
)
async def list_option_groups_endpoint(
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.options.manage"))],
    search: str | None = Query(default=None, description="Búsqueda por texto"),
) -> list[OptionGroupResponse]:
    """Lista la biblioteca de grupos de modificadores u opciones del tenant."""
    groups = _option_group_service.list_option_groups(tenant_id=principal.tenant_id, search=search)
    return [_to_option_group_response(g) for g in groups]


@router.post(
    "/api/v1/recipes/option-groups",
    response_model=OptionGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_option_group_endpoint(
    payload: OptionGroupCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.options.manage"))],
) -> OptionGroupResponse:
    """Crea un nuevo grupo de opciones en la biblioteca general o in-situ."""
    item_dtos = [
        OptionItemDTO(
            producto_id=it.producto_id,
            receta_id=it.receta_id,
            nombre=it.nombre,
            cantidad=it.cantidad,
            es_opcion_default=it.es_opcion_default,
            recargo_precio=it.recargo_precio,
            orden=it.orden,
        )
        for it in payload.items
    ]
    created = _option_group_service.create_option_group(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        seleccion_minima=payload.seleccion_minima,
        seleccion_maxima=payload.seleccion_maxima,
        permite_repetir=payload.permite_repetir,
        items=item_dtos,
        tenant_id=principal.tenant_id,
    )
    return _to_option_group_response(created)


@router.get(
    "/api/v1/recipes/option-groups/{id}",
    response_model=OptionGroupResponse,
    status_code=status.HTTP_200_OK,
)
async def get_option_group_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.options.manage"))],
) -> OptionGroupResponse:
    """Obtiene el detalle de un grupo de opciones y sus alternativas."""
    group = _option_group_service.get_option_group(group_id=id, tenant_id=principal.tenant_id)
    return _to_option_group_response(group)


@router.put(
    "/api/v1/recipes/option-groups/{id}",
    response_model=OptionGroupResponse,
    status_code=status.HTTP_200_OK,
)
async def update_option_group_endpoint(
    id: int,
    payload: OptionGroupUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.options.manage"))],
) -> OptionGroupResponse:
    """Actualiza configuración e ítems de un grupo de opciones."""
    item_dtos = None
    if payload.items is not None:
        item_dtos = [
            OptionItemDTO(
                producto_id=it.producto_id,
                receta_id=it.receta_id,
                nombre=it.nombre,
                cantidad=it.cantidad,
                es_opcion_default=it.es_opcion_default,
                recargo_precio=it.recargo_precio,
                orden=it.orden,
            )
            for it in payload.items
        ]
    updated = _option_group_service.update_option_group(
        group_id=id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        seleccion_minima=payload.seleccion_minima,
        seleccion_maxima=payload.seleccion_maxima,
        permite_repetir=payload.permite_repetir,
        items=item_dtos,
        tenant_id=principal.tenant_id,
    )
    return _to_option_group_response(updated)


@router.delete(
    "/api/v1/recipes/option-groups/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_option_group_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.options.manage"))],
) -> None:
    """Elimina un grupo de opciones con validación de uso en recetas o combos activos (retorna 409 si está en uso)."""
    _option_group_service.delete_option_group(group_id=id, tenant_id=principal.tenant_id)


# ============================================================================
# 2. CATEGORÍAS DE RECETAS (`/api/v1/recipes/categories`)
# ============================================================================


@router.get(
    "/api/v1/recipes/categories",
    response_model=list[RecipeCategoryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_recipe_categories_endpoint(
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.read"))],
) -> list[RecipeCategoryResponse]:
    """Lista las categorías clasificatorias de recetas del tenant."""
    cats = _recipe_service.list_categories(tenant_id=principal.tenant_id)
    return [
        RecipeCategoryResponse(
            id=c.id,
            nombre=c.nombre,
            color=c.color,
            icono=c.icono,
            orden=c.orden,
        )
        for c in cats
    ]


@router.post(
    "/api/v1/recipes/categories",
    response_model=RecipeCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipe_category_endpoint(
    payload: RecipeCategoryCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.write"))],
) -> RecipeCategoryResponse:
    """Crea una nueva categoría de recetas."""
    c = _recipe_service.create_category(
        nombre=payload.nombre,
        color=payload.color,
        icono=payload.icono,
        orden=payload.orden,
        tenant_id=principal.tenant_id,
    )
    return RecipeCategoryResponse(
        id=c.id,
        nombre=c.nombre,
        color=c.color,
        icono=c.icono,
        orden=c.orden,
    )


# ============================================================================
# 3. COMPATIBILIDAD RETROACTIVA CON ESCANDALLOS BÁSICOS
# ============================================================================


@router.post(
    "/api/v1/recipes/escandallos",
    response_model=EscandalloCostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_escandallo_endpoint(
    payload: EscandalloCreateRequest,
    _principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.escandallos.write"))],
) -> EscandalloCostResponse:
    """Registra una receta/escandallo y calcula recursivamente su costo por porción y Food Cost %."""
    domain_lines: list[DomainLegacyRecipeLine] = []
    for ln in payload.lines:
        if ln.ingredient_id is not None:
            _legacy_costing_service.set_ingredient_cost(ln.ingredient_id, ln.unit_cost)
        domain_lines.append(
            DomainLegacyRecipeLine(
                quantity=ln.quantity,
                ingredient_id=ln.ingredient_id,
                sub_recipe_id=ln.sub_recipe_id,
                waste_pct=ln.waste_pct,
            )
        )

    recipe = DomainLegacyRecipe(
        recipe_id=payload.recipe_id,
        lines=tuple(domain_lines),
        yield_portions=payload.yield_portions,
    )
    _legacy_costing_service.upsert_recipe(recipe)

    try:
        report = _legacy_costing_service.cost_report(payload.recipe_id, payload.net_price)
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
    _legacy_escandallos_store[payload.recipe_id] = resp
    return resp


@router.get(
    "/api/v1/recipes/escandallos",
    response_model=list[EscandalloCostResponse],
    status_code=status.HTTP_200_OK,
)
async def list_escandallos_endpoint(
    _principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.escandallos.read"))],
) -> list[EscandalloCostResponse]:
    """Lista los escandallos costeados del Tenant."""
    return list(_legacy_escandallos_store.values())


@router.post(
    "/api/v1/recipes/simulate-margin",
    response_model=MarginSimulationResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_margin_endpoint(
    payload: MarginSimulationRequest,
    _principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.margins.simulate"))],
) -> MarginSimulationResponse:
    """Simula Food Cost % y margen bruto en `Decimal` sin alterar las recetas persistidas."""
    return MarginSimulationResponse(
        portion_cost=payload.portion_cost,
        proposed_net_price=payload.proposed_net_price,
        food_cost_pct=legacy_food_cost_pct(payload.portion_cost, payload.proposed_net_price),
        margin_amount=legacy_margin_amount(payload.portion_cost, payload.proposed_net_price),
        margin_pct=legacy_margin_pct(payload.portion_cost, payload.proposed_net_price),
    )


# ============================================================================
# 4. FICHAS TÉCNICAS Y ESCANDALLOS DE RECETAS (`/api/v1/recipes`)
# ============================================================================


@router.get(
    "/api/v1/recipes",
    response_model=list[RecipeSummaryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_recipes_endpoint(
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.read"))],
    tipo: str | None = Query(default=None, description="Filtro de tipo: 'todas', 'estaticas', 'dinamicas', 'subrecetas'"),
    categoria_id: int | None = Query(default=None, description="Filtro por categoría"),
    search: str | None = Query(default=None, description="Búsqueda por nombre o código"),
) -> list[RecipeSummaryResponse]:
    """Lista las recetas del tenant con filtros por tipo gastronómico, categoría y búsqueda."""
    recipes = _recipe_service.list_recipes(
        tenant_id=principal.tenant_id,
        tipo=tipo,
        categoria_id=categoria_id,
        search=search,
    )
    return [_to_recipe_summary_response(r) for r in recipes]


@router.post(
    "/api/v1/recipes",
    response_model=RecipeDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipe_endpoint(
    payload: RecipeCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.write"))],
) -> RecipeDetailResponse:
    """Crea una receta gastronómica (estática o dinámica) con escandallo base y validación DAG."""
    ing_dtos = [
        RecipeIngredientDTO(
            producto_id=ing.producto_id,
            subreceta_id=ing.subreceta_id,
            cantidad_receta=ing.cantidad_receta,
            porcentaje_merma=ing.porcentaje_merma,
            bodega_consumo_id=ing.bodega_consumo_id,
            notas=ing.notas,
        )
        for ing in payload.ingredientes
    ]
    grp_links = [
        RecipeOptionGroupLinkDTO(
            grupo_id=link.grupo_id,
            orden=link.orden,
            es_requerido=link.es_requerido,
        )
        for link in payload.grupos_opciones
    ]
    created = _recipe_service.create_recipe(
        codigo=payload.codigo,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        categoria_receta_id=payload.categoria_receta_id,
        es_subreceta=payload.es_subreceta,
        es_dinamica=payload.es_dinamica,
        porciones_rendimiento=payload.porciones_rendimiento,
        precio_venta_neto=payload.precio_venta_neto,
        precio_venta_bruto=payload.precio_venta_bruto,
        iva_porcentaje=payload.iva_porcentaje,
        iva_incluido=payload.iva_incluido,
        imagen_url=payload.imagen_url,
        preparacion=payload.preparacion,
        video_url=payload.video_url,
        documento_url=payload.documento_url,
        tiempo_preparacion_minutos=payload.tiempo_preparacion_minutos,
        ingredientes=ing_dtos,
        grupos_opciones=grp_links,
        tenant_id=principal.tenant_id,
    )

    tree = _recipe_service.build_subrecipes_tree(created.id, principal.tenant_id)

    # Evento realtime
    await _publish_realtime_event(
        event_type="recipes.recipe.updated",
        principal=principal,
        required_permission="recipes.recipe.read",
        query_key="recipes",
        payload={"recipe_id": created.id, "action": "created"},
    )

    return _to_recipe_detail_response(created, tree)


@router.post(
    "/api/v1/recipes/{id}/simulate-cost",
    response_model=RecipeCostSimulationResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_recipe_cost_endpoint(
    id: int,
    payload: RecipeCostSimulationRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.costs"))],
) -> RecipeCostSimulationResponse:
    """Simula el costo de escandallo, recargos y margen ante una selección particular de opciones dinámicas."""
    sim_result: SimulationResult = _simulator_service.simulate_cost(
        recipe_id=id,
        selected_option_item_ids=payload.selected_option_item_ids,
        tenant_id=principal.tenant_id,
    )
    selected_res = [
        SimulatedOptionResponse(
            item_id=opt.item_id,
            grupo_id=opt.grupo_id,
            grupo_nombre=opt.grupo_nombre,
            nombre=opt.nombre,
            cantidad=opt.cantidad,
            costo_unitario=opt.costo_unitario,
            costo_total=opt.costo_total,
            recargo_precio=opt.recargo_precio,
        )
        for opt in sim_result.selected_options
    ]
    return RecipeCostSimulationResponse(
        recipe_id=sim_result.recipe_id,
        recipe_nombre=sim_result.recipe_nombre,
        base_fixed_cost=sim_result.base_fixed_cost,
        options_cost=sim_result.options_cost,
        total_cost=sim_result.total_cost,
        portion_cost=sim_result.portion_cost,
        total_surcharge=sim_result.total_surcharge,
        effective_net_price=sim_result.effective_net_price,
        effective_gross_price=sim_result.effective_gross_price,
        margin_amount=sim_result.margin_amount,
        margin_pct=sim_result.margin_pct,
        food_cost_pct=sim_result.food_cost_pct,
        selected_options=selected_res,
    )


@router.get(
    "/api/v1/recipes/{id}",
    response_model=RecipeDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recipe_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.read"))],
) -> RecipeDetailResponse:
    """Detalle completo de la receta con ingredientes fijos, grupos de opciones, escandallo y árbol de subrecetas."""
    recipe = _recipe_service.get_recipe(recipe_id=id, tenant_id=principal.tenant_id)
    tree = _recipe_service.build_subrecipes_tree(id, principal.tenant_id)
    return _to_recipe_detail_response(recipe, tree)


@router.get(
    "/api/v1/recipes/{id}/allergens",
    response_model=list[AllergenInfo],
    status_code=status.HTTP_200_OK,
)
async def get_recipe_allergens_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.read"))],
) -> list[AllergenInfo]:
    """Retorna la lista consolidada de alérgenos alimentarios normados presentes en la receta."""
    allergens = _recipe_service.get_recipe_allergens(recipe_id=id, tenant_id=principal.tenant_id)
    return [_to_allergen_info(a) for a in allergens]


@router.get(
    "/api/v1/recipes/{id}/kitchen-sheet",
    response_model=KitchenSheetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_kitchen_sheet_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.read"))],
    servings: Decimal | None = Query(
        default=None,
        description="Número de porciones solicitadas a escalar (estrictamente mayor a 0)",
        gt=Decimal("0"),
    ),
) -> KitchenSheetResponse:
    """Genera la ficha técnica de cocina escalada con porciones exactas, merma técnica y alérgenos."""
    sheet_dto = _recipe_service.generate_kitchen_sheet(
        recipe_id=id,
        servings=servings,
        tenant_id=principal.tenant_id,
    )
    return _to_kitchen_sheet_response(sheet_dto)


@router.put(
    "/api/v1/recipes/{id}",
    response_model=RecipeDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_recipe_endpoint(
    id: int,
    payload: RecipeUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.write"))],
) -> RecipeDetailResponse:
    """Actualiza una receta y recalcula recursivamente su escandallo."""
    ing_dtos = None
    if payload.ingredientes is not None:
        ing_dtos = [
            RecipeIngredientDTO(
                producto_id=ing.producto_id,
                subreceta_id=ing.subreceta_id,
                cantidad_receta=ing.cantidad_receta,
                porcentaje_merma=ing.porcentaje_merma,
                bodega_consumo_id=ing.bodega_consumo_id,
                notas=ing.notas,
            )
            for ing in payload.ingredientes
        ]

    grp_links = None
    if payload.grupos_opciones is not None:
        grp_links = [
            RecipeOptionGroupLinkDTO(
                grupo_id=link.grupo_id,
                orden=link.orden,
                es_requerido=link.es_requerido,
            )
            for link in payload.grupos_opciones
        ]

    updated = _recipe_service.update_recipe(
        recipe_id=id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        categoria_receta_id=payload.categoria_receta_id,
        es_subreceta=payload.es_subreceta,
        es_dinamica=payload.es_dinamica,
        porciones_rendimiento=payload.porciones_rendimiento,
        precio_venta_neto=payload.precio_venta_neto,
        precio_venta_bruto=payload.precio_venta_bruto,
        iva_porcentaje=payload.iva_porcentaje,
        iva_incluido=payload.iva_incluido,
        imagen_url=payload.imagen_url,
        preparacion=payload.preparacion,
        video_url=payload.video_url,
        documento_url=payload.documento_url,
        tiempo_preparacion_minutos=payload.tiempo_preparacion_minutos,
        ingredientes=ing_dtos,
        grupos_opciones=grp_links,
        tenant_id=principal.tenant_id,
    )

    tree = _recipe_service.build_subrecipes_tree(updated.id, principal.tenant_id)

    # Evento realtime
    await _publish_realtime_event(
        event_type="recipes.recipe.updated",
        principal=principal,
        required_permission="recipes.recipe.read",
        query_key="recipes",
        payload={"recipe_id": updated.id, "action": "updated"},
    )

    return _to_recipe_detail_response(updated, tree)


@router.delete(
    "/api/v1/recipes/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recipe_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.recipe.delete"))],
) -> None:
    """Soft-delete de receta con verificación de uso en subrecetas dependientes o combos."""
    _recipe_service.delete_recipe(recipe_id=id, tenant_id=principal.tenant_id)

    # Evento realtime
    await _publish_realtime_event(
        event_type="recipes.recipe.updated",
        principal=principal,
        required_permission="recipes.recipe.read",
        query_key="recipes",
        payload={"recipe_id": id, "action": "deleted"},
    )


# ============================================================================
# 5. CATEGORÍAS DE COMBOS (`/api/v1/combos/categories`)
# ============================================================================


@router.get(
    "/api/v1/combos/categories",
    response_model=list[ComboCategoryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_combo_categories_endpoint(
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.read"))],
) -> list[ComboCategoryResponse]:
    """Lista las categorías clasificatorias de combos del tenant."""
    cats = _combo_service.list_categories(tenant_id=principal.tenant_id)
    return [
        ComboCategoryResponse(
            id=c.id,
            nombre=c.nombre,
            color=c.color,
            icono=c.icono,
            orden=c.orden,
        )
        for c in cats
    ]


@router.post(
    "/api/v1/combos/categories",
    response_model=ComboCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_combo_category_endpoint(
    payload: ComboCategoryCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.write"))],
) -> ComboCategoryResponse:
    """Crea una nueva categoría de combos."""
    c = _combo_service.create_category(
        nombre=payload.nombre,
        color=payload.color,
        icono=payload.icono,
        orden=payload.orden,
        tenant_id=principal.tenant_id,
    )
    return ComboCategoryResponse(
        id=c.id,
        nombre=c.nombre,
        color=c.color,
        icono=c.icono,
        orden=c.orden,
    )


# ============================================================================
# 6. COMBOS PROMOCIONALES (`/api/v1/combos`)
# ============================================================================


@router.get(
    "/api/v1/combos",
    response_model=list[ComboSummaryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_combos_endpoint(
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.read"))],
    categoria_id: int | None = Query(default=None, description="Filtro por categoría de combo"),
    search: str | None = Query(default=None, description="Búsqueda por nombre o código"),
) -> list[ComboSummaryResponse]:
    """Lista combos comerciales con estado de disponibilidad de inventario."""
    combos = _combo_service.list_combos(
        tenant_id=principal.tenant_id,
        categoria_id=categoria_id,
        search=search,
    )
    return [_to_combo_summary_response(c) for c in combos]


@router.post(
    "/api/v1/combos",
    response_model=ComboDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_combo_endpoint(
    payload: ComboCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.write"))],
) -> ComboDetailResponse:
    """Crea un nuevo combo promocional (fijo o dinámico)."""
    items_dtos = [
        ComboItemDTO(
            producto_id=it.producto_id,
            receta_id=it.receta_id,
            cantidad=it.cantidad,
        )
        for it in payload.items
    ]
    grp_links = [
        ComboOptionGroupLinkDTO(
            grupo_id=link.grupo_id,
            orden=link.orden,
            es_requerido=link.es_requerido,
        )
        for link in payload.grupos_opciones
    ]
    created = _combo_service.create_combo(
        nombre=payload.nombre,
        codigo=payload.codigo,
        descripcion=payload.descripcion,
        categoria_combo_id=payload.categoria_combo_id,
        es_dinamico=payload.es_dinamico,
        precio_venta_neto=payload.precio_venta_neto,
        precio_venta_bruto=payload.precio_venta_bruto,
        iva_porcentaje=payload.iva_porcentaje,
        iva_incluido=payload.iva_incluido,
        imagen_url=payload.imagen_url,
        items=items_dtos,
        grupos_opciones=grp_links,
        tenant_id=principal.tenant_id,
    )

    # Evento realtime
    await _publish_realtime_event(
        event_type="recipes.combo.updated",
        principal=principal,
        required_permission="recipes.combo.read",
        query_key="combos",
        payload={"combo_id": created.id, "action": "created"},
    )

    return _to_combo_detail_response(created)


@router.get(
    "/api/v1/combos/{id}",
    response_model=ComboDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_combo_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.read"))],
) -> ComboDetailResponse:
    """Detalle completo de combo (componentes fijos + grupos de opciones)."""
    combo = _combo_service.get_combo(combo_id=id, tenant_id=principal.tenant_id)
    return _to_combo_detail_response(combo)


@router.put(
    "/api/v1/combos/{id}",
    response_model=ComboDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_combo_endpoint(
    id: int,
    payload: ComboUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.write"))],
) -> ComboDetailResponse:
    """Actualiza configuración y componentes de un combo."""
    items_dtos = None
    if payload.items is not None:
        items_dtos = [
            ComboItemDTO(
                producto_id=it.producto_id,
                receta_id=it.receta_id,
                cantidad=it.cantidad,
            )
            for it in payload.items
        ]

    grp_links = None
    if payload.grupos_opciones is not None:
        grp_links = [
            ComboOptionGroupLinkDTO(
                grupo_id=link.grupo_id,
                orden=link.orden,
                es_requerido=link.es_requerido,
            )
            for link in payload.grupos_opciones
        ]

    updated = _combo_service.update_combo(
        combo_id=id,
        nombre=payload.nombre,
        codigo=payload.codigo,
        descripcion=payload.descripcion,
        categoria_combo_id=payload.categoria_combo_id,
        es_dinamico=payload.es_dinamico,
        precio_venta_neto=payload.precio_venta_neto,
        precio_venta_bruto=payload.precio_venta_bruto,
        iva_porcentaje=payload.iva_porcentaje,
        iva_incluido=payload.iva_incluido,
        imagen_url=payload.imagen_url,
        items=items_dtos,
        grupos_opciones=grp_links,
        tenant_id=principal.tenant_id,
    )

    # Evento realtime
    await _publish_realtime_event(
        event_type="recipes.combo.updated",
        principal=principal,
        required_permission="recipes.combo.read",
        query_key="combos",
        payload={"combo_id": updated.id, "action": "updated"},
    )

    return _to_combo_detail_response(updated)


@router.delete(
    "/api/v1/combos/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_combo_endpoint(
    id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireTenantPermission("recipes.combo.delete"))],
) -> None:
    """Soft-delete de combo."""
    _combo_service.delete_combo(combo_id=id, tenant_id=principal.tenant_id)

    # Evento realtime
    await _publish_realtime_event(
        event_type="recipes.combo.updated",
        principal=principal,
        required_permission="recipes.combo.read",
        query_key="combos",
        payload={"combo_id": id, "action": "deleted"},
    )
