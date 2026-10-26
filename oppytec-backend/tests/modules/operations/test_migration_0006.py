"""
Tests unitarios de la migración 0006 y modelos de Aprobaciones / Matriz de Notificaciones.
(`test_migration_0006.py`).

Verifica:
1. Arquitectura de Modelos `SolicitudAprobacionModel` y `NotificationMatrixRuleModel` (`TenantBase`, `AuditTimestampsMixin`, `SoftDeleteMixin`).
2. Ciclo de vida ORM, JSON dict, UUID y soft delete.
3. Restricción UniqueConstraint("cargo", "tipo_solicitud").
4. Migración Alembic 0006: `upgrade()` y `downgrade()` simétrico e inverso.
5. Idempotencia y no-op cuando `current_schema == 'public'`.
6. Reemplazo limpio y seguro de tabla legacy si existiera.
"""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.operations.infrastructure import (
    NotificationMatrixRuleModel,
    SolicitudAprobacionModel,
)
from src.modules.inventory.infrastructure.models import (
    SolicitudAprobacion as InventorySolicitudAprobacion,
)
from src.shared.models_base import AuditTimestampsMixin, TenantBase
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = [pytest.mark.unit]


def _load_migration_0006():
    mig_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0006_tenant_approval_requests_and_notification_matrix.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0006", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_models_inheritance_and_contracts():
    """Valida la herencia obligatoria de TenantBase y mixins de auditoría/soft delete."""
    assert issubclass(SolicitudAprobacionModel, TenantBase)
    assert issubclass(SolicitudAprobacionModel, AuditTimestampsMixin)
    assert issubclass(SolicitudAprobacionModel, SoftDeleteMixin)

    assert issubclass(NotificationMatrixRuleModel, TenantBase)
    assert issubclass(NotificationMatrixRuleModel, AuditTimestampsMixin)
    assert issubclass(NotificationMatrixRuleModel, SoftDeleteMixin)

    # Compatibilidad retroactiva con inventario
    assert InventorySolicitudAprobacion is SolicitudAprobacionModel


def test_models_columns_and_indices_declared():
    """Valida columnas, tipos, defaults e índices esperados en los modelos declarativos."""
    sol_table = SolicitudAprobacionModel.__table__
    assert sol_table.name == "solicitudes_aprobacion"
    assert "id" in sol_table.c
    assert "tipo" in sol_table.c
    assert "estado" in sol_table.c
    assert "usuario_id" in sol_table.c
    assert "bodega_id" in sol_table.c
    assert "area_operativa_id" in sol_table.c
    assert "detalles" in sol_table.c
    assert "resuelto_por" in sol_table.c
    assert "motivo_rechazo" in sol_table.c
    assert "resuelto_at" in sol_table.c
    assert "is_deleted" in sol_table.c
    assert "created_at" in sol_table.c
    assert "updated_at" in sol_table.c

    sol_indexes = {ix.name for ix in sol_table.indexes}
    assert "ix_solicitudes_aprobacion_estado_created_at" in sol_indexes
    assert "ix_solicitudes_aprobacion_tipo_estado" in sol_indexes
    assert "ix_solicitudes_aprobacion_area_bodega" in sol_indexes

    rule_table = NotificationMatrixRuleModel.__table__
    assert rule_table.name == "notification_matrix_rules"
    assert "cargo" in rule_table.c
    assert "tipo_solicitud" in rule_table.c
    assert "canal_in_app" in rule_table.c
    assert "canal_email" in rule_table.c
    assert "canal_push" in rule_table.c
    assert "es_aprobador" in rule_table.c

    unique_constraints = [
        c.name for c in rule_table.constraints if c.__class__.__name__ == "UniqueConstraint"
    ]
    assert "uq_notification_matrix_rules_cargo_tipo_solicitud" in unique_constraints


def test_models_orm_lifecycle():
    """Valida inserción, lectura, manipulación JSON y soft-delete con SQLite en memoria."""
    engine = create_engine("sqlite:///:memory:")
    TenantBase.metadata.create_all(engine, tables=[
        SolicitudAprobacionModel.__table__,
        NotificationMatrixRuleModel.__table__,
    ])

    with Session(engine) as session:
        # Inserción de solicitud
        req_id = uuid.uuid4()
        solicitud = SolicitudAprobacionModel(
            id=req_id,
            tipo="merma",
            estado="pendiente",
            usuario_id=42,
            bodega_id=1,
            area_operativa_id=2,
            detalles={"producto_id": 10, "cantidad": "3.5", "motivo": "Vencimiento"},
        )
        session.add(solicitud)

        # Inserción de regla
        regla = NotificationMatrixRuleModel(
            cargo="chef",
            tipo_solicitud="merma",
            canal_in_app=True,
            canal_email=True,
            canal_push=False,
            es_aprobador=True,
        )
        session.add(regla)
        session.commit()

        # Consulta
        loaded_sol = session.scalar(
            select(SolicitudAprobacionModel).where(SolicitudAprobacionModel.id == req_id)
        )
        assert loaded_sol is not None
        assert loaded_sol.tipo == "merma"
        assert loaded_sol.detalles["producto_id"] == 10
        assert loaded_sol.is_deleted is False

        # Soft Delete
        loaded_sol.mark_soft_deleted(by_user_id=99)
        session.commit()
        assert loaded_sol.is_deleted is True
        assert loaded_sol.deleted_by == 99
        assert loaded_sol.deleted_at is not None

        loaded_sol.restore_soft_deleted()
        session.commit()
        assert loaded_sol.is_deleted is False
        assert loaded_sol.deleted_at is None

        # Violación de UniqueConstraint (cargo, tipo_solicitud)
        duplicado = NotificationMatrixRuleModel(
            cargo="chef",
            tipo_solicitud="merma",
        )
        session.add(duplicado)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_migration_0006_upgrade_and_downgrade_cycle():
    """Valida el ciclo de vida completo Alembic: upgrade crea tablas e índices, downgrade las elimina limpiamente."""
    mig = _load_migration_0006()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            # 1. Upgrade
            mig.upgrade()

            # Verificar existencia de tablas
            insp = inspect(conn)
            tables = insp.get_table_names()
            assert "solicitudes_aprobacion" in tables
            assert "notification_matrix_rules" in tables

            # Verificar columnas de solicitudes_aprobacion
            sol_cols = {c["name"] for c in insp.get_columns("solicitudes_aprobacion")}
            assert "tipo" in sol_cols
            assert "estado" in sol_cols
            assert "detalles" in sol_cols
            assert "resuelto_por" in sol_cols

            # Verificar columnas de notification_matrix_rules
            rule_cols = {c["name"] for c in insp.get_columns("notification_matrix_rules")}
            assert "cargo" in rule_cols
            assert "tipo_solicitud" in rule_cols
            assert "es_aprobador" in rule_cols

            # 2. Downgrade simétrico e inverso
            mig.downgrade()

            insp_after = inspect(conn)
            tables_after = insp_after.get_table_names()
            assert "solicitudes_aprobacion" not in tables_after
            assert "notification_matrix_rules" not in tables_after


def test_migration_0006_public_schema_noop():
    """Garantiza que la migración es no-op estricto si current_schema es 'public'."""
    mig = _load_migration_0006()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            with patch.object(mig, "_get_current_schema", return_value="public"):
                mig.upgrade()
                insp = inspect(conn)
                assert "solicitudes_aprobacion" not in insp.get_table_names()
                assert "notification_matrix_rules" not in insp.get_table_names()

                mig.downgrade()
                assert "solicitudes_aprobacion" not in insp.get_table_names()


def test_migration_0006_replaces_legacy_stub_table():
    """Si existe una tabla legacy (id int, sin columna 'tipo'), upgrade() la reemplaza limpiamente."""
    mig = _load_migration_0006()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            # Simular tabla legacy de 0002
            import sqlalchemy as sa
            op = Operations(ctx)
            op.create_table(
                "solicitudes_aprobacion",
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column("merma_id", sa.Integer(), nullable=True),
                sa.Column("estado", sa.String(32), nullable=False),
            )
            insp = inspect(conn)
            cols = {c["name"] for c in insp.get_columns("solicitudes_aprobacion")}
            assert "tipo" not in cols

            # Ejecutar upgrade()
            mig.upgrade()

            # Debe haber sido reemplazada con la estructura completa
            insp2 = inspect(conn)
            cols2 = {c["name"] for c in insp2.get_columns("solicitudes_aprobacion")}
            assert "tipo" in cols2
            assert "detalles" in cols2
            assert "usuario_id" in cols2
