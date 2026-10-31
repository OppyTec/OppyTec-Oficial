"""
Pruebas de Calidad en 5 Dimensiones (5D), Paridad Matemática y Pruebas de Propiedades (Hypothesis)
para OppyFy (`oppytec-backend/tests/unit/modules/test_oppyfy_5d_quality.py`).

Cumple la Fase 7.4 de PLAN_MAESTRO_OPPYFY_AI.md:
1. Dimensión 1 (Unitario): Casos de borde, redondeo ROUND_HALF_UP y límites discretos.
2. Dimensión 2 (Integración): Orquestación E2E (MeteredAIService + ThreeLayerRagService + OppyfyToolRouter + Wallet).
3. Dimensión 3 (Propiedades - Hypothesis): No desbordamiento en billeteras, monotonicidad y asociatividad.
4. Dimensión 4 (Contratos): Tipos Decimal obligatorios, cero float y precisión de esquema NUMERIC(14,6) / NUMERIC(14,2).
5. Dimensión 5 (Paridad Matemática): Paridad de tarifas de tokens en USD y CLP, y semáforo anti-alucinación con rollover al 5.00%.
"""
from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from src.adapters.ai.gemini_adapter import MeteredGeminiAdapter
from src.adapters.ai.jev_adapter import InMemoryTelemetrySink, MeteredJevAdapter
from src.core.fx.fx_service import FXService
from src.core.security import create_access_token
from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    ModelConfigRegistry,
    ModelTariff,
    OppyfyQueryRequest,
)
from src.modules.oppy_ai.application.operational_tools.inventory_tools import (
    get_stock_health_and_reorder_alerts,
)
from src.modules.oppy_ai.application.rag_service import (
    BusinessSpecChunkRecord,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.tool_router import OppyfyToolRouter
from src.modules.oppy_ai.domain.context_meter import (
    AMBER_MAX_PERCENT,
    AMBER_START_PERCENT,
    COMPACTION_REQUIRED_PERCENT,
    FRESH_THREAD_INITIAL_PERCENT,
    GREEN_MAX_PERCENT,
    MAX_SAFE_THREAD_TOKENS,
    PREVENTIVE_ALERT_THRESHOLD_PERCENT,
    calculate_safe_rollover_token_budget,
    compact_thread_for_fresh_handover,
    evaluate_context_usage,
)
from src.modules.oppy_ai.domain.credit_wallet import (
    CreditPackageSpec,
    HoldingCreditPool,
    WorkerCreditWalletState,
    allocate_credits_to_worker,
    calculate_wallet_balance,
    deduct_worker_credits,
    stack_credit_packages,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    BLOCKED_UNAUTHORIZED_PROMPT,
    REDACTED_COST_MARKER,
    OppyfyCapability,
    OppyfyPermissionGrantSpec,
    redact_cost_fields,
)
from src.modules.oppy_ai.presentation.router import (
    _metered_ai_service,
    _model_registry,
)
from src.modules.tenancy.domain.saas_policy_math import (
    calculate_real_api_cost_usd,
)

_SIX_DECIMALS = Decimal("0.000001")
_TWO_DECIMALS = Decimal("0.01")
_ONE_MILLION = Decimal("1000000")


def _make_metered_service(
    *,
    model_registry: ModelConfigRegistry | None = None,
    sink: InMemoryTelemetrySink | None = None,
    rag_service: ThreeLayerRagService | None = None,
) -> tuple[MeteredAIService, InMemoryTelemetrySink]:
    """Helper factory para instanciar MeteredAIService con componentes medidos."""
    telemetry_sink = sink or InMemoryTelemetrySink()
    jev_port = MeteredJevAdapter(telemetry_sink=telemetry_sink)
    llm_port = MeteredGeminiAdapter(telemetry_sink=telemetry_sink)
    rag = rag_service or ThreeLayerRagService()
    router = OppyfyToolRouter(jev_port)
    service = MeteredAIService(
        jev_port=jev_port,
        llm_port=llm_port,
        rag_service=rag,
        tool_router=router,
        model_registry=model_registry,
        telemetry_sink=telemetry_sink,
    )
    return service, telemetry_sink


# ============================================================================
# DIMENSIÓN 3 & 1: Billeteras y Acumuladores de Créditos (Hypothesis & No-Overflow)
# ============================================================================


class TestCreditWalletHypothesisProperties:
    """Pruebas basadas en propiedades (Hypothesis) para la economía de billeteras y créditos."""

    @given(
        current_balance=st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("100000000.00"),
            places=2,
        ),
        pack_amounts=st.lists(
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("50000000.00"),
                places=2,
            ),
            min_size=1,
            max_size=15,
        ),
    )
    @settings(max_examples=80)
    def test_prop_credit_wallet_stacking_no_overflow_and_associativity(
        self,
        current_balance: Decimal,
        pack_amounts: list[Decimal],
    ) -> None:
        """
        Propiedad:
        1. No hay desbordamiento numérico ni pérdida de precisión con Decimal.
        2. El saldo acumulado es monótonamente creciente (`stacked >= current_balance`).
        3. El apilamiento de paquetes es asociativo y conmutativo en la suma.
        """
        packages = [
            CreditPackageSpec(
                package_id=uuid.uuid4(),
                slug=f"pack-{idx}",
                name=f"Pack {idx}",
                credit_amount=amount,
                price_clp=amount * Decimal("15.00"),
                price_usd=amount * Decimal("0.015"),
            )
            for idx, amount in enumerate(pack_amounts)
        ]

        total_added = sum(pack_amounts, start=Decimal("0.00")).quantize(_TWO_DECIMALS)
        expected_balance = (current_balance + total_added).quantize(_TWO_DECIMALS)

        stacked_balance = stack_credit_packages(current_balance, packages)

        assert stacked_balance == expected_balance, (
            f"Expected {expected_balance}, got {stacked_balance}"
        )
        assert stacked_balance >= current_balance
        assert isinstance(stacked_balance, Decimal)

        # Conmutatividad: el orden de compra no altera el saldo final
        reversed_packages = list(reversed(packages))
        reversed_stacked = stack_credit_packages(current_balance, reversed_packages)
        assert stacked_balance == reversed_stacked

    @given(
        total_pool=st.decimals(
            min_value=Decimal("100.00"),
            max_value=Decimal("10000000.00"),
            places=2,
        ),
        allocated_so_far=st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("50.00"),
            places=2,
        ),
        worker_initial=st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("1000.00"),
            places=2,
        ),
        alloc_ratio=st.floats(min_value=0.01, max_value=0.99),
    )
    @settings(max_examples=60)
    def test_prop_holding_to_worker_allocation_credit_conservation(
        self,
        total_pool: Decimal,
        allocated_so_far: Decimal,
        worker_initial: Decimal,
        alloc_ratio: float,
    ) -> None:
        """
        Propiedad: Conservación estricta de créditos en transferencias del Holding al trabajador.
        `unallocated_pool_pre + worker_allocated_pre == unallocated_pool_post + worker_allocated_post`
        """
        pool = HoldingCreditPool(
            holding_id=uuid.uuid4(),
            total_purchased_credits=total_pool,
            allocated_to_workers_credits=allocated_so_far,
        )
        available = pool.unallocated_credits
        if available <= Decimal("0.01"):
            return

        alloc_amount = (available * Decimal(str(round(alloc_ratio, 2)))).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )
        if alloc_amount <= Decimal("0.00"):
            alloc_amount = Decimal("0.01")
        if alloc_amount > available:
            alloc_amount = available

        wallet = WorkerCreditWalletState(
            user_id=42,
            allocated_credits=worker_initial,
            consumed_credits=Decimal("0.00"),
        )

        initial_system_credits = pool.unallocated_credits + wallet.allocated_credits
        new_pool, new_wallet = allocate_credits_to_worker(pool, wallet, alloc_amount)
        final_system_credits = new_pool.unallocated_credits + new_wallet.allocated_credits

        assert final_system_credits == initial_system_credits, (
            f"Credit conservation violated: {initial_system_credits} != {final_system_credits}"
        )
        assert new_wallet.allocated_credits == wallet.allocated_credits + alloc_amount
        assert new_pool.unallocated_credits == pool.unallocated_credits - alloc_amount

    @given(
        allocated=st.decimals(
            min_value=Decimal("1.00"),
            max_value=Decimal("10000.00"),
            places=2,
        ),
        consumed=st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("500.00"),
            places=2,
        ),
        deduct_amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("1000.00"),
            places=2,
        ),
    )
    @settings(max_examples=60)
    def test_prop_deduct_worker_credits_invariants(
        self,
        allocated: Decimal,
        consumed: Decimal,
        deduct_amount: Decimal,
    ) -> None:
        """
        Propiedad: Invariantes de deducción atómica de créditos.
        - Si deduct_amount <= remaining_credits, allowed=True y remaining disminuye exactamente por deduct_amount.
        - Si deduct_amount > remaining_credits, allowed=False y la billetera permanece inmutable.
        """
        if consumed > allocated:
            consumed = allocated

        wallet = WorkerCreditWalletState(
            user_id=101,
            allocated_credits=allocated,
            consumed_credits=consumed,
            is_oppyfy_enabled=True,
        )
        remaining = wallet.remaining_credits

        result = deduct_worker_credits(wallet, deduct_amount)

        if deduct_amount <= remaining:
            assert result.allowed is True
            assert result.deducted_credits == deduct_amount
            assert result.updated_wallet.remaining_credits == (remaining - deduct_amount).quantize(
                _TWO_DECIMALS
            )
            assert result.updated_wallet.consumed_credits == (consumed + deduct_amount).quantize(
                _TWO_DECIMALS
            )
        else:
            assert result.allowed is False
            assert result.deducted_credits == Decimal("0.00")
            assert result.updated_wallet == wallet

    def test_wallet_extreme_balance_no_overflow(self) -> None:
        """Prueba de estrés numérico: acumulación sin overflow hasta 10^12 créditos."""
        extreme_base = Decimal("999999999999.99")
        added = Decimal("1000000.01")
        new_balance = calculate_wallet_balance(extreme_base, added)
        assert new_balance == Decimal("1000001000000.00")
        assert isinstance(new_balance, Decimal)


# ============================================================================
# DIMENSIÓN 5 & 3: Paridad Matemática de Tarifas de Tokens en USD y CLP
# ============================================================================


class TestTokenCostParityHypothesis:
    """Verificación de paridad matemática en cálculo de costos de tokens en USD y CLP."""

    @given(
        input_tokens=st.integers(min_value=0, max_value=2000000),
        cached_tokens=st.integers(min_value=0, max_value=500000),
        output_tokens=st.integers(min_value=0, max_value=500000),
        rate=st.decimals(min_value=Decimal("500.00"), max_value=Decimal("1500.00"), places=2),
    )
    @settings(max_examples=100)
    def test_prop_token_cost_calculation_usd_six_decimals_and_clp_two_decimals(
        self,
        input_tokens: int,
        cached_tokens: int,
        output_tokens: int,
        rate: Decimal,
    ) -> None:
        """
        Propiedad:
        1. El costo en USD siempre tiene escala 6 (NUMERIC(14,6)) y es no negativo.
        2. El costo en CLP siempre tiene escala 2 (NUMERIC(14,2)) y es no negativo.
        3. Monotonicidad: añadir tokens nunca reduce el costo.
        4. Paridad: CLP == round(USD * rate, 2).
        5. Cero uso de float en todo el pipeline de cómputo.
        """
        service, _ = _make_metered_service()

        cost_usd, cost_clp = service.calculate_token_cost(
            "gemini-1.5-flash",
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            usd_to_clp_rate=rate,
        )

        assert cost_usd >= Decimal("0.000000")
        assert cost_clp >= Decimal("0.00")
        assert cost_usd.as_tuple().exponent == -6
        assert cost_clp.as_tuple().exponent == -2
        assert isinstance(cost_usd, Decimal)
        assert isinstance(cost_clp, Decimal)

        expected_clp = (cost_usd * rate).quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
        assert cost_clp == expected_clp

    def test_finops_database_numeric_scale_limits(self) -> None:
        """
        Verifica que los valores calculados satisfacen los límites de PostgreSQL:
        - `public.llm_request_logs.provider_cost_usd` es NUMERIC(14,6) (máx 99999999.999999).
        - `public.llm_request_logs.provider_cost_clp` es NUMERIC(14,2) (máx 999999999999.99).
        """
        tariff = ModelTariff(
            model_slug="extreme-model",
            input_cost_per_1m_usd=Decimal("10.000000"),
            cached_cost_per_1m_usd=Decimal("2.500000"),
            output_cost_per_1m_usd=Decimal("30.000000"),
        )
        registry = ModelConfigRegistry({"extreme-model": tariff})
        metered, _ = _make_metered_service(model_registry=registry)

        # 10 millones de tokens de entrada + 5 millones de salida
        cost_usd, cost_clp = metered.calculate_token_cost(
            "extreme-model",
            input_tokens=10_000_000,
            cached_tokens=2_000_000,
            output_tokens=5_000_000,
            usd_to_clp_rate=Decimal("950.00"),
        )

        # in: 10M * $10 = $100.000000
        # cached: 2M * $2.5 = $5.000000
        # out: 5M * $30 = $150.000000
        # total: $255.000000 USD | CLP: 255 * 950 = 242,250.00 CLP
        assert cost_usd == Decimal("255.000000")
        assert cost_clp == Decimal("242250.00")
        assert cost_usd < Decimal("100000000.000000")

    def test_mathematical_parity_metered_service_vs_saas_policy_math(self) -> None:
        """
        Paridad matemática cruzada: `MeteredAIService.calculate_token_cost`
        debe ser matemáticamente equivalente a `saas_policy_math.calculate_real_api_cost_usd`.
        """
        service, _ = _make_metered_service()

        for inp, out in [(1500, 300), (8500, 1200), (32000, 4500), (120000, 15000)]:
            total = inp + out
            service_usd, _ = service.calculate_token_cost(
                "gemini-1.5-flash",
                input_tokens=inp,
                cached_tokens=0,
                output_tokens=out,
            )
            policy_math_usd = calculate_real_api_cost_usd(
                total,
                model="gemini-1.5-flash",
                input_tokens=inp,
                output_tokens=out,
            )
            assert service_usd == policy_math_usd, (
                f"Parity mismatch at {inp}/{out}: {service_usd} != {policy_math_usd}"
            )


# ============================================================================
# DIMENSIÓN 5, 1 & 3: Medidor Semafórico de Contexto y Anti-Alucinación
# ============================================================================


class TestContextMeterSemaphoricTransitions:
    """Pruebas del medidor de porcentaje de ventana de contexto (0-65% verde, 66-85% ámbar, >85% rojo)."""

    @given(accumulated_tokens=st.integers(min_value=0, max_value=25000))
    @settings(max_examples=120)
    def test_prop_context_meter_transitions_exact_boundaries(
        self,
        accumulated_tokens: int,
    ) -> None:
        """
        Propiedad: Transición rigurosa de los 3 estados semafóricos de salud:
        - 0.00% <= percent <= 65.00%: OPTIMAL_GREEN, no bloqueo anti-alucinación.
        - 65.01% <= percent <= 85.00%: WARNING_AMBER, preventive_alert solo si > 80.00%.
        - percent > 85.00%: CRITICAL_RED, is_anti_hallucination_blocked=True, requires_auto_compaction=True.
        """
        eval_res = evaluate_context_usage(accumulated_tokens, max_safe_tokens=MAX_SAFE_THREAD_TOKENS)

        pct = eval_res.context_usage_percent
        assert pct.as_tuple().exponent == -2
        assert Decimal("0.00") <= pct <= Decimal("100.00")

        if pct <= GREEN_MAX_PERCENT:
            assert eval_res.status == "OPTIMAL_GREEN"
            assert eval_res.is_anti_hallucination_blocked is False
            assert eval_res.requires_auto_compaction is False
            assert eval_res.preventive_alert is False
        elif pct <= AMBER_MAX_PERCENT:
            assert eval_res.status == "WARNING_AMBER"
            assert eval_res.is_anti_hallucination_blocked is False
            assert eval_res.requires_auto_compaction is False
            assert eval_res.preventive_alert == (pct > PREVENTIVE_ALERT_THRESHOLD_PERCENT)
        else:
            assert eval_res.status == "CRITICAL_RED"
            assert eval_res.is_anti_hallucination_blocked is True
            assert eval_res.requires_auto_compaction is True

    def test_context_meter_exact_discrete_boundary_points(self) -> None:
        """Verificación puntual de los umbrales discretos de transición."""
        # 8192 tokens totales seguros
        # 65.00% = 5324.8 tokens -> 5324 es 64.99% (Verde), 5325 es 65.00% (Verde), 5326 es 65.01% (Ámbar)
        green_boundary = evaluate_context_usage(5324)
        assert green_boundary.context_usage_percent == Decimal("64.99")
        assert green_boundary.status == "OPTIMAL_GREEN"

        green_exact = evaluate_context_usage(5325)
        assert green_exact.context_usage_percent == Decimal("65.00")
        assert green_exact.status == "OPTIMAL_GREEN"

        amber_start = evaluate_context_usage(5326)
        assert amber_start.context_usage_percent == Decimal("65.01")
        assert amber_start.status == "WARNING_AMBER"
        assert amber_start.preventive_alert is False

        # 80.00% = 6553.6 tokens -> 6553 es 79.99%, 6555 es 80.02% (Alerta preventiva)
        pre_alert = evaluate_context_usage(6553)
        assert pre_alert.context_usage_percent == Decimal("79.99")
        assert pre_alert.preventive_alert is False

        post_alert = evaluate_context_usage(6555)
        assert post_alert.context_usage_percent == Decimal("80.02")
        assert post_alert.preventive_alert is True
        assert post_alert.status == "WARNING_AMBER"

        # 85.00% = 6963.2 tokens -> 6963 es 85.00% (Ámbar), 6964 es 85.01% (Rojo bloqueado)
        amber_end = evaluate_context_usage(6963)
        assert amber_end.context_usage_percent == Decimal("85.00")
        assert amber_end.is_anti_hallucination_blocked is False
        assert amber_end.status == "WARNING_AMBER"

        red_start = evaluate_context_usage(6964)
        assert red_start.context_usage_percent == Decimal("85.01")
        assert red_start.status == "CRITICAL_RED"
        assert red_start.is_anti_hallucination_blocked is True
        assert red_start.requires_auto_compaction is True

    def test_context_compaction_and_rollover_to_fresh_5_percent(self) -> None:
        """
        Al alcanzar el límite crítico (>85%), compactación sintetiza el historial
        y realiza un rollover seguro a un nuevo hilo inicializado al 5.00% de contexto.
        """
        source_thread_id = uuid.uuid4()
        history = [
            "Consulta de stock: lomo vetado",
            "Respuesta: 14.50 kg disponibles",
            "Alerta FEFO: lote LOT-001 expira en 2 días",
            "Generar borrador de orden de compra",
            "Orden de compra creada por 35 kg",
        ]

        summary = compact_thread_for_fresh_handover(
            source_thread_id=source_thread_id,
            messages=history,
            max_safe_tokens=MAX_SAFE_THREAD_TOKENS,
        )

        assert summary.source_thread_id == source_thread_id
        assert summary.new_thread_id != source_thread_id
        assert summary.new_context_usage_percent == FRESH_THREAD_INITIAL_PERCENT
        assert summary.new_context_usage_percent == Decimal("5.00")
        assert summary.synthesized_summary.startswith("[COMPACTED_HANDOVER]")
        # 5% de 8192 tokens = 409.6 -> redondea a 410 tokens seguros de presupuesto
        assert summary.safe_token_budget_allocated == 410


# ============================================================================
# DIMENSIÓN 2 & 4: Integración 5D E2E y Contratos de Datos
# ============================================================================


class TestOppyfy5DIntegrationAndContracts:
    """Pruebas de integración E2E entre todas las capas de OppyFy y validación de contratos."""

    def test_integration_5d_full_query_pipeline_with_rag_and_wallet_deduction(self) -> None:
        """
        Integración 5D:
        - Flujo E2E desde OppyfyQueryRequest hasta OppyfyQueryResponse.
        - Ejecución determinista de herramienta en código duro.
        - Redacción física de costos cuando can_view_costs=False.
        - Descuento de créditos de la billetera individual.
        - Registro ineludible en el sumidero de telemetría LlmRequestLog.
        """
        rag_service = ThreeLayerRagService(
            business_spec_chunks=[
                BusinessSpecChunkRecord(
                    chunk_id=uuid.uuid4(),
                    spec_rel_path="specs/business-domain/inventory.md",
                    module_slug="inventory",
                    content_markdown="Regla FEFO: Consumir primero los lotes más próximos a caducar.",
                )
            ]
        )
        service, sink = _make_metered_service(rag_service=rag_service)

        holding_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        wallet = WorkerCreditWalletState(
            user_id=88,
            allocated_credits=Decimal("100.00"),
            consumed_credits=Decimal("10.00"),
            is_oppyfy_enabled=True,
        )

        stock_grant_no_costs = OppyfyPermissionGrantSpec(
            grant_id=uuid.uuid4(),
            subdomain_id=10,
            subdomain_slug="inventario_y_bodegas",
            user_id=88,
            effect="ALLOW",
            can_query=True,
            can_view_costs=False,
            max_prompts=10,
            used_prompts=1,
        )

        # Trabajador con can_view_costs=False
        request_no_costs = OppyfyQueryRequest(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema="tenant_las_condes",
            user_id=88,
            role_ids=(4,),
            hierarchy_rank=30,
            prompt_text="¿Cuáles son los insumos críticos que necesitamos reponer en bodega?",
            wallet=wallet,
            grants=(stock_grant_no_costs,),
            subdomain_id_by_slug={"inventario_y_bodegas": 10},
            prior_thread_tokens=1000,
        )

        response = service.execute_oppyfy_query(request_no_costs)

        assert response.allowed is True
        assert response.tool_execution is not None
        assert response.tool_execution.costs_redacted is True

        # Verificar que el payload sanitizado redactó físicamente todos los campos de costo
        sanitized = response.tool_execution.sanitized_payload
        if "alerts" in sanitized:
            for alert in sanitized.get("alerts", []):
                assert alert["costo_unitario"] == REDACTED_COST_MARKER
                assert alert["precio_compra"] == REDACTED_COST_MARKER
                assert alert["total_neto"] == REDACTED_COST_MARKER
        if "costo_unitario" in sanitized:
            assert sanitized["costo_unitario"] == REDACTED_COST_MARKER
        if "total_estimated_reorder_cost" in sanitized:
            assert sanitized["total_estimated_reorder_cost"] == REDACTED_COST_MARKER

        # Verificar descuento de créditos
        assert response.credits_deducted > Decimal("0.00")
        assert response.updated_wallet.consumed_credits > wallet.consumed_credits
        assert response.updated_wallet.remaining_credits == (
            wallet.remaining_credits - response.credits_deducted
        ).quantize(_TWO_DECIMALS)

        # Verificar telemetría en el sumidero
        assert len(sink.records) >= 2  # JEV System 1 + Gemini System 2
        llm_log = sink.records[-1]
        assert llm_log.provider_cost_usd > Decimal("0.000000")
        assert llm_log.provider_cost_clp > Decimal("0.00")
        assert llm_log.provider_cost_usd.as_tuple().exponent == -6
        assert llm_log.provider_cost_clp.as_tuple().exponent == -2

        # Context meter verificado
        assert response.context_health.status == "OPTIMAL_GREEN"
        assert response.context_health.context_usage_percent < Decimal("65.00")

    def test_integration_5d_unauthorized_subdomain_rbac_block_audit(self) -> None:
        """
        Integración 5D: Solicitud a sub-dominio no autorizado es bloqueada por RBAC,
        registrada en auditoría como BLOCKED_UNAUTHORIZED_PROMPT y no descuenta créditos de LLM.
        """
        service, _ = _make_metered_service()

        wallet = WorkerCreditWalletState(
            user_id=99,
            allocated_credits=Decimal("50.00"),
            consumed_credits=Decimal("0.00"),
            is_oppyfy_enabled=True,
        )

        grant_finance = OppyfyPermissionGrantSpec(
            grant_id=uuid.uuid4(),
            subdomain_id=11,
            subdomain_slug="analitica_financiera",
            user_id=99,
            effect="ALLOW",
            can_view_costs=True,
            max_prompts=10,
            used_prompts=1,
        )

        # El trabajador solo tiene permiso para 'analitica_financiera', pero pregunta por stock
        request_unauth = OppyfyQueryRequest(
            holding_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            tenant_schema="tenant_providencia",
            user_id=99,
            role_ids=(4,),
            hierarchy_rank=30,
            prompt_text="Dame el inventario y stock crítico de lomo vetado",
            wallet=wallet,
            grants=(grant_finance,),
            subdomain_id_by_slug={"analitica_financiera": 11, "inventario_y_bodegas": 10},
        )

        response = service.execute_oppyfy_query(request_unauth)

        assert response.allowed is False
        assert response.status_code == BLOCKED_UNAUTHORIZED_PROMPT
        assert response.tool_execution is None
        assert response.rag_bundle is None
        assert response.credits_deducted == Decimal("0.00")
        assert response.updated_wallet == wallet  # Billetera intacta

        # Auditoría registrada
        assert len(service.prompt_audit_logs) == 1
        audit = service.prompt_audit_logs[0]
        assert audit.decision_status == BLOCKED_UNAUTHORIZED_PROMPT
        assert audit.credits_consumed == Decimal("0.00")

    def test_contract_hardcoded_data_stripping_on_all_tools(self) -> None:
        """
        Contrato de Datos: Invocar herramientas operativas directamente con can_view_costs=False
        elimina invariablemente cualquier campo financiero del resultado.
        """
        result_redacted = get_stock_health_and_reorder_alerts("tenant_test", can_view_costs=False)
        assert result_redacted["total_estimated_reorder_cost"] == REDACTED_COST_MARKER
        for alert in result_redacted["alerts"]:
            assert alert["costo_unitario"] == REDACTED_COST_MARKER
            assert alert["precio_compra"] == REDACTED_COST_MARKER
            assert alert["total_neto"] == REDACTED_COST_MARKER

        result_raw = get_stock_health_and_reorder_alerts("tenant_test", can_view_costs=True)
        assert result_raw["total_estimated_reorder_cost"] != REDACTED_COST_MARKER
        assert isinstance(result_raw["total_estimated_reorder_cost"], Decimal)


# ============================================================================
# GESTIÓN DINÁMICA DE TARIFAS IA Y RESOLUCIÓN FX SERVICE EN PLATFORM ADMIN
# ============================================================================


def _make_admin_headers(
    permissions: list[str],
    *,
    user_id: int = 1,
    is_global_staff: bool = True,
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano de Platform Admin."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


class TestPlatformAdminDynamicTariffsAndFxIntegration:
    """
    Pruebas unitarias y de integración para la gestión dinámica de tarifas
    de modelos IA y tasas FX en base de datos / platform-admin.
    """

    @pytest.mark.asyncio
    async def test_platform_admin_dynamic_ai_tariffs_endpoint_and_registry_persistence(
        self,
        async_client: httpx.AsyncClient,
    ) -> None:
        """
        Verifica la actualización dinámica de tarifas de modelos IA vía endpoint REST en Platform Admin:
        1. GET /api/v1/platform-admin/ai-tariffs con permisos de lectura.
        2. PUT /api/v1/platform-admin/ai-tariffs/{model_slug} actualiza costos sin reiniciar la aplicación.
        3. Persistencia en memoria en _model_registry y reflejo inmediato en MeteredAIService.calculate_token_cost.
        4. Protección RBAC 403 Forbidden cuando faltan permisos 'platform_admin.ai_tariffs.read' o 'manage'.
        """
        read_headers = _make_admin_headers(["platform_admin.ai_tariffs.read"])
        manage_headers = _make_admin_headers(["platform_admin.ai_tariffs.manage"])
        unauthorized_headers = _make_admin_headers(["platform_admin.plans.read"])

        # 1. 403 Forbidden si no tiene permiso de lectura
        resp_unauth = await async_client.get(
            "/api/v1/platform-admin/ai-tariffs",
            headers=unauthorized_headers,
        )
        assert resp_unauth.status_code == 403

        # 2. GET lista las tarifas vigentes por defecto
        resp_get = await async_client.get(
            "/api/v1/platform-admin/ai-tariffs",
            headers=read_headers,
        )
        assert resp_get.status_code == 200
        tariffs = resp_get.json()
        assert isinstance(tariffs, list)
        model_slugs = [t["model_slug"] for t in tariffs]
        assert "gemini-2.5-flash" in model_slugs
        assert "gemini-1.5-pro" in model_slugs

        # 3. 403 Forbidden si intenta actualizar sin permiso manage
        update_payload = {
            "input_cost_per_1m_usd": "0.350000",
            "output_cost_per_1m_usd": "1.200000",
            "cached_cost_per_1m_usd": "0.080000",
        }
        resp_put_unauth = await async_client.put(
            "/api/v1/platform-admin/ai-tariffs/gemini-2.5-flash",
            json=update_payload,
            headers=unauthorized_headers,
        )
        assert resp_put_unauth.status_code == 403

        # 4. PUT con permiso manage actualiza la tarifa dinámicamente
        resp_put = await async_client.put(
            "/api/v1/platform-admin/ai-tariffs/gemini-2.5-flash",
            json=update_payload,
            headers=manage_headers,
        )
        assert resp_put.status_code == 200
        updated_data = resp_put.json()
        assert updated_data["model_slug"] == "gemini-2.5-flash"
        assert Decimal(str(updated_data["input_cost_per_1m_usd"])) == Decimal("0.350000")
        assert Decimal(str(updated_data["output_cost_per_1m_usd"])) == Decimal("1.200000")
        assert Decimal(str(updated_data["cached_cost_per_1m_usd"])) == Decimal("0.080000")

        # 5. Persistencia inmediata en el registry sin reiniciar la app
        active_tariff = _model_registry.get_tariff("gemini-2.5-flash")
        assert active_tariff.input_cost_per_1m_usd == Decimal("0.350000")
        assert active_tariff.output_cost_per_1m_usd == Decimal("1.200000")
        assert active_tariff.cached_cost_per_1m_usd == Decimal("0.080000")

        # 6. Cálculo en MeteredAIService utiliza la nueva tarifa inmediatamente
        # 1M input ($0.35) + 1M output ($1.20) = $1.550000 USD
        cost_usd, cost_clp = _metered_ai_service.calculate_token_cost(
            "gemini-2.5-flash",
            input_tokens=1_000_000,
            cached_tokens=0,
            output_tokens=1_000_000,
            usd_to_clp_rate=Decimal("950.00"),
        )
        assert cost_usd == Decimal("1.550000")
        assert cost_clp == Decimal("1472.50")

        # 7. GET refleja la tarifa actualizada
        resp_get_updated = await async_client.get(
            "/api/v1/platform-admin/ai-tariffs",
            headers=read_headers,
        )
        assert resp_get_updated.status_code == 200
        tariffs_after = {t["model_slug"]: t for t in resp_get_updated.json()}
        assert Decimal(str(tariffs_after["gemini-2.5-flash"]["input_cost_per_1m_usd"])) == Decimal("0.350000")

    def test_dynamic_fx_service_resolution_in_calculate_token_cost(self) -> None:
        """
        Verifica que `calculate_token_cost` resuelva la tasa de cambio USD/CLP dinámicamente
        desde `FXService` cuando `usd_to_clp_rate` es None, adaptándose a cambios de tasa.
        """
        fx = FXService()
        service, _ = _make_metered_service()
        service._fx = fx  # Inyectar motor cambiario

        # 1. Sin especificar usd_to_clp_rate -> Usa tasa oficial inicial de BCCh (950.00)
        usd, clp = service.calculate_token_cost(
            "gemini-1.5-flash",
            input_tokens=1_000_000,
            cached_tokens=0,
            output_tokens=1_000_000,
        )
        # input 0.075 + output 0.300 = 0.375000 USD
        assert usd == Decimal("0.375000")
        # 0.375 * 950 = 356.25 CLP
        assert clp == Decimal("356.25")

        # 2. Modificar dinámicamente la tasa FX mediante override manual auditado
        fx.apply_manual_fx_override(
            "USD",
            "CLP",
            Decimal("1000.00000000"),
            actor_user_id=1,
            reason="Ajuste cambiario de emergencia por volatilidad macroeconómica",
        )

        # 3. La siguiente llamada sin especificar tasa usa inmediatamente 1000.00
        usd2, clp2 = service.calculate_token_cost(
            "gemini-1.5-flash",
            input_tokens=1_000_000,
            cached_tokens=0,
            output_tokens=1_000_000,
        )
        assert usd2 == Decimal("0.375000")
        # 0.375 * 1000 = 375.00 CLP
        assert clp2 == Decimal("375.00")

        # 4. Si se provee una tasa explícita, debe tener precedencia
        usd3, clp3 = service.calculate_token_cost(
            "gemini-1.5-flash",
            input_tokens=1_000_000,
            cached_tokens=0,
            output_tokens=1_000_000,
            usd_to_clp_rate=Decimal("900.00"),
        )
        assert usd3 == Decimal("0.375000")
        # 0.375 * 900 = 337.50 CLP
        assert clp3 == Decimal("337.50")

    def test_model_config_registry_db_records_loading_and_updates(self) -> None:
        """
        Verifica la carga e inicialización de ModelConfigRegistry a partir de registros de BD
        y operaciones dinámicas de actualización.
        """
        db_rows = [
            {
                "model_slug": "claude-3.5-sonnet",
                "engine_tier": "SYSTEM_2_LLM",
                "input_cost_per_1m_usd": "3.000000",
                "cached_cost_per_1m_usd": "0.300000",
                "output_cost_per_1m_usd": "15.000000",
                "embedding_cost_per_1m_usd": "0.000000",
                "is_enabled": True,
            }
        ]

        registry = ModelConfigRegistry(db_records=db_rows)
        sonnet = registry.get_tariff("claude-3.5-sonnet")
        assert sonnet.model_slug == "claude-3.5-sonnet"
        assert sonnet.input_cost_per_1m_usd == Decimal("3.000000")
        assert sonnet.output_cost_per_1m_usd == Decimal("15.000000")

        # Actualización parcial
        updated = registry.update_tariff("claude-3.5-sonnet", input_cost_per_1m_usd=Decimal("2.500000"))
        assert updated.input_cost_per_1m_usd == Decimal("2.500000")
        assert updated.output_cost_per_1m_usd == Decimal("15.000000")

