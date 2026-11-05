"""
oppytec-backend/tests/unit/test_migration_0018_holding_hub.py
Tests unitarios de la migración correlativa 0018 y los modelos SQLAlchemy del Holding Hub:
- Holding (`credit_distribution_mode: 'shared' | 'per_tenant'`)
- HoldingCreditDistribution (`holding_credit_distributions`)
- HoldingCreditPurchase (`holding_credit_purchases`)
- Regla Pollo King (`translatable = False`), precisión Decimal y reversibilidad LIFO de Alembic.
"""
from __future__ import annotations

import importlib.util
import types
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, Numeric, String, Table, UniqueConstraint

from src.modules.tenancy.infrastructure.models import (
    Holding,
    HoldingCreditDistribution,
    HoldingCreditPurchase,
)
from src.shared.models_base import AuditTimestampsMixin, PublicBase

pytestmark = [pytest.mark.unit]


def _load_migration_0018() -> types.ModuleType:
    mig_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0018_public_holding_hub_credit_distribution_and_purchases.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0018", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_holding_model_credit_distribution_mode() -> None:
    """Valida el nuevo atributo `credit_distribution_mode` en el modelo Holding."""
    assert Holding.translatable is False
    table: Table = Holding.__table__  # type: ignore[assignment,explicit-any]
    assert table.schema == "public"
    assert "credit_distribution_mode" in table.c
    col: Column[str] = table.c.credit_distribution_mode
    assert isinstance(col.type, String)
    assert col.type.length == 20
    assert col.nullable is False
    assert col.default is not None
    assert getattr(col.default, "arg", None) == "shared"

    # Instanciación con modo explícito "shared"
    h_default = Holding(
        id=uuid.uuid4(),
        nombre="Grupo Genesis Enterprise",
        plan_id=uuid.uuid4(),
        credit_distribution_mode="shared",
    )
    assert h_default.credit_distribution_mode == "shared"

    # Instanciación con modo explícito "per_tenant"
    h_custom = Holding(
        id=uuid.uuid4(),
        nombre="Grupo Pacífico Corp",
        plan_id=uuid.uuid4(),
        credit_distribution_mode="per_tenant",
    )
    assert h_custom.credit_distribution_mode == "per_tenant"


def test_holding_credit_distribution_model() -> None:
    """Valida la arquitectura declarativa de HoldingCreditDistribution."""
    assert issubclass(HoldingCreditDistribution, PublicBase)
    assert issubclass(HoldingCreditDistribution, AuditTimestampsMixin)
    assert HoldingCreditDistribution.translatable is False

    table: Table = HoldingCreditDistribution.__table__  # type: ignore[assignment,explicit-any]
    assert table.name == "holding_credit_distributions"
    assert table.schema == "public"

    # Columnas obligatorias
    assert "id" in table.c
    assert "holding_id" in table.c
    assert "tenant_id" in table.c
    assert "monthly_ai_credits" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c

    assert isinstance(table.c.id.type, Integer)
    assert table.c.id.primary_key is True
    assert isinstance(table.c.monthly_ai_credits.type, Integer)
    assert table.c.monthly_ai_credits.nullable is False

    # UniqueConstraint(holding_id, tenant_id)
    unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    matching_uq = [
        c
        for c in unique_constraints
        if {col.name for col in c.columns} == {"holding_id", "tenant_id"}
    ]
    assert len(matching_uq) == 1
    assert matching_uq[0].name == "uq_holding_tenant_credit_distribution"

    # Instanciación
    h_id = uuid.uuid4()
    t_id = uuid.uuid4()
    dist = HoldingCreditDistribution(
        holding_id=h_id,
        tenant_id=t_id,
        monthly_ai_credits=3500,
    )
    assert dist.holding_id == h_id
    assert dist.tenant_id == t_id
    assert dist.monthly_ai_credits == 3500


def test_holding_credit_purchase_model() -> None:
    """Valida la arquitectura declarativa de HoldingCreditPurchase y la precisión Decimal/Numeric."""
    assert issubclass(HoldingCreditPurchase, PublicBase)
    assert not issubclass(HoldingCreditPurchase, AuditTimestampsMixin)
    assert HoldingCreditPurchase.translatable is False

    table: Table = HoldingCreditPurchase.__table__  # type: ignore[assignment,explicit-any]
    assert table.name == "holding_credit_purchases"
    assert table.schema == "public"

    # Columnas
    assert "id" in table.c
    assert "holding_id" in table.c
    assert "credits_amount" in table.c
    assert "price_clp" in table.c
    assert "price_usd" in table.c
    assert "status" in table.c
    assert "purchased_by_user_id" in table.c
    assert "created_at" in table.c

    assert isinstance(table.c.credits_amount.type, Integer)
    assert isinstance(table.c.price_clp.type, Numeric)
    assert table.c.price_clp.type.precision == 14
    assert table.c.price_clp.type.scale == 2

    assert isinstance(table.c.price_usd.type, Numeric)
    assert table.c.price_usd.type.precision == 14
    assert table.c.price_usd.type.scale == 4

    # Instanciación
    h_id = uuid.uuid4()
    purchase = HoldingCreditPurchase(
        holding_id=h_id,
        credits_amount=10000,
        price_clp=Decimal("150000.00"),
        price_usd=Decimal("150.0000"),
        status="COMPLETED",
        purchased_by_user_id=42,
    )
    assert purchase.holding_id == h_id
    assert purchase.credits_amount == 10000
    assert purchase.price_clp == Decimal("150000.00")
    assert purchase.price_usd == Decimal("150.0000")
    assert purchase.status == "COMPLETED"
    assert purchase.purchased_by_user_id == 42


def test_alembic_0018_spec_and_reversibility() -> None:
    """Valida metadata de Alembic 0018, ejecución de upgrade() y reversibilidad LIFO de downgrade()."""
    m = _load_migration_0018()

    assert m.revision == "0018_public_holding_hub_credit_distribution_and_purchases"
    assert m.down_revision == "0017_public_ai_benchmarks_and_tenant_feedback"
    assert m.migration_scope == "public"

    # Verificación de Upgrade DDL
    added_columns: list[tuple[str, str, str | None]] = []
    created_tables: list[tuple[str, str | None]] = []

    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"

    with (
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_column", return_value=False),
        patch.object(m, "_has_table", return_value=False),
        patch.object(
            m.op,
            "add_column",
            side_effect=lambda table, col, schema=None: added_columns.append((table, col.name, schema)),
        ),
        patch.object(
            m.op,
            "create_table",
            side_effect=lambda table, *_args, schema=None, **_kw: created_tables.append((table, schema)),
        ),
    ):
        m.upgrade()

    assert ("holdings", "credit_distribution_mode", "public") in added_columns
    assert ("holding_credit_distributions", "public") in created_tables
    assert ("holding_credit_purchases", "public") in created_tables

    # Verificación de Downgrade DDL (orden LIFO simétrico)
    dropped_tables: list[tuple[str, str | None]] = []
    dropped_columns: list[tuple[str, str, str | None]] = []

    with (
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_column", return_value=True),
        patch.object(m, "_has_table", return_value=True),
        patch.object(
            m.op,
            "drop_table",
            side_effect=lambda table, schema=None: dropped_tables.append((table, schema)),
        ),
        patch.object(
            m.op,
            "drop_column",
            side_effect=lambda table, col, schema=None: dropped_columns.append((table, col, schema)),
        ),
    ):
        m.downgrade()

    # Orden exacto LIFO: purchases -> distributions -> column
    assert dropped_tables == [
        ("holding_credit_purchases", "public"),
        ("holding_credit_distributions", "public"),
    ]
    assert dropped_columns == [
        ("holdings", "credit_distribution_mode", "public"),
    ]


def test_alembic_0018_idempotency() -> None:
    """Valida que upgrade() y downgrade() no fallen ni dupliquen llamadas si los objetos ya existen o ya fueron eliminados."""
    m = _load_migration_0018()

    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"

    # Cuando los objetos ya existen en upgrade(), no debe llamar create_table ni add_column
    with (
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_column", return_value=True),
        patch.object(m, "_has_table", return_value=True),
        patch.object(m.op, "add_column") as mock_add,
        patch.object(m.op, "create_table") as mock_create,
    ):
        m.upgrade()
        mock_add.assert_not_called()
        mock_create.assert_not_called()

    # Cuando los objetos ya no existen en downgrade(), no debe llamar drop_table ni drop_column
    with (
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_column", return_value=False),
        patch.object(m, "_has_table", return_value=False),
        patch.object(m.op, "drop_table") as mock_drop_table,
        patch.object(m.op, "drop_column") as mock_drop_col,
    ):
        m.downgrade()
        mock_drop_table.assert_not_called()
        mock_drop_col.assert_not_called()
