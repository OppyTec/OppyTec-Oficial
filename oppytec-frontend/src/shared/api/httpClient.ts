import { getRuntimeEnv } from "@/shared/config/env";
import { getActiveLanguage } from "@/shared/i18n";
import { createTraceHeaders } from "@/shared/telemetry/otel";

export interface HttpRequestContext {
  readonly accessToken?: string;
  readonly holdingId: string;
  readonly tenantId: string;
  readonly warehouseId?: string;
}

export interface ApiEnvelope<TData> {
  readonly data: TData;
  readonly traceId: string;
  readonly timestampIso: string;
  readonly tenantId: string;
}

let activeContext: HttpRequestContext = {
  holdingId: "holding-gastro-sur",
  tenantId: "tenant_rest_central",
  warehouseId: "bod-cocina-central",
};

export function setHttpRequestContext(next: Partial<HttpRequestContext>): HttpRequestContext {
  activeContext = {
    ...activeContext,
    ...next,
  };
  return activeContext;
}

export function getHttpRequestContext(): HttpRequestContext {
  return activeContext;
}

/**
 * Builds canonical HTTP headers for OppyTec API v1 requests:
 * `Authorization`, `X-Tenant-ID`, `X-Holding-ID`, `X-Warehouse-ID`, `X-Trace-ID`, `traceparent`, and `Accept-Language`.
 */
export function buildApiHeaders(
  overrideContext?: Partial<HttpRequestContext>
): Readonly<Record<string, string>> {
  const ctx: HttpRequestContext = {
    ...activeContext,
    ...(overrideContext ?? {}),
  };
  const trace = createTraceHeaders();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept-Language": getActiveLanguage(),
    "X-Holding-ID": ctx.holdingId,
    "X-Tenant-ID": ctx.tenantId,
    "X-Trace-ID": trace["X-Trace-ID"],
    traceparent: trace.traceparent,
  };
  if (ctx.warehouseId) {
    headers["X-Warehouse-ID"] = ctx.warehouseId;
  }
  if (ctx.accessToken) {
    headers.Authorization = `Bearer ${ctx.accessToken}`;
  }
  return headers;
}

export function resolveApiEndpointUrl(path: string): string {
  const env = getRuntimeEnv();
  const normalizedBase = env.VITE_API_BASE_URL.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export async function apiRequest<TResponse>(
  path: string,
  options?: {
    readonly method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
    readonly body?: unknown;
    readonly context?: Partial<HttpRequestContext>;
    readonly fallbackData?: TResponse;
  }
): Promise<ApiEnvelope<TResponse>> {
  const headers = buildApiHeaders(options?.context);
  const traceId = headers["X-Trace-ID"] ?? "00000000000000000000000000000000";
  const tenantId = headers["X-Tenant-ID"] ?? activeContext.tenantId;

  try {
    const response = await fetch(resolveApiEndpointUrl(path), {
      method: options?.method ?? "GET",
      headers,
      body: options?.body !== undefined ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      if (options?.fallbackData !== undefined) {
        return {
          data: options.fallbackData,
          traceId,
          timestampIso: new Date().toISOString(),
          tenantId,
        };
      }
      throw new Error(`HTTP ${String(response.status)} on ${path}`);
    }

    const parsed = (await response.json()) as TResponse;
    return {
      data: parsed,
      traceId: response.headers.get("X-Trace-ID") ?? traceId,
      timestampIso: new Date().toISOString(),
      tenantId,
    };
  } catch (err) {
    if (options?.fallbackData !== undefined) {
      return {
        data: options.fallbackData,
        traceId,
        timestampIso: new Date().toISOString(),
        tenantId,
      };
    }
    throw err;
  }
}
