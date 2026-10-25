// oppytec-frontend/src/features/inventory/stock/dialogs/AdjustmentDialog.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Settings2,
  ArrowDownToLine,
  ArrowUpFromLine,
  AlertCircle,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import type { StockItem, AdjustmentPayload } from "../../types";

export interface AdjustmentDialogProps {
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
  readonly onRegisterMovement: (payload: AdjustmentPayload) => Promise<unknown>;
}

const MOTIVOS_AJUSTE = [
  { key: "quadrature", defaultVal: "Cuadratura de inventario físico" },
  { key: "express_diff", defaultVal: "Diferencia de conteo express" },
  { key: "breakage", defaultVal: "Rotura / Daño accidental" },
  { key: "extraordinary", defaultVal: "Ingreso extraordinario / Hallazgo" },
  { key: "typing_error", defaultVal: "Error de digitación previo" },
  { key: "recipe_calibration", defaultVal: "Ajuste por calibración de recetas" },
  { key: "other_audit", defaultVal: "Otro motivo de auditoría" },
] as const;

export function AdjustmentDialog({
  open,
  onClose,
  stockItems,
  bodegas,
  initialProduct,
  onRegisterMovement,
}: AdjustmentDialogProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();

  const [tipo, setTipo] = useState<"AJUSTE_POSITIVO" | "AJUSTE_NEGATIVO">("AJUSTE_POSITIVO");
  const [bodegaId, setBodegaId] = useState<number>(() => {
    return initialProduct?.bodega_id ?? bodegas[0]?.id ?? 1;
  });
  const [productoId, setProductoId] = useState<number>(() => {
    return initialProduct?.producto_id ?? stockItems[0]?.producto_id ?? 1;
  });
  const [cantidad, setCantidad] = useState<number>(1);
  const [costoUnitario, setCostoUnitario] = useState<number>(0);
  const [motivo, setMotivo] = useState<string>(MOTIVOS_AJUSTE[0].defaultVal);
  const [justificacion, setJustificacion] = useState<string>("");
  const [loteCodigo, setLoteCodigo] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sincronizar al abrir
  useEffect(() => {
    if (open) {
      const bId = initialProduct?.bodega_id ?? bodegas[0]?.id ?? 1;
      setBodegaId(bId);

      const pId = initialProduct?.producto_id ?? stockItems[0]?.producto_id ?? 1;
      setProductoId(pId);

      const target = stockItems.find((it) => it.producto_id === pId && it.bodega_id === bId) ||
        stockItems.find((it) => it.producto_id === pId);
      
      setCostoUnitario(target?.costo_unitario_ppp ?? 0);
      setCantidad(1);
      setTipo("AJUSTE_POSITIVO");
      setMotivo(t(`modals.adjustment.reasons.${MOTIVOS_AJUSTE[0].key}`, MOTIVOS_AJUSTE[0].defaultVal));
      setJustificacion("");
      setLoteCodigo(target?.lotes?.[0]?.lote_codigo ?? "");
      setIsSubmitting(false);
    }
  }, [open, initialProduct, bodegas, stockItems, t]);

  // Insumos disponibles en la bodega seleccionada
  const availableInWarehouse = useMemo(() => {
    return stockItems.filter((it) => it.bodega_id === bodegaId);
  }, [stockItems, bodegaId]);

  // Producto seleccionado actual
  const currentItem = useMemo(() => {
    return availableInWarehouse.find((it) => it.producto_id === productoId) ||
      stockItems.find((it) => it.producto_id === productoId);
  }, [availableInWarehouse, stockItems, productoId]);

  // Al cambiar de producto, recalcular costo unitario y lote
  const handleSelectProduct = (newPId: number) => {
    setProductoId(newPId);
    const prod = stockItems.find((it) => it.producto_id === newPId && it.bodega_id === bodegaId) ||
      stockItems.find((it) => it.producto_id === newPId);
    if (prod) {
      setCostoUnitario(prod.costo_unitario_ppp);
      setLoteCodigo(prod.lotes?.[0]?.lote_codigo ?? "");
    }
  };

  // Validaciones
  const stockActual = currentItem?.stock_actual ?? 0;
  const isOverStock = tipo === "AJUSTE_NEGATIVO" && cantidad > stockActual;
  const isInvalidQuantity = cantidad <= 0 || isNaN(cantidad);
  const canSubmit = !isSubmitting && !isInvalidQuantity && !isOverStock && Boolean(productoId);

  // Cálculo del saldo resultante
  const saldoResultante = tipo === "AJUSTE_POSITIVO"
    ? stockActual + cantidad
    : stockActual - cantidad;

  const impactoFinanciero = cantidad * costoUnitario;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      const fullReason = justificacion.trim()
        ? `${motivo} — ${justificacion.trim()}`
        : motivo;

      const payload: AdjustmentPayload = {
        producto_id: productoId,
        bodega_id: bodegaId,
        tipo_movimiento: tipo,
        cantidad,
        unit_cost: costoUnitario,
        reason: fullReason,
        lote_codigo: loteCodigo || undefined,
      };

      await onRegisterMovement(payload);
      onClose();
    } catch {
      // Toast ya emitido por el hook
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("modals.adjustment.title", "Ajuste Directo de Inventario")}
      description={t("modals.adjustment.description", "Auditoría manual de existencias físicas para cuadratura inmediata en Kardex")}
      maxWidth="max-w-xl"
    >
      <div data-testid="dialog-adjustment-container" className="space-y-4 py-2">
        <div data-testid="dialog-adjustment-content" className="space-y-4">
        {/* 1. Selector de Tipo de Ajuste */}
        <div className="space-y-1.5">
          <label className="text-xs font-black uppercase tracking-wider text-muted-foreground block">
            {t("modals.adjustment.operation_type", "Tipo de Operación")}
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              data-testid="btn-ajuste-positivo"
              aria-label={t("modals.adjustment.positive_type", "+ Entrada (Sobrante)")}
              onClick={() => setTipo("AJUSTE_POSITIVO")}
              className={cn(
                "p-3 rounded-xl border text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer transition-all",
                tipo === "AJUSTE_POSITIVO"
                  ? "bg-emerald-500/15 border-emerald-500 text-emerald-600 dark:text-emerald-400 shadow-xs shadow-emerald-500/20"
                  : "border-border bg-card text-muted-foreground hover:bg-muted/50"
              )}
            >
              <ArrowDownToLine className="h-4 w-4" />
              <span>{t("modals.adjustment.positive_type", "+ Entrada (Sobrante)")}</span>
            </button>

            <button
              type="button"
              data-testid="btn-ajuste-negativo"
              aria-label={t("modals.adjustment.negative_type", "- Salida (Faltante)")}
              onClick={() => setTipo("AJUSTE_NEGATIVO")}
              className={cn(
                "p-3 rounded-xl border text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer transition-all",
                tipo === "AJUSTE_NEGATIVO"
                  ? "bg-destructive/15 border-destructive text-destructive shadow-xs shadow-destructive/20"
                  : "border-border bg-card text-muted-foreground hover:bg-muted/50"
              )}
            >
              <ArrowUpFromLine className="h-4 w-4" />
              <span>{t("modals.adjustment.negative_type", "- Salida (Faltante)")}</span>
            </button>
          </div>
        </div>

        {/* 2. Bodega y Producto */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.adjustment.warehouse", "Bodega")}
            </label>
            <select
              data-testid="adjustment-bodega-select"
              aria-label={t("modals.adjustment.warehouse", "Bodega")}
              value={bodegaId}
              onChange={(e) => {
                const b = Number(e.target.value);
                setBodegaId(b);
                const first = stockItems.find((it) => it.bodega_id === b);
                if (first) {
                  setProductoId(first.producto_id);
                  setCostoUnitario(first.costo_unitario_ppp);
                }
              }}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
            >
              {bodegas.map((b) => (
                <option key={`wh-${b.id}`} value={b.id}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.adjustment.product", "Insumo / Producto")}
            </label>
            <select
              data-testid="adjustment-product-select"
              aria-label={t("modals.adjustment.product", "Insumo / Producto")}
              value={productoId}
              onChange={(e) => handleSelectProduct(Number(e.target.value))}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
            >
              {availableInWarehouse.map((it) => (
                <option key={`prod-${it.producto_id}`} value={it.producto_id}>
                  {it.nombre} ({it.sku})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 3. Cantidad y Costo Unitario */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                {t("modals.adjustment.quantity_label", "Cantidad a Ajustar")}
              </label>
              <span className="text-[11px] font-mono text-muted-foreground">
                {t("modals.adjustment.current_stock", {
                  stock: stockActual,
                  unit: currentItem?.unidad_medida,
                  defaultValue: `Stock actual: ${stockActual} ${currentItem?.unidad_medida}`,
                })}
              </span>
            </div>
            <div className="relative">
              <input
                type="number"
                data-testid="adjustment-quantity-input"
                aria-label={t("modals.adjustment.quantity_label", "Cantidad a Ajustar")}
                step="any"
                min="0.001"
                value={cantidad || ""}
                onChange={(e) => setCantidad(Number(e.target.value))}
                className={cn(
                  "w-full h-10 px-3 rounded-xl border bg-card text-sm font-mono font-bold outline-none",
                  isOverStock
                    ? "border-destructive text-destructive focus:ring-2 focus:ring-destructive/20"
                    : "border-border text-foreground focus:ring-2 focus:ring-primary/20"
                )}
                placeholder={t("modals.adjustment.quantity_placeholder", "1.0")}
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground">
                {currentItem?.unidad_medida ?? "u"}
              </span>
            </div>
            {isOverStock && (
              <p className="text-[11px] font-bold text-destructive flex items-center gap-1 mt-0.5">
                <AlertCircle className="h-3 w-3" />
                <span>{t("modals.adjustment.error_exceeds_stock", { stock: stockActual, defaultValue: `Supera el stock actual (${stockActual})` })}</span>
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.adjustment.cost_label", "Costo Unitario PPP ($)")}
            </label>
            <div className="relative">
              <input
                type="number"
                data-testid="adjustment-cost-input"
                aria-label={t("modals.adjustment.cost_label", "Costo Unitario PPP ($)")}
                step="1"
                min="0"
                value={costoUnitario || ""}
                onChange={(e) => setCostoUnitario(Number(e.target.value))}
                className="w-full h-10 px-3 rounded-xl border border-border bg-card text-sm font-mono font-bold outline-none focus:ring-2 focus:ring-primary/20"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground">
                {t("modals.adjustment.currency_unit", "CLP")}
              </span>
            </div>
          </div>
        </div>

        {/* 4. Motivo y Justificación */}
        <div className="space-y-2">
          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.adjustment.reason_type", "Motivo Tipificado")}
            </label>
            <select
              data-testid="adjustment-reason-select"
              aria-label={t("modals.adjustment.reason_type", "Motivo Tipificado")}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
            >
              {MOTIVOS_AJUSTE.map((m) => (
                <option key={m.key} value={t(`modals.adjustment.reasons.${m.key}`, m.defaultVal)}>
                  {t(`modals.adjustment.reasons.${m.key}`, m.defaultVal)}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("modals.adjustment.audit_detail", "Detalle / Justificación de Auditoría")}
            </label>
            <input
              type="text"
              data-testid="adjustment-notes-input"
              aria-label={t("modals.adjustment.audit_detail", "Detalle / Justificación de Auditoría")}
              value={justificacion}
              onChange={(e) => setJustificacion(e.target.value)}
              placeholder={t("modals.adjustment.audit_detail_placeholder", "Ej: Conteo físico nocturno reveló excedente en estantería...")}
              className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs text-foreground outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        {/* 5. Panel de Balance y Saldo Resultante */}
        <div className="p-3 rounded-xl bg-muted/40 border border-border space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-muted-foreground">{t("modals.adjustment.resulting_balance", "Balance Resultante:")}</span>
            <span className="font-mono font-bold text-foreground">
              {stockActual} →{" "}
              <strong
                className={cn(
                  saldoResultante < 0 ? "text-destructive" : "text-emerald-500 font-black"
                )}
              >
                {saldoResultante} {currentItem?.unidad_medida}
              </strong>
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="font-semibold text-muted-foreground">{t("modals.adjustment.kardex_impact", "Impacto Económico en Kardex:")}</span>
            <span className="font-mono font-bold text-foreground">
              {tipo === "AJUSTE_POSITIVO" ? "+" : "-"}
              {convertAndFormat(impactoFinanciero, "CLP")}
            </span>
          </div>
        </div>

        {/* 6. Botones de Acción */}
        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="touch-target px-4 py-2 rounded-xl border border-border text-xs font-bold text-foreground hover:bg-secondary cursor-pointer transition-colors"
          >
            {t("modals.adjustment.cancel", "Cancelar")}
          </button>
          <button
            type="button"
            data-testid="btn-confirm-adjustment"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={cn(
              "touch-target px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider cursor-pointer shadow-md transition-all flex items-center gap-1.5",
              !canSubmit
                ? "bg-muted text-muted-foreground cursor-not-allowed opacity-60"
                : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-primary/20"
            )}
          >
            <Settings2 className="h-4 w-4" />
            <span>{isSubmitting ? t("modals.adjustment.submitting", "Registrando...") : t("modals.adjustment.confirm", "Registrar Ajuste")}</span>
          </button>
        </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}

export default AdjustmentDialog;
