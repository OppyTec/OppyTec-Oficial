"""
oppytec-backend/src/modules/tenancy/application/quota_service.py
Servicio de gestión de cupos de usuarios activos (`Seat Quotas`) por Plan con liberación
instantánea al aplicar `Soft-Delete` + invocación automática del `SessionKillSwitchService`.
"""
from __future__ import annotations

from dataclasses import replace

from src.core.exceptions import QuotaExceededError
from src.modules.identity.application.session_killswitch import (
    SessionKillSwitchResult,
    SessionKillSwitchService,
)
from src.modules.tenancy.domain.quotas import (
    ClientUserSeatState,
    QuotaResourceType,
    ResourceQuotaEvaluation,
    ResourceSlotState,
    SeatQuotaEvaluation,
    evaluate_resource_capacity_quota,
    evaluate_seat_quota_for_new_or_restored_user,
)


class SeatQuotaService:
    """
    Gobierna el ciclo de vida de los cupos de trabajadores por Holding/Tenant:
    - Creaciones y reactivaciones (`restore`) verifican `active_non_deleted_users < effective_max_users`.
    - `soft_delete_user` marca `is_deleted = True` (liberando el cupo en el acto) y dispara el Kill-Switch en Redis.
    """

    def __init__(
        self,
        *,
        plan_max_active_users: int,
        holding_override: int | None = None,
        tenant_override: int | None = None,
        killswitch_service: SessionKillSwitchService | None = None,
    ) -> None:
        self._plan_max_active_users = plan_max_active_users
        self._holding_override = holding_override
        self._tenant_override = tenant_override
        self._killswitch = killswitch_service or SessionKillSwitchService()
        self._users: dict[int, ClientUserSeatState] = {}

    def update_quota_limits(
        self,
        *,
        plan_max_active_users: int | None = None,
        holding_override: int | None = None,
        tenant_override: int | None = None,
    ) -> None:
        """Permite al SuperUser actualizar dinámicamente los cupos del plan o los overrides."""
        if plan_max_active_users is not None:
            self._plan_max_active_users = plan_max_active_users
        self._holding_override = holding_override
        self._tenant_override = tenant_override

    def evaluate_current_seats(self, holding_id: str) -> SeatQuotaEvaluation:
        """Evalúa el estado actual de cupos del `holding_id`."""
        holding_users = [
            u for u in self._users.values() if u.holding_id == holding_id
        ]
        return evaluate_seat_quota_for_new_or_restored_user(
            existing_users=holding_users,
            plan_max_active_users=self._plan_max_active_users,
            holding_override=self._holding_override,
            tenant_override=self._tenant_override,
        )

    def register_active_user(
        self,
        *,
        user_id: int,
        holding_id: str,
    ) -> ClientUserSeatState:
        """Registra un nuevo trabajador activo verificando primero el cupo del plan."""
        evaluation = self.evaluate_current_seats(holding_id)
        if not evaluation.allowed:
            raise QuotaExceededError(
                f"Maximum active users quota reached ({evaluation.effective_max_users}). "
                "Soft-delete an inactive worker or upgrade the plan.",
                i18n_key="tenancy:errors.seat_quota_exceeded",
                context={
                    "active_users": evaluation.active_non_deleted_users,
                    "max_users": evaluation.effective_max_users,
                },
            )
        state = ClientUserSeatState(
            user_id=user_id,
            holding_id=holding_id,
            is_deleted=False,
        )
        self._users[user_id] = state
        return state

    async def soft_delete_user(
        self,
        *,
        user_id: int,
        actor_user_id: int,
    ) -> tuple[ClientUserSeatState, SessionKillSwitchResult]:
        """
        Aplica `Soft-Delete` (`is_deleted = True`) liberando el cupo en el mismo instante
        y revocando todas las sesiones del usuario en Redis (`SessionKillSwitchService`).
        """
        existing = self._users.get(user_id)
        if existing is None:
            raise KeyError(f"User {user_id} not found in seat registry.")
        updated = replace(existing, is_deleted=True)
        self._users[user_id] = updated
        ks_result = await self._killswitch.revoke_all_user_sessions(
            user_id=user_id,
            actor_user_id=actor_user_id,
            scope="client",
        )
        return updated, ks_result

    def restore_soft_deleted_user(self, *, user_id: int) -> ClientUserSeatState:
        """
        Reactiva un ex-trabajador (`is_deleted = False`) únicamente si existe un cupo disponible.
        Si el cupo ya fue ocupado por un nuevo trabajador, lanza `QuotaExceededError` (HTTP 409).
        """
        existing = self._users.get(user_id)
        if existing is None:
            raise KeyError(f"User {user_id} not found in seat registry.")
        if not existing.is_deleted:
            return existing

        evaluation = self.evaluate_current_seats(existing.holding_id)
        if not evaluation.allowed:
            raise QuotaExceededError(
                f"Cannot restore user {user_id}: plan seat quota ({evaluation.effective_max_users}) is full.",
                i18n_key="tenancy:errors.seat_quota_exceeded_on_restore",
                context={
                    "active_users": evaluation.active_non_deleted_users,
                    "max_users": evaluation.effective_max_users,
                },
            )
        updated = replace(existing, is_deleted=False)
        self._users[user_id] = updated
        self._killswitch.clear_revocation_on_restore(user_id=user_id)
        return updated


class TenantCapacityQuotaService:
    """
    Motor multi-recurso de cuotas de capacidad comercial por Plan + Overrides de Holding/Tenant:
    Gobierna `users`, `products`, `suppliers`, `recipes`, `combos` y `storage_mb`,
    liberando cupos automáticamente cuando un registro pasa a `is_deleted = True`.
    """

    def __init__(
        self,
        *,
        plan_limits: dict[QuotaResourceType, int] | None = None,
        holding_overrides: dict[QuotaResourceType, int | None] | None = None,
        tenant_overrides: dict[QuotaResourceType, int | None] | None = None,
    ) -> None:
        default_limits: dict[QuotaResourceType, int] = {
            "users": 5,
            "products": 500,
            "suppliers": 20,
            "recipes": 0,
            "combos": 0,
            "storage_mb": 512,
        }
        if plan_limits:
            default_limits.update(plan_limits)
        self._plan_limits: dict[QuotaResourceType, int] = default_limits
        self._holding_overrides: dict[QuotaResourceType, int | None] = (
            dict(holding_overrides) if holding_overrides else {}
        )
        self._tenant_overrides: dict[QuotaResourceType, int | None] = (
            dict(tenant_overrides) if tenant_overrides else {}
        )
        self._slots: dict[tuple[QuotaResourceType, str], ResourceSlotState] = {}
        self._used_storage_mb: int = 0

    def update_limits(
        self,
        *,
        plan_limits: dict[QuotaResourceType, int] | None = None,
        holding_overrides: dict[QuotaResourceType, int | None] | None = None,
        tenant_overrides: dict[QuotaResourceType, int | None] | None = None,
    ) -> None:
        """Actualiza en caliente los techos del plan y los overrides del Holding o Tenant."""
        if plan_limits:
            self._plan_limits.update(plan_limits)
        if holding_overrides is not None:
            self._holding_overrides = dict(holding_overrides)
        if tenant_overrides is not None:
            self._tenant_overrides = dict(tenant_overrides)

    def set_used_storage_mb(self, used_mb: int) -> None:
        """Actualiza el consumo actual de almacenamiento en MB (imágenes WebP + PDFs DTE)."""
        if used_mb < 0:
            raise ValueError("used_mb cannot be negative.")
        self._used_storage_mb = used_mb

    def evaluate_resource(self, resource_type: QuotaResourceType) -> ResourceQuotaEvaluation:
        """Evalúa el estado actual de un recurso específico frente a su límite efectivo."""
        if resource_type == "storage_mb":
            active_count = self._used_storage_mb
            deleted_count = 0
        else:
            matching = [
                s for (rtype, _), s in self._slots.items() if rtype == resource_type
            ]
            active_count = sum(1 for s in matching if not s.is_deleted)
            deleted_count = sum(1 for s in matching if s.is_deleted)

        return evaluate_resource_capacity_quota(
            resource_type=resource_type,
            active_non_deleted_count=active_count,
            soft_deleted_count=deleted_count,
            plan_limit=self._plan_limits.get(resource_type, 0),
            holding_override=self._holding_overrides.get(resource_type),
            tenant_override=self._tenant_overrides.get(resource_type),
        )

    evaluate = evaluate_resource

    def evaluate_all_resources(self) -> dict[QuotaResourceType, ResourceQuotaEvaluation]:
        """Devuelve el mapa consolidado de las 6 cuotas del Plan y Tenant."""
        resources: tuple[QuotaResourceType, ...] = (
            "users",
            "products",
            "suppliers",
            "recipes",
            "combos",
            "storage_mb",
        )
        return {res: self.evaluate_resource(res) for res in resources}

    def register_item(
        self,
        *,
        resource_type: QuotaResourceType,
        item_id: str,
    ) -> ResourceSlotState:
        """Registra un nuevo ítem activo (`products`, `suppliers`, `recipes`, `combos`, `users`) o lanza HTTP 409."""
        evaluation = self.evaluate_resource(resource_type)
        if not evaluation.allowed:
            raise QuotaExceededError(
                f"Maximum {resource_type} quota reached ({evaluation.effective_max_limit}). "
                "Archive/soft-delete an unused item or upgrade the plan.",
                i18n_key=f"tenancy:errors.{resource_type}_quota_exceeded",
                context={
                    "resource_type": resource_type,
                    "active_count": evaluation.active_count,
                    "effective_max_limit": evaluation.effective_max_limit,
                },
            )
        slot = ResourceSlotState(
            item_id=item_id,
            resource_type=resource_type,
            is_deleted=False,
        )
        self._slots[(resource_type, item_id)] = slot
        return slot

    def soft_delete_item(
        self,
        *,
        resource_type: QuotaResourceType,
        item_id: str,
    ) -> ResourceSlotState:
        """Archiva (`is_deleted = True`) un ítem liberando inmediatamente 1 cupo activo en el Plan."""
        key = (resource_type, item_id)
        existing = self._slots.get(key)
        if existing is None:
            raise KeyError(f"Item {item_id} of type {resource_type} not found.")
        updated = replace(existing, is_deleted=True)
        self._slots[key] = updated
        return updated

    def restore_item(
        self,
        *,
        resource_type: QuotaResourceType,
        item_id: str,
    ) -> ResourceSlotState:
        """Restaura un ítem archivado (`is_deleted = False`) verificando que exista cupo disponible."""
        key = (resource_type, item_id)
        existing = self._slots.get(key)
        if existing is None:
            raise KeyError(f"Item {item_id} of type {resource_type} not found.")
        if not existing.is_deleted:
            return existing
        evaluation = self.evaluate_resource(resource_type)
        if not evaluation.allowed:
            raise QuotaExceededError(
                f"Cannot restore {resource_type} '{item_id}': quota ({evaluation.effective_max_limit}) is full.",
                i18n_key=f"tenancy:errors.{resource_type}_quota_exceeded_on_restore",
                context={
                    "resource_type": resource_type,
                    "active_count": evaluation.active_count,
                    "effective_max_limit": evaluation.effective_max_limit,
                },
            )
        updated = replace(existing, is_deleted=False)
        self._slots[key] = updated
        return updated

