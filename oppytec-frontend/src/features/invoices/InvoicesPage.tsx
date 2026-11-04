/**
 * oppytec-frontend/src/features/invoices/InvoicesPage.tsx
 * Vista principal del Módulo de Facturas y Conciliación Contable DTE (`/contabilidad/facturas`).
 * SectionHeader temático (#6366f1), AreaSelector y navegación entre 3 pestañas:
 * Dashboard, Facturas y Pipeline.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FileText, LayoutDashboard, ListFilter, Webhook } from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { useInvoices } from "./useInvoices";
import { DashboardTab } from "./components/DashboardTab";
import { InvoicesTab } from "./components/InvoicesTab";
import { PipelineTab } from "./components/PipelineTab";
import { cn } from "@/shared/lib";

export type InvoicesActiveTab = "dashboard" | "invoices" | "pipeline";

export function InvoicesPage() {
  const { t } = useTranslation(["invoices"]);
  const [activeTab, setActiveTab] = useState<InvoicesActiveTab>("invoices");

  const {
    invoices,
    isLoadingInvoices,
    filters,
    searchInput,
    setSearchInput,
    setFilter,
    resetFilters,
    stats,
    isLoadingStats,
    priceDriftItems,
    isLoadingPriceDrift,
    uploadInvoices,
    isUploading,
    uploadProgress,
    reprocessInvoice,
    deleteInvoice,
    bulkProcess,
    isBulkProcessing,
    bulkDelete,
    isBulkDeleting,
    exportInvoices,
    isExporting,
  } = useInvoices();

  return (
    <div
      data-testid="invoices-page"
      className="container mx-auto px-4 py-6 max-w-7xl space-y-6"
    >
      {/* Encabezado con ADN Visual Legacy */}
      <SectionHeader
        title={t("invoices:page.title", "Facturas")}
        subtitle={t("invoices:page.subtitle", "Procesamiento y Gestión de Compras con IA")}
        icon={FileText}
        color="#6366f1"
        center={true}
      />

      {/* Toolbar unificado: Selector de Área Operativa y Pestañas de Navegación */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 glass-card rounded-2xl border border-border p-3 shadow-sm">
        {/* Selector de Área Operativa */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap hidden sm:inline">
            {t("invoices:page.operative_area", "Área Operativa:")}
          </span>
          <AreaSelector
            selectedAreaId={filters.area_id}
            onSelectArea={(areaId) => setFilter("area_id", areaId)}
            allowAll={true}
            className="w-full sm:w-auto"
          />
        </div>

        {/* Selector de Pestañas con estilo Mobile-First y touch targets >= 44px */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-muted/60 border border-border/80 w-full md:w-auto overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab("dashboard")}
            className={cn(
              "flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all min-h-[44px]",
              activeTab === "dashboard"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <LayoutDashboard className="h-4 w-4" />
            {t("invoices:tabs.dashboard", "Dashboard")}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("invoices")}
            className={cn(
              "flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all min-h-[44px]",
              activeTab === "invoices"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <ListFilter className="h-4 w-4" />
            {t("invoices:tabs.invoices", "Facturas")}
            {stats?.pending_review ? (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-amber-500/20 text-amber-600 dark:text-amber-400">
                {stats.pending_review}
              </span>
            ) : null}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("pipeline")}
            className={cn(
              "flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all min-h-[44px]",
              activeTab === "pipeline"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Webhook className="h-4 w-4" />
            {t("invoices:tabs.pipeline", "Pipeline")}
          </button>
        </div>
      </div>

      {/* Contenido Dinámico de la Pestaña Activa */}
      {activeTab === "dashboard" && (
        <DashboardTab
          stats={stats}
          priceDriftItems={priceDriftItems}
          isLoading={isLoadingStats || isLoadingPriceDrift}
          onNavigateToReview={() => {
            setFilter("status", "READY_FOR_REVIEW");
            setActiveTab("invoices");
          }}
        />
      )}

      {activeTab === "invoices" && (
        <InvoicesTab
          invoices={invoices}
          isLoading={isLoadingInvoices}
          filters={filters}
          searchInput={searchInput}
          onSearchChange={setSearchInput}
          onFilterChange={setFilter}
          onResetFilters={resetFilters}
          onUpload={uploadInvoices}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
          onReprocess={reprocessInvoice}
          onDelete={deleteInvoice}
          onBulkProcess={bulkProcess}
          isBulkProcessing={isBulkProcessing}
          onBulkDelete={bulkDelete}
          isBulkDeleting={isBulkDeleting}
          onExport={(format, ids) => exportInvoices({ ids, format })}
          isExporting={isExporting}
        />
      )}

      {activeTab === "pipeline" && <PipelineTab />}
    </div>
  );
}

export default InvoicesPage;
