"""
oppytec-backend/src/core/config.py
Configuración Fail-Fast en el milisegundo 0 para los 5 Entornos de OppyTec v2.0.
Cumple ISO/IEC 27001 §A.12.1.4, OWASP API8 y Regla Inmutable 09 (Zero Hardcoding + SecretStr).
"""
from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import EmailStr, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentType = Literal["local", "preview", "ci", "staging", "production"]
PoolClassType = Literal["AsyncAdaptedQueuePool", "NullPool"]
StorageProviderType = Literal["local", "r2", "s3"]
EmailProviderType = Literal["console_mock", "mailpit", "resend", "smtp"]
OtelExporterType = Literal["none", "memory", "otlp"]

WEAK_SECRET_SUBSTRINGS: tuple[str, ...] = (
    "changeme",
    "default_secret",
    "password123",
    "1234567890",
    "secret_key_here",
)


def calculate_shannon_entropy(value: str) -> float:
    """Calcula la entropía de Shannon en bits por carácter para validar claves criptográficas."""
    if not value:
        return 0.0
    length = len(value)
    counts = Counter(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


class Settings(BaseSettings):  # type: ignore[explicit-any]
    """Configuración central tipada y validada en el milisegundo 0 (cero uso de Any)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )

    # 1. Identidad de los 5 Entornos y Namespace Efímero (Git Worktrees / PRs)
    ENVIRONMENT: EnvironmentType = "local"
    ENV_NAMESPACE: str = Field(default="default", pattern=r"^[a-z0-9_]{1,32}$")

    # 2. Criptografía y JWT (Obligatoriamente SecretStr, longitud >= 32 y entropía suficiente)
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("oppytec_v2_dev_secret_key_9x8B7v6N5m4L3k2J1h0G!@#")
    )
    JWT_ACCESS_SECRET_KEY: SecretStr = Field(
        default=SecretStr("oppytec_v2_jwt_access_key_3z4X5c6V7b8N9m0Q1w2E!@#")
    )
    JWT_REFRESH_SECRET_KEY: SecretStr = Field(
        default=SecretStr("oppytec_v2_jwt_refresh_key_7u8I9o0P1a2S3d4F5g6H!@#")
    )
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=120)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)

    # 3. Persistencia, Caché y Modo de Pooling (QueuePool vs NullPool para PgBouncer/Neon)
    DATABASE_URL: SecretStr = Field(
        default=SecretStr("postgresql+asyncpg://db_user:db_pass@localhost:5432/oppytec_dev")
    )
    REDIS_URL: SecretStr = Field(default=SecretStr("redis://localhost:6379/0"))
    DB_POOL_CLASS: PoolClassType = "AsyncAdaptedQueuePool"
    DB_POOL_SIZE: int = Field(default=40, ge=5, le=200)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    DB_STATEMENT_CACHE_SIZE: int = Field(default=0, ge=0, le=1024)

    # 4. SuperUser Génesis (Leído desde entorno / Secret Manager)
    SUPERUSER_GENESIS_EMAIL: EmailStr = "oppytec.admin@gmail.com"
    SUPERUSER_GENESIS_USERNAME: str = Field(
        default="oppytec.admin", min_length=4, max_length=64
    )
    SUPERUSER_GENESIS_PASSWORD: SecretStr = Field(
        default=SecretStr("OppyTec_Genesis_Local_Safe_Pass_2026!")
    )

    # 5. Marca Configurable de IA, Proveedores LLM y Motor JEV (Sistema 1)
    AI_ASSISTANT_BRAND_NAME: str = Field(default="OppyFy", min_length=2, max_length=32)
    GEMINI_API_KEY: SecretStr = Field(default=SecretStr("gemini_local_stub_api_key_value"))
    JEV_API_KEY: SecretStr = Field(default=SecretStr("jev_system1_local_stub_api_key_value"))

    # 6. Almacenamiento Cloudflare R2 y Respaldos Cifrados en 4 Capas (.sql.zst.age)
    STORAGE_PROVIDER: StorageProviderType = "local"
    R2_ACCOUNT_ID: str = "local_r2_account"
    R2_ACCESS_KEY_ID: str = "local_r2_access_key"
    R2_SECRET_ACCESS_KEY: SecretStr = Field(default=SecretStr("local_r2_secret_access_key_stub"))
    R2_MEDIA_BUCKET_NAME: str = "oppytec-media-staging"
    R2_PUBLIC_URL: str = "https://media-staging.oppytec.com"
    BACKUP_R2_BUCKET_NAME: str = "oppytec-backups-vault"
    BACKUP_ENCRYPTION_PUBLIC_KEY: str | None = None
    BACKUP_SECONDARY_VPS_ENABLED: bool = False
    BACKUP_SECONDARY_VPS_ENDPOINT: str | None = None

    # 7. Red, CORS, Sinkhole de Correo y Observabilidad 4-Pilares
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    EMAIL_PROVIDER: EmailProviderType = "mailpit"
    SAFE_OUTBOUND_EMAIL_DOMAINS: list[str] = Field(default_factory=lambda: ["oppytec.com"])
    OTEL_EXPORTER: OtelExporterType = "none"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    SENTRY_DSN: SecretStr | None = None
    UMAMI_ENABLED: bool = False
    UMAMI_WEBSITE_ID: str | None = None

    @property
    def is_openapi_enabled(self) -> bool:
        """Desactiva Swagger/Redoc/OpenAPI público en producción (OWASP API8)."""
        return self.ENVIRONMENT != "production"

    @property
    def redis_key_prefix(self) -> str:
        """Prefijo determinista por entorno y namespace (Git Worktree / PR)."""
        return f"{self.ENVIRONMENT}:{self.ENV_NAMESPACE}:"

    @model_validator(mode="after")
    def enforce_environment_security_boundaries(self) -> Settings:
        """Validación Fail-Fast en el milisegundo 0 para claves, hosts y fronteras de entorno."""
        # 1. Validar longitud (>= 32 chars) y entropía Shannon de claves criptográficas
        for secret_field in ("SECRET_KEY", "JWT_ACCESS_SECRET_KEY", "JWT_REFRESH_SECRET_KEY"):
            secret_val = getattr(self, secret_field).get_secret_value()
            lower_val = secret_val.lower()
            entropy = calculate_shannon_entropy(secret_val)
            if (
                len(secret_val) < 32
                or len(set(secret_val)) < 10
                or entropy < 3.0
                or any(weak in lower_val for weak in WEAK_SECRET_SUBSTRINGS)
            ):
                raise ValueError(
                    f"Fail-Fast Security Error: '{secret_field}' debe tener al menos 32 caracteres "
                    f"y alta entropía Shannon (>= 3.0 bits/char, actual={entropy:.2f})."
                )

        db_url_plain = self.DATABASE_URL.get_secret_value().lower()
        redis_url_plain = self.REDIS_URL.get_secret_value().lower()
        parsed_db = urlparse(db_url_plain)
        parsed_redis = urlparse(redis_url_plain)
        db_host = parsed_db.hostname or ""
        redis_host = parsed_redis.hostname or ""

        forbidden_remote_markers = (
            "prod.",
            "staging.",
            "-prod",
            "_prod",
            "-staging",
            "_staging",
            "oppytec-prod",
            "oppytec_prod",
            "prod-db",
            "staging-db",
        )

        # 2. Guardia de Frontera Cross-Environment: local / preview / ci jamás tocan staging o prod
        if self.ENVIRONMENT in ("local", "preview", "ci") and (
            any(m in db_url_plain for m in forbidden_remote_markers)
            or any(m in redis_url_plain for m in forbidden_remote_markers)
        ):
            raise ValueError(
                f"CrossEnvironmentViolation: El entorno '{self.ENVIRONMENT}' tiene prohibido "
                "conectarse a hosts o bases de datos de 'staging' o 'production'."
            )

        if self.ENVIRONMENT in ("local", "ci"):
            allowed_local_db_hosts = {"localhost", "127.0.0.1", "postgres", "db", "test-db"}
            allowed_local_redis_hosts = {"localhost", "127.0.0.1", "redis", "test-redis"}
            if db_host not in allowed_local_db_hosts:
                raise ValueError(
                    f"CrossEnvironmentViolation: En '{self.ENVIRONMENT}', DATABASE_URL host '{db_host}' "
                    f"debe pertenecer a {sorted(allowed_local_db_hosts)}."
                )
            if redis_host not in allowed_local_redis_hosts:
                raise ValueError(
                    f"CrossEnvironmentViolation: En '{self.ENVIRONMENT}', REDIS_URL host '{redis_host}' "
                    f"debe pertenecer a {sorted(allowed_local_redis_hosts)}."
                )

        if self.ENVIRONMENT == "ci" and (self.OTEL_EXPORTER == "otlp" or self.UMAMI_ENABLED):
            raise ValueError(
                "SecurityBoundaryViolation: En 'ci', OTEL_EXPORTER debe ser 'memory' o 'none' "
                "y UMAMI_ENABLED debe ser False (cero tráfico externo)."
            )

        # 3. Reglas de Correo y Sinkhole por Entorno
        if self.ENVIRONMENT in ("local", "preview", "ci", "staging"):
            if not self.SAFE_OUTBOUND_EMAIL_DOMAINS or any(
                d.strip() in ("*", "") for d in self.SAFE_OUTBOUND_EMAIL_DOMAINS
            ):
                raise ValueError(
                    f"SecurityBoundaryViolation: En '{self.ENVIRONMENT}', SAFE_OUTBOUND_EMAIL_DOMAINS "
                    "debe declarar dominios explícitos seguros para el sinkhole de salida."
                )
            if self.ENVIRONMENT in ("local", "ci") and self.EMAIL_PROVIDER not in (
                "console_mock",
                "mailpit",
            ):
                raise ValueError(
                    f"SecurityBoundaryViolation: En '{self.ENVIRONMENT}', EMAIL_PROVIDER debe ser "
                    "'console_mock' o 'mailpit' (sinkhole local)."
                )

        # 4. Endurecimiento estricto en Staging y Production
        if self.ENVIRONMENT in ("staging", "production"):
            origins_lower = [o.lower().strip() for o in self.ALLOWED_ORIGINS]
            if not origins_lower or any(
                o == "*" or "localhost" in o or "127.0.0.1" in o or o.startswith("http://")
                for o in origins_lower
            ):
                raise ValueError(
                    f"SecurityBoundaryViolation: En '{self.ENVIRONMENT}', ALLOWED_ORIGINS no puede "
                    "contener '*', 'localhost', '127.0.0.1' ni orígenes sin 'https://'."
                )
            if self.STORAGE_PROVIDER == "local":
                raise ValueError(
                    f"SecurityBoundaryViolation: En '{self.ENVIRONMENT}', STORAGE_PROVIDER no puede ser 'local'."
                )

        if self.ENVIRONMENT == "production" and self.EMAIL_PROVIDER in (
            "console_mock",
            "mailpit",
        ):
            raise ValueError(
                "SecurityBoundaryViolation: En 'production', EMAIL_PROVIDER no puede ser "
                "'console_mock' ni 'mailpit'."
            )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia singleton validada de Settings."""
    return Settings()
