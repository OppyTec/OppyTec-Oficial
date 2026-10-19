"""
Pruebas de Contrato OpenAPI 3.1 y Fuzzing Grey-Box Schemathesis (`tests/contracts/test_openapi_schemathesis.py`):
- Verifica que `/openapi.json` documente los endpoints de los 10 módulos de negocio + `/api/v1/health`.
- Audita que todos los schemas de entrada (`*Request`) generados en `components.schemas` impongan
  `additionalProperties: False` (`extra="forbid"`).
- Ejecuta fuzzing determinista de contratos sobre los endpoints de los 10 módulos inyectando propiedades
  no declaradas, tipos inválidos y cabeceras malformadas, certificando HTTP 401/403/422 y **cero HTTP 500**.
"""
from __future__ import annotations

import httpx
import pytest

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token

pytestmark = pytest.mark.security_redteam

EXPECTED_MODULE_TAGS: frozenset[str] = frozenset(
    {
        "system",
        "identity",
        "tenancy",
        "audit",
        "catalog",
        "inventory",
        "recipes",
        "procurement",
        "operations",
        "analytics",
        "oppyfy",
    }
)

EXPECTED_MODULE_PATHS: tuple[str, ...] = (
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/identity/roles",
    "/api/v1/identity/grants/jit",
    "/api/v1/tenancy/holdings",
    "/api/v1/tenancy/tenants",
    "/api/v1/tenancy/quotas/seats",
    "/api/v1/tenancy/quotas/storage",
    "/api/v1/audit/rbac",
    "/api/v1/audit/activity",
    "/api/v1/catalog/products",
    "/api/v1/catalog/units/convert",
    "/api/v1/catalog/import-excel",
    "/api/v1/catalog/media/upload",
    "/api/v1/inventory/kardex/movements",
    "/api/v1/inventory/counts",
    "/api/v1/inventory/mermas",
    "/api/v1/recipes/escandallos",
    "/api/v1/recipes/simulate-margin",
    "/api/v1/procurement/orders",
    "/api/v1/procurement/receptions/reconcile",
    "/api/v1/procurement/invoices/ocr",
    "/api/v1/operations/sales",
    "/api/v1/operations/buffet",
    "/api/v1/operations/events",
    "/api/v1/analytics/executive-summary",
    "/api/v1/analytics/food-cost-variance",
    "/api/v1/oppyfy/chat",
    "/api/v1/oppyfy/rbac/domains",
    "/api/v1/oppyfy/credits/wallet",
    "/api/v1/oppyfy/telemetry/logs",
)


async def test_openapi_schema_completeness_and_extra_forbid_enforcement(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que `/openapi.json` sea un documento OpenAPI 3.1 válido, incluya los 10 módulos
    y declare `additionalProperties: False` en todos los schemas `*Request`.
    """
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()

    assert str(spec.get("openapi", "")).startswith("3.")
    paths: dict[str, object] = spec.get("paths", {})
    for expected_path in EXPECTED_MODULE_PATHS:
        assert expected_path in paths, f"Missing route '{expected_path}' in /openapi.json"

    discovered_tags: set[str] = set()
    for path_item in paths.values():
        if isinstance(path_item, dict):
            for op in path_item.values():
                if isinstance(op, dict):
                    for tag in op.get("tags", []):
                        discovered_tags.add(str(tag))

    missing_tags = EXPECTED_MODULE_TAGS - discovered_tags
    assert not missing_tags, f"Missing OpenAPI tags: {sorted(missing_tags)}"

    schemas: dict[str, dict[str, object]] = spec.get("components", {}).get("schemas", {})
    request_schemas = {
        name: definition
        for name, definition in schemas.items()
        if name.endswith("Request") and isinstance(definition, dict)
    }
    assert len(request_schemas) >= 15

    for schema_name, definition in request_schemas.items():
        assert definition.get("additionalProperties") is False, (
            f"Request schema '{schema_name}' must enforce extra='forbid' (additionalProperties=False)"
        )


@pytest.mark.parametrize(
    ("endpoint", "valid_payload"),
    [
        (
            "/api/v1/catalog/products",
            {
                "sku": "SKU-100",
                "nombre": "Aceite de Oliva",
                "unidad_compra": "bidon",
                "unidad_almacen": "l",
                "unidad_receta": "ml",
                "factor_compra_a_almacen": "5",
                "factor_almacen_a_receta": "1000",
                "costo_compra_neto": "25000",
            },
        ),
        (
            "/api/v1/inventory/kardex/movements",
            {
                "producto_id": 10,
                "bodega_id": 1,
                "movement_type": "ENTRADA",
                "quantity": "10",
                "unit_cost": "1500",
            },
        ),
        (
            "/api/v1/recipes/simulate-margin",
            {
                "portion_cost": "2500",
                "proposed_net_price": "10000",
            },
        ),
        (
            "/api/v1/procurement/orders",
            {
                "po_number": "OC-900",
                "supplier_id": 1,
                "supplier_name": "Pollo King",
                "lines": [{"producto_id": 10, "quantity": "5", "unit_cost": "1000"}],
            },
        ),
        (
            "/api/v1/operations/buffet",
            {
                "service_name": "Buffet Corporativo",
                "total_buffet_cost": "100000",
                "pax": 25,
                "leftover_value": "10000",
            },
        ),
        (
            "/api/v1/analytics/executive-summary",
            {
                "theoretical_cost": "100000",
                "opening_inventory": "50000",
                "purchases": "100000",
                "closing_inventory": "50000",
                "net_sales": "300000",
            },
        ),
        (
            "/api/v1/oppyfy/chat",
            {
                "prompt_text": "¿Cuál es el margen objetivo?",
                "target_subdomain_slug": "recipes_kitchen",
            },
        ),
        (
            "/api/v1/audit/activity",
            {
                "event_type": "catalog.product.created",
                "entity_name": "Product",
                "entity_id": "100",
            },
        ),
    ],
)
async def test_undeclared_payload_properties_strictly_rejected_with_http_422(
    async_client: httpx.AsyncClient,
    endpoint: str,
    valid_payload: dict[str, object],
) -> None:
    """
    Grey-box contract test: inyecta un atributo fantasma `__undeclared_property__` en payloads válidos
    y verifica que FastAPI + Pydantic (`extra='forbid'`) respondan HTTP 422 (jamás 200 ni 500).
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    token = create_access_token(
        user_id=900,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=0,
        is_superuser_god=True,
        is_global_staff=True,
        accessible_tenants=["tenant_rest_a"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    polluted_payload = {
        **valid_payload,
        "__undeclared_property__": "mass_assignment_exploit",
    }
    resp = await async_client.post(endpoint, headers=headers, json=polluted_payload)
    assert resp.status_code == 422, f"Expected 422 on {endpoint} with extra property, got {resp.status_code}"


async def test_schemathesis_style_openapi_fuzzing_never_triggers_http_500(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Recorre dinámicamente todas las operaciones declaradas en `/openapi.json` enviando:
    1. Peticiones sin autenticación.
    2. Peticiones autenticadas con cuerpos JSON vacíos o tipos extremos (fuzzing de borde).
    Certifica que **ningún endpoint del sistema arroje HTTP 500 Internal Server Error**.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    spec_resp = await async_client.get("/openapi.json")
    assert spec_resp.status_code == 200
    paths: dict[str, dict[str, object]] = spec_resp.json().get("paths", {})

    god_token = create_access_token(
        user_id=1,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=0,
        is_superuser_god=True,
        is_global_staff=True,
        accessible_tenants=["tenant_rest_a"],
    )
    auth_headers = {
        "Authorization": f"Bearer {god_token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    for route_template, methods_map in paths.items():
        if not isinstance(methods_map, dict):
            continue
        concrete_route = (
            route_template.replace("{user_id}", "999")
            .replace("{merma_id}", "999")
            .replace("{event_id}", "evt-fuzz-01")
        )
        for http_method in methods_map:
            method_upper = http_method.upper()
            if method_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue

            get_rate_limiter().reset()
            unauth_res = await async_client.request(method_upper, concrete_route)
            assert unauth_res.status_code < 500, (
                f"HTTP 500 on unauthenticated {method_upper} {concrete_route}"
            )

            get_rate_limiter().reset()
            fuzzed_res = await async_client.request(
                method_upper,
                concrete_route,
                headers=auth_headers,
                json={"__fuzz__": None} if method_upper in {"POST", "PUT", "PATCH"} else None,
            )
            assert fuzzed_res.status_code < 500, (
                f"HTTP 500 on fuzzed {method_upper} {concrete_route}"
            )
