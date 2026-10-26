// oppytec-frontend/src/features/inventory/alerts/components/AlertasToolbar.tsx
import { motion, AnimatePresence } from "framer-motion";
import { Filter, LayoutGrid, LayoutList } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AreaSelector, BodegaSelector } from "@/shared/components/layout";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/shared/components/ui/dropdown-menu";
import { cn } from "@/shared/lib";
import type { AlertFilterType, AlertViewMode } from "../types";

const springTransition = {
  type: "spring" as const,
  stiffness: 350,
  damping: 25,
  mass: 1.2,
};

export interface AlertasToolbarProps {
  readonly selectedAreaId: string;
  readonly onSelectArea: (areaId: string) => void;
  readonly activeWarehouseId: string;
  readonly onSelectWarehouse: (warehouseId: string) => void;
  readonly filterType: AlertFilterType;
  readonly onFilterChange: (type: AlertFilterType) => void;
  readonly viewMode: AlertViewMode;
  readonly onViewModeChange: (mode: AlertViewMode) => void;
}

export function AlertasToolbar({
  selectedAreaId,
  onSelectArea,
  activeWarehouseId,
  onSelectWarehouse,
  filterType,
  onFilterChange,
  viewMode,
  onViewModeChange,
}: AlertasToolbarProps) {
  const { t } = useTranslation("alerts");

  return (
    <motion.div
      layoutId="app-toolbar-outer-card"
      data-testid="alerts-toolbar"
      className="bg-card backdrop-blur-md p-4 rounded-2xl border border-input shadow-xl relative z-50"
    >
      {/* =========================================================================
          DESKTOP VIEW (>= 1024px)
          ========================================================================= */}
      <motion.div
        layoutId="app-toolbar-inner-bar"
        data-testid="alerts-toolbar-desktop"
        className="hidden lg:block bg-muted/50 p-2.5 px-6 rounded-2xl border border-input shadow-inner w-full"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center w-full">
          {/* Columna Izquierda (4 columnas): Selectores de Área y Bodega */}
          <motion.div
            layoutId="app-toolbar-left-selectors"
            className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3 w-full lg:col-span-4"
          >
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={onSelectArea}
              className="w-full sm:w-auto"
              buttonClassName="h-10 rounded-xl bg-background border-input shadow-sm text-[9px] min-w-0 w-full sm:w-auto sm:min-w-[150px]"
            />
            <BodegaSelector
              activeWarehouseId={activeWarehouseId}
              onSelectWarehouse={onSelectWarehouse}
              allowAll
              className="w-full sm:w-auto min-w-[160px] h-10 rounded-xl bg-background border-input shadow-sm text-[9px]"
            />
          </motion.div>

          {/* Columna Central (5 columnas): Filtro de Alertas */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full lg:col-span-5">
            <AnimatePresence mode="popLayout">
              <motion.div
                key="alerta-filter-btn"
                layout
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                transition={springTransition}
              >
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      data-testid="alerts-filter-trigger"
                      className="h-10 px-6 gap-2 inline-flex items-center justify-center rounded-xl border border-input bg-background hover:bg-secondary text-foreground transition-all active:scale-95 font-bold uppercase text-[9px] tracking-widest w-full sm:w-auto shadow-sm cursor-pointer select-none"
                    >
                      <Filter className="h-3.5 w-3.5 text-primary" />
                      <span className="truncate">
                        {filterType === "all" && t("toolbar.filter_all")}
                        {filterType === "stock" && t("toolbar.filter_stock")}
                        {filterType === "upcoming" && t("toolbar.filter_upcoming")}
                        {filterType === "expired" && t("toolbar.filter_expired")}
                      </span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-52 bg-card border border-border">
                    <DropdownMenuLabel className="text-[10px] font-black uppercase tracking-wider text-muted-foreground px-3 py-2">
                      {t("toolbar.filter_label")}
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator className="bg-border" />
                    <DropdownMenuItem
                      data-testid="filter-option-all"
                      onClick={() => onFilterChange("all")}
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-3 py-2 cursor-pointer transition-colors rounded-lg",
                        filterType === "all" ? "bg-primary/10 text-primary" : "hover:bg-secondary"
                      )}
                    >
                      {t("toolbar.filter_all")}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      data-testid="filter-option-stock"
                      onClick={() => onFilterChange("stock")}
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-3 py-2 cursor-pointer transition-colors rounded-lg",
                        filterType === "stock" ? "bg-primary/10 text-primary" : "hover:bg-secondary"
                      )}
                    >
                      {t("toolbar.filter_stock")}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      data-testid="filter-option-upcoming"
                      onClick={() => onFilterChange("upcoming")}
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-3 py-2 cursor-pointer transition-colors rounded-lg",
                        filterType === "upcoming" ? "bg-primary/10 text-primary" : "hover:bg-secondary"
                      )}
                    >
                      {t("toolbar.filter_upcoming")}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      data-testid="filter-option-expired"
                      onClick={() => onFilterChange("expired")}
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-3 py-2 cursor-pointer transition-colors rounded-lg",
                        filterType === "expired" ? "bg-primary/10 text-primary" : "hover:bg-secondary"
                      )}
                    >
                      {t("toolbar.filter_expired")}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Columna Derecha (3 columnas): Toggle de Vistas */}
          <div className="flex justify-center lg:justify-end items-center gap-2 w-full lg:col-span-3">
            <AnimatePresence mode="popLayout">
              <motion.div
                key="alerta-viewtoggle-btn"
                layout
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                transition={springTransition}
              >
                <div
                  className="flex items-center gap-0.5 rounded-2xl border border-input bg-background/50 overflow-hidden h-10 select-none shrink-0"
                  data-testid="alerts-view-toggle"
                >
                  <button
                    type="button"
                    data-testid="toggle-view-cards"
                    onClick={() => onViewModeChange("cards")}
                    className={cn(
                      "flex items-center justify-center px-4 h-full gap-1.5 transition-all cursor-pointer select-none text-[9px] font-black uppercase tracking-widest touch-target min-h-[44px]",
                      viewMode === "cards"
                        ? "bg-primary/10 text-primary font-black"
                        : "opacity-40 hover:opacity-60 text-foreground"
                    )}
                    aria-pressed={viewMode === "cards"}
                  >
                    <LayoutGrid className="h-4 w-4" />
                    <span>{t("toolbar.view_cards")}</span>
                  </button>
                  <div className="w-[1px] h-full bg-border" />
                  <button
                    type="button"
                    data-testid="toggle-view-list"
                    onClick={() => onViewModeChange("list")}
                    className={cn(
                      "flex items-center justify-center px-4 h-full gap-1.5 transition-all cursor-pointer select-none text-[9px] font-black uppercase tracking-widest touch-target min-h-[44px]",
                      viewMode === "list"
                        ? "bg-primary/10 text-primary font-black"
                        : "opacity-40 hover:opacity-60 text-foreground"
                    )}
                    aria-pressed={viewMode === "list"}
                  >
                    <LayoutList className="h-4 w-4" />
                    <span>{t("toolbar.view_list")}</span>
                  </button>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </motion.div>

      {/* =========================================================================
          MOBILE VIEW (< 1024px)
          ========================================================================= */}
      <div className="block lg:hidden w-full" data-testid="alerts-toolbar-mobile">
        <div className="flex flex-col items-center justify-between gap-4 w-full">
          <div className="grid grid-cols-2 gap-2 w-full max-w-md mx-auto bg-muted/50 p-1.5 rounded-xl border border-input shadow-inner">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={onSelectArea}
              buttonClassName="w-full text-center"
            />
            <BodegaSelector
              activeWarehouseId={activeWarehouseId}
              onSelectWarehouse={onSelectWarehouse}
              allowAll
              className="w-full text-center justify-center"
            />
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2 w-full max-w-md mx-auto">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  data-testid="alerts-filter-trigger-mobile"
                  className="h-10 flex-1 px-4 inline-flex items-center justify-center rounded-xl gap-2 font-black uppercase text-[10px] tracking-widest border border-input bg-background hover:bg-secondary text-foreground touch-target min-h-[44px]"
                >
                  <Filter className="h-3.5 w-3.5 text-primary" />
                  <span className="truncate">
                    {filterType === "all"
                      ? t("toolbar.filter_all_short")
                      : filterType === "stock"
                      ? t("toolbar.filter_stock")
                      : filterType === "upcoming"
                      ? t("toolbar.filter_upcoming_short")
                      : t("toolbar.filter_expired_short")}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52 bg-card border border-border">
                <DropdownMenuItem
                  data-testid="filter-option-all-mobile"
                  onClick={() => onFilterChange("all")}
                >
                  {t("toolbar.filter_all")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  data-testid="filter-option-stock-mobile"
                  onClick={() => onFilterChange("stock")}
                >
                  {t("toolbar.filter_stock")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  data-testid="filter-option-upcoming-mobile"
                  onClick={() => onFilterChange("upcoming")}
                >
                  {t("toolbar.filter_upcoming")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  data-testid="filter-option-expired-mobile"
                  onClick={() => onFilterChange("expired")}
                >
                  {t("toolbar.filter_expired")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <div
              className="flex items-center gap-0.5 rounded-xl border border-input bg-background/50 overflow-hidden h-10 select-none"
              data-testid="alerts-view-toggle-mobile"
            >
              <button
                type="button"
                data-testid="toggle-view-cards-mobile"
                onClick={() => onViewModeChange("cards")}
                className={cn(
                  "px-3 h-full flex items-center justify-center text-[10px] font-black uppercase touch-target min-h-[44px] min-w-[44px]",
                  viewMode === "cards" && "bg-primary/10 text-primary"
                )}
                aria-label={t("toolbar.aria_cards")}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                type="button"
                data-testid="toggle-view-list-mobile"
                onClick={() => onViewModeChange("list")}
                className={cn(
                  "px-3 h-full flex items-center justify-center text-[10px] font-black uppercase touch-target min-h-[44px] min-w-[44px]",
                  viewMode === "list" && "bg-primary/10 text-primary"
                )}
                aria-label={t("toolbar.aria_list")}
              >
                <LayoutList className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
