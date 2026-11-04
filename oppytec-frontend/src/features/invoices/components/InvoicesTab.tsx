/**
 * oppytec-frontend/src/features/invoices/components/InvoicesTab.tsx
 * Pestaña principal de Facturas con toolbar, uploader desplegable, filtros y tabla interactiva.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { UploadCloud, ChevronDown, ChevronUp } from "lucide-react";
import { InvoiceUploader } from "./InvoiceUploader";
import { InvoiceFilters } from "./InvoiceFilters";
import { InvoiceTable } from "./InvoiceTable";
import { BulkActionsBar } from "./BulkActionsBar";
import type { ExportFormat, Invoice, InvoiceFilters as FilterState } from "../types";

export interface InvoicesTabProps {
  invoices: Invoice[];
  isLoading: boolean;
  filters: FilterState;
  searchInput: string;
  onSearchChange: (val: string) => void;
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onResetFilters: () => void;
  onUpload: (files: File[]) => Promise<any>;
  isUploading: boolean;
  uploadProgress: number;
  onReprocess: (id: string) => void;
  onDelete: (id: string) => void;
  onBulkProcess: (ids: string[]) => void;
  isBulkProcessing: boolean;
  onBulkDelete: (ids: string[]) => void;
  isBulkDeleting: boolean;
  onExport: (format: ExportFormat, ids: string[]) => void;
  isExporting: boolean;
}

export function InvoicesTab({
  invoices,
  isLoading,
  filters,
  searchInput,
  onSearchChange,
  onFilterChange,
  onResetFilters,
  onUpload,
  isUploading,
  uploadProgress,
  onReprocess,
  onDelete,
  onBulkProcess,
  isBulkProcessing,
  onBulkDelete,
  isBulkDeleting,
  onExport,
  isExporting,
}: InvoicesTabProps) {
  const { t } = useTranslation(["invoices"]);
  const [showUploader, setShowUploader] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = () => {
    if (selectedIds.length === invoices.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(invoices.map((i) => i.id));
    }
  };

  return (
    <div data-testid="invoices-tab" className="space-y-4">
      {/* Botón para alternar zona de subida */}
      <div className="flex justify-between items-center">
        <button
          type="button"
          onClick={() => setShowUploader((prev) => !prev)}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20 transition-all min-h-[44px]"
        >
          <UploadCloud className="h-4 w-4" />
          <span>
            {showUploader
              ? t("invoices:invoices_tab.hide_uploader", "Ocultar Carga de Facturas")
              : t("invoices:invoices_tab.show_uploader", "Cargar Facturas DTE (IA Gemini)")}
          </span>
          {showUploader ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
        </button>
      </div>

      {/* Zona de subida colapsable */}
      {showUploader && (
        <InvoiceUploader
          onUpload={async (files) => {
            await onUpload(files);
            setShowUploader(false);
          }}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
        />
      )}

      {/* Filtros */}
      <InvoiceFilters
        filters={filters}
        searchInput={searchInput}
        onSearchChange={onSearchChange}
        onFilterChange={onFilterChange}
        onReset={onResetFilters}
      />

      {/* Tabla de Facturas */}
      <InvoiceTable
        invoices={invoices}
        isLoading={isLoading}
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
        onToggleSelectAll={handleToggleSelectAll}
        onReprocess={onReprocess}
        onDelete={onDelete}
      />

      {/* Barra de Acciones Masivas Flotante */}
      <BulkActionsBar
        selectedCount={selectedIds.length}
        onClearSelection={() => setSelectedIds([])}
        onBulkProcess={() => onBulkProcess(selectedIds)}
        isBulkProcessing={isBulkProcessing}
        onBulkDelete={() => {
          onBulkDelete(selectedIds);
          setSelectedIds([]);
        }}
        isBulkDeleting={isBulkDeleting}
        onExport={(format) => onExport(format, selectedIds)}
        isExporting={isExporting}
      />
    </div>
  );
}
