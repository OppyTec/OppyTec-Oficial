"""
Pruebas unitarias 1:1 para `src/modules/inventory/`.
Verifica `Bodega`, `ProductoBodega`, Kardex Append-Only (`RegistroStock`), `StockTransfer`,
`ConteoInventario`, `ConteoItem`, `Merma` con `Decimal` y la migración Alembic correlativa `0004`.
"""
from __future__ import annotations

import importlib.util
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import (
    DomainValidationError,
    InsufficientStockError,
    ResourceNotFoundError,
    TransferSameWarehouseError,
)
from src.modules.inventory.application import (
    CountItemInput,
    InventoryService,
    PhysicalCountService,
)
from src.modules.inventory.infrastructure.models import (
    AreaOperativa,
    Bodega,
    ConteoInventario,
    ConteoItem,
    Merma,
    ProductoBodega,
    RegistroStock,
    StockTransfer,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = pytest.mark.unit


def test_inventory_kardex_append_only_and_decimal_stock() -> None:
    """Verifica que `RegistroStock` sea inmutable (sin `SoftDeleteMixin`) y opere con `Decimal`."""
    assert not issubclass(RegistroStock, SoftDeleteMixin)
    assert "is_deleted" not in RegistroStock.__table__.c

    bodega = Bodega(nombre="Bodega Frío", es_principal=True)
    bodega.set_localized_text("en", "Cold Storage Warehouse")
    assert bodega.get_localized_text("en", bodega.nombre) == "Cold Storage Warehouse"

    pb = ProductoBodega(
        producto_id=1,
        bodega_id=1,
        stock_actual=Decimal("42.5000"),
        stock_minimo=Decimal("5.0000"),
        stock_maximo=Decimal("100.0000"),
        punto_reorden=Decimal("15.0000"),
        pasillo="A",
        estante="3",
        nivel="2",
    )
    assert pb.stock_actual == Decimal("42.5000")
    assert pb.stock_minimo == Decimal("5.0000")
    assert pb.stock_maximo == Decimal("100.0000")
    assert pb.punto_reorden == Decimal("15.0000")
    assert pb.pasillo == "A"
    assert pb.estante == "3"
    assert pb.nivel == "2"

    mov_uuid = uuid.uuid4()
    mov = RegistroStock(
        producto_id=1,
        bodega_id=1,
        tipo_movimiento="ENTRADA_COMPRA",
        cantidad=Decimal("10.0000"),
        saldo_resultante=pb.stock_actual + Decimal("10.0000"),
        costo_unitario=Decimal("1850.00"),
        costo_unitario_ppp=Decimal("1820.50"),
        costo_total_movimiento=Decimal("18500.00"),
        lote_codigo="LOT-2026-X1",
        fecha_vencimiento_lote=date(2027, 6, 30),
        transfer_id=mov_uuid,
        actor_user_id=5,
    )
    assert mov.saldo_resultante == Decimal("52.5000")
    assert mov.costo_unitario_ppp == Decimal("1820.50")
    assert mov.costo_total_movimiento == Decimal("18500.00")
    assert mov.lote_codigo == "LOT-2026-X1"
    assert mov.fecha_vencimiento_lote == date(2027, 6, 30)
    assert mov.transfer_id == mov_uuid

    merma = Merma(
        producto_id=1,
        bodega_id=1,
        cantidad=Decimal("2.5000"),
        costo_total=Decimal("4625.00"),
        motivo="Corte de cadena de frío",
        reportado_por_user_id=5,
    )
    assert merma.costo_total == Decimal("4625.00")
    assert AreaOperativa.translatable is True
    assert ConteoItem.__tablename__ == "conteo_items"


def test_stock_transfer_model_and_indexes() -> None:
    """Verifica el modelo `StockTransfer` y los índices definidos en `RegistroStock`."""
    transfer_id = uuid.uuid4()
    transfer = StockTransfer(
        transfer_uuid=transfer_id,
        bodega_origen_id=1,
        bodega_destino_id=2,
        estado="SOLICITADA",
        solicitante_user_id=10,
        notas="Reabastecimiento urgente de barra",
    )
    assert transfer.transfer_uuid == transfer_id
    assert transfer.bodega_origen_id == 1
    assert transfer.bodega_destino_id == 2
    assert transfer.estado == "SOLICITADA"
    assert transfer.despachador_user_id is None
    assert transfer.receptor_user_id is None

    # Verificar índices en RegistroStock
    index_names = [idx.name for idx in RegistroStock.__table__.indexes]
    assert "ix_registro_stock_bodega_producto" in index_names
    assert "ix_registro_stock_created_tipo" in index_names
    assert "ix_registro_stock_transfer_id" in index_names


def test_conteo_inventario_and_items_enrichment() -> None:
    """Verifica los nuevos campos de `ConteoInventario` y `ConteoItem` con valorización de diferencias."""
    now = datetime.now(UTC)
    conteo = ConteoInventario(
        bodega_id=1,
        area_operativa_id=2,
        estado="EN_PROCESO",
        responsable_user_id=8,
        aprobador_user_id=1,
        notas="Conteo trimestral Q4",
        completed_at=now,
    )
    assert conteo.area_operativa_id == 2
    assert conteo.aprobador_user_id == 1
    assert conteo.notas == "Conteo trimestral Q4"
    assert conteo.completed_at == now

    item = ConteoItem(
        conteo_id=1,
        producto_id=10,
        stock_sistema=Decimal("100.0000"),
        stock_contado=Decimal("95.0000"),
        diferencia=Decimal("-5.0000"),
        lote_codigo="LOT-A-99",
        fecha_vencimiento=date(2027, 1, 15),
        costo_unitario_ppp=Decimal("250.00"),
        valorizacion_diferencia=Decimal("-1250.00"),
    )
    assert item.lote_codigo == "LOT-A-99"
    assert item.fecha_vencimiento == date(2027, 1, 15)
    assert item.costo_unitario_ppp == Decimal("250.00")
    assert item.valorizacion_diferencia == Decimal("-1250.00")


def test_alembic_migration_0004_spec_and_reversibility() -> None:
    """Verifica la carga dinámica, alcance tenant y simetría de la migración correlativa 0004."""
    versions_dir = Path(__file__).resolve().parents[3] / "alembic" / "versions"
    mig_path = versions_dir / "0004_tenant_inventory_kardex_and_physical_counts.py"
    assert mig_path.exists(), f"Migration file {mig_path} must exist"

    spec = importlib.util.spec_from_file_location("mig_0004", mig_path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    assert m.revision == "0004_tenant_inventory_kardex_and_physical_counts"
    assert m.down_revision == "0003_public_plans_quotas_and_tenant_capacity_overrides"
    assert m.migration_scope == "tenant"

    # En schema "public", upgrade y downgrade deben ser no-op
    with patch.object(m, "_get_current_schema", return_value="public"):
        mock_op = MagicMock()
        with patch.object(m, "op", mock_op):
            m.upgrade()
            mock_op.create_table.assert_not_called()
            mock_op.add_column.assert_not_called()

            m.downgrade()
            mock_op.drop_table.assert_not_called()
            mock_op.drop_column.assert_not_called()

    # En schema tenant, verificar que upgrade y downgrade llamen las operaciones DDL
    created_tables: list[str] = []
    dropped_tables: list[str] = []
    added_cols: list[tuple[str, str]] = []
    dropped_cols: list[tuple[str, str]] = []
    created_indices: list[str] = []
    dropped_indices: list[str] = []

    with (
        patch.object(m, "_get_current_schema", return_value="tenant_testing"),
        patch.object(m, "_has_table", return_value=False),
        patch.object(m, "_has_column", return_value=False),
        patch.object(m, "_has_index", return_value=False),
        patch.object(m.op, "create_table", side_effect=lambda t, *args, **kw: created_tables.append(t)),
        patch.object(m.op, "add_column", side_effect=lambda t, c, **kw: added_cols.append((t, c.name))),
        patch.object(m.op, "create_index", side_effect=lambda name, t, *args, **kw: created_indices.append(name)),
    ):
        m.upgrade()

    assert created_tables == ["stock_transfers"]
    assert len(added_cols) == 19  # 6 producto_bodegas + 5 registro_stock + 4 conteos_inventario + 4 conteo_items
    assert len(created_indices) == 4  # 3 en registro_stock + 1 en conteos_inventario (y transfers si no está creada)

    with (
        patch.object(m, "_get_current_schema", return_value="tenant_testing"),
        patch.object(m, "_has_table", return_value=True),
        patch.object(m, "_has_column", return_value=True),
        patch.object(m, "_has_index", return_value=True),
        patch.object(m.op, "drop_table", side_effect=lambda t, **kw: dropped_tables.append(t)),
        patch.object(m.op, "drop_column", side_effect=lambda t, c, **kw: dropped_cols.append((t, c))),
        patch.object(m.op, "drop_index", side_effect=lambda name, **kw: dropped_indices.append(name)),
    ):
        m.downgrade()

    assert dropped_tables == ["stock_transfers"]
    assert len(dropped_cols) == 19
    # Reversibilidad simétrica de columnas dropeadas
    assert set(dropped_cols) == set(added_cols)
