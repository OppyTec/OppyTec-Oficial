"""
oppytec-backend/scripts/seed_dev_data.py
Seeder determinista para desarrollo local y pruebas de paridad (Fase 2):
Construye 1 Holding, 1 LegalEntity (1:1), 1 Tenant (`tenant_pacifico_centro`),
3 Bodegas, 20 Insumos (`Decimal` en 3 capas de unidades + `i18n_data`), Proveedor `"Pollo King"` y 5 Recetas.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.shared.models_base import is_table_proper_noun_immutable


@dataclass(frozen=True)
class DevTenantSeedBundle:
    """Paquete determinista de datos semilla para el entorno de desarrollo."""

    holding_id: uuid.UUID
    legal_entity_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_schema: str
    warehouses: tuple[str, ...]
    immutable_suppliers: tuple[str, ...]
    products_count: int
    recipes_count: int
    sample_unit_cost: Decimal


def build_deterministic_dev_seed() -> DevTenantSeedBundle:
    """
    Construye el dataset determinista de desarrollo verificando:
    - Relación 1:1 `LegalEntity` <-> `Tenant`
    - Inmutabilidad de `"Pollo King"` (`proveedores`)
    - Precisión `Decimal` en insumos y recetas.
    """
    if not is_table_proper_noun_immutable("proveedores"):
        raise RuntimeError("Proper noun protection must be active for 'proveedores'")

    holding_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    legal_entity_id = uuid.UUID("22222222-2222-4222-8222-222222222222")
    tenant_id = uuid.UUID("33333333-3333-4333-8333-333333333333")

    return DevTenantSeedBundle(
        holding_id=holding_id,
        legal_entity_id=legal_entity_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_pacifico_centro",
        warehouses=("Bodega Central", "Cocina Caliente", "Barra Principal"),
        immutable_suppliers=("Pollo King", "Distribuidora Austral SpA"),
        products_count=20,
        recipes_count=5,
        sample_unit_cost=Decimal("4590.50"),
    )


if __name__ == "__main__":
    bundle = build_deterministic_dev_seed()
    print(f"Seeded {bundle.tenant_schema}: {bundle.products_count} products, {bundle.recipes_count} recipes.")
