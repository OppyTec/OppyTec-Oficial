"""
Vector Red Team 13 (`tests/security_redteam/test_13_recipes_combos_offensive_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant, RBAC y Prevención de DoS en Recetas y Combos:
1. Control de acceso RBAC de 3 niveles:
   - recipes.recipe.read
   - recipes.recipe.write
   - recipes.recipe.delete
   - recipes.recipe.costs
   - recipes.combo.read
   - recipes.combo.write
   - recipes.combo.delete
   - recipes.options.manage
   Verificación de denegación 403 con RFC 7807 (ProblemDetails) ante usuarios sin permisos.
2. Prevención de IDOR Cross-Tenant:
   - Tenant Beta no puede leer, modificar, eliminar, simular costos ni generar fichas técnicas de recetas, combos ni grupos de opciones pertenecientes a Tenant Alpha.
   - Prevención de inyección de referencias cruzadas entre tenants (sub-recetas o grupos de opciones foráneos).
3. Prevención de Manipulación Financiera y Mass Assignment (`extra="forbid"`):
   - Rechazo 422 ante inyección de campos calculados (`costo_total_calculado`, `costo_porcion`, `margen_pct`).
   - Rechazo 422 ante cantidades negativas o nulas (`cantidad_receta <= 0`, `porciones <= 0`).
   - Rechazo 422 ante mermas anómalas (merma < 0 o merma >= 100%).
   - Rechazo 422 ante recargos de precios negativos o precios negativos.
4. Prevención de DoS por Recursión Infinita (DAG Cycle Detection):
   - Bloqueo 422 con RECIPE_CYCLE_DETECTED ante autorreferencias directas (A -> A), ciclos de 2 nodos (A -> B -> A), ciclos profundos (A -> B -> C -> A) y ciclos en actualizaciones.
   - Verificación de no-falso-positivo en grafos acíclicos válidos (patrón diamante).
5. Sanitización de PII y Sanitización XSS:
   - Enmascaramiento determinista [REDACTED_PII] de correos, RUT, teléfonos, tarjetas y tokens en fichas técnicas de cocina y atributos de spans OpenTelemetry.
   - Sanitización de scripts XSS en nombres y descripciones.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import pytest

from src.core.guards import (
    clear_revoked_sessions,
    get_rate_limiter,
)
from src.core.guards.rbac_dependencies import (
    revoke_session_token,
)
from src.core.observability import (
    REDACTED_MARKER,
    clear_in_memory_recipe_metrics,
    get_in_memory_exporter,
)
from src.core.security import create_access_token
from src.modules.recipes.presentation.router import (
    _combo_service,
    _legacy_escandallos_store,
    _option_group_service,
    _recipe_service,
    _simulator_service,
)

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_alpha_santiago"
TENANT_BETA = "tenant_beta_valparaiso"
HOLDING_ID = "holding_pollogold"

_ALL_RECIPES_PERMISSIONS = [
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


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    hierarchy_rank: int = 20,
    jti: str | None = None,
    contracted_modules: list[str] | None = None,
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    modules = contracted_modules if contracted_modules is not None else ["recipes"]
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        hierarchy_rank=hierarchy_rank,
        contracted_modules=modules,
        role_grants=permissions,
        accessible_tenants=[tenant_id],
        jti=jti,
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_test_environment() -> None:
    clear_revoked_sessions()
    get_rate_limiter().reset()
    _recipe_service.reset()
    _combo_service.reset()
    _option_group_service.reset()
    _legacy_escandallos_store.clear()
    get_in_memory_exporter().clear()
    clear_in_memory_recipe_metrics()

    # Catálogo de insumos base con costos PPP
    _recipe_service.set_ingredient_cost(101, Decimal("1500.00"), "Carne Molida", "kg")
    _recipe_service.set_ingredient_cost(102, Decimal("500.00"), "Cebolla", "kg")
    _recipe_service.set_ingredient_cost(103, Decimal("200.00"), "Masa de Empanada", "und")
    _recipe_service.set_ingredient_cost(104, Decimal("2500.00"), "Papas Fritas", "kg")
    _recipe_service.set_ingredient_cost(105, Decimal("1200.00"), "Arroz Graneado", "kg")
    _recipe_service.set_ingredient_cost(106, Decimal("300.00"), "Pan Brioche", "und", allergens=["GLUTEN"])
    _recipe_service.set_ingredient_cost(107, Decimal("800.00"), "Queso Cheddar", "porcion", allergens=["MILK"])


# ============================================================================
# VECTOR 1: CONTROL DE ACCESO RBAC DE 3 NIVELES Y CONTRATOS RFC 7807
# ============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_requests_blocked_with_401(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que cualquier petición no autenticada sea rechazada con HTTP 401."""
    res_rec = await async_client.get("/api/v1/recipes")
    assert res_rec.status_code == 401

    res_cmb = await async_client.get("/api/v1/combos")
    assert res_cmb.status_code == 401

    res_opt = await async_client.get("/api/v1/recipes/option-groups")
    assert res_opt.status_code == 401


@pytest.mark.asyncio
async def test_rbac_recipes_recipe_read_permission_enforced(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que usuarios sin 'recipes.recipe.read' reciban 403 RFC 7807 al consultar
    recetas, categorías, alérgenos o fichas técnicas.
    """
    token_unauth = _create_token(201, TENANT_ALPHA, ["inventory.counts.read"])
    headers = _make_headers(token_unauth, TENANT_ALPHA)

    # 1. GET /api/v1/recipes
    r1 = await async_client.get("/api/v1/recipes", headers=headers)
    assert r1.status_code == 403
    p1 = r1.json()
    assert p1["status"] == 403
    assert p1["title"] in ("Forbidden", "RBAC Permission Denied")
    assert p1["error_code"] in ("RBAC_PERMISSION_DENIED", "MISSING_PERMISSION")
    assert "trace_id" in p1

    # 2. GET /api/v1/recipes/{id}
    r2 = await async_client.get("/api/v1/recipes/1", headers=headers)
    assert r2.status_code == 403

    # 3. GET /api/v1/recipes/{id}/allergens
    r3 = await async_client.get("/api/v1/recipes/1/allergens", headers=headers)
    assert r3.status_code == 403

    # 4. GET /api/v1/recipes/{id}/kitchen-sheet
    r4 = await async_client.get("/api/v1/recipes/1/kitchen-sheet", headers=headers)
    assert r4.status_code == 403

    # 5. GET /api/v1/recipes/categories
    r5 = await async_client.get("/api/v1/recipes/categories", headers=headers)
    assert r5.status_code == 403


@pytest.mark.asyncio
async def test_rbac_recipes_recipe_write_permission_enforced(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que usuarios con sólo lectura ('recipes.recipe.read') NO puedan
    crear, modificar ni borrar categorías o recetas (requiere 'recipes.recipe.write').
    """
    token_ro = _create_token(202, TENANT_ALPHA, ["recipes.recipe.read"])
    headers = _make_headers(token_ro, TENANT_ALPHA)

    # POST /api/v1/recipes
    r1 = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-RBAC-01", "nombre": "Receta Bloqueada"},
        headers=headers,
    )
    assert r1.status_code == 403
    assert r1.json()["status"] == 403

    # PUT /api/v1/recipes/{id}
    r2 = await async_client.put(
        "/api/v1/recipes/1",
        json={"nombre": "Nuevo Nombre"},
        headers=headers,
    )
    assert r2.status_code == 403

    # POST /api/v1/recipes/categories
    r3 = await async_client.post(
        "/api/v1/recipes/categories",
        json={"nombre": "Postres"},
        headers=headers,
    )
    assert r3.status_code == 403


@pytest.mark.asyncio
async def test_rbac_recipes_recipe_delete_permission_enforced(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que usuarios con 'recipes.recipe.write' pero sin 'recipes.recipe.delete'
    no puedan eliminar recetas.
    """
    token_write = _create_token(
        203,
        TENANT_ALPHA,
        ["recipes.recipe.read", "recipes.recipe.write"],
    )
    headers = _make_headers(token_write, TENANT_ALPHA)

    # DELETE /api/v1/recipes/{id}
    r = await async_client.delete("/api/v1/recipes/1", headers=headers)
    assert r.status_code == 403
    body = r.json()
    assert body["status"] == 403
    assert body["error_code"] in ("RBAC_PERMISSION_DENIED", "MISSING_PERMISSION")


@pytest.mark.asyncio
async def test_rbac_recipes_recipe_costs_permission_enforced(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que usuarios sin 'recipes.recipe.costs' no puedan simular costos en vivo
    ni acceder a márgenes y costos confidenciales (403 RFC 7807).
    """
    # 1. Crear receta primero con usuario admin
    admin_token = _create_token(100, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    admin_hdr = _make_headers(admin_token, TENANT_ALPHA)
    rec_res = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-COST-01",
            "nombre": "Plato Costoso",
            "precio_venta_neto": "10000.00",
            "ingredientes": [{"producto_id": 101, "cantidad_receta": "1.0000"}],
        },
        headers=admin_hdr,
    )
    assert rec_res.status_code == 201
    recipe_id = rec_res.json()["id"]

    # 2. Usuario sin 'recipes.recipe.costs' intenta simular costos
    token_no_costs = _create_token(
        204,
        TENANT_ALPHA,
        ["recipes.recipe.read", "recipes.recipe.write"],
    )
    no_costs_hdr = _make_headers(token_no_costs, TENANT_ALPHA)
    sim_res = await async_client.post(
        f"/api/v1/recipes/{recipe_id}/simulate-cost",
        json={"selected_option_item_ids": []},
        headers=no_costs_hdr,
    )
    assert sim_res.status_code == 403
    assert sim_res.json()["error_code"] in ("RBAC_PERMISSION_DENIED", "MISSING_PERMISSION")

    # 3. Usuario CON 'recipes.recipe.costs' puede simular exitosamente
    token_with_costs = _create_token(
        205,
        TENANT_ALPHA,
        ["recipes.recipe.read", "recipes.recipe.costs"],
    )
    with_costs_hdr = _make_headers(token_with_costs, TENANT_ALPHA)
    sim_ok = await async_client.post(
        f"/api/v1/recipes/{recipe_id}/simulate-cost",
        json={"selected_option_item_ids": []},
        headers=with_costs_hdr,
    )
    assert sim_ok.status_code == 200
    assert "total_cost" in sim_ok.json()


@pytest.mark.asyncio
async def test_rbac_recipes_combo_permissions_enforced(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica segregación estricta en combos:
    - Sin 'recipes.combo.read' -> 403 en GET
    - Sin 'recipes.combo.write' -> 403 en POST/PUT
    - Sin 'recipes.combo.delete' -> 403 en DELETE
    """
    token_unauth = _create_token(206, TENANT_ALPHA, ["inventory.counts.read"])
    unauth_hdr = _make_headers(token_unauth, TENANT_ALPHA)

    # GET combo denegado
    r_get = await async_client.get("/api/v1/combos", headers=unauth_hdr)
    assert r_get.status_code == 403

    # Usuario con sólo lectura de combo
    token_read = _create_token(207, TENANT_ALPHA, ["recipes.combo.read"])
    read_hdr = _make_headers(token_read, TENANT_ALPHA)

    # POST combo denegado
    r_post = await async_client.post(
        "/api/v1/combos",
        json={"nombre": "Combo No Permitido"},
        headers=read_hdr,
    )
    assert r_post.status_code == 403

    # Usuario con combo.write pero sin combo.delete
    token_write = _create_token(
        208,
        TENANT_ALPHA,
        ["recipes.combo.read", "recipes.combo.write"],
    )
    write_hdr = _make_headers(token_write, TENANT_ALPHA)

    r_del = await async_client.delete("/api/v1/combos/1", headers=write_hdr)
    assert r_del.status_code == 403


@pytest.mark.asyncio
async def test_rbac_recipes_options_manage_permission_enforced(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la administración de la biblioteca de grupos de opciones requiera
    estrictamente 'recipes.options.manage' para todas las operaciones CRUD.
    """
    token_read = _create_token(209, TENANT_ALPHA, ["recipes.recipe.read", "recipes.combo.read"])
    read_hdr = _make_headers(token_read, TENANT_ALPHA)

    # GET option-groups denegado
    r1 = await async_client.get("/api/v1/recipes/option-groups", headers=read_hdr)
    assert r1.status_code == 403

    # POST option-groups denegado
    r2 = await async_client.post(
        "/api/v1/recipes/option-groups",
        json={"nombre": "Salsas Especiales"},
        headers=read_hdr,
    )
    assert r2.status_code == 403

    # PUT option-groups/{id} denegado
    r3 = await async_client.put(
        "/api/v1/recipes/option-groups/1",
        json={"nombre": "Nuevo Nombre"},
        headers=read_hdr,
    )
    assert r3.status_code == 403

    # DELETE option-groups/{id} denegado
    r4 = await async_client.delete("/api/v1/recipes/option-groups/1", headers=read_hdr)
    assert r4.status_code == 403


@pytest.mark.asyncio
async def test_token_revocation_killswitch_invalidates_recipes_access(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que la revocación activa de una sesión impida el acceso con 401 inmediato."""
    test_jti = "jwt-killswitch-test-recipes-001"
    token = _create_token(
        user_id=210,
        tenant_id=TENANT_ALPHA,
        permissions=_ALL_RECIPES_PERMISSIONS,
        jti=test_jti,
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # Petición exitosa antes de revocación
    r_ok = await async_client.get("/api/v1/recipes", headers=headers)
    assert r_ok.status_code == 200

    # Kill-switch revocación
    revoke_session_token(jti=test_jti)

    # Petición inmediatamente bloqueada con 401
    r_revoked = await async_client.get("/api/v1/recipes", headers=headers)
    assert r_revoked.status_code == 401


@pytest.mark.asyncio
async def test_rbac_level1_contracted_module_not_enabled_in_plan_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica el Nivel 1 de RBAC (Plan / Módulos Contratados):
    Si el tenant no tiene contratado el módulo 'recipes', cualquier endpoint
    es bloqueado con 403 y error_code 'MODULE_NOT_ENABLED_IN_PLAN'.
    """
    token_no_module = _create_token(
        user_id=211,
        tenant_id=TENANT_ALPHA,
        permissions=_ALL_RECIPES_PERMISSIONS,
        contracted_modules=["inventory"],  # Falla módulo recipes
    )
    headers = _make_headers(token_no_module, TENANT_ALPHA)

    res = await async_client.get("/api/v1/recipes", headers=headers)
    assert res.status_code == 403
    body = res.json()
    assert body["status"] == 403
    assert body["error_code"] == "MODULE_NOT_ENABLED_IN_PLAN"


# ============================================================================
# VECTOR 2: PREVENCIÓN DE IDOR CROSS-TENANT
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_recipe_read_modify_delete_simulation_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que Tenant Beta NO pueda leer, modificar, eliminar, simular costos
    ni generar fichas técnicas de una receta perteneciente a Tenant Alpha.
    """
    alpha_token = _create_token(101, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    alpha_hdr = _make_headers(alpha_token, TENANT_ALPHA)

    beta_token = _create_token(102, TENANT_BETA, _ALL_RECIPES_PERMISSIONS)
    beta_hdr = _make_headers(beta_token, TENANT_BETA)

    # 1. Tenant Alpha crea receta confidencial
    rec_res = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-ALPHA-SECRET",
            "nombre": "Fórmula Secreta Alpha",
            "precio_venta_neto": "12000.00",
            "preparacion": "Receta confidencial del Chef Alpha",
            "ingredientes": [{"producto_id": 101, "cantidad_receta": "0.5000"}],
        },
        headers=alpha_hdr,
    )
    assert rec_res.status_code == 201
    recipe_alpha_id = rec_res.json()["id"]

    # 2. Tenant Beta intenta IDOR GET /api/v1/recipes/{id} -> 404 (cero filtración)
    idor_get = await async_client.get(f"/api/v1/recipes/{recipe_alpha_id}", headers=beta_hdr)
    assert idor_get.status_code == 404
    assert idor_get.json()["error_code"] == "RECIPE_NOT_FOUND"

    # 3. Tenant Beta intenta IDOR PUT /api/v1/recipes/{id} -> 404
    idor_put = await async_client.put(
        f"/api/v1/recipes/{recipe_alpha_id}",
        json={"nombre": "Hackeado por Beta"},
        headers=beta_hdr,
    )
    assert idor_put.status_code == 404

    # 4. Tenant Beta intenta IDOR DELETE /api/v1/recipes/{id} -> 404
    idor_del = await async_client.delete(f"/api/v1/recipes/{recipe_alpha_id}", headers=beta_hdr)
    assert idor_del.status_code == 404

    # 5. Tenant Beta intenta simular costos de receta de Alpha -> 404
    idor_sim = await async_client.post(
        f"/api/v1/recipes/{recipe_alpha_id}/simulate-cost",
        json={"selected_option_item_ids": []},
        headers=beta_hdr,
    )
    assert idor_sim.status_code == 404

    # 6. Tenant Beta intenta generar ficha técnica de cocina de receta de Alpha -> 404
    idor_sheet = await async_client.get(
        f"/api/v1/recipes/{recipe_alpha_id}/kitchen-sheet",
        headers=beta_hdr,
    )
    assert idor_sheet.status_code == 404

    # 7. Tenant Beta intenta consultar alérgenos de receta de Alpha -> 404
    idor_all = await async_client.get(
        f"/api/v1/recipes/{recipe_alpha_id}/allergens",
        headers=beta_hdr,
    )
    assert idor_all.status_code == 404

    # 8. Verificar que la receta de Tenant Alpha sigue intacta
    alpha_check = await async_client.get(f"/api/v1/recipes/{recipe_alpha_id}", headers=alpha_hdr)
    assert alpha_check.status_code == 200
    assert alpha_check.json()["nombre"] == "Fórmula Secreta Alpha"


@pytest.mark.asyncio
async def test_cross_tenant_idor_combos_and_option_groups_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que Tenant Beta no pueda consultar, mutar ni eliminar combos
    o grupos de opciones creados por Tenant Alpha.
    """
    alpha_token = _create_token(101, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    alpha_hdr = _make_headers(alpha_token, TENANT_ALPHA)

    beta_token = _create_token(102, TENANT_BETA, _ALL_RECIPES_PERMISSIONS)
    beta_hdr = _make_headers(beta_token, TENANT_BETA)

    # 1. Tenant Alpha crea Option Group
    grp_res = await async_client.post(
        "/api/v1/recipes/option-groups",
        json={
            "nombre": "Salsas Alpha",
            "seleccion_minima": 1,
            "seleccion_maxima": 1,
            "items": [
                {"producto_id": 101, "nombre": "Salsa BBQ", "es_opcion_default": True},
            ],
        },
        headers=alpha_hdr,
    )
    assert grp_res.status_code == 201
    group_alpha_id = grp_res.json()["id"]

    # 2. Tenant Alpha crea Combo
    cmb_res = await async_client.post(
        "/api/v1/combos",
        json={
            "nombre": "Combo Almuerzo Alpha",
            "precio_venta_neto": "8000.00",
            "items": [{"producto_id": 104, "cantidad": "1.0000"}],
            "grupos_opciones": [{"grupo_id": group_alpha_id}],
        },
        headers=alpha_hdr,
    )
    assert cmb_res.status_code == 201
    combo_alpha_id = cmb_res.json()["id"]

    # 3. Tenant Beta intenta IDOR sobre Option Group de Alpha
    assert (await async_client.get(f"/api/v1/recipes/option-groups/{group_alpha_id}", headers=beta_hdr)).status_code == 404
    assert (await async_client.put(f"/api/v1/recipes/option-groups/{group_alpha_id}", json={"nombre": "Hack"}, headers=beta_hdr)).status_code == 404
    assert (await async_client.delete(f"/api/v1/recipes/option-groups/{group_alpha_id}", headers=beta_hdr)).status_code == 404

    # 4. Tenant Beta intenta IDOR sobre Combo de Alpha
    assert (await async_client.get(f"/api/v1/combos/{combo_alpha_id}", headers=beta_hdr)).status_code == 404
    assert (await async_client.put(f"/api/v1/combos/{combo_alpha_id}", json={"nombre": "Hack"}, headers=beta_hdr)).status_code == 404
    assert (await async_client.delete(f"/api/v1/combos/{combo_alpha_id}", headers=beta_hdr)).status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_reference_injection_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que Tenant Beta NO pueda inyectar sub-recetas ni grupos de opciones
    pertenecientes a Tenant Alpha al crear recetas o combos.
    """
    alpha_token = _create_token(101, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    alpha_hdr = _make_headers(alpha_token, TENANT_ALPHA)

    beta_token = _create_token(102, TENANT_BETA, _ALL_RECIPES_PERMISSIONS)
    beta_hdr = _make_headers(beta_token, TENANT_BETA)

    # 1. Tenant Alpha crea sub-receta y grupo de opciones
    alpha_sub = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "SUB-ALPHA-01", "nombre": "Salsa Base Alpha", "es_subreceta": True},
        headers=alpha_hdr,
    )
    alpha_sub_id = alpha_sub.json()["id"]

    alpha_grp = await async_client.post(
        "/api/v1/recipes/option-groups",
        json={
            "nombre": "Guarniciones Alpha",
            "seleccion_minima": 1,
            "seleccion_maxima": 1,
            "items": [{"producto_id": 105, "nombre": "Arroz Alpha", "es_opcion_default": True}],
        },
        headers=alpha_hdr,
    )
    alpha_grp_id = alpha_grp.json()["id"]

    # 2. Tenant Beta intenta crear receta referenciando sub-receta de Alpha -> 404
    inject_sub = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-BETA-PIRATE",
            "nombre": "Receta Pirata Beta",
            "ingredientes": [{"subreceta_id": alpha_sub_id, "cantidad_receta": "1.0000"}],
        },
        headers=beta_hdr,
    )
    assert inject_sub.status_code == 404
    assert inject_sub.json()["error_code"] == "RECIPE_NOT_FOUND"

    # 3. Tenant Beta intenta crear receta vinculando grupo de opciones de Alpha -> 404
    inject_grp = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-BETA-PIRATE-2",
            "nombre": "Receta Pirata Beta 2",
            "grupos_opciones": [{"grupo_id": alpha_grp_id}],
        },
        headers=beta_hdr,
    )
    assert inject_grp.status_code == 404
    assert inject_grp.json()["error_code"] == "OPTION_GROUP_NOT_FOUND"

    # 4. Tenant Beta intenta crear combo vinculando grupo de opciones de Alpha -> 404
    inject_combo_grp = await async_client.post(
        "/api/v1/combos",
        json={
            "nombre": "Combo Pirata Beta",
            "grupos_opciones": [{"grupo_id": alpha_grp_id}],
        },
        headers=beta_hdr,
    )
    assert inject_combo_grp.status_code == 404
    assert inject_combo_grp.json()["error_code"] == "OPTION_GROUP_NOT_FOUND"


# ============================================================================
# VECTOR 3: PREVENCIÓN DE MANIPULACIÓN FINANCIERA Y MASS ASSIGNMENT
# ============================================================================


@pytest.mark.asyncio
async def test_mass_assignment_extra_forbid_rejection(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que cualquier intento de inyectar costos calculados, Food Cost %
    o campos no autorizados sea rechazado con HTTP 422 (ConfigDict extra='forbid').
    """
    token = _create_token(301, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # Intento de inyectar 'costo_total_calculado' en receta
    r1 = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-HACK-01",
            "nombre": "Receta con Costo Falso",
            "costo_total_calculado": "0.01",  # Inyección maliciosa
        },
        headers=headers,
    )
    assert r1.status_code == 422
    assert "extra_forbidden" in str(r1.json()).lower()

    # Intento de inyectar 'margen_pct' en receta
    r2 = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-HACK-02",
            "nombre": "Receta Margen Inyectado",
            "margen_pct": "99.99",
        },
        headers=headers,
    )
    assert r2.status_code == 422

    # Intento de inyectar 'costo_total' en combo
    r3 = await async_client.post(
        "/api/v1/combos",
        json={
            "nombre": "Combo Hack",
            "costo_total_calculado": "1.00",
        },
        headers=headers,
    )
    assert r3.status_code == 422

    # Intento de inyectar 'is_deleted' en grupo de opciones
    r4 = await async_client.post(
        "/api/v1/recipes/option-groups",
        json={
            "nombre": "Grupo Hack",
            "is_deleted": True,
        },
        headers=headers,
    )
    assert r4.status_code == 422


@pytest.mark.asyncio
async def test_financial_manipulation_negative_and_zero_quantities_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que cantidades negativas o cero sean rechazadas deterministamente con 422.
    """
    token = _create_token(302, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # Cantidad de ingrediente negativa
    r1 = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-NEG-QTY",
            "nombre": "Receta Cantidad Negativa",
            "ingredientes": [{"producto_id": 101, "cantidad_receta": "-5.0000"}],
        },
        headers=headers,
    )
    assert r1.status_code == 422

    # Cantidad de ingrediente cero
    r2 = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-ZERO-QTY",
            "nombre": "Receta Cantidad Cero",
            "ingredientes": [{"producto_id": 101, "cantidad_receta": "0.0000"}],
        },
        headers=headers,
    )
    assert r2.status_code == 422

    # Porciones de rendimiento <= 0
    r3 = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-NEG-YIELD",
            "nombre": "Receta Porciones Negativas",
            "porciones_rendimiento": "-2.0000",
        },
        headers=headers,
    )
    assert r3.status_code == 422


@pytest.mark.asyncio
async def test_financial_manipulation_waste_percentage_and_surcharges_invariants(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que mermas >= 100% o < 0%, y recargos de precio negativos sean rechazados con 422.
    """
    token = _create_token(303, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # Merma >= 100% (100% de merma implica división por cero o cantidad nula inutilizable)
    r_merma_100 = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-MERMA-100",
            "nombre": "Receta Merma 100",
            "ingredientes": [
                {"producto_id": 101, "cantidad_receta": "1.0000", "porcentaje_merma": "100.00"},
            ],
        },
        headers=headers,
    )
    assert r_merma_100.status_code == 422

    # Merma negativa
    r_merma_neg = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-MERMA-NEG",
            "nombre": "Receta Merma Negativa",
            "ingredientes": [
                {"producto_id": 101, "cantidad_receta": "1.0000", "porcentaje_merma": "-10.00"},
            ],
        },
        headers=headers,
    )
    assert r_merma_neg.status_code == 422

    # Recargo de precio negativo en grupo de opciones
    r_recargo_neg = await async_client.post(
        "/api/v1/recipes/option-groups",
        json={
            "nombre": "Grupo Recargo Negativo",
            "items": [
                {
                    "producto_id": 101,
                    "nombre": "Opcion Descuento Ilegal",
                    "es_opcion_default": True,
                    "recargo_precio": "-500.00",
                }
            ],
        },
        headers=headers,
    )
    assert r_recargo_neg.status_code == 422

    # Precios de venta negativos
    r_precio_neg = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-PRECIO-NEG",
            "nombre": "Receta Precio Negativo",
            "precio_venta_neto": "-1000.00",
        },
        headers=headers,
    )
    assert r_precio_neg.status_code == 422


# ============================================================================
# VECTOR 4: PREVENCIÓN DE DoS POR RECURSIÓN INFINITA (DAG CYCLE DETECTION)
# ============================================================================


@pytest.mark.asyncio
async def test_cycle_detector_blocks_self_referential_cycle(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que una receta no pueda referenciarse a sí misma como sub-receta (A -> A)."""
    token = _create_token(401, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Crear Receta A
    res_a = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-CYCLE-SELF", "nombre": "Receta Narciso", "es_subreceta": True},
        headers=headers,
    )
    assert res_a.status_code == 201
    aid = res_a.json()["id"]

    # 2. Intentar actualizar Receta A para incluirse a sí misma como subreceta
    res_cycle = await async_client.put(
        f"/api/v1/recipes/{aid}",
        json={"ingredientes": [{"subreceta_id": aid, "cantidad_receta": "1.0000"}]},
        headers=headers,
    )
    assert res_cycle.status_code == 422
    body = res_cycle.json()
    assert body["error_code"] == "RECIPE_CYCLE_DETECTED"
    assert f"{aid} -> {aid}" in body["detail"]


@pytest.mark.asyncio
async def test_cycle_detector_blocks_indirect_cycle_2_nodes(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que un ciclo circular entre 2 recetas (A -> B -> A) sea bloqueado con 422."""
    token = _create_token(402, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Crear Receta A
    ra = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-CYC-2A", "nombre": "Receta A", "es_subreceta": True},
        headers=headers,
    )
    assert ra.status_code == 201
    aid = ra.json()["id"]

    # 2. Crear Receta B que contiene A
    rb = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-CYC-2B",
            "nombre": "Receta B",
            "es_subreceta": True,
            "ingredientes": [{"subreceta_id": aid, "cantidad_receta": "1.0000"}],
        },
        headers=headers,
    )
    assert rb.status_code == 201
    bid = rb.json()["id"]

    # 3. Intentar mutar A para contener B (creando A -> B -> A)
    res_cycle = await async_client.put(
        f"/api/v1/recipes/{aid}",
        json={"ingredientes": [{"subreceta_id": bid, "cantidad_receta": "1.0000"}]},
        headers=headers,
    )
    assert res_cycle.status_code == 422
    body = res_cycle.json()
    assert body["error_code"] == "RECIPE_CYCLE_DETECTED"
    assert f"{aid} -> {bid} -> {aid}" in body["detail"]


@pytest.mark.asyncio
async def test_cycle_detector_blocks_deep_cycle_3_nodes(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que un ciclo profundo de 3 saltos (A -> B -> C -> A) sea bloqueado."""
    token = _create_token(403, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Crear A
    ra = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-CYC-3A", "nombre": "Receta 3A", "es_subreceta": True},
        headers=headers,
    )
    aid = ra.json()["id"]

    # 2. Crear B conteniendo A
    rb = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-CYC-3B",
            "nombre": "Receta 3B",
            "es_subreceta": True,
            "ingredientes": [{"subreceta_id": aid, "cantidad_receta": "1.0000"}],
        },
        headers=headers,
    )
    bid = rb.json()["id"]

    # 3. Crear C conteniendo B
    rc = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-CYC-3C",
            "nombre": "Receta 3C",
            "es_subreceta": True,
            "ingredientes": [{"subreceta_id": bid, "cantidad_receta": "1.0000"}],
        },
        headers=headers,
    )
    cid = rc.json()["id"]

    # 4. Actualizar A conteniendo C (A -> C -> B -> A)
    res_cycle = await async_client.put(
        f"/api/v1/recipes/{aid}",
        json={"ingredientes": [{"subreceta_id": cid, "cantidad_receta": "1.0000"}]},
        headers=headers,
    )
    assert res_cycle.status_code == 422
    assert res_cycle.json()["error_code"] == "RECIPE_CYCLE_DETECTED"


@pytest.mark.asyncio
async def test_cycle_detector_allows_valid_diamond_dag(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que grafos acíclicos con ramificación diamante (A -> B, A -> C, B -> D, C -> D)
    sean permitidos sin falsos positivos.
    """
    token = _create_token(404, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # D: Base común (ej. Caldo base)
    rd = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-DAG-D", "nombre": "Caldo Base D", "es_subreceta": True},
        headers=headers,
    )
    did = rd.json()["id"]

    # B y C usan D
    rb = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-DAG-B",
            "nombre": "Salsa B",
            "es_subreceta": True,
            "ingredientes": [{"subreceta_id": did, "cantidad_receta": "1.0000"}],
        },
        headers=headers,
    )
    bid = rb.json()["id"]

    rc = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-DAG-C",
            "nombre": "Salsa C",
            "es_subreceta": True,
            "ingredientes": [{"subreceta_id": did, "cantidad_receta": "1.0000"}],
        },
        headers=headers,
    )
    cid = rc.json()["id"]

    # A usa B y C (patrón diamante acíclico)
    ra = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-DAG-A",
            "nombre": "Plato Final Diamante A",
            "ingredientes": [
                {"subreceta_id": bid, "cantidad_receta": "1.0000"},
                {"subreceta_id": cid, "cantidad_receta": "1.0000"},
            ],
        },
        headers=headers,
    )
    assert ra.status_code == 201
    assert ra.json()["id"] is not None


# ============================================================================
# VECTOR 5: SANITIZACIÓN PII EN FICHAS TÉCNICAS Y SPANS OPENTELEMETRY
# ============================================================================


@pytest.mark.asyncio
async def test_pii_sanitization_in_kitchen_sheet_and_allergens(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que correos electrónicos, RUT chileno, teléfonos, números de tarjetas de crédito
    y tokens Bearer sean redactados ([REDACTED_PII]) en la ficha técnica de cocina.
    """
    token = _create_token(501, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # Crear receta con información confidencial/PII en campos de texto libre
    create_res = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-PII-01",
            "nombre": "Lasaña Chef Especial",
            "descripcion": "Contacto chef: chef.juan@oppytec.cl con RUT 12.345.678-9.",
            "preparacion": "Llamar al +56 9 8765 4321 si hay dudas. Tarjeta pago insumos: 4532 1234 5678 9012.",
            "ingredientes": [
                {
                    "producto_id": 101,
                    "cantidad_receta": "0.5000",
                    "notas": "Proveedor secreto Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    rid = create_res.json()["id"]

    # Solicitar ficha técnica de cocina
    sheet_res = await async_client.get(f"/api/v1/recipes/{rid}/kitchen-sheet", headers=headers)
    assert sheet_res.status_code == 200
    sheet = sheet_res.json()

    # Validar redacción determinista en descripción
    assert "chef.juan@oppytec.cl" not in sheet["descripcion"]
    assert "12.345.678-9" not in sheet["descripcion"]
    assert REDACTED_MARKER in sheet["descripcion"]

    # Validar redacción determinista en instrucciones de preparación
    assert "+56 9 8765 4321" not in sheet["preparacion"]
    assert "4532 1234 5678 9012" not in sheet["preparacion"]
    assert REDACTED_MARKER in sheet["preparacion"]

    # Validar redacción determinista en notas de ingredientes
    ing_notas = sheet["ingredientes_fijos"][0]["notas"]
    assert "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token" not in ing_notas
    assert REDACTED_MARKER in ing_notas


@pytest.mark.asyncio
async def test_pii_sanitization_in_opentelemetry_spans(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que los atributos de trazas y spans de OpenTelemetry nunca contengan
    PII en texto plano, redáctandola automáticamente en 'notes_scrubbed'.
    """
    exporter = get_in_memory_exporter()
    exporter.clear()

    token = _create_token(502, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # Crear receta con PII
    create_res = await async_client.post(
        "/api/v1/recipes",
        json={
            "codigo": "REC-SPAN-PII",
            "nombre": "Plato con Spans",
            "descripcion": "Email secreto: supervisor@restaurante.com",
            "ingredientes": [
                {
                    "producto_id": 102,
                    "cantidad_receta": "0.3000",
                    "notas": "Teléfono de urgencia: +56 9 1122 3344",
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    rid = create_res.json()["id"]

    # Generar ficha técnica
    await async_client.get(f"/api/v1/recipes/{rid}/kitchen-sheet", headers=headers)

    # Inspeccionar spans finalizados
    spans = exporter.get_finished_spans()
    kitchen_spans = [s for s in spans if s.name == "recipe.kitchen_sheet.generate"]
    assert len(kitchen_spans) >= 1

    for sp in kitchen_spans:
        notes_attr = sp.attributes.get("notes_scrubbed", "")
        assert "supervisor@restaurante.com" not in notes_attr
        assert "+56 9 1122 3344" not in notes_attr
        assert REDACTED_MARKER in notes_attr


@pytest.mark.asyncio
async def test_xss_ssti_sqli_polyglot_attacks_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que inyecciones de payloads XSS, SSTI y SQLi en nombres o descripciones
    sean neutralizadas y bloqueadas deterministamente con HTTP 422.
    """
    token = _create_token(503, TENANT_ALPHA, _ALL_RECIPES_PERMISSIONS)
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Vector XSS
    xss_payload = "<script>alert('XSS_ATTACK')</script>Burger Supremo"
    res_xss = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-XSS-01", "nombre": xss_payload},
        headers=headers,
    )
    assert res_xss.status_code == 422
    assert res_xss.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"

    # 2. Vector SSTI
    ssti_payload = "Receta {{ 7*7 }}"
    res_ssti = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-SSTI-01", "nombre": ssti_payload},
        headers=headers,
    )
    assert res_ssti.status_code == 422
    assert res_ssti.json()["error_code"] == "SSTI_PAYLOAD_BLOCKED"

    # 3. Vector SQLi
    sqli_payload = "Receta '; DROP TABLE recipes; --"
    res_sqli = await async_client.post(
        "/api/v1/recipes",
        json={"codigo": "REC-SQLI-01", "nombre": sqli_payload},
        headers=headers,
    )
    assert res_sqli.status_code == 422
    assert res_sqli.json()["error_code"] == "SQLI_PAYLOAD_BLOCKED"
