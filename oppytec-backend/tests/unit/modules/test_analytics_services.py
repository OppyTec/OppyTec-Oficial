"""
Pruebas unitarias 1:1 para `src/modules/analytics/`, `scripts/seed_dev_data.py` y `scripts/anonymize_for_staging.py`.
Verifica `KpiSnapshot`, `FinancialProjection` en `Decimal`, el seeder determinista y el anonimizador ISO 27001.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from scripts.anonymize_for_staging import anonymize_user_record
from scripts.seed_dev_data import build_deterministic_dev_seed

from src.modules.analytics.infrastructure.models import (
    FinancialProjection,
    KpiSnapshot,
)

pytestmark = pytest.mark.unit


def test_analytics_kpi_and_financial_projection_decimal_precision() -> None:
    """Verifica que los snapshots de KPIs y proyecciones financieras usen `Decimal` exacto."""
    kpi = KpiSnapshot(
        periodo_codigo="2026-10",
        fecha_corte=datetime.now(UTC),
        ventas_totales=Decimal("45000000.00"),
        costo_ventas=Decimal("13500000.00"),
        mermas_totales=Decimal("450000.00"),
        food_cost_porcentaje=Decimal("30.00"),
    )
    proj = FinancialProjection(
        horizonte_meses=6,
        moneda="CLP",
        ingresos_proyectados=Decimal("270000000.00"),
        egresos_proyectados=Decimal("195000000.00"),
        margen_neto_proyectado=Decimal("75000000.00"),
    )
    assert proj.ingresos_proyectados - proj.egresos_proyectados == proj.margen_neto_proyectado
    assert kpi.food_cost_porcentaje == Decimal("30.00")


def test_dev_seeder_and_staging_anonymizer() -> None:
    """Verifica el paquete de seed determinista y el anonimizador de PII para Staging."""
    bundle = build_deterministic_dev_seed()
    assert bundle.tenant_schema == "tenant_pacifico_centro"
    assert "Pollo King" in bundle.immutable_suppliers
    assert bundle.products_count == 20
    assert bundle.recipes_count == 5

    sanitized = anonymize_user_record(
        {"email": "juan.perez@cliente-real.cl", "tax_id": "15.432.198-7"}
    )
    assert sanitized["email"].endswith("@oppytec.com")
    assert "juan.perez" not in sanitized["email"]
    assert sanitized["tax_id"] != "15.432.198-7"
