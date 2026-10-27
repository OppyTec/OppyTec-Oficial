"""
oppytec-backend/tests/unit/modules/test_admin_plans_observability.py
Pruebas unitarias de observabilidad OpenTelemetry (4-Pilares) para administración
de Planes Comerciales, Política Global SaaS y Cuotas de Créditos IA:
- `platform_admin.plans.upsert` (create y update)
- `platform_admin.plans.delete` (delete)
- `tenancy.saas_policy.update`
- `platform_admin.tokens.quota_adjust` (holding y tenant)
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.core.observability import get_in_memory_exporter
from src.modules.tenancy.application.admin_plans_service import AdminPlansService
from src.modules.tenancy.application.credit_quota_adjustment_service import (
    CreditQuotaAdjustmentService,
)
from src.modules.tenancy.application.saas_policy_service import SaaSPolicyService

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_spans() -> None:
    get_in_memory_exporter().clear()


def test_admin_plans_service_spans() -> None:
    """Verifica que las operaciones de AdminPlansService emitan spans OpenTelemetry correctos."""
    service = AdminPlansService()
    exporter = get_in_memory_exporter()

    # 1. create_plan -> platform_admin.plans.upsert (create)
    new_plan = service.create_plan(
        {
            "slug": "plan-observability-test",
            "name": "Plan Observability Test",
            "tier": 2,
            "monthly_ai_credits": 3000,
            "price_clp": Decimal("45000.00"),
        }
    )
    spans = exporter.get_finished_spans()
    create_spans = [s for s in spans if s.name == "platform_admin.plans.upsert" and s.attributes.get("action") == "create"]
    assert len(create_spans) == 1
    create_span = create_spans[0]
    assert create_span.attributes.get("plan_slug") == "plan-observability-test"
    assert create_span.attributes.get("tier") == "2"
    assert create_span.status_code == 200

    # 2. update_plan -> platform_admin.plans.upsert (update)
    service.update_plan(
        "plan-observability-test",
        {"name": "Plan Observability Test Updated", "monthly_ai_credits": 4500},
    )
    spans = exporter.get_finished_spans()
    update_spans = [s for s in spans if s.name == "platform_admin.plans.upsert" and s.attributes.get("action") == "update"]
    assert len(update_spans) == 1
    update_span = update_spans[0]
    assert update_span.attributes.get("plan_slug") == "plan-observability-test"
    assert update_span.attributes.get("tier") == "2"
    assert update_span.status_code == 200

    # 3. delete_plan -> platform_admin.plans.delete (delete)
    service.delete_plan("plan-observability-test")
    spans = exporter.get_finished_spans()
    delete_spans = [s for s in spans if s.name == "platform_admin.plans.delete"]
    assert len(delete_spans) == 1
    delete_span = delete_spans[0]
    assert delete_span.attributes.get("action") == "delete"
    assert delete_span.attributes.get("plan_slug") == "plan-observability-test"
    assert delete_span.status_code == 200


def test_saas_policy_service_spans() -> None:
    """Verifica que update_policy_config emita el span tenancy.saas_policy.update."""
    service = SaaSPolicyService()
    exporter = get_in_memory_exporter()

    service.update_policy_config(
        tokens_per_credit=1500,
        default_monthly_credits=5000,
        actor_id=42,
    )
    spans = exporter.get_finished_spans()
    policy_spans = [s for s in spans if s.name == "tenancy.saas_policy.update"]
    assert len(policy_spans) == 1
    policy_span = policy_spans[0]
    assert policy_span.attributes.get("actor_id") == "42"
    # "token" es parte de SENSITIVE_KEY_TOKENS, por lo que scrub_telemetry_payload lo redacta a [REDACTED_PII]
    assert policy_span.attributes.get("tokens_per_credit") == "[REDACTED_PII]"
    assert policy_span.status_code == 200


def test_credit_quota_adjustment_service_spans() -> None:
    """Verifica que update_holding_credits y update_tenant_credits emitan platform_admin.tokens.quota_adjust."""
    service = CreditQuotaAdjustmentService()
    exporter = get_in_memory_exporter()

    # 1. update_holding_credits
    service.update_holding_credits(
        holding_id="holding_genesis",
        monthly_credits=8000,
        distribution_mode="shared",
        actor_id=10,
    )
    spans = exporter.get_finished_spans()
    holding_spans = [
        s for s in spans
        if s.name == "platform_admin.tokens.quota_adjust" and s.attributes.get("target_type") == "holding"
    ]
    assert len(holding_spans) == 1
    assert holding_spans[0].attributes.get("holding_id") == "holding_genesis"
    assert holding_spans[0].attributes.get("monthly_credits") == "8000"

    # 2. update_tenant_credits
    service.update_tenant_credits(
        tenant_id="tenant_genesis",
        monthly_credits=4000,
        actor_id=10,
    )
    spans = exporter.get_finished_spans()
    tenant_spans = [
        s for s in spans
        if s.name == "platform_admin.tokens.quota_adjust" and s.attributes.get("target_type") == "tenant"
    ]
    assert len(tenant_spans) == 1
    assert tenant_spans[0].attributes.get("tenant_id") == "tenant_genesis"
    assert tenant_spans[0].attributes.get("monthly_credits") == "4000"
