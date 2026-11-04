/**
 * oppytec-frontend/src/features/invoices/components/BulkActionsBar.tsx
 * Barra flotante inferior para acciones masivas (procesar, exportar, eliminar) sobre facturas.
 */

import { useTranslation } from "react-i18next";
import { Play, Trash2, X } from "lucide-react";
import { ExportDropdown } from "./ExportDropdown";
import type { ExportFormat } from "../types";

export interface BulkActionsBarProps {
  selectedCount: number;
  onClearSelection: () => void;
  onBulkProcess: () => void;
  isBulkProcessing: boolean;
  onBulkDelete: () => void;
  isBulkDeleting: boolean;
  onExport: (format: ExportFormat) => void;
  isExporting: boolean;
}

export function BulkActionsBar({
  selectedCount,
  onClearSelection,
  onBulkProcess,
  isBulkProcessing,
  onBulkDelete,
  isBulkDeleting,
  onExport,
  isExporting,
}: BulkActionsBarProps) {
  const { t } = useTranslation(["invoices"]);
  if (selectedCount === 0) return null;

  return (
    <div
      data-testid="bulk-actions-bar"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 rounded-2xl border border-border/80 bg-popover/95 backdrop-blur-md shadow-2xl animate-in slide-in-from-bottom-5 text-xs text-foreground max-w-[95vw] flex-wrap justify-center"
    >
      <div className="flex items-center gap-2 font-bold font-mono">
        <span className="h-6 w-6 rounded-lg bg-primary/15 text-primary flex items-center justify-center text-xs">
          {selectedCount}
        </span>
        <span>
          {selectedCount === 1
            ? t("invoices:bulk_actions.selected_singular", "factura seleccionada")
            : t("invoices:bulk_actions.selected_plural", "facturas seleccionadas")}
        </span>
      </div>

      <div className="h-4 w-px bg-border/80 hidden sm:block" />

      {/* Procesar Masivamente */}
      <button
        type="button"
        disabled={isBulkProcessing}
        onClick={onBulkProcess}
        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50"
      >
        <Play className="h-3.5 w-3.5" />
        {isBulkProcessing
          ? t("invoices:bulk_actions.processing", "Procesando...")
          : t("invoices:bulk_actions.process_bulk", "Procesar con IA")}
      </button>

      {/* Exportar */}
      <ExportDropdown onExport={onExport} isExporting={isExporting} />

      {/* Eliminar Masivamente */}
      <button
        type="button"
        disabled={isBulkDeleting}
        onClick={() => {
          if (
            confirm(
              t("invoices:bulk_actions.delete_confirm", {
                count: selectedCount,
                defaultValue: `¿Eliminar ${selectedCount} facturas seleccionadas?`,
              })
            )
          ) {
            onBulkDelete();
          }
        }}
        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-500/15 text-rose-600 dark:text-rose-400 font-semibold hover:bg-rose-500/25 transition-colors border border-rose-500/30 disabled:opacity-50"
      >
        <Trash2 className="h-3.5 w-3.5" />
        {isBulkDeleting
          ? t("invoices:bulk_actions.deleting", "Eliminando...")
          : t("invoices:bulk_actions.delete_bulk", "Eliminar")}
      </button>

      <button
        type="button"
        onClick={onClearSelection}
        title={t("invoices:bulk_actions.cancel_selection", "Cancelar selección")}
        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors ml-1"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
