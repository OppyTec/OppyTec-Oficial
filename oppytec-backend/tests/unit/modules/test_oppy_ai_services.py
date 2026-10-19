"""
Pruebas unitarias 1:1 para `src/modules/oppy_ai/` y `scripts/db_migration.py`.
Verifica `LlmRequestLog` (`PublicBase`), dominios editables de `OppyFy` (`TenantBase`),
billetera acumulable sin caducidad (`AiCreditPackage`) y CLI de migraciones correlativas.
"""
from __future__ import annotations

import uuid
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
