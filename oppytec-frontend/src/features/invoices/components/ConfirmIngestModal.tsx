/**
 * oppytec-frontend/src/features/invoices/components/ConfirmIngestModal.tsx
 * Modal de confirmación transaccional previa antes de asentar stock físico en Kardex y bodegas.
 */

import { useTranslation, Trans } from "react-i18next";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { Box, BookmarkPlus, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { InvoiceLineItem, WarehouseOption } from "../types";

export interface ConfirmIngestModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
  items: InvoiceLineItem[];
  warehouses?: WarehouseOption[];
}

export function ConfirmIngestModal({
  open,
  onClose,
  onConfirm,
  isConfirming,
  items,
  warehouses = [],
}: ConfirmIngestModalProps) {
  const { t } = useTranslation(["invoices"]);
  const newProductsCount = items.filter((i) => i.product_action === "create_new").length;
  const newAliasesCount = items.filter((i) => i.remember_alias).length;

  const totalStock = items.reduce((sum, i) => sum + (i.total_stock_fisico || 0), 0);

  // Bodegas involucradas
  const distinctBodegas = Array.from(new Set(items.map((i) => i.bodega_id)));

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("invoices:confirm_modal.title", "Confirmar Ingreso Físico a Bodega (FEFO)")}
      description={t(
        "invoices:confirm_modal.description",
        "Esta acción actualizará existencias en inventario, registrará movimientos en Kardex y memorizará aliases de proveedor."
      )}
      className="max-w-lg"
    >
      <div className="space-y-4 pt-2">
        {/* Resumen de Métricas */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-muted/60 border border-border">
            <span className="text-[11px] text-muted-foreground block">
              {t("invoices:confirm_modal.purchase_lines", "Líneas de Compra")}
            </span>
            <span className="text-lg font-bold text-foreground font-mono">
              {t("invoices:confirm_modal.items_count", {
                count: items.length,
                defaultValue: `${items.length} ítems`,
              })}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 block font-medium">
              {t("invoices:confirm_modal.total_physical_stock", "Total Físico Ingresado")}
            </span>
            <span className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400 font-mono">
              {t("invoices:confirm_modal.units_kg_suffix", {
                amount: totalStock.toLocaleString("es-CL", { maximumFractionDigits: 2 }),
                defaultValue: `${totalStock.toLocaleString("es-CL", { maximumFractionDigits: 2 })} unidades/kg`,
              })}
            </span>
          </div>
        </div>

        {/* Detalles Transaccionales */}
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2 p-2.5 rounded-xl bg-background border border-border">
            <Box className="h-4 w-4 text-primary shrink-0" />
            <div className="flex-1">
              <strong>{t("invoices:confirm_modal.destination_warehouses", "Bodegas de Destino:")}</strong>{" "}
              {distinctBodegas
                .map((bId) => warehouses.find((w) => w.id === bId)?.nombre || bId)
                .join(", ")}
            </div>
          </div>

          {newProductsCount > 0 && (
            <div className="flex items-center gap-2 p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400">
              <Sparkles className="h-4 w-4 shrink-0" />
              <div className="flex-1">
                <Trans
                  i18nKey="invoices:confirm_modal.new_products_notice"
                  values={{ count: newProductsCount }}
                  components={{ 1: <strong /> }}
                />
              </div>
            </div>
          )}

          {newAliasesCount > 0 && (
            <div className="flex items-center gap-2 p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-600 dark:text-purple-400">
              <BookmarkPlus className="h-4 w-4 shrink-0" />
              <div className="flex-1">
                <Trans
                  i18nKey="invoices:confirm_modal.new_aliases_notice"
                  values={{ count: newAliasesCount }}
                  components={{ 1: <strong /> }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-700 dark:text-amber-400 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <p>
            <Trans
              i18nKey="invoices:confirm_modal.warning"
              components={{ 1: <strong /> }}
            />
          </p>
        </div>

        {/* Acciones */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
          <button
            type="button"
            disabled={isConfirming}
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded-xl border border-border hover:bg-muted text-muted-foreground transition-colors"
          >
            {t("invoices:confirm_modal.cancel", "Cancelar")}
          </button>
          <button
            type="button"
            disabled={isConfirming}
            onClick={onConfirm}
            className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/20 transition-colors disabled:opacity-50"
          >
            {isConfirming ? (
              <>
                <div className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t("invoices:confirm_modal.ingesting", "Ingresando a Kardex...")}
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                {t("invoices:confirm_modal.confirm", "Confirmar e Ingresar")}
              </>
            )}
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
