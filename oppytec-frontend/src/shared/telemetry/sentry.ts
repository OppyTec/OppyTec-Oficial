import { getRuntimeEnv } from "@/shared/config/env";
import { generateTraceId } from "@/shared/telemetry/otel";

/**
 * Pilar 3 de Observabilidad en Frontend: Sentry / GlitchTip Error Boundary & PII Redactor
 * Cumple ISO/IEC 27001 §A.12.4 y Regla 17 (Zero Secret / PII Leak to Telemetry).
 */
export const REDACTED_PLACEHOLDER = "[REDACTED]" as const;

const SENSITIVE_FIELD_PATTERNS = [
  "password",
  "hashed_password",
  "token",
  "access_token",
  "refresh_token",
  "secret",
  "api_key",
  "apikey",
  "authorization",
  "cookie",
  "set-cookie",
  "x-api-key",
  "tax_id",
  "credit_card",
  "cvv",
  "jwt",
] as const;

const BEARER_REGEX = /Bearer\s+[A-Za-z0-9\-._~+/]+=*/gi;

function isSensitiveKey(key: string): boolean {
  const normalized = key.trim().toLowerCase();
  return SENSITIVE_FIELD_PATTERNS.some(
    (pattern) => normalized === pattern || normalized.includes(pattern)
  );
}

function scrubStringValue(value: string): string {
  return value.replace(BEARER_REGEX, `Bearer ${REDACTED_PLACEHOLDER}`);
}

/**
 * Redacta recursivamente cualquier campo PII, credencial o token antes de enviarlo a Sentry/GlitchTip.
 */
export function scrubFrontendPii<T>(payload: T): T {
  if (payload === null || payload === undefined) {
    return payload;
  }

  if (typeof payload === "string") {
    return scrubStringValue(payload) as unknown as T;
  }

  if (Array.isArray(payload)) {
    return payload.map((item: unknown) => scrubFrontendPii(item)) as unknown as T;
  }

  if (typeof payload === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(payload as Record<string, unknown>)) {
      if (isSensitiveKey(key)) {
        result[key] = REDACTED_PLACEHOLDER;
      } else {
        result[key] = scrubFrontendPii(val);
      }
    }
    return result as T;
  }

  return payload;
}

export interface FrontendExceptionContext {
  readonly traceId?: string;
  readonly holdingId?: string;
  readonly tenantSchema?: string;
  readonly userId?: number;
  readonly roleRank?: number;
  readonly componentStack?: string;
  readonly extra?: Record<string, unknown>;
}

export interface SanitizedErrorReport {
  readonly eventId: string;
  readonly traceId: string;
  readonly environment: string;
  readonly sendDefaultPii: false;
  readonly errorName: string;
  readonly errorMessage: string;
  readonly tenantSchema: string;
  readonly holdingId: string;
  readonly sanitizedExtra: Record<string, unknown>;
  readonly timestamp: string;
}

/**
 * Prepara y sanitiza un reporte de excepción de ErrorBoundary vinculado a X-Trace-ID.
 */
export function captureFrontendException(
  error: unknown,
  context: FrontendExceptionContext = {}
): SanitizedErrorReport {
  const env = getRuntimeEnv();
  const traceId = context.traceId ?? generateTraceId();
  const errObj =
    error instanceof Error ? error : new Error(typeof error === "string" ? error : "UnknownError");

  const environmentTag =
    env.VITE_ENVIRONMENT === "preview"
      ? `preview:${env.VITE_ENV_NAMESPACE}`
      : env.VITE_ENVIRONMENT;

  const sanitizedExtra = scrubFrontendPii(context.extra ?? {});

  return {
    eventId: generateTraceId().slice(0, 16),
    traceId,
    environment: environmentTag,
    sendDefaultPii: false,
    errorName: errObj.name,
    errorMessage: scrubStringValue(errObj.message),
    tenantSchema: context.tenantSchema ?? "public",
    holdingId: context.holdingId ?? "global",
    sanitizedExtra,
    timestamp: new Date().toISOString(),
  };
}
