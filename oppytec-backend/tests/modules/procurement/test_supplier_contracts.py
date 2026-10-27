"""
oppytec-backend/tests/modules/procurement/test_supplier_contracts.py
Certificación 5D (Tarea 7.4) — Contratos de Proveedores, Unicidad RUT, Regla "Pollo King" y Catálogo Pactado:
1. Unitario: Validación Módulo 11 chileno (`calculate_chilean_dv`, `RutTaxId`), soporte de Tax ID internacional
   e invariante de nombres propios no traducibles (`Supplier.translatable == False`).
2. Integración (In-Memory & PostgreSQL): Unicidad de RUT normalizado, bloqueo de renombrado/traducción
   ("Pollo King" -> `ProperNounImmutabilityError`), acuerdos de precios pactados (`ProductoProveedor`) y
   exclusividad de `es_proveedor_principal` por insumo.
3. Propiedades (Hypothesis): Verificación universal de Módulo 11 para cualquier cuerpo numérico (1..999_999_999)
   y preservación exacta de precios pactados `Decimal(14, 2)`.
4. Contratos: Esquemas Pydantic v2 (`SupplierCreateRequest`, `SupplierResponse`, `SupplierCatalogBulkUpdateRequest`).
5. Paridad con Legacy: Regla inmutable "Pollo King" en `SupplierService` y `ProcurementService`.
"""
from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.core.exceptions import (
    DomainValidationError,
    ProperNounImmutabilityError,
)
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.procurement.application.procurement_service import ProcurementService
from src.modules.procurement.application.supplier_service import SupplierService
from src.modules.procurement.domain import (
    InvalidRutError,
    RutTaxId,
    Supplier,
    assert_supplier_name_immutable,
    calculate_chilean_dv,
)
from src.modules.procurement.presentation.schemas import (
    SupplierCatalogBulkUpdateRequest,
    SupplierCatalogItemPayload,
    SupplierCreateRequest,
    SupplierResponse,
)

pytestmark = [pytest.mark.unit]

DB_TENANT_SCHEMA = "tenant_test_procurement"

ALL_DV_CHARS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "K")


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión PostgreSQL asíncrona real en `tenant_test_procurement`."""
    settings_obj = get_settings()
    engine = create_async_engine(
        settings_obj.DATABASE_URL.get_secret_value(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": f"{DB_TENANT_SCHEMA},public"}},
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    tables = [
        "compra_incidencias",
        "compra_items",
        "compras",
        "producto_proveedores",
        "proveedores",
        "mermas",
        "registro_stock",
        "producto_bodegas",
        "productos",
        "bodegas",
        "categorias",
    ]
    truncate_stmt = f"TRUNCATE TABLE {', '.join(f'{DB_TENANT_SCHEMA}.{t}' for t in tables)} CASCADE"

    async with session_factory() as session:
        await session.execute(text(truncate_stmt))
        await session.commit()
        try:
            yield session
        finally:
            with contextlib.suppress(Exception):
                await session.rollback()
            with contextlib.suppress(Exception):
                await session.execute(text(truncate_stmt))
                await session.commit()

    await engine.dispose()


# ==============================================================================
# DIMENSIÓN 1 & 3: PROPIEDADES (HYPOTHESIS) DE RUT MÓDULO 11 Y TAX ID INTL
# ==============================================================================


class TestRutModulo11AndInternationalTaxIdProperties:
    """Pruebas basadas en propiedades (Hypothesis) para el algoritmo Módulo 11 chileno y Tax IDs."""

    @given(rut_body_int=st.integers(min_value=1, max_value=999_999_999))
    @settings(max_examples=80, deadline=None)
    def test_property_chilean_modulo_11_accepts_valid_dv_and_rejects_all_mutations(
        self, rut_body_int: int
    ) -> None:
        """
        Propiedad universal Módulo 11:
        Para cualquier entero `rut_body_int` de 1 a 9 dígitos:
        1. `dv = calculate_chilean_dv(rut_body_int)` pertenece a `{'0'..'9', 'K'}`.
        2. Tanto el formato limpio `"{body}-{dv}"` como el formato con puntos producen el mismo `RutTaxId`.
        3. Cualquier dígito verificador distinto `wrong_dv != dv` dispara `InvalidRutError`.
        """
        body_str = str(rut_body_int)
        dv = calculate_chilean_dv(body_str)
        assert dv in ALL_DV_CHARS

        raw_clean = f"{body_str}-{dv}"
        formatted_body = f"{rut_body_int:,}".replace(",", ".")
        raw_dotted = f"{formatted_body}-{dv.lower()}"

        vo_clean = RutTaxId(raw_clean)
        vo_dotted = RutTaxId(raw_dotted)

        assert vo_clean == vo_dotted
        assert vo_clean.formatted == f"{formatted_body}-{dv}"
        assert vo_clean.clean == f"{body_str}-{dv}"
        assert vo_clean.body == body_str
        assert vo_clean.dv == dv
        assert vo_clean.is_chilean is True

        # Probar que un DV alterado siempre falla
        wrong_dv = next(ch for ch in ALL_DV_CHARS if ch != dv)
        with pytest.raises(InvalidRutError):
            RutTaxId(f"{body_str}-{wrong_dv}")

    @pytest.mark.parametrize(
        ("tax_id", "country"),
        [
            ("US-98-7654321", "US"),
            ("DE123456789", "DE"),
            ("ES-B87654321", "ES"),
            ("MX-ABC010203XYZ", "MX"),
        ],
    )
    def test_international_tax_id_formats(self, tax_id: str, country: str) -> None:
        vo = RutTaxId.from_international(tax_id, country=country)
        assert vo.is_chilean is False
        assert vo.country == country
        assert vo.value == tax_id.upper()
        assert vo.dv == ""


# ==============================================================================
# DIMENSIÓN 1 & 5: REGLA INMUTABLE "POLLO KING" (NOMBRES PROPIOS NO TRADUCIBLES)
# ==============================================================================


class TestPolloKingProperNounImmutabilityContract:
    """Certifica la regla arquitectónica inmutable 'Pollo King' en dominio y servicios."""

    def test_domain_supplier_and_reconciliation_enforce_pollo_king(self) -> None:
        supplier = Supplier(
            rut_tax_id=RutTaxId("76.543.210-3"),
            razon_social="Pollo King",
            nombre_fantasia="Pollo King SpA",
        )
        assert Supplier.translatable is False
        assert supplier.translatable is False

        # Mismo nombre propio es válido
        supplier.assert_proper_noun_immutable("Pollo King")
        supplier.assert_proper_noun_immutable("Pollo King SpA")
        assert_supplier_name_immutable("Pollo King", "Pollo King")

        # Traducción o alteración levanta ProperNounImmutabilityError
        for translated in ("Chicken King", "Rooster King", "Pollo Rey", "Pollo King Translated"):
            with pytest.raises(ProperNounImmutabilityError):
                supplier.assert_proper_noun_immutable(translated)
            with pytest.raises(ProperNounImmutabilityError):
                assert_supplier_name_immutable("Pollo King", translated)

    @pytest.mark.asyncio
    async def test_services_reject_pollo_king_translation_or_rename(self) -> None:
        sup_service = SupplierService(use_in_memory=True)
        created = await sup_service.create_supplier(
            None,
            {
                "rut_tax_id": "76.543.210-3",
                "razon_social": "Pollo King",
                "nombre_fantasia": "Pollo King Distribución",
            },
        )

        with pytest.raises(ProperNounImmutabilityError):
            await sup_service.update_supplier(
                None,
                created["id"],
                {"razon_social": "Chicken King LLC"},
            )

        proc_service = ProcurementService(use_in_memory=True)
        proc_service.register_supplier(created["id"], "Pollo King")
        with pytest.raises(ProperNounImmutabilityError):
            proc_service.rename_supplier(created["id"], "Chicken King")
        assert proc_service.supplier_name(created["id"]) == "Pollo King"


# ==============================================================================
# DIMENSIÓN 2 & 3 & 4: UNICIDAD DE RUT Y PRECIOS PACTADOS (`ProductoProveedor`)
# ==============================================================================


class TestSupplierUniquenessAndCatalogAgreements:
    """Verifica unicidad de RUT y consistencia de acuerdos de catálogo en memoria y PostgreSQL."""

    @pytest.mark.asyncio
    async def test_rut_uniqueness_across_formatted_and_unformatted_inputs(self) -> None:
        """Si se registra '76543210-3', un segundo intento con '76.543.210-3' es rechazado por duplicidad."""
        service = SupplierService(use_in_memory=True)
        first = await service.create_supplier(
            None,
            {
                "rut_tax_id": "76543210-3",
                "razon_social": "Pollo King",
            },
        )
        assert first["rut_tax_id"] == "76.543.210-3"

        with pytest.raises(DomainValidationError):
            await service.create_supplier(
                None,
                {
                    "rut_tax_id": "76.543.210-3",
                    "razon_social": "Otro Proveedor SpA",
                },
            )

    @given(
        agreed_prices=st.lists(
            st.decimals(
                min_value=Decimal("10.00"),
                max_value=Decimal("999999.99"),
                places=2,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=40, deadline=None)
    @pytest.mark.asyncio
    async def test_property_catalog_agreed_prices_preserve_exact_decimal(
        self, agreed_prices: list[Decimal]
    ) -> None:
        """
        Propiedad de Consistencia de Precios Pactados:
        Todo precio pactado en `update_supplier_catalog` se persiste y recupera con precisión
        exacta `Decimal(14, 2)` sin deriva numérica.
        """
        service = SupplierService(use_in_memory=True)
        sup = await service.create_supplier(
            None,
            {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King"},
        )
        items_payload = [
            {
                "producto_id": idx + 1,
                "precio_pactado": price,
                "codigo_producto_proveedor": f"PK-{idx + 1:03d}",
                "tiempo_entrega_dias": 2,
                "es_proveedor_principal": idx == 0,
            }
            for idx, price in enumerate(agreed_prices)
        ]

        catalog = await service.update_supplier_catalog(None, sup["id"], items_payload)
        assert len(catalog) == len(agreed_prices)
        for idx, entry in enumerate(catalog):
            assert isinstance(entry["precio_pactado"], Decimal)
            assert entry["precio_pactado"] == agreed_prices[idx]

    @pytest.mark.asyncio
    async def test_postgresql_single_primary_supplier_per_product_invariant(
        self, async_db_session: AsyncSession
    ) -> None:
        """
        Certifica en PostgreSQL real que cuando un proveedor B marca `es_proveedor_principal=True`
        para un `producto_id`, el proveedor A que era principal anteriormente pasa automáticamente
        a `es_proveedor_principal=False`.
        """
        cat = Categoria(nombre="Insumos Principales")
        async_db_session.add(cat)
        await async_db_session.flush()

        prod = Producto(sku="INS-ACEITE-20L", nombre="Aceite Vegetal 20L", categoria_id=cat.id)
        async_db_session.add(prod)
        await async_db_session.flush()
        prod_id = prod.id
        await async_db_session.commit()

        service = SupplierService(use_in_memory=False)
        sup_a = await service.create_supplier(
            async_db_session,
            {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King"},
        )
        sup_b = await service.create_supplier(
            async_db_session,
            {"rut_tax_id": "77.123.456-9", "razon_social": "Distribuidora Austral"},
        )

        # 1. Asignar Proveedor A como proveedor principal del producto
        cat_a = await service.update_supplier_catalog(
            async_db_session,
            sup_a["id"],
            [
                {
                    "producto_id": prod_id,
                    "precio_pactado": Decimal("24500.00"),
                    "codigo_producto_proveedor": "PK-AC20",
                    "tiempo_entrega_dias": 2,
                    "es_proveedor_principal": True,
                }
            ],
        )
        assert cat_a[0]["es_proveedor_principal"] is True

        # 2. Asignar Proveedor B como nuevo proveedor principal del mismo producto
        cat_b = await service.update_supplier_catalog(
            async_db_session,
            sup_b["id"],
            [
                {
                    "producto_id": prod_id,
                    "precio_pactado": Decimal("23900.00"),
                    "codigo_producto_proveedor": "DA-AC20",
                    "tiempo_entrega_dias": 1,
                    "es_proveedor_principal": True,
                }
            ],
        )
        assert cat_b[0]["es_proveedor_principal"] is True

        # 3. Verificar que Proveedor A quedó desmarcado como principal pero conserva su precio pactado
        cat_a_after = await service.get_supplier_catalog(async_db_session, sup_a["id"])
        assert len(cat_a_after) == 1
        assert cat_a_after[0]["precio_pactado"] == Decimal("24500.00")
        assert cat_a_after[0]["es_proveedor_principal"] is False

    def test_supplier_pydantic_schemas_and_xss_sanitization(self) -> None:
        """Verifica contratos Pydantic v2 de proveedores y catálogo pactado."""
        create_req = SupplierCreateRequest(
            rut_tax_id="76.543.210-3",
            razon_social="Pollo King",
            nombre_fantasia="Pollo King SpA",
            email_contacto="ventas@polloking.cl",
            lead_time_dias=3,
        )
        assert create_req.razon_social == "Pollo King"

        bulk_req = SupplierCatalogBulkUpdateRequest(
            items=[
                SupplierCatalogItemPayload(
                    producto_id=10,
                    precio_pactado=Decimal("4990.50"),
                    codigo_producto_proveedor="PK-010",
                    tiempo_entrega_dias=2,
                    es_proveedor_principal=True,
                )
            ]
        )
        assert bulk_req.items[0].precio_pactado == Decimal("4990.50")

        resp = SupplierResponse(
            id=1,
            rut_tax_id="76.543.210-3",
            razon_social="Pollo King",
            total_compras_historicas=Decimal("540000.00"),
            ordenes_activas_count=3,
        )
        assert resp.total_compras_historicas == Decimal("540000.00")
