"""
oppytec-backend/src/modules/invoices/domain/ports.py
Puertos de Arquitectura Limpia (Protocols) para el Módulo de Facturas y Contabilidad.
Define las interfaces abstractas que la capa de infraestructura implementará (DIP - Dependency Inversion Principle).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.invoices.domain.entities import (
    Invoice,
    InvoiceAuditFlag,
    SupplierProductAlias,
)
from src.modules.invoices.domain.value_objects import (
    InvoiceStatus,
)


@runtime_checkable
class InvoiceRepositoryPort(Protocol):
    """Puerto de persistencia para el agregado Invoice y sus líneas asociadas."""

    async def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Obtiene una factura por su identificador único."""
        ...

    async def get_by_file_hash(self, tenant_id: str, file_hash_sha256: str) -> Invoice | None:
        """Busca una factura por el hash SHA-256 del archivo para deduplicación."""
        ...

    async def save(self, invoice: Invoice) -> Invoice:
        """Persiste una factura nueva o actualiza una existente con sus líneas y flags."""
        ...

    async def list(
        self,
        tenant_id: str,
        status: InvoiceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invoice]:
        """Obtiene el listado paginado de facturas filtradas por tenant y estado opcional."""
        ...

    async def delete(self, invoice_id: UUID) -> bool:
        """Elimina una factura del repositorio."""
        ...


@runtime_checkable
class SupplierAliasRepositoryPort(Protocol):
    """Puerto de persistencia para la memoria de aliases de productos de proveedores."""

    async def find_by_vendor_name(
        self,
        tenant_id: str,
        supplier_id: UUID | None,
        raw_vendor_product_name: str,
    ) -> SupplierProductAlias | None:
        """Busca un alias exacto o difuso dado el nombre del producto en la factura del proveedor."""
        ...

    async def save_alias(self, alias: SupplierProductAlias) -> SupplierProductAlias:
        """Guarda o actualiza un mapeo de alias de proveedor."""
        ...

    async def list_by_supplier(
        self,
        tenant_id: str,
        supplier_id: UUID,
    ) -> list[SupplierProductAlias]:
        """Obtiene todos los alias conocidos para un proveedor determinado."""
        ...


@runtime_checkable
class InvoiceStoragePort(Protocol):
    """Puerto para almacenamiento binario seguro de archivos PDF e imágenes (Cloudflare R2 / S3)."""

    async def upload_file(
        self,
        tenant_id: str,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Almacena el archivo en el bucket aislado y retorna la clave de almacenamiento (file_path)."""
        ...

    async def get_presigned_url(
        self,
        file_path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Genera una URL firmada temporal de solo lectura para el visor de facturas."""
        ...

    async def delete_file(self, file_path: str) -> bool:
        """Elimina el archivo del almacenamiento."""
        ...


@runtime_checkable
class DTEValidatorPort(Protocol):
    """Puerto para validación tributaria de DTEs y reglas fiscales oficiales."""

    async def validate_dte(self, invoice: Invoice) -> list[InvoiceAuditFlag]:
        """Verifica la coherencia fiscal del DTE contra reglas de negocio y del SII."""
        ...
