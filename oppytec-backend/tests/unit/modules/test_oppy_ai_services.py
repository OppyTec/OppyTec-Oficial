"""
Pruebas unitarias 1:1 para `src/adapters/ai/`, `src/modules/oppy_ai/` y `scripts/db_migration.py`.
Verifica:
- `LlmRequestLog` (`PublicBase`), dominios editables de `OppyFy` (`TenantBase`) y CLI de migraciones.
- `MeteredJevAdapter` (3 primitivas `decide_boolean`, `decide_choice`, `decide_score`, `< 500 ms` y telemetría `SYSTEM_1_JEV`).
- `MeteredGeminiAdapter` (generación minimalista estilo `Pi`, embeddings en `Decimal` y audio).
- `oppyfy_rbac.py` (expiración por `expires_at`, `max_prompts`, `temp_credit_ceiling`, `BLOCKED_UNAUTHORIZED_PROMPT` y redacción `can_view_costs=False`).
- `credit_wallet.py` (acumulación sin caducidad `1000 + 10000 = 11000`, distribución y descuento atómico).
- `context_meter.py` (alerta preventiva `> 80%` y compactación hacia hilo fresco al `5.00%`).
- `tool_router.py`, `rag_service.py` (3 capas aisladas) y `metered_ai_service.py` (orquestación E2E).
"""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from scripts.db_migration import (
    create_correlative_migration,
    rebase_colliding_migrations,
    sanitize_migration_slug,
    should_execute_migration_for_target,
    verify_migrations_chain,
)

from src.adapters.ai import (
    MeteredGeminiAdapter,
    MeteredJevAdapter,
)
from src.adapters.ai.jev_adapter import InMemoryTelemetrySink
from src.core.bootstrap import DEFAULT_SYSTEM_PLANS, PLAN_BASICO_10_MODULES
from src.modules.oppy_ai.application import (
    BusinessSpecChunkRecord,
    MeteredAIService,
    OppyfyQueryRequest,
    OppyfyToolRouter,
    TenantDocumentChunkRecord,
    TenantMemoryRecord,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.domain import (
    BLOCKED_UNAUTHORIZED_PROMPT,
    REDACTED_COST_MARKER,
    CreditPackageSpec,
    HoldingCreditPool,
    OppyfyPermissionGrantSpec,
    WorkerCreditWalletState,
    allocate_credits_to_worker,
    compact_thread_for_fresh_handover,
    deduct_worker_credits,
    evaluate_context_usage,
    evaluate_oppyfy_subdomain_access,
    redact_cost_fields,
    stack_credit_packages,
)
from src.modules.oppy_ai.infrastructure.models import (
    AiChatThread,
    AiCreditPackage,
    LlmRequestLog,
    OppyfyDomain,
    OppyfyPermissionGrant,
    OppyfyPromptAuditLog,
    OppyfySubdomain,
    OppyfyWorkerCreditWallet,
    SpecChunk,
    SpecSyncMetadata,
)

pytestmark = pytest.mark.unit


def test_oppyfy_public_telemetry_and_tenant_rbac_models() -> None:
    """Verifica `LlmRequestLog` en `public`, paquetes acumulables sin caducidad y RBAC editable de `OppyFy`."""
    assert LlmRequestLog.__table__.schema == "public"
    assert AiCreditPackage.__table__.schema == "public"
    assert SpecSyncMetadata.__table__.schema == "public"
    assert SpecChunk.__table__.schema == "public"

    assert OppyfyDomain.__table__.schema is None
    assert OppyfySubdomain.__table__.schema is None
    assert OppyfyPermissionGrant.__table__.schema is None
    assert OppyfyPromptAuditLog.__table__.schema is None

    pkg_1k = AiCreditPackage(
        slug="pack_1000",
        name="Paquete 1.000 Créditos",
        credit_amount=Decimal("1000.00"),
        price_clp=Decimal("9990.00"),
        price_usd=Decimal("11.00"),
        expires_in_days=None,
    )
    pkg_10k = AiCreditPackage(
        slug="pack_10000",
        name="Paquete 10.000 Créditos",
        credit_amount=Decimal("10000.00"),
        price_clp=Decimal("79990.00"),
        price_usd=Decimal("88.00"),
        expires_in_days=None,
    )
    assert pkg_1k.expires_in_days is None
    assert pkg_1k.credit_amount + pkg_10k.credit_amount == Decimal("11000.00")

    log = LlmRequestLog(
        holding_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tenant_schema="tenant_pacifico_centro",
        user_id=1,
        engine_tier="SYSTEM_1_JEV",
        caller_feature="merma_judge",
        model_name="gemini-3.8-flash",
        input_tokens=120,
        output_tokens=15,
        total_tokens=135,
        provider_cost_usd=Decimal("0.000135"),
        provider_cost_clp=Decimal("0.13"),
        credits_deducted=Decimal("1.00"),
    )
    assert log.engine_tier == "SYSTEM_1_JEV"

    wallet = OppyfyWorkerCreditWallet(
        user_id=5,
        allocated_credits=Decimal("500.00"),
        consumed_credits=Decimal("12.50"),
        is_oppyfy_enabled=True,
    )
    thread = AiChatThread(
        user_id=5,
        title="Consulta de Ventas",
        context_usage_percent=Decimal("34.50"),
    )
    assert wallet.allocated_credits - wallet.consumed_credits == Decimal("487.50")
    assert thread.context_usage_percent == Decimal("34.50")


def test_correlative_migration_cli_and_scope_routing(tmp_path: Path) -> None:
    """Verifica `db_migration.py` (`new`, `rebase`, `verify`) y el filtro `should_execute_migration_for_target`."""
    assert should_execute_migration_for_target("public", "public") is True
    assert should_execute_migration_for_target("tenant", "public") is False
    assert should_execute_migration_for_target("tenant", "tenant_pacifico") is True
    assert should_execute_migration_for_target("public", "tenant_pacifico") is False

    assert sanitize_migration_slug("Add Accounting Cost-Centers!") == "add_accounting_cost_centers"

    mig1 = create_correlative_migration("public", "genesis", versions_dir=tmp_path)
    mig2 = create_correlative_migration("tenant", "initial_ops", versions_dir=tmp_path)
    assert mig1.name == "0001_public_genesis.py"
    assert mig2.name == "0002_tenant_initial_ops.py"
    assert verify_migrations_chain(tmp_path) == []

    # Simular colisión de rama paralela (dos archivos 0002_*)
    colliding = tmp_path / "0002_tenant_parallel_feature.py"
    colliding.write_text(mig2.read_text(encoding="utf-8"), encoding="utf-8")
    renamed = rebase_colliding_migrations(tmp_path)
    assert renamed == ["0003_tenant_parallel_feature.py"]
    assert verify_migrations_chain(tmp_path) == []


def test_metered_jev_adapter_and_gemini_adapter_telemetry() -> None:
    """Verifica que `MeteredJevAdapter` y `MeteredGeminiAdapter` ejecuten en `< 500 ms` y registren en `llm_request_logs`."""
    sink = InMemoryTelemetrySink()
    jev = MeteredJevAdapter(telemetry_sink=sink)
    gemini = MeteredGeminiAdapter(telemetry_sink=sink)
    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    bool_res = jev.decide_boolean(
        decision_id="OCR_DUPLICATE_CHECK",
        prompt_or_input="Coca Cola Lata 350ml | Coca-Cola 350ml Lata",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_austral",
        user_id=10,
        caller_feature="invoice_ocr",
    )
    assert bool_res.value is True
    assert bool_res.confidence >= Decimal("0.85")
    assert bool_res.meets_threshold is True
    assert bool_res.fallback_required is False
    assert bool_res.usage_record.engine_tier == "SYSTEM_1_JEV"
    assert bool_res.usage_record.request_duration_ms < 500

    excel_choice = jev.decide_choice(
        decision_id="EXCEL_COLUMN_MAP",
        prompt_or_input="Precio Costo Neto Unitario",
        candidates=("nombre", "costo_neto", "unidad", "bodega"),
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_austral",
        user_id=10,
        caller_feature="excel_importer",
    )
    assert excel_choice.value == "costo_neto"
    assert excel_choice.meets_threshold is True

    merma_score = jev.decide_score(
        decision_id="MERMA_SEVERITY_JUDGE",
        prompt_or_input="Alerta de quiebre y rotura de botella en cámara fría",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_austral",
        user_id=10,
        caller_feature="merma_judge",
    )
    assert merma_score.level == "HIGH"
    assert merma_score.numeric_score == Decimal("0.78")

    text_resp, gen_log = gemini.generate_minimalist_response(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_austral",
        user_id=10,
        caller_feature="oppyfy_chat",
        user_prompt="Resumen de ventas",
        compact_context_payload={"ventas": Decimal("1200000.00")},
    )
    assert "OppyFy" in text_resp
    assert gen_log.engine_tier == "SYSTEM_2_LLM"

    vec, emb_log = gemini.embed_text(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_austral",
        user_id=10,
        caller_feature="spec_embedding",
        text="Manual funcional de inventario FEFO",
    )
    assert len(vec) == 8
    assert emb_log.engine_tier == "EMBEDDING"

    audio_log = gemini.transcribe_or_synthesize_audio(
        holding_id=holding_id,
        tenant_id=tenant_id,
        user_id=10,
        duration_seconds=Decimal("12.00"),
    )
    assert audio_log.credits_deducted == Decimal("0.60")
    assert len(sink.records) == 5


def test_oppyfy_editable_rbac_expirations_and_cost_redaction() -> None:
    """
    Verifica el motor RBAC editable de `OppyFy`:
    - Expiración por `expires_at`, `max_prompts` y `temp_credit_ceiling`.
    - Código de auditoría `"BLOCKED_UNAUTHORIZED_PROMPT"`.
    - Redacción automática `"[REDACTED_COST]"` cuando `can_view_costs=False`.
    """
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)

    expired_by_prompts = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=2,
        subdomain_slug="inventario_y_bodegas",
        user_id=25,
        effect="ALLOW",
        can_view_costs=False,
        max_prompts=5,
        used_prompts=5,
    )
    dec_prompts = evaluate_oppyfy_subdomain_access(
        user_id=25,
        role_ids=(3,),
        hierarchy_rank=20,
        target_subdomain_slug="inventario_y_bodegas",
        grants=(expired_by_prompts,),
        now=now,
    )
    assert dec_prompts.allowed is False
    assert dec_prompts.audit_code == BLOCKED_UNAUTHORIZED_PROMPT
    assert dec_prompts.denial_reason == "GRANT_EXPIRED_BY_MAX_PROMPTS"

    expired_by_ceiling = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=2,
        subdomain_slug="inventario_y_bodegas",
        user_id=25,
        effect="ALLOW",
        can_view_costs=False,
        temp_credit_ceiling=Decimal("10.00"),
        credits_used_in_grant=Decimal("9.50"),
    )
    dec_ceiling = evaluate_oppyfy_subdomain_access(
        user_id=25,
        role_ids=(3,),
        hierarchy_rank=20,
        target_subdomain_slug="inventario_y_bodegas",
        grants=(expired_by_ceiling,),
        estimated_cost=Decimal("1.00"),
        now=now,
    )
    assert dec_ceiling.allowed is False
    assert dec_ceiling.audit_code == BLOCKED_UNAUTHORIZED_PROMPT
    assert dec_ceiling.denial_reason == "GRANT_EXPIRED_BY_CREDIT_CEILING"

    expired_by_time = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=2,
        subdomain_slug="inventario_y_bodegas",
        user_id=25,
        effect="ALLOW",
        expires_at=now - timedelta(minutes=1),
    )
    dec_time = evaluate_oppyfy_subdomain_access(
        user_id=25,
        role_ids=(3,),
        hierarchy_rank=20,
        target_subdomain_slug="inventario_y_bodegas",
        grants=(expired_by_time,),
        now=now,
    )
    assert dec_time.allowed is False
    assert dec_time.denial_reason == "GRANT_EXPIRED_BY_TIMESTAMP"

    raw_tool_data: dict[str, str | int | Decimal | bool | list[dict[str, str | int | Decimal | bool]]] = {
        "insumo": "Salmón Atlántico",
        "stock_kg": Decimal("42.00"),
        "costo_unitario": Decimal("11500.00"),
        "margen_bruto": Decimal("54.00"),
    }
    redacted = redact_cost_fields(raw_tool_data, can_view_costs=False)
    assert redacted["stock_kg"] == Decimal("42.00")
    assert redacted["costo_unitario"] == REDACTED_COST_MARKER
    assert redacted["margen_bruto"] == REDACTED_COST_MARKER


def test_credit_wallet_stackable_packages_and_context_meter() -> None:
    """Verifica la acumulación sin caducidad (`1000 + 10000 = 11000`), la billetera y el medidor `% contexto`."""
    pack_1k = CreditPackageSpec(
        package_id=uuid.uuid4(),
        slug="pack_1000",
        name="1.000 Créditos",
        credit_amount=Decimal("1000.00"),
        price_clp=Decimal("9990.00"),
        price_usd=Decimal("11.00"),
        expires_in_days=None,
    )
    pack_10k = CreditPackageSpec(
        package_id=uuid.uuid4(),
        slug="pack_10000",
        name="10.000 Créditos",
        credit_amount=Decimal("10000.00"),
        price_clp=Decimal("79990.00"),
        price_usd=Decimal("88.00"),
        expires_in_days=None,
    )
    stacked_total = stack_credit_packages(Decimal("1000.00"), (pack_10k,))
    assert stacked_total == Decimal("11000.00")
    assert stack_credit_packages(Decimal("0.00"), (pack_1k, pack_10k)) == Decimal("11000.00")

    pool = HoldingCreditPool(
        holding_id=uuid.uuid4(),
        total_purchased_credits=stacked_total,
        allocated_to_workers_credits=Decimal("0.00"),
    )
    worker_wallet = WorkerCreditWalletState(
        user_id=7,
        allocated_credits=Decimal("0.00"),
        consumed_credits=Decimal("0.00"),
        is_oppyfy_enabled=True,
    )
    pool, worker_wallet = allocate_credits_to_worker(pool, worker_wallet, Decimal("250.00"))
    assert pool.unallocated_credits == Decimal("10750.00")
    assert worker_wallet.remaining_credits == Decimal("250.00")

    deduction = deduct_worker_credits(worker_wallet, Decimal("1.40"))
    assert deduction.allowed is True
    assert deduction.updated_wallet.remaining_credits == Decimal("248.60")

    ctx_green = evaluate_context_usage(4000, max_safe_tokens=16000)
    assert ctx_green.context_usage_percent == Decimal("25.00")
    assert ctx_green.preventive_alert is False

    ctx_alert = evaluate_context_usage(13200, max_safe_tokens=16000)
    assert ctx_alert.context_usage_percent == Decimal("82.50")
    assert ctx_alert.preventive_alert is True
    assert ctx_alert.requires_auto_compaction is False

    ctx_critical = evaluate_context_usage(14400, max_safe_tokens=16000)
    assert ctx_critical.context_usage_percent == Decimal("90.00")
    assert ctx_critical.requires_auto_compaction is True

    handover = compact_thread_for_fresh_handover(
        source_thread_id=uuid.uuid4(),
        messages=("Turno 1: Stock de lomo", "Turno 2: Evento 120 invitados"),
    )
    assert handover.new_context_usage_percent == Decimal("5.00")
    assert "[COMPACTED_HANDOVER]" in handover.synthesized_summary


def test_e2e_metered_ai_service_rag_and_rbac_enforcement() -> None:
    """
    Verifica el flujo E2E de `MeteredAIService`:
    - Consulta autorizada con `can_view_costs=False` redacta costos (`[REDACTED_COST]`),
      recupera las 3 capas del RAG, descuenta créditos y registra en `llm_request_logs`.
    - Consulta no autorizada retorna `BLOCKED_UNAUTHORIZED_PROMPT` y registra en `prompt_audit_logs`.
    """
    sink = InMemoryTelemetrySink()
    jev = MeteredJevAdapter(telemetry_sink=sink)
    gemini = MeteredGeminiAdapter(telemetry_sink=sink)

    rag = ThreeLayerRagService(
        tenant_doc_chunks=(
            TenantDocumentChunkRecord(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                oppyfy_subdomain_id=10,
                chunk_text="Protocolo interno de recepción de carnes en bodega central.",
            ),
            TenantDocumentChunkRecord(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                oppyfy_subdomain_id=99,
                chunk_text="Documento confidencial de otro sub-dominio.",
            ),
        ),
        tenant_memories=(
            TenantMemoryRecord(
                memory_id=uuid.uuid4(),
                user_id=None,
                agent_affinity="general",
                memory_fact="El restaurante cierra los lunes por mantenimiento.",
            ),
        ),
        business_spec_chunks=(
            BusinessSpecChunkRecord(
                chunk_id=uuid.uuid4(),
                spec_rel_path="specs/business-domain/inventory.business.spec.md",
                module_slug="inventory",
                content_markdown="Guía funcional de control de stock y lotes FEFO.",
            ),
        ),
    )
    router = OppyfyToolRouter(jev)
    service = MeteredAIService(
        jev_port=jev,
        llm_port=gemini,
        rag_service=rag,
        tool_router=router,
    )

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    wallet = WorkerCreditWalletState(
        user_id=42,
        allocated_credits=Decimal("50.00"),
        consumed_credits=Decimal("0.00"),
        is_oppyfy_enabled=True,
    )
    stock_grant_no_costs = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=10,
        subdomain_slug="inventario_y_bodegas",
        user_id=42,
        effect="ALLOW",
        can_view_costs=False,
        max_prompts=10,
        used_prompts=1,
    )

    allowed_req = OppyfyQueryRequest(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_pacifico",
        user_id=42,
        role_ids=(4,),
        hierarchy_rank=30,
        prompt_text="¿Cuál es el nivel de stock e inventario en bodega hoy?",
        wallet=wallet,
        grants=(stock_grant_no_costs,),
        subdomain_id_by_slug={"inventario_y_bodegas": 10},
    )
    allowed_resp = service.execute_oppyfy_query(allowed_req)
    assert allowed_resp.allowed is True
    assert allowed_resp.routed_tool == "query_stock_levels"
    assert allowed_resp.tool_execution is not None
    assert allowed_resp.tool_execution.costs_redacted is True
    assert allowed_resp.tool_execution.sanitized_payload["costo_unitario"] == REDACTED_COST_MARKER
    assert allowed_resp.rag_bundle is not None
    assert len(allowed_resp.rag_bundle.layer2_tenant_doc_chunks) == 1
    assert allowed_resp.credits_deducted == Decimal("1.40")
    assert allowed_resp.updated_wallet.remaining_credits == Decimal("48.60")
    assert len(allowed_resp.llm_usage_records) == 3

    # Intento de consultar ventas/finanzas sin permiso en el sub-dominio 'finanzas_y_rentabilidad'
    unauthorized_req = OppyfyQueryRequest(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_pacifico",
        user_id=42,
        role_ids=(4,),
        hierarchy_rank=30,
        prompt_text="Muéstrame el resumen de ventas y facturación del mes",
        wallet=allowed_resp.updated_wallet,
        grants=(stock_grant_no_costs,),
        subdomain_id_by_slug={"inventario_y_bodegas": 10, "finanzas_y_rentabilidad": 20},
    )
    blocked_resp = service.execute_oppyfy_query(unauthorized_req)
    assert blocked_resp.allowed is False
    assert blocked_resp.status_code == BLOCKED_UNAUTHORIZED_PROMPT
    assert blocked_resp.prompt_audit_entry.decision_status == BLOCKED_UNAUTHORIZED_PROMPT
    assert blocked_resp.credits_deducted == Decimal("0.00")


def test_jev_system1_latency_sla_under_5ms() -> None:
    """
    Verifica que el motor JEV (Sistema 1) no sufra regresiones de rendimiento y mantenga su SLA < 5ms
    en sus tres primitivas inmutables:
    - `decide_boolean` (guardrails de inyección y equivalencia semántica)
    - `decide_choice` (enrutamiento de herramientas y subdominios)
    - `decide_score` (clasificación de severidad y evaluación)
    """
    sink = InMemoryTelemetrySink()
    jev = MeteredJevAdapter(telemetry_sink=sink)
    h_id = uuid.uuid4()
    t_id = uuid.uuid4()

    # Ejecutar 50 iteraciones de cada primitiva para medir SLA
    boolean_latencies: list[float] = []
    choice_latencies: list[float] = []
    score_latencies: list[float] = []

    for _ in range(50):
        t0 = time.perf_counter()
        b_res = jev.decide_boolean(
            decision_id="SECURITY_CHECK",
            prompt_or_input="Select all products from inventory",
            holding_id=h_id,
            tenant_id=t_id,
            tenant_schema="tenant_test",
            user_id=1,
            caller_feature="test_security",
        )
        boolean_latencies.append((time.perf_counter() - t0) * 1000.0)
        assert b_res.meets_threshold is True

        t1 = time.perf_counter()
        c_res = jev.decide_choice(
            decision_id="TOOL_ROUTE",
            prompt_or_input="Dame el resumen de ventas del día",
            candidates=("query_sales_summary", "query_stock_levels", "query_recipe_costs"),
            holding_id=h_id,
            tenant_id=t_id,
            tenant_schema="tenant_test",
            user_id=1,
            caller_feature="test_router",
        )
        choice_latencies.append((time.perf_counter() - t1) * 1000.0)
        assert c_res.value == "query_sales_summary"

        t2 = time.perf_counter()
        s_res = jev.decide_score(
            decision_id="MERMA_SEVERITY",
            prompt_or_input="Alerta de merma crítica por quiebre de stock",
            holding_id=h_id,
            tenant_id=t_id,
            tenant_schema="tenant_test",
            user_id=1,
            caller_feature="test_score",
        )
        score_latencies.append((time.perf_counter() - t2) * 1000.0)
        assert s_res.level == "HIGH"

    p95_bool = sorted(boolean_latencies)[int(len(boolean_latencies) * 0.95)]
    p95_choice = sorted(choice_latencies)[int(len(choice_latencies) * 0.95)]
    p95_score = sorted(score_latencies)[int(len(score_latencies) * 0.95)]

    # SLA < 5ms estricto para cada primitiva
    assert p95_bool < 5.0, f"decide_boolean P95 SLA exceeded: {p95_bool:.3f}ms >= 5.0ms"
    assert p95_choice < 5.0, f"decide_choice P95 SLA exceeded: {p95_choice:.3f}ms >= 5.0ms"
    assert p95_score < 5.0, f"decide_score P95 SLA exceeded: {p95_score:.3f}ms >= 5.0ms"


def test_plan_basico_oppyfy_disabled_by_default_and_upgrade_or_override() -> None:
    """
    Certifica las reglas de gobierno de Plan Básico respecto al Asistente IA OppyFy:
    1. En `PLAN_BASICO_10_MODULES`, 'oppy_ai' está desactivado por defecto (no incluido).
    2. El plan 'basic' en `DEFAULT_SYSTEM_PLANS` usa `PLAN_BASICO_10_MODULES`.
    3. El plan 'enterprise' incluye 'oppy_ai' por defecto.
    4. La estructura del payload `TenantModulesAndQuotasUpdateRequest` permite agregar 'oppy_ai'
       a `enabled_modules` como activación opcional sin requerir cambio de plan base.
    """
    # 1. 'oppy_ai' no está en el Plan Básico por defecto
    assert "oppy_ai" not in PLAN_BASICO_10_MODULES

    # 2. Plan básico en catálogo usa PLAN_BASICO_10_MODULES
    basic_plan = next(p for p in DEFAULT_SYSTEM_PLANS if p.slug == "basic")
    assert "oppy_ai" not in basic_plan.included_modules
    assert set(basic_plan.included_modules) == set(PLAN_BASICO_10_MODULES)

    # 3. Plan Corporativo incluye 'oppy_ai'
    enterprise_plan = next(p for p in DEFAULT_SYSTEM_PLANS if p.slug == "enterprise")
    assert "oppy_ai" in enterprise_plan.included_modules

    # 4. Activación opcional mediante `TenantModulesAndQuotasUpdateRequest`
    from src.modules.tenancy.presentation.schemas import TenantModulesAndQuotasUpdateRequest

    req_with_ai = TenantModulesAndQuotasUpdateRequest(
        enabled_modules=[*PLAN_BASICO_10_MODULES, "oppy_ai"],
        custom_max_users_override=10,
    )
    assert "oppy_ai" in req_with_ai.enabled_modules
    assert req_with_ai.custom_max_users_override == 10


def test_operational_tools_and_cost_stripping() -> None:
    """
    Verifica las herramientas operativas deterministas (JEV Layer 2):
    - Inventario FEFO y alertas de reposición
    - Factibilidad de banquetes y eventos
    - Mermas y Food Cost
    - Regla inmutable "Pollo King": nombres de proveedores intactos
    - Hard-Code Data Stripping cuando can_view_costs=False
    """
    from src.adapters.ai.jev_protocol import JevChoiceResult
    from src.modules.oppy_ai.application.operational_tools import (
        analyze_event_supply_feasibility,
        analyze_waste_and_merma_impact,
        build_optimal_purchase_order_draft,
        evaluate_supplier_lead_times_and_price_drift,
        get_expiring_batches_fefo,
        get_sales_and_food_cost_variance,
        get_stock_health_and_reorder_alerts,
        render_canvas_chart,
        render_canvas_table,
    )

    schema = "tenant_test"

    # 1. Inventario & FEFO
    stock_alerts = get_stock_health_and_reorder_alerts(schema, critical_threshold_days=7)
    assert stock_alerts["critical_items_count"] == 2
    assert isinstance(stock_alerts["total_estimated_reorder_cost"], Decimal)

    exp_batches = get_expiring_batches_fefo(schema, days_window=14)
    assert exp_batches["expiring_batches_count"] == 3
    assert exp_batches["batches"][0]["risk_level"] == "CRITICAL"

    # 2. Proveedores & Demoras (Regla Pollo King)
    supp_drift = evaluate_supplier_lead_times_and_price_drift(schema)
    pk_supp = next(
        s for s in supp_drift["suppliers_evaluated"] if s["supplier_name"] == "Pollo King SpA"
    )
    assert pk_supp["supplier_name"] == "Pollo King SpA"
    assert pk_supp["lead_time_drift_hours"] == 12

    po_draft = build_optimal_purchase_order_draft(schema)
    assert any(
        order["supplier_name"] == "Pollo King SpA" for order in po_draft["supplier_orders"]
    )
    assert isinstance(po_draft["total_draft_neto_clp"], Decimal)

    # 3. Banquetes & Eventos
    event_feasibility = analyze_event_supply_feasibility(schema, guest_count=120)
    assert event_feasibility["stock_sufficient"] is False
    assert len(event_feasibility["critical_shortages"]) > 0

    event_ok = analyze_event_supply_feasibility(schema, guest_count=50)
    assert event_ok["stock_sufficient"] is True
    assert len(event_ok["critical_shortages"]) == 0

    # 4. Mermas & Food Cost
    food_cost = get_sales_and_food_cost_variance(schema)
    assert food_cost["food_cost_real_pct"] == Decimal("32.00")
    assert food_cost["variacion_costo_pct"] == Decimal("2.00")

    waste_impact = analyze_waste_and_merma_impact(schema)
    assert waste_impact["total_merma_incidents"] == 5
    assert isinstance(waste_impact["costo_total_merma"], Decimal)

    # 5. Canvas Tools
    canvas_tbl = render_canvas_table("Stock Crítico", ["Item", "Stock"], [["Lomo", "14kg"]])
    assert canvas_tbl["artifact_type"] == "canvas_table"

    canvas_chrt = render_canvas_chart("bar", "Costos", [{"name": "Costo", "data": [30]}])
    assert canvas_chrt["artifact_type"] == "canvas_chart"

    # 6. Hard-Code Data Stripping en tool router
    jev_dummy = JevChoiceResult(
        decision_id="TEST",
        value="get_stock_health_and_reorder_alerts",
        confidence=Decimal("0.99"),
        threshold=Decimal("0.70"),
        meets_threshold=True,
        fallback_required=False,
        alternatives=(),
        usage_record=None,  # type: ignore[arg-type]
    )
    router = OppyfyToolRouter(None)  # type: ignore[arg-type]

    # Sin permiso de costos
    res_redacted = router.execute_hardcoded_tool(
        "get_stock_health_and_reorder_alerts",
        tenant_schema=schema,
        can_view_costs=False,
        jev_choice=jev_dummy,
    )
    assert res_redacted.costs_redacted is True
    first_alert = res_redacted.sanitized_payload["alerts"][0]
    assert first_alert["costo_unitario"] == REDACTED_COST_MARKER
    assert first_alert["precio_compra"] == REDACTED_COST_MARKER
    assert first_alert["total_neto"] == REDACTED_COST_MARKER
    assert res_redacted.sanitized_payload["total_estimated_reorder_cost"] == REDACTED_COST_MARKER

    # Con permiso de costos
    res_allowed = router.execute_hardcoded_tool(
        "get_stock_health_and_reorder_alerts",
        tenant_schema=schema,
        can_view_costs=True,
        jev_choice=jev_dummy,
    )
    assert res_allowed.costs_redacted is False
    assert isinstance(res_allowed.sanitized_payload["alerts"][0]["costo_unitario"], Decimal)


def test_metered_ai_service_model_tariffs_and_cost_precision() -> None:
    """
    Verifica que MeteredAIService calcule costos exactos en USD NUMERIC(14,6)
    y CLP NUMERIC(14,2) a partir de ai_model_configs.
    """
    from src.modules.oppy_ai.application.metered_ai_service import (
        ModelConfigRegistry,
        ModelTariff,
    )

    registry = ModelConfigRegistry()
    tariff = registry.get_tariff("gemini-1.5-flash")
    assert tariff.input_cost_per_1m_usd == Decimal("0.075000")
    assert tariff.output_cost_per_1m_usd == Decimal("0.300000")

    # Registro de tarifa personalizada
    registry.set_tariff(
        ModelTariff(
            model_slug="custom-llm",
            input_cost_per_1m_usd=Decimal("0.500000"),
            cached_cost_per_1m_usd=Decimal("0.100000"),
            output_cost_per_1m_usd=Decimal("2.000000"),
        )
    )
    custom_tariff = registry.get_tariff("custom-llm")
    assert custom_tariff.input_cost_per_1m_usd == Decimal("0.500000")

    # Verificación de cálculo monetario con Decimal
    service = MeteredAIService(
        jev_port=None,  # type: ignore[arg-type]
        llm_port=None,  # type: ignore[arg-type]
        rag_service=None,  # type: ignore[arg-type]
        model_registry=registry,
    )
    usd, clp = service.calculate_token_cost(
        "custom-llm",
        input_tokens=100_000,
        cached_tokens=50_000,
        output_tokens=20_000,
        usd_to_clp_rate=Decimal("950.00"),
    )
    # (100k * 0.50 + 50k * 0.10 + 20k * 2.00) / 1M = (0.05 + 0.005 + 0.04) = 0.095000 USD
    assert usd == Decimal("0.095000")
    # 0.095 * 950 = 90.25 CLP
    assert clp == Decimal("90.25")


def test_three_layer_rag_and_semantic_cache_l1_l2() -> None:
    """
    Verifica el RAG de 3 Capas:
    - Capa 1: Context health
    - Capa 2: Live tools (is_cacheable = False)
    - Capa 3: specs/business-domain (0% fuga)
    - Caché semántica L1 Redis con TTL 48h
    """
    from src.modules.oppy_ai.application.rag_service import (
        BusinessSpecChunkRecord,
        InMemoryRedisSemanticCache,
        ThreeLayerRagService,
    )
    from src.modules.oppy_ai.application.tool_router import RoutedToolExecutionResult

    cache = InMemoryRedisSemanticCache(default_ttl_seconds=172800)
    rag = ThreeLayerRagService(
        business_spec_chunks=[
            BusinessSpecChunkRecord(
                chunk_id=uuid.uuid4(),
                spec_rel_path="specs/business-domain/inventory/fefo.md",
                module_slug="inventory",
                content_markdown="Reglas FEFO oficiales",
            )
        ],
        semantic_cache=cache,
    )

    # 1. Consulta conceptual (sin herramientas vivas) -> Cacheable
    bundle_conceptual = rag.build_three_layer_context(
        user_prompt="¿Cómo funciona FEFO en OppyTec?",
        authorized_subdomain_id=1,
        user_id=1,
        routed_tool_result=None,
    )
    assert bundle_conceptual.is_cacheable is True
    saved = rag.store_conceptual_cache(
        "¿Cómo funciona FEFO en OppyTec?",
        "FEFO prioriza el lote que vence primero.",
        is_cacheable=bundle_conceptual.is_cacheable,
    )
    assert saved is True
    hit = rag.check_conceptual_cache("¿Cómo funciona FEFO en OppyTec?")
    assert hit == "FEFO prioriza el lote que vence primero."

    # 2. Consulta con datos vivos de Capa 2 -> Estrictamente NO cacheable
    live_result = RoutedToolExecutionResult(
        tool_code="query_stock_levels",
        subdomain_slug="inventario_y_bodegas",
        jev_choice=None,  # type: ignore[arg-type]
        raw_fields_count=2,
        sanitized_payload={"stock_disponible_kg": Decimal("18.50")},
        costs_redacted=False,
    )
    bundle_live = rag.build_three_layer_context(
        user_prompt="Muéstrame el stock vivo",
        authorized_subdomain_id=1,
        user_id=1,
        routed_tool_result=live_result,
    )
    assert bundle_live.is_cacheable is False
    assert rag.store_conceptual_cache("Muéstrame el stock vivo", "18.50kg", is_cacheable=bundle_live.is_cacheable) is False

    # 3. Aislamiento estricto: rechazo de rutas fuera de specs/business-domain
    with pytest.raises(ValueError, match="RAG Isolation Error"):
        rag.register_business_spec_chunk(
            BusinessSpecChunkRecord(
                chunk_id=uuid.uuid4(),
                spec_rel_path="src/modules/identity/passwords.py",
                module_slug="identity",
                content_markdown="Código interno prohibido",
            )
        )


def test_ai_credit_packs_service_crud_quote_and_stacking() -> None:
    """
    Verifica el servicio de paquetes de créditos IA:
    - CRUD en public.ai_credit_packs
    - Cotización con descuento por nivel de plan base SaaS
    - Acumulación sin caducidad (1000 + 10000 = 11000)
    """
    from src.modules.oppy_ai.application.ai_credit_packs_service import (
        AiCreditPacksService,
    )

    service = AiCreditPacksService()
    packs = service.list_packs()
    assert len(packs) >= 3

    # Creación
    new_p = service.create_pack(
        pack_name="Turbo 2.500",
        credits_amount=Decimal("2500.00"),
        price_clp=Decimal("22990.00"),
        price_usd=Decimal("25.00"),
        bonus_credits=Decimal("100.00"),
        plan_tier_discounts={"plan_pro": Decimal("10.00"), "plan_enterprise": Decimal("20.00")},
    )
    assert new_p.total_credits == Decimal("2600.00")

    # Cotización con descuento Plan Enterprise (20%)
    quote = service.calculate_quote(new_p.id, base_plan_tier="plan_enterprise")
    assert quote.discount_pct == Decimal("20.00")
    # 25.00 - 20% = 20.00 USD
    assert quote.final_price_usd == Decimal("20.00")

    # Actualización
    updated = service.update_pack(new_p.id, is_popular=True)
    assert updated.is_popular is True

    # Eliminación
    assert service.delete_pack(new_p.id) is True


def test_token_consumption_finops_analytics() -> None:
    """
    Verifica las métricas consolidadas de rentabilidad y margen bruto FinOps
    calculadas por TokenConsumptionAggregatorService.
    """
    from src.modules.oppy_ai.application.token_consumption_service import (
        TokenConsumptionAggregatorService,
    )

    aggregator = TokenConsumptionAggregatorService()
    finops = aggregator.get_finops_analytics(credit_sale_price_clp=Decimal("15.00"))
    assert finops.total_tokens > 0
    assert finops.provider_cost_usd > Decimal("0.000000")
    assert finops.provider_cost_clp > Decimal("0.00")
    assert finops.credits_revenue_clp > Decimal("0.00")
    assert "gemini-1.5-flash" in finops.model_breakdown
    assert finops.model_breakdown["gemini-1.5-flash"]["tokens"] > 0


