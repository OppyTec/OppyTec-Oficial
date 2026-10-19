import { z } from "zod";

/**
 * Cadena Canónica de los 5 Entornos de OppyTec v2.0
 * Referencia: .agent/estrategias/estrategia_entornos_y_despliegue_001.md
 */
export const RUNTIME_ENVIRONMENTS = [
  "local",
  "preview",
  "ci",
  "staging",
  "production",
] as const;

export type EnvironmentType = (typeof RUNTIME_ENVIRONMENTS)[number];

export interface RawRuntimeEnvMap {
  readonly VITE_ENVIRONMENT?: string;
  readonly VITE_ENV_NAMESPACE?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_WS_BASE_URL?: string;
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_OTEL_COLLECTOR_URL?: string;
  readonly VITE_UMAMI_ENABLED?: string;
  readonly VITE_UMAMI_WEBSITE_ID?: string;
  readonly VITE_AI_ASSISTANT_BRAND_NAME?: string;
}

declare global {
  interface Window {
    __OPPYTEC_RUNTIME_ENV__?: RawRuntimeEnvMap;
  }
}

const LOCAL_HOST_MARKERS = ["localhost", "127.0.0.1", "0.0.0.0"] as const;
const REMOTE_PROD_MARKERS = [
  "oppytec-prod",
  "oppytec_prod",
  "api.oppytec.com",
  "staging.oppytec.com",
] as const;

export const RuntimeEnvSchema = z
  .object({
    VITE_ENVIRONMENT: z.enum(RUNTIME_ENVIRONMENTS).default("local"),
    VITE_ENV_NAMESPACE: z
      .string()
      .regex(
        /^[a-z0-9_]{1,32}$/,
        "VITE_ENV_NAMESPACE debe contener solo minúsculas, números o guion bajo (1..32 chars)."
      )
      .default("default"),
    VITE_API_BASE_URL: z.string().min(1).default("/api/v1"),
    VITE_WS_BASE_URL: z.string().min(1).default("/api/v1/ws/realtime"),
    VITE_SENTRY_DSN: z.string().default(""),
    VITE_OTEL_COLLECTOR_URL: z.string().default(""),
    VITE_UMAMI_ENABLED: z
      .enum(["true", "false"])
      .default("false")
      .transform((val) => val === "true"),
    VITE_UMAMI_WEBSITE_ID: z.string().default(""),
    VITE_AI_ASSISTANT_BRAND_NAME: z
      .string()
      .min(2)
      .max(48)
      .default("OppyFy"),
  })
  .superRefine((env, ctx) => {
    const apiLower = env.VITE_API_BASE_URL.toLowerCase();
    const wsLower = env.VITE_WS_BASE_URL.toLowerCase();
    const otelLower = env.VITE_OTEL_COLLECTOR_URL.toLowerCase();

    // Guardrail 1: En production y staging queda prohibido apuntar a localhost o usar HTTP/WS sin TLS en URLs absolutas
    if (env.VITE_ENVIRONMENT === "production" || env.VITE_ENVIRONMENT === "staging") {
      for (const marker of LOCAL_HOST_MARKERS) {
        if (
          apiLower.includes(marker) ||
          wsLower.includes(marker) ||
          otelLower.includes(marker)
        ) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["VITE_API_BASE_URL"],
            message: `Fail-Fast Security Error: El entorno '${env.VITE_ENVIRONMENT}' prohíbe URLs que apunten a '${marker}'.`,
          });
        }
      }

      if (apiLower.startsWith("http://")) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["VITE_API_BASE_URL"],
          message: `Fail-Fast Security Error: En '${env.VITE_ENVIRONMENT}', VITE_API_BASE_URL debe usar 'https://' o una ruta relativa '/api/v1'.`,
        });
      }

      if (wsLower.startsWith("ws://")) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["VITE_WS_BASE_URL"],
          message: `Fail-Fast Security Error: En '${env.VITE_ENVIRONMENT}', VITE_WS_BASE_URL debe usar 'wss://' o una ruta relativa.`,
        });
      }
    }

    // Guardrail 2: En local y ci queda prohibido apuntar por accidente a hosts productivos o de staging
    if (env.VITE_ENVIRONMENT === "local" || env.VITE_ENVIRONMENT === "ci") {
      for (const prodMarker of REMOTE_PROD_MARKERS) {
        if (apiLower.includes(prodMarker) || wsLower.includes(prodMarker)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["VITE_API_BASE_URL"],
            message: `SecurityBoundaryViolation: El entorno '${env.VITE_ENVIRONMENT}' tiene prohibido conectarse a '${prodMarker}'.`,
          });
        }
      }
    }

    // Guardrail 3: En ci, Umami debe estar siempre desactivado (cero tráfico externo)
    if (env.VITE_ENVIRONMENT === "ci" && env.VITE_UMAMI_ENABLED) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["VITE_UMAMI_ENABLED"],
        message:
          "SecurityBoundaryViolation: En 'ci', VITE_UMAMI_ENABLED debe ser 'false' (100% aislado de internet público).",
      });
    }
  });

export type RuntimeEnv = z.output<typeof RuntimeEnvSchema>;

function readImportMetaEnv(): RawRuntimeEnvMap {
  const metaEnv = (import.meta.env ?? {}) as Record<string, string | undefined>;
  return {
    VITE_ENVIRONMENT: metaEnv["VITE_ENVIRONMENT"],
    VITE_ENV_NAMESPACE: metaEnv["VITE_ENV_NAMESPACE"],
    VITE_API_BASE_URL: metaEnv["VITE_API_BASE_URL"],
    VITE_WS_BASE_URL: metaEnv["VITE_WS_BASE_URL"],
    VITE_SENTRY_DSN: metaEnv["VITE_SENTRY_DSN"],
    VITE_OTEL_COLLECTOR_URL: metaEnv["VITE_OTEL_COLLECTOR_URL"],
    VITE_UMAMI_ENABLED: metaEnv["VITE_UMAMI_ENABLED"],
    VITE_UMAMI_WEBSITE_ID: metaEnv["VITE_UMAMI_WEBSITE_ID"],
    VITE_AI_ASSISTANT_BRAND_NAME: metaEnv["VITE_AI_ASSISTANT_BRAND_NAME"],
  };
}

/**
 * Lee primero `window.__OPPYTEC_RUNTIME_ENV__` (inyectado por `/runtime-env.js`)
 * y aplica fallback a `import.meta.env`, validando con Zod en modo Fail-Fast.
 */
export function parseRuntimeEnv(explicitSource?: RawRuntimeEnvMap): RuntimeEnv {
  const windowEnv: RawRuntimeEnvMap =
    typeof window !== "undefined" && window.__OPPYTEC_RUNTIME_ENV__
      ? window.__OPPYTEC_RUNTIME_ENV__
      : {};
  const fallbackEnv = readImportMetaEnv();

  const merged: RawRuntimeEnvMap = {
    VITE_ENVIRONMENT:
      explicitSource?.VITE_ENVIRONMENT ??
      windowEnv.VITE_ENVIRONMENT ??
      fallbackEnv.VITE_ENVIRONMENT ??
      "local",
    VITE_ENV_NAMESPACE:
      explicitSource?.VITE_ENV_NAMESPACE ??
      windowEnv.VITE_ENV_NAMESPACE ??
      fallbackEnv.VITE_ENV_NAMESPACE ??
      "default",
    VITE_API_BASE_URL:
      explicitSource?.VITE_API_BASE_URL ??
      windowEnv.VITE_API_BASE_URL ??
      fallbackEnv.VITE_API_BASE_URL ??
      "/api/v1",
    VITE_WS_BASE_URL:
      explicitSource?.VITE_WS_BASE_URL ??
      windowEnv.VITE_WS_BASE_URL ??
      fallbackEnv.VITE_WS_BASE_URL ??
      "/api/v1/ws/realtime",
    VITE_SENTRY_DSN:
      explicitSource?.VITE_SENTRY_DSN ??
      windowEnv.VITE_SENTRY_DSN ??
      fallbackEnv.VITE_SENTRY_DSN ??
      "",
    VITE_OTEL_COLLECTOR_URL:
      explicitSource?.VITE_OTEL_COLLECTOR_URL ??
      windowEnv.VITE_OTEL_COLLECTOR_URL ??
      fallbackEnv.VITE_OTEL_COLLECTOR_URL ??
      "",
    VITE_UMAMI_ENABLED:
      explicitSource?.VITE_UMAMI_ENABLED ??
      windowEnv.VITE_UMAMI_ENABLED ??
      fallbackEnv.VITE_UMAMI_ENABLED ??
      "false",
    VITE_UMAMI_WEBSITE_ID:
      explicitSource?.VITE_UMAMI_WEBSITE_ID ??
      windowEnv.VITE_UMAMI_WEBSITE_ID ??
      fallbackEnv.VITE_UMAMI_WEBSITE_ID ??
      "",
    VITE_AI_ASSISTANT_BRAND_NAME:
      explicitSource?.VITE_AI_ASSISTANT_BRAND_NAME ??
      windowEnv.VITE_AI_ASSISTANT_BRAND_NAME ??
      fallbackEnv.VITE_AI_ASSISTANT_BRAND_NAME ??
      "OppyFy",
  };

  return RuntimeEnvSchema.parse(merged);
}

let cachedEnv: RuntimeEnv | null = null;

export function getRuntimeEnv(forceRefresh = false): RuntimeEnv {
  if (!cachedEnv || forceRefresh) {
    cachedEnv = parseRuntimeEnv();
  }
  return cachedEnv;
}
