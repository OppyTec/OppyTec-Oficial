"""
Pruebas de Integración de `Soft-Delete`, Liberación Inmediata de Cupo y Kill-Switch de Sesión
(`tests/integration/test_soft_delete_and_redis_killswitch.py`).

Verifica el flujo extremo a extremo:
1. El usuario activo (`user_id=205`) se autentica y opera normalmente en la API.
2. El administrador (`user_id=100`) invoca `POST /api/v1/identity/users/{user_id}/soft-delete`.
3. El cupo de usuario (`seat quota`) se libera en el acto (`freed_seat = True` / `seat_released = True`).
4. El `jti` / `user_id` del JWT queda revocado en el Kill-Switch.
5. Cualquier petición subsiguiente con ese JWT (o su Refresh Token) devuelve HTTP 401 (`AuthenticationError`).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.exceptions import QuotaExceededError
from src.core.guards import (
    clear_revoked_sessions,
    get_rate_limiter,
    is_session_revoked,
    restore_revoked_user_session,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from src.main import create_app
from src.modules.identity.application.session_killswitch import SessionKillSwitchService
from src.modules.tenancy.application.quota_service import SeatQuotaService

pytestmark = pytest.mark.integration


async def test_soft_delete_releases_seat_immediately_and_revokes_jwt_killswitch() -> None:
    """
    Verifica extremo a extremo que el `soft-delete` de un trabajador:
    - Libera el cupo del plan de inmediato (`freed_seat=True`).
    - Revoca el JWT y Refresh Token en el Kill-Switch.
    - Bloquea con HTTP 401 (`AuthenticationError` / `SESSION_REVOKED_KILLSWITCH`) toda petición posterior.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    killswitch_service = SessionKillSwitchService()
    quota_service = SeatQuotaService(
        plan_max_active_users=2,
        killswitch_service=killswitch_service,
    )

    # Registramos 2 usuarios activos en `holding_01` (llenando el techo de 2 cupos del plan)
    admin_seat = quota_service.register_active_user(user_id=100, holding_id="holding_01")
    worker_seat = quota_service.register_active_user(user_id=205, holding_id="holding_01")
    assert admin_seat.is_deleted is False
    assert worker_seat.is_deleted is False

    quota_before = quota_service.evaluate_current_seats("holding_01")
    assert quota_before.active_non_deleted_users == 2
    assert quota_before.remaining_seats == 0
    assert quota_before.allowed is False

    # Con el cupo lleno, intentar registrar un 3er usuario falla con QuotaExceededError (HTTP 409)
    with pytest.raises(QuotaExceededError):
        quota_service.register_active_user(user_id=206, holding_id="holding_01")

    app = create_app()

    # Emitimos tokens para el trabajador activo (`user_id=205`) y el administrador (`user_id=100`)
    worker_access_token = create_access_token(
        user_id=205,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=30,
        contracted_modules=["catalog"],
        role_grants=["catalog.products.read"],
        accessible_tenants=["tenant_rest_a"],
    )
    worker_refresh_token = create_refresh_token(
        user_id=205,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=30,
    )
    worker_claims = decode_access_token(worker_access_token)

    admin_access_token = create_access_token(
        user_id=100,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=10,
        contracted_modules=["settings", "catalog", "tenancy"],
        role_grants=[
            "settings.users.soft_delete",
            "catalog.products.read",
            "tenancy.quotas.read",
        ],
        accessible_tenants=["tenant_rest_a"],
    )

    with TestClient(app) as client:
        # Paso 1: El usuario activo (`user_id=205`) hace una petición autenticada -> HTTP 200
        active_resp = client.get(
            "/api/v1/catalog/products",
            headers={
                "Authorization": f"Bearer {worker_access_token}",
                "X-Tenant-ID": "tenant_rest_a",
            },
        )
        assert active_resp.status_code == 200

        # Paso 2: El administrador llama `POST /api/v1/identity/users/205/soft-delete`
        soft_del_resp = client.post(
            "/api/v1/identity/users/205/soft-delete",
            headers={
                "Authorization": f"Bearer {admin_access_token}",
                "X-Tenant-ID": "tenant_rest_a",
            },
            json={"reason": "Fin de contrato de temporada"},
        )
        assert soft_del_resp.status_code == 200
        soft_del_body = soft_del_resp.json()
        assert soft_del_body["user_id"] == 205
        assert soft_del_body["is_deleted"] is True
        assert soft_del_body["session_revoked"] is True
        assert soft_del_body["seat_released"] is True

        # Sincronizamos el servicio de cuotas de dominio/aplicación y verificamos `freed_seat=True`
        updated_seat, ks_result = await quota_service.soft_delete_user(
            user_id=205,
            actor_user_id=100,
        )
        quota_after = quota_service.evaluate_current_seats("holding_01")
        freed_seat = (
            updated_seat.is_deleted is True
            and soft_del_body["seat_released"] is True
            and quota_after.remaining_seats == 1
            and quota_after.allowed is True
        )
        assert freed_seat is True
        assert quota_after.active_non_deleted_users == 1
        assert quota_after.soft_deleted_users == 1
        assert ks_result.revoked is True
        assert await killswitch_service.is_user_session_revoked(user_id=205) is True

        # El cupo liberado permite contratar de inmediato a un nuevo trabajador (`user_id=206`)
        new_worker_seat = quota_service.register_active_user(
            user_id=206,
            holding_id="holding_01",
        )
        assert new_worker_seat.is_deleted is False
        assert quota_service.evaluate_current_seats("holding_01").remaining_seats == 0

        # Si se intenta restaurar a `user_id=205` cuando el cupo ya fue ocupado por `206` -> QuotaExceededError
        with pytest.raises(QuotaExceededError):
            quota_service.restore_soft_deleted_user(user_id=205)

        # Paso 3: Verificamos que el JWT `jti` / `user_id` de `205` está revocado en el Kill-Switch
        assert is_session_revoked(jti=worker_claims.jti, user_id=205) is True

        # Paso 4: Cualquier petición posterior con el mismo JWT devuelve HTTP 401 (`AuthenticationError`)
        revoked_api_resp = client.get(
            "/api/v1/catalog/products",
            headers={
                "Authorization": f"Bearer {worker_access_token}",
                "X-Tenant-ID": "tenant_rest_a",
            },
        )
        assert revoked_api_resp.status_code == 401
        revoked_err = revoked_api_resp.json()
        assert revoked_err["error_code"] == "SESSION_REVOKED_KILLSWITCH"
        assert revoked_err["status"] == 401

        # Paso 5: Intentar refrescar el token del usuario eliminado también devuelve HTTP 401
        revoked_refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": worker_refresh_token},
        )
        assert revoked_refresh_resp.status_code == 401

        # Paso 6: Un administrador no puede auto-eliminarse (`self-delete` -> HTTP 403)
        self_del_resp = client.post(
            "/api/v1/identity/users/100/soft-delete",
            headers={
                "Authorization": f"Bearer {admin_access_token}",
                "X-Tenant-ID": "tenant_rest_a",
            },
            json={"reason": "Intento de auto-bloqueo"},
        )
        assert self_del_resp.status_code == 403

    restore_revoked_user_session(205)
    clear_revoked_sessions()
