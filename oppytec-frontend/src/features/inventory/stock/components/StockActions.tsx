// oppytec-frontend/src/features/inventory/stock/components/StockActions.tsx
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  ArrowUpDown,
  Tags,
  Truck,
  ShoppingBag,
  Settings2,
  AlertTriangle,
  LayoutGrid,
  List,
} from "lucide-react";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { BodegaSelector } from "@/shared/components/layout/BodegaSelector";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/shared/components/ui/dropdown-menu";
import { cn } from "@/shared/lib";
import type { StockSortOption, StockViewMode } from "../../types";

export interface StockActionsProps {
  // Selectores
  readonly selectedAreaId?: string;
  readonly onSelectArea?: (areaId: string) => void;
  readonly activeWarehouseId?: string;
  readonly onSelectWarehouse?: (warehouseId: string) => void;

  // Acciones operativas
  readonly onOpenSolicitar: () => void;
  readonly onOpenMerma: () => void;
  readonly onOpenAdjustment: () => void;
  readonly onOpenReceive: () => void;

  // Filtros visuales
  readonly showCategories: boolean;
  readonly onToggleCategories: () => void;
  readonly sortOption: StockSortOption;
  readonly onSortChange: (option: StockSortOption) => void;
  readonly viewMode?: StockViewMode;
  readonly onToggleViewMode?: () => void;
}

export function StockActions({
  selectedAreaId = "all",
  onSelectArea,
  activeWarehouseId = "all",
  onSelectWarehouse,
  onOpenSolicitar,
  onOpenMerma,
  onOpenAdjustment,
  onOpenReceive,
  showCategories,
  onToggleCategories,
  sortOption,
  onSortChange,
  viewMode = "agrupado",
  onToggleViewMode,
}: StockActionsProps) {
  const { t } = useTranslation("inventory");
  return (
    <div className="space-y-4" data-testid="stock-actions-toolbar">
      <motion.div
        layoutId="stock-toolbar-outer-card"
        className="bg-card backdrop-blur-md p-3 sm:p-4 rounded-2xl border border-border shadow-md relative z-30"
      >
        {/* =========================================================================
            DESKTOP VIEW (>= 1024px)
            ========================================================================= */}
        <div className="hidden lg:block bg-muted/40 p-2.5 px-4 rounded-2xl border border-border/60 shadow-inner w-full">
          <div className="grid grid-cols-12 gap-3 items-center w-full">
            {/* Columna Izquierda: Selectores de Área y Bodega */}
            <div className="col-span-4 flex items-center gap-2">
              <AreaSelector
                selectedAreaId={selectedAreaId}
                onSelectArea={onSelectArea}
                buttonClassName="h-10 rounded-xl bg-background border-border shadow-xs text-xs font-semibold min-w-[150px]"
              />
              <BodegaSelector
                activeWarehouseId={activeWarehouseId}
                onSelectWarehouse={(id) => onSelectWarehouse?.(id)}
              />
            </div>

            {/* Columna Central: Ordenamiento, Categorías y Modo de Vista */}
            <div className="col-span-4 flex items-center justify-center gap-2">
              {/* Dropdown de Ordenamiento */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    data-testid="stock-sort-trigger"
                    className="h-10 px-4 gap-2 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-secondary text-foreground text-xs font-bold tracking-tight shadow-xs transition-colors cursor-pointer select-none"
                  >
                    <ArrowUpDown className="h-4 w-4 text-primary shrink-0" />
                    <span>{t("stock.toolbar.sort")}</span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="center" className="w-56 p-1.5">
                  <DropdownMenuItem
                    onClick={() => onSortChange("urgency")}
                    className={cn(
                      "text-xs font-bold py-2 cursor-pointer",
                      sortOption === "urgency" && "bg-primary/10 text-primary"
                    )}
                  >
                    {t("stock.toolbar.sort_urgency")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onSortChange("az")}
                    className={cn(
                      "text-xs font-bold py-2 cursor-pointer",
                      sortOption === "az" && "bg-primary/10 text-primary"
                    )}
                  >
                    {t("stock.toolbar.sort_az")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onSortChange("za")}
                    className={cn(
                      "text-xs font-bold py-2 cursor-pointer",
                      sortOption === "za" && "bg-primary/10 text-primary"
                    )}
                  >
                    {t("stock.toolbar.sort_za")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onSortChange("stock_asc")}
                    className={cn(
                      "text-xs font-bold py-2 cursor-pointer",
                      sortOption === "stock_asc" && "bg-primary/10 text-primary"
                    )}
                  >
                    {t("stock.toolbar.sort_stock_asc")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onSortChange("stock_desc")}
                    className={cn(
                      "text-xs font-bold py-2 cursor-pointer",
                      sortOption === "stock_desc" && "bg-primary/10 text-primary"
                    )}
                  >
                    {t("stock.toolbar.sort_stock_desc")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Botón Toggle Categorías */}
              <button
                type="button"
                data-testid="stock-toggle-categories"
                onClick={onToggleCategories}
                className={cn(
                  "h-10 px-4 gap-2 inline-flex items-center justify-center rounded-xl text-xs font-bold tracking-tight shadow-xs transition-all cursor-pointer select-none",
                  showCategories
                    ? "bg-primary text-primary-foreground shadow-primary/20"
                    : "border border-border bg-background hover:bg-secondary text-foreground"
                )}
              >
                <Tags className={cn("h-4 w-4 shrink-0", !showCategories && "text-primary")} />
                <span>{t("stock.toolbar.categories")}</span>
              </button>

              {/* Toggle de Modo de Vista (Agrupado vs Plano) */}
              {onToggleViewMode && (
                <button
                  type="button"
                  data-testid="stock-toggle-viewmode"
                  onClick={onToggleViewMode}
                  title={viewMode === "agrupado" ? t("stock.toolbar.view_flat") : t("stock.toolbar.view_grouped")}
                  className="h-10 px-3 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-secondary text-foreground text-xs font-bold shadow-xs transition-colors cursor-pointer select-none"
                >
                  {viewMode === "agrupado" ? (
                    <LayoutGrid className="h-4 w-4 text-primary" />
                  ) : (
                    <List className="h-4 w-4 text-primary" />
                  )}
                </button>
              )}
            </div>

            {/* Columna Derecha: Botones de Acción Operativa */}
            <div className="col-span-4 flex items-center justify-end gap-2">
              {/* Recibir / Agregar */}
              <button
                type="button"
                data-testid="stock-action-receive"
                onClick={onOpenReceive}
                className="h-10 px-3.5 gap-1.5 inline-flex items-center justify-center rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-black text-xs uppercase tracking-wider shadow-sm shadow-primary/20 transition-all active:scale-95 cursor-pointer"
              >
                <Truck className="h-4 w-4 shrink-0" />
                <span>{t("stock.toolbar.action_receive")}</span>
              </button>

              {/* Solicitudes */}
              <button
                type="button"
                data-testid="stock-action-solicitar"
                onClick={onOpenSolicitar}
                className="h-10 px-3 gap-1.5 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-blue-500/10 hover:text-blue-500 text-foreground font-black text-xs uppercase tracking-wider shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                <ShoppingBag className="h-4 w-4 shrink-0 text-blue-500" />
                <span>{t("stock.toolbar.action_solicitar")}</span>
              </button>

              {/* Ajustar */}
              <button
                type="button"
                data-testid="stock-action-adjustment"
                onClick={onOpenAdjustment}
                className="h-10 px-3 gap-1.5 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-amber-500/10 hover:text-amber-500 text-foreground font-black text-xs uppercase tracking-wider shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                <Settings2 className="h-4 w-4 shrink-0 text-amber-500" />
                <span>{t("stock.toolbar.action_adjustment")}</span>
              </button>

              {/* Merma */}
              <button
                type="button"
                data-testid="stock-action-merma"
                onClick={onOpenMerma}
                className="h-10 px-3 gap-1.5 inline-flex items-center justify-center rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground font-black text-xs uppercase tracking-wider shadow-sm shadow-destructive/20 transition-all active:scale-95 cursor-pointer"
              >
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{t("stock.toolbar.action_merma")}</span>
              </button>
            </div>
          </div>
        </div>

        {/* =========================================================================
            MOBILE / TABLET VIEW (< 1024px) — Touch Targets >= 44px
            ========================================================================= */}
        <div className="block lg:hidden w-full space-y-3">
          {/* Fila 1: Selectores Integrados */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={onSelectArea}
              className="w-full sm:w-1/2"
              buttonClassName="w-full min-h-[44px] justify-between"
            />
            <div className="w-full sm:w-1/2">
              <BodegaSelector
                activeWarehouseId={activeWarehouseId}
                onSelectWarehouse={(id) => onSelectWarehouse?.(id)}
              />
            </div>
          </div>

          {/* Fila 2: Filtros de Orden y Categorías en Móvil */}
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  data-testid="stock-mobile-sort-trigger"
                  className="flex-1 min-h-[44px] px-3 gap-2 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-secondary text-foreground text-xs font-bold transition-colors cursor-pointer"
                >
                  <ArrowUpDown className="h-4 w-4 text-primary shrink-0" />
                  <span>{t("stock.toolbar.sort")}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56 p-1.5">
                <DropdownMenuItem
                  onClick={() => onSortChange("urgency")}
                  className="text-xs font-bold py-2 cursor-pointer"
                >
                  {t("stock.toolbar.sort_urgency")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onSortChange("az")}
                  className="text-xs font-bold py-2 cursor-pointer"
                >
                  {t("stock.toolbar.sort_az")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onSortChange("za")}
                  className="text-xs font-bold py-2 cursor-pointer"
                >
                  {t("stock.toolbar.sort_za")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onSortChange("stock_asc")}
                  className="text-xs font-bold py-2 cursor-pointer"
                >
                  {t("stock.toolbar.sort_stock_asc")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onSortChange("stock_desc")}
                  className="text-xs font-bold py-2 cursor-pointer"
                >
                  {t("stock.toolbar.sort_stock_desc")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <button
              type="button"
              data-testid="stock-mobile-toggle-categories"
              onClick={onToggleCategories}
              className={cn(
                "flex-1 min-h-[44px] px-3 gap-2 inline-flex items-center justify-center rounded-xl text-xs font-bold transition-all cursor-pointer",
                showCategories
                  ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                  : "border border-border bg-background hover:bg-secondary text-foreground"
              )}
            >
              <Tags className={cn("h-4 w-4 shrink-0", !showCategories && "text-primary")} />
              <span>{t("stock.toolbar.categories")}</span>
            </button>

            {onToggleViewMode && (
              <button
                type="button"
                data-testid="stock-mobile-toggle-viewmode"
                onClick={onToggleViewMode}
                className="min-h-[44px] min-w-[44px] px-3 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-secondary text-foreground cursor-pointer"
              >
                {viewMode === "agrupado" ? (
                  <LayoutGrid className="h-4 w-4 text-primary" />
                ) : (
                  <List className="h-4 w-4 text-primary" />
                )}
              </button>
            )}
          </div>

          {/* Fila 3: Botones de Acción Operativa con Touch Target >= 44px */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full pt-1">
            <button
              type="button"
              data-testid="stock-mobile-receive"
              onClick={onOpenReceive}
              className="min-h-[44px] px-3 gap-1.5 inline-flex items-center justify-center rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-black text-xs uppercase tracking-wider shadow-sm transition-all active:scale-95 cursor-pointer"
            >
              <Truck className="h-4 w-4 shrink-0" />
              <span>{t("stock.toolbar.action_receive")}</span>
            </button>

            <button
              type="button"
              data-testid="stock-mobile-solicitar"
              onClick={onOpenSolicitar}
              className="min-h-[44px] px-3 gap-1.5 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-blue-500/10 hover:text-blue-500 text-foreground font-black text-xs uppercase tracking-wider transition-all active:scale-95 cursor-pointer"
            >
              <ShoppingBag className="h-4 w-4 shrink-0 text-blue-500" />
              <span>{t("stock.toolbar.action_solicitar")}</span>
            </button>

            <button
              type="button"
              data-testid="stock-mobile-adjustment"
              onClick={onOpenAdjustment}
              className="min-h-[44px] px-3 gap-1.5 inline-flex items-center justify-center rounded-xl border border-border bg-background hover:bg-amber-500/10 hover:text-amber-500 text-foreground font-black text-xs uppercase tracking-wider transition-all active:scale-95 cursor-pointer"
            >
              <Settings2 className="h-4 w-4 shrink-0 text-amber-500" />
              <span>{t("stock.toolbar.action_adjustment")}</span>
            </button>

            <button
              type="button"
              data-testid="stock-mobile-merma"
              onClick={onOpenMerma}
              className="min-h-[44px] px-3 gap-1.5 inline-flex items-center justify-center rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground font-black text-xs uppercase tracking-wider shadow-sm transition-all active:scale-95 cursor-pointer"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{t("stock.toolbar.action_merma")}</span>
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default StockActions;
