/**
 * oppytec-frontend/src/features/invoices/components/InvoiceFilters.tsx
 * Barra de filtros avanzados con búsqueda debounced, estado, tipo DTE y rango de fecha.
 */

import { useTranslation } from "react-i18next";
import { Search, RotateCcw } from "lucide-react";
import { cn } from "@/shared/lib";
import type { DTEType, InvoiceFilters as FilterState, InvoiceStatus } from "../types";

export interface InvoiceFiltersProps {
  filters: FilterState;
  searchInput: string;
  onSearchChange: (val: string) => void;
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  className?: string;
}

export function InvoiceFilters({
  filters,
  searchInput,
  onSearchChange,
  onFilterChange,
  onReset,
  className,
}: InvoiceFiltersProps) {
  const { t } = useTranslation(["invoices"]);

  return (
    <div
      data-testid="invoice-filters"
      className={cn("glass-card rounded-2xl border border-border p-4 shadow-sm space-y-3", className)}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Buscador de texto libre */}
        <div className="relative lg:col-span-2">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t("invoices:filters.search_placeholder", "Buscar por folio, RUT, proveedor o ítem...")}
            value={searchInput}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Selector de Estado */}
        <div>
          <select
            value={filters.status || "ALL"}
            onChange={(e) =>
              onFilterChange("status", e.target.value as InvoiceStatus | "ALL")
            }
            className="w-full py-2 px-3 text-xs rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 font-medium"
          >
            <option value="ALL">{t("invoices:status.all", "Todos los Estados")}</option>
            <option value="READY_FOR_REVIEW">{t("invoices:status.ready_for_review", "Por Revisar")}</option>
            <option value="CONFIRMED_STOCK">{t("invoices:status.confirmed_stock_filter", "Ingresado en Bodega")}</option>
            <option value="ANALYZING">{t("invoices:status.analyzing_filter", "Analizando con IA")}</option>
            <option value="UPLOADED">{t("invoices:status.uploaded", "Cargada")}</option>
            <option value="REJECTED">{t("invoices:status.rejected", "Rechazada")}</option>
            <option value="ERROR">{t("invoices:status.error", "Error OCR")}</option>
          </select>
        </div>

        {/* Selector Tipo DTE */}
        <div>
          <select
            value={filters.dte_type || "ALL"}
            onChange={(e) =>
              onFilterChange("dte_type", e.target.value as DTEType | "ALL")
            }
            className="w-full py-2 px-3 text-xs rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 font-medium"
          >
            <option value="ALL">{t("invoices:dte.all", "Todos los DTE")}</option>
            <option value="FACTURA_ELECTRONICA_33">{t("invoices:dte.filter_33", "Factura Electrónica (33)")}</option>
            <option value="FACTURA_EXENTA_34">{t("invoices:dte.filter_34", "Factura Exenta (34)")}</option>
            <option value="GUIA_DESPACHO_52">{t("invoices:dte.filter_52", "Guía de Despacho (52)")}</option>
            <option value="BOLETA_ELECTRONICA_39">{t("invoices:dte.filter_39", "Boleta Electrónica (39)")}</option>
            <option value="NOTA_CREDITO_61">{t("invoices:dte.filter_61", "Nota de Crédito (61)")}</option>
            <option value="NOTA_DEBITO_56">{t("invoices:dte.filter_56", "Nota de Débito (56)")}</option>
          </select>
        </div>

        {/* Botón Limpiar Filtros */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onReset}
            className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 text-xs font-semibold rounded-xl border border-border hover:bg-muted text-muted-foreground transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {t("invoices:filters.reset_filters", "Limpiar Filtros")}
          </button>
        </div>
      </div>
    </div>
  );
}
