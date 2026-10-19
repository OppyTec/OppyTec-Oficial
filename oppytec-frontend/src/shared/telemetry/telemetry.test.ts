import { afterEach, describe, expect, it } from "vitest";
import { getRuntimeEnv } from "@/shared/config/env";
import {
  buildW3CTraceparent,
  createTraceHeaders,
  generateSpanId,
  generateTraceId,
} from "./otel";
import {
  REDACTED_PLACEHOLDER,
  captureFrontendException,
  scrubFrontendPii,
} from "./sentry";
import {
  resolveUmamiConfig,
  sanitizeAnalyticsPath,
  trackUmamiEvent,
} from "./umami";

describe("Frontend Telemetry 4-Pillar Suite (OTel, Sentry PII Redactor & Umami)", () => {
  afterEach(() => {
    if (typeof window !== "undefined") {
      delete window.__OPPYTEC_RUNTIME_ENV__;
    }
    getRuntimeEnv(true);
  });

  describe("OpenTelemetry (otel.ts)", () => {
    it("generates valid W3C traceparent and X-Trace-ID headers", () => {
      window.__OPPYTEC_RUNTIME_ENV__ = {
        VITE_ENVIRONMENT: "preview",
        VITE_ENV_NAMESPACE: "wt_p1_3",
      };
      getRuntimeEnv(true);

      const traceId = generateTraceId();
      const spanId = generateSpanId();
      expect(traceId).toMatch(/^[0-9a-f]{32}$/);
      expect(spanId).toMatch(/^[0-9a-f]{16}$/);

      const traceparent = buildW3CTraceparent(traceId, spanId, true);
      expect(traceparent).toBe(`00-${traceId}-${spanId}-01`);

      const headers = createTraceHeaders({
        traceId,
        tenantSchema: "tenant_pacifico_centro",
      });
      expect(headers["X-Trace-ID"]).toBe(traceId);
      expect(headers.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
      expect(headers["X-Env-Namespace"]).toBe("wt_p1_3");
      expect(headers["X-Tenant-Schema"]).toBe("tenant_pacifico_centro");
    });
  });

  describe("Sentry / GlitchTip PII Redactor (sentry.ts)", () => {
    it("redacts passwords, tokens, authorization headers and tax_id recursively", () => {
      const dirtyPayload = {
        module: "inventory",
        password: "super-secret-password",
        nested: {
          access_token: "jwt-12345",
          refresh_token: "refresh-67890",
          tax_id: "76.123.456-7",
          headers: {
            Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.a.b",
            Cookie: "session_id=xyz",
          },
          safeCount: 42,
        },
        note: "Header leaked Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig in error",
      };

      const clean = scrubFrontendPii(dirtyPayload);
      expect(clean.module).toBe("inventory");
      expect(clean.password).toBe(REDACTED_PLACEHOLDER);
      expect(clean.nested.access_token).toBe(REDACTED_PLACEHOLDER);
      expect(clean.nested.refresh_token).toBe(REDACTED_PLACEHOLDER);
      expect(clean.nested.tax_id).toBe(REDACTED_PLACEHOLDER);
      expect(clean.nested.headers.Authorization).toBe(REDACTED_PLACEHOLDER);
      expect(clean.nested.headers.Cookie).toBe(REDACTED_PLACEHOLDER);
      expect(clean.nested.safeCount).toBe(42);
      expect(clean.note).toContain(`Bearer ${REDACTED_PLACEHOLDER}`);
    });

    it("captures frontend exceptions linked to X-Trace-ID with sendDefaultPii=false", () => {
      const traceId = generateTraceId();
      const report = captureFrontendException(
        new Error("Failed with Bearer secretToken123"),
        {
          traceId,
          tenantSchema: "tenant_pacifico_centro",
          holdingId: "holding_01",
          extra: {
            api_key: "sk-live-secret",
            bodegaId: 3,
          },
        }
      );

      expect(report.traceId).toBe(traceId);
      expect(report.sendDefaultPii).toBe(false);
      expect(report.tenantSchema).toBe("tenant_pacifico_centro");
      expect(report.errorMessage).toContain(`Bearer ${REDACTED_PLACEHOLDER}`);
      expect(report.sanitizedExtra["api_key"]).toBe(REDACTED_PLACEHOLDER);
      expect(report.sanitizedExtra["bodegaId"]).toBe(3);
    });
  });

  describe("Umami Cookie-less Analytics (umami.ts)", () => {
    it("remains disabled in local and preview even if not configured", () => {
      window.__OPPYTEC_RUNTIME_ENV__ = {
        VITE_ENVIRONMENT: "local",
        VITE_UMAMI_ENABLED: "false",
      };
      getRuntimeEnv(true);

      const cfg = resolveUmamiConfig();
      expect(cfg.enabled).toBe(false);
      expect(cfg.cookieLess).toBe(true);
    });

    it("enables Umami in production when VITE_UMAMI_ENABLED === 'true' and strips tokens from URLs", () => {
      window.__OPPYTEC_RUNTIME_ENV__ = {
        VITE_ENVIRONMENT: "production",
        VITE_API_BASE_URL: "https://app.oppytec.com/api/v1",
        VITE_WS_BASE_URL: "wss://app.oppytec.com/api/v1/ws/realtime",
        VITE_UMAMI_ENABLED: "true",
        VITE_UMAMI_WEBSITE_ID: "umami-site-prod-001",
      };
      getRuntimeEnv(true);

      const cleanUrl = sanitizeAnalyticsPath(
        "https://app.oppytec.com/auth/reset/eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig?token=secret&email=user@test.com#hash"
      );
      expect(cleanUrl).toBe("/auth/reset/[REDACTED_TOKEN]");

      const tracked = trackUmamiEvent(
        "module_opened",
        "/inventory/stock?jwt=secret",
        {
          moduleName: "inventory",
          token: "should-be-redacted",
        }
      );

      expect(tracked.dispatched).toBe(true);
      expect(tracked.sanitizedPath).toBe("/inventory/stock");
      expect(tracked.payload["moduleName"]).toBe("inventory");
      expect(tracked.payload["token"]).toBe(REDACTED_PLACEHOLDER);
    });
  });
});
