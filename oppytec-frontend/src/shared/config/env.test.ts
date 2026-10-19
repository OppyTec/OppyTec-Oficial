import { afterEach, describe, expect, it } from "vitest";
import {
  RUNTIME_ENVIRONMENTS,
  getRuntimeEnv,
  parseRuntimeEnv,
} from "./env";

describe("RuntimeEnvSchema & parseRuntimeEnv (Invarianza SHA-256 + Fail-Fast)", () => {
  afterEach(() => {
    if (typeof window !== "undefined") {
      delete window.__OPPYTEC_RUNTIME_ENV__;
    }
    getRuntimeEnv(true);
  });

  it("prioritizes window.__OPPYTEC_RUNTIME_ENV__ injected by /runtime-env.js over defaults", () => {
    window.__OPPYTEC_RUNTIME_ENV__ = {
      VITE_ENVIRONMENT: "preview",
      VITE_ENV_NAMESPACE: "wt_p1_3",
      VITE_API_BASE_URL: "https://preview-wt3.oppytec.dev/api/v1",
      VITE_WS_BASE_URL: "wss://preview-wt3.oppytec.dev/api/v1/ws/realtime",
      VITE_UMAMI_ENABLED: "false",
      VITE_AI_ASSISTANT_BRAND_NAME: "OppyFy",
    };

    const env = getRuntimeEnv(true);
    expect(env.VITE_ENVIRONMENT).toBe("preview");
    expect(env.VITE_ENV_NAMESPACE).toBe("wt_p1_3");
    expect(env.VITE_API_BASE_URL).toBe("https://preview-wt3.oppytec.dev/api/v1");
    expect(env.VITE_UMAMI_ENABLED).toBe(false);
  });

  it("supports all 5 canonical environments when configured with valid boundaries", () => {
    expect(RUNTIME_ENVIRONMENTS).toEqual([
      "local",
      "preview",
      "ci",
      "staging",
      "production",
    ]);

    const prodEnv = parseRuntimeEnv({
      VITE_ENVIRONMENT: "production",
      VITE_ENV_NAMESPACE: "prod_main",
      VITE_API_BASE_URL: "https://app.oppytec.com/api/v1",
      VITE_WS_BASE_URL: "wss://app.oppytec.com/api/v1/ws/realtime",
      VITE_UMAMI_ENABLED: "true",
      VITE_UMAMI_WEBSITE_ID: "eb812340-1111-2222-3333-444455556666",
    });

    expect(prodEnv.VITE_ENVIRONMENT).toBe("production");
    expect(prodEnv.VITE_UMAMI_ENABLED).toBe(true);
  });

  it("blocks localhost URLs in production and staging (Fail-Fast Frontend)", () => {
    expect(() =>
      parseRuntimeEnv({
        VITE_ENVIRONMENT: "production",
        VITE_API_BASE_URL: "https://localhost:8000/api/v1",
      })
    ).toThrow(/Fail-Fast Security Error/);

    expect(() =>
      parseRuntimeEnv({
        VITE_ENVIRONMENT: "staging",
        VITE_WS_BASE_URL: "wss://127.0.0.1:8000/api/v1/ws/realtime",
      })
    ).toThrow(/Fail-Fast Security Error/);
  });

  it("blocks insecure http:// or ws:// URLs in production", () => {
    expect(() =>
      parseRuntimeEnv({
        VITE_ENVIRONMENT: "production",
        VITE_API_BASE_URL: "http://app.oppytec.com/api/v1",
      })
    ).toThrow(/Fail-Fast Security Error/);
  });

  it("blocks production hosts in local and ci environments", () => {
    expect(() =>
      parseRuntimeEnv({
        VITE_ENVIRONMENT: "local",
        VITE_API_BASE_URL: "https://api.oppytec.com/api/v1",
      })
    ).toThrow(/SecurityBoundaryViolation/);
  });

  it("rejects invalid environment names or malformed ENV_NAMESPACE", () => {
    expect(() =>
      parseRuntimeEnv({
        VITE_ENVIRONMENT: "unknown_env",
      })
    ).toThrow();

    expect(() =>
      parseRuntimeEnv({
        VITE_ENVIRONMENT: "preview",
        VITE_ENV_NAMESPACE: "INVALID-NAMESPACE-WITH-DASH!",
      })
    ).toThrow();
  });
});
