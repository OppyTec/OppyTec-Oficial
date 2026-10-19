export const FEATURE_MODULE_ROUTES = [
  { id: "analytics", labelEs: "Analítica & KPIs", labelEn: "Analytics & KPIs" },
  { id: "catalog", labelEs: "Catálogo & R2", labelEn: "Catalog & R2" },
  { id: "inventory", labelEs: "Inventario & Mermas", labelEn: "Inventory & Waste" },
  { id: "recipes", labelEs: "Recetas & Escandallos", labelEn: "Recipes & BOM" },
  { id: "procurement", labelEs: "Compras & OCR DTE", labelEn: "Procurement & DTE" },
  { id: "operations", labelEs: "Operaciones & POS", labelEn: "Operations & POS" },
  { id: "oppyfy", labelEs: "Asistente IA OppyFy", labelEn: "OppyFy AI Assistant" },
  { id: "rbac-and-audit", labelEs: "RBAC 3-Niveles & Auditoría", labelEn: "3-Level RBAC & Audit" },
  { id: "platform-admin", labelEs: "SuperAdmin & Observabilidad", labelEn: "SuperAdmin & Observability" },
  { id: "auth", labelEs: "Sesión & Impersonación", labelEn: "Session & Impersonation" },
] as const;

export type FeatureRouteId = (typeof FEATURE_MODULE_ROUTES)[number]["id"];

export interface SidebarProps {
  readonly activeFeature: FeatureRouteId;
  readonly onSelectFeature: (feature: FeatureRouteId) => void;
  readonly showAllFeatures: boolean;
  readonly onToggleShowAll: () => void;
  readonly language?: "es" | "en";
}

export function Sidebar({
  activeFeature,
  onSelectFeature,
  showAllFeatures,
  onToggleShowAll,
  language = "es",
}: SidebarProps) {
  return (
    <aside
      aria-label="Feature Navigation Sidebar"
      data-testid="app-sidebar"
      className="glass-card flex flex-col gap-1.5 rounded-xl p-3"
    >
      <div className="mb-1 flex items-center justify-between border-b border-border pb-2">
        <span className="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">
          10 Módulos v2.0
        </span>
        <button
          type="button"
          data-testid="sidebar-toggle-all-views"
          onClick={onToggleShowAll}
          className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary/15 px-2.5 py-1 font-mono text-[11px] font-semibold text-primary"
        >
          {showAllFeatures ? "Vista Única" : "Ver 10 Módulos"}
        </button>
      </div>
      <nav className="flex flex-wrap gap-1.5 lg:flex-col">
        {FEATURE_MODULE_ROUTES.map((route) => {
          const isSelected = activeFeature === route.id;
          return (
            <button
              key={route.id}
              type="button"
              data-testid={`nav-feature-${route.id}`}
              aria-current={isSelected ? "page" : undefined}
              onClick={() => onSelectFeature(route.id)}
              className={`touch-target inline-flex min-h-[44px] items-center justify-between rounded-lg px-3 py-2 text-left text-xs font-semibold transition-all ${
                isSelected
                  ? "animate-perimeter-glow bg-primary text-primary-foreground"
                  : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
              }`}
            >
              <span>{language === "en" ? route.labelEn : route.labelEs}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
