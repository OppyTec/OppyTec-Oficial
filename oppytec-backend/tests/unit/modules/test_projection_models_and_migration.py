"""
oppytec-backend/tests/unit/modules/test_projection_models_and_migration.py
Pruebas Unitarias de Arquitectura de Modelos de Persistencia SQLAlchemy 2.0 y Migración Alembic
para el Módulo de Proyección (Fase 1).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import class_mapper

from src.modules.catalog.infrastructure.models import Producto
from src.modules.inventory.infrastructure.models import Bodega
from src.modules.projection.infrastructure.models import (
    DailyConsumptionRate,
    ProjectionSnapshot,
)
from src.shared.models_base import AuditTimestampsMixin, TenantBase
from tests.architecture.test_alembic_integrity import validate_migration_ast

pytestmark = pytest.mark.unit


def test_projection_snapshot_model_structure() -> None:
    """Verifica que ProjectionSnapshot herede de TenantBase y AuditTimestampsMixin con todos sus atributos requeridos."""
    assert issubclass(ProjectionSnapshot, TenantBase)
    assert issubclass(ProjectionSnapshot, AuditTimestampsMixin)
    assert ProjectionSnapshot.__tablename__ == "projection_snapshots"

    table = ProjectionSnapshot.__table__
    cols = {col.name: col for col in table.columns}

    # Columnas esperadas
    expected_cols = [
        "id",
        "producto_id",
        "bodega_id",
        "horizon_days",
        "current_stock",
        "projected_stock",
        "depletion_date",
        "worst_status",
        "worst_status_label",
        "worst_day",
        "daily_consumption_rate",
        "projection_curve",
        "calculated_at",
        "is_stale",
        "metadata_payload",
        "created_at",
        "updated_at",
    ]
    for col_name in expected_cols:
        assert col_name in cols, f"Columna '{col_name}' no encontrada en projection_snapshots"

    # Tipos de datos estrictos
    assert isinstance(cols["id"].type, BigInteger)
    assert cols["id"].primary_key is True

    assert isinstance(cols["producto_id"].type, BigInteger)
    assert cols["producto_id"].nullable is False

    assert isinstance(cols["bodega_id"].type, BigInteger)
    assert cols["bodega_id"].nullable is True

    assert isinstance(cols["horizon_days"].type, Integer)
    assert cols["horizon_days"].nullable is False

    assert isinstance(cols["current_stock"].type, Numeric)
    assert cols["current_stock"].type.precision == 12
    assert cols["current_stock"].type.scale == 4

    assert isinstance(cols["projected_stock"].type, Numeric)
    assert cols["projected_stock"].type.precision == 12
    assert cols["projected_stock"].type.scale == 4

    assert isinstance(cols["depletion_date"].type, Date)
    assert cols["depletion_date"].nullable is True

    assert isinstance(cols["worst_status"].type, String)
    assert cols["worst_status"].type.length == 20

    assert isinstance(cols["worst_status_label"].type, String)
    assert cols["worst_status_label"].type.length == 64

    assert isinstance(cols["worst_day"].type, Integer)
    assert cols["worst_day"].nullable is True

    assert isinstance(cols["daily_consumption_rate"].type, Numeric)
    assert cols["daily_consumption_rate"].type.precision == 12
    assert cols["daily_consumption_rate"].type.scale == 4

    assert isinstance(cols["calculated_at"].type, DateTime)
    assert cols["calculated_at"].type.timezone is True

    assert isinstance(cols["is_stale"].type, Boolean)

    # Restricción de unicidad
    uq_names = {uq.name for uq in table.constraints if hasattr(uq, "columns")}
    assert "uq_proj_snapshots_prod_bod_horiz" in uq_names

    # Índices esperados
    index_names = {idx.name for idx in table.indexes}
    assert "idx_proj_snapshots_lookup" in index_names
    assert "idx_proj_snapshots_prod" in index_names
    assert "idx_proj_snapshots_calc" in index_names

    # Relaciones ORM
    mapper = class_mapper(ProjectionSnapshot)
    assert "producto" in mapper.relationships
    assert mapper.relationships["producto"].mapper.class_ is Producto
    assert "bodega" in mapper.relationships
    assert mapper.relationships["bodega"].mapper.class_ is Bodega


def test_daily_consumption_rate_model_structure() -> None:
    """Verifica que DailyConsumptionRate herede de TenantBase y AuditTimestampsMixin con sus columnas exactas."""
    assert issubclass(DailyConsumptionRate, TenantBase)
    assert issubclass(DailyConsumptionRate, AuditTimestampsMixin)
    assert DailyConsumptionRate.__tablename__ == "daily_consumption_rates"

    table = DailyConsumptionRate.__table__
    cols = {col.name: col for col in table.columns}

    expected_cols = [
        "id",
        "producto_id",
        "bodega_id",
        "rate_7d",
        "rate_30d",
        "rate_90d",
        "last_calculated_at",
        "created_at",
        "updated_at",
    ]
    for col_name in expected_cols:
        assert col_name in cols, f"Columna '{col_name}' no encontrada en daily_consumption_rates"

    assert isinstance(cols["id"].type, BigInteger)
    assert cols["id"].primary_key is True

    assert isinstance(cols["producto_id"].type, BigInteger)
    assert cols["producto_id"].nullable is False

    assert isinstance(cols["bodega_id"].type, BigInteger)
    assert cols["bodega_id"].nullable is True

    for rate_col in ["rate_7d", "rate_30d", "rate_90d"]:
        assert isinstance(cols[rate_col].type, Numeric)
        assert cols[rate_col].type.precision == 12
        assert cols[rate_col].type.scale == 4

    assert isinstance(cols["last_calculated_at"].type, DateTime)
    assert cols["last_calculated_at"].type.timezone is True

    # Restricción de unicidad
    uq_names = {uq.name for uq in table.constraints if hasattr(uq, "columns")}
    assert "uq_daily_consumption_rates_prod_bod" in uq_names

    # Relaciones ORM
    mapper = class_mapper(DailyConsumptionRate)
    assert "producto" in mapper.relationships
    assert mapper.relationships["producto"].mapper.class_ is Producto
    assert "bodega" in mapper.relationships
    assert mapper.relationships["bodega"].mapper.class_ is Bodega


def test_alembic_migration_0014_file_ast_and_governance() -> None:
    """Verifica que el archivo de migración 0014 cumpla los requisitos de gobernanza de Alembic de OppyTec v2.0."""
    versions_dir = Path(__file__).resolve().parents[3] / "alembic" / "versions"
    migration_file = versions_dir / "0014_tenant_projection_snapshots_and_consumption_rates.py"

    assert migration_file.exists(), f"El archivo {migration_file.name} debe existir"

    content = migration_file.read_text(encoding="utf-8")
    errors = validate_migration_ast(content, migration_file.name)
    assert not errors, f"Errores de AST en migración 0014: {errors}"

    # Verificación de constantes
    assert 'revision = "0014_tenant_projection_snapshots_and_consumption_rates"' in content
    assert 'down_revision = "0013_tenant_events_salones_and_reservations"' in content
    assert 'migration_scope: Literal["public", "tenant"] = "tenant"' in content
    assert "def upgrade() -> None:" in content
    assert "def downgrade() -> None:" in content
    assert "_get_tenant_schemas" in content
