import { Moon, Palette, ShieldCheck, Sun, Waves } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getRuntimeEnv } from "@/shared/config/env";
import { createTraceHeaders } from "@/shared/telemetry/otel";
import { captureFrontendException } from "@/shared/telemetry/sentry";
import { resolveUmamiConfig, trackUmamiEvent } from "@/shared/telemetry/umami";
import {
  OFFICIAL_THEMES,
  type OppyTecTheme,
  PRESET_COLORS,
} from "../../tailwind.config";

const SHELL_I18N_DICTIONARY = {
  es: {
    "shell.brand.subtitle": "Software de Grado Operacional y Financiero v2.0",
    "shell.theme.light": "Claro",
    "shell.theme.dark": "Oscuro",
    "shell.theme.ocean-blue": "Ocean Blue",
    "shell.env.badge": "Entorno Validado (Zod + SHA-256)",
    "shell.trace.badge": "X-Trace-ID Activo",
    "shell.mobile.title": "Arquitectura Mobile-First & ADN Visual Legacy",
    "shell.mobile.description":
      "3 temas oficiales (light / dark / ocean-blue), targets táctiles >= 44px, 42 colores gastronómicos y observabilidad 4-pilares.",
    "shell.palette.title": "Paleta Gastronómica de 42 Colores (PRESET_COLORS 6x7)",
    "shell.telemetry.title": "Estado de Telemetría 4-Pilares",
    "shell.action.verify_trace": "Renovar X-Trace-ID",
  },
} as const;

type ShellLocaleKey = keyof (typeof SHELL_I18N_DICTIONARY)["es"];

function translateShellKey(key: ShellLocaleKey): string {
  return SHELL_I18N_DICTIONARY.es[key];
}

function applyDocumentTheme(theme: OppyTecTheme): void {
  if (typeof document === "undefined") {
    return;
  }
  const root = document.documentElement;
  root.classList.remove("light", "dark", "ocean-blue");
  root.classList.add(theme);
  root.setAttribute("data-theme", theme);
}

export function App() {
  const runtimeEnv = useMemo(() => getRuntimeEnv(), []);
  const umamiConfig = useMemo(() => resolveUmamiConfig(), []);
  const [activeTheme, setActiveTheme] = useState<OppyTecTheme>("ocean-blue");
  const [traceSeed, setTraceSeed] = useState<number>(0);

  const traceHeaders = useMemo(() => {
    void traceSeed;
    return createTraceHeaders();
  }, [traceSeed]);

  useEffect(() => {
    applyDocumentTheme(activeTheme);
    trackUmamiEvent("theme_changed", window.location.pathname, {
      theme: activeTheme,
    });
  }, [activeTheme]);

  const handleRenewTrace = (): void => {
    setTraceSeed((prev) => prev + 1);
  };

  const handleSimulatedBoundaryCheck = (): void => {
    captureFrontendException(new Error("HealthCheckBoundary"), {
      traceId: traceHeaders["X-Trace-ID"],
    });
  };

  return (
    <div className="min-h-dvh w-full overflow-x-hidden p-4 md:p-6 lg:p-8">
      <header className="glass-card mx-auto mb-6 flex max-w-7xl flex-col gap-4 rounded-xl p-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="touch-target flex items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-md">
            <ShieldCheck className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight md:text-2xl">
              {runtimeEnv.VITE_AI_ASSISTANT_BRAND_NAME}
            </h1>
            <p className="text-xs text-muted-foreground md:text-sm">
              {translateShellKey("shell.brand.subtitle")}
            </p>
          </div>
        </div>

        {/* Conmutador de los 3 Temas Oficiales (Mobile-First >= 44px touch targets) */}
        <nav
          aria-label="Theme Switcher"
          className="flex flex-wrap items-center gap-2"
        >
          {OFFICIAL_THEMES.map((theme) => {
            const isSelected = activeTheme === theme;
            return (
              <button
                key={theme}
                type="button"
                onClick={() => setActiveTheme(theme)}
                aria-pressed={isSelected}
                className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-all ${
                  isSelected
                    ? "animate-perimeter-glow bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {theme === "light" && <Sun className="h-4 w-4" aria-hidden="true" />}
                {theme === "dark" && <Moon className="h-4 w-4" aria-hidden="true" />}
                {theme === "ocean-blue" && (
                  <Waves className="h-4 w-4" aria-hidden="true" />
                )}
                <span>{translateShellKey(`shell.theme.${theme}`)}</span>
              </button>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 md:grid-cols-2 lg:gap-6">
        <section className="glass-card rounded-xl p-4 md:p-6">
          <div className="mb-3 flex items-center justify-between gap-2">
            <span className="rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-medium text-primary">
              {translateShellKey("shell.env.badge")}
            </span>
            <span className="rounded-full bg-secondary px-2.5 py-0.5 font-mono text-xs text-muted-foreground">
              {`${runtimeEnv.VITE_ENVIRONMENT}:${runtimeEnv.VITE_ENV_NAMESPACE}`}
            </span>
          </div>
          <h2 className="mb-2 text-lg font-semibold md:text-xl">
            {translateShellKey("shell.mobile.title")}
          </h2>
          <p className="mb-4 text-sm text-muted-foreground">
            {translateShellKey("shell.mobile.description")}
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleRenewTrace}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm"
            >
              {translateShellKey("shell.action.verify_trace")}
            </button>
            <button
              type="button"
              onClick={handleSimulatedBoundaryCheck}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-md border border-border bg-card px-3 py-2 font-mono text-xs text-card-foreground"
            >
              {`${translateShellKey("shell.trace.badge")}: ${traceHeaders["X-Trace-ID"].slice(0, 12)}`}
            </button>
          </div>
        </section>

        <section className="glass-card rounded-xl p-4 md:p-6">
          <div className="mb-3 flex items-center gap-2">
            <Palette className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="text-lg font-semibold md:text-xl">
              {translateShellKey("shell.palette.title")}
            </h2>
          </div>
          <div className="grid grid-cols-7 gap-1.5">
            {PRESET_COLORS.map((hex) => (
              <div
                key={hex}
                title={hex}
                data-preset-color={hex}
                className="flex h-6 w-full items-center justify-center rounded-sm border border-border bg-secondary/60 font-mono text-[10px] text-muted-foreground shadow-sm"
              >
                {hex.slice(1, 4)}
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
            <span>{translateShellKey("shell.telemetry.title")}</span>
            <span className="font-mono">
              {`OTel + Sentry + Umami(${String(umamiConfig.enabled)})`}
            </span>
          </div>
        </section>
      </main>
    </div>
  );
}
export default App;
