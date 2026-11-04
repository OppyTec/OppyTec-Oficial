/**
 * oppytec-frontend/src/features/invoices/InvoiceDetailPage.tsx
 * Inspector Dual en Pantalla Dividida (Split Screen) para conciliación contable y revisión de empaque.
 * Panel izquierdo: Visor interactivo de documento PDF/imagen original.
 * Panel derecho: Banner de proveedor, banderas de auditoría y grilla interactiva de 13 columnas.
 * Barra inferior con confirmación e ingreso transaccional a inventario (Kardex FEFO).
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { useInvoiceDetail } from "./useInvoices";
import { InvoicePreview } from "./components/InvoicePreview";
import { FacturaSupplierBanner } from "./components/FacturaSupplierBanner";
import { AuditWarnings } from "./components/AuditWarnings";
import { FacturaReviewGrid } from "./components/FacturaReviewGrid";
import { ConfirmIngestModal } from "./components/ConfirmIngestModal";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { cn } from "@/shared/lib";

export function InvoiceDetailPage() {
  const { t } = useTranslation(["invoices"]);
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  const [mobileTab, setMobileTab] = useState<"doc" | "grid">("grid");
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);

  const {
    invoice,
    isLoading,
    error,
    editableItems,
    setEditableItems,
    hasUnsavedChanges,
    discardDraft,
    saveChanges,
    isSaving,
    confirmStockIngest,
    isConfirmingStock,
  } = useInvoiceDetail(id);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12 flex flex-col items-center justify-center min-h-[400px]">
        <div className="h-10 w-10 animate-spin rounded-2xl border-4 border-primary border-t-transparent shadow-lg shadow-primary/20" />
        <p className="mt-4 text-xs font-semibold text-muted-foreground animate-pulse">
          {t("invoices:detail_page.loading", "Cargando factura e inspector multimodal...")}
        </p>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="container mx-auto px-4 py-12 max-w-lg text-center space-y-4">
        <div className="h-14 w-14 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto">
          <AlertTriangle className="h-7 w-7" />
        </div>
        <h3 className="text-base font-bold text-foreground">
          {t("invoices:detail_page.not_found_title", "Factura no encontrada")}
        </h3>
        <p className="text-xs text-muted-foreground">
          {t("invoices:detail_page.not_found_desc", "No fue posible cargar los datos de la factura solicitada o fue eliminada previamente.")}
        </p>
        <button
          type="button"
          onClick={() => navigate("/contabilidad/facturas")}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("invoices:detail_page.back_to_invoices", "Volver a Facturas")}
        </button>
      </div>
    );
  }

  const handleConfirmStock = async () => {
    try {
      await confirmStockIngest({
        bodega_id: invoice.confirmed_bodega_id || "bod-central",
        items: editableItems.map((item) => ({
          item_id: item.id,
          product_action: item.product_action,
          product_id: item.matched_product_id,
          product_name: item.nombre_negocio || item.raw_description,
          categoria_id: item.categoria_id,
          bodega_id: item.bodega_id,
          factor_empaque: item.factor_empaque,
          kitchen_base_unit: item.kitchen_base_unit,
          total_stock_fisico: item.total_stock_fisico,
          costo_unitario_inventario: item.costo_unitario_inventario,
          remember_alias: item.remember_alias,
        })),
      });
      setIsConfirmModalOpen(false);
    } catch {
      // Error handled by hook toast
    }
  };

  return (
    <div
      data-testid="invoice-detail-page"
      className="container mx-auto px-4 py-4 max-w-[1700px] space-y-4 pb-24"
    >
      {/* Barra de Navegación Superior */}
      <div className="flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => navigate("/contabilidad/facturas")}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-bold rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors min-h-[44px]"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>{t("invoices:detail_page.back_to_invoices", "Volver a Facturas")}</span>
        </button>

        <div className="flex items-center gap-2">
          {hasUnsavedChanges && (
            <span className="text-[11px] font-semibold text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">
              {t("invoices:detail_page.unsaved_changes", "● Cambios no guardados")}
            </span>
          )}
        </div>
      </div>

      {/* Selector Móvil de Paneles */}
      {isMobile && (
        <div className="flex items-center gap-2 p-1 rounded-xl bg-muted/60 border border-border">
          <button
            type="button"
            onClick={() => setMobileTab("doc")}
            className={cn(
              "flex-1 py-2 text-xs font-bold rounded-lg transition-all min-h-[44px]",
              mobileTab === "doc"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground"
            )}
          >
            {t("invoices:detail_page.mobile_doc_tab", "Documento Original")}
          </button>
          <button
            type="button"
            onClick={() => setMobileTab("grid")}
            className={cn(
              "flex-1 py-2 text-xs font-bold rounded-lg transition-all min-h-[44px]",
              mobileTab === "grid"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground"
            )}
          >
            {t("invoices:detail_page.mobile_grid_tab", { count: editableItems.length, defaultValue: `Líneas de Compra (${editableItems.length})` })}
          </button>
        </div>
      )}

      {/* Inspector Dual en Pantalla Dividida (50% / 50% en desktop) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* Panel Izquierdo: Visor Interactivo de Documento Original (5 columnas) */}
        <div
          className={cn(
            "xl:col-span-5 xl:sticky xl:top-4",
            isMobile && mobileTab !== "doc" && "hidden"
          )}
        >
          <InvoicePreview
            fileUrl={invoice.file_url}
            fileType={invoice.file_type}
            filename={invoice.filename}
          />
        </div>

        {/* Panel Derecho: Banner de Proveedor + Grilla de 13 Columnas (7 columnas) */}
        <div
          className={cn(
            "xl:col-span-7 space-y-4",
            isMobile && mobileTab !== "grid" && "hidden"
          )}
        >
          {/* Banner de Proveedor */}
          <FacturaSupplierBanner invoice={invoice} />

          {/* Advertencias de Auditoría */}
          <AuditWarnings flags={invoice.audit_flags} />

          {/* Grilla Interactiva de 13 Columnas */}
          <FacturaReviewGrid
            items={editableItems}
            onChangeItems={setEditableItems}
          />
        </div>
      </div>

      {/* Barra de Acciones Fija Inferior */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-background/95 backdrop-blur-md border-t border-border p-3 shadow-2xl">
        <div className="container mx-auto max-w-[1700px] flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            {hasUnsavedChanges && (
              <button
                type="button"
                onClick={discardDraft}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors min-h-[44px]"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                {t("invoices:detail_page.discard_changes", "Descartar Cambios")}
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Guardar Cambios */}
            <button
              type="button"
              disabled={isSaving}
              onClick={() => saveChanges(invoice)}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl border border-border bg-background hover:bg-muted/80 text-foreground transition-colors shadow-sm disabled:opacity-50 min-h-[44px]"
            >
              <Save className="h-4 w-4" />
              {isSaving ? t("invoices:detail_page.saving", "Guardando...") : t("invoices:detail_page.save_changes", "Guardar Cambios")}
            </button>

            {/* Botón Primario Verde Destacado: Ingresar a Bodega (Auto-Stock) */}
            <button
              type="button"
              disabled={isConfirmingStock || invoice.is_confirmed_to_inventory}
              onClick={() => setIsConfirmModalOpen(true)}
              className={cn(
                "inline-flex items-center gap-2 px-5 py-2 text-xs font-extrabold rounded-xl transition-all shadow-lg min-h-[44px]",
                invoice.is_confirmed_to_inventory
                  ? "bg-muted text-muted-foreground cursor-not-allowed border border-border"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/25 hover:shadow-emerald-600/40 active:scale-[0.98]"
              )}
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>
                {invoice.is_confirmed_to_inventory
                  ? t("invoices:detail_page.stock_already_ingested", "Stock Ya Ingresado en Bodega")
                  : t("invoices:detail_page.ingest_to_warehouse", "Ingresar a Bodega (Auto-Stock)")}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Modal de Confirmación Transaccional */}
      <ConfirmIngestModal
        open={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        onConfirm={handleConfirmStock}
        isConfirming={isConfirmingStock}
        items={editableItems}
      />
    </div>
  );
}

export default InvoiceDetailPage;
