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
    SeatQuotaEvaluation,
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
