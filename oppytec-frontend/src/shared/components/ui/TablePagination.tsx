import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";

export interface TablePaginationProps {
  readonly currentPage: number;
  readonly totalItems: number;
  readonly pageSize: number;
  readonly pageSizeOptions?: readonly number[];
  readonly onPageChange: (page: number) => void;
  readonly onPageSizeChange: (pageSize: number) => void;
  readonly itemLabel?: string;
  readonly className?: string;
}

export function TablePagination({
  currentPage,
  totalItems,
  pageSize,
  pageSizeOptions = [10, 30, 50, 100],
  onPageChange,
  onPageSizeChange,
  itemLabel = "productos",
  className,
}: TablePaginationProps) {
  const { t } = useTranslation(["operations", "common"]);
  const safePageSize = Math.max(1, pageSize);
  const totalPages = Math.max(1, Math.ceil(totalItems / safePageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const fromItem = totalItems === 0 ? 0 : (safeCurrentPage - 1) * safePageSize + 1;
  const toItem = Math.min(safeCurrentPage * safePageSize, totalItems);

  // Generar lista de páginas visibles con elipsis
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
      data-testid="table-pagination"
      className={cn(
        "flex flex-col sm:flex-row items-center justify-between gap-4 py-4 px-2 text-xs font-medium text-muted-foreground border-t border-border/50 mt-4",
        className
      )}
    >
      {/* Resumen de items */}
      <div className="flex items-center gap-2">
        <span className="font-semibold text-foreground">
          {t("consumption.pagination.showing", {
            from: fromItem,
            to: toItem,
            defaultValue: `Mostrando ${fromItem} - ${toItem}`,
          })}
        </span>
        <span>{t("consumption.pagination.of", { defaultValue: "de" })}</span>
        <span className="font-bold text-foreground bg-primary/10 text-primary px-2.5 py-0.5 rounded-lg border border-primary/20">
          {totalItems} {itemLabel}
        </span>
      </div>

      {/* Controles de paginación y Selector de filas */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        {/* Selector de items por página */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {t("consumption.pagination.show_label", { defaultValue: "Mostrar:" })}
          </span>
          <select
            value={safePageSize}
            onChange={(e) => {
              onPageSizeChange(Number(e.target.value));
              onPageChange(1);
            }}
            data-testid="pagination-page-size-select"
            className="h-9 min-h-[36px] rounded-xl border border-border bg-card px-2.5 py-1 text-xs font-bold text-foreground focus:border-primary focus:outline-none transition-colors cursor-pointer"
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {t("consumption.pagination.per_page", {
                  count: option,
                  defaultValue: `${option} por página`,
                })}
              </option>
            ))}
          </select>
        </div>

        {/* Botones de navegación de página */}
        <div className="flex items-center gap-1">
          {/* Ir a la primera página */}
          <button
            type="button"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
            onClick={() => onPageChange(1)}
            disabled={safeCurrentPage === 1}
            title={t("consumption.pagination.first_page", { defaultValue: "Primera página" })}
            data-testid="pagination-first-page"
          >
            <ChevronsLeft className="h-4 w-4" />
          </button>

          {/* Página anterior */}
          <button
            type="button"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
            onClick={() => onPageChange(safeCurrentPage - 1)}
            disabled={safeCurrentPage === 1}
            title={t("consumption.pagination.prev_page", { defaultValue: "Página anterior" })}
            data-testid="pagination-prev-page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {/* Números de página */}
          <div className="flex items-center gap-1 px-1">
            {getPageNumbers().map((page, idx) => {
              if (typeof page === "string") {
                return (
                  <span
                    key={`ellipsis-${idx}`}
                    className="px-1 text-muted-foreground font-bold"
                  >
                    ...
                  </span>
                );
              }
              const isActive = page === safeCurrentPage;
              return (
                <button
                  key={`page-${page}`}
                  type="button"
                  data-testid={`pagination-page-${page}`}
                  className={cn(
                    "flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl font-bold text-xs transition-all cursor-pointer select-none",
                    isActive
                      ? "bg-primary text-primary-foreground shadow-sm shadow-primary/30"
                      : "border border-border bg-card text-foreground hover:bg-secondary"
                  )}
                  onClick={() => onPageChange(page)}
                >
                  {page}
                </button>
              );
            })}
          </div>

          {/* Página siguiente */}
          <button
            type="button"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
            onClick={() => onPageChange(safeCurrentPage + 1)}
            disabled={safeCurrentPage === totalPages}
            title={t("consumption.pagination.next_page", { defaultValue: "Página siguiente" })}
            data-testid="pagination-next-page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>

          {/* Ir a la última página */}
          <button
            type="button"
            className="flex h-9 w-9 min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer select-none"
            onClick={() => onPageChange(totalPages)}
            disabled={safeCurrentPage === totalPages}
            title={t("consumption.pagination.last_page", { defaultValue: "Última página" })}
            data-testid="pagination-last-page"
          >
            <ChevronsRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default TablePagination;
