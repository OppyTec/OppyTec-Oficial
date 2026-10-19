import { Palette } from "lucide-react";
import { useMemo, useState } from "react";
import { AppProviders } from "@/app/providers";
import { AppRouter } from "@/app/router";
import {
  AppLayout,
  type FeatureRouteId,
  OFFICIAL_TENANT_OPTIONS,
  OFFICIAL_WAREHOUSES,
  type TenantOption,
} from "@/shared/components/layout";
import {
  GASTRONOMIC_ICONS,
  PRESET_COLORS,
} from "@/shared/components/ui";
import { getRuntimeEnv } from "@/shared/config/env";
import { useTheme } from "@/shared/hooks";
import { getActiveLanguage, type SupportedLanguage } from "@/shared/i18n";
import { createTraceHeaders } from "@/shared/telemetry/otel";
import { captureFrontendException } from "@/shared/telemetry/sentry";
import { resolveUmamiConfig } from "@/shared/telemetry/umami";

export function App() {
  const runtimeEnv = useMemo(() => getRuntimeEnv(), []);
  const umamiConfig = useMemo(() => resolveUmamiConfig(), []);
  const { theme, setTheme } = useTheme("ocean-blue");

  const [activeTenant, setActiveTenant] = useState<TenantOption>(
    () =>
      OFFICIAL_TENANT_OPTIONS[0] ?? {
        holdingId: "holding-gastro-sur",
        holdingName: "Holding Gastronómico Sur SpA",
        tenantId: "tenant_rest_central",
        tenantName: "Restaurante Central Santiago",
        rut: "76.543.210-K",
      }
  );
  const [activeWarehouseId, setActiveWarehouseId] = useState<string>(
    OFFICIAL_WAREHOUSES[0]?.id ?? "bod-cocina-central"
  );
  const [activeFeature, setActiveFeature] =
    useState<FeatureRouteId>("analytics");
  const [showAllFeatures, setShowAllFeatures] = useState<boolean>(true);
  const [language, setLanguage] = useState<SupportedLanguage>(() =>
    getActiveLanguage()
  );
  const [traceSeed, setTraceSeed] = useState<number>(0);

  const traceHeaders = useMemo(() => {
    void traceSeed;
    return createTraceHeaders();
  }, [traceSeed]);

  const handleSimulatedBoundaryCheck = (): void => {
    captureFrontendException(new Error("HealthCheckBoundary"), {
      traceId: traceHeaders["X-Trace-ID"],
    });
  };

  return (
    <AppProviders
      holdingId={activeTenant.holdingId}
      tenantId={activeTenant.tenantId}
    >
      <AppLayout
        brandName={runtimeEnv.VITE_AI_ASSISTANT_BRAND_NAME}
        environmentLabel={`${runtimeEnv.VITE_ENVIRONMENT}:${runtimeEnv.VITE_ENV_NAMESPACE}`}
        activeTheme={theme}
        onSelectTheme={setTheme}
        activeTenantId={activeTenant.tenantId}
        onSelectTenant={setActiveTenant}
        activeWarehouseId={activeWarehouseId}
        onSelectWarehouse={setActiveWarehouseId}
        activeFeature={activeFeature}
        onSelectFeature={setActiveFeature}
        showAllFeatures={showAllFeatures}
        onToggleShowAll={() => setShowAllFeatures((prev) => !prev)}
        language={language}
        onLanguageChanged={setLanguage}
      >
        {/* Resumen del ADN Visual Legacy (42 Colores + 49 Íconos + Telemetría 4-Pilares) */}
        <section
          data-testid="legacy-dna-summary"
          className="glass-card rounded-xl p-4"
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Palette className="h-5 w-5 text-primary" aria-hidden="true" />
              <h2 className="text-sm font-bold md:text-base">
                {`ADN Visual Legacy: 42 Colores Predefinidos (6x7) & ${String(GASTRONOMIC_ICONS.length)} Íconos Gastronómicos`}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                data-testid="renew-trace-btn"
                onClick={() => setTraceSeed((prev) => prev + 1)}
                className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground"
              >
                Renovar X-Trace-ID
              </button>
              <button
                type="button"
                data-testid="trace-badge-btn"
                onClick={handleSimulatedBoundaryCheck}
                className="touch-target inline-flex min-h-[44px] items-center rounded-md border border-border bg-card px-3 py-1.5 font-mono text-xs text-card-foreground"
              >
                {`X-Trace-ID: ${traceHeaders["X-Trace-ID"].slice(0, 12)} · Umami(${String(umamiConfig.enabled)})`}
              </button>
            </div>
          </div>
          <div className="grid grid-cols-7 gap-1.5">
            {PRESET_COLORS.map((hex) => (
              <div
                key={hex}
                title={hex}
                data-preset-color={hex}
                className="flex h-5 w-full items-center justify-center rounded-sm border border-border bg-secondary/60 font-mono text-[10px] text-muted-foreground"
              >
                {hex.slice(1, 4)}
              </div>
            ))}
          </div>
        </section>

        <AppRouter
          activeFeature={activeFeature}
          showAllFeatures={showAllFeatures}
        />
      </AppLayout>
    </AppProviders>
  );
}
