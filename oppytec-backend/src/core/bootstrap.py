"""
oppytec-backend/src/core/bootstrap.py
Semilla idempotente Génesis para el Plano de Control (`public`) y esquemas de clientes (`tenant_*`).
Lee `SUPERUSER_GENESIS_*` estrictamente desde `Settings` (`SecretStr`, cero hardcoding de contraseñas).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pwdlib import PasswordHash

from src.core.config import Settings, get_settings

_password_hasher = PasswordHash.recommended()


@dataclass(frozen=True)
class RoleSeedSpec:
    """Especificación inmutable de un rol base (global o de cliente) con `hierarchy_rank` e `i18n_data`."""

    slug: str
    name: str
    hierarchy_rank: int
    i18n_data: dict[str, str]
    is_system_base: bool = True


@dataclass(frozen=True)
class ModuleSeedSpec:
    """Especificación inmutable de un módulo del catálogo `public.app_modules`."""

    slug: str
    name: str
    is_core: bool
    i18n_data: dict[str, str]


@dataclass(frozen=True)
class PlanSeedSpec:
    """Especificación inmutable de un plan comercial base con cuotas y precios multi-moneda `Decimal`."""

    slug: str
    name: str
    max_active_users: int
    max_storage_mb: int
    included_modules: tuple[str, ...]
    price_clp: Decimal
    price_usd: Decimal
    price_eur: Decimal
    price_brl: Decimal


@dataclass(frozen=True)
class GenesisSuperuserManifest:
    """Manifiesto en memoria del SuperUser Génesis construido desde variables de entorno."""

    email: str
    username: str
    hashed_password: str
    role_slug: str
    is_superuser_god: bool


# Roles Globales Base en `public.global_roles`
GLOBAL_BASE_ROLES: tuple[RoleSeedSpec, ...] = (
    RoleSeedSpec(
        slug="superuser",
        name="SuperUser Global",
        hierarchy_rank=0,
        i18n_data={"es": "SuperUsuario Global", "en": "Global SuperUser"},
    ),
    RoleSeedSpec(
        slug="admin",
        name="Administrador OppyTec",
        hierarchy_rank=10,
        i18n_data={"es": "Administrador OppyTec", "en": "OppyTec Administrator"},
    ),
    RoleSeedSpec(
        slug="supervisor",
        name="Supervisor de Plataforma",
        hierarchy_rank=20,
        i18n_data={"es": "Supervisor de Plataforma", "en": "Platform Supervisor"},
    ),
    RoleSeedSpec(
        slug="developer",
        name="Desarrollador / Soporte",
        hierarchy_rank=30,
        i18n_data={"es": "Desarrollador / Soporte", "en": "Developer / Support"},
    ),
)

# Roles Cliente Base Editables en `tenant_*.roles`
TENANT_BASE_ROLES: tuple[RoleSeedSpec, ...] = (
    RoleSeedSpec(
        slug="propietario",
        name="Propietario",
        hierarchy_rank=0,
        i18n_data={"es": "Propietario", "en": "Owner"},
    ),
    RoleSeedSpec(
        slug="superuser",
        name="SuperUser de Sucursal",
        hierarchy_rank=5,
        i18n_data={"es": "SuperUsuario de Sucursal", "en": "Branch SuperUser"},
    ),
    RoleSeedSpec(
        slug="admin",
        name="Administrador de Local",
        hierarchy_rank=10,
        i18n_data={"es": "Administrador de Local", "en": "Store Administrator"},
    ),
    RoleSeedSpec(
        slug="supervisor",
        name="Supervisor / Contador",
        hierarchy_rank=20,
        i18n_data={"es": "Supervisor / Contador", "en": "Supervisor / Accountant"},
    ),
    RoleSeedSpec(
        slug="cajero",
        name="Cajero / Usuario Operativo",
        hierarchy_rank=30,
        i18n_data={"es": "Cajero / Usuario Operativo", "en": "Cashier / Operational User"},
    ),
)

# Catálogo Maestro de Módulos (`public.app_modules`)
DEFAULT_APP_MODULES: tuple[ModuleSeedSpec, ...] = (
    ModuleSeedSpec(
        slug="catalog",
        name="Catálogo de Productos",
        is_core=True,
        i18n_data={"es": "Catálogo de Productos", "en": "Product Catalog"},
    ),
    ModuleSeedSpec(
        slug="inventory",
        name="Inventario y Bodegas",
        is_core=True,
        i18n_data={"es": "Inventario y Bodegas", "en": "Inventory & Warehouses"},
    ),
    ModuleSeedSpec(
        slug="recipes",
        name="Recetas y Escandallos",
        is_core=True,
        i18n_data={"es": "Recetas y Escandallos", "en": "Recipes & Costing"},
    ),
    ModuleSeedSpec(
        slug="procurement",
        name="Compras y Facturas",
        is_core=False,
        i18n_data={"es": "Compras y Facturas", "en": "Procurement & Invoices"},
    ),
    ModuleSeedSpec(
        slug="operations",
        name="Ventas, Buffet y Eventos",
        is_core=False,
        i18n_data={"es": "Ventas, Buffet y Eventos", "en": "Sales, Buffet & Events"},
    ),
    ModuleSeedSpec(
        slug="analytics",
        name="Analítica y Finanzas",
        is_core=False,
        i18n_data={"es": "Analítica y Finanzas", "en": "Analytics & Finance"},
    ),
    ModuleSeedSpec(
        slug="oppy_ai",
        name="Asistente IA OppyFy",
        is_core=False,
        i18n_data={"es": "Asistente IA OppyFy", "en": "OppyFy AI Assistant"},
    ),
)

# Planes Base Multi-Moneda (`public.system_plans`)
DEFAULT_SYSTEM_PLANS: tuple[PlanSeedSpec, ...] = (
    PlanSeedSpec(
        slug="starter",
        name="Plan Esencial",
        max_active_users=10,
        max_storage_mb=512,
        included_modules=("catalog", "inventory", "recipes"),
        price_clp=Decimal("49990.00"),
        price_usd=Decimal("55.00"),
        price_eur=Decimal("50.00"),
        price_brl=Decimal("280.00"),
    ),
    PlanSeedSpec(
        slug="enterprise",
        name="Plan Corporativo",
        max_active_users=100,
        max_storage_mb=5120,
        included_modules=(
            "catalog",
            "inventory",
            "recipes",
            "procurement",
            "operations",
            "analytics",
            "oppy_ai",
        ),
        price_clp=Decimal("149990.00"),
        price_usd=Decimal("165.00"),
        price_eur=Decimal("150.00"),
        price_brl=Decimal("850.00"),
    ),
)


def build_genesis_superuser_manifest(settings: Settings | None = None) -> GenesisSuperuserManifest:
    """
    Construye el manifiesto del SuperUser Génesis extrayendo sus credenciales
    desde `settings.SUPERUSER_GENESIS_*` y generando el hash Argon2id en memoria.
    """
    resolved = settings or get_settings()
    raw_password = resolved.SUPERUSER_GENESIS_PASSWORD.get_secret_value()
    if len(raw_password) < 8:
        raise ValueError("SUPERUSER_GENESIS_PASSWORD must be at least 8 characters long")
    hashed = _password_hasher.hash(raw_password)
    return GenesisSuperuserManifest(
        email=str(resolved.SUPERUSER_GENESIS_EMAIL),
        username=resolved.SUPERUSER_GENESIS_USERNAME,
        hashed_password=hashed,
        role_slug="superuser",
        is_superuser_god=True,
    )


def verify_genesis_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra el hash Argon2id generado por el bootstrapper."""
    return bool(_password_hasher.verify(plain_password, hashed_password))
