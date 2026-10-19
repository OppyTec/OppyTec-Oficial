"""
oppytec-backend/src/modules/identity/infrastructure/models.py
Modelos SQLAlchemy 2.0 para Identidad y RBAC Dual:
- `PublicBase` (`public`): `GlobalUser`, `GlobalRole`, `GlobalPermission`, `GlobalUserPermissionGrant`.
- `TenantBase` (`tenant_*`): `Role`, `Cargo`, `Permission`, `UserTenantRole`, `UserPermissionGrant` (JIT).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    PublicBase,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class GlobalUser(PublicBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Trabajador global de OppyTec en el esquema `public` (cupo ilimitado + soft-delete)."""

    __tablename__ = "global_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    is_superuser_god: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GlobalRole(PublicBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Rol global de trabajadores de OppyTec (`superuser=0`, `admin=10`, `supervisor=20`, `developer=30`)."""

    __tablename__ = "global_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    hierarchy_rank: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_system_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GlobalPermission(PublicBase, AuditTimestampsMixin):
    """Permiso de 3 niveles (`<modulo>.<submodulo>.<funcion>`) para el plano de control global."""

    __tablename__ = "global_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    module_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    submodule_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    action_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)


class GlobalUserPermissionGrant(PublicBase, AuditTimestampsMixin):
    """Concesión o denegación explícita (`ALLOW` | `DENY`) para un `GlobalUser` con vigencia opcional."""

    __tablename__ = "global_user_permission_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public.global_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    effect: Mapped[str] = mapped_column(String(16), default="ALLOW", nullable=False)
    granted_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public.global_users.id"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Role(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Rol editable dentro del esquema `tenant_*`
    (`propietario=0`, `superuser=5`, `admin=10`, `supervisor=20`, `cajero=30`, custom `> 30`).
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    hierarchy_rank: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_system_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Cargo(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Posición operativa del negocio vinculada a un `Role` con ícono y color del ADN visual."""

    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    icono: Mapped[str] = mapped_column(String(64), default="ChefHat", nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#007BFF", nullable=False)


class Permission(TenantBase, AuditTimestampsMixin):
    """Permiso operativo de 3 niveles (`<modulo>.<submodulo>.<funcion>`) dentro de `tenant_*`."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    module_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    submodule_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    action_slug: Mapped[str] = mapped_column(String(64), nullable=False)


class UserTenantRole(TenantBase, AuditTimestampsMixin):
    """Asignación del rol que ejerce un `client_user_id` dentro de un `tenant_*` específico."""

    __tablename__ = "user_tenant_roles"
    __table_args__ = (UniqueConstraint("client_user_id", "role_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cargo_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cargos.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    assigned_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)


class UserPermissionGrant(TenantBase, AuditTimestampsMixin):
    """Permiso temporal Just-In-Time (JIT) o excepción explícita (`ALLOW` | `DENY`) en `tenant_*`."""

    __tablename__ = "user_permission_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    effect: Mapped[str] = mapped_column(String(16), default="ALLOW", nullable=False)
    granted_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
