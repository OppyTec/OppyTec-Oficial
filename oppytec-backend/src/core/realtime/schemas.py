"""
oppytec-backend/src/core/realtime/schemas.py
Contratos tipados para el Motor de Tiempo Real (`/api/v1/ws/realtime`) con Redis Pub/Sub + Streams,
aislamiento por canal `rt:{env_ns}:{holding_id}:{tenant_id}` y validación de permisos RBAC de 3 niveles.
"""
from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

THREE_LEVEL_PERMISSION_REGEX: re.Pattern[str] = re.compile(
    r"^(?:[a-z0-9_]+|\*)\.(?:[a-z0-9_]+|\*)\.(?:[a-z0-9_]+|\*)$"
)
HighlightEffectType = Literal["blink-green", "blink-orange", "blink-red"]


def validate_three_level_permission_code(permission: str) -> str:
    """
    Valida que un código de permiso cumpla estrictamente la jerarquía de 3 niveles:
    `<modulo>.<submodulo>.<funcion>` (ej. `inventory.mermas.approve`).
    """
    cleaned = permission.strip().lower()
    if not THREE_LEVEL_PERMISSION_REGEX.match(cleaned):
        raise ValueError(
            f"El permiso RBAC '{permission}' debe cumplir el formato de 3 niveles "
            "'<modulo>.<submodulo>.<funcion>'."
        )
    return cleaned


def build_realtime_channel(
    env_ns: str,
    holding_id: UUID | None,
    tenant_id: UUID | None,
) -> str:
    """
    Construye el identificador físico de canal en Redis Pub/Sub aislado por entorno y sucursal:
    `rt:{env_ns}:{holding_id}:{tenant_id}` o `rt:{env_ns}:public:admin` para eventos de plataforma.
    """
    clean_ns = env_ns.strip() or "default"
    if holding_id is None or tenant_id is None:
        return f"rt:{clean_ns}:public:admin"
    return f"rt:{clean_ns}:{holding_id}:{tenant_id}"


def build_realtime_stream_key(
    env_ns: str,
    holding_id: UUID | None,
    tenant_id: UUID | None,
) -> str:
    """Construye la clave del Redis Stream para catch-up tras micro-cortes de red móvil."""
    return f"{build_realtime_channel(env_ns, holding_id, tenant_id)}:stream"


def parse_stream_event_id(event_id: str) -> tuple[int, int]:
    """
    Convierte un ID secuencial de Redis Stream (`"<timestamp_ms>-<seq>"`) en una tupla comparable `(ms, seq)`.
    """
    cleaned = event_id.strip()
    if "-" not in cleaned:
        raise ValueError(f"Formato de event_id de Redis Stream inválido: {event_id!r}")
    ms_part, seq_part = cleaned.split("-", 1)
    return (int(ms_part), int(seq_part))


class RealtimeEventEnvelope(BaseModel):  # type: ignore[explicit-any]
    """
    Sobre de evento en tiempo real transmitido por Redis Pub/Sub + Redis Streams y filtrado en servidor.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(
        default="0-0",
        description="ID secuencial de Redis Stream (ej. '1729271000123-0')",
    )
    event_type: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="Tipo de evento de dominio o sistema (ej. 'inventory.mermas.approval_requested' o 'SESSION_REVOKED')",
    )
    holding_id: UUID | None = None
    tenant_id: UUID | None = None
    required_permission: str | None = Field(
        default=None,
        description="Permiso RBAC de 3 niveles '<modulo>.<submodulo>.<funcion>' exigido para recibir este evento",
    )
    target_user_ids: list[int] | None = None
    target_bodega_id: int | None = None
    query_keys_to_invalidate: list[list[str]] = Field(default_factory=list)
    payload: dict[str, object] = Field(default_factory=dict)
    i18n_toast_key: str | None = None
    i18n_toast_params: dict[str, object] = Field(default_factory=dict)
    ui_highlight_effect: HighlightEffectType | None = None
    trace_id: str = Field(default="00000000000000000000000000000000")

    @field_validator("required_permission")
    @classmethod
    def check_three_level_permission(cls, value: str | None) -> str | None:
        """Garantiza que `required_permission`, cuando se define, tenga formato de 3 niveles."""
        if value is None:
            return None
        return validate_three_level_permission_code(value)
