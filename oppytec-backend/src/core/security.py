"""
oppytec-backend/src/core/security.py
Criptografía de autenticación y autorización Multi-Tenant:
- Hashing de contraseñas Argon2id (`pwdlib`) con fallback determinista PBKDF2-HMAC-SHA256.
- Emisión y verificación de JWT (`access` y `refresh`) mediante `PyJWT` y `SecretStr`.
- Extracción tipada de claims Multi-Tenant (`TenantJwtClaims`).
"""
# ruff: noqa: S105, S106, S107
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash

from src.core.config import Settings, get_settings
from src.core.exceptions import PermissionDeniedError

TokenType = Literal["access", "refresh"]

_argon2_hasher = PasswordHash.recommended()
_PBKDF2_PREFIX = "pbkdf2_sha256$"
_PBKDF2_ITERATIONS = 210_000


@dataclass(frozen=True)
class TenantJwtClaims:
    """Claims Multi-Tenant extraídos y validados de un token JWT de OppyTec v2.0."""

    user_id: int
    holding_id: str | None
    tenant_id: str | None
    tenant_schema: str | None
    hierarchy_rank: int
    is_superuser_god: bool
    token_type: TokenType
    jti: str
    issued_at: int
    expires_at: int


def hash_password_pbkdf2_fallback(plain_password: str, salt: str | None = None) -> str:
    """Fallback determinista PBKDF2-HMAC-SHA256 cuando se requiere hashing portable."""
    resolved_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        resolved_salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return f"{_PBKDF2_PREFIX}{_PBKDF2_ITERATIONS}${resolved_salt}${derived.hex()}"


def verify_password_pbkdf2_fallback(plain_password: str, encoded_hash: str) -> bool:
    """Verifica un hash con formato `pbkdf2_sha256$<iterations>$<salt>$<hex>` en tiempo constante."""
    if not encoded_hash.startswith(_PBKDF2_PREFIX):
        return False
    parts = encoded_hash.split("$")
    if len(parts) != 4:
        return False
    try:
        iterations = int(parts[1])
    except ValueError:
        return False
    salt = parts[2]
    expected_hex = parts[3]
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(derived.hex(), expected_hex)


def hash_password(plain_password: str, *, use_pbkdf2_fallback: bool = False) -> str:
    """Hashea una contraseña en texto plano con Argon2id (o PBKDF2-HMAC-SHA256 si se solicita)."""
    if len(plain_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if use_pbkdf2_fallback:
        return hash_password_pbkdf2_fallback(plain_password)
    try:
        return str(_argon2_hasher.hash(plain_password))
    except Exception:
        return hash_password_pbkdf2_fallback(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra un hash Argon2id o PBKDF2-HMAC-SHA256."""
    if not plain_password or not hashed_password:
        return False
    if hashed_password.startswith(_PBKDF2_PREFIX):
        return verify_password_pbkdf2_fallback(plain_password, hashed_password)
    try:
        return bool(_argon2_hasher.verify(plain_password, hashed_password))
    except Exception:
        return False


def create_jwt_token(
    *,
    user_id: int,
    token_type: TokenType = "access",
    holding_id: str | None = None,
    tenant_id: str | None = None,
    tenant_schema: str | None = None,
    hierarchy_rank: int = 30,
    is_superuser_god: bool = False,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
    settings: Settings | None = None,
) -> str:
    """
    Emite un JWT firmado (`HS256`) con `JWT_ACCESS_SECRET_KEY` o `JWT_REFRESH_SECRET_KEY`.
    Incluye todos los claims Multi-Tenant requeridos para aislamiento de esquemas y RBAC Dual.
    """
    resolved = settings or get_settings()
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire_dt = now + expires_delta
    elif token_type == "access":
        expire_dt = now + timedelta(minutes=resolved.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire_dt = now + timedelta(days=resolved.REFRESH_TOKEN_EXPIRE_DAYS)

    secret = (
        resolved.JWT_ACCESS_SECRET_KEY.get_secret_value()
        if token_type == "access"
        else resolved.JWT_REFRESH_SECRET_KEY.get_secret_value()
    )
    token_jti = jti or str(uuid.uuid4())
    payload: dict[str, object] = {
        "sub": str(user_id),
        "user_id": user_id,
        "holding_id": holding_id,
        "tenant_id": tenant_id,
        "tenant_schema": tenant_schema,
        "hierarchy_rank": hierarchy_rank,
        "is_superuser_god": is_superuser_god,
        "type": token_type,
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expire_dt.timestamp()),
    }
    return str(jwt.encode(payload, secret, algorithm=resolved.ALGORITHM))


def create_access_token(
    *,
    user_id: int,
    holding_id: str | None = None,
    tenant_id: str | None = None,
    tenant_schema: str | None = None,
    hierarchy_rank: int = 30,
    is_superuser_god: bool = False,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    """Atajo tipado para emitir un `access` token JWT."""
    return create_jwt_token(
        user_id=user_id,
        token_type="access",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema=tenant_schema,
        hierarchy_rank=hierarchy_rank,
        is_superuser_god=is_superuser_god,
        expires_delta=expires_delta,
        settings=settings,
    )


def create_refresh_token(
    *,
    user_id: int,
    holding_id: str | None = None,
    tenant_id: str | None = None,
    tenant_schema: str | None = None,
    hierarchy_rank: int = 30,
    is_superuser_god: bool = False,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    """Atajo tipado para emitir un `refresh` token JWT."""
    return create_jwt_token(
        user_id=user_id,
        token_type="refresh",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema=tenant_schema,
        hierarchy_rank=hierarchy_rank,
        is_superuser_god=is_superuser_god,
        expires_delta=expires_delta,
        settings=settings,
    )


def decode_and_extract_claims(
    token: str,
    *,
    expected_type: TokenType = "access",
    settings: Settings | None = None,
) -> TenantJwtClaims:
    """
    Verifica firma y expiración del JWT y extrae `TenantJwtClaims`.
    Lanza `PermissionDeniedError` (HTTP 403/401) si el token es inválido, expiró o el tipo no coincide.
    """
    resolved = settings or get_settings()
    secret = (
        resolved.JWT_ACCESS_SECRET_KEY.get_secret_value()
        if expected_type == "access"
        else resolved.JWT_REFRESH_SECRET_KEY.get_secret_value()
    )
    try:
        raw_payload: dict[str, object] = jwt.decode(
            token,
            secret,
            algorithms=[resolved.ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise PermissionDeniedError(
            "Invalid or expired JWT token.",
            i18n_key="auth:errors.invalid_or_expired_token",
            status_code=401,
        ) from exc

    tok_type = str(raw_payload.get("type", ""))
    if tok_type != expected_type:
        raise PermissionDeniedError(
            f"Unexpected JWT token type '{tok_type}', expected '{expected_type}'.",
            i18n_key="auth:errors.invalid_token_type",
            status_code=401,
        )

    raw_user_id = raw_payload.get("user_id", raw_payload.get("sub"))
    if not isinstance(raw_user_id, (int, str)):
        raise PermissionDeniedError(
            "Missing user_id claim in token.",
            i18n_key="auth:errors.missing_user_claim",
            status_code=401,
        )
    user_id = int(raw_user_id)

    raw_rank = raw_payload.get("hierarchy_rank", 30)
    hierarchy_rank = int(raw_rank) if isinstance(raw_rank, (int, str)) else 30

    holding_val = raw_payload.get("holding_id")
    tenant_val = raw_payload.get("tenant_id")
    schema_val = raw_payload.get("tenant_schema")

    raw_iat = raw_payload.get("iat", 0)
    raw_exp = raw_payload.get("exp", 0)

    return TenantJwtClaims(
        user_id=user_id,
        holding_id=str(holding_val) if holding_val is not None else None,
        tenant_id=str(tenant_val) if tenant_val is not None else None,
        tenant_schema=str(schema_val) if schema_val is not None else None,
        hierarchy_rank=hierarchy_rank,
        is_superuser_god=bool(raw_payload.get("is_superuser_god", False)),
        token_type=expected_type,
        jti=str(raw_payload.get("jti", "")),
        issued_at=int(raw_iat) if isinstance(raw_iat, (int, str)) else 0,
        expires_at=int(raw_exp) if isinstance(raw_exp, (int, str)) else 0,
    )
