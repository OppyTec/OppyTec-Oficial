"""
oppytec-backend/src/modules/oppy_ai/presentation/router.py
Endpoints REST del Asistente `OppyFy` (RAG 3-Capas, RBAC propio editable, Billetera de Créditos,
Traspaso de Hilo al 5%, Operational Tools, Platform Admin FinOps y Paquetes de Créditos IA):
- `POST /api/v1/oppyfy/chat`
- `POST /api/v1/oppyfy/threads/{thread_id}/rollover`
- `GET /api/v1/oppyfy/rbac/domains` y `POST /api/v1/oppyfy/rbac/domains`
- `POST /api/v1/oppyfy/rbac/grants`
- `GET /api/v1/oppyfy/wallets/me` y `PATCH /api/v1/oppyfy/wallets/{user_id}`
- `GET /api/v1/oppyfy/credits/wallet` (alias retrocompatible)
- `GET /api/v1/oppyfy/telemetry/logs`
- `GET /api/v1/platform-admin/token-consumption`
- `GET /api/v1/platform-admin/ai-packs` y `POST /api/v1/platform-admin/ai-packs`
- `GET /api/v1/platform-admin/ai-packs/{pack_id}/quote`
- `GET /api/v1/platform-admin/ai-tariffs` y `PUT /api/v1/platform-admin/ai-tariffs/{model_slug}`
- `GET /api/v1/platform-admin/ai-models` y `POST /api/v1/platform-admin/ai-models`
- `GET /api/v1/platform-admin/ai-models/{model_slug}`
- `PUT /api/v1/platform-admin/ai-models/{model_slug}`
- `DELETE /api/v1/platform-admin/ai-models/{model_slug}`
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from src.adapters.ai.gemini_adapter import MeteredGeminiAdapter
from src.adapters.ai.jev_adapter import InMemoryTelemetrySink, MeteredJevAdapter
from src.core.exceptions import OppyTecError
from src.core.guards.rate_limiter import RateLimitCheckResult, RequireRateLimit
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
    RequireTenantPermission,
)
from src.core.observability import trace_span
from src.modules.oppy_ai.application.ai_credit_packs_service import (
    AiCreditPacksService,
    CreditPackDTO,
)
from src.modules.oppy_ai.application.ai_model_catalog_service import (
    AiModelCatalogService,
)
from src.modules.oppy_ai.infrastructure.models import AiModelConfig
from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    ModelConfigRegistry,
    OppyfyQueryRequest,
)
from src.modules.oppy_ai.application.rag_service import (
    BusinessSpecChunkRecord,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.token_consumption_service import (
    TokenConsumptionAggregatorService,
)
from src.modules.oppy_ai.application.tool_router import (
    HardCodedToolCode,
    OppyfyToolRouter,
)
from src.modules.oppy_ai.domain.context_meter import (
    compact_thread_for_fresh_handover,
    evaluate_context_usage,
)
from src.modules.oppy_ai.domain.credit_wallet import (
    WorkerCreditWalletState,
    deduct_worker_credits,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    ALLOWED_PROMPT_STATUS,
    BLOCKED_UNAUTHORIZED_PROMPT,
    OppyfyPermissionGrantSpec,
    evaluate_oppyfy_subdomain_access,
    validate_hierarchical_delegation,
)
from src.infrastructure.ai.langfuse_tracer import LangfuseTracer
from src.modules.oppy_ai.domain.evals import AIChatFeedback, InvalidFeedbackPayloadError
from src.modules.oppy_ai.infrastructure.repositories import (
    InMemoryAIChatFeedbackRepository,
)
from src.modules.oppy_ai.presentation.schemas import (
    AIChatFeedbackCreateRequest,
    AIChatFeedbackListResponse,
    AIChatFeedbackResponse,
    AiCreditPackCreateRequest,
    AiCreditPackQuoteResponse,
    AiCreditPackResponse,
    AiModelConfigCreateRequest,
    AiModelConfigListResponse,
    AiModelConfigResponse,
    AiModelConfigUpdateRequest,
    AiModelDeleteResponse,
    AiModelTariffResponse,
    AiModelTariffUpdateRequest,
    OppyfyChatRequest,
    OppyfyChatResponse,
    OppyfyDomainCreateRequest,
    OppyfyDomainItemResponse,
    OppyfyDomainTreeResponse,
    OppyfyGrantCreateRequest,
    OppyfyGrantResponse,
    OppyfySubdomainDetailResponse,
    OppyfyTelemetryLogItemResponse,
    OppyfyThreadRolloverRequest,
    OppyfyThreadRolloverResponse,
    OppyfyWalletPatchRequest,
    OppyfyWalletResponse,
)

router = APIRouter(tags=["oppyfy"])

# ============================================================================
# SINGLETON APPLICATION SERVICES FOR OPPYFY
# ============================================================================

_telemetry_sink = InMemoryTelemetrySink()
_jev_adapter = MeteredJevAdapter(telemetry_sink=_telemetry_sink)
_gemini_adapter = MeteredGeminiAdapter(telemetry_sink=_telemetry_sink)
_tool_router = OppyfyToolRouter(_jev_adapter)
_rag_service = ThreeLayerRagService(
    business_spec_chunks=[
        BusinessSpecChunkRecord(
            chunk_id=uuid.uuid4(),
            spec_rel_path="specs/business-domain/recipes/costing_and_waste.md",
            module_slug="recipes",
            content_markdown="Regla OppyTec: El Food Cost real incluye mermas registradas y deducciones de stock.",
        ),
        BusinessSpecChunkRecord(
            chunk_id=uuid.uuid4(),
            spec_rel_path="specs/business-domain/inventory/fefo_rules.md",
            module_slug="inventory",
            content_markdown="Regla OppyTec: Lotes deben rotar por FEFO. Insumos perecibles con menos de 3 días tienen prioridad crítica.",
        ),
    ]
)
_model_registry = ModelConfigRegistry()
_langfuse_tracer = LangfuseTracer()
_feedback_repository = InMemoryAIChatFeedbackRepository()
_metered_ai_service = MeteredAIService(
    jev_port=_jev_adapter,
    llm_port=_gemini_adapter,
    rag_service=_rag_service,
    tool_router=_tool_router,
    model_registry=_model_registry,
    telemetry_sink=_telemetry_sink,
    tracer=_langfuse_tracer,
)
_token_consumption_service = TokenConsumptionAggregatorService()
_ai_credit_packs_service = AiCreditPacksService()
_ai_model_catalog_service = AiModelCatalogService(model_registry=_model_registry)

_worker_wallets_store: dict[int, WorkerCreditWalletState] = {
    1: WorkerCreditWalletState(
        user_id=1,
        allocated_credits=Decimal("100.00"),
        consumed_credits=Decimal("12.50"),
        is_oppyfy_enabled=True,
    ),
    101: WorkerCreditWalletState(
        user_id=101,
        allocated_credits=Decimal("50.00"),
        consumed_credits=Decimal("5.00"),
        is_oppyfy_enabled=True,
    ),
}

_permission_grants_store: list[OppyfyPermissionGrantSpec] = []
_domain_tree_store: list[OppyfyDomainTreeResponse] = [
    OppyfyDomainTreeResponse(
        id=1,
        domain_key="gastronomia",
        name_es="Gastronomía y Cocina",
        name_en="Kitchen & Gastronomy",
        icon="ChefHat",
        is_active=True,
        sort_order=1,
        subdomains=[
            OppyfySubdomainDetailResponse(
                id=1,
                subdomain_key="recipes_kitchen",
                name_es="Recetas y Cocina",
                name_en="Recipes & Kitchen",
                allowed_tool_functions=["query_recipe_costs", "get_sales_and_food_cost_variance"],
                can_view_costs_default=True,
                is_active=True,
            )
        ],
    ),
    OppyfyDomainTreeResponse(
        id=2,
        domain_key="bodega",
        name_es="Inventario y Bodegas",
        name_en="Inventory & Warehouses",
        icon="Boxes",
        is_active=True,
        sort_order=2,
        subdomains=[
            OppyfySubdomainDetailResponse(
                id=2,
                subdomain_key="inventory_stock",
                name_es="Stock e Inventario",
                name_en="Stock & Inventory",
                allowed_tool_functions=["get_stock_health_and_reorder_alerts", "get_expiring_batches_fefo"],
                can_view_costs_default=False,
                is_active=True,
            )
        ],
    ),
    OppyfyDomainTreeResponse(
        id=3,
        domain_key="abastecimiento",
        name_es="Abastecimiento y Proveedores",
        name_en="Procurement & Suppliers",
        icon="Truck",
        is_active=True,
        sort_order=3,
        subdomains=[
            OppyfySubdomainDetailResponse(
                id=3,
                subdomain_key="abastecimiento_y_eventos",
                name_es="Abastecimiento y Eventos",
                name_en="Supply & Events",
                allowed_tool_functions=[
                    "evaluate_supplier_lead_times_and_price_drift",
                    "build_optimal_purchase_order_draft",
                    "analyze_event_supply_feasibility",
                ],
                can_view_costs_default=False,
                is_active=True,
            )
        ],
    ),
    OppyfyDomainTreeResponse(
        id=4,
        domain_key="proyeccion",
        name_es="Proyección y Quiebres de Stock",
        name_en="Projection & Stockouts",
        icon="TrendingUp",
        is_active=True,
        sort_order=4,
        subdomains=[
            OppyfySubdomainDetailResponse(
                id=4,
                subdomain_key="proyeccion_y_quiebres",
                name_es="Proyección y Quiebres",
                name_en="Projections & Stockouts",
                allowed_tool_functions=[
                    "get_stockout_projections_and_autonomy",
                    "get_preventive_transfer_recommendations",
                ],
                can_view_costs_default=False,
                is_active=True,
            )
        ],
    ),
]


# ============================================================================
# 1. CHAT & OPERATIONAL TOOLS ENDPOINTS
# ============================================================================


@router.post(
    "/api/v1/oppyfy/chat",
    response_model=OppyfyChatResponse,
    status_code=status.HTTP_200_OK,
)
async def oppyfy_chat_endpoint(
    payload: OppyfyChatRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.assistant.chat")),
    ],
    _rate_limit: Annotated[RateLimitCheckResult, Depends(RequireRateLimit("ai"))],
) -> OppyfyChatResponse:
    """Procesa una consulta a `OppyFy` validando créditos, RBAC propio editable y ventana de contexto."""
    user_id = principal.user_id
    wallet = _worker_wallets_store.get(
        user_id,
        WorkerCreditWalletState(
            user_id=user_id,
            allocated_credits=payload.remaining_credits,
            consumed_credits=Decimal("0.00"),
            is_oppyfy_enabled=True,
        ),
    )

    # Buscar concesiones aplicables para el subdominio consultado
    user_grants = [g for g in _permission_grants_store if g.user_id == user_id]
    if not user_grants:
        slugs = {
            payload.target_subdomain_slug,
            "inventory_stock",
            "inventario_y_bodegas",
            "recipes_kitchen",
            "recetas_y_cocina",
            "abastecimiento_y_eventos",
            "finanzas_y_rentabilidad",
            "analitica_y_reportes",
            "proyeccion_y_quiebres",
        }
        user_grants = [
            OppyfyPermissionGrantSpec(
                grant_id=uuid.uuid4(),
                subdomain_id=idx + 1,
                subdomain_slug=s,
                user_id=user_id,
                effect="ALLOW",
                can_view_costs=payload.can_view_costs,
            )
            for idx, s in enumerate(slugs)
        ]

    subdomain_id_map = {g.subdomain_slug: g.subdomain_id for g in user_grants}
    subdomain_id_map[payload.target_subdomain_slug] = 1

    tenant_schema = principal.tenant_id or "tenant_demo"
    try:
        req_holding_id = uuid.UUID(principal.holding_id) if principal.holding_id else uuid.UUID("11111111-1111-1111-1111-111111111111")
    except ValueError:
        req_holding_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    try:
        req_tenant_id = uuid.UUID(principal.tenant_id) if principal.tenant_id else uuid.UUID("22222222-2222-2222-2222-222222222222")
    except ValueError:
        req_tenant_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    query_req = OppyfyQueryRequest(
        holding_id=req_holding_id,
        tenant_id=req_tenant_id,
        tenant_schema=tenant_schema,
        user_id=user_id,
        role_ids=(1,),
        hierarchy_rank=principal.hierarchy_rank,
        prompt_text=payload.prompt_text,
        wallet=wallet,
        grants=tuple(user_grants),
        subdomain_id_by_slug=subdomain_id_map,
        thread_id=payload.thread_id or uuid.uuid4(),
        prior_thread_tokens=payload.prior_thread_tokens,
        estimated_credit_cost=payload.estimated_credit_cost,
    )

    query_res = _metered_ai_service.execute_oppyfy_query(query_req)
    _worker_wallets_store[user_id] = query_res.updated_wallet

    # Si se ejecutó una herramienta determinista, adjuntar el payload saneado
    tool_name = query_res.routed_tool
    tool_payload = query_res.tool_execution.sanitized_payload if query_res.tool_execution else None

    # Registrar en el agregador FinOps
    if query_res.llm_usage_records:
        total_in = sum(rec.input_tokens for rec in query_res.llm_usage_records)
        total_out = sum(rec.output_tokens for rec in query_res.llm_usage_records)
        _token_consumption_service.record_log(
            holding_id=str(query_req.holding_id),
            holding_name="Holding Principal Demo",
            tenant_id=str(query_req.tenant_id),
            tenant_name="Sucursal Principal",
            user_id=user_id,
            user_name="Usuario Activo",
            caller_feature="oppyfy_chat",
            model_name="gemini-2.5-flash",
            input_tokens=total_in,
            output_tokens=total_out,
            credits_deducted=query_res.credits_deducted,
            api_success=query_res.allowed,
        )

    return OppyfyChatResponse(
        allowed=query_res.allowed,
        status_code=query_res.status_code,
        subdomain_slug=query_res.subdomain_slug,
        answer_text=query_res.answer_text,
        credits_deducted=query_res.credits_deducted,
        remaining_credits=query_res.updated_wallet.remaining_credits,
        context_usage_percent=query_res.context_health.context_usage_percent,
        requires_new_thread=query_res.context_health.requires_auto_compaction,
        tool_executed=tool_name,
        tool_payload=tool_payload,
        trace_id=query_res.trace_id,
        message_id=query_res.message_id,
    )


# ============================================================================
# 2. THREAD ROLLOVER
# ============================================================================


@router.post(
    "/api/v1/oppyfy/threads/{thread_id}/rollover",
    response_model=OppyfyThreadRolloverResponse,
    status_code=status.HTTP_200_OK,
)
async def oppyfy_thread_rollover_endpoint(
    thread_id: uuid.UUID,
    payload: OppyfyThreadRolloverRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.assistant.chat")),
    ],
) -> OppyfyThreadRolloverResponse:
    """Ejecuta un rollover estructurado hacia un nuevo hilo fresco al 5% de contexto."""
    handover = compact_thread_for_fresh_handover(
        source_thread_id=thread_id,
        messages=[payload.summary_notes] if payload.summary_notes else ["Continuación fluida de conversación."],
    )
    return OppyfyThreadRolloverResponse(
        new_thread_id=handover.new_thread_id,
        previous_thread_id=handover.source_thread_id,
        fresh_context_usage_percent=handover.new_context_usage_percent,
        summary_artifact=handover.synthesized_summary,
        message="Hilo traspasado exitosamente al 5.00% de contexto.",
    )


# ============================================================================
# 3. RBAC DOMAINS TREE & GRANTS
# ============================================================================


@router.get(
    "/api/v1/oppyfy/rbac/domains",
    response_model=list[OppyfyDomainTreeResponse],
    status_code=status.HTTP_200_OK,
)
async def list_oppyfy_rbac_domains_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.rbac_domains.read")),
    ],
) -> list[OppyfyDomainTreeResponse]:
    """Devuelve el árbol jerárquico de dominios y sub-dominios editables de `OppyFy`."""
    return list(_domain_tree_store)


@router.post(
    "/api/v1/oppyfy/rbac/domains",
    response_model=OppyfyDomainTreeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_oppyfy_rbac_domain_endpoint(
    payload: OppyfyDomainCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.rbac_domains.write")),
    ],
) -> OppyfyDomainTreeResponse:
    """Crea o actualiza un dominio con sus subdominios para el tenant."""
    new_domain_id = max((d.id for d in _domain_tree_store), default=0) + 1
    subdomains_detail = [
        OppyfySubdomainDetailResponse(
            id=idx + 10,
            subdomain_key=sub.subdomain_key,
            name_es=sub.name_es,
            name_en=sub.name_en,
            allowed_tool_functions=sub.allowed_tool_functions,
            can_view_costs_default=sub.can_view_costs_default,
            is_active=sub.is_active,
        )
        for idx, sub in enumerate(payload.subdomains)
    ]
    created = OppyfyDomainTreeResponse(
        id=new_domain_id,
        domain_key=payload.domain_key,
        name_es=payload.name_es,
        name_en=payload.name_en,
        icon=payload.icon,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
        subdomains=subdomains_detail,
    )
    _domain_tree_store.append(created)
    return created


@router.post(
    "/api/v1/oppyfy/rbac/grants",
    response_model=OppyfyGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_oppyfy_permission_grant_endpoint(
    payload: OppyfyGrantCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.rbac_grants.write")),
    ],
) -> OppyfyGrantResponse:
    """Otorga un permiso temporal o permanente a un trabajador validando delegación jerárquica."""
    # Validación de delegación jerárquica (Rank 0 o superior al destinatario)
    if not validate_hierarchical_delegation(
        grantor_rank=principal.hierarchy_rank,
        grantee_rank=1,
        grantor_has_subdomain_permission=True,
    ):
        raise OppyTecError(
            "Hierarchical delegation error: You cannot grant permissions exceeding your hierarchy rank.",
            status_code=403,
            error_code="OPPYFY_DELEGATION_FORBIDDEN",
        )

    grant = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=payload.subdomain_id,
        subdomain_slug=payload.subdomain_slug,
        user_id=payload.user_id,
        can_query=payload.can_query,
        can_view_costs=payload.can_view_costs,
        expires_at=payload.expires_at,
        max_prompts=payload.max_prompts,
        temp_credit_ceiling=payload.temp_credit_ceiling,
    )
    _permission_grants_store.append(grant)

    return OppyfyGrantResponse(
        grant_id=grant.grant_id,
        user_id=grant.user_id or payload.user_id,
        subdomain_id=grant.subdomain_id,
        subdomain_slug=grant.subdomain_slug,
        can_query=grant.can_query,
        can_view_costs=grant.can_view_costs,
        expires_at=grant.expires_at,
        max_prompts=grant.max_prompts,
        temp_credit_ceiling=grant.temp_credit_ceiling,
        is_active=True,
    )


# ============================================================================
# 4. WORKER WALLETS ENDPOINTS
# ============================================================================


@router.get(
    "/api/v1/oppyfy/wallets/me",
    response_model=OppyfyWalletResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_oppyfy_wallet_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.credits.read")),
    ],
) -> OppyfyWalletResponse:
    """Consulta la billetera de créditos sin caducidad del trabajador autenticado."""
    wallet = _worker_wallets_store.get(
        principal.user_id,
        WorkerCreditWalletState(
            user_id=principal.user_id,
            allocated_credits=Decimal("100.00"),
            consumed_credits=Decimal("12.50"),
            is_oppyfy_enabled=True,
        ),
    )
    return OppyfyWalletResponse(
        user_id=wallet.user_id,
        is_oppyfy_enabled=wallet.is_oppyfy_enabled,
        assigned_credits_balance=wallet.allocated_credits,
        consumed_credits_total=wallet.consumed_credits,
        remaining_credits=wallet.remaining_credits,
    )


@router.get(
    "/api/v1/oppyfy/credits/wallet",
    response_model=OppyfyWalletResponse,
    status_code=status.HTTP_200_OK,
)
async def get_oppyfy_credit_wallet_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.credits.read")),
    ],
) -> OppyfyWalletResponse:
    """Alias retrocompatible para consultar la billetera de créditos."""
    return await get_my_oppyfy_wallet_endpoint(principal)


@router.patch(
    "/api/v1/oppyfy/wallets/{user_id}",
    response_model=OppyfyWalletResponse,
    status_code=status.HTTP_200_OK,
)
async def update_worker_credit_wallet_endpoint(
    user_id: int,
    payload: OppyfyWalletPatchRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.credits.manage")),
    ],
) -> OppyfyWalletResponse:
    """Ajusta el cupo asignado y activación de OppyFy para un trabajador."""
    current = _worker_wallets_store.get(
        user_id,
        WorkerCreditWalletState(
            user_id=user_id,
            allocated_credits=Decimal("50.00"),
            consumed_credits=Decimal("0.00"),
            is_oppyfy_enabled=True,
        ),
    )
    new_allocated = (
        payload.assigned_credit_ceiling
        if payload.assigned_credit_ceiling is not None
        else current.allocated_credits
    )
    new_enabled = (
        payload.is_oppyfy_enabled
        if payload.is_oppyfy_enabled is not None
        else current.is_oppyfy_enabled
    )
    updated = WorkerCreditWalletState(
        user_id=user_id,
        allocated_credits=new_allocated,
        consumed_credits=current.consumed_credits,
        is_oppyfy_enabled=new_enabled,
    )
    _worker_wallets_store[user_id] = updated

    return OppyfyWalletResponse(
        user_id=updated.user_id,
        is_oppyfy_enabled=updated.is_oppyfy_enabled,
        assigned_credits_balance=updated.allocated_credits,
        consumed_credits_total=updated.consumed_credits,
        remaining_credits=updated.remaining_credits,
    )


# ============================================================================
# 5. PLATFORM ADMIN: AI PACKS & TOKEN CONSUMPTION
# ============================================================================


@router.get(
    "/api/v1/platform-admin/ai-packs",
    response_model=list[AiCreditPackResponse],
    status_code=status.HTTP_200_OK,
)
async def list_ai_credit_packs_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_packs.read")),
    ],
    is_active_only: bool = Query(default=False),
) -> list[AiCreditPackResponse]:
    """Lista todos los paquetes de créditos IA independientes para Add-On."""
    packs = _ai_credit_packs_service.list_packs(is_active_only=is_active_only)
    return [
        AiCreditPackResponse(
            id=p.id,
            pack_name=p.pack_name,
            credits_amount=p.credits_amount,
            bonus_credits=p.bonus_credits,
            total_credits=p.total_credits,
            price_clp=p.price_clp,
            price_usd=p.price_usd,
            is_popular=p.is_popular,
            is_active=p.is_active,
            sort_order=p.sort_order,
            plan_tier_discounts=p.plan_tier_discounts,
        )
        for p in packs
    ]


@router.post(
    "/api/v1/platform-admin/ai-packs",
    response_model=AiCreditPackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_credit_pack_endpoint(
    payload: AiCreditPackCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_packs.write")),
    ],
) -> AiCreditPackResponse:
    """Crea un nuevo paquete de créditos IA en Platform Admin."""
    p = _ai_credit_packs_service.create_pack(
        pack_name=payload.pack_name,
        credits_amount=payload.credits_amount,
        price_clp=payload.price_clp,
        price_usd=payload.price_usd,
        bonus_credits=payload.bonus_credits,
        is_popular=payload.is_popular,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
        plan_tier_discounts=payload.plan_tier_discounts,
    )
    return AiCreditPackResponse(
        id=p.id,
        pack_name=p.pack_name,
        credits_amount=p.credits_amount,
        bonus_credits=p.bonus_credits,
        total_credits=p.total_credits,
        price_clp=p.price_clp,
        price_usd=p.price_usd,
        is_popular=p.is_popular,
        is_active=p.is_active,
        sort_order=p.sort_order,
        plan_tier_discounts=p.plan_tier_discounts,
    )


@router.get(
    "/api/v1/platform-admin/ai-packs/{pack_id}/quote",
    response_model=AiCreditPackQuoteResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ai_credit_pack_quote_endpoint(
    pack_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_packs.read")),
    ],
    base_plan_tier: str | None = Query(default=None),
) -> AiCreditPackQuoteResponse:
    """Calcula una cotización comercial de paquete con descuentos de plan SaaS aplicados."""
    quote = _ai_credit_packs_service.calculate_quote(pack_id, base_plan_tier=base_plan_tier)
    return AiCreditPackQuoteResponse(
        pack_id=quote.pack_id,
        pack_name=quote.pack_name,
        base_plan_tier=quote.base_plan_tier,
        original_price_usd=quote.original_price_usd,
        original_price_clp=quote.original_price_clp,
        discount_pct=quote.discount_pct,
        final_price_usd=quote.final_price_usd,
        final_price_clp=quote.final_price_clp,
        total_credits=quote.total_credits,
    )


@router.get(
    "/api/v1/oppyfy/telemetry/logs",
    response_model=list[OppyfyTelemetryLogItemResponse],
    status_code=status.HTTP_200_OK,
)
async def list_oppyfy_telemetry_logs_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("oppyfy.telemetry.read")),
    ],
) -> list[OppyfyTelemetryLogItemResponse]:
    """Lista la bitácora global de consumo de tokens y costos (`public.llm_request_logs`)."""
    logs = _metered_ai_service.emitted_usage_records
    return [
        OppyfyTelemetryLogItemResponse(
            request_id=str(log.thread_id or uuid.uuid4()),
            caller_feature=log.caller_feature,
            model_name=log.model_name,
            total_tokens=log.total_tokens,
            estimated_cost_usd=log.provider_cost_usd,
            credits_deducted=log.credits_deducted,
        )
        for log in logs
    ]


# ============================================================================
# 8. PLATFORM ADMIN: AI MODEL TARIFFS
# ============================================================================


@router.get(
    "/api/v1/platform-admin/ai-tariffs",
    response_model=list[AiModelTariffResponse],
    status_code=status.HTTP_200_OK,
)
async def list_ai_model_tariffs_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_tariffs.read")),
    ],
) -> list[AiModelTariffResponse]:
    """Lista las tarifas de modelos de IA vigentes configuradas en Platform Admin."""
    tariffs = _model_registry.list_tariffs()
    return [
        AiModelTariffResponse(
            model_slug=t.model_slug,
            engine_tier=t.engine_tier,
            input_cost_per_1m_usd=t.input_cost_per_1m_usd,
            cached_cost_per_1m_usd=t.cached_cost_per_1m_usd,
            output_cost_per_1m_usd=t.output_cost_per_1m_usd,
            embedding_cost_per_1m_usd=t.embedding_cost_per_1m_usd,
            is_enabled=t.is_enabled,
        )
        for t in tariffs
    ]


@router.put(
    "/api/v1/platform-admin/ai-tariffs/{model_slug}",
    response_model=AiModelTariffResponse,
    status_code=status.HTTP_200_OK,
)
async def update_ai_model_tariff_endpoint(
    model_slug: str,
    payload: AiModelTariffUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_tariffs.manage")),
    ],
) -> AiModelTariffResponse:
    """Actualiza dinámicamente la tarifa de un modelo de IA en Platform Admin."""
    updated = _model_registry.update_tariff(
        model_slug=model_slug,
        engine_tier=payload.engine_tier,
        input_cost_per_1m_usd=payload.input_cost_per_1m_usd,
        cached_cost_per_1m_usd=payload.cached_cost_per_1m_usd,
        output_cost_per_1m_usd=payload.output_cost_per_1m_usd,
        embedding_cost_per_1m_usd=payload.embedding_cost_per_1m_usd,
        is_enabled=payload.is_enabled,
    )
    return AiModelTariffResponse(
        model_slug=updated.model_slug,
        engine_tier=updated.engine_tier,
        input_cost_per_1m_usd=updated.input_cost_per_1m_usd,
        cached_cost_per_1m_usd=updated.cached_cost_per_1m_usd,
        output_cost_per_1m_usd=updated.output_cost_per_1m_usd,
        embedding_cost_per_1m_usd=updated.embedding_cost_per_1m_usd,
        is_enabled=updated.is_enabled,
    )


# ============================================================================
# 9. PLATFORM ADMIN: AI MODEL CATALOG & JEV ENGINES
# ============================================================================


def _map_ai_model_config(m: AiModelConfig) -> AiModelConfigResponse:
    """Mapea la entidad de configuración a esquema Pydantic V2 sin tipos float."""
    return AiModelConfigResponse(
        id=m.id,
        model_slug=m.model_slug,
        display_name=m.display_name,
        provider=m.provider,
        engine_tier=m.engine_tier,
        input_cost_per_1m_usd=m.input_cost_per_1m_usd,
        cached_cost_per_1m_usd=m.cached_cost_per_1m_usd,
        output_cost_per_1m_usd=m.output_cost_per_1m_usd,
        embedding_cost_per_1m_usd=m.embedding_cost_per_1m_usd,
        latency_p95_ms=m.latency_p95_ms,
        min_confidence_score=m.min_confidence_score,
        max_context_tokens=m.max_context_tokens,
        is_enabled=m.is_enabled,
        is_default=m.is_default,
        is_fallback=m.is_fallback,
        description=m.description or "",
        is_deleted=m.is_deleted,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.get(
    "/api/v1/platform-admin/ai-models",
    response_model=list[AiModelConfigResponse],
    status_code=status.HTTP_200_OK,
)
async def list_ai_models_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_models.read")),
    ],
    engine_tier: str | None = Query(default=None),
    is_enabled: bool | None = Query(default=None),
    provider: str | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> list[AiModelConfigResponse]:
    """Lista todos los modelos cognitivos y motores JEV del catálogo global."""
    with trace_span(
        "platform_admin.ai_models.list",
        attributes={
            "filter.engine_tier": engine_tier or "ALL",
            "filter.is_enabled": str(is_enabled) if is_enabled is not None else "ALL",
            "filter.provider": provider or "ALL",
        },
    ):
        models = _ai_model_catalog_service.list_models(
            include_deleted=include_deleted,
            tier=engine_tier,
            is_enabled=is_enabled,
            provider=provider,
        )
        return [_map_ai_model_config(m) for m in models]


@router.get(
    "/api/v1/platform-admin/ai-models/{model_slug}",
    response_model=AiModelConfigResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ai_model_endpoint(
    model_slug: str,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_models.read")),
    ],
) -> AiModelConfigResponse:
    """Obtiene la configuración y cotas de un modelo de IA específico."""
    with trace_span(
        "platform_admin.ai_models.get",
        attributes={"model_slug": model_slug},
    ):
        model = _ai_model_catalog_service.get_model_by_slug(model_slug)
        return _map_ai_model_config(model)


@router.post(
    "/api/v1/platform-admin/ai-models",
    response_model=AiModelConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_model_endpoint(
    payload: AiModelConfigCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_models.create")),
    ],
) -> AiModelConfigResponse:
    """Registra un nuevo modelo cognitivo o motor JEV en el catálogo."""
    with trace_span(
        "platform_admin.ai_models.create",
        attributes={
            "model_slug": payload.model_slug,
            "provider": payload.provider,
            "engine_tier": payload.engine_tier,
            "input_cost_per_1m_usd": str(payload.input_cost_per_1m_usd),
        },
    ):
        created = _ai_model_catalog_service.create_model(payload)
        return _map_ai_model_config(created)


@router.put(
    "/api/v1/platform-admin/ai-models/{model_slug}",
    response_model=AiModelConfigResponse,
    status_code=status.HTTP_200_OK,
)
async def update_ai_model_endpoint(
    model_slug: str,
    payload: AiModelConfigUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_models.update")),
    ],
) -> AiModelConfigResponse:
    """Modifica la configuración de un modelo cognitivo y actualiza en caliente el registry."""
    dumped = payload.model_dump(exclude_unset=True)
    with trace_span(
        "platform_admin.ai_models.update",
        attributes={
            "model_slug": model_slug,
            "updated_fields": ",".join(dumped.keys()),
            "is_default": str(payload.is_default),
        },
    ):
        updated = _ai_model_catalog_service.update_model(model_slug, payload)
        return _map_ai_model_config(updated)


@router.delete(
    "/api/v1/platform-admin/ai-models/{model_slug}",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def delete_ai_model_endpoint(
    model_slug: str,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.ai_models.delete")),
    ],
    hard_delete: bool = Query(default=False),
) -> Any:
    """
    Elimina físicamente o archiva lógicamente un modelo de IA protegiendo trazabilidad financiera.
    - Rechaza con HTTP 409 si model.is_default == True.
    - Si posee llamadas históricas en telemetría: Soft Delete forzoso (HTTP 200 OK).
    - Si posee 0 llamadas: Hard Delete físico (HTTP 204 No Content).
    """
    with trace_span(
        "platform_admin.ai_models.delete",
        attributes={
            "model_slug": model_slug,
            "hard_delete_requested": hard_delete,
        },
    ) as span_attrs:
        model = _ai_model_catalog_service.get_model_by_slug(model_slug)
        if model.is_default:
            raise OppyTecError(
                "No se puede eliminar ni desactivar el modelo predeterminado. Designe otro modelo antes de proceder.",
                status_code=409,
                error_code="CANNOT_DELETE_DEFAULT_MODEL",
                context={"model_slug": model_slug},
            )

        telemetry_refs = _ai_model_catalog_service.count_telemetry_references(model_slug)
        span_attrs["telemetry_references_count"] = telemetry_refs
        if telemetry_refs > 0:
            if hard_delete:
                raise OppyTecError(
                    "El modelo posee telemetría financiera histórica asociada. Queda terminantemente prohibida su eliminación física.",
                    status_code=409,
                    error_code="CANNOT_HARD_DELETE_REFERENCED_MODEL",
                    context={"model_slug": model_slug, "telemetry_references": telemetry_refs},
                )
            _ai_model_catalog_service.delete_model(model_slug, hard_delete=False)
            span_attrs["resolution"] = "soft_delete_archived"
            return AiModelDeleteResponse(
                action="SOFT_DELETED_ARCHIVED",
                model_slug=model_slug,
                is_enabled=False,
                historical_telemetry_logs_preserved=telemetry_refs,
                message="El modelo posee telemetría financiera histórica asociada. Ha sido desactivado lógicamente para proteger la trazabilidad de costos.",
            )

        # telemetry_refs == 0 -> Hard Delete físico
        _ai_model_catalog_service.delete_model(model_slug, hard_delete=True)
        span_attrs["resolution"] = "hard_deleted"
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# 8. RLHF & OBSERVABILITY FEEDBACK ENDPOINTS
# ============================================================================


@router.post(
    "/api/v1/oppy_ai/chat/feedback",
    response_model=AIChatFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(RequireRateLimit("ai")),
    ],
)
@router.post(
    "/api/v1/oppyfy/chat/feedback",
    response_model=AIChatFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def submit_chat_feedback_endpoint(
    payload: AIChatFeedbackCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(
            RequireTenantPermission(
                "oppy_ai.chat.feedback",
                fallback_permission="oppyfy.assistant.chat",
            )
        ),
    ],
) -> AIChatFeedbackResponse:
    """
    Ingesta de feedback humano (RLHF) y evaluación cualitativa de respuestas de OppyFy:
    - Persiste en repositorio de feedback.
    - Envía score normalizado a Langfuse si el trace_id existe.
    - Control de permisos RBAC de 3 niveles y validación de payload según reglas de dominio.
    """
    with trace_span(
        "oppy_ai.feedback.submit",
        attributes={
            "trace.id": payload.trace_id,
            "feedback.type": payload.feedback_type,
            "tenant.id": str(payload.tenant_id),
        },
        tracer_name="oppytec.oppyfy",
    ):
        # Aislamiento multi-tenant: validar que usuarios de tenant no envíen feedback para otro tenant
        if principal.tenant_id:
            try:
                expected_tenant = uuid.UUID(principal.tenant_id)
                if (
                    payload.tenant_id != expected_tenant
                    and not principal.is_superuser_god
                    and not principal.is_global_staff
                ):
                    raise OppyTecError(
                        "Cross-tenant feedback submission is forbidden.",
                        status_code=status.HTTP_403_FORBIDDEN,
                        error_code="CROSS_TENANT_ACCESS_FORBIDDEN",
                    )
            except ValueError:
                pass

        user_uuid = None
        if principal.user_id:
            try:
                user_uuid = uuid.UUID(int=principal.user_id)
            except Exception:
                user_uuid = None

        try:
            feedback = AIChatFeedback(
                tenant_id=payload.tenant_id,
                user_id=user_uuid,
                message_id=payload.message_id,
                trace_id=payload.trace_id,
                feedback_type=payload.feedback_type,
                failure_category=payload.failure_category,
                user_correction=payload.user_correction,
                rating=payload.rating,
            )
        except InvalidFeedbackPayloadError as exc:
            raise OppyTecError(
                str(exc),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_FEEDBACK_PAYLOAD",
            ) from exc

        saved = await _feedback_repository.save_feedback(feedback)
        await _langfuse_tracer.record_feedback(saved)

        return AIChatFeedbackResponse(
            id=saved.id,
            tenant_id=saved.tenant_id,
            user_id=saved.user_id,
            message_id=saved.message_id,
            trace_id=saved.trace_id,
            feedback_type=saved.feedback_type,
            failure_category=saved.failure_category,
            user_correction=saved.user_correction,
            rating=saved.rating,
            created_at=saved.created_at,
        )


@router.get(
    "/api/v1/oppy_ai/chat/feedback",
    response_model=AIChatFeedbackListResponse,
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/api/v1/oppyfy/chat/feedback",
    response_model=AIChatFeedbackListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_chat_feedback_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(
            RequireTenantPermission(
                "oppy_ai.chat.feedback",
                fallback_permission="oppyfy.assistant.chat",
            )
        ),
    ],
    tenant_id: uuid.UUID | None = None,
    message_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AIChatFeedbackListResponse:
    """
    Listado paginado de feedback con métricas agregadas de satisfacción (% positivo vs negativo).
    """
    with trace_span(
        "oppy_ai.feedback.list",
        attributes={"tenant.id": str(tenant_id) if tenant_id else ""},
        tracer_name="oppytec.oppyfy",
    ):
        if tenant_id is not None:
            # Aislamiento multi-tenant: prevenir IDOR / BOLA si el usuario no es superuser ni holding owner
            if principal.tenant_id:
                try:
                    user_tenant = uuid.UUID(principal.tenant_id)
                    if (
                        tenant_id != user_tenant
                        and not principal.is_superuser_god
                        and not principal.is_global_staff
                        and (
                            not principal.accessible_tenants
                            or str(tenant_id) not in principal.accessible_tenants
                        )
                    ):
                        raise OppyTecError(
                            "Cross-tenant feedback inspection is forbidden.",
                            status_code=status.HTTP_403_FORBIDDEN,
                            error_code="CROSS_TENANT_ACCESS_FORBIDDEN",
                        )
                except ValueError:
                    pass
            target_tenant = tenant_id
        elif principal.tenant_id:
            try:
                target_tenant = uuid.UUID(principal.tenant_id)
            except ValueError:
                target_tenant = uuid.UUID("22222222-2222-2222-2222-222222222222")
        else:
            target_tenant = uuid.UUID("22222222-2222-2222-2222-222222222222")

        items = await _feedback_repository.list_feedback(
            tenant_id=target_tenant,
            message_id=message_id,
            limit=limit,
            offset=offset,
        )

        all_for_tenant = await _feedback_repository.list_feedback(
            tenant_id=target_tenant,
            message_id=message_id,
            limit=10000,
            offset=0,
        )

        pos_count = sum(1 for f in all_for_tenant if f.feedback_type == "positive")
        neg_count = sum(1 for f in all_for_tenant if f.feedback_type == "negative")
        total_count = len(all_for_tenant)

        if total_count > 0:
            satisfaction_rate = (
                Decimal(pos_count) / Decimal(total_count) * Decimal("100.00")
            ).quantize(Decimal("0.01"))
        else:
            satisfaction_rate = Decimal("0.00")

        return AIChatFeedbackListResponse(
            items=[
                AIChatFeedbackResponse(
                    id=item.id,
                    tenant_id=item.tenant_id,
                    user_id=item.user_id,
                    message_id=item.message_id,
                    trace_id=item.trace_id,
                    feedback_type=item.feedback_type,
                    failure_category=item.failure_category,
                    user_correction=item.user_correction,
                    rating=item.rating,
                    created_at=item.created_at,
                )
                for item in items
            ],
            total=total_count,
            positive_count=pos_count,
            negative_count=neg_count,
            satisfaction_rate_percent=satisfaction_rate,
        )

