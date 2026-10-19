"""
oppytec-backend/src/modules/audit/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`) para el Doble Libro de Auditoría Forense Append-Only.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class RbacAuditCreateRequest(BaseModel):
    """Evento para agregar al libro `audit_rbac_changes`."""

    model_config = ConfigDict(extra="forbid")

    target_user_id: int | None = None
    action_type: str = Field(..., min_length=2, max_length=80)
    permission_or_role: str = Field(..., min_length=2, max_length=120)
    before_state: dict[str, str | int | bool] = Field(default_factory=dict)
    after_state: dict[str, str | int | bool] = Field(default_factory=dict)
    scope: Literal["public", "tenant"] = "tenant"

    @field_validator("action_type", "permission_or_role")
    @classmethod
    def _sanitize_fields(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="audit_field")


class RbacAuditResponse(BaseModel):
    """Registro inmutable del libro `audit_rbac_changes`."""

    model_config = ConfigDict(extra="forbid")

    event_uuid: str
    scope: Literal["public", "tenant"]
    actor_user_id: int
    target_user_id: int | None
    action_type: str
    permission_or_role: str
    occurred_at_iso: str


class ActivityAuditCreateRequest(BaseModel):
    """Evento para agregar al libro `audit_activity_log` con `authorization_lineage`."""

    model_config = ConfigDict(extra="forbid")

    action_code: str = Field(..., min_length=2, max_length=80)
    resource_type: str = Field(..., min_length=2, max_length=80)
    resource_id: str = Field(..., min_length=1, max_length=120)
    before_state: dict[str, str | int | bool] = Field(default_factory=dict)
    after_state: dict[str, str | int | bool] = Field(default_factory=dict)
    scope: Literal["public", "tenant"] = "tenant"

    @field_validator("action_code", "resource_type", "resource_id")
    @classmethod
    def _sanitize_activity_fields(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="activity_field")


class ActivityAuditResponse(BaseModel):
    """Registro inmutable del libro `audit_activity_log`."""

    model_config = ConfigDict(extra="forbid")

    event_uuid: str
    scope: Literal["public", "tenant"]
    actor_user_id: int
    action_code: str
    resource_type: str
    resource_id: str
    authorization_lineage: dict[str, object]
    occurred_at_iso: str
