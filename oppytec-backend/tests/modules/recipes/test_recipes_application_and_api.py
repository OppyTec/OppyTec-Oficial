"""
oppytec-backend/tests/modules/recipes/test_recipes_application_and_api.py
Suite exhaustiva de pruebas de integración y API para la FASE 2:
- CRUD de recetas estáticas y dinámicas con escandallo base y peor caso en Decimal.
- Prevención de ciclos en subrecetas vía API (DAG anti-recursión cíclica -> 422).
- CRUD de combos fijos y dinámicos con disponibilidad de stock y grupos de opciones.
- Simulación en vivo de costo dinámico POST /api/v1/recipes/{id}/simulate-cost.
- Biblioteca de grupos de opciones polimórficos y validaciones de integridad.
- Verificación estricta de guardias RBAC de 3 niveles y respuestas RFC 7807 (ProblemDetails).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app
from src.modules.recipes.presentation.router import (
    get_combo_service,
    get_option_group_service,
    get_recipe_service,
)

pytestmark = pytest.mark.integration

_ALL_MODULES = [
    "catalog",
    "inventory",
    "recipes",
    "procurement",
    "operations",
    "analytics",
    "oppyfy",
    "audit",
    "settings",
    "tenancy",
]

_RECIPES_FULL_GRANTS = [
    "recipes.recipe.read",
    "recipes.recipe.write",
    "recipes.recipe.delete",
    "recipes.recipe.costs",
    "recipes.combo.read",
    "recipes.combo.write",
    "recipes.combo.delete",
    "recipes.options.manage",
    "recipes.escandallos.read",
    "recipes.escandallos.write",
    "recipes.margins.simulate",
]

_RECIPES_READ_ONLY_GRANTS = [
    "recipes.recipe.read",
    "recipes.combo.read",
]


@pytest.fixture(autouse=True)
def setup_services_and_env():
    """Inicializa estado en memoria limpio y catálogo de insumos con costos PPP."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    rec_srv = get_recipe_service()
    rec_srv.reset()
    get_combo_service().reset()
    get_option_group_service().reset()

    # Pre-configurar insumos y costos PPP en Decimal
    rec_srv.set_ingredient_cost(101, Decimal("15.50"), "Lomo de Res", "gr")
    rec_srv.set_ingredient_cost(102, Decimal("3.20"), "Cebolla Morada", "gr")
    rec_srv.set_ingredient_cost(103, Decimal("4.10"), "Tomate", "gr")
    rec_srv.set_ingredient_cost(104, Decimal("2500.00"), "Papas Fritas Gourmet", "porcion")
    rec_srv.set_ingredient_cost(105, Decimal("1200.00"), "Arroz Blanco", "porcion")
    rec_srv.set_ingredient_cost(106, Decimal("3500.00"), "Bebida Lata 350ml", "und")
    rec_srv.set_ingredient_cost(107, Decimal("850.00"), "Salsa BBQ Casera", "porcion")
    rec_srv.set_ingredient_cost(108, Decimal("1100.00"), "Salsa Queso Cheddar", "porcion")


@pytest.fixture
def api_client():
    app = create_app()
    return TestClient(app)


def _build_headers(user_id: int, role_grants: list[str], tenant_id: str = "tenant_test") -> dict[str, str]:
    token = create_access_token(
        user_id=user_id,
        holding_id="holding_test",
        tenant_id=tenant_id,
        hierarchy_rank=10,
        contracted_modules=_ALL_MODULES,
        role_grants=role_grants,
        accessible_tenants=[tenant_id],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


# ==============================================================================
# 1. BIBLIOTECA DE GRUPOS DE OPCIONES & VALIDACIONES DE INTEGRIDAD
# ==============================================================================


class TestOptionGroupsAPI:
    """Pruebas para /api/v1/recipes/option-groups."""

    def test_create_option_group_success(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)
        payload = {
            "nombre": "Elección de Guarnición",
            "descripcion": "Acompañamiento incluido para platos de fondo",
            "seleccion_minima": 1,
            "seleccion_maxima": 1,
            "permite_repetir": False,
            "items": [
                {
                    "producto_id": 104,
                    "nombre": "Papas Fritas",
                    "cantidad": "1.0000",
                    "es_opcion_default": True,
                    "recargo_precio": "0.00",
                    "orden": 1,
                },
                {
                    "producto_id": 105,
                    "nombre": "Arroz Blanco",
                    "cantidad": "1.0000",
                    "es_opcion_default": False,
                    "recargo_precio": "500.00",
                    "orden": 2,
                },
            ],
        }
        res = api_client.post("/api/v1/recipes/option-groups", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["id"] > 0
        assert data["nombre"] == "Elección de Guarnición"
        assert data["seleccion_minima"] == 1
        assert data["seleccion_maxima"] == 1
        assert len(data["items"]) == 2
        assert data["items"][0]["es_opcion_default"] is True

    def test_create_option_group_validation_required_without_default_fails(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)
        payload = {
            "nombre": "Salsa Obligatoria",
            "seleccion_minima": 1,
            "seleccion_maxima": 1,
            "items": [
                {
                    "producto_id": 107,
                    "es_opcion_default": False,  # No hay default en grupo obligatorio
                }
            ],
        }
        res = api_client.post("/api/v1/recipes/option-groups", json=payload, headers=headers)
        assert res.status_code == 422
        body = res.json()
        assert body["error_code"] == "RECIPE_INVALID_OPTION_SELECTION"
        assert "default" in body["detail"].lower()

    def test_create_option_group_polymorphic_xor_validation(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)
        # Caso 1: Sin target (ambos None)
        bad_payload_1 = {
            "nombre": "Grupo Inválido",
            "seleccion_minima": 0,
            "seleccion_maxima": 1,
            "items": [{"cantidad": "1.0000"}],
        }
        res1 = api_client.post("/api/v1/recipes/option-groups", json=bad_payload_1, headers=headers)
        assert res1.status_code == 422

        # Caso 2: Ambos seteados
        bad_payload_2 = {
            "nombre": "Grupo Inválido Ambos",
            "seleccion_minima": 0,
            "seleccion_maxima": 1,
            "items": [{"producto_id": 101, "receta_id": 1, "cantidad": "1.0000"}],
        }
        res2 = api_client.post("/api/v1/recipes/option-groups", json=bad_payload_2, headers=headers)
        assert res2.status_code == 422

    def test_option_group_crud_lifecycle(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # 1. Create
        create_res = api_client.post(
            "/api/v1/recipes/option-groups",
            json={
                "nombre": "Término de la Carne",
                "seleccion_minima": 1,
                "seleccion_maxima": 1,
                "items": [
                    {"producto_id": 101, "nombre": "A Punto", "es_opcion_default": True},
                    {"producto_id": 102, "nombre": "Bien Cocido", "es_opcion_default": False},
                ],
            },
            headers=headers,
        )
        gid = create_res.json()["id"]

        # 2. Get
        get_res = api_client.get(f"/api/v1/recipes/option-groups/{gid}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["nombre"] == "Término de la Carne"

        # 3. Update
        up_res = api_client.put(
            f"/api/v1/recipes/option-groups/{gid}",
            json={"nombre": "Punto de Cocción Actualizado"},
            headers=headers,
        )
        assert up_res.status_code == 200
        assert up_res.json()["nombre"] == "Punto de Cocción Actualizado"

        # 4. List
        list_res = api_client.get("/api/v1/recipes/option-groups", headers=headers)
        assert list_res.status_code == 200
        assert any(g["id"] == gid for g in list_res.json())

        # 5. Delete
        del_res = api_client.delete(f"/api/v1/recipes/option-groups/{gid}", headers=headers)
        assert del_res.status_code == 204

        # 6. Verify deleted (404)
        get_after = api_client.get(f"/api/v1/recipes/option-groups/{gid}", headers=headers)
        assert get_after.status_code == 404

    def test_delete_option_group_in_use_returns_409(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Crear grupo
        grp_res = api_client.post(
            "/api/v1/recipes/option-groups",
            json={
                "nombre": "Salsa Base",
                "seleccion_minima": 1,
                "seleccion_maxima": 1,
                "items": [{"producto_id": 107, "es_opcion_default": True}],
            },
            headers=headers,
        )
        gid = grp_res.json()["id"]

        # Crear receta que vincula este grupo
        rec_res = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-BURGER-01",
                "nombre": "Burger Dinámica",
                "precio_venta_neto": "8000.00",
                "ingredientes": [
                    {"producto_id": 101, "cantidad_receta": "150.0000", "porcentaje_merma": "0.00"}
                ],
                "grupos_opciones": [{"grupo_id": gid, "es_requerido": True}],
            },
            headers=headers,
        )
        assert rec_res.status_code == 201

        # Intentar borrar el grupo en uso -> 409 Conflict
        del_res = api_client.delete(f"/api/v1/recipes/option-groups/{gid}", headers=headers)
        assert del_res.status_code == 409
        assert del_res.json()["error_code"] == "OPTION_GROUP_IN_USE"


# ==============================================================================
# 2. CATEGORÍAS DE RECETAS Y COMBOS
# ==============================================================================


class TestCategoriesAPI:
    """Pruebas para categorías de recetas y combos."""

    def test_recipe_and_combo_categories_lifecycle(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Categoría Receta
        cat_rec = api_client.post(
            "/api/v1/recipes/categories",
            json={"nombre": "Carnes Rojas", "color": "#ef4444", "icono": "Beef", "orden": 1},
            headers=headers,
        )
        assert cat_rec.status_code == 201
        assert cat_rec.json()["nombre"] == "Carnes Rojas"

        list_cat_rec = api_client.get("/api/v1/recipes/categories", headers=headers)
        assert list_cat_rec.status_code == 200
        assert len(list_cat_rec.json()) >= 1

        # Categoría Combo
        cat_combo = api_client.post(
            "/api/v1/combos/categories",
            json={"nombre": "Almuerzos Ejecutivos", "color": "#10b981", "icono": "Utensils", "orden": 1},
            headers=headers,
        )
        assert cat_combo.status_code == 201
        assert cat_combo.json()["nombre"] == "Almuerzos Ejecutivos"

        list_cat_com = api_client.get("/api/v1/combos/categories", headers=headers)
        assert list_cat_com.status_code == 200
        assert len(list_cat_com.json()) >= 1


# ==============================================================================
# 3. CRUD DE RECETAS ESTÁTICAS Y DINÁMICAS CON ESCANDALLO BASE Y PEOR CASO
# ==============================================================================


class TestRecipesAPI:
    """Pruebas para /api/v1/recipes."""

    def test_create_static_recipe_with_calculated_escandallo_and_margins(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Insumo 101 (Lomo): 200g a $15.50/g = $3.100, Merma 5% -> Bruto 210g * 15.50 = $3.255,00
        # Insumo 102 (Cebolla): 50g a $3.20/g = $160, Merma 10% -> Bruto 55g * 3.20 = $176,00
        # Insumo 103 (Tomate): 80g a $4.10/g = $328, Merma 0% -> $328,00
        # Costo total lote = 3.255 + 176 + 328 = $3.759,00
        # Yield = 1.0000 porción -> Costo porción = $3.759,00
        # Precio neto = $12.000,00 -> IVA 19% = $14.280,00 bruto
        # Margen neto = 12.000 - 3.759 = $8.241,00
        # Margen % = 8.241 / 12.000 * 100 = 68.68%
        # Food Cost % = 3.759 / 12.000 * 100 = 31.33%

        payload = {
            "codigo": "REC-LOMO-SALTADO",
            "nombre": "Lomo Saltado Estándar",
            "descripcion": "Ficha técnica clásica de lomo saltado",
            "es_subreceta": False,
            "es_dinamica": False,
            "porciones_rendimiento": "1.0000",
            "precio_venta_neto": "12000.00",
            "iva_porcentaje": "19.00",
            "iva_incluido": True,
            "tiempo_preparacion_minutos": 15,
            "ingredientes": [
                {"producto_id": 101, "cantidad_receta": "200.0000", "porcentaje_merma": "5.00"},
                {"producto_id": 102, "cantidad_receta": "50.0000", "porcentaje_merma": "10.00"},
                {"producto_id": 103, "cantidad_receta": "80.0000", "porcentaje_merma": "0.00"},
            ],
            "grupos_opciones": [],
        }

        res = api_client.post("/api/v1/recipes", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        data = res.json()

        assert data["id"] > 0
        assert data["es_dinamica"] is False
        assert Decimal(str(data["costo_total_calculado"])) == Decimal("3759.00")
        assert Decimal(str(data["costo_porcion"])) == Decimal("3759.00")
        assert Decimal(str(data["precio_venta_neto"])) == Decimal("12000.00")
        assert Decimal(str(data["precio_venta_bruto"])) == Decimal("14280.00")
        assert Decimal(str(data["margen_neto"])) == Decimal("8241.00")
        assert Decimal(str(data["margen_pct"])) == Decimal("68.68")
        assert Decimal(str(data["food_cost_pct"])) == Decimal("31.33")
        assert len(data["ingredientes_fijos"]) == 3

    def test_create_dynamic_recipe_autodetection_and_worst_case_cost(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # 1. Crear grupo de opciones: Salsa (Default BBQ a $850, Alternativa Cheddar a $1.100)
        grp_res = api_client.post(
            "/api/v1/recipes/option-groups",
            json={
                "nombre": "Salsa de Acompañamiento",
                "seleccion_minima": 1,
                "seleccion_maxima": 1,
                "items": [
                    {"producto_id": 107, "nombre": "BBQ", "es_opcion_default": True},      # 850
                    {"producto_id": 108, "nombre": "Cheddar", "es_opcion_default": False},  # 1100 (peor caso)
                ],
            },
            headers=headers,
        )
        gid = grp_res.json()["id"]

        # 2. Crear receta con ingrediente fijo 101 ($15.50 * 100g = $1.550) y grupo de opciones
        # Base: $1.550 + default $850 = $2.400,00
        # Peor caso: $1.550 + peor $1.100 = $2.650,00
        rec_res = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-BURGER-DIN",
                "nombre": "Hamburguesa Dinámica",
                "precio_venta_neto": "9000.00",
                "ingredientes": [
                    {"producto_id": 101, "cantidad_receta": "100.0000", "porcentaje_merma": "0.00"}
                ],
                "grupos_opciones": [{"grupo_id": gid, "es_requerido": True}],
            },
            headers=headers,
        )
        assert rec_res.status_code == 201
        data = rec_res.json()

        assert data["es_dinamica"] is True  # Autodetección exitosa
        assert Decimal(str(data["costo_total_calculado"])) == Decimal("2400.00")
        assert Decimal(str(data["costo_porcion"])) == Decimal("2400.00")
        assert Decimal(str(data["costo_peor_caso"])) == Decimal("2650.00")
        assert Decimal(str(data["costo_mejor_caso"])) == Decimal("2400.00")

    def test_list_recipes_with_filters(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Crear subreceta
        api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-SUB-SALSA",
                "nombre": "Salsa Secreta Base",
                "es_subreceta": True,
                "ingredientes": [
                    {"producto_id": 102, "cantidad_receta": "10.0000"}
                ],
            },
            headers=headers,
        )

        # Crear receta estática
        api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-PLATO-FIJO",
                "nombre": "Plato Fijo Tradicional",
                "es_subreceta": False,
                "ingredientes": [
                    {"producto_id": 101, "cantidad_receta": "50.0000"}
                ],
            },
            headers=headers,
        )

        # Filtro por subrecetas
        sub_res = api_client.get("/api/v1/recipes?tipo=subrecetas", headers=headers)
        assert sub_res.status_code == 200
        assert all(r["es_subreceta"] for r in sub_res.json())

        # Filtro por estáticas
        est_res = api_client.get("/api/v1/recipes?tipo=estaticas", headers=headers)
        assert est_res.status_code == 200
        assert any(r["codigo"] == "REC-PLATO-FIJO" for r in est_res.json())

        # Búsqueda por texto
        q_res = api_client.get("/api/v1/recipes?search=Secreta", headers=headers)
        assert q_res.status_code == 200
        assert len(q_res.json()) == 1
        assert q_res.json()[0]["codigo"] == "REC-SUB-SALSA"

    def test_delete_recipe_in_use_as_subrecipe_returns_409(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # 1. Crear subreceta
        sub_res = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-SUB-CALDO",
                "nombre": "Caldo de Carne Concentrado",
                "es_subreceta": True,
                "ingredientes": [{"producto_id": 101, "cantidad_receta": "20.0000"}],
            },
            headers=headers,
        )
        sub_id = sub_res.json()["id"]

        # 2. Crear receta principal que utiliza la subreceta
        main_res = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-SOPA-CARNE",
                "nombre": "Sopa de Carne Criolla",
                "ingredientes": [
                    {"subreceta_id": sub_id, "cantidad_receta": "1.0000"}
                ],
            },
            headers=headers,
        )
        assert main_res.status_code == 201

        # 3. Intentar eliminar la subreceta -> 409 Conflict
        del_sub = api_client.delete(f"/api/v1/recipes/{sub_id}", headers=headers)
        assert del_sub.status_code == 409
        assert del_sub.json()["error_code"] == "RECIPE_IN_USE"


# ==============================================================================
# 4. PREVENCIÓN DE CICLOS EN SUBRECETAS VÍA API (DAG ANTI-RECURSIÓN)
# ==============================================================================


class TestRecipeCyclesAPI:
    """Pruebas para detección de ciclos anti-recursión cíclica en subrecetas."""

    def test_direct_self_cycle_prevented(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Crear receta inicial
        r1 = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-AUTO-1",
                "nombre": "Receta Auto Referencial",
                "ingredientes": [{"producto_id": 101, "cantidad_receta": "10.0000"}],
            },
            headers=headers,
        )
        r1_id = r1.json()["id"]

        # Intentar actualizarla referenciándose a sí misma (r1 -> r1)
        up_res = api_client.put(
            f"/api/v1/recipes/{r1_id}",
            json={
                "ingredientes": [{"subreceta_id": r1_id, "cantidad_receta": "1.0000"}]
            },
            headers=headers,
        )
        assert up_res.status_code == 422
        body = up_res.json()
        assert body["error_code"] == "RECIPE_CYCLE_DETECTED"
        assert "cycle detected" in body["detail"].lower()

    def test_indirect_cycle_prevented(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # 1. Receta A
        ra = api_client.post(
            "/api/v1/recipes",
            json={"codigo": "REC-DAG-A", "nombre": "Receta A", "ingredientes": [{"producto_id": 101, "cantidad_receta": "5.0"}]},
            headers=headers,
        )
        a_id = ra.json()["id"]

        # 2. Receta B que incluye A (B -> A)
        rb = api_client.post(
            "/api/v1/recipes",
            json={"codigo": "REC-DAG-B", "nombre": "Receta B", "ingredientes": [{"subreceta_id": a_id, "cantidad_receta": "1.0"}]},
            headers=headers,
        )
        b_id = rb.json()["id"]

        # 3. Intentar hacer que A incluya B (A -> B -> A) -> CICLO!
        cycle_res = api_client.put(
            f"/api/v1/recipes/{a_id}",
            json={"ingredientes": [{"subreceta_id": b_id, "cantidad_receta": "1.0"}]},
            headers=headers,
        )
        assert cycle_res.status_code == 422
        body = cycle_res.json()
        assert body["error_code"] == "RECIPE_CYCLE_DETECTED"
        assert f"{a_id} -> {b_id} -> {a_id}" in body["detail"]


# ==============================================================================
# 5. SIMULACIÓN DE COSTO DINÁMICO (POST /api/v1/recipes/{id}/simulate-cost)
# ==============================================================================


class TestRecipeCostSimulatorAPI:
    """Pruebas para simulación de costo en tiempo real ante selecciones dinámicas."""

    def test_simulate_cost_successful_calculation(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Grupo: Guarnición (Papas $2.500 / Arroz $1.200 con recargo $400)
        grp = api_client.post(
            "/api/v1/recipes/option-groups",
            json={
                "nombre": "Acompañamiento",
                "seleccion_minima": 1,
                "seleccion_maxima": 1,
                "items": [
                    {"producto_id": 104, "nombre": "Papas Fritas", "es_opcion_default": True, "recargo_precio": "0.00"},
                    {"producto_id": 105, "nombre": "Arroz con Recargo", "es_opcion_default": False, "recargo_precio": "400.00"},
                ],
            },
            headers=headers,
        )
        gid = grp.json()["id"]
        papas_item_id = grp.json()["items"][0]["id"]
        arroz_item_id = grp.json()["items"][1]["id"]

        # Receta: Base Lomo 100g ($1.550) + Precio Neto $10.000
        rec = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-SIM-01",
                "nombre": "Plato para Simular",
                "precio_venta_neto": "10000.00",
                "ingredientes": [{"producto_id": 101, "cantidad_receta": "100.0000"}],
                "grupos_opciones": [{"grupo_id": gid, "es_requerido": True}],
            },
            headers=headers,
        )
        rid = rec.json()["id"]

        # Simular seleccionando Arroz con recargo ($1.200 costo + $400 recargo precio)
        sim_res = api_client.post(
            f"/api/v1/recipes/{rid}/simulate-cost",
            json={"selected_option_item_ids": [arroz_item_id]},
            headers=headers,
        )
        assert sim_res.status_code == 200
        sim = sim_res.json()

        assert Decimal(str(sim["base_fixed_cost"])) == Decimal("1550.00")
        assert Decimal(str(sim["options_cost"])) == Decimal("1200.00")
        assert Decimal(str(sim["total_cost"])) == Decimal("2750.00")
        assert Decimal(str(sim["portion_cost"])) == Decimal("2750.00")
        assert Decimal(str(sim["total_surcharge"])) == Decimal("400.00")
        assert Decimal(str(sim["effective_net_price"])) == Decimal("10400.00")
        assert Decimal(str(sim["margin_amount"])) == Decimal("7650.00")
        assert len(sim["selected_options"]) == 1

    def test_simulate_cost_cardinality_violations(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        grp = api_client.post(
            "/api/v1/recipes/option-groups",
            json={
                "nombre": "Salsas (Min 1, Max 2)",
                "seleccion_minima": 1,
                "seleccion_maxima": 2,
                "permite_repetir": False,
                "items": [
                    {"producto_id": 107, "nombre": "BBQ", "es_opcion_default": True},
                    {"producto_id": 108, "nombre": "Cheddar", "es_opcion_default": False},
                ],
            },
            headers=headers,
        )
        gid = grp.json()["id"]
        bbq_id = grp.json()["items"][0]["id"]
        cheddar_id = grp.json()["items"][1]["id"]

        rec = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-SIM-VIOLATION",
                "nombre": "Plato Validaciones",
                "ingredientes": [{"producto_id": 101, "cantidad_receta": "100.0000"}],
                "grupos_opciones": [{"grupo_id": gid, "es_requerido": True}],
            },
            headers=headers,
        )
        rid = rec.json()["id"]

        # Violación 1: Min 1, pero se envía lista vacía
        res1 = api_client.post(
            f"/api/v1/recipes/{rid}/simulate-cost",
            json={"selected_option_item_ids": []},
            headers=headers,
        )
        assert res1.status_code == 422
        assert res1.json()["error_code"] == "RECIPE_INVALID_OPTION_SELECTION"

        # Violación 2: Repetir ítem cuando permite_repetir es False
        res2 = api_client.post(
            f"/api/v1/recipes/{rid}/simulate-cost",
            json={"selected_option_item_ids": [bbq_id, bbq_id]},
            headers=headers,
        )
        assert res2.status_code == 422
        assert "cannot be selected multiple times" in res2.json()["detail"].lower()

        # Violación 3: Ítem que no pertenece a ningún grupo de la receta
        res3 = api_client.post(
            f"/api/v1/recipes/{rid}/simulate-cost",
            json={"selected_option_item_ids": [9999]},
            headers=headers,
        )
        assert res3.status_code == 422
        assert "does not belong" in res3.json()["detail"].lower()


# ==============================================================================
# 6. CRUD DE COMBOS FIJOS Y DINÁMICOS CON DISPONIBILIDAD DE STOCK
# ==============================================================================


class TestCombosAPI:
    """Pruebas para /api/v1/combos."""

    def test_create_fixed_and_dynamic_combos(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # 1. Crear receta base para el combo
        rec = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-BURGER-BASE",
                "nombre": "Burger Cuarto de Libra",
                "ingredientes": [{"producto_id": 101, "cantidad_receta": "125.0000"}],
            },
            headers=headers,
        )
        rid = rec.json()["id"]

        # 2. Crear combo fijo: 1 Burger ($1.937,50) + 1 Bebida Lata 106 ($3.500,00)
        # Costo total combo = $5.437,50
        # Precio venta neto = $8.000,00 -> IVA 19% = $9.520,00
        # Margen = $8.000 - $5.437,50 = $2.562,50 (32.03%)
        combo_fijo_res = api_client.post(
            "/api/v1/combos",
            json={
                "codigo": "CMB-DUO-EXPRESS",
                "nombre": "Combo Dúo Express",
                "descripcion": "Burger clásica + bebida en lata",
                "precio_venta_neto": "8000.00",
                "items": [
                    {"receta_id": rid, "cantidad": "1.0000"},
                    {"producto_id": 106, "cantidad": "1.0000"},
                ],
            },
            headers=headers,
        )
        assert combo_fijo_res.status_code == 201
        data_fijo = combo_fijo_res.json()

        assert data_fijo["es_dinamico"] is False
        assert Decimal(str(data_fijo["costo_total_calculado"])) == Decimal("5437.50")
        assert Decimal(str(data_fijo["margen_amount"])) == Decimal("2562.50")
        assert Decimal(str(data_fijo["margen_pct"])) == Decimal("32.03")

        # 3. Crear grupo de opciones para combo
        grp = api_client.post(
            "/api/v1/recipes/option-groups",
            json={
                "nombre": "Papas o Aros",
                "seleccion_minima": 1,
                "seleccion_maxima": 1,
                "items": [
                    {"producto_id": 104, "nombre": "Papas Fritas", "es_opcion_default": True}
                ],
            },
            headers=headers,
        )
        gid = grp.json()["id"]

        # 4. Crear combo dinámico vinculando el grupo de opciones
        combo_din_res = api_client.post(
            "/api/v1/combos",
            json={
                "codigo": "CMB-TRIO-DINAMICO",
                "nombre": "Combo Trío Dinámico",
                "precio_venta_neto": "11000.00",
                "items": [{"receta_id": rid, "cantidad": "1.0000"}],
                "grupos_opciones": [{"grupo_id": gid, "es_requerido": True}],
            },
            headers=headers,
        )
        assert combo_din_res.status_code == 201
        assert combo_din_res.json()["es_dinamico"] is True

    def test_combo_stock_availability_calculation(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        # Inyectar saldo de inventario para producto 106 (Bebida) en ComboService
        combo_srv = get_combo_service()
        combo_srv.set_product_stock_balance(106, Decimal("15.0000"))  # 15 bebidas disponibles

        combo_res = api_client.post(
            "/api/v1/combos",
            json={
                "codigo": "CMB-PROMO-BEBIDAS",
                "nombre": "Pack 2 Bebidas",
                "precio_venta_neto": "5000.00",
                "items": [{"producto_id": 106, "cantidad": "2.0000"}],  # Exige 2 bebidas por combo
            },
            headers=headers,
        )
        cid = combo_res.json()["id"]

        # Consultar combo: 15 / 2 = 7 porciones teóricas
        get_res = api_client.get(f"/api/v1/combos/{cid}", headers=headers)
        assert get_res.status_code == 200
        combo_data = get_res.json()
        assert combo_data["disponibilidad_stock_porciones"] == 7
        assert combo_data["esta_disponible"] is True

    def test_combo_lifecycle_get_update_delete(self, api_client: TestClient) -> None:
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)

        create_res = api_client.post(
            "/api/v1/combos",
            json={
                "codigo": "CMB-TEMPORAL",
                "nombre": "Combo Temporal",
                "precio_venta_neto": "6000.00",
                "items": [{"producto_id": 106, "cantidad": "1.0000"}],
            },
            headers=headers,
        )
        cid = create_res.json()["id"]

        # Update
        up_res = api_client.put(
            f"/api/v1/combos/{cid}",
            json={"nombre": "Combo Actualizado"},
            headers=headers,
        )
        assert up_res.status_code == 200
        assert up_res.json()["nombre"] == "Combo Actualizado"

        # List
        list_res = api_client.get("/api/v1/combos", headers=headers)
        assert list_res.status_code == 200
        assert any(c["id"] == cid for c in list_res.json())

        # Delete
        del_res = api_client.delete(f"/api/v1/combos/{cid}", headers=headers)
        assert del_res.status_code == 204

        # Confirm 404
        get_after = api_client.get(f"/api/v1/combos/{cid}", headers=headers)
        assert get_after.status_code == 404


# ==============================================================================
# 7. GUARDIAS RBAC DE 3 NIVELES Y CONTRATOS RFC 7807
# ==============================================================================


class TestRBACGuardsAPI:
    """Verificación rigurosa de control de accesos RBAC y contratos de error RFC 7807."""

    def test_unauthenticated_request_fails(self, api_client: TestClient) -> None:
        res = api_client.get("/api/v1/recipes")
        assert res.status_code == 401

    def test_read_only_user_cannot_create_or_modify_recipe(self, api_client: TestClient) -> None:
        ro_headers = _build_headers(2, _RECIPES_READ_ONLY_GRANTS)

        # GET permitido
        get_res = api_client.get("/api/v1/recipes", headers=ro_headers)
        assert get_res.status_code == 200

        # POST denegado (requiere recipes.recipe.write)
        post_res = api_client.post(
            "/api/v1/recipes",
            json={"codigo": "REC-HACK", "nombre": "No Permitido"},
            headers=ro_headers,
        )
        assert post_res.status_code == 403
        body = post_res.json()
        assert body["status"] == 403
        assert body["error_code"] in ("RBAC_PERMISSION_DENIED", "MISSING_PERMISSION")
        assert "trace_id" in body

    def test_user_without_options_manage_cannot_create_option_group(self, api_client: TestClient) -> None:
        ro_headers = _build_headers(2, _RECIPES_READ_ONLY_GRANTS)
        res = api_client.post(
            "/api/v1/recipes/option-groups",
            json={"nombre": "Grupo No Permitido"},
            headers=ro_headers,
        )
        assert res.status_code == 403
        assert res.json()["error_code"] in ("RBAC_PERMISSION_DENIED", "MISSING_PERMISSION")

    def test_user_without_combo_write_cannot_create_combo(self, api_client: TestClient) -> None:
        ro_headers = _build_headers(2, _RECIPES_READ_ONLY_GRANTS)
        res = api_client.post(
            "/api/v1/combos",
            json={"nombre": "Combo No Permitido"},
            headers=ro_headers,
        )
        assert res.status_code == 403
        assert res.json()["error_code"] in ("RBAC_PERMISSION_DENIED", "MISSING_PERMISSION")


# ============================================================================
# 8. CATÁLOGO DE 14 ALÉRGENOS NORMADOS Y CONSOLIDACIÓN RECURSIVA (FASE 6)
# ============================================================================


class TestAllergensAndConsolidation:
    """Verificación de catálogo internacional de 14 alérgenos y consolidación en subrecetas."""

    def test_standard_14_allergens_catalog(self) -> None:
        """Verifica que el catálogo contenga exactamente los 14 alérgenos normados con i18n e íconos."""
        from src.modules.recipes.domain.allergens import (
            STANDARD_ALLERGENS,
            StandardAllergenCode,
            list_standard_allergens,
            normalize_allergen_code,
            resolve_allergen_definitions,
        )

        assert len(STANDARD_ALLERGENS) == 14
        expected_codes = {
            "GLUTEN", "CRUSTACEANS", "EGGS", "FISH", "PEANUTS",
            "SOYBEANS", "MILK", "NUTS", "CELERY", "MUSTARD",
            "SESAME", "SULPHITES", "LUPIN", "MOLLUSCS",
        }
        assert set(STANDARD_ALLERGENS.keys()) == expected_codes

        for code, allergen in STANDARD_ALLERGENS.items():
            assert allergen.code == code
            assert allergen.nombre and len(allergen.nombre) > 0
            assert allergen.nombre_en and len(allergen.nombre_en) > 0
            assert allergen.icono and len(allergen.icono) > 0
            assert allergen.descripcion and len(allergen.descripcion) > 0

        # Normalización bilingüe y alias
        assert normalize_allergen_code("gluten") == "GLUTEN"
        assert normalize_allergen_code("trigo") == "GLUTEN"
        assert normalize_allergen_code("wheat") == "GLUTEN"
        assert normalize_allergen_code("crustáceos") == "CRUSTACEANS"
        assert normalize_allergen_code("shrimp") == "CRUSTACEANS"
        assert normalize_allergen_code("leche") == "MILK"
        assert normalize_allergen_code("dairy") == "MILK"
        assert normalize_allergen_code("frutos secos") == "NUTS"
        assert normalize_allergen_code("non_existent_code") is None

    def test_recursive_allergen_consolidation_subrecipes_and_options(self) -> None:
        """
        Verifica que una receta padre consolide recursivamente los alérgenos de:
        - Sus propios insumos fijos
        - Sus subrecetas multinivel
        - Las opciones dinámicas de sus grupos de opciones
        """
        rec_srv = get_recipe_service()
        opt_srv = get_option_group_service()

        # Configurar insumos con alérgenos
        # 201: Harina de Trigo -> GLUTEN
        rec_srv.set_ingredient_cost(201, Decimal("1.20"), "Harina de Trigo", "gr", allergens=["GLUTEN"])
        # 202: Mantequilla -> MILK
        rec_srv.set_ingredient_cost(202, Decimal("3.50"), "Mantequilla", "gr", allergens=["MILK"])
        # 203: Huevo Fresco -> EGGS
        rec_srv.set_ingredient_cost(203, Decimal("250.00"), "Huevo Fresco", "und", allergens=["EGGS"])
        # 204: Salsa de Soja -> SOYBEANS
        rec_srv.set_ingredient_cost(204, Decimal("2.10"), "Salsa de Soja", "ml", allergens=["SOYBEANS"])
        # 205: Semillas de Sésamo -> SESAME
        rec_srv.set_ingredient_cost(205, Decimal("4.00"), "Semillas de Sésamo", "gr", allergens=["SESAME"])
        # 206: Camarones -> CRUSTACEANS
        rec_srv.set_ingredient_cost(206, Decimal("15.00"), "Camarones", "gr", allergens=["CRUSTACEANS"])

        # Subreceta 1: Masa Madre (Harina con GLUTEN)
        from src.modules.recipes.application.recipe_service import (
            RecipeIngredientDTO,
            RecipeOptionGroupLinkDTO,
        )

        sub1 = rec_srv.create_recipe(
            codigo="SUB-MASA",
            nombre="Masa Madre Base",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
            ingredientes=[
                RecipeIngredientDTO(producto_id=201, cantidad_receta=Decimal("200.0000")),
            ],
            tenant_id="tenant_test",
        )

        # Subreceta 2: Relleno Pastelero (Mantequilla con MILK + Huevo con EGGS)
        sub2 = rec_srv.create_recipe(
            codigo="SUB-RELLENO",
            nombre="Relleno Pastelero",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
            ingredientes=[
                RecipeIngredientDTO(producto_id=202, cantidad_receta=Decimal("50.0000")),
                RecipeIngredientDTO(producto_id=203, cantidad_receta=Decimal("2.0000")),
            ],
            tenant_id="tenant_test",
        )

        # Grupo de Opciones: Toppings Extras (Opción A: Sésamo SESAME, Opción B: Camarones CRUSTACEANS)
        from src.modules.recipes.application.option_group_service import OptionItemDTO

        grp = opt_srv.create_option_group(
            nombre="Toppings Extras",
            seleccion_minima=0,
            seleccion_maxima=2,
            items=[
                OptionItemDTO(
                    producto_id=205,
                    cantidad=Decimal("10.0000"),
                ),
                OptionItemDTO(
                    producto_id=206,
                    cantidad=Decimal("30.0000"),
                ),
            ],
            tenant_id="tenant_test",
        )

        # Receta Principal: Pastel Supremo
        principal = rec_srv.create_recipe(
            codigo="REC-SUPREMO",
            nombre="Pastel Gourmet Supremo",
            porciones_rendimiento=Decimal("2.0000"),
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=sub1.id, cantidad_receta=Decimal("1.0000")),
                RecipeIngredientDTO(subreceta_id=sub2.id, cantidad_receta=Decimal("1.0000")),
                RecipeIngredientDTO(producto_id=204, cantidad_receta=Decimal("15.0000")),
            ],
            grupos_opciones=[
                RecipeOptionGroupLinkDTO(grupo_id=grp.id, orden=1, es_requerido=False),
            ],
            tenant_id="tenant_test",
        )

        # Verificar consolidación
        allergens = rec_srv.get_recipe_allergens(principal.id, tenant_id="tenant_test")
        allergen_codes = [a.code for a in allergens]

        assert len(allergen_codes) == 6
        assert "GLUTEN" in allergen_codes
        assert "MILK" in allergen_codes
        assert "EGGS" in allergen_codes
        assert "SOYBEANS" in allergen_codes
        assert "SESAME" in allergen_codes
        assert "CRUSTACEANS" in allergen_codes


# ============================================================================
# 9. ASISTENTE DE ESCANDALLO: FICHA TÉCNICA DE COCINA Y ESCALAMIENTO (FASE 6)
# ============================================================================


class TestKitchenSheetAndScalingAPI:
    """Verificación de ficha técnica de cocina, escalamiento matemático exacto, merma y endpoints REST."""

    def test_kitchen_sheet_scaling_exact_math_and_waste(self) -> None:
        """
        Verifica el escalamiento matemático exacto de porciones (ej: 1 -> 50 porciones):
        - Porciones solicitadas: 50
        - Porciones base: 1 (factor = 50)
        - Insumo A: 100g neto base, 10% merma -> neto escalado: 5000g, bruto escalado: 5500g
        - Subreceta B: 1 porción base -> escalado: 50 porciones de subreceta
        - Merma calculada estrictamente en Decimal (cero floats).
        """
        rec_srv = get_recipe_service()
        from src.modules.recipes.application.recipe_service import RecipeIngredientDTO

        # Insumo A: 301 Carne Vacuno (10% merma)
        rec_srv.set_ingredient_cost(301, Decimal("20.00"), "Carne Vacuno", "gr", allergens=["GLUTEN"])
        # Insumo B: 302 Cebollas (20% merma)
        rec_srv.set_ingredient_cost(302, Decimal("5.00"), "Cebollas", "gr")

        # Subreceta: Fondo de Carne (50g carne con 10% merma)
        sub = rec_srv.create_recipe(
            codigo="SUB-FONDO",
            nombre="Caldo Concentrado",
            es_subreceta=True,
            porciones_rendimiento=Decimal("1.0000"),
            ingredientes=[
                RecipeIngredientDTO(
                    producto_id=301,
                    cantidad_receta=Decimal("50.0000"),
                    porcentaje_merma=Decimal("10.00"),
                ),
            ],
            tenant_id="tenant_test",
        )

        # Receta Principal: Asado de Vacuno (Rendimiento 1 porción)
        receta = rec_srv.create_recipe(
            codigo="REC-ASADO",
            nombre="Asado Tradicional",
            porciones_rendimiento=Decimal("1.0000"),
            preparacion="1. Sellar la carne. 2. Agregar caldo. 3. Hornear a 180°C durante 45 minutos.",
            tiempo_preparacion_minutos=45,
            ingredientes=[
                RecipeIngredientDTO(
                    producto_id=302,
                    cantidad_receta=Decimal("100.0000"),
                    porcentaje_merma=Decimal("20.00"),
                ),
                RecipeIngredientDTO(
                    subreceta_id=sub.id,
                    cantidad_receta=Decimal("1.0000"),
                    porcentaje_merma=Decimal("0.00"),
                ),
            ],
            tenant_id="tenant_test",
        )

        # Generar ficha técnica para 50 porciones
        sheet = rec_srv.generate_kitchen_sheet(
            recipe_id=receta.id,
            servings=Decimal("50.0000"),
            tenant_id="tenant_test",
        )

        assert sheet.porciones_base == Decimal("1.0000")
        assert sheet.porciones_solicitadas == Decimal("50.0000")
        assert sheet.factor_escalamiento == Decimal("50.0000")
        assert sheet.preparacion == receta.preparacion
        assert sheet.tiempo_preparacion_minutos == 45

        # Verificar cebollas
        cebolla_item = next(it for it in sheet.ingredientes_fijos if it.producto_id == 302)
        assert cebolla_item.cantidad_neta_base == Decimal("100.0000")
        # 100 * 50 = 5000.0000
        assert cebolla_item.cantidad_neta_escalada == Decimal("5000.0000")
        assert cebolla_item.porcentaje_merma == Decimal("20.00")
        # 5000 * (1 + 0.20) = 6000.0000
        assert cebolla_item.cantidad_bruta_escalada == Decimal("6000.0000")

        # Verificar subreceta caldo
        sub_item = next(it for it in sheet.ingredientes_fijos if it.subreceta_id == sub.id)
        assert sub_item.cantidad_neta_base == Decimal("1.0000")
        assert sub_item.cantidad_neta_escalada == Decimal("50.0000")
        assert sub_item.cantidad_bruta_escalada == Decimal("50.0000")
        assert len(sub_item.subreceta_desglose) == 1

        # Desglose interno de la subreceta para 50 porciones
        desglose_carne = sub_item.subreceta_desglose[0]
        assert desglose_carne.producto_id == 301
        assert desglose_carne.cantidad_neta_base == Decimal("50.0000")
        # 50 * 50 = 2500.0000
        assert desglose_carne.cantidad_neta_escalada == Decimal("2500.0000")
        # 2500 * (1 + 0.10) = 2750.0000
        assert desglose_carne.cantidad_bruta_escalada == Decimal("2750.0000")

    def test_kitchen_sheet_and_allergens_api_endpoints_200_and_rfc7807(self, api_client: TestClient) -> None:
        """
        Prueba completa de los endpoints REST:
        - GET /api/v1/recipes/{id}/allergens
        - GET /api/v1/recipes/{id}/kitchen-sheet?servings=10
        - GET /api/v1/recipes/{id} (incluye alergenos y allergens)
        - Manejo de RFC 7807 en 404 Not Found y 422 Invalid Servings.
        """
        headers = _build_headers(1, _RECIPES_FULL_GRANTS)
        rec_srv = get_recipe_service()

        # Configurar insumo con alérgenos
        rec_srv.set_ingredient_cost(401, Decimal("10.00"), "Queso Parmesano", "gr", allergens=["MILK"])
        rec_srv.set_ingredient_cost(402, Decimal("8.00"), "Pasta Seca", "gr", allergens=["GLUTEN"])

        # Crear receta vía API
        create_res = api_client.post(
            "/api/v1/recipes",
            json={
                "codigo": "REC-PASTA",
                "nombre": "Pasta al Parmesano",
                "porciones_rendimiento": "2.0000",
                "precio_venta_neto": "8500.00",
                "preparacion": "Hervir pasta durante 10 minutos y espolvorear parmesano.",
                "tiempo_preparacion_minutos": 15,
                "ingredientes": [
                    {"producto_id": 401, "cantidad_receta": "50.0000", "porcentaje_merma": "5.00"},
                    {"producto_id": 402, "cantidad_receta": "200.0000", "porcentaje_merma": "0.00"},
                ],
            },
            headers=headers,
        )
        assert create_res.status_code == 201
        recipe_id = create_res.json()["id"]

        # 1. GET /api/v1/recipes/{id} (Verificar que incluye alergenos y allergens)
        detail_res = api_client.get(f"/api/v1/recipes/{recipe_id}", headers=headers)
        assert detail_res.status_code == 200
        detail_body = detail_res.json()
        assert "alergenos" in detail_body
        assert "allergens" in detail_body
        codes = [a["code"] for a in detail_body["alergenos"]]
        assert "GLUTEN" in codes
        assert "MILK" in codes

        # 2. GET /api/v1/recipes/{id}/allergens
        allergens_res = api_client.get(f"/api/v1/recipes/{recipe_id}/allergens", headers=headers)
        assert allergens_res.status_code == 200
        allergens_body = allergens_res.json()
        assert isinstance(allergens_body, list)
        assert len(allergens_body) == 2
        for item in allergens_body:
            assert "code" in item
            assert "nombre" in item
            assert "icono" in item

        # 3. GET /api/v1/recipes/{id}/kitchen-sheet?servings=10
        sheet_res = api_client.get(f"/api/v1/recipes/{recipe_id}/kitchen-sheet?servings=10", headers=headers)
        assert sheet_res.status_code == 200
        sheet_body = sheet_res.json()
        assert sheet_body["recipe_id"] == recipe_id
        assert sheet_body["porciones_base"] == "2.0000"
        assert sheet_body["porciones_solicitadas"] == "10.0000"
        assert sheet_body["factor_escalamiento"] == "5.0000"
        assert len(sheet_body["ingredientes_fijos"]) == 2
        assert len(sheet_body["alergenos_consolidados"]) == 2

        # Insumo pasta: 200g base * 5 = 1000g netos, 0% merma -> 1000g brutos
        pasta_item = next(it for it in sheet_body["ingredientes_fijos"] if it["producto_id"] == 402)
        assert pasta_item["cantidad_neta_escalada"] == "1000.0000"
        assert pasta_item["cantidad_bruta_escalada"] == "1000.0000"

        # Insumo queso: 50g base * 5 = 250g netos, 5% merma -> 250 * 1.05 = 262.5g brutos
        queso_item = next(it for it in sheet_body["ingredientes_fijos"] if it["producto_id"] == 401)
        assert queso_item["cantidad_neta_escalada"] == "250.0000"
        assert queso_item["cantidad_bruta_escalada"] == "262.5000"

        # 4. Error 404 RFC 7807 cuando receta no existe
        not_found_res = api_client.get("/api/v1/recipes/99999/kitchen-sheet", headers=headers)
        assert not_found_res.status_code == 404
        problem_404 = not_found_res.json()
        assert problem_404["status"] == 404
        assert "title" in problem_404 or "detail" in problem_404

        not_found_allg = api_client.get("/api/v1/recipes/99999/allergens", headers=headers)
        assert not_found_allg.status_code == 404

        # 5. Error 422 RFC 7807 cuando servings <= 0
        invalid_servings = api_client.get(f"/api/v1/recipes/{recipe_id}/kitchen-sheet?servings=0", headers=headers)
        assert invalid_servings.status_code == 422

        invalid_negative = api_client.get(f"/api/v1/recipes/{recipe_id}/kitchen-sheet?servings=-4", headers=headers)
        assert invalid_negative.status_code == 422

