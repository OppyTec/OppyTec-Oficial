"""
oppytec-backend/src/modules/operations/domain/approvals.py
Capa de dominio pura DDD para el Centro de Aprobaciones y Gobernanza de Operaciones.
Aislada al 100% de SQLAlchemy, FastAPI y dependencias de infraestructura.
Cumple Regla 01 (Clean Architecture), Regla 02 (Zero-Float con Decimal) y Regla 15 (i18n).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from src.core.exceptions import OppyTecError

MONEY_QUANT: Decimal = Decimal("0.01")
ZERO_MONEY: Decimal = Decimal("0.00")
MIN_REJECTION_REASON_LENGTH: int = 5


class ApprovalDomainError(OppyTecError, ValueError):
    """Excepción base para violaciones de reglas de negocio en el Centro de Aprobaciones."""

    default_status_code = 400
    default_error_code = "APPROVAL_DOMAIN_ERROR"
    default_i18n_key = "operations:errors.approval_domain_error"
    default_title = "Approval Domain Error"


class InvalidApprovalTransitionError(ApprovalDomainError):
    """Transición de estado ilegal en una solicitud de aprobación."""

    default_status_code = 409
    default_error_code = "INVALID_APPROVAL_TRANSITION"
    default_i18n_key = "operations:errors.invalid_approval_transition"
    default_title = "Invalid Approval Transition"


class InvalidRejectionReasonError(ApprovalDomainError):
    """Motivo de rechazo inválido o insuficiente (mínimo 5 caracteres no vacíos)."""

    default_status_code = 422
    default_error_code = "INVALID_REJECTION_REASON"
    default_i18n_key = "operations:errors.invalid_rejection_reason"
    default_title = "Invalid Rejection Reason"


class ApprovalCategory(StrEnum):
    """Categorías funcionales canónicas de solicitudes de aprobación."""

    OPERACIONES = "operaciones"
    INVENTARIO = "inventario"
    COMPRAS = "compras"
    EQUIPO = "equipo"


class ApprovalType(StrEnum):
    """12 tipos canónicos de solicitudes de aprobación heredados de Legacy."""

    MERMA = "merma"
    MERMA_RECETA = "merma_receta"
    CONSUMO = "consumo"
    CONSUMO_BUFFET = "consumo_buffet"
    CONTEO = "conteo"
    PRODUCTO_BORRADOR_RECETA = "producto_borrador_receta"
    RECIBIR_PEDIDO = "recibir_pedido"
    SOLICITUD_COMPRA = "solicitud_compra"
    VINCULACION_PROVEEDOR = "vinculacion_proveedor"
    MENCION_NOTA = "mencion_nota"
    PERFIL = "perfil"
    COLOR_TURNO = "color_turno"


class ApprovalStatus(StrEnum):
    """Estados del ciclo de vida de una solicitud de aprobación."""

    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    APROBADO_TEMPORAL = "aprobado_temporal"


APPROVAL_TYPE_TO_CATEGORY: dict[ApprovalType, ApprovalCategory] = {
    ApprovalType.MERMA: ApprovalCategory.OPERACIONES,
    ApprovalType.MERMA_RECETA: ApprovalCategory.OPERACIONES,
    ApprovalType.CONSUMO: ApprovalCategory.OPERACIONES,
    ApprovalType.CONSUMO_BUFFET: ApprovalCategory.OPERACIONES,
    ApprovalType.CONTEO: ApprovalCategory.INVENTARIO,
    ApprovalType.PRODUCTO_BORRADOR_RECETA: ApprovalCategory.INVENTARIO,
    ApprovalType.RECIBIR_PEDIDO: ApprovalCategory.COMPRAS,
    ApprovalType.SOLICITUD_COMPRA: ApprovalCategory.COMPRAS,
    ApprovalType.VINCULACION_PROVEEDOR: ApprovalCategory.COMPRAS,
    ApprovalType.MENCION_NOTA: ApprovalCategory.EQUIPO,
    ApprovalType.PERFIL: ApprovalCategory.EQUIPO,
    ApprovalType.COLOR_TURNO: ApprovalCategory.EQUIPO,
}


def get_approval_category(tipo: ApprovalType | str) -> ApprovalCategory:
    """Mapeo canónico de un tipo de solicitud de aprobación a su categoría funcional."""
    if isinstance(tipo, str):
        try:
            tipo_enum = ApprovalType(tipo)
        except ValueError:
            raise ApprovalDomainError(
                f"Tipo de aprobación no reconocido: '{tipo}'",
                context={"tipo": str(tipo)},
            )
    elif isinstance(tipo, ApprovalType):
        tipo_enum = tipo
    else:
        raise ApprovalDomainError(
            f"Tipo de solicitud no válido: {type(tipo).__name__}",
        )
    return APPROVAL_TYPE_TO_CATEGORY[tipo_enum]


@dataclass(frozen=True)
class ApprovalRequestId:
    """Value Object inmutable para el identificador único de una solicitud."""

    value: UUID

    @classmethod
    def generate(cls) -> ApprovalRequestId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, val: str) -> ApprovalRequestId:
        return cls(UUID(val))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class MoneyAmount:
    """
    Value Object inmutable para montos financieros con precisión determinista Decimal.
    Cumple la prohibición estricta de números en punto flotante (Cero Float).
    """

    amount: Decimal = field(default=ZERO_MONEY)
    currency: str = "CLP"

    def __post_init__(self) -> None:
        raw_val = self.amount
        if not isinstance(raw_val, (Decimal, int, str)) or isinstance(raw_val, bool):
            raise TypeError(
                f"MoneyAmount no admite tipo {type(raw_val).__name__}, se requiere Decimal, int o str"
            )
        dec = Decimal(str(raw_val)) if not isinstance(raw_val, Decimal) else raw_val
        if dec.is_nan() or dec.is_infinite():
            raise ValueError(f"MoneyAmount no puede ser NaN o infinito: {dec}")

        quantized = dec.quantize(MONEY_QUANT, ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)
        object.__setattr__(self, "currency", self.currency.upper().strip())

    @classmethod
    def zero(cls, currency: str = "CLP") -> MoneyAmount:
        return cls(ZERO_MONEY, currency=currency)

    def to_decimal(self) -> Decimal:
        return self.amount


@dataclass
class ApprovalRequest:
    """
    Entidad de dominio pura que modela una solicitud de aprobación.
    Encapsula invariantes de negocio, transiciones de estado y auditoría.
    """

    tipo: ApprovalType
    usuario_id: int
    id: UUID = field(default_factory=uuid4)
    estado: ApprovalStatus = ApprovalStatus.PENDIENTE
    bodega_id: int | None = None
    area_operativa_id: int | None = None
    detalles: dict[str, Any] = field(default_factory=dict)
    resuelto_por: int | None = None
    motivo_rechazo: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resuelto_at: datetime | None = None
    monto_estimado: Decimal | None = None

    def __post_init__(self) -> None:
        # Validación de usuario solicitante
        if not isinstance(self.usuario_id, int) or isinstance(self.usuario_id, bool) or self.usuario_id <= 0:
            raise ApprovalDomainError(
                "usuario_id debe ser un entero positivo válido",
                context={"usuario_id": str(self.usuario_id)},
            )

        # Normalización de tipo
        if isinstance(self.tipo, str):
            try:
                object.__setattr__(self, "tipo", ApprovalType(self.tipo))
            except ValueError:
                raise ApprovalDomainError(
                    f"Tipo de aprobación '{self.tipo}' no es válido",
                    context={"tipo": str(self.tipo)},
                )

        # Normalización de estado
        if isinstance(self.estado, str):
            try:
                object.__setattr__(self, "estado", ApprovalStatus(self.estado))
            except ValueError:
                raise ApprovalDomainError(
                    f"Estado de aprobación '{self.estado}' no es válido",
                    context={"estado": str(self.estado)},
                )

        # Normalización de id
        if isinstance(self.id, str):
            try:
                object.__setattr__(self, "id", UUID(self.id))
            except ValueError:
                raise ApprovalDomainError(
                    f"id de aprobación no es un UUID válido: '{self.id}'",
                    context={"id": str(self.id)},
                )
        elif isinstance(self.id, ApprovalRequestId):
            object.__setattr__(self, "id", self.id.value)

        # Normalización y validación estricta de monto_estimado (Zero-Float)
        if self.monto_estimado is not None:
            raw_monto = self.monto_estimado
            if not isinstance(raw_monto, (Decimal, int, str)) or isinstance(raw_monto, bool):
                raise TypeError(
                    f"monto_estimado no admite tipo {type(raw_monto).__name__}, use Decimal"
                )
            dec_monto = Decimal(str(raw_monto)) if not isinstance(raw_monto, Decimal) else raw_monto
            if dec_monto.is_nan() or dec_monto.is_infinite():
                raise ValueError(f"monto_estimado no puede ser NaN o infinito: {dec_monto}")
            object.__setattr__(self, "monto_estimado", dec_monto.quantize(MONEY_QUANT, ROUND_HALF_UP))

        # Invariante de estado inicial si ya viene rechazado
        if self.estado == ApprovalStatus.RECHAZADO:
            self._validate_rejection_reason(self.motivo_rechazo)

    def _validate_rejection_reason(self, reason: str | None) -> str:
        clean_reason = reason.strip() if isinstance(reason, str) else ""
        if len(clean_reason) < MIN_REJECTION_REASON_LENGTH:
            raise InvalidRejectionReasonError(
                f"El motivo de rechazo debe contener al menos {MIN_REJECTION_REASON_LENGTH} caracteres no vacíos.",
                context={"solicitud_id": str(self.id), "longitud": str(len(clean_reason))},
            )
        return clean_reason

    @property
    def category(self) -> ApprovalCategory:
        """Categoría funcional canónica calculada a partir del tipo."""
        return get_approval_category(self.tipo)

    @property
    def is_pending(self) -> bool:
        """Indica si la solicitud está pendiente de resolución."""
        return self.estado == ApprovalStatus.PENDIENTE

    @property
    def is_approved(self) -> bool:
        """Indica si la solicitud ha sido aprobada de forma definitiva o temporal."""
        return self.estado in (ApprovalStatus.APROBADO, ApprovalStatus.APROBADO_TEMPORAL)

    @property
    def is_rejected(self) -> bool:
        """Indica si la solicitud ha sido rechazada."""
        return self.estado == ApprovalStatus.RECHAZADO

    @property
    def is_resolved(self) -> bool:
        """Indica si la solicitud ya concluyó su evaluación."""
        return self.estado != ApprovalStatus.PENDIENTE

    def approve(self, actor_id: int, resolved_at: datetime | None = None) -> None:
        """
        Aprueba la solicitud de forma definitiva.
        Invariante: Solo solicitudes en estado PENDIENTE pueden transicionar a APROBADO.
        """
        if self.estado != ApprovalStatus.PENDIENTE:
            raise InvalidApprovalTransitionError(
                f"Transición inválida: la solicitud {self.id} está en estado '{self.estado.value}' "
                f"y solo solicitudes en estado 'pendiente' pueden transicionar a 'aprobado'.",
                context={
                    "solicitud_id": str(self.id),
                    "estado_actual": self.estado.value,
                    "accion": "aprobar",
                },
            )

        if not isinstance(actor_id, int) or isinstance(actor_id, bool) or actor_id <= 0:
            raise ApprovalDomainError("actor_id debe ser un entero positivo válido de usuario resolutor.")

        self.estado = ApprovalStatus.APROBADO
        self.resuelto_por = actor_id
        self.resuelto_at = resolved_at or datetime.now(timezone.utc)

    def reject(self, actor_id: int, reason: str, resolved_at: datetime | None = None) -> None:
        """
        Rechaza la solicitud registrando obligatoriamente el motivo.
        Invariantes:
        - Solo solicitudes en estado PENDIENTE pueden transicionar a RECHAZADO.
        - El motivo de rechazo debe contener un mínimo de 5 caracteres no vacíos.
        """
        if self.estado != ApprovalStatus.PENDIENTE:
            raise InvalidApprovalTransitionError(
                f"Transición inválida: la solicitud {self.id} está en estado '{self.estado.value}' "
                f"y solo solicitudes en estado 'pendiente' pueden transicionar a 'rechazado'.",
                context={
                    "solicitud_id": str(self.id),
                    "estado_actual": self.estado.value,
                    "accion": "rechazar",
                },
            )

        if not isinstance(actor_id, int) or isinstance(actor_id, bool) or actor_id <= 0:
            raise ApprovalDomainError("actor_id debe ser un entero positivo válido de usuario resolutor.")

        clean_reason = self._validate_rejection_reason(reason)

        self.estado = ApprovalStatus.RECHAZADO
        self.motivo_rechazo = clean_reason
        self.resuelto_por = actor_id
        self.resuelto_at = resolved_at or datetime.now(timezone.utc)

    def approve_temporal(self, actor_id: int, resolved_at: datetime | None = None) -> None:
        """
        Aprueba la solicitud de forma temporal (e.g. desbloqueo operativo con revisión diferida).
        Invariante: Solo solicitudes en estado PENDIENTE pueden transicionar.
        """
        if self.estado != ApprovalStatus.PENDIENTE:
            raise InvalidApprovalTransitionError(
                f"Transición inválida: la solicitud {self.id} está en estado '{self.estado.value}' "
                f"y solo solicitudes en estado 'pendiente' pueden transicionar a 'aprobado_temporal'.",
                context={
                    "solicitud_id": str(self.id),
                    "estado_actual": self.estado.value,
                    "accion": "aprobar_temporal",
                },
            )

        if not isinstance(actor_id, int) or isinstance(actor_id, bool) or actor_id <= 0:
            raise ApprovalDomainError("actor_id debe ser un entero positivo válido de usuario resolutor.")

        self.estado = ApprovalStatus.APROBADO_TEMPORAL
        self.resuelto_por = actor_id
        self.resuelto_at = resolved_at or datetime.now(timezone.utc)


__all__ = [
    "ApprovalCategory",
    "ApprovalDomainError",
    "ApprovalRequest",
    "ApprovalRequestId",
    "ApprovalStatus",
    "ApprovalType",
    "InvalidApprovalTransitionError",
    "InvalidRejectionReasonError",
    "MoneyAmount",
    "get_approval_category",
]
