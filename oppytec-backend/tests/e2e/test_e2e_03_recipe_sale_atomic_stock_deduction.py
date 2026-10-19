"""
Flujo E2E 03: Escandallos Recursivos, Simulador de Margen, Venta POS Atómica, Buffet y Eventos
(`tests/e2e/test_e2e_03_recipe_sale_atomic_stock_deduction.py`).

Recorre el flujo completo de ingeniería de menú y operación gastronómica:
1. Creación de sub-receta base y receta principal con factor de merma técnica (`/api/v1/recipes/escandallos`).
2. Simulación de precio de carta y margen de contribución (`/api/v1/recipes/simulate-margin`).
3. Abastecimiento inicial de stock en Kardex y explosión de venta POS descontando insumos (`/api/v1/operations/sales`).
4. Liquidación de servicio Buffet por comensal (`pax`) descontando sobrante reutilizable (`/api/v1/operations/buffet`).
5. Cotización y margen bruto de Evento de Banquetería (`/api/v1/operations/events`).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.e2e


def test_e2e_03_recipe_escandallo_pos_sale_explosion_buffet_and_events() -> None:
    """
    Ejecuta extremo a extremo el ciclo de recetas, simulación de margen y consumo operativo POS/Buffet/Eventos.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()

    chef_token = create_access_token(
        user_id=310,
        holding_id="holding_e2e_03",
        tenant_id="tenant_e2e_03",
        hierarchy_rank=20,
        contracted_modules=["recipes", "inventory", "operations"],
        role_grants=[
            "recipes.escandallos.write",
            "recipes.escandallos.read",
            "recipes.margins.simulate",
            "inventory.kardex.write",
            "inventory.kardex.read",
            "operations.sales.create",
            "operations.buffet.calculate",
            "operations.events.create",
        ],
        accessible_tenants=["tenant_e2e_03"],
    )
    headers = {
        "Authorization": f"Bearer {chef_token}",
        "X-Tenant-ID": "tenant_e2e_03",
    }

    with TestClient(app) as client:
        # 1. Sub-receta base (`recipe_id=601`): Caldo Concentrado (rinde 4 porciones, costo total 2.000 -> 500/porción)
        sub_recipe_resp = client.post(
            "/api/v1/recipes/escandallos",
            headers=headers,
            json={
                "recipe_id": 601,
                "name": "Caldo Concentrado de Ave",
                "yield_portions": "4",
                "net_price": "2000",
                "lines": [
                    {
                        "ingredient_id": 8101,
                        "quantity": "1.00",
                        "unit_cost": "2000",
                        "waste_pct": "0",
                    }
                ],
            },
        )
        assert sub_recipe_resp.status_code == 201
        assert Decimal(sub_recipe_resp.json()["portion_cost"]) == Decimal("500.0000")

        # Receta principal (`recipe_id=602`): Risotto con Pechuga Pollo King
        # - 1 porción de sub-receta 601 = 500
        # - 0.25 kg de Pechuga (ingredient_id=8102) con 20% merma técnica -> 0.25 * 1.20 = 0.30 kg * 6.000 = 1.800
        # - 0.10 kg de Arroz Carnaroli (ingredient_id=8103) sin merma -> 0.10 * 2.000 = 200
        # Costo total por porción = 500 + 1.800 + 200 = 2.500. Precio venta neto = 10.000 -> Food Cost = 25.00%
        main_recipe_resp = client.post(
            "/api/v1/recipes/escandallos",
            headers=headers,
            json={
                "recipe_id": 602,
                "name": "Risotto Cremoso Pollo King",
                "yield_portions": "1",
                "net_price": "10000",
                "lines": [
                    {
                        "sub_recipe_id": 601,
                        "quantity": "1",
                        "unit_cost": "0",
                        "waste_pct": "0",
                    },
                    {
                        "ingredient_id": 8102,
                        "quantity": "0.25",
                        "unit_cost": "6000",
                        "waste_pct": "20",
                    },
                    {
                        "ingredient_id": 8103,
                        "quantity": "0.10",
                        "unit_cost": "2000",
                        "waste_pct": "0",
                    },
                ],
            },
        )
        assert main_recipe_resp.status_code == 201
        main_data = main_recipe_resp.json()
        assert Decimal(main_data["portion_cost"]) == Decimal("2500.0000")
        assert Decimal(main_data["food_cost_pct"]) == Decimal("25.00")
        assert Decimal(main_data["margin_amount"]) == Decimal("7500.00")
        assert Decimal(main_data["margin_pct"]) == Decimal("75.00")

        # 2. Simulador de margen proponiendo precio neto CLP 12.500 -> Food Cost baja a 20.00%
        sim_resp = client.post(
            "/api/v1/recipes/simulate-margin",
            headers=headers,
            json={
                "portion_cost": "2500",
                "proposed_net_price": "12500",
            },
        )
        assert sim_resp.status_code == 200
        assert Decimal(sim_resp.json()["food_cost_pct"]) == Decimal("20.00")
        assert Decimal(sim_resp.json()["margin_amount"]) == Decimal("10000.00")

        # 3. Explosión de venta POS por 6 porciones de `recipe_id=602`
        pos_sale_resp = client.post(
            "/api/v1/operations/sales",
            headers=headers,
            json={
                "bodega_id": 3,
                "items": [{"recipe_id": 602, "portions": "6"}],
                "recipe_ingredients": {
                    "602": {
                        "8102": "0.30",
                        "8103": "0.10",
                    }
                },
            },
        )
        assert pos_sale_resp.status_code == 201
        consumed = pos_sale_resp.json()["consumed_by_ingredient"]
        assert Decimal(consumed["8102"]) == Decimal("1.8000")
        assert Decimal(consumed["8103"]) == Decimal("0.6000")

        # 4. Liquidación de Buffet para 100 comensales (`pax=100`), costo bruto 550.000 y recupero de 50.000 -> 5.000/pax
        buffet_resp = client.post(
            "/api/v1/operations/buffet",
            headers=headers,
            json={
                "service_name": "Buffet Ejecutivo Mediodía",
                "total_buffet_cost": "550000",
                "pax": 100,
                "leftover_value": "50000",
            },
        )
        assert buffet_resp.status_code == 200
        assert Decimal(buffet_resp.json()["total_buffet_cost"]) == Decimal("550000")
        assert Decimal(buffet_resp.json()["leftover_value"]) == Decimal("50000")
        assert Decimal(buffet_resp.json()["cost_per_pax"]) == Decimal("5000.00")

        # 5. Evento de Banquetería para 150 asistentes
        event_resp = client.post(
            "/api/v1/operations/events",
            headers=headers,
            json={
                "event_name": "Matrimonio Salón Pacífico",
                "attendees_pax": 150,
                "food_cost_per_pax": "9000",
                "net_price_per_pax": "30000",
            },
        )
        assert event_resp.status_code == 201
        evt_data = event_resp.json()
        assert Decimal(evt_data["total_food_cost"]) == Decimal("1350000.00")
        assert Decimal(evt_data["total_net_revenue"]) == Decimal("4500000.00")
        assert Decimal(evt_data["gross_margin"]) == Decimal("3150000.00")
