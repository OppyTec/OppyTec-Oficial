"""
oppytec-backend/src/modules/operations/presentation/schemas_approvals.py
Contratos Pydantic v2 para el Centro de Aprobaciones, Auditorías de Buffet y Gobernanza:
Cumple Zero-Float (Decimal), validaciones deterministas y respuestas RFC 7807.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SolicitudAprobacionCreateRequest(BaseModel):
    """Payload para emitir una nueva solicitud de aprobación operacional."""

    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(..., min_length=2, max_length=50, description="Tipo canónico de aprobación")
    detalles: dict[str, Any] = Field(default_factory=dict, description="Payload estructurado de la solicitud")
    bodega_id: int | None = Field(default=None, description="Bodega asociada si aplica impacto en stock")
    area_operativa_id: int | None = Field(default=None, description="Área operativa solicitante")


class SolicitudAprobacionItemResponse(BaseModel):
    """Representación individual de una solicitud de aprobación en bandeja o historial."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tipo: str
    categoria: str
    estado: str
    usuario_id: int
    bodega_id: int | None = None
    area_operativa_id: int | None = None
    detalles: dict[str, Any] = Field(default_factory=dict)
    resuelto_por: int | None = None
    motivo_rechazo: str | None = None
    created_at: datetime
    resuelto_at: datetime | None = None


class SolicitudAprobacionListResponse(BaseModel):
    """Listado paginado de solicitudes de aprobación con metadatos."""

    model_config = ConfigDict(from_attributes=True)

    items: list[SolicitudAprobacionItemResponse]
    total: int
    page: int
    page_size: int


class PendingCountByCategory(BaseModel):
    """Desglose de pendientes por las 4 categorías funcionales canónicas."""

    operaciones: int = 0
    inventario: int = 0
    compras: int = 0
    equipo: int = 0


class PendingCountResponse(BaseModel):
    """Conteo ultraliviano para el Navbar (campana) y el Sidebar."""

    total_pending: int
    by_category: PendingCountByCategory
    area_id: str | None = None


class AprobarSolicitudRequest(BaseModel):
    """Payload de aprobación con soporte opcional para edición inline antes de confirmar."""

    model_config = ConfigDict(extra="forbid")

    edited_details: dict[str, Any] | None = Field(
        default=None,
        description="Detalles modificados antes de la aprobación definitiva (ej. cantidad ajustada)",
    )


class RechazarSolicitudRequest(BaseModel):
    """Payload obligatorio para rechazar una solicitud."""

    model_config = ConfigDict(extra="forbid")

    motivo_rechazo: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Justificación obligatoria del rechazo (mínimo 5 caracteres)",
    )


class BuffetItemResolutionRequest(BaseModel):
    """Resolución granular de un insumo de buffet (retorno a bodega vs merma)."""

    model_config = ConfigDict(extra="forbid")

    item_id: Any | None = None
    producto_id: int | None = None
    item_type: str = "insumo"
    nombre: str = ""
    cantidad: Decimal = Field(default=Decimal("0.00"), description="Cantidad consumida neta")
    cantidad_sobrante: Decimal = Field(default=Decimal("0.00"), description="Cantidad de sobrante")
    accion_sobrante: str = Field(default="retornar", description="'retornar' o 'merma'")
    motivo_merma: str | None = None


class BuffetResolveRequest(BaseModel):
    """Payload para resolver la auditoría de sesión de buffet."""

    model_config = ConfigDict(extra="forbid")

    accion: str = Field(default="aprobar", description="'aprobar' o 'rechazar'")
    motivo_rechazo: str | None = Field(default=None, description="Obligatorio si accion es 'rechazar'")
    items_override: list[BuffetItemResolutionRequest] | None = Field(
        default=None,
        description="Resolución ítem por ítem con asignación de retorno o merma",
    )


class BuffetApprovalDetailResponse(BaseModel):
    """Resumen completo de la sesión de buffet para inspección pre-resolución."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tipo: str
    estado: str
    usuario_id: int
    bodega_id: int | None = None
    area_operativa_id: int | None = None
    detalles: dict[str, Any] = Field(default_factory=dict)
    resuelto_por: int | None = None
    motivo_rechazo: str | None = None
    created_at: datetime
    resuelto_at: datetime | None = None


class NotificationMatrixRuleItem(BaseModel):
    """Regla individual de despacho y suscripción a alertas."""

    model_config = ConfigDict(from_attributes=True)

    cargo: str
    tipo_solicitud: str
    canal_in_app: bool = True
    canal_email: bool = False
    canal_push: bool = False
    es_aprobador: bool = False


class NotificationMatrixUpdateRequest(BaseModel):
    """Guardado masivo de la matriz de gobernanza."""

    model_config = ConfigDict(extra="forbid")

    rules: list[NotificationMatrixRuleItem]


class CargoMatrixItemResponse(BaseModel):
    """Cargo con sus preferencias consolidadas para la vista de gobernanza."""

    id: int
    name: str
    role_name: str
    description: str | None = None
    is_system: bool = True
    notification_permissions: dict[str, bool] = Field(default_factory=dict)


class NotificationCatalogItemResponse(BaseModel):
    """Ficha informativa de cada tipo de notificación."""

    type: str
    label: str
    category: str
    description: str


class NotificationMatrixResponse(BaseModel):
    """Matriz completa retornada al frontend para renderizar NotificationMatrixView."""

    catalog: list[NotificationCatalogItemResponse]
    cargos: list[CargoMatrixItemResponse]
    rules: list[NotificationMatrixRuleItem]
    is_admin: bool = True


class CargoPermissionUpdateRequest(BaseModel):
    """Actualización de permisos de notificación para un cargo específico."""

    model_config = ConfigDict(extra="forbid")

    notification_permissions: dict[str, bool]


class UserPreferencesUpdateRequest(BaseModel):
    """Actualización de preferencias personales del usuario actual."""

    model_config = ConfigDict(extra="forbid")

    preferences: dict[str, bool]
