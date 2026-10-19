import { getRuntimeEnv } from "@/shared/config/env";

/**
 * Pilar 1 de Observabilidad en Frontend: OpenTelemetry (W3C Trace Context + X-Trace-ID)
 * Genera trazas distribuidas extremo a extremo hacia FastAPI (src/core/observability.py).
 */
export interface TraceContextHeaders {
  readonly "X-Trace-ID": string;
  readonly traceparent: string;
  readonly "X-Env-Namespace": string;
  readonly "X-Tenant-Schema"?: string;
}

export interface ActiveSpanContext {
  readonly traceId: string;
  readonly spanId: string;
  readonly traceparent: string;
  readonly namespace: string;
  readonly tenantSchema?: string;
}

function generateRandomHex(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < byteLength; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function generateTraceId(): string {
  return generateRandomHex(16); // 32 caracteres hexadecimales (128-bit W3C trace-id)
}

export function generateSpanId(): string {
  return generateRandomHex(8); // 16 caracteres hexadecimales (64-bit W3C parent-id)
}

export function buildW3CTraceparent(
  traceId = generateTraceId(),
  spanId = generateSpanId(),
  sampled = true
): string {
  const flags = sampled ? "01" : "00";
  return `00-${traceId}-${spanId}-${flags}`;
}

export function createSpanContext(options?: {
  readonly traceId?: string;
  readonly tenantSchema?: string;
}): ActiveSpanContext {
  const env = getRuntimeEnv();
  const traceId = options?.traceId ?? generateTraceId();
  const spanId = generateSpanId();
  const traceparent = buildW3CTraceparent(traceId, spanId, true);

  return {
    traceId,
    spanId,
    traceparent,
    namespace: env.VITE_ENV_NAMESPACE,
    ...(options?.tenantSchema ? { tenantSchema: options.tenantSchema } : {}),
  };
}

/**
 * Construye las cabeceras HTTP para propagar en cada petición Axios/Fetch hacia FastAPI.
 */
export function createTraceHeaders(options?: {
  readonly traceId?: string;
  readonly tenantSchema?: string;
}): TraceContextHeaders {
  const span = createSpanContext(options);
  return {
    "X-Trace-ID": span.traceId,
    traceparent: span.traceparent,
    "X-Env-Namespace": span.namespace,
    ...(span.tenantSchema ? { "X-Tenant-Schema": span.tenantSchema } : {}),
  };
}
