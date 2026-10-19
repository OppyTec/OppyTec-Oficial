import { Moon, ShieldCheck, Sun, Waves, Wifi } from "lucide-react";
import {
  OFFICIAL_THEMES,
  type OppyTecTheme,
} from "@/shared/components/ui/designTokens";
import { CurrencySelector } from "@/shared/currency";
import { LanguageFlagSelector, translateKey } from "@/shared/i18n";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { BodegaSelector } from "./BodegaSelector";
import {
  HoldingTenantSwitcher,
  type TenantOption,
} from "./HoldingTenantSwitcher";

export interface NavbarProps {
  readonly brandName: string;
  readonly environmentLabel: string;
  readonly activeTheme: OppyTecTheme;
  readonly onSelectTheme: (theme: OppyTecTheme) => void;
  readonly activeTenantId: string;
  readonly onSelectTenant: (tenant: TenantOption) => void;
  readonly activeWarehouseId: string;
  readonly onSelectWarehouse: (warehouseId: string) => void;
  readonly onLanguageChanged?: (lang: "es" | "en") => void;
}

const THEME_LABELS: Readonly<Record<OppyTecTheme, string>> = {
  light: "Claro",
  dark: "Oscuro",
  "ocean-blue": "Ocean Blue",
};

export function Navbar({
  brandName,
  environmentLabel,
  activeTheme,
  onSelectTheme,
  activeTenantId,
  onSelectTenant,
  activeWarehouseId,
  onSelectWarehouse,
  onLanguageChanged,
}: NavbarProps) {
  const { connected, channelKey, lastEventId } = useRealtimeSync();

  return (
    <header
      data-testid="app-navbar"
      className="glass-card mx-auto mb-4 flex max-w-7xl flex-col gap-3 rounded-xl p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="touch-target flex items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-md">
            <ShieldCheck className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight md:text-xl">
                {brandName}
              </h1>
              <span
                data-testid="navbar-env-badge"
                className="rounded-full bg-primary/15 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-primary"
              >
                {environmentLabel}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {translateKey("common", "app.subtitle")}
            </p>
          </div>
        </div>

        {/* Conmutador de los 3 Temas Oficiales (light, dark, ocean-blue) */}
        <nav
          aria-label="Theme Switcher"
          className="flex flex-wrap items-center gap-1.5"
        >
          {OFFICIAL_THEMES.map((theme) => {
            const isSelected = activeTheme === theme;
            return (
              <button
                key={theme}
                type="button"
                data-testid={`theme-btn-${theme}`}
                onClick={() => onSelectTheme(theme)}
                aria-pressed={isSelected}
                className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center gap-1.5 rounded-md px-3 py-2 text-xs font-semibold transition-all ${
                  isSelected
                    ? "animate-perimeter-glow bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {theme === "light" && (
                  <Sun className="h-4 w-4" aria-hidden="true" />
                )}
                {theme === "dark" && (
                  <Moon className="h-4 w-4" aria-hidden="true" />
                )}
                {theme === "ocean-blue" && (
                  <Waves className="h-4 w-4" aria-hidden="true" />
                )}
                <span>{THEME_LABELS[theme]}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Barra Operativa Multi-Holding, Multi-Bodega, Multi-Idioma (SVG Flags) y Multi-Moneda FX */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
        <div className="flex flex-wrap items-center gap-2">
          <HoldingTenantSwitcher
            activeTenantId={activeTenantId}
            onSelectTenant={onSelectTenant}
          />
          <BodegaSelector
            activeWarehouseId={activeWarehouseId}
            onSelectWarehouse={onSelectWarehouse}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            data-testid="realtime-ws-badge"
            title={channelKey}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/50 px-2.5 py-1 font-mono text-[11px] font-semibold text-foreground"
          >
            <Wifi
              className={`h-3.5 w-3.5 ${
                connected ? "text-primary" : "text-destructive"
              }`}
              aria-hidden="true"
            />
            <span>{`WS /api/v1/ws/realtime (#${lastEventId})`}</span>
          </span>
          <CurrencySelector />
          <LanguageFlagSelector onLanguageChange={onLanguageChanged} />
        </div>
      </div>
    </header>
  );
}
