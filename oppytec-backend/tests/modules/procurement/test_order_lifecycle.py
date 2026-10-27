"""
oppytec-backend/tests/modules/procurement/test_order_lifecycle.py
Certificación 5D (Tarea 7.4) — Ciclo de Vida Completo de Órdenes de Compra:
1. Unitario: Máquina de estados estricta (`BORRADOR` -> `SOLICITADA` -> `EN_CAMINO` -> `RECIBIDA_PARCIAL` -> `RECIBIDA_TOTAL` y `CANCELADA`).
2. Integración: Flujo transaccional en `ProcurementService` (creación, edición, recepción parcial/total, incidencias y cancelación).
3. Propiedades (Hypothesis): Invariantes matemáticos de totalización en `Decimal(14, 2)` e IVA chileno (19%) con 0% float.
4. Contratos: Validación de esquemas Pydantic v2 (`PurchaseOrderCreateRequest`, `PurchaseOrderResponse`, `CancelOrderRequest`).
5. Paridad Matemática con Legacy: Redondeo bancario `ROUND_HALF_UP` y conciliación tripartita (`reconcile_three_way`).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.exceptions import DomainValidationError, ResourceNotFoundError
from src.modules.procurement.application.procurement_service import ProcurementService
from src.modules.procurement.domain import (
    DocLine,
    IncidenceResolution,
    IncidenceType,
    InvalidPurchaseStatusTransitionError,
    MatchStatus,
    MoneyAmount,
    PurchaseItem,
    PurchaseOrder,
    PurchaseStatus,
    reconcile_three_way,
)
from src.modules.procurement.presentation.schemas import (
    CancelOrderRequest,
    PurchaseIncidenceCreateRequest,
    PurchaseOrderCreateRequest,
    PurchaseOrderItemPayload,
    PurchaseOrderResponse,
)

pytestmark = [pytest.mark.unit]

# Estrategias Hypothesis para cantidades Decimal(12, 4) y costos unitarios Decimal(14, 2)
st_quantity = st.decimals(
    min_value=Decimal("0.0100"),
    max_value=Decimal("5000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
st_unit_cost = st.decimals(
    min_value=Decimal("1.00"),
    max_value=Decimal("1000000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
st_line_tuple = st.tuples(
    st.integers(min_value=1, max_value=9999),
    st_quantity,
    st_unit_cost,
)


# ==============================================================================
# DIMENSIÓN 1: UNITARIO — MÁQUINA DE ESTADOS DEL AGREGADO PURCHASE ORDER
# ==============================================================================


class TestOrderLifecycleStateTransitions:
    """Verifica todas las rutas válidas e inválidas de la máquina de estados de compras."""

    def test_happy_path_borrador_to_recibida_total_via_parcial(self) -> None:
        """Ruta canónica: BORRADOR -> SOLICITADA -> EN_CAMINO -> RECIBIDA_PARCIAL -> RECIBIDA_TOTAL."""
        item = PurchaseItem(
            producto_id=101,
            cantidad_solicitada=Decimal("20.0000"),
            precio_unitario=MoneyAmount("4500.00"),
        )
        neto = item.subtotal_linea or MoneyAmount("90000.00")
        iva = MoneyAmount((neto.to_decimal() * Decimal("0.19")).quantize(Decimal("0.01")))
        total = neto + iva

        order = PurchaseOrder(
            numero_orden="OC-2026-5D-001",
            proveedor_id=10,
            bodega_destino_id=1,
            monto_neto=neto,
            monto_impuestos=iva,
            monto_total=total,
            items=[item],
        )

        assert order.estado == PurchaseStatus.BORRADOR
        assert order.estado.is_terminal is False
        assert order.estado.is_receivable is False

        order.submit()
        assert order.estado == PurchaseStatus.SOLICITADA
        assert order.estado.is_terminal is False

        order.mark_in_transit()
        assert order.estado == PurchaseStatus.EN_CAMINO
        assert order.estado.is_receivable is True

        order.receive_delivery(fully_received=False)
        assert order.estado == PurchaseStatus.RECIBIDA_PARCIAL
        assert order.estado.is_receivable is True
        assert order.estado.is_terminal is False

        order.receive_delivery(fully_received=True)
        assert order.estado == PurchaseStatus.RECIBIDA_TOTAL
        assert order.estado.is_terminal is True
        assert order.estado.is_receivable is False

    def test_direct_reception_en_camino_to_recibida_total(self) -> None:
        """Ruta directa cuando llega el 100% en la primera entrega: EN_CAMINO -> RECIBIDA_TOTAL."""
        order = PurchaseOrder(
            numero_orden="OC-2026-5D-002",
            proveedor_id=10,
            bodega_destino_id=1,
            monto_neto=MoneyAmount("50000.00"),
            monto_impuestos=MoneyAmount("9500.00"),
            monto_total=MoneyAmount("59500.00"),
        )
        order.submit()
        order.mark_in_transit()
        order.receive_delivery(fully_received=True)
        assert order.estado == PurchaseStatus.RECIBIDA_TOTAL
        assert order.estado.is_terminal is True

    @pytest.mark.parametrize(
        "non_terminal_setup",
        [
            [],
            ["submit"],
            ["submit", "mark_in_transit"],
            ["submit", "mark_in_transit", "partial"],
        ],
    )
    def test_cancellation_allowed_from_any_non_terminal_state(
        self, non_terminal_setup: list[str]
    ) -> None:
        """Toda orden en estado no terminal (BORRADOR, SOLICITADA, EN_CAMINO, RECIBIDA_PARCIAL) puede cancelarse."""
        order = PurchaseOrder(
            numero_orden="OC-2026-5D-CANCEL",
            proveedor_id=1,
            bodega_destino_id=1,
            monto_neto=MoneyAmount("10000.00"),
            monto_impuestos=MoneyAmount("1900.00"),
            monto_total=MoneyAmount("11900.00"),
        )
        for step in non_terminal_setup:
            if step == "submit":
                order.submit()
            elif step == "mark_in_transit":
                order.mark_in_transit()
            elif step == "partial":
                order.receive_delivery(fully_received=False)

        order.cancel()
        assert order.estado == PurchaseStatus.CANCELADA
        assert order.estado.is_terminal is True

    def test_forbidden_transitions_raise_domain_error(self) -> None:
        """Estados terminales (RECIBIDA_TOTAL, CANCELADA) y saltos ilegales lanzan InvalidPurchaseStatusTransitionError."""
        order = PurchaseOrder(
            numero_orden="OC-2026-5D-ILLEGAL",
            proveedor_id=1,
            bodega_destino_id=1,
            monto_neto=MoneyAmount("10000.00"),
            monto_impuestos=MoneyAmount("1900.00"),
            monto_total=MoneyAmount("11900.00"),
        )
        # BORRADOR no puede recepcionar sin haberse solicitado y despachado en el agregado puro
        with pytest.raises(InvalidPurchaseStatusTransitionError):
            order.receive_delivery(fully_received=True)

        order.cancel()
        with pytest.raises(InvalidPurchaseStatusTransitionError):
            order.submit()
        with pytest.raises(InvalidPurchaseStatusTransitionError):
            order.cancel()


# ==============================================================================
# DIMENSIÓN 2: INTEGRACIÓN — SERVICIO DE APLICACIÓN PROCUREMENT SERVICE
# ==============================================================================


class TestProcurementServiceLifecycleIntegration:
    """Verifica el flujo completo en `ProcurementService` incluyendo edición, recepción e incidencias."""

    @pytest.mark.asyncio
    async def test_service_complete_lifecycle_borrador_to_recibida_total(self) -> None:
        service = ProcurementService(use_in_memory=True)

        # 1. Crear en BORRADOR
        created = await service.create_order(
            None,
            {
                "numero_orden": "OC-LIFE-001",
                "proveedor_id": 7,
                "supplier_name": "Pollo King",
                "bodega_destino_id": 2,
                "estado": "BORRADOR",
                "items": [
                    {
                        "producto_id": 10,
                        "cantidad_solicitada": Decimal("40.0000"),
                        "costo_unitario_neto": Decimal("2500.00"),
                    },
                    {
                        "producto_id": 20,
                        "cantidad_solicitada": Decimal("10.0000"),
                        "costo_unitario_neto": Decimal("5000.00"),
                    },
                ],
                "notas": "Borrador inicial",
            },
            user_id=501,
        )
        order_id = created["id"]
        assert created["estado"] == "BORRADOR"
        assert created["monto_neto"] == Decimal("150000.00")
        assert created["monto_impuestos"] == Decimal("28500.00")
        assert created["monto_total"] == Decimal("178500.00")

        # 2. Actualizar a SOLICITADA
        submitted = await service.update_order(
            None,
            order_id,
            {"estado": "SOLICITADA", "notas": "Enviada al proveedor Pollo King"},
        )
        assert submitted["estado"] == "SOLICITADA"

        # 3. Recepción Parcial (llegan 25 de 40 del producto 10, y 10 de 10 del producto 20)
        partial = await service.receive_goods(
            None,
            order_id,
            [
                {
                    "producto_id": 10,
                    "cantidad_recibida": Decimal("25.0000"),
                    "lote_codigo": "LOTE-A1",
                },
                {
                    "producto_id": 20,
                    "cantidad_recibida": Decimal("10.0000"),
                    "lote_codigo": "LOTE-B1",
                },
            ],
            user_id=502,
        )
        assert partial["estado"] == "RECIBIDA_PARCIAL"
        assert partial["receptor_user_id"] == 502

        # En estado RECIBIDA_PARCIAL ya no se permite edición administrativa de cabecera
        with pytest.raises(DomainValidationError):
            await service.update_order(None, order_id, {"notas": "Intento ilegal"})

        # 4. Registrar incidencia por los 15 faltantes
        incidence = await service.register_incidence(
            None,
            order_id,
            {
                "tipo_incidencia": IncidenceType.DIFERENCIA_CANTIDAD.value,
                "cantidad_afectada": Decimal("15.0000"),
                "monto_disputa": Decimal("37500.00"),
                "resolucion": IncidenceResolution.REEMPLAZO.value,
                "descripcion": "Quedan 15 unidades pendientes para segundo camión",
            },
            user_id=502,
        )
        assert incidence["tipo_incidencia"] == "DIFERENCIA_CANTIDAD"
        assert incidence["resolucion"] == "REEMPLAZO"

        # 5. Segunda recepción que completa el pedido -> RECIBIDA_TOTAL
        completed = await service.receive_goods(
            None,
            order_id,
            [
                {
                    "producto_id": 10,
                    "cantidad_recibida": Decimal("15.0000"),
                    "lote_codigo": "LOTE-A2",
                }
            ],
            user_id=502,
        )
        assert completed["estado"] == "RECIBIDA_TOTAL"

        # 6. Una orden RECIBIDA_TOTAL no puede volver a recepcionarse ni cancelarse
        with pytest.raises(DomainValidationError):
            await service.receive_goods(
                None,
                order_id,
                [{"producto_id": 10, "cantidad_recibida": Decimal("1.0000")}],
                user_id=502,
            )

        with pytest.raises(DomainValidationError):
            await service.cancel_order(
                None,
                order_id,
                reason="Intento de cancelar orden ya recibida totalmente",
                user_id=501,
            )

    @pytest.mark.asyncio
    async def test_service_cancellation_and_validation_guards(self) -> None:
        service = ProcurementService(use_in_memory=True)

        # Rechaza orden sin ítems
        with pytest.raises(DomainValidationError):
            await service.create_order(
                None,
                {"proveedor_id": 1, "bodega_destino_id": 1, "items": []},
                user_id=1,
            )

        order = await service.create_order(
            None,
            {
                "numero_orden": "OC-CANCEL-5D",
                "proveedor_id": 1,
                "bodega_destino_id": 1,
                "estado": "SOLICITADA",
                "items": [
                    {
                        "producto_id": 5,
                        "cantidad_solicitada": Decimal("10.0000"),
                        "costo_unitario_neto": Decimal("1000.00"),
                    }
                ],
            },
            user_id=10,
        )

        # Motivo vacío debe fallar
        with pytest.raises(DomainValidationError):
            await service.cancel_order(None, order["id"], reason="   ", user_id=10)

        cancelled = await service.cancel_order(
            None,
            order["id"],
            reason="Proveedor sin disponibilidad de stock",
            user_id=10,
        )
        assert cancelled["estado"] == "CANCELADA"

        # Orden cancelada rechaza recepción y re-cancelación
        with pytest.raises(DomainValidationError):
            await service.receive_goods(
                None,
                order["id"],
                [{"producto_id": 5, "cantidad_recibida": Decimal("5.0000")}],
                user_id=10,
            )

        with pytest.raises(DomainValidationError):
            await service.cancel_order(
                None,
                order["id"],
                reason="Segunda cancelación",
                user_id=10,
            )

        # Orden inexistente lanza ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError):
            await service.get_order_detail(None, 999999)


# ==============================================================================
# DIMENSIÓN 3 Y 5: PROPIEDADES (HYPOTHESIS) & PARIDAD MATEMÁTICA DECIMAL(14, 2)
# ==============================================================================


class TestOrderTotalizationAndVatProperties:
    """Pruebas basadas en propiedades (Hypothesis) para totalización Decimal(14, 2) e IVA 19%."""

    @given(lines=st.lists(st_line_tuple, min_size=1, max_size=15))
    @settings(max_examples=60, deadline=None)
    @pytest.mark.asyncio
    async def test_property_order_totals_and_19_percent_iva_exact_decimal(
        self, lines: list[tuple[int, Decimal, Decimal]]
    ) -> None:
        """
        Propiedad universal:
        Para cualquier conjunto de líneas con cantidad Decimal(12, 4) > 0 y costo Decimal(14, 2) >= 0:
        1. Cada subtotal de línea es exactamente `(qty * unit_cost).quantize(Decimal("0.01"))`.
        2. `monto_neto` es exactamente la suma de los subtotales de línea.
        3. `monto_impuestos` es exactamente `(monto_neto * Decimal("0.19")).quantize(Decimal("0.01"))`.
        4. `monto_total == monto_neto + monto_impuestos`.
        5. Todos los valores son instancias puras de `Decimal` con escala 2 (`Decimal(14, 2)`).
        """
        service = ProcurementService(use_in_memory=True)
        payload_items = [
            {
                "producto_id": prod_id,
                "cantidad_solicitada": qty,
                "costo_unitario_neto": cost,
            }
            for prod_id, qty, cost in lines
        ]

        created = await service.create_order(
            None,
            {
                "proveedor_id": 1,
                "bodega_destino_id": 1,
                "estado": "BORRADOR",
                "items": payload_items,
            },
            user_id=1,
        )

        expected_subtotals = [
            (qty * cost).quantize(Decimal("0.01"))
            for _, qty, cost in lines
        ]
        expected_neto = sum(expected_subtotals, Decimal("0.00"))
        expected_iva = (expected_neto * Decimal("0.19")).quantize(Decimal("0.01"))
        expected_total = expected_neto + expected_iva

        assert isinstance(created["monto_neto"], Decimal)
        assert isinstance(created["monto_impuestos"], Decimal)
        assert isinstance(created["monto_total"], Decimal)

        assert created["monto_neto"] == expected_neto
        assert created["monto_impuestos"] == expected_iva
        assert created["monto_total"] == expected_total
        assert created["monto_neto"] + created["monto_impuestos"] == created["monto_total"]

        for idx, item_out in enumerate(created["items"]):
            assert isinstance(item_out["subtotal_linea"], Decimal)
            assert item_out["subtotal_linea"] == expected_subtotals[idx]

    @given(qty=st_quantity, cost=st_unit_cost)
    @settings(max_examples=50, deadline=None)
    def test_property_purchase_item_entity_subtotal_invariance(
        self, qty: Decimal, cost: Decimal
    ) -> None:
        """Verifica que `PurchaseItem` calcule siempre su `subtotal_linea` en `MoneyAmount` con ROUND_HALF_UP."""
        price_vo = MoneyAmount(cost)
        item = PurchaseItem(
            producto_id=1,
            cantidad_solicitada=qty,
            precio_unitario=price_vo,
        )
        expected = (cost * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert item.subtotal_linea is not None
        assert item.subtotal_linea.to_decimal() == expected
        assert item.pending_quantity() == qty
        assert item.is_fully_received() is False


# ==============================================================================
# DIMENSIÓN 4: CONTRATOS PYDANTIC V2 & CONCILIACIÓN 3-WAY
# ==============================================================================


class TestOrderSchemasAndThreeWayReconciliationContracts:
    """Valida contratos de entrada/salida y conciliación OC vs Recepción vs Factura."""

    def test_pydantic_order_schemas_preserve_decimal_types(self) -> None:
        req = PurchaseOrderCreateRequest(
            numero_orden="OC-CONTRACT-01",
            proveedor_id=3,
            supplier_name="Pollo King",
            bodega_destino_id=1,
            estado="SOLICITADA",
            moneda="CLP",
            items=[
                PurchaseOrderItemPayload(
                    producto_id=9,
                    cantidad_solicitada=Decimal("12.5000"),
                    costo_unitario_neto=Decimal("3200.00"),
                    lote_codigo="LOTE-PK-99",
                    fecha_vencimiento=date(2027, 1, 15),
                )
            ],
        )
        assert req.items is not None
        assert isinstance(req.items[0].cantidad_solicitada, Decimal)
        assert isinstance(req.items[0].costo_unitario_neto, Decimal)

        resp = PurchaseOrderResponse(
            id=1,
            po_number="OC-CONTRACT-01",
            numero_orden="OC-CONTRACT-01",
            supplier_id=3,
            proveedor_id=3,
            supplier_name="Pollo King",
            proveedor_nombre="Pollo King",
            bodega_destino_id=1,
            estado="SOLICITADA",
            moneda="CLP",
            line_count=1,
            items_count=1,
            net_total=Decimal("40000.00"),
            monto_neto=Decimal("40000.00"),
            monto_impuestos=Decimal("7600.00"),
            monto_total=Decimal("47600.00"),
            fecha_emision=datetime.now(UTC),
        )
        assert resp.monto_total == Decimal("47600.00")

        inc_req = PurchaseIncidenceCreateRequest(
            tipo_incidencia="PRODUCTO_DANADO",
            cantidad_afectada=Decimal("2.0000"),
            monto_disputa=Decimal("6400.00"),
            descripcion="Envase perforado en transporte",
        )
        assert inc_req.monto_disputa == Decimal("6400.00")

        cancel_req = CancelOrderRequest(motivo="Duplicidad de orden de compra")
        assert cancel_req.motivo == "Duplicidad de orden de compra"

    def test_three_way_reconciliation_detects_quantity_and_cost_discrepancies(self) -> None:
        oc_lines = [DocLine(producto_id=1, quantity=Decimal("50"), unit_cost=Decimal("2000.00"))]
        rec_lines = [DocLine(producto_id=1, quantity=Decimal("45"), unit_cost=Decimal("2000.00"))]
        inv_lines = [DocLine(producto_id=1, quantity=Decimal("50"), unit_cost=Decimal("2000.00"))]

        res = reconcile_three_way(oc_lines, rec_lines, inv_lines)
        assert res.status != MatchStatus.MATCHED
        assert res.quantity_diffs[1] != Decimal("0")
        assert res.invoice_total_diff == Decimal("10000.00")
