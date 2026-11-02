// oppytec-frontend/src/features/events/dialogs/ResumenFaltantesDialog.tsx
import { AlertTriangle, Download, Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { i18next } from "@/shared/i18n";
import { useEventAlerts } from "../hooks/useEventAlerts";
import type { FaltanteItem } from "../types";
import { formatDateISO } from "../utils/dateUtils";

export interface ResumenFaltantesDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly faltantesOverride?: FaltanteItem[];
}

export function exportFaltantesToCSV(
  items: FaltanteItem[],
  tFn?: (key: string, options?: Record<string, unknown>) => string
) {
  if (!items || items.length === 0) return;

  const t =
    tFn ??
    ((key: string, options?: Record<string, unknown>) =>
      String(i18next.t(key, { ns: "events", ...options })));

  const rows = [
    [
      t("export.shortages_headers.product_id"),
      t("export.shortages_headers.product"),
      t("export.shortages_headers.warehouse"),
      t("export.shortages_headers.physical_stock"),
      t("export.shortages_headers.committed_stock"),
      t("export.shortages_headers.real_available"),
      t("export.shortages_headers.shortage_deficit"),
      t("export.shortages_headers.unit"),
    ],
  ];

  items.forEach((item) => {
    const id = item.producto_id;
    const nombre = item.producto_nombre || item.nombre || `Producto #${item.producto_id}`;
    const bodega = item.bodega_nombre || `Bodega #${item.bodega_id ?? "1"}`;
    const fisico = item.stock_actual ?? item.disponible ?? 0;
    const necesario = item.cantidad_requerida ?? item.necesario ?? 0;
    const disponibleReal = Math.max(0, fisico - necesario);
    const deficit = item.deficit ?? item.faltante ?? Math.max(0, necesario - fisico);
    const unidad = item.unidad_medida || item.unidad || "u.";

    rows.push([
      String(id),
      nombre,
      bodega,
      String(fisico),
      String(necesario),
      String(disponibleReal),
      String(deficit),
      unidad,
    ]);
  });

  const csvContent =
    "\uFEFF" + rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute(
    "download",
    `${t("export.suggested_order_prefix")}_${formatDateISO(new Date())}.csv`
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function ResumenFaltantesDialog({
  open,
  onClose,
  faltantesOverride,
}: ResumenFaltantesDialogProps) {
  const { t } = useTranslation("events");
  const {
    items: alertsFaltantes,
    isLoading,
    getCommittedStockByProduct,
    criticalAlerts,
  } = useEventAlerts();

  const items: FaltanteItem[] = faltantesOverride ?? alertsFaltantes ?? [];

  const handleExport = () => {
    exportFaltantesToCSV(items, (k, opts) => t(k, opts));
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("shortages_dialog.title")}
      description={t("shortages_dialog.description")}
      maxWidth="max-w-4xl"
    >
      <div data-testid="resumen-faltantes-dialog-content" className="space-y-4 py-2">
        {/* Banner de alerta informativa */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-700 dark:text-amber-400">
          <div className="flex items-center gap-2 text-xs font-semibold">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
            <span>
              {items.length === 1
                ? t("shortages_dialog.alert_detected_single")
                : t("shortages_dialog.alert_detected", { count: items.length })}
            </span>
          </div>

          <button
            type="button"
            data-testid="btn-descargar-csv"
            onClick={handleExport}
            disabled={items.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-bold text-white shadow hover:bg-amber-700 active:scale-95 transition-all cursor-pointer disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t("shortages_dialog.btn_download_csv")}</span>
          </button>
        </div>

        {/* Nota explicativa de fórmula FASE 7 */}
        <div className="flex items-start gap-2 rounded-xl bg-secondary/50 p-3 text-xs text-muted-foreground border border-border/50">
          <Info className="h-4 w-4 shrink-0 text-primary mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-foreground">
              {t("shortages_dialog.formula_title")}
            </span>
            <p className="font-mono text-[11px]">
              {t("shortages_dialog.formula_text")}
            </p>
          </div>
        </div>

        {/* Grilla de items con déficit y detalle de stock comprometido */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[440px] overflow-y-auto pr-1">
          {items.map((item: FaltanteItem) => {
            const prodIdNum = Number(item.producto_id);
            const nombre = item.producto_nombre || item.nombre || `Producto #${item.producto_id}`;
            const necesario = item.cantidad_requerida ?? item.necesario ?? 0;
            const disponible = item.stock_actual ?? item.disponible ?? 0;
            const deficit = item.deficit ?? item.faltante ?? Math.max(0, necesario - disponible);
            const unidad = item.unidad_medida || item.unidad || "u.";

            // Desglose enriquecido desde committedStock
            const committedInfo = getCommittedStockByProduct(item.producto_id, item.bodega_id);
            const stockComprometido = committedInfo ? committedInfo.stock_comprometido : necesario;
            const stockDisponibleReal = committedInfo
              ? committedInfo.stock_disponible_real
              : Math.max(0, disponible - necesario);

            // Verificación si pertenece a un evento crítico < 48h
            const isCriticalItem = criticalAlerts.some((a) =>
              a.insumos_deficit?.some((d) => d.producto_id === prodIdNum)
            );

            return (
              <div
                key={String(item.producto_id)}
                data-testid={`faltante-card-${item.producto_id}`}
                className="flex flex-col justify-between rounded-xl border border-amber-500/25 bg-card p-3 shadow-xs space-y-2 hover:border-amber-500/40 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-start justify-between gap-1">
                    <span className="font-bold text-foreground text-xs line-clamp-2">{nombre}</span>
                    <span
                      data-testid={`badge-deficit-${item.producto_id}`}
                      className="rounded-md bg-rose-500/10 px-1.5 py-0.5 text-[10px] font-bold text-rose-600 shrink-0 border border-rose-500/20"
                    >
                      -{deficit} {unidad}
                    </span>
                  </div>
                  {item.bodega_nombre && (
                    <p className="text-[10px] text-muted-foreground truncate">
                      {t("shortages_dialog.warehouse_label", { name: item.bodega_nombre })}
                    </p>
                  )}
                  {isCriticalItem && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-600 dark:text-rose-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
                      {t("shortages_dialog.critical_badge")}
                    </span>
                  )}
                </div>

                {/* Métricas analíticas de stock FASE 7 */}
                <div className="space-y-1 rounded-lg bg-secondary/30 p-2 text-[11px] font-mono border border-border/40 text-muted-foreground">
                  <div className="flex items-center justify-between">
                    <span>{t("shortages_dialog.metric_physical")}</span>
                    <span className="font-bold text-foreground">{disponible} {unidad}</span>
                  </div>
                  <div className="flex items-center justify-between text-amber-600 dark:text-amber-400">
                    <span>{t("shortages_dialog.metric_committed")}</span>
                    <span className="font-bold">{stockComprometido} {unidad}</span>
                  </div>
                  <div className="flex items-center justify-between border-t border-border/40 pt-1 text-emerald-600 dark:text-emerald-400">
                    <span>{t("shortages_dialog.metric_available")}</span>
                    <span className="font-bold">{stockDisponibleReal} {unidad}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {items.length === 0 && !isLoading && (
          <div className="py-8 text-center text-xs text-muted-foreground">
            {t("shortages_dialog.no_shortages")}
          </div>
        )}
      </div>
    </ResponsiveDialog>
  );
}
