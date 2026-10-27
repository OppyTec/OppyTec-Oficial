import React from "react";
import { Package, ChefHat, Boxes, TrendingDown } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";

export type GestionTabKey = "productos" | "recetas" | "combos" | "mermas";

export interface GestionTabNavProps {
  activeTab: GestionTabKey;
  onSelectTab: (tab: GestionTabKey) => void;
}

export function GestionTabNav({ activeTab, onSelectTab }: GestionTabNavProps) {
  const { t } = useTranslation("recipes");

  const tabs: Array<{
    id: GestionTabKey;
    label: string;
    icon: React.ElementType;
    color: string;
    badgeCount?: number;
  }> = [
    {
      id: "productos",
      label: t("tabs.productos", "Insumos & Productos"),
      icon: Package,
      color: "#eab308",
    },
    {
      id: "recetas",
      label: t("tabs.recetas", "Recetas & Escandallos"),
      icon: ChefHat,
      color: "#f59e0b",
    },
    {
      id: "combos",
      label: t("tabs.combos", "Combos & Promociones"),
      icon: Boxes,
      color: "#ec4899",
    },
    {
      id: "mermas",
      label: t("tabs.mermas", "Control de Mermas"),
      icon: TrendingDown,
      color: "#ef4444",
    },
  ];

  return (
    <nav
      role="tablist"
      aria-label={t("tabs.aria_label")}
      className="w-full flex items-center justify-start sm:justify-center overflow-x-auto no-scrollbar py-1"
    >
      <div className="inline-flex p-1.5 rounded-2xl bg-card border border-border/80 shadow-sm gap-1.5 min-w-full sm:min-w-0">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              aria-selected={isActive}
              data-testid={`gestion-tab-${tab.id}`}
              onClick={() => onSelectTab(tab.id)}
              className={cn(
                "relative flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm tracking-tight transition-all duration-200 min-h-[44px] cursor-pointer select-none outline-none",
                isActive
                  ? "bg-primary text-primary-foreground shadow-md font-extrabold"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-transform duration-200",
                  isActive ? "scale-110" : "opacity-80"
                )}
                style={{ color: isActive ? "currentColor" : tab.color }}
              />
              <span className="whitespace-nowrap">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export default GestionTabNav;
