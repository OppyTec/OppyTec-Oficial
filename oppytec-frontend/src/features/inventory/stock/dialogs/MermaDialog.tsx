// oppytec-frontend/src/features/inventory/stock/dialogs/MermaDialog.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  ShieldAlert,
  Calendar,
  Trash2,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import type { StockItem, MermaPayload, InventoryLot } from "../../types";

export interface MermaDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly stockItems: StockItem[];
  readonly bodegas: ReadonlyArray<{
    readonly id: number;
    readonly nombre: string;
    readonly color?: string;
    readonly icono?: string;
  }>;
  readonly initialProduct?: StockItem | null;
  readonly onReportMerma: (payload: MermaPayload) => Promise<unknown>;
}

const MOTIVOS_MERMA = [
  { key: "expiration", defaultVal: "Vencimiento / Caducidad" },
  { key: "package_damage", defaultVal: "Daño / Rotura física de envase" },
  { key: "handling_error", defaultVal: "Error de manipulación culinaria" },
  { key: "cold_chain_loss", defaultVal: "Pérdida de cadena de frío" },
  { key: "decomposition", defaultVal: "Descomposición / Mal estado orgánico" },
  { key: "cross_contamination", defaultVal: "Contaminación cruzada" },
  { key: "other_waste", defaultVal: "Otro motivo de desecho" },
] as const;

const UMBRAL_APROBACION_MERMA = 50000; // $50.000 CLP

export function MermaDialog({
  open,
  onClose,
  stockItems,
  bodegas,
  initialProduct,
  onReportMerma,
}: MermaDialogProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();

  const [bodegaId, setBodegaId] = useState<number>(() => {
    return initialProduct?.bodega_id ?? bodegas[0]?.id ?? 1;
  });
  const [productoId, setProductoId] = useState<number>(() => {
    return initialProduct?.producto_id ?? stockItems[0]?.producto_id ?? 1;
  });
  const [cantidad, setCantidad] = useState<number>(1);
  const [selectedLoteCodigo, setSelectedLoteCodigo] = useState<string>("");
  const [motivo, setMotivo] = useState<string>(MOTIVOS_MERMA[0].defaultVal);
  const [detalles, setDetalles] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Inicializar al abrir
  useEffect(() => {
    if (open) {
      const bId = initialProduct?.bodega_id ?? bodegas[0]?.id ?? 1;
      setBodegaId(bId);

      const pId = initialProduct?.producto_id ?? stockItems[0]?.producto_id ?? 1;
      setProductoId(pId);

      const prod = stockItems.find((it) => it.producto_id === pId && it.bodega_id === bId) ||
        stockItems.find((it) => it.producto_id === pId);

      setSelectedLoteCodigo(prod?.lotes?.[0]?.lote_codigo ?? "");
      setCantidad(1);
      setMotivo(t(`modals.merma.reasons.${MOTIVOS_MERMA[0].key}`, MOTIVOS_MERMA[0].defaultVal));
      setDetalles("");
      setIsSubmitting(false);
    }
  }, [open, initialProduct, bodegas, stockItems, t]);

  // Insumos disponibles en la bodega seleccionada
  const availableInWarehouse = useMemo(() => {
    return stockItems.filter((it) => it.bodega_id === bodegaId);
  }, [stockItems, bodegaId]);

  // Insumo actual
  const currentItem = useMemo(() => {
    return availableInWarehouse.find((it) => it.producto_id === productoId) ||
      stockItems.find((it) => it.producto_id === productoId);
  }, [availableInWarehouse, stockItems, productoId]);

  // Lotes disponibles para el producto actual
  const lotes: InventoryLot[] = currentItem?.lotes ?? [];

  // Lote seleccionado
  const selectedLot = useMemo(() => {
    return lotes.find((l) => l.lote_codigo === selectedLoteCodigo);
  }, [lotes, selectedLoteCodigo]);

  // Stock disponible: si hay lote seleccionado, se basa en el lote, de lo contrario stock general
  const stockDisponible = selectedLot ? selectedLot.cantidad : (currentItem?.stock_actual ?? 0);
  const isOverStock = cantidad > stockDisponible;
  const isInvalidQuantity = cantidad <= 0 || isNaN(cantidad);

  // Valorización económica al PPP
  const costoUnitario = currentItem?.costo_unitario_ppp ?? 0;
  const montoValorizado = cantidad * costoUnitario;
  const requiereAprobacion = montoValorizado >= UMBRAL_APROBACION_MERMA;

  const canSubmit = !isSubmitting && !isInvalidQuantity && !isOverStock && Boolean(productoId);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      const fullReason = detalles.trim()
        ? `${motivo}: ${detalles.trim()}`
        : motivo;

      const payload: MermaPayload = {
        producto_id: productoId,
        bodega_id: bodegaId,
        quantity: cantidad,
        unit_cost: costoUnitario,
        reason: fullReason,
        lote_codigo: selectedLoteCodigo || undefined,
      };

      await onReportMerma(payload);
      onClose();
    } catch {
      // Toast ya emitido por hook
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("modals.merma.title", "Declarar Merma Operativa")}
      description={t("modals.merma.description", "Reporte tipificado de insumos caducados, dañados o desechados con valorización al PPP")}
      maxWidth="max-w-xl"
    >
      <div data-testid="dialog-merma-container" className="space-y-4 py-2">
        <div data-testid="dialog-merma-content" className="space-y-4">
        {/* 1. Bodega y Producto */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.merma.warehouse", "Bodega")}
            </label>
            <select
              data-testid="merma-bodega-select"
              aria-label={t("modals.merma.warehouse", "Bodega")}
              value={bodegaId}
              onChange={(e) => {
                const b = Number(e.target.value);
                setBodegaId(b);
                const first = stockItems.find((it) => it.bodega_id === b);
                if (first) {
                  setProductoId(first.producto_id);
                  setSelectedLoteCodigo(first.lotes?.[0]?.lote_codigo ?? "");
                }
              }}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
            >
              {bodegas.map((b) => (
                <option key={`merma-wh-${b.id}`} value={b.id}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.merma.product", "Insumo / Producto Afectado")}
            </label>
            <select
              data-testid="merma-product-select"
              aria-label={t("modals.merma.product", "Insumo / Producto Afectado")}
              value={productoId}
              onChange={(e) => {
                const p = Number(e.target.value);
                setProductoId(p);
                const item = stockItems.find((it) => it.producto_id === p && it.bodega_id === bodegaId);
                setSelectedLoteCodigo(item?.lotes?.[0]?.lote_codigo ?? "");
              }}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
            >
              {availableInWarehouse.map((it) => (
                <option key={`merma-prod-${it.producto_id}`} value={it.producto_id}>
                  {it.nombre} ({it.sku})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 2. Selector de Lote & Vigencia */}
        <div className="space-y-1.5 p-3 rounded-xl bg-muted/20 border border-border">
          <div className="flex items-center justify-between">
            <label className="text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-primary" />
              {t("modals.merma.fefo_control", "Lote & Control FEFO")}
            </label>
            <span className="text-[11px] text-muted-foreground">
              {t("modals.merma.registered_lots", { count: lotes.length, defaultValue: `${lotes.length} lote(s) registrado(s)` })}
            </span>
          </div>

          {lotes.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              {lotes.map((lote) => {
                const isSelected = selectedLoteCodigo === lote.lote_codigo;
                const isExpired = new Date(lote.fecha_vencimiento) < new Date();
                return (
                  <button
                    key={lote.lote_codigo}
                    type="button"
                    data-testid={`merma-lote-badge-${lote.lote_codigo}`}
                    onClick={() => setSelectedLoteCodigo(lote.lote_codigo)}
                    className={cn(
                      "p-2 rounded-lg border text-left text-xs transition-all cursor-pointer flex flex-col justify-between",
                      isSelected
                        ? "border-destructive bg-destructive/10 text-destructive font-bold ring-1 ring-destructive"
                        : "border-border bg-card hover:bg-muted/60 text-foreground"
                    )}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono font-bold truncate">{lote.lote_codigo}</span>
                      {isExpired && (
                        <span className="text-[9px] px-1 py-0.2 rounded bg-destructive text-destructive-foreground font-black uppercase">
                          {t("modals.merma.expired_badge", "Vencido")}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-1">
                      <span>{t("modals.merma.expires_label", { date: lote.fecha_vencimiento, defaultValue: `Vence: ${lote.fecha_vencimiento}` })}</span>
                      <span className="font-mono font-semibold">{t("modals.merma.lot_stock", { stock: lote.cantidad, defaultValue: `Stock: ${lote.cantidad}` })}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic py-1">
              {t("modals.merma.no_lots_notice", "Insumo sin lotes registrados en esta bodega. Se descontará del saldo global.")}
            </p>
          )}
        </div>

        {/* 3. Cantidad y Motivo Tipificado */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                {t("modals.merma.quantity_label", "Cantidad a Dar de Baja")}
              </label>
              <span className="text-[11px] font-mono text-muted-foreground">
                {t("modals.merma.available_stock", {
                  stock: stockDisponible,
                  unit: currentItem?.unidad_medida,
                  defaultValue: `Disp: ${stockDisponible} ${currentItem?.unidad_medida}`,
                })}
              </span>
            </div>
            <div className="relative">
              <input
                type="number"
                data-testid="merma-quantity-input"
                aria-label={t("modals.merma.quantity_label", "Cantidad a Dar de Baja")}
                step="any"
                min="0.001"
                max={stockDisponible}
                value={cantidad || ""}
                onChange={(e) => setCantidad(Number(e.target.value))}
                className={cn(
                  "w-full h-10 px-3 rounded-xl border bg-card text-sm font-mono font-bold outline-none",
                  isOverStock
                    ? "border-destructive text-destructive focus:ring-2 focus:ring-destructive/20"
                    : "border-border text-foreground focus:ring-2 focus:ring-primary/20"
                )}
                placeholder={t("modals.merma.quantity_placeholder", "1.0")}
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground">
                {currentItem?.unidad_medida ?? "u"}
              </span>
            </div>
            {isOverStock && (
              <p className="text-[11px] font-bold text-destructive flex items-center gap-1 mt-0.5">
                <AlertTriangle className="h-3 w-3" />
                <span>{t("modals.merma.error_exceeds_stock", { stock: stockDisponible, defaultValue: `Supera el stock disponible (${stockDisponible})` })}</span>
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.merma.reason_type", "Motivo Tipificado")}
            </label>
            <select
              data-testid="merma-reason-select"
              aria-label={t("modals.merma.reason_type", "Motivo Tipificado")}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
            >
              {MOTIVOS_MERMA.map((m) => (
                <option key={m.key} value={t(`modals.merma.reasons.${m.key}`, m.defaultVal)}>
                  {t(`modals.merma.reasons.${m.key}`, m.defaultVal)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 4. Observaciones y Justificación */}
        <div className="space-y-1">
          <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
            {t("modals.merma.details_label", "Detalles / Observaciones Operativas")}
          </label>
          <textarea
            rows={2}
            data-testid="merma-notes-input"
            aria-label={t("modals.merma.details_label", "Detalles / Observaciones Operativas")}
            value={detalles}
            onChange={(e) => setDetalles(e.target.value)}
            placeholder={t("modals.merma.details_placeholder", "Describa la causa de la pérdida o evidencia física observada...")}
            className="w-full p-2.5 rounded-xl border border-border bg-card text-xs text-foreground outline-none resize-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* 5. Valorización Económica al PPP */}
        <div className="p-3 rounded-xl bg-destructive/5 border border-destructive/20 space-y-2">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="text-muted-foreground">{t("modals.merma.economic_valuation", "Valorización Económica (PPP):")}</span>
            <span className="font-mono text-sm text-destructive font-black">
              {convertAndFormat(montoValorizado, "CLP")}
            </span>
          </div>

          {/* 6. Aviso de Umbral de Aprobación ($50.000 CLP) */}
          {requiereAprobacion && (
            <div
              data-testid="merma-threshold-warning"
              className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400 font-semibold"
            >
              <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div>
                <p className="font-bold">{t("modals.merma.supervisor_approval_title", "Requiere Aprobación de Supervisor")}</p>
                <p className="text-[11px] font-normal mt-0.5 opacity-90">
                  {t("modals.merma.supervisor_approval_desc", {
                    amount: convertAndFormat(montoValorizado, "CLP"),
                    threshold: convertAndFormat(UMBRAL_APROBACION_MERMA, "CLP"),
                    defaultValue: `El monto (${convertAndFormat(montoValorizado, "CLP")}) excede el umbral de control interno de ${convertAndFormat(UMBRAL_APROBACION_MERMA, "CLP")}. Se registrará en estado PENDIENTE DE REVISIÓN antes de impactar el balance contable final.`,
                  })}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 7. Botones de Acción */}
        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="touch-target px-4 py-2 rounded-xl border border-border text-xs font-bold text-foreground hover:bg-secondary cursor-pointer transition-colors"
          >
            {t("modals.merma.cancel", "Cancelar")}
          </button>
          <button
            type="button"
            data-testid="btn-confirm-merma"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={cn(
              "touch-target px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider cursor-pointer shadow-md transition-all flex items-center gap-1.5",
              !canSubmit
                ? "bg-muted text-muted-foreground cursor-not-allowed opacity-60"
                : "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-destructive/20"
            )}
          >
            <Trash2 className="h-4 w-4" />
            <span>{isSubmitting ? t("modals.merma.submitting", "Reportando...") : t("modals.merma.confirm", "Confirmar Merma")}</span>
          </button>
        </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}

export default MermaDialog;
