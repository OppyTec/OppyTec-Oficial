#!/bin/sh
# ==============================================================================
# oppytec-frontend/docker-entrypoint.sh
# Invarianza del Artefacto (Build Once, Deploy Everywhere — SHA-256):
# Genera dinámicamente /usr/share/nginx/html/runtime-env.js al iniciar el contenedor
# sin modificar ni recompilar los bundles JS/CSS compilados por Vite.
# ==============================================================================
set -eu

RUNTIME_ENV_PATH="${RUNTIME_ENV_OUTPUT_PATH:-/usr/share/nginx/html/runtime-env.js}"

escape_json() {
  printf '%s' "${1:-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

VITE_ENVIRONMENT_VAL="$(escape_json "${VITE_ENVIRONMENT:-local}")"
VITE_ENV_NAMESPACE_VAL="$(escape_json "${VITE_ENV_NAMESPACE:-default}")"
VITE_API_BASE_URL_VAL="$(escape_json "${VITE_API_BASE_URL:-/api/v1}")"
VITE_WS_BASE_URL_VAL="$(escape_json "${VITE_WS_BASE_URL:-/api/v1/ws/realtime}")"
VITE_SENTRY_DSN_VAL="$(escape_json "${VITE_SENTRY_DSN:-}")"
VITE_OTEL_COLLECTOR_URL_VAL="$(escape_json "${VITE_OTEL_COLLECTOR_URL:-}")"
VITE_UMAMI_ENABLED_VAL="$(escape_json "${VITE_UMAMI_ENABLED:-false}")"
VITE_UMAMI_WEBSITE_ID_VAL="$(escape_json "${VITE_UMAMI_WEBSITE_ID:-}")"
VITE_AI_ASSISTANT_BRAND_NAME_VAL="$(escape_json "${VITE_AI_ASSISTANT_BRAND_NAME:-OppyFy}")"

cat <<EOF > "${RUNTIME_ENV_PATH}"
// Generated at container startup by docker-entrypoint.sh (Immutable SHA-256 Artifact)
window.__OPPYTEC_RUNTIME_ENV__ = Object.freeze({
  VITE_ENVIRONMENT: "${VITE_ENVIRONMENT_VAL}",
  VITE_ENV_NAMESPACE: "${VITE_ENV_NAMESPACE_VAL}",
  VITE_API_BASE_URL: "${VITE_API_BASE_URL_VAL}",
  VITE_WS_BASE_URL: "${VITE_WS_BASE_URL_VAL}",
  VITE_SENTRY_DSN: "${VITE_SENTRY_DSN_VAL}",
  VITE_OTEL_COLLECTOR_URL: "${VITE_OTEL_COLLECTOR_URL_VAL}",
  VITE_UMAMI_ENABLED: "${VITE_UMAMI_ENABLED_VAL}",
  VITE_UMAMI_WEBSITE_ID: "${VITE_UMAMI_WEBSITE_ID_VAL}",
  VITE_AI_ASSISTANT_BRAND_NAME: "${VITE_AI_ASSISTANT_BRAND_NAME_VAL}"
});
EOF

if [ "$#" -gt 0 ]; then
  exec "$@"
fi
