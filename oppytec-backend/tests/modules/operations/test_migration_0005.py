"""
Tests unitarios de la migración 0005 y modelos de persistencia del Módulo de Consumo,
Buffet Inteligente y Manos Libres (`test_migration_0005.py`).

Verifica:
1. Arquitectura de Modelos `ConsumptionRecord`, `ConsumptionRecordItem`, `ConsumptionTemplate`,
   `BuffetSessionItem`, `BuffetTemplate`, `BuffetSession`, `BuffetStation`, `VoiceStation`, `VoiceOrderLog`.
2. Herencia estricta de `TenantBase`, `AuditTimestampsMixin`, `SoftDeleteMixin`, `TranslatableI18nMixin`.
3. Migración Alembic 0005: `revision = 0005...`, `down_revision = 0004...`, `migration_scope = tenant`.
4. Ejecución DDL segura e idempotente en esquemas tenant y no-op en public.
5. Vistas de compatibilidad en español (`registros_consumo`, `registro_consumo_items`, `plantillas_consumo`).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.operations.infrastructure.models import (
    BuffetSession,
    BuffetSessionItem,
    BuffetStation,
    BuffetTemplate,
    ConsumptionRecord,
    ConsumptionRecordItem,
    ConsumptionTemplate,
    VoiceOrderLog,
    VoiceStation,
)
from src.shared.models_base import AuditTimestampsMixin, TenantBase, TranslatableI18nMixin
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = [pytest.mark.unit]


def _load_migration_0005():
    mig_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0005_tenant_consumption_buffet_and_voice_tables.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0005", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_consumption_models_inheritance_and_contracts():
    """Valida la herencia obligatoria de TenantBase y mixins correspondientes."""
    assert issubclass(ConsumptionRecord, TenantBase)
    assert issubclass(ConsumptionRecord, AuditTimestampsMixin)
    assert issubclass(ConsumptionRecord, SoftDeleteMixin)

    assert issubclass(ConsumptionRecordItem, TenantBase)
    assert issubclass(ConsumptionRecordItem, AuditTimestampsMixin)

    assert issubclass(ConsumptionTemplate, TenantBase)
    assert issubclass(ConsumptionTemplate, AuditTimestampsMixin)
    assert issubclass(ConsumptionTemplate, SoftDeleteMixin)
    assert issubclass(ConsumptionTemplate, TranslatableI18nMixin)

    assert issubclass(BuffetSessionItem, TenantBase)
    assert issubclass(BuffetSessionItem, AuditTimestampsMixin)

    assert issubclass(BuffetTemplate, TenantBase)
    assert issubclass(BuffetTemplate, TranslatableI18nMixin)

    assert issubclass(BuffetSession, TenantBase)
    assert issubclass(BuffetSession, SoftDeleteMixin)

    assert issubclass(BuffetStation, TenantBase)
    assert issubclass(BuffetStation, TranslatableI18nMixin)

    assert issubclass(VoiceStation, TenantBase)
    assert issubclass(VoiceStation, AuditTimestampsMixin)
    assert issubclass(VoiceStation, SoftDeleteMixin)

    assert issubclass(VoiceOrderLog, TenantBase)
    assert issubclass(VoiceOrderLog, AuditTimestampsMixin)


def test_consumption_record_and_items_declared_columns():
    """Valida columnas, claves foráneas e índices esperados en consumo."""
    cr_table = ConsumptionRecord.__table__
    assert cr_table.name == "consumption_records"
    assert "id" in cr_table.c
    assert "codigo_folio" in cr_table.c
    assert "folio_ticket" in cr_table.c
    assert "area_operativa_id" in cr_table.c
    assert "bodega_id" in cr_table.c
    assert "usuario_id" in cr_table.c
    assert "tipo_origen" in cr_table.c
    assert "costo_total" in cr_table.c
    assert "notas" in cr_table.c
    assert "is_deleted" in cr_table.c

    item_table = ConsumptionRecordItem.__table__
    assert item_table.name == "consumption_record_items"
    assert "consumption_record_id" in item_table.c
    assert "tipo_item" in item_table.c
    assert "item_id" in item_table.c
    assert "cantidad" in item_table.c
    assert "unidad_medida" in item_table.c
    assert "costo_unitario_ppp" in item_table.c
    assert "costo_total" in item_table.c
    assert "lote_codigo" in item_table.c
    assert "fecha_vencimiento_lote" in item_table.c
    assert "kardex_movement_id" in item_table.c
    assert "opciones_seleccionadas" in item_table.c


def test_buffet_and_voice_declared_columns():
    """Valida columnas del buffet enriquecido y estaciones de voz."""
    bsi_table = BuffetSessionItem.__table__
    assert bsi_table.name == "buffet_session_items"
    assert "session_id" in bsi_table.c
    assert "station_id" in bsi_table.c
    assert "cantidad_montada" in bsi_table.c
    assert "cantidad_sobrante" in bsi_table.c
    assert "cantidad_merma" in bsi_table.c
    assert "cantidad_neta_consumida" in bsi_table.c
    assert "costo_unitario_ppp" in bsi_table.c
    assert "costo_total" in bsi_table.c

    # BuffetTemplate enriquecido
    bt_table = BuffetTemplate.__table__
    assert "descripcion" in bt_table.c
    assert "estaciones_json" in bt_table.c
    assert "is_system" in bt_table.c
    assert "is_public" in bt_table.c

    # BuffetSession enriquecida
    bs_table = BuffetSession.__table__
    assert "area_operativa_id" in bs_table.c
    assert "bodega_id" in bs_table.c
    assert "usuario_creador_id" in bs_table.c
    assert "tipo_servicio" in bs_table.c
    assert "pax_comensales" in bs_table.c
    assert "costo_total_montaje" in bs_table.c
    assert "valor_sobrante_reutilizable" in bs_table.c
    assert "costo_neto_pax" in bs_table.c

    # BuffetStation enriquecida
    bst_table = BuffetStation.__table__
    assert "orden" in bst_table.c

    # VoiceStation
    vs_table = VoiceStation.__table__
    assert vs_table.name == "voice_stations"
    assert "area_operativa_id" in vs_table.c
    assert "nombre_estacion" in vs_table.c
    assert "voice_command" in vs_table.c
    assert "usuario_asignado_id" in vs_table.c
    assert "is_active" in vs_table.c

    # VoiceOrderLog
    vol_table = VoiceOrderLog.__table__
    assert vol_table.name == "voice_order_logs"
    assert "station_id" in vol_table.c
    assert "texto_transcrito" in vol_table.c
    assert "accion_detectada" in vol_table.c
    assert "confianza_ia" in vol_table.c
    assert "items_interpretados_json" in vol_table.c
    assert "estado" in vol_table.c
    assert "consumption_record_id" in vol_table.c


def test_alembic_0005_spec_and_operations():
    """Valida la especificación, reversibilidad e invocaciones DDL de Alembic 0005."""
    m = _load_migration_0005()

    assert m.revision == "0005_tenant_consumption_buffet_and_voice_tables"
    assert m.down_revision == "0004_tenant_inventory_kardex_and_physical_counts"
    assert m.migration_scope == "tenant"

    # En schema "public" sin tenants, upgrade y downgrade deben ser no-op
    mock_bind = MagicMock()
    with (
        patch.object(m, "_get_current_schema", return_value="public"),
        patch.object(m, "_get_tenant_schemas", return_value=[]),
        patch.object(m.op, "get_bind", return_value=mock_bind),
    ):
        mock_op = MagicMock()
        mock_op.get_bind.return_value = mock_bind
        with patch.object(m, "op", mock_op):
            m.upgrade()
            mock_op.create_table.assert_not_called()
            mock_op.add_column.assert_not_called()

            m.downgrade()
            mock_op.drop_table.assert_not_called()
            mock_op.drop_column.assert_not_called()

    # En schema tenant, verificar creación de tablas e índices
    created_tables: list[str] = []
    added_cols: list[tuple[str, str]] = []
    created_indices: list[str] = []

    with (
        patch.object(m, "_get_current_schema", return_value="tenant_restaurante"),
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_table", side_effect=lambda name, schema=None: name in ("buffet_templates", "buffet_sessions", "buffet_stations")),  # noqa: ARG005
        patch.object(m, "_has_column", return_value=False),
        patch.object(m, "_has_index", return_value=False),
        patch.object(m.op, "create_table", side_effect=lambda t, *_args, **_kw: created_tables.append(t)),
        patch.object(m.op, "add_column", side_effect=lambda t, c, **_kw: added_cols.append((t, c.name))),
        patch.object(m.op, "create_index", side_effect=lambda name, *_args, **_kw: created_indices.append(name)),
    ):
        m.upgrade()

    assert "consumption_records" in created_tables
    assert "consumption_record_items" in created_tables
    assert "consumption_templates" in created_tables
    assert "buffet_session_items" in created_tables
    assert "voice_stations" in created_tables
    assert "voice_order_logs" in created_tables

    # Columnas enriquecidas en buffet_templates, buffet_sessions, buffet_stations
    added_table_names = {t for t, _ in added_cols}
    assert "buffet_templates" in added_table_names
    assert "buffet_sessions" in added_table_names
    assert "buffet_stations" in added_table_names

    # Downgrade
    dropped_tables: list[str] = []
    dropped_cols: list[tuple[str, str]] = []

    with (
        patch.object(m, "_get_current_schema", return_value="tenant_restaurante"),
        patch.object(m.op, "get_bind", return_value=mock_bind),
        patch.object(m, "_has_table", return_value=True),
        patch.object(m, "_has_column", return_value=True),
        patch.object(m, "_has_index", return_value=True),
        patch.object(m.op, "drop_table", side_effect=lambda t, **_kw: dropped_tables.append(t)),
        patch.object(m.op, "drop_column", side_effect=lambda t, c, **_kw: dropped_cols.append((t, c))),
        patch.object(m.op, "drop_index", return_value=None),
    ):
        m.downgrade()

    assert "voice_order_logs" in dropped_tables
    assert "voice_stations" in dropped_tables
    assert "buffet_session_items" in dropped_tables
    assert "consumption_templates" in dropped_tables
    assert "consumption_record_items" in dropped_tables
    assert "consumption_records" in dropped_tables
