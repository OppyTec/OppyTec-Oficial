import { useState } from "react";

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

export const PLAN_BASICO_10_NAV_ITEMS = [
  {
    slug: "inicio",
    labelEs: "1. Inicio",
    labelEn: "1. Home Dashboard",
    targetFeature: "analytics",
  },
  {
    slug: "registro_de_consumo",
    labelEs: "2. Registro de Consumo",
    labelEn: "2. Consumption Log",
    targetFeature: "operations",
  },
  {
    slug: "registro_de_stock",
    labelEs: "3. Registro de Stock",
    labelEn: "3. Stock Entry",
    targetFeature: "inventory",
  },
  {
    slug: "gestion_de_productos",
    labelEs: "4. Gestión de Productos",
    labelEn: "4. Product Management",
    targetFeature: "catalog",
  },
  {
    slug: "gestion_de_mermas",
    labelEs: "5. Gestión de Mermas",
    labelEn: "5. Waste Management",
    targetFeature: "inventory",
  },
  {
    slug: "recuento_unificado",
    labelEs: "6. Recuento (+ Historial)",
    labelEn: "6. Physical Count (+ History)",
    targetFeature: "inventory",
  },
  {
    slug: "notificaciones",
    labelEs: "7. Notificaciones",
    labelEn: "7. Notifications",
    targetFeature: "operations",
  },
  {
    slug: "alertas",
    labelEs: "8. Alertas",
    labelEn: "8. Stock & FEFO Alerts",
    targetFeature: "inventory",
  },
  {
    slug: "historial",
    labelEs: "9. Historial",
    labelEn: "9. Movement History",
    targetFeature: "rbac-and-audit",
  },
  {
    slug: "usuarios",
    labelEs: "10. Usuarios",
    labelEn: "10. Users & Seats",
    targetFeature: "rbac-and-audit",
  },
] as const;

export type BasicPlanNavItem = (typeof PLAN_BASICO_10_NAV_ITEMS)[number];

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
  const [showBasicPlanMenu, setShowBasicPlanMenu] = useState<boolean>(false);

  return (
    <aside
      aria-label="Feature Navigation Sidebar"
      data-testid="app-sidebar"
      className="glass-card flex flex-col gap-1.5 rounded-xl p-3"
    >
      <div className="mb-1 flex flex-wrap items-center justify-between gap-1.5 border-b border-border pb-2">
        <span className="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">
          {showBasicPlanMenu ? "Plan Básico (10)" : "10 Módulos v2.0"}
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            data-testid="sidebar-toggle-plan-basico"
            onClick={() => setShowBasicPlanMenu((prev) => !prev)}
            className="touch-target inline-flex min-h-[44px] items-center rounded-md border border-primary/30 bg-primary/10 px-2 py-1 font-mono text-[10px] font-semibold text-primary"
          >
            {showBasicPlanMenu ? "Suite v2.0" : "Plan Básico"}
          </button>
          <button
            type="button"
            data-testid="sidebar-toggle-all-views"
            onClick={onToggleShowAll}
            className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary/15 px-2.5 py-1 font-mono text-[11px] font-semibold text-primary"
          >
            {showAllFeatures ? "Vista Única" : "Ver 10 Módulos"}
          </button>
        </div>
      </div>

      {showBasicPlanMenu && (
        <div
          data-testid="sidebar-plan-basico-list"
          className="mb-2 flex flex-col gap-1 rounded-lg border border-primary/30 bg-primary/5 p-2"
        >
          <span className="font-mono text-[10px] font-bold uppercase text-primary">
            Menú Cliente — Plan Básico (10 Módulos)
          </span>
          {PLAN_BASICO_10_NAV_ITEMS.map((item) => (
            <button
              key={item.slug}
              type="button"
              data-testid={`nav-basic-${item.slug}`}
              onClick={() => onSelectFeature(item.targetFeature)}
              className="touch-target inline-flex min-h-[44px] items-center justify-between rounded-md bg-card px-2.5 py-1.5 text-left text-xs font-semibold text-foreground hover:bg-secondary"
            >
              <span>{language === "en" ? item.labelEn : item.labelEs}</span>
            </button>
          ))}
        </div>
      )}

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
