import { getRuntimeEnv } from "@/shared/config/env";
import { scrubFrontendPii } from "@/shared/telemetry/sentry";

/**
 * Pilar 4 de Observabilidad en Frontend: Umami Analytics (100% Ético, Sin Cookies, Cero PII)
 * Solo se activa cuando VITE_UMAMI_ENABLED === true y jamás envía tokens ni parámetros sensibles en la URL.
 */
export interface UmamiTrackerConfig {
  readonly enabled: boolean;
  readonly websiteId: string;
  readonly environment: string;
  readonly cookieLess: true;
  readonly doNotTrackRespect: true;
}

const TOKEN_SEGMENT_REGEX =
  /\/(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|[0-9a-f]{32,64})(?=\/|$)/gi;

/**
 * Limpia cualquier query string con tokens/PII o segmentos con JWT/hashes en la ruta antes de reportar a Umami.
 */
export function sanitizeAnalyticsPath(rawUrlOrPath: string): string {
  const withoutOrigin = rawUrlOrPath.replace(/^https?:\/\/[^/]+/i, "");
  const [pathnameOnly = "/"] = withoutOrigin.split("?");
  const [cleanPath = "/"] = pathnameOnly.split("#");
  const normalized = cleanPath.startsWith("/") ? cleanPath : `/${cleanPath}`;
  return normalized.replace(TOKEN_SEGMENT_REGEX, "/[REDACTED_TOKEN]");
}

export function resolveUmamiConfig(): UmamiTrackerConfig {
  const env = getRuntimeEnv();
  const isAllowedEnv =
    env.VITE_ENVIRONMENT === "staging" || env.VITE_ENVIRONMENT === "production";
  const enabled =
    isAllowedEnv &&
    env.VITE_UMAMI_ENABLED &&
    env.VITE_UMAMI_WEBSITE_ID.trim().length > 0;

  return {
    enabled,
    websiteId: enabled ? env.VITE_UMAMI_WEBSITE_ID.trim() : "",
    environment: env.VITE_ENVIRONMENT,
    cookieLess: true,
    doNotTrackRespect: true,
  };
}

export interface UmamiTrackedEvent {
  readonly dispatched: boolean;
  readonly eventName: string;
  readonly sanitizedPath: string;
  readonly payload: Record<string, unknown>;
}

export function trackUmamiEvent(
  eventName: string,
  rawPath: string,
  metadata: Record<string, unknown> = {}
): UmamiTrackedEvent {
  const config = resolveUmamiConfig();
  const sanitizedPath = sanitizeAnalyticsPath(rawPath);
  const sanitizedPayload = scrubFrontendPii(metadata);

  if (!config.enabled) {
    return {
      dispatched: false,
      eventName,
      sanitizedPath,
      payload: sanitizedPayload,
    };
  }

  return {
    dispatched: true,
    eventName,
    sanitizedPath,
    payload: sanitizedPayload,
  };
}
