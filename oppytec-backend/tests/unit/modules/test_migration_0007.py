"""
Tests unitarios de la migración 0007 y modelos de SystemPlan y SaaSAIPolicyConfig.
(`test_migration_0007.py`).

Verifica:
1. Modelos `SystemPlan` extendido y `SaaSAIPolicyConfig` (`PublicBase`, `AuditTimestampsMixin`).
2. Tipos de datos, defaults, precisión Decimal y claves foráneas.
3. Migración Alembic 0007: metadata correlativa lineal, `upgrade()` idempotente y `downgrade()` simétrico.
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Integer, Numeric, SmallInteger, Text

from src.modules.tenancy.infrastructure.models import SaaSAIPolicyConfig, SystemPlan
from src.shared.models_base import AuditTimestampsMixin, PublicBase

pytestmark = [pytest.mark.unit]


def _load_migration_0007():
    mig_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0007_public_system_plans_extension_and_saas_policy.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0007", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_system_plan_extended_fields():
    """Valida los nuevos campos en SystemPlan: description, monthly_ai_credits, tier, is_popular, is_active."""
    plan = SystemPlan(
        slug="enterprise-ai",
        name="Plan Enterprise AI",
        description="Plan avanzado con cuota extendida de tokens",
        monthly_ai_credits=5000,
        tier=3,
        is_popular=True,
        is_active=True,
        price_clp=Decimal("199990.00"),
        price_usd=Decimal("249.00"),
    )

    assert plan.slug == "enterprise-ai"
    assert plan.description == "Plan avanzado con cuota extendida de tokens"
    assert plan.monthly_ai_credits == 5000
    assert plan.tier == 3
    assert plan.is_popular is True
    assert plan.is_active is True

    # Verificar presencia en SQLAlchemy Table
    table = SystemPlan.__table__
    assert "description" in table.c
    assert "monthly_ai_credits" in table.c
    assert "tier" in table.c
    assert "is_popular" in table.c
    assert "is_active" in table.c

    assert isinstance(table.c.description.type, Text)
    assert isinstance(table.c.monthly_ai_credits.type, Integer)
    assert isinstance(table.c.tier.type, SmallInteger)


def test_saas_ai_policy_config_model():
    """Valida la arquitectura declarativa de SaaSAIPolicyConfig en el esquema public."""
    assert issubclass(SaaSAIPolicyConfig, PublicBase)
    assert issubclass(SaaSAIPolicyConfig, AuditTimestampsMixin)

    table = SaaSAIPolicyConfig.__table__
    assert table.name == "saas_ai_policy_config"
    assert table.schema == "public"
    assert "id" in table.c
    assert "tokens_per_credit" in table.c
    assert "default_monthly_credits" in table.c
    assert "credit_price_clp" in table.c
    assert "credit_price_usd" in table.c
    assert "updated_by" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c

    assert isinstance(table.c.tokens_per_credit.type, Integer)
    assert isinstance(table.c.credit_price_clp.type, Numeric)
    assert isinstance(table.c.credit_price_usd.type, Numeric)

    # Instanciación con valores default
    cfg = SaaSAIPolicyConfig(
        tokens_per_credit=1000,
        default_monthly_credits=2000,
        credit_price_clp=Decimal("15.00"),
        credit_price_usd=Decimal("0.0150"),
    )
    assert cfg.tokens_per_credit == 1000
    assert cfg.default_monthly_credits == 2000
    assert cfg.credit_price_clp == Decimal("15.00")
    assert cfg.credit_price_usd == Decimal("0.0150")


def test_alembic_0007_spec_and_reversibility():
    """Valida la especificación, reversibilidad e invocaciones DDL de Alembic 0007."""
    m = _load_migration_0007()

    assert m.revision == "0007_public_system_plans_extension_and_saas_policy"
    assert m.down_revision == "0006_tenant_approval_requests_and_notification_matrix"
    assert m.migration_scope == "public"

    created_tables: list[str] = []
    added_cols: list[tuple[str, str]] = []
    created_indices: list[str] = []
    bulk_inserts: list[str] = []

    mock_bind = MagicMock()
    mock_bind.execute.return_value.scalar.return_value = None

    with (
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_table", return_value=False),
        patch.object(m, "_has_column", return_value=False),
        patch.object(m, "_has_index", return_value=False),
        patch.object(m.op, "create_table", side_effect=lambda t, *_args, **_kw: created_tables.append(t)),
        patch.object(m.op, "add_column", side_effect=lambda t, c, **_kw: added_cols.append((t, c.name))),
        patch.object(m.op, "create_index", side_effect=lambda name, *_args, **_kw: created_indices.append(name)),
        patch.object(m.op, "bulk_insert", side_effect=lambda table, _rows: bulk_inserts.append(table.name)),
    ):
        m.upgrade()

    assert "saas_ai_policy_config" in created_tables
    assert ("system_plans", "description") in added_cols
    assert ("system_plans", "monthly_ai_credits") in added_cols
    assert ("system_plans", "tier") in added_cols
    assert ("system_plans", "is_popular") in added_cols
    assert ("system_plans", "is_active") in added_cols
    assert "ix_system_plans_tier" in created_indices
    assert "ix_system_plans_is_active" in created_indices
    assert "saas_ai_policy_config" in bulk_inserts

    # Downgrade
    dropped_tables: list[str] = []
    dropped_cols: list[tuple[str, str]] = []
    dropped_indices: list[str] = []

    with (
        patch.object(m, "_has_table", return_value=True),
        patch.object(m, "_has_column", return_value=True),
        patch.object(m, "_has_index", return_value=True),
        patch.object(m.op, "drop_table", side_effect=lambda t, **_kw: dropped_tables.append(t)),
        patch.object(m.op, "drop_column", side_effect=lambda t, c, **_kw: dropped_cols.append((t, c))),
        patch.object(m.op, "drop_index", side_effect=lambda name, **_kw: dropped_indices.append(name)),
    ):
        m.downgrade()

    assert "saas_ai_policy_config" in dropped_tables
    assert ("system_plans", "is_active") in dropped_cols
    assert ("system_plans", "is_popular") in dropped_cols
    assert ("system_plans", "tier") in dropped_cols
    assert ("system_plans", "monthly_ai_credits") in dropped_cols
    assert ("system_plans", "description") in dropped_cols
    assert "ix_system_plans_is_active" in dropped_indices
    assert "ix_system_plans_tier" in dropped_indices
