"""
Tests unitarios para modelos de persistencia de Procurement y Migración 0007.
(`test_models_and_migration.py`).

Verifica:
1. Arquitectura de Modelos `Proveedor`, `ProductoProveedor`, `Compra`, `CompraItem`, `CompraIncidencia`, `Invoice`.
2. Herencia estricta de `TenantBase`, mixins `AuditTimestampsMixin` y `SoftDeleteMixin`.
3. Inmutabilidad de nombres propios (regla "Pollo King" con `translatable = False`).
4. Ciclo de vida ORM, cálculo Decimal(14, 2) y Decimal(12, 4), soft-delete y timestamps.
5. Migración Alembic 0007: `upgrade()` y `downgrade()` simétrico, no-op en public e idempotencia.
"""
from __future__ import annotations

import importlib.util
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from src.modules.catalog.infrastructure import models as _cat_models  # noqa: F401
from src.modules.inventory.infrastructure import models as _inv_models  # noqa: F401
from src.modules.operations.infrastructure import models as _ops_models  # noqa: F401
from src.modules.procurement.infrastructure.models import (
    Compra,
    CompraIncidencia,
    CompraItem,
    Invoice,
    ProductoProveedor,
    Proveedor,
)
from src.modules.recipes.infrastructure import models as _rec_models  # noqa: F401
from src.shared.models_base import AuditTimestampsMixin, TenantBase, is_table_proper_noun_immutable
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = [pytest.mark.unit]


def _load_migration_0009():
    mig_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0009_tenant_procurement_purchases_and_suppliers.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0009", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_models_inheritance_and_contracts():
    """Valida la herencia obligatoria de TenantBase y mixins de auditoría/soft delete."""
    for model_cls in (Proveedor, ProductoProveedor, Compra, CompraItem, CompraIncidencia, Invoice):
        assert issubclass(model_cls, TenantBase), f"{model_cls.__name__} debe heredar de TenantBase"
        assert issubclass(model_cls, AuditTimestampsMixin), f"{model_cls.__name__} debe tener AuditTimestampsMixin"

    # Modelos con SoftDeleteMixin
    assert issubclass(Proveedor, SoftDeleteMixin)
    assert issubclass(Compra, SoftDeleteMixin)
    assert issubclass(Invoice, SoftDeleteMixin)

    # Inmutabilidad Pollo King
    assert Proveedor.translatable is False
    assert is_table_proper_noun_immutable(Proveedor.__tablename__) is True
    assert "i18n_data" not in Proveedor.__table__.c


def test_models_columns_and_indices_declared():
    """Valida columnas, tipos e índices esperados en los modelos declarativos de Procurement."""
    # 1. Proveedor
    p_cols = Proveedor.__table__.c
    for col in (
        "id", "rut_tax_id", "razon_social", "nombre_fantasia",
        "email_contacto", "telefono", "direccion", "lead_time_dias",
        "estado", "notas", "is_deleted", "created_at", "updated_at",
    ):
        assert col in p_cols, f"Falta columna {col} en Proveedor"

    # 2. ProductoProveedor
    pp_cols = ProductoProveedor.__table__.c
    for col in (
        "id", "producto_id", "proveedor_id", "codigo_proveedor",
        "ultimo_costo_neto", "tiempo_entrega_dias", "es_proveedor_principal",
        "created_at", "updated_at",
    ):
        assert col in pp_cols, f"Falta columna {col} en ProductoProveedor"

    # 3. Compra
    c_cols = Compra.__table__.c
    for col in (
        "id", "numero_orden", "proveedor_id", "bodega_destino_id",
        "estado", "moneda", "tasa_fx_aplicada", "monto_neto",
        "monto_impuestos", "monto_total", "fecha_entrega_comprometida",
        "fecha_recepcion_real", "notas", "solicitante_user_id",
        "receptor_user_id", "is_deleted", "created_at", "updated_at",
    ):
        assert col in c_cols, f"Falta columna {col} en Compra"

    compra_indexes = {ix.name for ix in Compra.__table__.indexes}
    assert "ix_compras_proveedor_estado" in compra_indexes

    # 4. CompraItem
    ci_cols = CompraItem.__table__.c
    for col in (
        "id", "compra_id", "producto_id", "cantidad_solicitada",
        "cantidad_recibida", "costo_unitario_neto", "subtotal_linea",
        "lote_codigo", "fecha_vencimiento", "created_at", "updated_at",
    ):
        assert col in ci_cols, f"Falta columna {col} en CompraItem"

    # 5. CompraIncidencia
    inc_cols = CompraIncidencia.__table__.c
    for col in (
        "id", "compra_id", "compra_item_id", "tipo_incidencia",
        "cantidad_afectada", "monto_disputa", "resolucion",
        "descripcion", "foto_evidencia_url", "registrado_por_user_id",
        "created_at", "updated_at",
    ):
        assert col in inc_cols, f"Falta columna {col} en CompraIncidencia"


def test_models_orm_lifecycle_sqlite():
    """Valida inserción, lectura, cálculo Decimal y soft-delete con SQLite en memoria."""
    engine = create_engine("sqlite:///:memory:")

    TenantBase.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Crear Proveedor
        prov = Proveedor(
            rut_tax_id="76.123.456-7",
            razon_social="Distribuidora de Alimentos Gourmet SpA",
            nombre_fantasia="Gourmet Alimentos",
            email_contacto="contacto@gourmet.cl",
            telefono="+56911223344",
            direccion="Av. Providencia 1234, Providencia",
            lead_time_dias=3,
            estado="ACTIVO",
            notas="Proveedor prioritario de lácteos y carnes",
        )
        session.add(prov)
        session.commit()
        session.refresh(prov)

        assert prov.id is not None
        assert prov.razon_social == "Distribuidora de Alimentos Gourmet SpA"
        assert prov.estado == "ACTIVO"
        assert prov.lead_time_dias == 3
        assert prov.is_deleted is False

        # 2. Crear ProductoProveedor
        pp = ProductoProveedor(
            producto_id=101,
            proveedor_id=prov.id,
            codigo_proveedor="PROV-HARINA-01",
            ultimo_costo_neto=Decimal("12500.50"),
            tiempo_entrega_dias=2,
            es_proveedor_principal=True,
        )
        session.add(pp)

        # 3. Crear Compra
        compra = Compra(
            numero_orden="OC-2026-10-0001",
            proveedor_id=prov.id,
            bodega_destino_id=1,
            estado="BORRADOR",
            moneda="CLP",
            tasa_fx_aplicada=Decimal("1.00000000"),
            monto_neto=Decimal("125005.00"),
            monto_impuestos=Decimal("23750.95"),
            monto_total=Decimal("148755.95"),
            fecha_entrega_comprometida=datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc),
            notas="Entrega antes del mediodía",
            solicitante_user_id=10,
        )
        session.add(compra)
        session.commit()
        session.refresh(compra)

        assert compra.id is not None
        assert compra.numero_orden == "OC-2026-10-0001"
        assert compra.monto_total == Decimal("148755.95")

        # 4. Crear CompraItem
        item = CompraItem(
            compra_id=compra.id,
            producto_id=101,
            cantidad_solicitada=Decimal("10.0000"),
            cantidad_recibida=Decimal("8.0000"),
            costo_unitario_neto=Decimal("12500.50"),
            subtotal_linea=Decimal("100004.00"),
            lote_codigo="LOT-2026-10A",
            fecha_vencimiento=date(2027, 10, 31),
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.id is not None
        assert item.cantidad_recibida == Decimal("8.0000")
        assert item.subtotal_linea == Decimal("100004.00")
        assert item.lote_codigo == "LOT-2026-10A"

        # 5. Crear CompraIncidencia
        inc = CompraIncidencia(
            compra_id=compra.id,
            compra_item_id=item.id,
            tipo_incidencia="DIFERENCIA_CANTIDAD",
            cantidad_afectada=Decimal("2.0000"),
            monto_disputa=Decimal("25001.00"),
            resolucion="PENDIENTE",
            descripcion="Faltaron 2 sacos de harina en la entrega",
            foto_evidencia_url="https://storage.oppytec.com/tenants/demo/evidence_01.jpg",
            registrado_por_user_id=15,
        )
        session.add(inc)
        session.commit()
        session.refresh(inc)

        assert inc.id is not None
        assert inc.tipo_incidencia == "DIFERENCIA_CANTIDAD"
        assert inc.cantidad_afectada == Decimal("2.0000")
        assert inc.monto_disputa == Decimal("25001.00")

        # 6. Soft Delete en Compra y Proveedor
        compra.mark_soft_deleted(by_user_id=10)
        prov.mark_soft_deleted(by_user_id=10)
        session.commit()

        assert compra.is_deleted is True
        assert compra.deleted_by == 10
        assert compra.deleted_at is not None

        assert prov.is_deleted is True
        assert prov.deleted_by == 10

        compra.restore_soft_deleted()
        assert compra.is_deleted is False
        assert compra.deleted_at is None


def test_migration_0009_metadata():
    """Valida los metadatos de Alembic de la migración correlativa 0009."""
    mig = _load_migration_0009()
    assert mig.revision == "0009_tenant_procurement_purchases_and_suppliers"
    assert mig.down_revision == "0008_tenant_recipes_combos_dynamic_option_groups"
    assert mig.migration_scope == "tenant"


def test_migration_0009_upgrade_and_downgrade_cycle():
    """Valida el ciclo de vida completo Alembic: upgrade enriquece tablas y crea compra_incidencias, downgrade revierte."""
    mig = _load_migration_0009()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        op_harness = Operations(ctx)

        # 1. Simular esquema previo de 0002 (tablas básicas sin las nuevas columnas)
        import sqlalchemy as sa
        op_harness.create_table(
            "proveedores",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rut_tax_id", sa.String(64), nullable=False),
            sa.Column("razon_social", sa.String(180), nullable=False),
            sa.Column("nombre_fantasia", sa.String(180), nullable=True),
            sa.Column("email_contacto", sa.String(255), nullable=True),
            sa.Column("lead_time_dias", sa.Integer(), default=1),
        )
        op_harness.create_table(
            "producto_proveedores",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("producto_id", sa.Integer(), nullable=False),
            sa.Column("proveedor_id", sa.Integer(), nullable=False),
            sa.Column("codigo_proveedor", sa.String(64), nullable=True),
            sa.Column("ultimo_costo_neto", sa.Numeric(14, 2), default=0),
        )
        op_harness.create_table(
            "compras",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("proveedor_id", sa.Integer(), nullable=False),
            sa.Column("bodega_destino_id", sa.Integer(), nullable=False),
            sa.Column("estado", sa.String(32), default="BORRADOR"),
            sa.Column("moneda", sa.String(10), default="CLP"),
            sa.Column("tasa_fx_aplicada", sa.Numeric(18, 8), default=1),
            sa.Column("monto_neto", sa.Numeric(14, 2), default=0),
            sa.Column("monto_impuestos", sa.Numeric(14, 2), default=0),
            sa.Column("monto_total", sa.Numeric(14, 2), default=0),
        )
        op_harness.create_table(
            "compra_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("compra_id", sa.Integer(), nullable=False),
            sa.Column("producto_id", sa.Integer(), nullable=False),
            sa.Column("cantidad_solicitada", sa.Numeric(12, 4), nullable=False),
            sa.Column("cantidad_recibida", sa.Numeric(12, 4), default=0),
            sa.Column("costo_unitario_neto", sa.Numeric(14, 2), nullable=False),
        )

        with Operations.context(ctx):
            # Ejecutar upgrade
            mig.upgrade()

            insp = inspect(conn)
            tables = insp.get_table_names()
            assert "compra_incidencias" in tables

            # Verificar columnas agregadas
            prov_cols = {c["name"] for c in insp.get_columns("proveedores")}
            assert "telefono" in prov_cols
            assert "direccion" in prov_cols
            assert "estado" in prov_cols
            assert "notas" in prov_cols

            pp_cols = {c["name"] for c in insp.get_columns("producto_proveedores")}
            assert "tiempo_entrega_dias" in pp_cols
            assert "es_proveedor_principal" in pp_cols

            compra_cols = {c["name"] for c in insp.get_columns("compras")}
            assert "numero_orden" in compra_cols
            assert "notas" in compra_cols
            assert "solicitante_user_id" in compra_cols
            assert "receptor_user_id" in compra_cols

            item_cols = {c["name"] for c in insp.get_columns("compra_items")}
            assert "subtotal_linea" in item_cols
            assert "lote_codigo" in item_cols
            assert "fecha_vencimiento" in item_cols

            inc_cols = {c["name"] for c in insp.get_columns("compra_incidencias")}
            assert "tipo_incidencia" in inc_cols
            assert "cantidad_afectada" in inc_cols
            assert "monto_disputa" in inc_cols
            assert "resolucion" in inc_cols

            # Ejecutar downgrade
            mig.downgrade()

            insp_after = inspect(conn)
            tables_after = insp_after.get_table_names()
            assert "compra_incidencias" not in tables_after

            prov_cols_after = {c["name"] for c in insp_after.get_columns("proveedores")}
            assert "telefono" not in prov_cols_after
            assert "direccion" not in prov_cols_after
            assert "estado" not in prov_cols_after
            assert "notas" not in prov_cols_after

            pp_cols_after = {c["name"] for c in insp_after.get_columns("producto_proveedores")}
            assert "tiempo_entrega_dias" not in pp_cols_after
            assert "es_proveedor_principal" not in pp_cols_after

            compra_cols_after = {c["name"] for c in insp_after.get_columns("compras")}
            assert "numero_orden" not in compra_cols_after
            assert "solicitante_user_id" not in compra_cols_after

            item_cols_after = {c["name"] for c in insp_after.get_columns("compra_items")}
            assert "subtotal_linea" not in item_cols_after
            assert "lote_codigo" not in item_cols_after
            assert "fecha_vencimiento" not in item_cols_after


def test_migration_0009_public_schema_noop():
    """Garantiza que la migración es no-op estricto si current_schema es 'public'."""
    mig = _load_migration_0009()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            with patch.object(mig, "_get_current_schema", return_value="public"):
                mig.upgrade()
                insp = inspect(conn)
                assert "compra_incidencias" not in insp.get_table_names()

                mig.downgrade()
                assert "compra_incidencias" not in insp.get_table_names()
