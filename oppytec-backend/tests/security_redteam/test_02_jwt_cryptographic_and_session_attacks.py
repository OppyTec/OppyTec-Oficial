"""
Vector Red Team 02 (`tests/security_redteam/test_02_jwt_cryptographic_and_session_attacks.py`):
- Ataque `alg: none` (token sin firma criptográfica).
- Adulteración de payload / firma HMAC (`HS256` tampering).
- Rechazo de tokens expirados (`exp` en el pasado) y confusión de tipo (`refresh` usado como `access`).
- Firma con clave secreta equivocada o atacante externo.
- Revocación instantánea por Kill-Switch (`jti` y `user_id` soft-deleted).
"""
from __future__ import annotations

import base64
import json
from datetime import timedelta

import httpx
import jwt
import pytest

from src.core.exceptions import AuthenticationError
from src.core.guards import (
    clear_revoked_sessions,
    get_rate_limiter,
    revoke_session_token,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)

pytestmark = pytest.mark.security_redteam


def _forge_alg_none_token(payload: dict[str, object]) -> str:
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"{header_b64}.{payload_b64}."


def test_jwt_alg_none_signature_tampering_and_wrong_secret_rejected() -> None:
    """Verifica que `decode_access_token` bloquee `alg: none`, firmas adulteradas y secretos falsos."""
    alg_none_tok = _forge_alg_none_token(
        {
            "sub": "1",
            "user_id": 1,
            "is_superuser_god": True,
            "hierarchy_rank": 0,
            "type": "access",
        }
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(alg_none_tok)

    # Token firmado con clave de atacante externo
    attacker_tok = jwt.encode(
        {
            "sub": "1",
            "user_id": 1,
            "is_superuser_god": True,
            "hierarchy_rank": 0,
            "type": "access",
        },
        "attacker_forged_secret_key_with_32_plus_chars_!@#",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(attacker_tok)

    # Adulteración del payload de un token válido sin recalcular HMAC
    valid_tok = create_access_token(
        user_id=55,
        tenant_id="tenant_rest_a",
        hierarchy_rank=30,
        is_superuser_god=False,
    )
    header_part, _payload_part, sig_part = valid_tok.split(".")
    tampered_payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "sub": "55",
                    "user_id": 55,
                    "tenant_id": "tenant_rest_a",
                    "hierarchy_rank": 0,
                    "is_superuser_god": True,
                    "type": "access",
                }
            ).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    tampered_tok = f"{header_part}.{tampered_payload}.{sig_part}"
    with pytest.raises(AuthenticationError):
        decode_access_token(tampered_tok)


def test_jwt_expired_and_token_type_confusion_rejected() -> None:
    """Verifica rechazo de tokens expirados y prohibición de usar `refresh_token` como `access_token`."""
    expired_tok = create_access_token(
        user_id=77,
        tenant_id="tenant_rest_a",
        expires_delta=timedelta(seconds=-120),
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(expired_tok)

    refresh_tok = create_refresh_token(
        user_id=77,
        tenant_id="tenant_rest_a",
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(refresh_tok)


async def test_session_killswitch_revokes_jti_and_soft_deleted_user_immediately(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el Kill-Switch bloquee inmediatamente tanto un `jti` revocado como un usuario soft-deleted."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    token = create_access_token(
        user_id=88,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=20,
        role_grants=["catalog.products.read"],
        accessible_tenants=["tenant_rest_a"],
        jti="jti-redteam-killswitch-01",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    ok_resp = await async_client.get("/api/v1/catalog/products", headers=headers)
    assert ok_resp.status_code == 200

    # Revocar el JTI específico
    revoke_session_token(jti="jti-redteam-killswitch-01")
    revoked_resp = await async_client.get("/api/v1/catalog/products", headers=headers)
    assert revoked_resp.status_code == 401
    assert revoked_resp.json()["error_code"] == "SESSION_REVOKED_KILLSWITCH"

    clear_revoked_sessions()
    # Verificar también token con claim is_deleted=True
    deleted_claim_token = create_access_token(
        user_id=89,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        role_grants=["catalog.products.read"],
        accessible_tenants=["tenant_rest_a"],
        extra_claims={"is_deleted": True},
    )
    deleted_resp = await async_client.get(
        "/api/v1/catalog/products",
        headers={
            "Authorization": f"Bearer {deleted_claim_token}",
            "X-Tenant-ID": "tenant_rest_a",
        },
    )
    assert deleted_resp.status_code == 401
    assert deleted_resp.json()["error_code"] == "SESSION_REVOKED_KILLSWITCH"
    clear_revoked_sessions()
