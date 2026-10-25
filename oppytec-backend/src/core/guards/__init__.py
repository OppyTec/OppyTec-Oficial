"""
oppytec-backend/src/core/guards/__init__.py
Exportación unificada de guardias de seguridad, RBAC de 3 niveles, Magic Bytes, XSS/SSTI/SQLi y Rate Limiting.
"""
from __future__ import annotations

from src.core.guards.file_magic_guard import (
    ALLOWED_MIME_BY_EXTENSION,
    DEFAULT_MAX_UPLOAD_BYTES,
    MAX_BATCH_ROWS,
    MAX_ZIP_COMPRESSION_RATIO,
    MAX_ZIP_UNCOMPRESSED_BYTES,
    RequireSafeFileUpload,
    ValidatedUploadPayload,
    detect_magic_mime_type,
    sanitize_spreadsheet_cell,
    sanitize_spreadsheet_export_value,
    validate_file_magic_bytes,
)
from src.core.guards.rate_limiter import (
    RATE_LIMIT_PROFILES,
    RateLimitCheckResult,
    RateLimitProfile,
    RateLimitQuota,
    RequireRateLimit,
    SlidingWindowRateLimiter,
    get_rate_limiter,
)
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
    RequireTenantPermission,
    clear_revoked_sessions,
    is_session_revoked,
    restore_revoked_user_session,
    revoke_session_token,
)
from src.core.guards.xss_sanitizer import (
    sanitize_text_input,
    validate_no_path_traversal,
)

__all__ = [
    "ALLOWED_MIME_BY_EXTENSION",
    "DEFAULT_MAX_UPLOAD_BYTES",
    "MAX_BATCH_ROWS",
    "MAX_ZIP_COMPRESSION_RATIO",
    "MAX_ZIP_UNCOMPRESSED_BYTES",
    "RATE_LIMIT_PROFILES",
    "AuthenticatedPrincipal",
    "RateLimitCheckResult",
    "RateLimitProfile",
    "RateLimitQuota",
    "RequireGlobalPermission",
    "RequireRateLimit",
    "RequireSafeFileUpload",
    "RequireTenantPermission",
    "SlidingWindowRateLimiter",
    "ValidatedUploadPayload",
    "clear_revoked_sessions",
    "detect_magic_mime_type",
    "get_rate_limiter",
    "is_session_revoked",
    "restore_revoked_user_session",
    "revoke_session_token",
    "sanitize_spreadsheet_cell",
    "sanitize_spreadsheet_export_value",
    "sanitize_text_input",
    "validate_file_magic_bytes",
    "validate_no_path_traversal",
]
