"""
Pruebas unitarias 1:1 para `src/modules/operations/`.
Verifica `Venta`, `VentaReceta`, `Salon`, `Evento`, `BuffetSession`, `BuffetStation`, `TurnoHorario` y `Tarea`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.modules.operations.infrastructure.models import (
    BuffetSession,
    BuffetStation,
    BuffetTemplate,
    Evento,
    NotaEquipo,
    NotaPersonal,
    Salon,
    Tarea,
    TurnoHorario,
    Venta,
    VentaReceta,
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
