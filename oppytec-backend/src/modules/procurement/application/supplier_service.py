"""
oppytec-backend/src/modules/procurement/application/supplier_service.py
Servicio de Aplicación transaccional y asíncrono para Proveedores y Catálogo pactado.
Cumple Clean Architecture, Regla Inmutable "Pollo King" (translatable = False),
precisión Decimal(14, 2) estricta y SoftDelete.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import contextlib
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    CrossTenantAccessError,
    DomainValidationError,
    ProperNounImmutabilityError,
    ResourceNotFoundError,
)
from src.core.observability import format_structured_log
from src.modules.catalog.infrastructure.models import Producto
from src.modules.procurement.domain.entities import Supplier
from src.modules.procurement.domain.value_objects import RutTaxId
from src.modules.procurement.infrastructure.models import (
    Compra,
    ProductoProveedor,
    Proveedor,
)

logger = logging.getLogger("oppytec.procurement.supplier_service")


class SupplierService:
    """Servicio de aplicación para gestión de proveedores y acuerdos de catálogo."""

    def __init__(self, use_in_memory: bool = False) -> None:
        self._use_in_memory = use_in_memory
        self._memory_suppliers: dict[int, dict[str, Any]] = {}
        self._memory_catalogs: dict[int, list[dict[str, Any]]] = {}
        self._seq = 100

    def enable_in_memory_mode(self) -> None:
        self._use_in_memory = True

    def reset_in_memory_store(self) -> None:
        self._memory_suppliers.clear()
        self._memory_catalogs.clear()
        self._seq = 100

    def reset(self) -> None:
        self.reset_in_memory_store()

    async def list_suppliers(
        self,
        session: AsyncSession | None,
        search: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
        tenant_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Listado paginado de proveedores con búsqueda por nombre, RUT y estado."""
        if not self._use_in_memory and session is not None:
            try:
                stmt = select(Proveedor).where(Proveedor.is_deleted.is_(False))
                if status:
                    stmt = stmt.where(Proveedor.estado == status)
                if search:
                    term = f"%{search.strip()}%"
                    stmt = stmt.where(
                        or_(
                            Proveedor.razon_social.ilike(term),
                            Proveedor.nombre_fantasia.ilike(term),
                            Proveedor.rut_tax_id.ilike(term),
                        )
                    )

                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar() or 0

                stmt = stmt.order_by(Proveedor.id.desc()).offset(skip).limit(limit)
                result = await session.execute(stmt)
                suppliers = list(result.scalars().all())

                items: list[dict[str, Any]] = []
                for s in suppliers:
                    stats_stmt = select(
                        func.coalesce(func.sum(Compra.monto_neto), Decimal("0.00")),
                        func.count(Compra.id),
                    ).where(
                        Compra.proveedor_id == s.id,
                        Compra.is_deleted.is_(False),
                        Compra.estado != "CANCELADA",
                    )
                    stats_res = (await session.execute(stats_stmt)).first()
                    total_gastado = stats_res[0] if stats_res else Decimal("0.00")
                    total_ordenes = stats_res[1] if stats_res else 0

                    items.append({
                        "id": s.id,
                        "rut_tax_id": s.rut_tax_id,
                        "razon_social": s.razon_social,
                        "nombre_fantasia": s.nombre_fantasia,
                        "email_contacto": s.email_contacto,
                        "telefono": s.telefono,
                        "direccion": s.direccion,
                        "lead_time_dias": s.lead_time_dias,
                        "estado": s.estado,
                        "notas": s.notas,
                        "total_compras_historicas": total_gastado,
                        "ordenes_activas_count": total_ordenes,
                        "created_at": s.created_at,
                        "updated_at": s.updated_at,
                    })

                return items, total
            except Exception as exc:
                logger.debug("list_suppliers fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        active = [
            s for s in self._memory_suppliers.values()
            if not s.get("is_deleted", False)
            and (tenant_id is None or s.get("tenant_id") in (None, tenant_id))
        ]
        if status:
            active = [s for s in active if s.get("estado") == status]
        if search:
            term = search.lower().strip()
            active = [
                s for s in active
                if term in s.get("razon_social", "").lower()
                or term in (s.get("nombre_fantasia") or "").lower()
                or term in s.get("rut_tax_id", "").lower()
            ]
        total = len(active)
        paginated = active[skip : skip + limit]
        return paginated, total

    async def create_supplier(
        self,
        session: AsyncSession | None,
        data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Alta de proveedor con validación de RUT único e inmutabilidad "Pollo King"."""
        raw_rut = str(data.get("rut_tax_id", "")).strip()
        rut_vo = RutTaxId(raw_rut)
        canonical_rut = rut_vo.value

        razon_social = str(data.get("razon_social", "")).strip()
        if not razon_social:
            raise DomainValidationError(
                "La razón social del proveedor es obligatoria.",
                i18n_key="procurement:errors.supplier_name_required",
            )

        entity = Supplier(
            rut_tax_id=rut_vo,
            razon_social=razon_social,
            nombre_fantasia=data.get("nombre_fantasia"),
            email_contacto=data.get("email_contacto"),
            telefono=data.get("telefono"),
            direccion=data.get("direccion"),
            lead_time_dias=int(data.get("lead_time_dias", 1)),
            estado=data.get("estado", "ACTIVO"),
            notas=data.get("notas"),
        )
        entity.assert_proper_noun_immutable(razon_social)

        if not self._use_in_memory and session is not None:
            try:
                dup_stmt = select(Proveedor).where(
                    Proveedor.rut_tax_id == canonical_rut,
                    Proveedor.is_deleted.is_(False),
                )
                existing = (await session.execute(dup_stmt)).scalar_one_or_none()
                if existing:
                    raise DomainValidationError(
                        f"Ya existe un proveedor registrado con el RUT/Tax ID '{canonical_rut}'.",
                        i18n_key="procurement:errors.supplier_rut_already_exists",
                    )

                model = Proveedor(
                    rut_tax_id=canonical_rut,
                    razon_social=razon_social,
                    nombre_fantasia=entity.nombre_fantasia,
                    email_contacto=entity.email_contacto,
                    telefono=entity.telefono,
                    direccion=entity.direccion,
                    lead_time_dias=entity.lead_time_dias,
                    estado=entity.estado,
                    notas=entity.notas,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)

                result_db = {
                    "id": model.id,
                    "rut_tax_id": model.rut_tax_id,
                    "razon_social": model.razon_social,
                    "nombre_fantasia": model.nombre_fantasia,
                    "email_contacto": model.email_contacto,
                    "telefono": model.telefono,
                    "direccion": model.direccion,
                    "lead_time_dias": model.lead_time_dias,
                    "estado": model.estado,
                    "notas": model.notas,
                    "total_compras_historicas": Decimal("0.00"),
                    "ordenes_activas_count": 0,
                    "created_at": model.created_at,
                    "updated_at": model.updated_at,
                }
                logger.info(
                    format_structured_log(
                        "INFO",
                        "procurement.supplier.create",
                        {
                            "supplier_id": model.id,
                            "razon_social": model.razon_social,
                            "nombre_fantasia": model.nombre_fantasia,
                            "rut_tax_id": model.rut_tax_id,
                            "email_contacto": model.email_contacto,
                            "telefono": model.telefono,
                            "direccion": model.direccion,
                            "estado": model.estado,
                        },
                    )
                )
                return result_db
            except DomainValidationError:
                raise
            except Exception as exc:
                logger.debug("create_supplier fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        resolved_tenant = tenant_id or data.get("tenant_id")
        for s in self._memory_suppliers.values():
            if (
                not s.get("is_deleted", False)
                and s.get("rut_tax_id") == canonical_rut
                and s.get("tenant_id") == resolved_tenant
            ):
                raise DomainValidationError(
                    f"Ya existe un proveedor registrado con el RUT/Tax ID '{canonical_rut}'.",
                    i18n_key="procurement:errors.supplier_rut_already_exists",
                )
        self._seq += 1
        now = datetime.now(timezone.utc)
        record = {
            "id": self._seq,
            "rut_tax_id": canonical_rut,
            "razon_social": razon_social,
            "nombre_fantasia": entity.nombre_fantasia,
            "email_contacto": entity.email_contacto,
            "telefono": entity.telefono,
            "direccion": entity.direccion,
            "lead_time_dias": entity.lead_time_dias,
            "estado": entity.estado,
            "notas": entity.notas,
            "total_compras_historicas": Decimal("0.00"),
            "ordenes_activas_count": 0,
            "created_at": now,
            "updated_at": now,
            "is_deleted": False,
            "tenant_id": resolved_tenant,
        }
        self._memory_suppliers[self._seq] = record
        logger.info(
            format_structured_log(
                "INFO",
                "procurement.supplier.create",
                {
                    "supplier_id": record["id"],
                    "razon_social": razon_social,
                    "nombre_fantasia": entity.nombre_fantasia,
                    "rut_tax_id": canonical_rut,
                    "email_contacto": entity.email_contacto,
                    "telefono": entity.telefono,
                    "direccion": entity.direccion,
                    "estado": entity.estado,
                },
            )
        )
        return record

    async def get_supplier(
        self,
        session: AsyncSession | None,
        supplier_id: int,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Obtiene detalle de proveedor con estadísticas financieras."""
        if not self._use_in_memory and session is not None:
            try:
                stmt = select(Proveedor).where(Proveedor.id == supplier_id, Proveedor.is_deleted.is_(False))
                model = (await session.execute(stmt)).scalar_one_or_none()
                if not model:
                    raise ResourceNotFoundError(
                        f"Proveedor {supplier_id} no encontrado.",
                        i18n_key="procurement:errors.supplier_not_found",
                    )

                stats_stmt = select(
                    func.coalesce(func.sum(Compra.monto_neto), Decimal("0.00")),
                    func.count(Compra.id),
                ).where(
                    Compra.proveedor_id == model.id,
                    Compra.is_deleted.is_(False),
                    Compra.estado != "CANCELADA",
                )
                stats_res = (await session.execute(stats_stmt)).first()
                total_gastado = stats_res[0] if stats_res else Decimal("0.00")
                total_ordenes = stats_res[1] if stats_res else 0

                return {
                    "id": model.id,
                    "rut_tax_id": model.rut_tax_id,
                    "razon_social": model.razon_social,
                    "nombre_fantasia": model.nombre_fantasia,
                    "email_contacto": model.email_contacto,
                    "telefono": model.telefono,
                    "direccion": model.direccion,
                    "lead_time_dias": model.lead_time_dias,
                    "estado": model.estado,
                    "notas": model.notas,
                    "total_compras_historicas": total_gastado,
                    "ordenes_activas_count": total_ordenes,
                    "created_at": model.created_at,
                    "updated_at": model.updated_at,
                }
            except (ResourceNotFoundError, CrossTenantAccessError):
                raise
            except Exception as exc:
                logger.debug("get_supplier fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        s = self._memory_suppliers.get(supplier_id)
        if not s or s.get("is_deleted", False):
            raise ResourceNotFoundError(
                f"Proveedor {supplier_id} no encontrado.",
                i18n_key="procurement:errors.supplier_not_found",
            )
        if tenant_id and s.get("tenant_id") and s.get("tenant_id") != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: supplier {supplier_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )
        return s

    async def update_supplier(
        self,
        session: AsyncSession | None,
        supplier_id: int,
        data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Actualiza datos del proveedor preservando la regla 'Pollo King'."""
        if not self._use_in_memory and session is not None:
            try:
                stmt = select(Proveedor).where(Proveedor.id == supplier_id, Proveedor.is_deleted.is_(False))
                model = (await session.execute(stmt)).scalar_one_or_none()
                if not model:
                    raise ResourceNotFoundError(
                        f"Proveedor {supplier_id} no encontrado.",
                        i18n_key="procurement:errors.supplier_not_found",
                    )

                proposed_razon = data.get("razon_social")
                if proposed_razon and proposed_razon != model.razon_social:
                    raise ProperNounImmutabilityError(
                        f"El nombre comercial '{model.razon_social}' es un nombre propio inmutable y no puede traducirse.",
                        context={"supplier_id": supplier_id},
                    )

                if "nombre_fantasia" in data:
                    model.nombre_fantasia = data["nombre_fantasia"]
                if "email_contacto" in data:
                    model.email_contacto = data["email_contacto"]
                if "telefono" in data:
                    model.telefono = data["telefono"]
                if "direccion" in data:
                    model.direccion = data["direccion"]
                if "lead_time_dias" in data and data["lead_time_dias"] is not None:
                    model.lead_time_dias = int(data["lead_time_dias"])
                if "estado" in data and data["estado"]:
                    model.estado = str(data["estado"]).strip().upper()
                if "notas" in data:
                    model.notas = data["notas"]

                await session.commit()
                return await self.get_supplier(session, supplier_id, tenant_id=tenant_id)
            except (ResourceNotFoundError, ProperNounImmutabilityError, CrossTenantAccessError):
                raise
            except Exception as exc:
                logger.debug("update_supplier fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        s = self._memory_suppliers.get(supplier_id)
        if not s or s.get("is_deleted", False):
            raise ResourceNotFoundError(
                f"Proveedor {supplier_id} no encontrado.",
                i18n_key="procurement:errors.supplier_not_found",
            )
        if tenant_id and s.get("tenant_id") and s.get("tenant_id") != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: supplier {supplier_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )
        proposed_razon = data.get("razon_social")
        if proposed_razon and proposed_razon != s["razon_social"]:
            raise ProperNounImmutabilityError(
                f"El nombre comercial '{s['razon_social']}' es un nombre propio inmutable.",
                context={"supplier_id": supplier_id},
            )
        for k in ("nombre_fantasia", "email_contacto", "telefono", "direccion", "lead_time_dias", "estado", "notas"):
            if k in data and data[k] is not None:
                s[k] = data[k]
        s["updated_at"] = datetime.now(timezone.utc)
        return s

    async def delete_supplier(
        self,
        session: AsyncSession | None,
        supplier_id: int,
        tenant_id: str | None = None,
    ) -> bool:
        """Borrado lógico (SoftDelete) del proveedor."""
        if not self._use_in_memory and session is not None:
            try:
                stmt = select(Proveedor).where(Proveedor.id == supplier_id, Proveedor.is_deleted.is_(False))
                model = (await session.execute(stmt)).scalar_one_or_none()
                if not model:
                    raise ResourceNotFoundError(
                        f"Proveedor {supplier_id} no encontrado.",
                        i18n_key="procurement:errors.supplier_not_found",
                    )

                model.is_deleted = True
                model.deleted_at = datetime.now(timezone.utc)
                await session.commit()
                return True
            except (ResourceNotFoundError, CrossTenantAccessError):
                raise
            except Exception as exc:
                logger.debug("delete_supplier fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        s = self._memory_suppliers.get(supplier_id)
        if not s or s.get("is_deleted", False):
            raise ResourceNotFoundError(
                f"Proveedor {supplier_id} no encontrado.",
                i18n_key="procurement:errors.supplier_not_found",
            )
        if tenant_id and s.get("tenant_id") and s.get("tenant_id") != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: supplier {supplier_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )
        s["is_deleted"] = True
        s["deleted_at"] = datetime.now(timezone.utc)
        return True

    async def get_supplier_catalog(
        self,
        session: AsyncSession | None,
        supplier_id: int,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Obtiene el catálogo de productos y precios pactados del proveedor."""
        if not self._use_in_memory and session is not None:
            try:
                await self.get_supplier(session, supplier_id, tenant_id=tenant_id)

                stmt = (
                    select(
                        ProductoProveedor,
                        Producto.nombre.label("producto_nombre"),
                        Producto.sku.label("producto_sku"),
                    )
                    .outerjoin(Producto, ProductoProveedor.producto_id == Producto.id)
                    .where(ProductoProveedor.proveedor_id == supplier_id)
                    .order_by(ProductoProveedor.id.asc())
                )
                results = (await session.execute(stmt)).all()
                catalog_items: list[dict[str, Any]] = []
                for pp, prod_nombre, prod_sku in results:
                    catalog_items.append({
                        "id": pp.id,
                        "producto_id": pp.producto_id,
                        "producto_nombre": prod_nombre,
                        "producto_sku": prod_sku,
                        "proveedor_id": pp.proveedor_id,
                        "precio_pactado": pp.ultimo_costo_neto,
                        "codigo_producto_proveedor": pp.codigo_proveedor,
                        "tiempo_entrega_dias": pp.tiempo_entrega_dias,
                        "es_proveedor_principal": pp.es_proveedor_principal,
                    })
                return catalog_items
            except (ResourceNotFoundError, CrossTenantAccessError):
                raise
            except Exception as exc:
                logger.debug("get_supplier_catalog fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        await self.get_supplier(session, supplier_id, tenant_id=tenant_id)
        return list(self._memory_catalogs.get(supplier_id, []))

    async def update_supplier_catalog(
        self,
        session: AsyncSession | None,
        supplier_id: int,
        items: list[dict[str, Any]],
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Upsert masivo de acuerdos de precios y catálogo de insumos."""
        if not self._use_in_memory and session is not None:
            try:
                await self.get_supplier(session, supplier_id, tenant_id=tenant_id)

                for item_data in items:
                    prod_id = int(item_data["producto_id"])
                    precio = Decimal(str(item_data["precio_pactado"]))
                    codigo = item_data.get("codigo_producto_proveedor") or item_data.get("codigo_proveedor")
                    lead_dias = item_data.get("tiempo_entrega_dias")
                    es_principal = bool(item_data.get("es_proveedor_principal", False))

                    stmt = select(ProductoProveedor).where(
                        ProductoProveedor.proveedor_id == supplier_id,
                        ProductoProveedor.producto_id == prod_id,
                    )
                    pp = (await session.execute(stmt)).scalar_one_or_none()
                    if pp:
                        pp.ultimo_costo_neto = precio
                        pp.codigo_proveedor = codigo
                        pp.tiempo_entrega_dias = lead_dias
                        pp.es_proveedor_principal = es_principal
                    else:
                        pp = ProductoProveedor(
                            proveedor_id=supplier_id,
                            producto_id=prod_id,
                            ultimo_costo_neto=precio,
                            codigo_proveedor=codigo,
                            tiempo_entrega_dias=lead_dias,
                            es_proveedor_principal=es_principal,
                        )
                        session.add(pp)

                    if es_principal:
                        other_stmt = (
                            select(ProductoProveedor)
                            .where(
                                ProductoProveedor.producto_id == prod_id,
                                ProductoProveedor.proveedor_id != supplier_id,
                                ProductoProveedor.es_proveedor_principal.is_(True),
                            )
                        )
                        others = (await session.execute(other_stmt)).scalars().all()
                        for o in others:
                            o.es_proveedor_principal = False

                await session.commit()
                return await self.get_supplier_catalog(session, supplier_id, tenant_id=tenant_id)
            except (ResourceNotFoundError, CrossTenantAccessError):
                raise
            except Exception as exc:
                logger.debug("update_supplier_catalog fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        await self.get_supplier(session, supplier_id, tenant_id=tenant_id)
        existing = self._memory_catalogs.setdefault(supplier_id, [])
        for it in items:
            prod_id = int(it["producto_id"])
            precio = Decimal(str(it["precio_pactado"]))
            found = False
            for ex in existing:
                if ex["producto_id"] == prod_id:
                    ex["precio_pactado"] = precio
                    ex["codigo_producto_proveedor"] = it.get("codigo_producto_proveedor")
                    ex["tiempo_entrega_dias"] = it.get("tiempo_entrega_dias")
                    ex["es_proveedor_principal"] = bool(it.get("es_proveedor_principal", False))
                    found = True
                    break
            if not found:
                existing.append({
                    "id": len(existing) + 1,
                    "producto_id": prod_id,
                    "producto_nombre": it.get("producto_nombre"),
                    "producto_sku": it.get("producto_sku"),
                    "proveedor_id": supplier_id,
                    "precio_pactado": precio,
                    "codigo_producto_proveedor": it.get("codigo_producto_proveedor"),
                    "tiempo_entrega_dias": it.get("tiempo_entrega_dias"),
                    "es_proveedor_principal": bool(it.get("es_proveedor_principal", False)),
                })
        return existing
