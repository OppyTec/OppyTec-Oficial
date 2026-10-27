"""
oppytec-backend/tests/modules/recipes/test_recipes_models_and_migration.py
Pruebas unitarias y de arquitectura para los modelos de Recetas, Combos y Opciones Dinámicas,
y ciclo de vida de la migración Alembic 0008 (`0008_tenant_recipes_combos_dynamic_option_groups.py`).
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.catalog.infrastructure import models as _cat_models
from src.modules.inventory.infrastructure import models as _inv_models
from src.modules.recipes.infrastructure.models import (
    CategoriaCombo,
    CategoriaReceta,
    Combo,
    ComboGrupoOpcion,
    ComboItem,
    GrupoOpciones,
    GrupoOpcionesItem,
    Receta,
    RecetaGrupoOpcion,
    RecetaIngrediente,
)
from src.shared.models_base import (
    AuditTimestampsMixin,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = [pytest.mark.unit]


def _load_migration_0008():
    mig_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0008_tenant_recipes_combos_dynamic_option_groups.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0008", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_models_inheritance_and_mixins():
    """Valida que todos los modelos hereden estrictamente de TenantBase y los mixins requeridos."""
    # Categorías
    for cat_cls in (CategoriaReceta, CategoriaCombo):
        assert issubclass(cat_cls, TenantBase)
        assert issubclass(cat_cls, AuditTimestampsMixin)
        assert issubclass(cat_cls, SoftDeleteMixin)
        assert issubclass(cat_cls, TranslatableI18nMixin)

    # Receta y Combos
    for main_cls in (Receta, Combo):
        assert issubclass(main_cls, TenantBase)
        assert issubclass(main_cls, AuditTimestampsMixin)
        assert issubclass(main_cls, SoftDeleteMixin)
        assert issubclass(main_cls, TranslatableI18nMixin)

    # Grupo de Opciones
    assert issubclass(GrupoOpciones, TenantBase)
    assert issubclass(GrupoOpciones, AuditTimestampsMixin)
    assert issubclass(GrupoOpciones, SoftDeleteMixin)
    assert issubclass(GrupoOpciones, TranslatableI18nMixin)

    # Componentes e Intermedias
    for child_cls in (
        RecetaIngrediente,
        GrupoOpcionesItem,
        RecetaGrupoOpcion,
        ComboItem,
        ComboGrupoOpcion,
    ):
        assert issubclass(child_cls, TenantBase)
        assert issubclass(child_cls, AuditTimestampsMixin)


def test_recipe_model_decimal_precision_and_no_float():
    """Valida instanciación de Receta con campos Decimal y ausencia de floats."""
    receta = Receta(
        codigo="REC-CEVICHE-001",
        nombre="Ceviche Clásico Peruano",
        descripcion="Ceviche tradicional con pesca del día",
        es_subreceta=False,
        es_dinamica=True,
        porciones_rendimiento=Decimal("2.5000"),
        costo_total_calculado=Decimal("4560.75"),
        precio_venta_neto=Decimal("12000.00"),
        precio_venta_bruto=Decimal("14280.00"),
        iva_porcentaje=Decimal("19.00"),
        iva_incluido=True,
        tiempo_preparacion_minutos=18,
    )

    assert isinstance(receta.porciones_rendimiento, Decimal)
    assert isinstance(receta.costo_total_calculado, Decimal)
    assert isinstance(receta.precio_venta_neto, Decimal)
    assert isinstance(receta.precio_venta_bruto, Decimal)
    assert isinstance(receta.iva_porcentaje, Decimal)

    assert receta.porciones_rendimiento == Decimal("2.5000")
    assert receta.costo_total_calculado == Decimal("4560.75")
    assert receta.precio_venta_bruto - receta.costo_total_calculado == Decimal("9719.25")
    assert receta.es_dinamica is True


def test_combo_model_decimal_precision():
    """Valida instanciación de Combo y ComboItem con campos Decimal."""
    combo = Combo(
        codigo="CMB-DUO-01",
        nombre="Dúo Marino",
        es_dinamico=True,
        precio_venta_neto=Decimal("22000.00"),
        precio_venta_bruto=Decimal("26180.00"),
        costo_total_calculado=Decimal("9800.50"),
    )
    assert isinstance(combo.precio_venta_neto, Decimal)
    assert isinstance(combo.precio_venta_bruto, Decimal)
    assert isinstance(combo.costo_total_calculado, Decimal)

    c_item = ComboItem(combo_id=1, producto_id=15, cantidad=Decimal("1.5000"))
    assert isinstance(c_item.cantidad, Decimal)
    assert c_item.cantidad == Decimal("1.5000")


def test_grupo_opciones_synonyms_and_items():
    """Valida que GrupoOpciones soporte sinonimia min/max_selecciones y GrupoOpcionesItem con recargo Decimal."""
    grupo = GrupoOpciones(
        nombre="Término de la Carne",
        seleccion_minima=1,
        seleccion_maxima=1,
        permite_repetir=False,
    )
    assert grupo.min_selecciones == 1
    assert grupo.max_selecciones == 1

    # Invertir: asignación por sinónimo
    grupo.min_selecciones = 2
    assert grupo.seleccion_minima == 2

    item = GrupoOpcionesItem(
        grupo_id=1,
        producto_id=102,
        cantidad=Decimal("0.2500"),
        es_opcion_default=True,
        recargo_precio=Decimal("1200.00"),
        orden=1,
    )
    assert isinstance(item.cantidad, Decimal)
    assert isinstance(item.recargo_precio, Decimal)
    assert item.es_opcion_default is True
    assert item.recargo_precio == Decimal("1200.00")


def test_exclusive_fk_constraints_in_memory_db():
    """
    Valida en SQLite en memoria que las restricciones CHECK exclusivas (producto XOR subreceta)
    impidan registros inconsistentes (ambos nulos o ambos con valor).
    """
    engine = create_engine("sqlite:///:memory:")
    recipe_tables = [
        _cat_models.Producto.__table__,
        _inv_models.Bodega.__table__,
        CategoriaReceta.__table__,
        CategoriaCombo.__table__,
        Receta.__table__,
        RecetaIngrediente.__table__,
        GrupoOpciones.__table__,
        GrupoOpcionesItem.__table__,
        RecetaGrupoOpcion.__table__,
        Combo.__table__,
        ComboItem.__table__,
        ComboGrupoOpcion.__table__,
    ]
    TenantBase.metadata.create_all(engine, tables=recipe_tables)

    with Session(engine) as session:
        # 1. Crear receta válida
        receta = Receta(
            codigo="REC-BASE-01",
            nombre="Fondo de Pescado",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
        )
        session.add(receta)
        session.commit()

        # 2. RecetaIngrediente válido con producto_id
        ing1 = RecetaIngrediente(
            receta_id=receta.id,
            producto_id=10,
            subreceta_id=None,
            cantidad_receta=Decimal("0.5000"),
        )
        session.add(ing1)
        session.commit()
        assert ing1.id is not None

        # 3. RecetaIngrediente inválido: ambos NOT NULL
        ing_invalido_ambos = RecetaIngrediente(
            receta_id=receta.id,
            producto_id=10,
            subreceta_id=receta.id,
            cantidad_receta=Decimal("0.5000"),
        )
        session.add(ing_invalido_ambos)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 4. RecetaIngrediente inválido: ambos NULL
        ing_invalido_ninguno = RecetaIngrediente(
            receta_id=receta.id,
            producto_id=None,
            subreceta_id=None,
            cantidad_receta=Decimal("0.5000"),
        )
        session.add(ing_invalido_ninguno)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 5. GrupoOpcionesItem inválido: ambos NOT NULL
        grupo = GrupoOpciones(nombre="Guarnición", seleccion_minima=1, seleccion_maxima=1)
        session.add(grupo)
        session.commit()

        item_invalido = GrupoOpcionesItem(
            grupo_id=grupo.id,
            producto_id=10,
            receta_id=receta.id,
            cantidad=Decimal("1.0000"),
        )
        session.add(item_invalido)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 6. ComboItem inválido: ambos NULL
        combo = Combo(nombre="Combo Fiesta")
        session.add(combo)
        session.commit()

        c_item_invalido = ComboItem(combo_id=combo.id, producto_id=None, receta_id=None)
        session.add(c_item_invalido)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_migration_0008_metadata():
    """Valida los metadatos de Alembic de la migración correlativa lineal 0008."""
    mig = _load_migration_0008()
    assert mig.revision == "0008_tenant_recipes_combos_dynamic_option_groups"
    assert mig.down_revision == "0007_public_system_plans_extension_and_saas_policy"
    assert mig.migration_scope == "tenant"


def test_migration_0008_upgrade_and_downgrade_cycle():
    """Valida el ciclo completo de upgrade() y downgrade() idempotente en un esquema tenant."""
    mig = _load_migration_0008()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        op_harness = Operations(ctx)

        # 1. Crear tablas base requeridas para simular un esquema tenant previo
        with Operations.context(ctx):
            op_harness.create_table(
                "productos",
                op_harness.f("id"),
                importlib.import_module("sqlalchemy").Column("id", importlib.import_module("sqlalchemy").BigInteger, primary_key=True),
            )
            op_harness.create_table(
                "bodegas",
                op_harness.f("id"),
                importlib.import_module("sqlalchemy").Column("id", importlib.import_module("sqlalchemy").BigInteger, primary_key=True),
            )

        with patch.object(mig, "op", op_harness):
            # Aplicar upgrade
            mig._apply_upgrade_to_schema(None)

            insp = inspect(conn)
            tables = insp.get_table_names()

            expected_tables = {
                "categorias_recetas",
                "categorias_combos",
                "recetas",
                "receta_ingredientes",
                "grupos_opciones",
                "grupo_opciones_items",
                "receta_grupos_opciones",
                "combos",
                "combo_items",
                "combo_grupos_opciones",
            }
            for table in expected_tables:
                assert table in tables, f"Tabla {table} no fue creada por upgrade()"

            # Re-ejecutar upgrade para validar idempotencia (no debe fallar)
            mig._apply_upgrade_to_schema(None)

            # Revertir con downgrade
            mig._apply_downgrade_to_schema(None)
            insp_after = inspect(conn)
            tables_after = insp_after.get_table_names()

            for table in expected_tables:
                assert table not in tables_after, f"Tabla {table} no fue eliminada por downgrade()"


def test_migration_0008_public_schema_noop():
    """Garantiza que la migración es no-op estricto si current_schema es 'public' y no hay tenants."""
    mig = _load_migration_0008()
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            with patch.object(mig, "_get_current_schema", return_value="public"):
                with patch.object(mig, "_get_tenant_schemas", return_value=[]):
                    mig.upgrade()
                    mig.downgrade()
