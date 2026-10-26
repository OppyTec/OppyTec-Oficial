"""
Pruebas unitarias 1:1 para `src/modules/operations/`.
Verifica `Venta`, `VentaReceta`, `Salon`, `Evento`, `BuffetSession`, `BuffetStation`, `BuffetSessionItem`,
`ConsumptionRecord`, `ConsumptionRecordItem`, `ConsumptionTemplate`, `VoiceStation`, `VoiceOrderLog`.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.modules.operations.infrastructure.models import (
    BuffetSession,
    BuffetSessionItem,
    BuffetStation,
    BuffetTemplate,
    ConsumptionRecord,
    ConsumptionRecordItem,
    ConsumptionTemplate,
    Evento,
    NotaEquipo,
    NotaPersonal,
    Salon,
    Tarea,
    TurnoHorario,
    Venta,
    VentaReceta,
    VoiceOrderLog,
    VoiceStation,
)

pytestmark = pytest.mark.unit


def test_operations_sales_buffet_and_events_models() -> None:
    """Verifica modelos operativos con precisión `Decimal` y traducción dinámica en entidades conceptuales."""
    venta = Venta(
        folio_ticket="TCK-000123",
        cajero_user_id=4,
        moneda="CLP",
        monto_total_bruto=Decimal("25800.00"),
        costo_total_insumos=Decimal("7100.50"),
    )
    vr = VentaReceta(
        venta_id=1,
        receta_id=2,
        cantidad=Decimal("2.0000"),
        precio_unitario_bruto=Decimal("12900.00"),
    )
    assert vr.cantidad * vr.precio_unitario_bruto == venta.monto_total_bruto

    salon = Salon(nombre="Salón Pacífico", capacidad_personas=120)
    salon.set_localized_text("en", "Pacific Hall")
    assert salon.get_localized_text("en", salon.nombre) == "Pacific Hall"

    now = datetime.now(UTC)
    evento = Evento(
        salon_id=1,
        nombre_evento="Cena Anual",
        fecha_inicio=now,
        fecha_fin=now,
        asistentes_confirmados=80,
        presupuesto_acordado=Decimal("3200000.00"),
    )
    tpl = BuffetTemplate(nombre="Buffet Desayuno", comensales_estimados=90)
    session = BuffetSession(
        template_id=1,
        comensales_reales=85,
        costo_total_sesion=Decimal("410000.00"),
    )
    station = BuffetStation(
        session_id=1,
        nombre="Estación Frutas",
        peso_inicial_kg=Decimal("15.5000"),
        peso_sobrante_kg=Decimal("2.2500"),
    )
    turno = TurnoHorario(user_id=4, inicio_turno=now, fin_turno=now)
    nota_p = NotaPersonal(user_id=4, titulo="Checklist", contenido="Revisar cámara 2")
    nota_e = NotaEquipo(autor_user_id=4, titulo="Entrega turno", contenido="Todo en orden")
    tarea = Tarea(titulo="Limpieza profunda", completada=True)

    assert station.peso_inicial_kg - station.peso_sobrante_kg == Decimal("13.2500")
    assert evento.presupuesto_acordado == Decimal("3200000.00")
    assert tpl.comensales_estimados == 90
    assert session.comensales_reales == 85
    assert turno.user_id == 4
    assert nota_p.titulo == "Checklist"
    assert nota_e.titulo == "Entrega turno"
    assert tarea.completada is True


def test_operations_consumption_and_templates_models() -> None:
    """Verifica modelos de consumo directo, items y plantillas de turnos."""
    rec = ConsumptionRecord(
        codigo_folio="CONS-20261025-001",
        folio_ticket="TCK-CONS-001",
        area_operativa_id=1,
        bodega_id=2,
        usuario_id=5,
        tipo_origen="MANUAL_TERMINAL",
        costo_total=Decimal("15200.50"),
        notas="Consumo de turno de almuerzo",
    )
    item = ConsumptionRecordItem(
        tipo_item="PRODUCTO",
        item_id=101,
        cantidad=Decimal("3.5000"),
        unidad_medida="KG",
        costo_unitario_ppp=Decimal("4343.00"),
        costo_total=Decimal("15200.50"),
        lote_codigo="LOT-2026-X",
        fecha_vencimiento_lote=date(2026, 12, 31),
        opciones_seleccionadas={"sin_sal": True},
    )
    rec.items.append(item)

    assert rec.codigo_folio == "CONS-20261025-001"
    assert len(rec.items) == 1
    assert rec.items[0].costo_unitario_ppp == Decimal("4343.00")
    assert rec.items[0].consumption_record == rec

    tpl = ConsumptionTemplate(
        slug="cuadrilla-manana",
        nombre="Cuadrilla Mañana",
        descripcion="Insumos frecuentes desayuno",
        usuario_creador_id=5,
        is_public=True,
        columnas_count=6,
        sort_mode="alpha_asc",
        product_ids=[101, 102, 103],
    )
    tpl.set_localized_text("en", "Morning Crew")
    assert tpl.columnas_count == 6
    assert tpl.is_public is True
    assert tpl.get_localized_text("en", tpl.nombre) == "Morning Crew"


def test_operations_buffet_enriched_and_session_items() -> None:
    """Verifica modelos de Buffet enriquecidos y conciliación de sesión."""
    tpl = BuffetTemplate(
        nombre="Buffet Ejecutivo",
        descripcion="Montaje para salón principal",
        comensales_estimados=120,
        estaciones_json=[{"id": 1, "nombre": "Ensaladas"}],
        is_system=True,
        is_public=True,
    )
    session = BuffetSession(
        template_id=1,
        area_operativa_id=1,
        bodega_id=1,
        usuario_creador_id=4,
        tipo_servicio="ALMUERZO",
        estado="ACTIVA",
        comensales_reales=110,
        pax_comensales=110,
        costo_total_montaje=Decimal("550000.00"),
        valor_sobrante_reutilizable=Decimal("50000.00"),
        costo_neto_pax=Decimal("4545.45"),
    )
    station = BuffetStation(
        session_id=1,
        nombre="Estación Fría",
        orden=1,
        peso_inicial_kg=Decimal("20.0000"),
        peso_sobrante_kg=Decimal("3.0000"),
    )
    item = BuffetSessionItem(
        session_id=1,
        station_id=1,
        tipo_item="RECETA",
        item_id=12,
        cantidad_montada=Decimal("10.0000"),
        cantidad_sobrante=Decimal("2.0000"),
        cantidad_merma=Decimal("0.5000"),
        cantidad_neta_consumida=Decimal("7.5000"),
        costo_unitario_ppp=Decimal("8000.00"),
        costo_total=Decimal("60000.00"),
    )
    session.stations.append(station)
    session.items.append(item)

    assert tpl.is_system is True
    assert session.tipo_servicio == "ALMUERZO"
    assert session.pax_comensales == 110
    assert station.orden == 1
    assert station.nombre_estacion == "Estación Fría"
    assert len(session.items) == 1
    assert session.items[0].cantidad_neta_consumida == Decimal("7.5000")


def test_operations_voice_stations_and_order_logs() -> None:
    """Verifica modelos de manos libres y transcripciones por voz."""
    station = VoiceStation(
        area_operativa_id=2,
        nombre_estacion="Cocina Caliente",
        voice_command="estacion_uno",
        usuario_asignado_id=8,
        is_active=True,
    )
    log = VoiceOrderLog(
        texto_transcrito="consumir 2 porciones de carne mechada",
        accion_detectada="CONSUMO",
        confianza_ia=Decimal("0.9850"),
        items_interpretados_json=[{"sku": "REC-01", "qty": 2}],
        estado="PENDIENTE",
    )
    station.order_logs.append(log)

    assert station.nombre_estacion == "Cocina Caliente"
    assert len(station.order_logs) == 1
    assert station.order_logs[0].confianza_ia == Decimal("0.9850")
    assert station.order_logs[0].station == station


def test_alembic_0005_migration_metadata() -> None:
    """Verifica que la migración correlativa 0005 esté correctamente enlazada a 0004."""
    import importlib.util
    from pathlib import Path

    migration_path = Path(__file__).resolve().parents[3] / "alembic/versions/0005_tenant_consumption_buffet_and_voice_tables.py"
    spec = importlib.util.spec_from_file_location("m0005", str(migration_path))
    assert spec is not None and spec.loader is not None
    m0005 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0005)

    assert m0005.revision == "0005_tenant_consumption_buffet_and_voice_tables"
    assert m0005.down_revision == "0004_tenant_inventory_kardex_and_physical_counts"
    assert m0005.migration_scope == "tenant"
    assert callable(m0005.upgrade)
    assert callable(m0005.downgrade)

