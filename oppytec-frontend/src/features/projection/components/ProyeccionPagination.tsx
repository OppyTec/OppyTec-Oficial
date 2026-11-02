/**
 * oppytec-frontend/src/features/projection/components/ProyeccionPagination.tsx
 * Componente canónico de paginación server-side y client-side para Proyección.
 * Incluye selector de filas (10, 30, 50, 100), resumen de rango visible, navegación ágil con elipsis
 * y diseño táctil adaptativo Mobile-First.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import { useEffect, type FC, type ChangeEvent } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";

export interface ProyeccionPaginationProps {
  readonly currentPage: number;
  readonly totalItems: number;
  readonly pageSize: number;
  readonly pageSizeOptions?: readonly number[];
  readonly onPageChange: (page: number) => void;
  readonly onPageSizeChange: (pageSize: number) => void;
  readonly isLoading?: boolean;
  readonly itemLabel?: string;
  readonly className?: string;
}

const DEFAULT_PAGE_SIZES: readonly number[] = [10, 30, 50, 100];

export const ProyeccionPagination: FC<ProyeccionPaginationProps> = ({
  currentPage,
  totalItems,
  pageSize,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  onPageChange,
  onPageSizeChange,
  isLoading = false,
  itemLabel,
  className,
}) => {
  const { t } = useTranslation("projection");

  const safePageSize = Math.max(1, pageSize);
  const totalPages = Math.max(1, Math.ceil(totalItems / safePageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const fromItem = totalItems === 0 ? 0 : (safeCurrentPage - 1) * safePageSize + 1;
  const toItem = Math.min(safeCurrentPage * safePageSize, totalItems);

  const displayItemLabel =
    itemLabel ?? t("pagination.products", { defaultValue: "productos" });

  // Navegación por teclado (Flechas izquierda / derecha) cuando no se esté editando un input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
        return;
      }
      if (e.key === "ArrowLeft" && safeCurrentPage > 1 && !isLoading) {
        onPageChange(safeCurrentPage - 1);
      } else if (e.key === "ArrowRight" && safeCurrentPage < totalPages && !isLoading) {
        onPageChange(safeCurrentPage + 1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [safeCurrentPage, totalPages, isLoading, onPageChange]);

  const handlePageSizeChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newSize = Number(e.target.value);
    onPageSizeChange(newSize);
    onPageChange(1);
  };

  // Generación de lista de números con elipsis compacta
  const getPageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = [];
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      let start = Math.max(2, safeCurrentPage - 1);
      let end = Math.min(totalPages - 1, safeCurrentPage + 1);

      if (safeCurrentPage <= 3) {
        end = 4;
      } else if (safeCurrentPage >= totalPages - 2) {
        start = totalPages - 3;
      }

      if (start > 2) pages.push("...");
      for (let i = start; i <= end; i++) pages.push(i);
      if (end < totalPages - 1) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <div
      data-testid="proyeccion-pagination"
      className={cn(
        "flex flex-col sm:flex-row items-center justify-between gap-3 py-3 px-2 text-xs font-medium text-muted-foreground border-t border-border/60 mt-4",
        isLoading && "opacity-60 pointer-events-none",
        className
      )}
    >
      {/* 1. Resumen visual: Mostrando {start} - {end} de {total} productos */}
      <div
        data-testid="pagination-summary"
        className="flex items-center gap-1.5 text-xs text-muted-foreground"
      >
        <span className="font-semibold text-foreground">
          {t("pagination.showing", {
            from: fromItem,
            to: toItem,
            defaultValue: `Mostrando ${fromItem} - ${toItem}`,
          })}
        </span>
        <span>{t("pagination.of", { defaultValue: "de" })}</span>
        <span className="font-bold text-foreground bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-lg border border-emerald-500/20">
          {totalItems} {displayItemLabel}
        </span>
      </div>

      {/* 2. Controles de paginación y Selector de tamaño */}
      <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3">
        {/* Selector de tamaño de página */}
        <div className="flex items-center gap-1.5">
          <label
            htmlFor="projection-pagination-size-select"
            className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
          >
            {t("pagination.show_label", { defaultValue: "Mostrar:" })}
          </label>
          <select
            id="projection-pagination-size-select"
            value={safePageSize}
            onChange={handlePageSizeChange}
            data-testid="pagination-page-size-select"
            className="h-9 min-h-[36px] rounded-xl border border-border bg-card px-2.5 py-1 text-xs font-bold text-foreground focus:border-emerald-500 focus:outline-none transition-colors cursor-pointer"
          >
            {pageSizeOptions.map((option) => (
              <option key={`opt-size-${option}`} value={option}>
                {t("pagination.per_page", {
                  count: option,
                  defaultValue: `${option} por página`,
                })}
              </option>
            ))}
          </select>
        </div>

        {/* Botones de navegación táctiles */}
        <div className="flex items-center gap-1">
          {/* Primer Página */}
          <button
            type="button"
            onClick={() => onPageChange(1)}
            disabled={safeCurrentPage === 1 || isLoading}
            title={t("pagination.first_page", { defaultValue: "Primera página" })}
            data-testid="pagination-first-page"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
          >
            <ChevronsLeft className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">
              {t("pagination.first_page", { defaultValue: "Primera página" })}
            </span>
          </button>

          {/* Página Anterior */}
          <button
            type="button"
            onClick={() => onPageChange(safeCurrentPage - 1)}
            disabled={safeCurrentPage === 1 || isLoading}
            title={t("pagination.prev_page", { defaultValue: "Página anterior" })}
            data-testid="pagination-prev-page"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">
              {t("pagination.prev_page", { defaultValue: "Página anterior" })}
            </span>
          </button>

          {/* Números de página con elipsis */}
          <div className="flex items-center gap-1 px-1">
            {getPageNumbers().map((p, idx) => {
              if (typeof p === "string") {
                return (
                  <span
                    key={`ellipsis-${idx}`}
                    className="px-1 text-muted-foreground font-bold"
                  >
                    ...
                  </span>
                );
              }
              const isActive = p === safeCurrentPage;
              return (
                <button
                  key={`page-${p}`}
                  type="button"
                  data-testid={`pagination-page-${p}`}
                  onClick={() => onPageChange(p)}
                  disabled={isLoading}
                  className={cn(
                    "flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl font-bold text-xs transition-all cursor-pointer select-none",
                    isActive
                      ? "bg-emerald-600 text-white shadow-sm shadow-emerald-600/30"
                      : "border border-border bg-card text-foreground hover:bg-secondary"
                  )}
                >
                  {p}
                </button>
              );
            })}
          </div>

          {/* Página Siguiente */}
          <button
            type="button"
            onClick={() => onPageChange(safeCurrentPage + 1)}
            disabled={safeCurrentPage === totalPages || isLoading}
            title={t("pagination.next_page", { defaultValue: "Página siguiente" })}
            data-testid="pagination-next-page"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">
              {t("pagination.next_page", { defaultValue: "Página siguiente" })}
            </span>
          </button>

          {/* Última Página */}
          <button
            type="button"
            onClick={() => onPageChange(totalPages)}
            disabled={safeCurrentPage === totalPages || isLoading}
            title={t("pagination.last_page", { defaultValue: "Última página" })}
            data-testid="pagination-last-page"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
          >
            <ChevronsRight className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">
              {t("pagination.last_page", { defaultValue: "Última página" })}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProyeccionPagination;
