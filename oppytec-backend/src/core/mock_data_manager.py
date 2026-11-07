"""
oppytec-backend/src/core/mock_data_manager.py
Gestor Central de Mock Data vs Clean Slate (ADR-022):
- `load_mock_data_backup() -> dict[str, Any]`: carga y valida `oppytec-backend/fixtures/mock_data_backup.json`.
- `purge_all_runtime_mock_stores() -> dict[str, int]`: vacía en memoria todos los datos mock/demostrativos
  de routers y servicios para dejar el sistema en estado Clean Slate 100% limpio, preservando únicamente:
  * El SuperUser Génesis (`OppyTec.Admin@gmail.com` / `oppytec.admin`, contraseña `oppytec2026`).
  * Los módulos del sistema, los 5 roles base (`TENANT_BASE_ROLES`) y los 3 planes comerciales base (`DEFAULT_SYSTEM_PLANS`).
- `restore_runtime_mock_stores(preset_id: str | None = None) -> dict[str, int]`: restaura bajo demanda
  los stores en memoria a partir de `oppytec-backend/fixtures/mock_data_backup.json`.
- `reset_default_demo_stores() -> dict[str, int]`: restaura el estado base demostrativo para suites de pruebas unitarias.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import copy
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.core.bootstrap import DEFAULT_SYSTEM_PLANS, TENANT_BASE_ROLES
from src.core.security import hash_password

_BACKUP_JSON_PATH: Path = (
    Path(__file__).resolve().parents[2] / "fixtures" / "mock_data_backup.json"
)
_CACHED_BACKUP_PAYLOAD: dict[str, Any] | None = None
_CACHED_DEMO_PASSWORD_HASH: str | None = None
_CACHED_GENESIS_PASSWORD_HASH: str | None = None
_IS_CLEAN_SLATE_ACTIVE: bool = False

DEMO_HOLDING_IDS: frozenset[str] = frozenset({"holding_genesis", "holding_pacifico"})
DEMO_LEGAL_ENTITY_IDS: frozenset[str] = frozenset({"le_genesis", "le_pacifico"})
DEMO_TENANT_IDS: frozenset[str] = frozenset({"tenant_genesis", "tenant_pacifico_centro"})
DEMO_CLIENT_USER_EMAILS: frozenset[str] = frozenset(
    {"admin.local@restaurant.cl", "chef@pacifico.cl"}
)
DEMO_CLIENT_USER_IDS: frozenset[int] = frozenset({101, 102})


def is_clean_slate_active() -> bool:
    """Indica si el sistema se encuentra actualmente en modo Clean Slate global."""
    return _IS_CLEAN_SLATE_ACTIVE


def _get_demo_password_hash() -> str:
    """Obtiene o precalcula el hash Argon2id de la clave demo para evitar recálculo en tests."""
    global _CACHED_DEMO_PASSWORD_HASH
    if _CACHED_DEMO_PASSWORD_HASH is None:
        from src.modules.identity.presentation.router import _CLIENT_USERS_STORE

        existing_101 = _CLIENT_USERS_STORE.get(101)
        if existing_101 and isinstance(existing_101.get("password_hash"), str):
            _CACHED_DEMO_PASSWORD_HASH = str(existing_101["password_hash"])
        else:
            _CACHED_DEMO_PASSWORD_HASH = hash_password("OppyTec#2026")
    return _CACHED_DEMO_PASSWORD_HASH


def _get_genesis_password_hash() -> str:
    """Obtiene o precalcula el hash Argon2id para el SuperUser Génesis (`oppytec2026`)."""
    global _CACHED_GENESIS_PASSWORD_HASH
    if _CACHED_GENESIS_PASSWORD_HASH is None:
        _CACHED_GENESIS_PASSWORD_HASH = hash_password("oppytec2026")
    return _CACHED_GENESIS_PASSWORD_HASH


def load_mock_data_backup() -> dict[str, Any]:
    """
    Carga y valida la estructura canónica de `oppytec-backend/fixtures/mock_data_backup.json`.
    Retorna una copia profunda para evitar mutaciones accidentales en memoria.
    """
    global _CACHED_BACKUP_PAYLOAD
    if _CACHED_BACKUP_PAYLOAD is None:
        if not _BACKUP_JSON_PATH.is_file():
            raise FileNotFoundError(
                f"Mock data backup file not found at '{_BACKUP_JSON_PATH}'."
            )
        raw_text = _BACKUP_JSON_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError("Mock data backup JSON root must be an object.")
        required_keys = {"metadata", "postgresql_pre_clean_snapshot", "backend_modules"}
        missing = required_keys - set(parsed.keys())
        if missing:
            raise ValueError(
                f"Mock data backup JSON is missing required root sections: {sorted(missing)}"
            )
        _CACHED_BACKUP_PAYLOAD = parsed
    return copy.deepcopy(_CACHED_BACKUP_PAYLOAD)


def purge_all_runtime_mock_stores() -> dict[str, int]:
    """
    Limpia en memoria todos los datos mock/demostrativos de routers y servicios para dejar
    el sistema en estado Clean Slate 100% limpio, conservando únicamente:
    - El SuperUser Génesis (`OppyTec.Admin@gmail.com` / `oppytec.admin`, pass `oppytec2026`).
    - Los 3 planes comerciales base (`DEFAULT_SYSTEM_PLANS`).
    - Los 5 roles base de sucursal (`TENANT_BASE_ROLES`).
    """
    global _IS_CLEAN_SLATE_ACTIVE
    _get_demo_password_hash()

    from src.modules.catalog.presentation.router import (
        _brands_store,
        _categories_store,
        _container_types_store,
        _products_store,
    )
    from src.modules.events.presentation.router import (  # noqa: F401
        router as _events_router,
    )
    from src.modules.identity.presentation.router import (
        _CLIENT_USERS_STORE,
        _GLOBAL_USERS_STORE,
        _build_genesis_store_entry,
        _custom_roles,
    )
    from src.modules.identity.presentation.schemas import RoleResponse
    from src.modules.inventory.presentation.router import (
        _inventory_service,
        _merma_analytics_service,
        _physical_count_service,
        _waste_service,
    )
    from src.modules.operations.presentation.router_actividades import (
        _actividades_service,
    )
    from src.modules.oppy_ai.presentation.router import (
        _permission_grants_store,
        _worker_wallets_store,
    )
    from src.modules.tenancy.presentation.platform_admin_router import (
        _admin_plans_service,
        _jev_consumption_service,
        _token_consumption_service,
    )
    from src.modules.tenancy.presentation.router import (
        _holdings_store,
        _legal_entities_store,
        _plans_store,
        _tenants_store,
    )
    from src.modules.tenancy.presentation.sandbox_router import _sandbox_service
    from src.modules.tenancy.presentation.schemas import SystemPlanResponse

    purged_counts: dict[str, int] = {}

    # 1. Tenancy router: vaciar holdings, legal_entities y tenants; conservar los 3 planes base
    purged_counts["holdings"] = len(_holdings_store)
    purged_counts["legal_entities"] = len(_legal_entities_store)
    purged_counts["tenants"] = len(_tenants_store)
    _holdings_store.clear()
    _legal_entities_store.clear()
    _tenants_store.clear()
    _plans_store.clear()
    for plan in DEFAULT_SYSTEM_PLANS:
        _plans_store[plan.slug] = SystemPlanResponse(
            slug=plan.slug,
            name=plan.name,
            max_active_users=plan.max_active_users,
            max_products=plan.max_products,
            max_suppliers=plan.max_suppliers,
            max_recipes=plan.max_recipes,
            max_combos=plan.max_combos,
            max_storage_mb=plan.max_storage_mb,
            included_modules=list(plan.included_modules),
            anchor_currency="CLP",
            price_clp=plan.price_clp,
            price_usd=plan.price_usd,
            price_eur=plan.price_eur,
            price_brl=plan.price_brl,
            auto_convert_fx=True,
        )

    # 2. Identity router: vaciar _CLIENT_USERS_STORE y asegurar únicamente SuperUser Génesis en _GLOBAL_USERS_STORE
    purged_counts["client_users"] = len(_CLIENT_USERS_STORE)
    purged_counts["extra_global_users"] = max(0, len(_GLOBAL_USERS_STORE) - 1)
    _CLIENT_USERS_STORE.clear()
    _GLOBAL_USERS_STORE.clear()
    genesis_entry = _build_genesis_store_entry()
    genesis_entry["email"] = "OppyTec.Admin@gmail.com"
    genesis_entry["username"] = "oppytec.admin"
    genesis_entry["hashed_password"] = _get_genesis_password_hash()
    _GLOBAL_USERS_STORE[1] = genesis_entry
    _custom_roles.clear()
    for role in TENANT_BASE_ROLES:
        _custom_roles[role.slug] = RoleResponse(
            slug=role.slug,
            name=role.name,
            hierarchy_rank=role.hierarchy_rank,
            permissions=(
                ["settings.rbac.delegate_subordinates"]
                if role.hierarchy_rank <= 20
                else []
            ),
        )

    # 3. Catalog router: vaciar _products_store, _categories_store, _brands_store, _container_types_store
    purged_counts["products"] = len(_products_store)
    purged_counts["categories"] = len(_categories_store)
    purged_counts["brands"] = len(_brands_store)
    purged_counts["container_types"] = len(_container_types_store)
    _products_store.clear()
    _categories_store.clear()
    _brands_store.clear()
    _container_types_store.clear()
    catalog_mod = sys.modules.get("src.modules.catalog.presentation.router")
    if catalog_mod is not None:
        catalog_mod._product_seq = 0  # type: ignore[attr-defined]
        catalog_mod._category_seq = 0  # type: ignore[attr-defined]
        catalog_mod._brand_seq = 0  # type: ignore[attr-defined]
        catalog_mod._container_type_seq = 0  # type: ignore[attr-defined]

    # 4. OppyAI router: vaciar _worker_wallets_store y _permission_grants_store
    purged_counts["worker_wallets"] = len(_worker_wallets_store)
    purged_counts["permission_grants"] = len(_permission_grants_store)
    _worker_wallets_store.clear()
    _permission_grants_store.clear()

    # 5. Operations / Actividades router: limpiar colecciones en memoria de _actividades_service
    purged_counts["actividades_records"] = (
        len(_actividades_service._notas_equipo)
        + len(_actividades_service._notas_personales)
        + len(_actividades_service._tareas)
        + len(_actividades_service._plantillas)
        + len(_actividades_service._turnos)
    )
    _actividades_service.reset()

    # 6. Inventory router: limpiar _inventory_service, _waste_service, _physical_count_service, _merma_analytics_service
    purged_counts["inventory_ledger"] = len(_inventory_service._ledger)
    purged_counts["wastes"] = len(_waste_service._wastes)
    purged_counts["physical_counts"] = len(_physical_count_service._sessions)
    purged_counts["merma_analytics"] = len(_merma_analytics_service._memory_mermas)
    _inventory_service.reset()
    _waste_service._wastes.clear()
    _waste_service._seq = 0
    _physical_count_service.reset()
    _merma_analytics_service.reset()

    # 7. Events router: limpiar _salon_service y _event_service si están inicializados
    purged_salones = 0
    purged_events = 0
    events_mod = sys.modules.get("src.modules.events.presentation.router")
    if events_mod is not None:
        salon_srv = getattr(events_mod, "_salon_service", None)
        if salon_srv is not None:
            purged_salones = sum(len(m) for m in salon_srv._salones.values())
            salon_srv.reset()
        event_srv = getattr(events_mod, "_event_service", None)
        if event_srv is not None:
            purged_events = sum(len(m) for m in event_srv._events.values())
            event_srv.reset()
    purged_counts["salones"] = purged_salones
    purged_counts["events"] = purged_events

    # 8. Sandbox router: limpiar _sandbox_service._history_ring_buffer
    purged_counts["sandbox_history"] = len(_sandbox_service._history_ring_buffer)
    _sandbox_service._history_ring_buffer.clear()

    # 9. Platform Admin FinOps logs: limpiar logs demostrativos de tokens y JEV
    purged_counts["token_logs"] = len(_token_consumption_service._logs)
    purged_counts["jev_logs"] = len(_jev_consumption_service._logs)
    _token_consumption_service._logs.clear()
    _jev_consumption_service._logs.clear()

    # Sincronizar referencia de planes de Platform Admin
    _admin_plans_service.set_clients_stores(_holdings_store, _tenants_store)

    _IS_CLEAN_SLATE_ACTIVE = True
    return purged_counts


def restore_runtime_mock_stores(
    preset_id: str | None = None,
    *,
    seed_products: bool = True,
) -> dict[str, int]:
    """
    Restaura en memoria los stores a partir de `oppytec-backend/fixtures/mock_data_backup.json`
    (holdings, legal_entities, tenants, client_users, categorías, marcas, tipos de envase,
    productos, billeteras IA, historial).
    """
    global _IS_CLEAN_SLATE_ACTIVE
    backup = load_mock_data_backup()
    backend_mods = backup.get("backend_modules", {})
    demo_pw_hash = _get_demo_password_hash()

    from src.modules.catalog.presentation.router import (
        _brands_store,
        _categories_store,
        _container_types_store,
        _products_store,
    )
    from src.modules.catalog.presentation.schemas import (
        BrandResponse,
        CategoryResponse,
        ContainerTypeResponse,
        ProductResponse,
    )
    from src.modules.identity.presentation.router import (
        _CLIENT_USERS_STORE,
        _GLOBAL_USERS_STORE,
        _build_genesis_store_entry,
        _custom_roles,
    )
    from src.modules.identity.presentation.schemas import RoleResponse
    from src.modules.oppy_ai.domain.credit_wallet import WorkerCreditWalletState
    from src.modules.oppy_ai.presentation.router import _worker_wallets_store
    from src.modules.tenancy.presentation.platform_admin_router import (
        _admin_plans_service,
        _jev_consumption_service,
        _token_consumption_service,
    )
    from src.modules.tenancy.presentation.router import (
        _holdings_store,
        _legal_entities_store,
        _plans_store,
        _tenants_store,
    )
    from src.modules.tenancy.presentation.sandbox_router import _sandbox_service
    from src.modules.tenancy.presentation.schemas import (
        HoldingResponse,
        LegalEntityResponse,
        SystemPlanResponse,
        TenantResponse,
    )
    from src.modules.tenancy.presentation.schemas_sandbox import MockDataHistoryItem

    restored_counts: dict[str, int] = {}

    # 1. Tenancy router stores
    tenancy_data = backend_mods.get("tenancy_router", {})
    holdings_raw = tenancy_data.get("holdings", {})
    legal_entities_raw = tenancy_data.get("legal_entities", {})
    tenants_raw = tenancy_data.get("tenants", {})
    plans_raw = tenancy_data.get("plans", {})

    _holdings_store.clear()
    for h_id, h_payload in holdings_raw.items():
        _holdings_store[str(h_id)] = HoldingResponse.model_validate(h_payload)
    restored_counts["holdings"] = len(_holdings_store)

    _legal_entities_store.clear()
    for le_id, le_payload in legal_entities_raw.items():
        _legal_entities_store[str(le_id)] = LegalEntityResponse.model_validate(
            le_payload
        )
    restored_counts["legal_entities"] = len(_legal_entities_store)

    _tenants_store.clear()
    for t_id, t_payload in tenants_raw.items():
        _tenants_store[str(t_id)] = TenantResponse.model_validate(t_payload)
    restored_counts["tenants"] = len(_tenants_store)

    _plans_store.clear()
    if plans_raw:
        for p_slug, p_payload in plans_raw.items():
            _plans_store[str(p_slug)] = SystemPlanResponse.model_validate(p_payload)
    else:
        for plan in DEFAULT_SYSTEM_PLANS:
            _plans_store[plan.slug] = SystemPlanResponse(
                slug=plan.slug,
                name=plan.name,
                max_active_users=plan.max_active_users,
                max_products=plan.max_products,
                max_suppliers=plan.max_suppliers,
                max_recipes=plan.max_recipes,
                max_combos=plan.max_combos,
                max_storage_mb=plan.max_storage_mb,
                included_modules=list(plan.included_modules),
                anchor_currency="CLP",
                price_clp=plan.price_clp,
                price_usd=plan.price_usd,
                price_eur=plan.price_eur,
                price_brl=plan.price_brl,
                auto_convert_fx=True,
            )
    restored_counts["plans"] = len(_plans_store)

    # 2. Identity router stores
    identity_data = backend_mods.get("identity_router", {})
    client_users_raw = identity_data.get("client_users", {})
    custom_roles_raw = identity_data.get("custom_roles", {})

    _GLOBAL_USERS_STORE.clear()
    genesis_entry = _build_genesis_store_entry()
    genesis_entry["email"] = "OppyTec.Admin@gmail.com"
    genesis_entry["username"] = "oppytec.admin"
    genesis_entry["hashed_password"] = _get_genesis_password_hash()
    _GLOBAL_USERS_STORE[1] = genesis_entry

    _CLIENT_USERS_STORE.clear()
    for uid_str, u_payload in client_users_raw.items():
        uid_int = int(uid_str)
        entry = dict(u_payload)
        entry.setdefault("user_id", uid_int)
        entry["password_hash"] = demo_pw_hash
        _CLIENT_USERS_STORE[uid_int] = entry
    restored_counts["client_users"] = len(_CLIENT_USERS_STORE)

    _custom_roles.clear()
    if custom_roles_raw:
        for r_slug, r_payload in custom_roles_raw.items():
            _custom_roles[str(r_slug)] = RoleResponse.model_validate(r_payload)
    else:
        for role in TENANT_BASE_ROLES:
            _custom_roles[role.slug] = RoleResponse(
                slug=role.slug,
                name=role.name,
                hierarchy_rank=role.hierarchy_rank,
                permissions=(
                    ["settings.rbac.delegate_subordinates"]
                    if role.hierarchy_rank <= 20
                    else []
                ),
            )
    restored_counts["custom_roles"] = len(_custom_roles)

    # 3. Catalog router stores (categories, brands, container_types, products)
    catalog_data = backend_mods.get("catalog_router", {})
    categories_raw = catalog_data.get("categories", {})
    brands_raw = catalog_data.get("brands", {})
    container_types_raw = catalog_data.get("container_types", {})
    catalog_mod = sys.modules.get("src.modules.catalog.presentation.router")

    _categories_store.clear()
    for cid_str, c_payload in categories_raw.items():
        cid_int = int(cid_str)
        _categories_store[cid_int] = CategoryResponse.model_validate(c_payload)
    if catalog_mod is not None:
        catalog_mod._category_seq = max(_categories_store.keys(), default=0)  # type: ignore[attr-defined]
    restored_counts["categories"] = len(_categories_store)

    _brands_store.clear()
    for bid_str, b_payload in brands_raw.items():
        bid_int = int(bid_str)
        _brands_store[bid_int] = BrandResponse.model_validate(b_payload)
    if catalog_mod is not None:
        catalog_mod._brand_seq = max(_brands_store.keys(), default=0)  # type: ignore[attr-defined]
    restored_counts["brands"] = len(_brands_store)

    _container_types_store.clear()
    for ctid_str, ct_payload in container_types_raw.items():
        ctid_int = int(ctid_str)
        _container_types_store[ctid_int] = ContainerTypeResponse.model_validate(
            ct_payload
        )
    if catalog_mod is not None:
        catalog_mod._container_type_seq = max(  # type: ignore[attr-defined]
            _container_types_store.keys(), default=0
        )
    restored_counts["container_types"] = len(_container_types_store)

    _products_store.clear()
    if catalog_mod is not None:
        catalog_mod._product_seq = 0  # type: ignore[attr-defined]
    if seed_products:
        sandbox_data = backend_mods.get("sandbox_service", {})
        seed_catalog = sandbox_data.get("seed_fefo_catalog", [])
        category_map = {"carnes": 1, "verduras": 2, "lacteos": 3}
        for idx, item in enumerate(seed_catalog, start=1):
            cost_dec = Decimal(str(item.get("cost", "1000.00"))).quantize(
                Decimal("0.01")
            )
            cat_id = category_map.get(str(item.get("category", "")).lower(), 1)
            brand_id = 1 if preset_id == "fast-food-pollo-king" or idx <= 3 else 3
            brand_name = (
                _brands_store[brand_id].nombre
                if brand_id in _brands_store
                else "Pollo King"
            )
            unit_str = str(item.get("unit", "kg"))
            prod = ProductResponse(
                id=idx,
                product_id=idx,
                sku=str(item.get("sku", f"SKU-MOCK-{idx:03d}")),
                nombre=str(item.get("name", f"Insumo Demo {idx}")),
                marca_id=brand_id,
                marca_comercial=brand_name,
                categoria_id=cat_id,
                unidad_base=unit_str.upper(),
                costo_unitario=cost_dec,
                costo_compra_neto=cost_dec,
                costo_unitario_almacen=cost_dec,
                costo_unitario_receta=(cost_dec / Decimal("1000")).quantize(
                    Decimal("0.0001")
                ),
                precio_venta=(cost_dec * Decimal("1.50")).quantize(Decimal("0.01")),
                unidad_compra=unit_str,
                unidad_almacen=unit_str,
                unidad_receta="g" if unit_str == "kg" else unit_str,
                is_active=True,
            )
            _products_store[idx] = prod
            if catalog_mod is not None:
                catalog_mod._product_seq = idx  # type: ignore[attr-defined]
    restored_counts["products"] = len(_products_store)

    # 4. OppyAI router wallets
    oppy_ai_data = backend_mods.get("oppy_ai_router", {})
    wallets_raw = oppy_ai_data.get("worker_wallets", {})
    _worker_wallets_store.clear()
    for wid_str, w_payload in wallets_raw.items():
        wid_int = int(wid_str)
        _worker_wallets_store[wid_int] = WorkerCreditWalletState(
            user_id=int(w_payload.get("user_id", wid_int)),
            allocated_credits=Decimal(str(w_payload.get("allocated_credits", "0.00"))),
            consumed_credits=Decimal(str(w_payload.get("consumed_credits", "0.00"))),
            is_oppyfy_enabled=bool(w_payload.get("is_oppyfy_enabled", True)),
        )
    restored_counts["worker_wallets"] = len(_worker_wallets_store)

    # 5. Sandbox history ring buffer
    sandbox_data = backend_mods.get("sandbox_service", {})
    default_history_raw = sandbox_data.get("default_history", [])
    _sandbox_service._history_ring_buffer.clear()
    if default_history_raw:
        for h_item in reversed(default_history_raw):
            _sandbox_service._history_ring_buffer.append(
                MockDataHistoryItem.model_validate(h_item)
            )
    else:
        _sandbox_service._seed_default_history()
    restored_counts["sandbox_history"] = len(_sandbox_service._history_ring_buffer)

    # 6. Platform Admin FinOps logs: restaurar muestras por defecto
    _token_consumption_service.reset()
    _jev_consumption_service.reset()
    restored_counts["token_logs"] = len(_token_consumption_service._logs)
    restored_counts["jev_logs"] = len(_jev_consumption_service._logs)

    # Sincronizar referencia de planes de Platform Admin
    _admin_plans_service.set_clients_stores(_holdings_store, _tenants_store)

    _IS_CLEAN_SLATE_ACTIVE = False
    return restored_counts


def reset_default_demo_stores() -> dict[str, int]:
    """
    Restaura los stores demostrativos predeterminados para aislamiento determinista
    en suites de pruebas unitarias (`pytest`).
    """
    return restore_runtime_mock_stores(preset_id=None, seed_products=False)
