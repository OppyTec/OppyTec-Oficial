"""
oppytec-backend/tests/api/test_import_excel.py
Pruebas para el importador inteligente de planillas Excel:
- POST /api/v1/catalog/import/analyze-excel:
  * Inferencia heurística de columnas canónicas (nombre, sku, costo, etc.)
  * Detección de marcas y categorías nuevas vs existentes
  * Sanitización de fórmulas contra CWE-1236 (ej: '=SUM(...)', '@COMMAND', '+cmd')
- POST /api/v1/catalog/import/batch-create:
  * Creación exitosa en lote con entidades sugeridas
  * Límite estricto anti-DoS de 1.500 productos (falla con 400 si > 1500)
  * Inicialización de stock en Kardex para la bodega asignada
"""
from __future__ import annotations

import httpx
import pytest

from src.core.security import create_access_token

pytestmark = pytest.mark.unit

TENANT_ID = "tenant_excel_import_test"


def _headers(permissions: list[str]) -> dict[str, str]:
    token = create_access_token(
        user_id=202,
        tenant_id=TENANT_ID,
        holding_id="holding_excel",
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.mark.asyncio
async def test_analyze_excel_column_inference_and_entity_detection(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica la inferencia de columnas y la detección de categorías/marcas nuevas vs existentes."""
    headers = _headers(["catalog.import.analyze"])

    # 'Lácteos y Quesos' y 'Colun' ya existen por defecto en los stores
    payload = {
        "sheet_name": "Insumos 2026",
        "raw_headers": ["Producto", "Codigo SKU", "Rubro Categoria", "Marca Fabricante", "Costo Neto", "Stock Inicial"],
        "rows_data": [
            {
                "Producto": "Queso Gouda Laminado",
                "Codigo SKU": "Q-GOU-01",
                "Rubro Categoria": "Lácteos y Quesos",  # Existente
                "Marca Fabricante": "Colun",            # Existente
                "Costo Neto": "3500.00",
                "Stock Inicial": "20",
            },
            {
                "Producto": "Vino Cabernet Sauvignon",
                "Codigo SKU": "VIN-CAB-01",
                "Rubro Categoria": "Vinos y Licores",    # Nueva
                "Marca Fabricante": "Viña Concha y Toro",# Nueva
                "Costo Neto": "4500.00",
                "Stock Inicial": "15",
            },
        ],
    }

    resp = await async_client.post(
        "/api/v1/catalog/import/analyze-excel",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    # 1. Inferencia de columnas
    detected = data["detected_columns"]
    assert detected.get("Producto") == "nombre"
    assert detected.get("Codigo SKU") == "sku"
    assert detected.get("Rubro Categoria") == "categoria"
    assert detected.get("Marca Fabricante") == "marca"
    assert detected.get("Costo Neto") == "costo_neto"
    assert detected.get("Stock Inicial") == "stock_inicial"

    # 2. Detección de entidades nuevas vs existentes
    assert "Lácteos y Quesos" in data["existing_categories"]
    assert "Vinos y Licores" in data["suggested_categories_to_create"]
    assert "Colun" in data["existing_brands"]
    assert "Viña Concha y Toro" in data["suggested_brands_to_create"]
    assert data["total_rows"] == 2


@pytest.mark.asyncio
async def test_analyze_excel_formula_sanitization_cwe_1236(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que celdas con prefijos de fórmula (=, @, +, -) sean sanitizadas anteponiendo comilla."""
    headers = _headers(["catalog.import.analyze"])

    payload = {
        "sheet_name": "Sheet1",
        "raw_headers": ["Producto", "Detalle Formula", "Comando"],
        "rows_data": [
            {
                "Producto": "=SUM(A1:A10)",
                "Detalle Formula": "@COMMAND|'calc.exe'!A0",
                "Comando": "+12345_TEST",
            }
        ],
    }

    resp = await async_client.post(
        "/api/v1/catalog/import/analyze-excel",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Comprobar que en sample_rows las fórmulas fueron neutralizadas
    first_sample = data["sample_rows"][0]
    assert first_sample["Producto"] == "'=SUM(A1:A10)"
    assert first_sample["Detalle Formula"].startswith("'")
    assert first_sample["Comando"].startswith("'")
    assert len(data["warnings"]) >= 3


@pytest.mark.asyncio
async def test_batch_create_successful_with_initial_stock(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica creación por lotes, creación de entidades sugeridas e inicialización de stock en Kardex."""
    headers = _headers(["catalog.import.batch_create"])

    payload = {
        "items": [
            {
                "nombre": "Harina de Trigo 1kg",
                "sku": "HAR-001",
                "categoria": "Abarrotes y Harinas",
                "marca": "Molino del Sol",
                "costo_neto": "950.00",
                "precio_venta": "1490.00",
                "stock_inicial": "100.0000",
            },
            {
                "nombre": "Aceite Maravilla 900ml",
                "sku": "ACE-001",
                "categoria": "Abarrotes y Harinas",
                "marca": "Molino del Sol",
                "costo_neto": "1800.00",
                "precio_venta": "2490.00",
                "stock_inicial": "50.0000",
            },
        ],
        "entities_to_create": {
            "categories": ["Abarrotes y Harinas"],
            "brands": ["Molino del Sol"],
        },
        "register_initial_stock": True,
        "default_bodega_id": 1,
    }

    resp = await async_client.post(
        "/api/v1/catalog/import/batch-create",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["created_products_count"] == 2
    assert "Abarrotes y Harinas" in data["created_categories"]
    assert "Molino del Sol" in data["created_brands"]
    assert data["kardex_movements_count"] == 2
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_batch_create_limit_exceeded_rejects_with_400(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que si la lista de items supera el límite de 1.500 productos, sea rechazada con HTTP 400."""
    headers = _headers(["catalog.import.batch_create"])

    # Generar 1.501 items dummy
    massive_items = [
        {"nombre": f"Item {i}", "sku": f"SKU-{i}", "costo_neto": "100.00"}
        for i in range(1501)
    ]

    payload = {
        "items": massive_items,
        "register_initial_stock": False,
    }

    resp = await async_client.post(
        "/api/v1/catalog/import/batch-create",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 400
    err_body = resp.json()
    assert "Batch limit exceeded" in err_body["detail"] or "batch_limit_exceeded" in err_body.get("i18n_key", "")
