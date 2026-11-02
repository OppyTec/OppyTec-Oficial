/**
 * oppytec-frontend/src/features/projection/components/ProyeccionToolbar.tsx
 * Barra de herramientas unificada para la feature Proyección.
 * Integra búsqueda rápida, selector de horizonte temporal, ordenamiento, toggle de categorías,
 * botón de recálculo con feedback y selector de tamaño de página.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC, ChangeEvent } from "react";
import {
  ArrowUpDown,
  Calendar,
  RefreshCw,
  Search,
  Tags,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import type { ProjectionHorizonDays, ProjectionSortOrder } from "../types";

export interface ProyeccionToolbarProps {
  readonly searchTerm: string;
  readonly onSearchChange: (search: string) => void;
  readonly horizonDays: number;
  readonly onHorizonChange: (days: ProjectionHorizonDays) => void;
  readonly sortBy: ProjectionSortOrder;
  readonly onSortChange: (sort: ProjectionSortOrder) => void;
  readonly isCategoriesOpen?: boolean;
  readonly onToggleCategories?: () => void;
  readonly activeCategoriesCount?: number;
  readonly onRecompute?: () => void;
  readonly isRecomputing?: boolean;
  readonly lastRecomputedAt?: string | null;
  readonly pageSize: number;
  readonly onPageSizeChange: (pageSize: number) => void;
  readonly pageSizeOptions?: readonly number[];
  readonly horizonOptions?: readonly ProjectionHorizonDays[];
  readonly className?: string;
}

const DEFAULT_PAGE_SIZES: readonly number[] = [10, 30, 50, 100];
const DEFAULT_HORIZONS: readonly ProjectionHorizonDays[] = [7, 15, 30, 60, 90];

export const ProyeccionToolbar: FC<ProyeccionToolbarProps> = ({
  searchTerm,
  onSearchChange,
  horizonDays,
  onHorizonChange,
  sortBy,
  onSortChange,
  isCategoriesOpen = false,
  onToggleCategories,
  activeCategoriesCount = 0,
  onRecompute,
  isRecomputing = false,
  lastRecomputedAt,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  horizonOptions = DEFAULT_HORIZONS,
  className,
}) => {
  const { t } = useTranslation("projection");

  const handleSearchInput = (e: ChangeEvent<HTMLInputElement>) => {
    onSearchChange(e.target.value);
  };

  const handleClearSearch = () => {
    onSearchChange("");
  };

  const handleHorizonSelect = (e: ChangeEvent<HTMLSelectElement>) => {
    const val = Number(e.target.value) as ProjectionHorizonDays;
    onHorizonChange(val);
  };

  const handleSortSelect = (e: ChangeEvent<HTMLSelectElement>) => {
    onSortChange(e.target.value as ProjectionSortOrder);
  };

  const handlePageSizeSelect = (e: ChangeEvent<HTMLSelectElement>) => {
    onPageSizeChange(Number(e.target.value));
  };

  return (
    <div
      data-testid="proyeccion-toolbar"
      className={cn(
        "rounded-2xl border border-input shadow-xl bg-card p-3 sm:p-4 text-card-foreground transition-all duration-200",
        className
      )}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {/* Columna Izquierda: Buscador */}
        <div className="relative flex-1 min-w-[240px]">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
            <Search className="h-4 w-4" aria-hidden="true" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchInput}
            placeholder={t("toolbar.search_placeholder", {
              defaultValue: "Buscar por producto, SKU o categoría...",
            })}
            data-testid="projection-search-input"
            className="w-full h-10 rounded-xl border border-border bg-background pl-9 pr-9 text-xs sm:text-sm font-medium text-foreground placeholder:text-muted-foreground focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={handleClearSearch}
              data-testid="projection-search-clear"
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
              aria-label={t("toolbar.clear", { defaultValue: "Limpiar búsqueda" })}
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Columna Central y Derecha: Controles y Selectores */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Selector de Horizonte de Días */}
          <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs font-semibold text-foreground">
            <Calendar className="h-3.5 w-3.5 text-emerald-500 shrink-0" aria-hidden="true" />
            <label htmlFor="projection-horizon-select" className="sr-only">
              {t("toolbar.horizon_label", { defaultValue: "Horizonte" })}
            </label>
            <select
              id="projection-horizon-select"
              data-testid="projection-horizon-select"
              value={horizonDays}
              onChange={handleHorizonSelect}
              className="bg-transparent text-xs font-bold text-foreground focus:outline-none cursor-pointer py-1"
            >
              {horizonOptions.map((days) => (
                <option key={`horizon-${days}`} value={days} className="bg-card text-foreground">
                  {t("toolbar.horizon_days", {
                    count: days,
                    defaultValue: `${days} días`,
                  })}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Ordenamiento */}
          <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs font-semibold text-foreground">
            <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" aria-hidden="true" />
            <label htmlFor="projection-sort-select" className="sr-only">
              {t("toolbar.sort_label", { defaultValue: "Ordenar por" })}
            </label>
            <select
              id="projection-sort-select"
              data-testid="projection-sort-select"
              value={sortBy}
              onChange={handleSortSelect}
              className="bg-transparent text-xs font-bold text-foreground focus:outline-none cursor-pointer py-1"
            >
              <option value="urgency_desc" className="bg-card text-foreground">
                {t("sort.urgency_desc", { defaultValue: "Mayor Urgencia" })}
              </option>
              <option value="name_asc" className="bg-card text-foreground">
                {t("sort.name_asc", { defaultValue: "Nombre A-Z" })}
              </option>
              <option value="name_desc" className="bg-card text-foreground">
                {t("sort.name_desc", { defaultValue: "Nombre Z-A" })}
              </option>
              <option value="projected_asc" className="bg-card text-foreground">
                {t("sort.projected_asc", { defaultValue: "Menor Stock Proyectado" })}
              </option>
              <option value="current_desc" className="bg-card text-foreground">
                {t("sort.current_desc", { defaultValue: "Mayor Stock Actual" })}
              </option>
            </select>
          </div>

          {/* Botón Toggle de Categorías */}
          {onToggleCategories && (
            <button
              type="button"
              onClick={onToggleCategories}
              data-testid="projection-toggle-categories"
              className={cn(
                "flex h-9 items-center gap-1.5 rounded-xl border px-3 text-xs font-bold transition-all cursor-pointer select-none",
                isCategoriesOpen
                  ? "border-emerald-500 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-border bg-background text-foreground hover:bg-secondary"
              )}
              aria-expanded={isCategoriesOpen}
            >
              <Tags className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>
                {t("toolbar.categories_button", { defaultValue: "Categorías" })}
              </span>
              {activeCategoriesCount > 0 && (
                <span className="ml-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-emerald-500 text-[10px] font-black text-white px-1">
                  {activeCategoriesCount}
                </span>
              )}
            </button>
          )}

          {/* Selector de Filas por Página */}
          <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs font-semibold text-foreground">
            <span className="text-[10px] uppercase font-bold text-muted-foreground">
              {t("toolbar.page_size_label", { defaultValue: "Filas" })}:
            </span>
            <label htmlFor="projection-pagesize-select" className="sr-only">
              {t("toolbar.page_size_tooltip", { defaultValue: "Filas por página" })}
            </label>
            <select
              id="projection-pagesize-select"
              data-testid="projection-pagesize-select"
              value={pageSize}
              onChange={handlePageSizeSelect}
              className="bg-transparent text-xs font-bold text-foreground focus:outline-none cursor-pointer py-1"
            >
              {pageSizeOptions.map((opt) => (
                <option key={`ps-${opt}`} value={opt} className="bg-card text-foreground">
                  {opt}
                </option>
              ))}
            </select>
          </div>

          {/* Botón Recalcular Ahora */}
          {onRecompute && (
            <button
              type="button"
              onClick={onRecompute}
              disabled={isRecomputing}
              data-testid="projection-recompute-btn"
              title={
                lastRecomputedAt
                  ? t("toolbar.last_calculated", {
                      time: lastRecomputedAt,
                      defaultValue: `Último cálculo: ${lastRecomputedAt}`,
                    })
                  : t("toolbar.recompute_title", {
                      defaultValue: "Recalcular proyección con últimos movimientos de Kardex",
                    })
              }
              className={cn(
                "flex h-9 items-center gap-2 rounded-xl bg-emerald-600 px-3.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer select-none",
                isRecomputing && "cursor-wait"
              )}
            >
              <RefreshCw
                className={cn("h-3.5 w-3.5 shrink-0", isRecomputing && "animate-spin")}
                aria-hidden="true"
              />
              <span className="hidden sm:inline">
                {isRecomputing
                  ? t("toolbar.recomputing", { defaultValue: "Calculando..." })
                  : t("toolbar.recompute_now", { defaultValue: "Recalcular Ahora" })}
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProyeccionToolbar;
