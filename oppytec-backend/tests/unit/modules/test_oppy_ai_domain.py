"""
Pruebas Unitarias de Dominio Puro para OppyFy (`tests/unit/modules/test_oppy_ai_domain.py`).
Verifica el 100% de las reglas de negocio de:
1. `context_meter.py`: Medidor de salud de contexto (% de tokens respecto al límite seguro MAX_SAFE_THREAD_TOKENS = 8192),
   semáforo (Verde <65%, Ámbar 66-85%, Rojo >85%), bloqueo anti-alucinación (>85%) y rollover al 5%.
2. `credit_wallet.py`: Billetera de créditos acumulables sin vencimiento, balance nuevo = actual + comprados,
   deducción atómica con `Decimal`, comprobación de cupos por trabajador y políticas de cuota.
3. `ai_credit_packs.py`: Primitiva de dominio para paquetes de créditos IA independientes configurados en Admin
   que hacen juego con los planes base (descuentos por tier, cálculo de costos unitarios en USD/CLP).
4. `oppyfy_rbac.py`: Entidades y reglas para el RBAC propio de OppyFy (dominios, subdominios, capacidades,
   permisos temporales con triple caducidad: timestamp, max_prompts, temp_credit_ceiling, y redacción de costos).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.modules.oppy_ai.domain import (
    ALLOWED_PROMPT_STATUS,
    AMBER_MAX_PERCENT,
    BLOCKED_UNAUTHORIZED_PROMPT,
    COMPACTION_REQUIRED_PERCENT,
    DEFAULT_MAX_SAFE_THREAD_TOKENS,
    FRESH_THREAD_INITIAL_PERCENT,
    GREEN_MAX_PERCENT,
    MAX_SAFE_THREAD_TOKENS,
    PREVENTIVE_ALERT_THRESHOLD_PERCENT,
    REDACTED_COST_MARKER,
    SENSITIVE_COST_KEYS,
    AiCreditPack,
    ContextHealthEvaluation,
    CreditDeductionResult,
    CreditPackageSpec,
    EditableOppyfyDomainSpec,
    EditableOppyfySubdomainSpec,
    HoldingCreditPool,
    OppyfyAccessDecision,
    OppyfyCapability,
    OppyfyPermissionGrantSpec,
    ThreadCompactionSummary,
    WorkerCreditWalletState,
    WorkerQuotaPolicy,
    allocate_credits_to_worker,
    calculate_safe_rollover_token_budget,
    calculate_wallet_balance,
    check_worker_quota_policy,
    compact_thread_for_fresh_handover,
    consume_grant_quota,
    deduct_worker_credits,
    evaluate_context_usage,
    evaluate_oppyfy_subdomain_access,
    evaluate_pack_plan_match,
    is_grant_currently_valid,
    redact_cost_fields,
    stack_ai_credit_packs,
    stack_credit_packages,
    validate_hierarchical_delegation,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# 1. CONTEXT METER & ANTI-HALLUCINATION ROADS
# ==============================================================================


def test_context_meter_constants_and_limits() -> None:
    """Verifica los límites canónicos de salud de contexto y umbrales semafóricos."""
    assert MAX_SAFE_THREAD_TOKENS == 8192
    assert DEFAULT_MAX_SAFE_THREAD_TOKENS == 8192
    assert GREEN_MAX_PERCENT == Decimal("65.00")
    assert AMBER_MAX_PERCENT == Decimal("85.00")
    assert PREVENTIVE_ALERT_THRESHOLD_PERCENT == Decimal("80.00")
    assert COMPACTION_REQUIRED_PERCENT == Decimal("85.00")
    assert FRESH_THREAD_INITIAL_PERCENT == Decimal("5.00")


def test_context_meter_optimal_green() -> None:
    """Verifica que consumos inferiores o iguales al 65.00% resulten en OPTIMAL_GREEN sin bloqueo."""
    evaluation = evaluate_context_usage(2048)  # 2048 / 8192 = 25.00%
    assert evaluation.accumulated_tokens == 2048
    assert evaluation.max_safe_tokens == 8192
    assert evaluation.context_usage_percent == Decimal("25.00")
    assert evaluation.status == "OPTIMAL_GREEN"
    assert evaluation.preventive_alert is False
    assert evaluation.requires_auto_compaction is False
    assert evaluation.is_anti_hallucination_blocked is False
    assert evaluation.recommendation_key == "oppyfy.context_meter.optimal"

    # Exactamente en el límite de 65.00%
    exact_65_tokens = int(8192 * 0.65)  # 5324
    eval_65 = evaluate_context_usage(exact_65_tokens)
    assert eval_65.context_usage_percent <= Decimal("65.00")
    assert eval_65.status == "OPTIMAL_GREEN"
    assert eval_65.is_anti_hallucination_blocked is False


def test_context_meter_warning_amber_and_preventive_alert() -> None:
    """Verifica el semáforo WARNING_AMBER (66-85%) y la activación de alerta preventiva al >80%."""
    # Rango Ámbar sin alerta preventiva (ej. 70.00%)
    tokens_70 = int(8192 * 0.70)  # 5734 -> ~69.99%
    eval_70 = evaluate_context_usage(tokens_70)
    assert eval_70.status == "WARNING_AMBER"
    assert eval_70.preventive_alert is False
    assert eval_70.requires_auto_compaction is False
    assert eval_70.is_anti_hallucination_blocked is False

    # Rango Ámbar con alerta preventiva (>80% pero <=85%)
    tokens_82 = int(8192 * 0.825)  # 6758 -> 82.50%
    eval_82 = evaluate_context_usage(tokens_82)
    assert eval_82.status == "WARNING_AMBER"
    assert eval_82.preventive_alert is True
    assert eval_82.requires_auto_compaction is False
    assert eval_82.is_anti_hallucination_blocked is False
    assert eval_82.recommendation_key == "oppyfy.context_meter.preventive_alert_80"


def test_context_meter_critical_red_and_anti_hallucination_lock() -> None:
    """Verifica que al superar 85.00% se active CRITICAL_RED y el bloqueo anti-alucinación estricto."""
    # 86.00% de contexto
    tokens_86 = int(8192 * 0.86)  # ~7045 tokens
    eval_86 = evaluate_context_usage(tokens_86)
    assert eval_86.context_usage_percent > Decimal("85.00")
    assert eval_86.status == "CRITICAL_RED"
    assert eval_86.preventive_alert is True
    assert eval_86.requires_auto_compaction is True
    assert eval_86.is_anti_hallucination_blocked is True
    assert eval_86.recommendation_key == "oppyfy.context_meter.critical_handover_required"

    # Saturación completa o desborde (10.000 tokens clamped a 100.00%)
    eval_overflow = evaluate_context_usage(10000)
    assert eval_overflow.context_usage_percent == Decimal("100.00")
    assert eval_overflow.status == "CRITICAL_RED"
    assert eval_overflow.is_anti_hallucination_blocked is True


def test_context_meter_negative_and_invalid_inputs() -> None:
    """Verifica manejo seguro de tokens negativos y excepciones en límites no válidos."""
    # Tokens negativos se acotan a 0
    eval_neg = evaluate_context_usage(-50)
    assert eval_neg.accumulated_tokens == 0
    assert eval_neg.context_usage_percent == Decimal("0.00")
    assert eval_neg.status == "OPTIMAL_GREEN"

    # max_safe_tokens inválido lanza ValueError
    with pytest.raises(ValueError, match="must be strictly positive"):
        evaluate_context_usage(100, max_safe_tokens=0)

    with pytest.raises(ValueError, match="must be strictly positive"):
        evaluate_context_usage(100, max_safe_tokens=-100)


def test_context_meter_thread_compaction_and_rollover_at_5_percent() -> None:
    """Verifica la compactación de hilo y cálculo de presupuesto de tokens para rollover al 5.00%."""
    budget = calculate_safe_rollover_token_budget(8192)
    assert budget == 410  # 8192 * 0.05 = 409.6 -> 410

    source_id = uuid.uuid4()
    messages = [
        "Usuario: ¿Cuál es el costo de la receta Lomo Saltado?",
        "Asistente: El costo teórico unitario es CLP 4.500.",
        "Usuario: Genera un plan de producción para 50 platos.",
    ]
    handover = compact_thread_for_fresh_handover(
        source_thread_id=source_id,
        messages=messages,
    )
    assert handover.source_thread_id == source_id
    assert handover.new_thread_id != source_id
    assert handover.new_context_usage_percent == Decimal("5.00")
    assert "[COMPACTED_HANDOVER]" in handover.synthesized_summary
    assert "Genera un plan de producción para 50 platos" in handover.synthesized_summary
    assert handover.safe_token_budget_allocated == 410


# ==============================================================================
# 2. CREDIT WALLET & QUOTA POLICIES
# ==============================================================================


def test_credit_package_spec_immutability_and_never_expires() -> None:
    """Verifica que CreditPackageSpec rechace caducidad (expires_in_days=None requerido)."""
    pkg = CreditPackageSpec(
        package_id=uuid.uuid4(),
        slug="pack_1000",
        name="Pack 1.000 Créditos",
        credit_amount=Decimal("1000.00"),
        price_clp=Decimal("9990.00"),
        price_usd=Decimal("11.00"),
    )
    assert pkg.expires_in_days is None
    assert pkg.credit_amount == Decimal("1000.00")

    with pytest.raises(ValueError, match="never expire by policy"):
        CreditPackageSpec(
            package_id=uuid.uuid4(),
            slug="pack_invalid",
            name="Pack Inválido",
            credit_amount=Decimal("500.00"),
            price_clp=Decimal("5000.00"),
            price_usd=Decimal("5.00"),
            expires_in_days=30,  # Prohibido por regla de negocio
        )

    with pytest.raises(ValueError, match="strictly positive"):
        CreditPackageSpec(
            package_id=uuid.uuid4(),
            slug="pack_zero",
            name="Pack Cero",
            credit_amount=Decimal("0.00"),
            price_clp=Decimal("0.00"),
            price_usd=Decimal("0.00"),
        )


def test_stack_credit_packages_accumulation() -> None:
    """Verifica acumulación inmediata: balance nuevo = balance actual + comprados."""
    pkg_1k = CreditPackageSpec(
        package_id=uuid.uuid4(),
        slug="pack_1k",
        name="Pack 1k",
        credit_amount=Decimal("1000.00"),
        price_clp=Decimal("9990.00"),
        price_usd=Decimal("11.00"),
    )
    pkg_10k = CreditPackageSpec(
        package_id=uuid.uuid4(),
        slug="pack_10k",
        name="Pack 10k",
        credit_amount=Decimal("10000.00"),
        price_clp=Decimal("79990.00"),
        price_usd=Decimal("88.00"),
    )

    # 1.000 + 10.000 = 11.000
    stacked = stack_credit_packages(Decimal("1000.00"), (pkg_10k,))
    assert stacked == Decimal("11000.00")

    # Múltiples paquetes acumulados simultáneamente
    stacked_multi = stack_credit_packages(Decimal("500.00"), (pkg_1k, pkg_10k))
    assert stacked_multi == Decimal("11500.00")

    # Helper calculate_wallet_balance
    new_bal = calculate_wallet_balance(Decimal("250.00"), Decimal("750.50"))
    assert new_bal == Decimal("1000.50")


def test_allocate_credits_to_worker() -> None:
    """Verifica transferencia atómica desde la bolsa Holding hacia la billetera del trabajador."""
    pool = HoldingCreditPool(
        holding_id=uuid.uuid4(),
        total_purchased_credits=Decimal("15000.00"),
        allocated_to_workers_credits=Decimal("5000.00"),
    )
    assert pool.unallocated_credits == Decimal("10000.00")

    wallet = WorkerCreditWalletState(
        user_id=101,
        allocated_credits=Decimal("200.00"),
        consumed_credits=Decimal("50.00"),
        is_oppyfy_enabled=True,
    )
    assert wallet.remaining_credits == Decimal("150.00")

    updated_pool, updated_wallet = allocate_credits_to_worker(pool, wallet, Decimal("800.00"))
    assert updated_pool.allocated_to_workers_credits == Decimal("5800.00")
    assert updated_pool.unallocated_credits == Decimal("9200.00")
    assert updated_wallet.allocated_credits == Decimal("1000.00")
    assert updated_wallet.remaining_credits == Decimal("950.00")

    # Rechazo por saldo insuficiente en el pool
    with pytest.raises(ValueError, match="Insufficient unallocated credits"):
        allocate_credits_to_worker(updated_pool, updated_wallet, Decimal("20000.00"))


def test_deduct_worker_credits_success_and_failures() -> None:
    """Verifica deducción atómica, bloqueo por interruptor y rechazo por saldo insuficiente."""
    wallet = WorkerCreditWalletState(
        user_id=202,
        allocated_credits=Decimal("100.00"),
        consumed_credits=Decimal("20.00"),
        is_oppyfy_enabled=True,
    )
    assert wallet.remaining_credits == Decimal("80.00")

    # Deducción exitosa con Decimal
    result = deduct_worker_credits(wallet, Decimal("15.75"))
    assert result.allowed is True
    assert result.reason_code == "CREDITS_DEDUCTED_OK"
    assert result.deducted_credits == Decimal("15.75")
    assert result.updated_wallet.consumed_credits == Decimal("35.75")
    assert result.updated_wallet.remaining_credits == Decimal("64.25")

    # Rechazo por saldo insuficiente
    failed_funds = deduct_worker_credits(result.updated_wallet, Decimal("70.00"))
    assert failed_funds.allowed is False
    assert failed_funds.reason_code == "INSUFFICIENT_WORKER_CREDITS"
    assert failed_funds.deducted_credits == Decimal("0.00")

    # Rechazo por interruptor deshabilitado
    disabled_wallet = WorkerCreditWalletState(
        user_id=202,
        allocated_credits=Decimal("100.00"),
        consumed_credits=Decimal("0.00"),
        is_oppyfy_enabled=False,
    )
    failed_disabled = deduct_worker_credits(disabled_wallet, Decimal("5.00"))
    assert failed_disabled.allowed is False
    assert failed_disabled.reason_code == "OPPYFY_DISABLED_FOR_WORKER"


def test_worker_quota_policies_and_ceilings() -> None:
    """Verifica políticas de cuota por consulta, cuota diaria y techo acumulado del trabajador."""
    policy = WorkerQuotaPolicy(
        max_daily_credits=Decimal("50.00"),
        max_per_query_credits=Decimal("10.00"),
        assigned_credit_ceiling=Decimal("200.00"),
    )

    wallet = WorkerCreditWalletState(
        user_id=303,
        allocated_credits=Decimal("500.00"),
        consumed_credits=Decimal("150.00"),
        is_oppyfy_enabled=True,
        assigned_credit_ceiling=Decimal("200.00"),
    )
    assert wallet.remaining_credits == Decimal("350.00")
    assert wallet.is_ceiling_reached is False

    # 1. Rechazo por exceder cuota por consulta (12.00 > 10.00)
    res_query_over = deduct_worker_credits(
        wallet,
        Decimal("12.00"),
        quota_policy=policy,
        daily_consumed_credits=Decimal("10.00"),
    )
    assert res_query_over.allowed is False
    assert res_query_over.reason_code == "EXCEEDS_PER_QUERY_QUOTA"

    # 2. Rechazo por exceder cuota diaria (48.00 + 5.00 > 50.00)
    res_daily_over = deduct_worker_credits(
        wallet,
        Decimal("5.00"),
        quota_policy=policy,
        daily_consumed_credits=Decimal("48.00"),
    )
    assert res_daily_over.allowed is False
    assert res_daily_over.reason_code == "EXCEEDS_DAILY_QUOTA"

    # 3. Rechazo por exceder techo acumulado (150.00 + 60.00 = 210.00 > 200.00)
    res_ceiling_over = deduct_worker_credits(
        wallet,
        Decimal("60.00"),
        quota_policy=policy,
    )
    assert res_ceiling_over.allowed is False
    assert res_ceiling_over.reason_code == "WORKER_CREDIT_CEILING_EXCEEDED"

    # 4. Aprobado dentro de todas las cuotas
    res_ok = deduct_worker_credits(
        wallet,
        Decimal("8.00"),
        quota_policy=policy,
        daily_consumed_credits=Decimal("20.00"),
    )
    assert res_ok.allowed is True
    assert res_ok.updated_wallet.consumed_credits == Decimal("158.00")


# ==============================================================================
# 3. AI CREDIT PACKS & BASE PLAN MATCHING
# ==============================================================================


def test_ai_credit_packs_domain_entity_and_calculations() -> None:
    """Verifica la entidad AiCreditPack, cálculo de bonos y costo unitario en USD/CLP."""
    pack = AiCreditPack(
        pack_id=uuid.uuid4(),
        slug="pack_pro_5k",
        name="Paquete 5.000 + 500 Bono",
        credit_amount=Decimal("5000.00"),
        bonus_credits=Decimal("500.00"),
        price_clp=Decimal("44990.00"),
        price_usd=Decimal("50.00"),
        plan_tier_discounts={
            "plan_basico": Decimal("0.00"),
            "plan_pro": Decimal("10.00"),
            "plan_enterprise": Decimal("20.00"),
        },
    )
    assert pack.total_credits == Decimal("5500.00")
    # Costo por crédito USD: 50.00 / 5500 = 0.009091
    assert pack.cost_per_credit_usd == Decimal("0.009091")
    # Costo por crédito CLP: 44990.00 / 5500 = 8.18
    assert pack.cost_per_credit_clp == Decimal("8.18")


def test_ai_credit_packs_base_plan_matching_and_discounts() -> None:
    """Verifica que los paquetes hagan juego comercialmente con los planes base SaaS contratados."""
    pack = AiCreditPack(
        pack_id=uuid.uuid4(),
        slug="pack_corporate",
        name="Pack Corporativo",
        credit_amount=Decimal("10000.00"),
        price_clp=Decimal("80000.00"),
        price_usd=Decimal("100.00"),
        plan_tier_discounts={
            "plan_basico": Decimal("0.00"),
            "plan_pro": Decimal("15.00"),
            "plan_enterprise": Decimal("25.00"),
        },
    )

    # Plan Básico: 0% descuento -> 100.00 USD / 80.000 CLP
    disc_b, usd_b, clp_b = evaluate_pack_plan_match(pack, "plan_basico")
    assert disc_b == Decimal("0.00")
    assert usd_b == Decimal("100.00")
    assert clp_b == Decimal("80000.00")

    # Plan Pro: 15% descuento -> 85.00 USD / 68.000 CLP
    disc_p, usd_p, clp_p = evaluate_pack_plan_match(pack, "plan_pro")
    assert disc_p == Decimal("15.00")
    assert usd_p == Decimal("85.00")
    assert clp_p == Decimal("68000.00")

    # Plan Enterprise: 25% descuento -> 75.00 USD / 60.000 CLP
    disc_e, usd_e, clp_e = evaluate_pack_plan_match(pack, "plan_enterprise")
    assert disc_e == Decimal("25.00")
    assert usd_e == Decimal("75.00")
    assert clp_e == Decimal("60000.00")


def test_stack_ai_credit_packs_domain_helper() -> None:
    """Verifica stack_ai_credit_packs sumando paquetes con bonificaciones."""
    p1 = AiCreditPack(
        pack_id=uuid.uuid4(),
        slug="p1",
        name="Pack 1",
        credit_amount=Decimal("1000.00"),
        bonus_credits=Decimal("100.00"),
        price_clp=Decimal("9990.00"),
        price_usd=Decimal("11.00"),
    )
    p2 = AiCreditPack(
        pack_id=uuid.uuid4(),
        slug="p2",
        name="Pack 2",
        credit_amount=Decimal("2000.00"),
        price_clp=Decimal("19990.00"),
        price_usd=Decimal("22.00"),
    )
    total = stack_ai_credit_packs(Decimal("500.00"), (p1, p2))
    assert total == Decimal("3600.00")  # 500 + 1100 + 2000


# ==============================================================================
# 4. OPPYFY RBAC, CAPABILITIES & TRIPLE EXPIRATION
# ==============================================================================


def test_oppyfy_rbac_domains_and_subdomains_specs() -> None:
    """Verifica especificaciones inmutables de dominios, subdominios y capacidades."""
    domain = EditableOppyfyDomainSpec(
        id=1,
        slug="gastronomia",
        name="Gastronomía y Operaciones",
        is_enabled=True,
        icon="utensils",
        sort_order=1,
    )
    assert domain.slug == "gastronomia"
    assert domain.is_enabled is True

    subdomain = EditableOppyfySubdomainSpec(
        id=10,
        domain_id=1,
        slug="recetas_cocina",
        name="Escandallo de Recetas",
        bound_tool_codes=("get_recipe_cost", "simulate_menu_margin"),
        module_slug="oppy_ai",
        can_view_costs_default=False,
    )
    assert subdomain.bound_tool_codes == ("get_recipe_cost", "simulate_menu_margin")
    assert OppyfyCapability.QUERY_AI == "oppyfy.capability.query_ai"
    assert OppyfyCapability.VIEW_FINANCIAL_COSTS == "oppyfy.capability.view_financial_costs"


def test_oppyfy_rbac_owner_bypass_and_uncontracted_module() -> None:
    """Verifica que el Propietario (Rank 0) tenga acceso irrestricto y que módulos no contratados denieguen."""
    # Propietario Rank 0
    decision_owner = evaluate_oppyfy_subdomain_access(
        user_id=1,
        role_ids=(1,),
        hierarchy_rank=0,
        target_subdomain_slug="recetas_cocina",
        grants=(),
        contracted_modules=("oppy_ai", "inventory"),
    )
    assert decision_owner.allowed is True
    assert decision_owner.can_view_costs is True
    assert decision_owner.audit_code == ALLOWED_PROMPT_STATUS

    # Módulo no contratado en el plan del Tenant
    decision_uncontracted = evaluate_oppyfy_subdomain_access(
        user_id=2,
        role_ids=(2,),
        hierarchy_rank=3,
        target_subdomain_slug="banquetes",
        grants=(),
        contracted_modules=("inventory",),
        subdomain_module_slug="oppy_ai",
    )
    assert decision_uncontracted.allowed is False
    assert decision_uncontracted.audit_code == BLOCKED_UNAUTHORIZED_PROMPT
    assert decision_uncontracted.denial_reason == "MODULE_NOT_CONTRACTED_IN_PLAN"


def test_oppyfy_rbac_triple_expiration_mechanisms() -> None:
    """Verifica la triple caducidad temporal: expires_at, max_prompts y temp_credit_ceiling."""
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)

    # 1. Caducidad por fecha/hora (expires_at)
    grant_expired_time = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=10,
        subdomain_slug="fefo_alerts",
        user_id=42,
        expires_at=fixed_now - timedelta(minutes=5),  # Expirado
    )
    valid, reason = is_grant_currently_valid(
        grant_expired_time, estimated_cost=Decimal("1.00"), now=fixed_now
    )
    assert valid is False
    assert reason == "GRANT_EXPIRED_BY_TIMESTAMP"

    # 2. Caducidad por cantidad máxima de prompts (max_prompts)
    grant_expired_prompts = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=10,
        subdomain_slug="fefo_alerts",
        user_id=42,
        max_prompts=5,
        used_prompts=5,  # Límite alcanzado
    )
    valid_p, reason_p = is_grant_currently_valid(
        grant_expired_prompts, estimated_cost=Decimal("1.00"), now=fixed_now
    )
    assert valid_p is False
    assert reason_p == "GRANT_EXPIRED_BY_MAX_PROMPTS"

    # 3. Caducidad por techo de créditos (temp_credit_ceiling)
    grant_expired_credits = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=10,
        subdomain_slug="fefo_alerts",
        user_id=42,
        temp_credit_ceiling=Decimal("10.00"),
        credits_used_in_grant=Decimal("9.50"),
    )
    # Consulta de 1.00 excede el remanente de 0.50
    valid_c, reason_c = is_grant_currently_valid(
        grant_expired_credits, estimated_cost=Decimal("1.00"), now=fixed_now
    )
    assert valid_c is False
    assert reason_c == "GRANT_EXPIRED_BY_CREDIT_CEILING"

    # Concesión vigente dentro de los 3 límites
    grant_valid = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=10,
        subdomain_slug="fefo_alerts",
        user_id=42,
        expires_at=fixed_now + timedelta(hours=2),
        max_prompts=10,
        used_prompts=3,
        temp_credit_ceiling=Decimal("50.00"),
        credits_used_in_grant=Decimal("12.00"),
    )
    valid_ok, reason_ok = is_grant_currently_valid(
        grant_valid, estimated_cost=Decimal("2.00"), now=fixed_now
    )
    assert valid_ok is True
    assert reason_ok is None

    # Consumo de cuota con la primitiva pura consume_grant_quota
    updated_grant = consume_grant_quota(grant_valid, credits_spent=Decimal("2.00"))
    assert updated_grant.used_prompts == 4
    assert updated_grant.credits_used_in_grant == Decimal("14.00")


def test_oppyfy_rbac_explicit_deny_and_unauthorized_prompt() -> None:
    """Verifica que un DENY explícito anule cualquier ALLOW y que falta de grant retorne BLOCKED_UNAUTHORIZED_PROMPT."""
    grant_allow = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=20,
        subdomain_slug="suppliers_lead_time",
        role_id=5,
        effect="ALLOW",
        can_view_costs=False,
    )
    grant_deny = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=20,
        subdomain_slug="suppliers_lead_time",
        user_id=88,
        effect="DENY",
    )

    # Usuario con ALLOW por rol pero DENY específico por usuario
    decision = evaluate_oppyfy_subdomain_access(
        user_id=88,
        role_ids=(5,),
        hierarchy_rank=4,
        target_subdomain_slug="suppliers_lead_time",
        grants=(grant_allow, grant_deny),
    )
    assert decision.allowed is False
    assert decision.audit_code == BLOCKED_UNAUTHORIZED_PROMPT
    assert decision.denial_reason == "EXPLICIT_DENY_GRANT"

    # Usuario sin ninguna concesión
    decision_no_grant = evaluate_oppyfy_subdomain_access(
        user_id=99,
        role_ids=(9,),
        hierarchy_rank=4,
        target_subdomain_slug="suppliers_lead_time",
        grants=(),
    )
    assert decision_no_grant.allowed is False
    assert decision_no_grant.audit_code == BLOCKED_UNAUTHORIZED_PROMPT
    assert decision_no_grant.denial_reason == "NO_MATCHING_OPPYFY_GRANT"


def test_oppyfy_rbac_hierarchical_delegation() -> None:
    """Verifica reglas de delegación por jerarquía (Propietario Rank 0 y superiores Rank N)."""
    # Propietario (Rank 0) puede delegar a cualquiera
    assert validate_hierarchical_delegation(
        grantor_rank=0, grantee_rank=3, grantor_has_subdomain_permission=False
    ) is True

    # Superior (Rank 2) delegando a subordinado (Rank 4): permitido si posee el permiso
    assert validate_hierarchical_delegation(
        grantor_rank=2, grantee_rank=4, grantor_has_subdomain_permission=True
    ) is True

    # Superior (Rank 2) que no tiene el permiso intenta delegarlo: rechazo
    assert validate_hierarchical_delegation(
        grantor_rank=2, grantee_rank=4, grantor_has_subdomain_permission=False
    ) is False

    # Subordinado (Rank 4) intentando delegar a superior (Rank 2): rechazo
    assert validate_hierarchical_delegation(
        grantor_rank=4, grantee_rank=2, grantor_has_subdomain_permission=True
    ) is False


def test_oppyfy_rbac_hard_code_cost_redaction() -> None:
    """Verifica redacción física estricta en código duro cuando can_view_costs=False."""
    payload = {
        "item_name": "Salmón Fresco 1kg",
        "stock_units": 45,
        "costo_unitario": Decimal("8500.00"),
        "precio_compra": Decimal("8000.00"),
        "margen_bruto": Decimal("35.50"),
        "suppliers": [
            {
                "vendor_name": "Pesquera Austral",
                "lead_time_days": 2,
                "unit_cost": Decimal("8200.00"),
            }
        ],
    }

    # Autorizado para ver costos -> payload intacto
    allowed_view = redact_cost_fields(payload, can_view_costs=True)
    assert allowed_view["costo_unitario"] == Decimal("8500.00")
    assert allowed_view["suppliers"][0]["unit_cost"] == Decimal("8200.00")

    # No autorizado para ver costos -> redacción en código duro
    redacted = redact_cost_fields(payload, can_view_costs=False)
    assert redacted["item_name"] == "Salmón Fresco 1kg"
    assert redacted["stock_units"] == 45
    assert redacted["costo_unitario"] == REDACTED_COST_MARKER
    assert redacted["precio_compra"] == REDACTED_COST_MARKER
    assert redacted["margen_bruto"] == REDACTED_COST_MARKER
    assert redacted["suppliers"][0]["vendor_name"] == "Pesquera Austral"
    assert redacted["suppliers"][0]["unit_cost"] == REDACTED_COST_MARKER
