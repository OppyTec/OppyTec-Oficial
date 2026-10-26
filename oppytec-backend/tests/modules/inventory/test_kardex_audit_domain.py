"""
oppytec-backend/tests/modules/inventory/test_kardex_audit_domain.py
Suite de pruebas unitarias 5D para el Dominio de Auditoría de Kardex (Fase 1.2 OppyTec v2.0):

1. Value Object `AuditDelta`: inmutabilidad, cálculo before/after/delta, tolerancia cero a floats.
2. Value Object `MovementSign`: lógica pura para determinar signo algebraico (+, -, 0).
3. Función matemática pura `compute_audit_delta`:
   - Movimientos regulares de salida (SALIDA, CONSUMO, MERMA, VENTA, TRASPASO_OUT, AJUSTE_NEGATIVO).
   - Movimientos regulares de entrada (ENTRADA, COMPRA, TRASPASO_IN, AJUSTE_POSITIVO).
   - Conteos y conciliaciones (CONTEO, AJUSTE_AUDITORIA).
   - Transferencias inter-bodega (TRANSFERENCIA).
4. Entidad inmutable `KardexMovement`: nuevos atributos de auditoría y cálculo de delta integrado.
5. Entidad `KardexAuditRecord`: entidad pura enriquecida para el visor de historial (/historial).
6. Conversor de zona horaria determinista `TimezoneConverter` (America/Santiago).
7. Verificación de invariantes algebraicas (before + delta == after) con Hypothesis.
8. Gate de Clean Architecture estricta: cero dependencias de FastAPI o SQLAlchemy en domain.
"""
from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.modules.inventory.domain import (
    AuditDelta,
    KardexAuditRecord,
    KardexMovement,
    MoneyAmount,
    MovementSign,
    MovementType,
    StockQuantity,
    TimezoneConverter,
    compute_audit_delta,
)

pytestmark = [pytest.mark.unit]

dec_positive = st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("50000.0000"), places=4)
dec_balance = st.decimals(min_value=Decimal("0.0000"), max_value=Decimal("100000.0000"), places=4)


# ============================================================================
# 1. VALUE OBJECT: AuditDelta
# ============================================================================


class TestAuditDeltaValueObject:
    """Verifica inmutabilidad, precisión exacta y rechazo estricto de floats en AuditDelta."""

    def test_audit_delta_creation_and_attributes(self) -> None:
        delta = AuditDelta(
            before=Decimal("100.0000"),
            after=Decimal("80.0000"),
            delta=Decimal("-20.0000"),
            unit="kg",
        )
        assert delta.before == Decimal("100.0000")
        assert delta.after == Decimal("80.0000")
        assert delta.delta == Decimal("-20.0000")
        assert delta.unit == "kg"
        assert delta.has_change is True
        assert delta.is_negative is True
        assert delta.is_positive is False
        assert delta.is_neutral is False

    def test_audit_delta_computes_delta_if_omitted(self) -> None:
        delta = AuditDelta(
            before=Decimal("50.0000"),
            after=Decimal("75.0000"),
            unit="unidades",
        )
        assert delta.delta == Decimal("25.0000")
        assert delta.is_positive is True
        assert delta.has_change is True

    def test_audit_delta_neutral_when_no_change(self) -> None:
        delta = AuditDelta(
            before=Decimal("10.5000"),
            after=Decimal("10.5000"),
            unit="litros",
        )
        assert delta.delta == Decimal("0.0000")
        assert delta.is_neutral is True
        assert delta.has_change is False

    def test_audit_delta_is_strictly_immutable(self) -> None:
        delta = AuditDelta(before=Decimal("10"), after=Decimal("20"))
        with pytest.raises(FrozenInstanceError):
            delta.before = Decimal("15")  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            delta.after = Decimal("25")  # type: ignore[misc]

    def test_audit_delta_forbids_floats(self) -> None:
        raw_float = 12.34
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            AuditDelta(before=raw_float, after=Decimal("20.0000"))
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            AuditDelta(before=Decimal("10.0000"), after=raw_float)
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            AuditDelta(before=Decimal("10.0000"), after=Decimal("20.0000"), delta=raw_float)

    def test_audit_delta_string_and_formatting(self) -> None:
        delta = AuditDelta(
            before=Decimal("150.0000"),
            after=Decimal("120.0000"),
            unit="kg",
        )
        assert delta.format_transition() == "150.0000 kg -> 120.0000 kg"
        assert "Δ -30.0000" in str(delta)
        assert "AuditDelta" in repr(delta)

    def test_audit_delta_to_dict(self) -> None:
        delta = AuditDelta(before=Decimal("10.0000"), after=Decimal("15.0000"), unit="L")
        d = delta.to_dict()
        assert d == {
            "before": Decimal("10.0000"),
            "after": Decimal("15.0000"),
            "delta": Decimal("5.0000"),
            "unit": "L",
        }


# ============================================================================
# 2. VALUE OBJECT: MovementSign
# ============================================================================


class TestMovementSignValueObject:
    """Verifica reglas de signo algebraico de movimientos de Kardex."""

    @pytest.mark.parametrize(
        "mov_type",
        [
            MovementType.ENTRADA,
            MovementType.COMPRA,
            MovementType.AJUSTE_POSITIVO,
            MovementType.TRASPASO_IN,
            "ENTRADA",
            "compra",
            "ajuste_positivo",
            "traspaso_in",
        ],
    )
    def test_positive_movement_types(self, mov_type: MovementType | str) -> None:
        sign = MovementSign.from_movement_type(mov_type)
        assert sign == MovementSign.POSITIVE
        assert sign.is_positive is True
        assert sign.is_negative is False
        assert sign.is_neutral is False
        assert sign.multiplier == Decimal(1)
        assert sign.apply_to(Decimal("10.5000")) == Decimal("10.5000")

    @pytest.mark.parametrize(
        "mov_type",
        [
            MovementType.SALIDA,
            MovementType.CONSUMO,
            MovementType.MERMA,
            MovementType.AJUSTE_NEGATIVO,
            MovementType.TRASPASO_OUT,
            "SALIDA",
            "consumo",
            "merma",
            "venta",
            "ajuste_negativo",
            "traspaso_out",
        ],
    )
    def test_negative_movement_types(self, mov_type: MovementType | str) -> None:
        sign = MovementSign.from_movement_type(mov_type)
        assert sign == MovementSign.NEGATIVE
        assert sign.is_positive is False
        assert sign.is_negative is True
        assert sign.is_neutral is False
        assert sign.multiplier == Decimal(-1)
        assert sign.apply_to(Decimal("10.5000")) == Decimal("-10.5000")

    def test_conteo_and_audit_adjustment_sign_depends_on_quantity(self) -> None:
        # Sobrante físico -> Positivo (+)
        assert (
            MovementSign.from_movement_type("CONTEO", quantity=Decimal("5.0000"))
            == MovementSign.POSITIVE
        )
        assert (
            MovementSign.from_movement_type(MovementType.AJUSTE_AUDITORIA, quantity=Decimal("12.0000"))
            == MovementSign.POSITIVE
        )

        # Faltante físico -> Negativo (-)
        assert (
            MovementSign.from_movement_type("conteo", quantity=Decimal("-3.5000"))
            == MovementSign.NEGATIVE
        )
        assert (
            MovementSign.from_movement_type(MovementType.AJUSTE_AUDITORIA, quantity=Decimal("-8.0000"))
            == MovementSign.NEGATIVE
        )

        # Sin discrepancia -> Neutro (0)
        assert (
            MovementSign.from_movement_type("conteo", quantity=Decimal("0.0000"))
            == MovementSign.NEUTRAL
        )
        assert MovementSign.from_movement_type("conteo") == MovementSign.NEUTRAL

    def test_movement_sign_forbids_floats(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            MovementSign.from_movement_type("conteo", quantity=5.0)

        sign = MovementSign.POSITIVE
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            sign.apply_to(10.0)


# ============================================================================
# 3. HELPER PURO: compute_audit_delta
# ============================================================================


class TestComputeAuditDelta:
    """Verifica el cálculo de transiciones Before / After / Delta en movimientos de Kardex."""

    @pytest.mark.parametrize(
        "mov_type",
        [
            MovementType.SALIDA,
            MovementType.CONSUMO,
            MovementType.MERMA,
            MovementType.AJUSTE_NEGATIVO,
            MovementType.TRASPASO_OUT,
            "salida",
            "consumo",
            "merma",
            "venta",
        ],
    )
    def test_outbound_movements_compute_delta(self, mov_type: MovementType | str) -> None:
        # Si el saldo resultante tras una salida de 20 es 80, antes había 100.
        delta = compute_audit_delta(
            resulting_balance=Decimal("80.0000"),
            quantity=Decimal("20.0000"),
            movement_type=mov_type,
            unit="kg",
        )
        assert delta.before == Decimal("100.0000")
        assert delta.after == Decimal("80.0000")
        assert delta.delta == Decimal("-20.0000")
        assert delta.unit == "kg"
        # Invariante: before + delta == after
        assert delta.before + delta.delta == delta.after

    @pytest.mark.parametrize(
        "mov_type",
        [
            MovementType.ENTRADA,
            MovementType.COMPRA,
            MovementType.AJUSTE_POSITIVO,
            MovementType.TRASPASO_IN,
            "entrada",
            "compra",
            "ajuste_positivo",
        ],
    )
    def test_inbound_movements_compute_delta(self, mov_type: MovementType | str) -> None:
        # Si el saldo resultante tras una entrada de 30 es 110, antes había 80.
        delta = compute_audit_delta(
            resulting_balance=Decimal("110.0000"),
            quantity=Decimal("30.0000"),
            movement_type=mov_type,
            unit="unidades",
        )
        assert delta.before == Decimal("80.0000")
        assert delta.after == Decimal("110.0000")
        assert delta.delta == Decimal("30.0000")
        assert delta.unit == "unidades"
        # Invariante: before + delta == after
        assert delta.before + delta.delta == delta.after

    def test_conteo_surplus_discrepancy(self) -> None:
        # En recuento físico había 10 teórico en sistema y se contaron 12 (saldo_resultante = 12).
        # Discrepancia = +2.
        delta = compute_audit_delta(
            resulting_balance=Decimal("12.0000"),
            quantity=Decimal("2.0000"),
            movement_type="CONTEO",
            unit="botellas",
        )
        assert delta.before == Decimal("10.0000")
        assert delta.after == Decimal("12.0000")
        assert delta.delta == Decimal("2.0000")
        assert delta.is_positive is True
        assert delta.before + delta.delta == delta.after

    def test_conteo_shortage_discrepancy(self) -> None:
        # Había 10 teórico en sistema y se contaron 7 (saldo_resultante = 7).
        # Discrepancia = -3.
        delta = compute_audit_delta(
            resulting_balance=Decimal("7.0000"),
            quantity=Decimal("-3.0000"),
            movement_type="conteo",
            unit="botellas",
        )
        assert delta.before == Decimal("10.0000")
        assert delta.after == Decimal("7.0000")
        assert delta.delta == Decimal("-3.0000")
        assert delta.is_negative is True
        assert delta.before + delta.delta == delta.after

    def test_conteo_with_explicit_theoretical_stock(self) -> None:
        delta = compute_audit_delta(
            resulting_balance=Decimal("95.0000"),
            quantity=Decimal("5.0000"),
            movement_type="AJUSTE_AUDITORIA",
            theoretical_stock=Decimal("100.0000"),
            unit="cajas",
        )
        assert delta.before == Decimal("100.0000")
        assert delta.after == Decimal("95.0000")
        assert delta.delta == Decimal("-5.0000")
        assert delta.before + delta.delta == delta.after

    def test_conteo_with_is_positive_adjustment_flag(self) -> None:
        # Shortage de 4 unidades indicado por flag
        delta = compute_audit_delta(
            resulting_balance=Decimal("26.0000"),
            quantity=Decimal("4.0000"),
            movement_type=MovementType.AJUSTE_AUDITORIA,
            is_positive_adjustment=False,
            unit="litros",
        )
        assert delta.before == Decimal("30.0000")
        assert delta.after == Decimal("26.0000")
        assert delta.delta == Decimal("-4.0000")
        assert delta.before + delta.delta == delta.after

    def test_transferencia_movements(self) -> None:
        # Bodega origen (salida de 15) -> saldo resultante 85 -> antes 100
        delta_out = compute_audit_delta(
            resulting_balance=Decimal("85.0000"),
            quantity=Decimal("-15.0000"),
            movement_type="TRANSFERENCIA",
            unit="kg",
        )
        assert delta_out.before == Decimal("100.0000")
        assert delta_out.after == Decimal("85.0000")
        assert delta_out.delta == Decimal("-15.0000")

        # Bodega destino (entrada de 15) -> saldo resultante 35 -> antes 20
        delta_in = compute_audit_delta(
            resulting_balance=Decimal("35.0000"),
            quantity=Decimal("15.0000"),
            movement_type="TRANSFERENCIA",
            unit="kg",
        )
        assert delta_in.before == Decimal("20.0000")
        assert delta_in.after == Decimal("35.0000")
        assert delta_in.delta == Decimal("15.0000")

    def test_compute_audit_delta_forbids_floats(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            compute_audit_delta(resulting_balance=50.0, quantity=Decimal("10"), movement_type="SALIDA")
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            compute_audit_delta(resulting_balance=Decimal("50"), quantity=10.0, movement_type="SALIDA")
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            compute_audit_delta(
                resulting_balance=Decimal("50"),
                quantity=Decimal("10"),
                movement_type="CONTEO",
                theoretical_stock=60.0,
            )


# ============================================================================
# 4. HYPOTHESIS PROPERTY TESTING: INVARIANTE ALGEBRAICA (before + delta == after)
# ============================================================================


class TestAuditDeltaAlgebraicInvariants:
    """Garantiza la invariante matemática universal en 100% de los espacios muestrales."""

    @given(balance=dec_balance, qty=dec_positive)
    def test_outbound_invariant_always_holds(self, balance: Decimal, qty: Decimal) -> None:
        delta = compute_audit_delta(
            resulting_balance=balance,
            quantity=qty,
            movement_type=MovementType.SALIDA,
        )
        assert delta.before == balance + qty
        assert delta.after == balance
        assert delta.delta == -qty
        assert delta.before + delta.delta == delta.after

    @given(balance=dec_balance, qty=dec_positive)
    def test_inbound_invariant_always_holds(self, balance: Decimal, qty: Decimal) -> None:
        delta = compute_audit_delta(
            resulting_balance=balance,
            quantity=qty,
            movement_type=MovementType.ENTRADA,
        )
        assert delta.before == balance - qty
        assert delta.after == balance
        assert delta.delta == qty
        assert delta.before + delta.delta == delta.after


# ============================================================================
# 5. ENTIDADES DE DOMINIO: KardexMovement & KardexAuditRecord
# ============================================================================


class TestDomainEntitiesAuditSupport:
    """Verifica atributos de auditoría en KardexMovement y KardexAuditRecord."""

    def test_kardex_movement_audit_fields(self) -> None:
        movement = KardexMovement(
            producto_id=101,
            bodega_id=1,
            tipo_movimiento=MovementType.MERMA,
            cantidad=StockQuantity("5.0000"),
            saldo_resultante=StockQuantity("45.0000"),
            costo_unitario_ppp=MoneyAmount("2500.00"),
            costo_total_movimiento=MoneyAmount("12500.00"),
            actor_user_id=7,
            motivo_merma="vencimiento",
            descripcion_merma="Lote caducado en bodega seca",
            fecha_recuento=date(2026, 10, 25),
            user_display_name="Juan Perez",
        )
        assert movement.motivo_merma == "vencimiento"
        assert movement.descripcion_merma == "Lote caducado en bodega seca"
        assert movement.fecha_recuento == date(2026, 10, 25)
        assert movement.user_display_name == "Juan Perez"

        # Cálculo de delta integrado
        delta = movement.compute_audit_delta(unit="kg")
        assert delta.before == Decimal("50.0000")
        assert delta.after == Decimal("45.0000")
        assert delta.delta == Decimal("-5.0000")
        assert delta.unit == "kg"
        assert movement.movement_sign == MovementSign.NEGATIVE

    def test_kardex_movement_immutability(self) -> None:
        movement = KardexMovement(
            producto_id=101,
            bodega_id=1,
            tipo_movimiento=MovementType.ENTRADA,
            cantidad=StockQuantity("10.0000"),
            saldo_resultante=StockQuantity("100.0000"),
            costo_unitario_ppp=MoneyAmount("1000.00"),
            costo_total_movimiento=MoneyAmount("10000.00"),
            actor_user_id=1,
        )
        with pytest.raises(FrozenInstanceError):
            movement.motivo_merma = "daño"  # type: ignore[misc]

    def test_kardex_audit_record_full_lifecycle(self) -> None:
        transfer_id = uuid4()
        now_dt = datetime.now(UTC)
        record = KardexAuditRecord(
            id=1001,
            created_at=now_dt,
            fecha_recuento=date(2026, 10, 25),
            producto_id=50,
            nombre_producto="Harina Integral",
            unidad_medida="kg",
            bodega_id=2,
            nombre_bodega="Cocina Principal",
            tipo_movimiento="merma",
            cantidad=Decimal("3.0000"),
            saldo_resultante=Decimal("27.0000"),
            costo_unitario_ppp=Decimal("1200.00"),
            costo_total_movimiento=Decimal("3600.00"),
            actor_user_id=4,
            user_display_name="Chef Ejecutivo",
            motivo_merma="daño",
            descripcion_merma="Saco roto durante faena",
            transfer_id=transfer_id,
            tenant_id="tenant_santiago",
        )
        assert record.id == 1001
        assert record.nombre_producto == "Harina Integral"
        assert record.unidad_medida == "kg"
        assert record.movement_sign == MovementSign.NEGATIVE

        # Delta calculado automáticamente
        delta = record.audit_delta
        assert delta.before == Decimal("30.0000")
        assert delta.after == Decimal("27.0000")
        assert delta.delta == Decimal("-3.0000")
        assert delta.unit == "kg"

        # Serialización a dict para presentación
        data = record.to_dict()
        assert data["id"] == 1001
        assert data["nombre_producto"] == "Harina Integral"
        assert data["delta_before"] == Decimal("30.0000")
        assert data["delta_after"] == Decimal("27.0000")
        assert data["movement_sign"] == "-"
        assert data["transfer_id"] == str(transfer_id)

    def test_kardex_audit_record_forbids_floats(self) -> None:
        now_dt = datetime.now(UTC)
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            KardexAuditRecord(
                id=1,
                created_at=now_dt,
                fecha_recuento=date.today(),
                producto_id=1,
                nombre_producto="Test",
                unidad_medida="kg",
                bodega_id=1,
                nombre_bodega="Bodega",
                tipo_movimiento="salida",
                cantidad=5.0,  # FLOAT ILEGAL
                saldo_resultante=Decimal("45.0000"),
                costo_unitario_ppp=Decimal("100.00"),
                costo_total_movimiento=Decimal("500.00"),
                actor_user_id=1,
                user_display_name="Admin",
            )


# ============================================================================
# 6. TIMEZONE CONVERTER: America/Santiago
# ============================================================================


class TestTimezoneConverter:
    """Verifica la proyección determinista de UTC a hora local de Chile."""

    def test_timezone_conversion_to_chile(self) -> None:
        utc_dt = datetime(2026, 10, 25, 15, 30, 0, tzinfo=UTC)
        chile_dt = TimezoneConverter.to_chile(utc_dt)
        # Chile en octubre está en horario de verano (UTC-3)
        assert chile_dt.hour == 12
        assert chile_dt.minute == 30
        assert TimezoneConverter.format_chile_datetime(utc_dt) == "25/10/2026 12:30:00"
        assert TimezoneConverter.format_chile_date(utc_dt) == "25/10/2026"


# ============================================================================
# 7. CLEAN ARCHITECTURE GATE: Cero dependencias de infraestructura en domain
# ============================================================================


class TestCleanArchitectureDomainIsolation:
    """Asegura que domain/ no contenga imports de frameworks o persistencia."""

    def test_domain_has_zero_imports_of_fastapi_or_sqlalchemy(self) -> None:
        domain_dir = Path(__file__).resolve().parents[3] / "src" / "modules" / "inventory" / "domain"
        forbidden = {"fastapi", "sqlalchemy", "starlette", "pydantic"}

        violations: list[str] = []
        for py_file in domain_dir.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=py_file.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in forbidden:
                            violations.append(f"{py_file.name}:{node.lineno} imports '{alias.name}'")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        if top in forbidden:
                            violations.append(f"{py_file.name}:{node.lineno} imports from '{node.module}'")

        assert not violations, "Violación estricta de Clean Architecture en domain:\n" + "\n".join(violations)
