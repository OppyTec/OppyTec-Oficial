"""
oppytec-backend/tests/modules/inventory/test_waste_analytics.py
Suite de Certificación 5D (Tarea 7.4) en `tests/modules/inventory/`:
Verifica agregaciones temporales, desglose por motivos y ratios de mermas valorizadas a PPP
en `MermaAnalyticsService` y `WasteService`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.merma_analytics_service import (
    MermaAnalyticsService,
)
from src.modules.inventory.application.waste_service import WasteService
from src.modules.inventory.domain.kardex_math import (
    waste_requires_approval,
    waste_total_cost,
)

pytestmark = [pytest.mark.unit]

st_qty = st.decimals(
    min_value=Decimal("0.2500"),
    max_value=Decimal("250.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
st_ppp = st.decimals(
    min_value=Decimal("50.00"),
    max_value=Decimal("80000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


class TestInventoryWasteAnalyticsSuite:
    """Suite de inventario para ratios de mermas valorizadas a PPP y agregaciones."""

    @given(
        items=st.lists(
            st.tuples(
                st.sampled_from(["VENCIMIENTO", "DANO", "ERROR_PREPARACION", "MAL_ESTADO", "OTRO"]),
                st_qty,
                st_ppp,
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_inventory_waste_ppp_ratios_and_history_consistency(
        self,
        items: list[tuple[str, Decimal, Decimal]],
    ) -> None:
        """Verifica con Hypothesis que la pérdida neta PPP y el historial coincidan al 100%."""
        svc = MermaAnalyticsService(use_in_memory=True)
        expected_loss = Decimal("0.00")

        for idx, (motivo, qty, ppp) in enumerate(items):
            cost = waste_total_cost(qty, ppp)
            expected_loss += cost
            svc.register_in_memory_merma(
                {
                    "id": idx + 1,
                    "producto_id": idx + 1,
                    "producto_nombre": f"Producto {idx + 1}",
                    "bodega_id": 1,
                    "categoria_id": 1,
                    "categoria_nombre": "Perecederos",
                    "cantidad": qty,
                    "costo_total": cost,
                    "motivo": motivo,
                    "estado_aprobacion": "APROBADA",
                    "fecha_merma": date.today().isoformat(),
                    "reportado_por_user_id": 1,
                }
            )

        analytics = await svc.get_analytics(None, bodega_id=1)
        assert analytics["total_perdida_ppp"] == expected_loss
        assert analytics["items_mermados_count"] == len(items)

        history_rows, total = await svc.get_history(None, bodega_id=1)
        assert total == len(items)
        assert sum((r["costo_total"] for r in history_rows), Decimal("0.00")) == expected_loss

    def test_waste_rejection_does_not_deduct_kardex(self) -> None:
        """Rechazar una merma PENDIENTE mantiene intacto el saldo del Kardex."""
        inv = InventoryService()
        inv.register_movement(
            producto_id=50,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("40.0000"),
            unit_cost=Decimal("3000.00"),
            actor_user_id=1,
        )
        waste_svc = WasteService(inventory=inv, approval_threshold=Decimal("10000.00"))
        rec = waste_svc.report_waste(
            producto_id=50,
            bodega_id=1,
            quantity=Decimal("10.0000"),
            unit_cost=Decimal("3000.00"),
            reason="OTRO",
            reporter_user_id=10,
            tenant_id="tenant_inv",
        )
        assert rec.status == "PENDIENTE"
        assert waste_requires_approval(rec.total_cost, Decimal("10000.00")) is True

        rejected = waste_svc.reject(rec.waste_id, tenant_id="tenant_inv")
        assert rejected.status == "RECHAZADA"
        assert inv.balance(50, 1) == Decimal("40.0000")
