"""
oppytec-backend/tests/unit/modules/test_jev_consumption_schemas.py
Pruebas unitarias de contratos Pydantic v2 para la Consola FinOps de Decisiones JEV:
- `JevLogItem`
- `JevTenantGroup`
- `JevHoldingGroup`
- `JevConsumptionSummaryResponse`
Valida:
1. Inmutabilidad y rigidez de esquema (`extra="forbid"`).
2. Precisión decimal estricta (`Decimal`, cero float).
3. Serialización Pydantic v2 compatible con OpenAPI y FastAPI.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.modules.tenancy.presentation.schemas_platform_admin import (
    JevConsumptionSummaryResponse,
    JevHoldingGroup,
    JevLogItem,
    JevTenantGroup,
)

pytestmark = pytest.mark.unit


def test_jev_log_item_creation_and_defaults() -> None:
    """Valida creación exitosa de JevLogItem y defaults de campos opcionales."""
    log_id = str(uuid.uuid4())
    holding_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    item = JevLogItem(
        id=log_id,
        created_at=now,
        holding_id=holding_id,
        holding_name="Holding Central",
        tenant_id=tenant_id,
        tenant_name="Sucursal Norte",
        tenant_schema="tenant_sucursal_norte",
        caller_feature="inventory_anomaly_detection",
        decision_id="dec_12345",
        decision_primitive="CLASSIFY",
        input_summary="Stock audit payload",
        result_value="NORMAL",
        confidence_score=Decimal("0.9950"),
        calibrated_action="AUTO_ACCEPTED",
        model_name="jev-decision-v1",
        estimated_tokens=42,
        provider_cost_usd=Decimal("0.000004"),
        provider_cost_clp=Decimal("0.00"),
        credits_deducted=Decimal("0.01"),
        latency_ms=12,
        is_success=True,
    )

    assert item.id == log_id
    assert item.user_id is None
    assert item.trace_id is None
    assert item.error_message is None
    assert isinstance(item.confidence_score, Decimal)
    assert isinstance(item.provider_cost_usd, Decimal)
    assert item.confidence_score == Decimal("0.9950")


def test_jev_log_item_extra_fields_forbidden() -> None:
    """Verifica que campos no declarados sean rechazados con ValidationError."""
    with pytest.raises(ValidationError):
        JevLogItem(  # type: ignore[call-arg]
            id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            holding_id=str(uuid.uuid4()),
            holding_name="Holding",
            tenant_id=str(uuid.uuid4()),
            tenant_name="Tenant",
            tenant_schema="tenant_schema",
            caller_feature="test",
            decision_id="dec_1",
            decision_primitive="ROUTE",
            input_summary="test",
            result_value="OK",
            confidence_score=Decimal("0.9000"),
            calibrated_action="AUTO_ACCEPTED",
            model_name="jev-v1",
            estimated_tokens=10,
            provider_cost_usd=Decimal("0.000100"),
            provider_cost_clp=Decimal("0.10"),
            credits_deducted=Decimal("0.05"),
            latency_ms=5,
            is_success=True,
            unauthorized_injection="malicious_payload",
        )


def test_jev_tenant_group_aggregation() -> None:
    """Valida agregación a nivel de TenantGroup con lista de logs."""
    tenant_group = JevTenantGroup(
        tenant_id=str(uuid.uuid4()),
        tenant_name="Tenant Alpha",
        tenant_schema="tenant_alpha",
        holding_id=str(uuid.uuid4()),
        total_decisions=100,
        total_cost_usd=Decimal("0.005000"),
        total_cost_clp=Decimal("5.00"),
        total_credits_deducted=Decimal("1.25"),
        avg_latency_ms=Decimal("15.42"),
        auto_accepted_count=95,
        flagged_warning_count=3,
        fallback_llm_count=2,
    )

    assert tenant_group.logs == []
    assert tenant_group.total_decisions == 100
    assert tenant_group.auto_accepted_count == 95
    assert isinstance(tenant_group.avg_latency_ms, Decimal)


def test_jev_holding_group_aggregation() -> None:
    """Valida agregación jerárquica a nivel de HoldingGroup con lista de tenants."""
    holding_group = JevHoldingGroup(
        holding_id=str(uuid.uuid4()),
        holding_name="Holding Corporativo",
        total_decisions=500,
        total_cost_usd=Decimal("0.025000"),
        total_cost_clp=Decimal("25.00"),
        total_credits_deducted=Decimal("6.25"),
        avg_latency_ms=Decimal("14.10"),
    )

    assert holding_group.tenants == []
    assert holding_group.total_decisions == 500


def test_jev_consumption_summary_response_complete_hierarchy() -> None:
    """Valida respuesta consolidada de la Consola FinOps JEV con jerarquía anidada y lista plana."""
    log = JevLogItem(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC),
        holding_id="h-1",
        holding_name="Holding 1",
        tenant_id="t-1",
        tenant_name="Tenant 1",
        tenant_schema="tenant_1",
        user_id=101,
        trace_id="trc_9988",
        caller_feature="invoice_parser",
        decision_id="dec_001",
        decision_primitive="EXTRACT",
        input_summary="Factura RUT 123",
        result_value="VALID",
        confidence_score=Decimal("0.9990"),
        calibrated_action="AUTO_ACCEPTED",
        model_name="jev-v1",
        estimated_tokens=50,
        provider_cost_usd=Decimal("0.000005"),
        provider_cost_clp=Decimal("0.01"),
        credits_deducted=Decimal("0.02"),
        latency_ms=8,
        is_success=True,
    )

    tenant_group = JevTenantGroup(
        tenant_id="t-1",
        tenant_name="Tenant 1",
        tenant_schema="tenant_1",
        holding_id="h-1",
        total_decisions=1,
        total_cost_usd=Decimal("0.000005"),
        total_cost_clp=Decimal("0.01"),
        total_credits_deducted=Decimal("0.02"),
        avg_latency_ms=Decimal("8.00"),
        auto_accepted_count=1,
        flagged_warning_count=0,
        fallback_llm_count=0,
        logs=[log],
    )

    holding_group = JevHoldingGroup(
        holding_id="h-1",
        holding_name="Holding 1",
        total_decisions=1,
        total_cost_usd=Decimal("0.000005"),
        total_cost_clp=Decimal("0.01"),
        total_credits_deducted=Decimal("0.02"),
        avg_latency_ms=Decimal("8.00"),
        tenants=[tenant_group],
    )

    summary = JevConsumptionSummaryResponse(
        total_decisions_all=1,
        total_cost_usd_all=Decimal("0.000005"),
        total_cost_clp_all=Decimal("0.01"),
        total_credits_deducted_all=Decimal("0.02"),
        avg_latency_ms_all=Decimal("8.00"),
        total_auto_accepted_all=1,
        total_flagged_warning_all=0,
        total_fallback_llm_all=0,
        estimated_savings_usd_all=Decimal("0.002995"),
        estimated_savings_clp_all=Decimal("2.99"),
        holdings=[holding_group],
        tenants=[tenant_group],
        all_logs=[log],
        page=1,
        page_size=50,
        total_logs_count=1,
    )

    # Verificación de tipos e integridad
    dump = summary.model_dump()
    assert dump["total_decisions_all"] == 1
    assert dump["holdings"][0]["holding_name"] == "Holding 1"
    assert dump["tenants"][0]["logs"][0]["id"] == log.id
    assert dump["all_logs"][0]["caller_feature"] == "invoice_parser"
    assert isinstance(summary.estimated_savings_usd_all, Decimal)
    assert isinstance(summary.estimated_savings_clp_all, Decimal)

    # Verificación de serialización JSON
    json_str = summary.model_dump_json()
    assert "invoice_parser" in json_str
    assert "Holding 1" in json_str
