/**
 * oppytec-frontend/src/features/procurement/dialogs/MercaderiaReceptionDialog.tsx
 * Modal de Recepción Física de Mercadería en Bodega / Andén.
 * Validación de cantidades recibidas, captura de lotes y fechas de vencimiento,
 * y detección reactiva de discrepancias operacionales.
 */

import { useState, useEffect, useMemo } from "react";
import { AlertTriangle, PackageCheck, Calendar, Tag } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type { CompraOrder, ReceiveGoodsPayload, ReceiveGoodsItemPayload } from "../types";

export interface MercaderiaReceptionDialogProps {
  readonly open: boolean;
  readonly order: CompraOrder | null;
  readonly onClose: () => void;
  readonly onConfirm: (payload: ReceiveGoodsPayload) => Promise<void> | void;
  readonly isSubmitting?: boolean;
}

interface ItemReceptionFormState {
  producto_id: number;
  compra_item_id?: number | null;
  producto_nombre: string;
  cantidad_solicitada: number;
  cantidad_recibida: number;
  lote_codigo: string;
  fecha_vencimiento: string;
}

export function MercaderiaReceptionDialog({
  open,
  order,
  onClose,
  onConfirm,
  isSubmitting = false,
}: MercaderiaReceptionDialogProps) {
  const isMobile = useIsMobile();
  const [itemsState, setItemsState] = useState<ItemReceptionFormState[]>([]);
  const [notas, setNotas] = useState("");

  // Inicializar estado cuando se abre una orden
  useEffect(() => {
    if (order && order.items) {
      const initial: ItemReceptionFormState[] = order.items.map((item) => ({
        producto_id: item.producto_id,
        compra_item_id: item.id,
        producto_nombre: item.producto_nombre || `Producto #${item.producto_id}`,
        cantidad_solicitada: Number(item.cantidad_solicitada) || 0,
        cantidad_recibida: Number(item.cantidad_solicitada) || 0,
        lote_codigo: item.lote_codigo || "",
        fecha_vencimiento: item.fecha_vencimiento || "",
      }));
      setItemsState(initial);
      setNotas(order.notas ? `Recepción: ${order.notas}` : "");
    } else {
      setItemsState([]);
      setNotas("");
    }
  }, [order]);

  const updateItem = (
    index: number,
    field: keyof ItemReceptionFormState,
    value: string | number
  ) => {
    setItemsState((prev) => {
      const updated = [...prev];
      const target = updated[index];
      if (target) {
        updated[index] = { ...target, [field]: value } as ItemReceptionFormState;
      }
      return updated;
    });
  };

  // Detectar si hay discrepancias de cantidad
  const hasDiscrepancy = useMemo(() => {
    return itemsState.some(
      (item) => Number(item.cantidad_recibida) !== Number(item.cantidad_solicitada)
    );
  }, [itemsState]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order || !order.id) return;

    const payloadItems: ReceiveGoodsItemPayload[] = itemsState.map((it) => ({
      compra_item_id: it.compra_item_id,
      producto_id: it.producto_id,
      cantidad_recibida: Number(it.cantidad_recibida),
      lote_codigo: it.lote_codigo.trim() || null,
      fecha_vencimiento: it.fecha_vencimiento || null,
    }));

    await onConfirm({
      order_id: order.id,
      items: payloadItems,
      notas: notas.trim() || undefined,
    });
  };

  if (!order) return null;

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={`Recepción de Mercadería: ${order.numero_orden || order.po_number}`}
      description={`Proveedor: ${order.proveedor_nombre} · Destino: ${order.bodega_nombre || "Bodega Central"}`}
      isMobile={isMobile}
      maxWidth="max-w-2xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        {/* Banner de Discrepancia si aplica */}
        {hasDiscrepancy && (
          <div
            data-testid="reception-discrepancy-alert"
            className="flex items-start gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-400"
          >
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Advertencia: Discrepancia en cantidades detectada</p>
              <p className="mt-0.5">
                Una o más cantidades recibidas no coinciden con lo solicitado originalmente.
                Se generará un registro con estado parcial o ajuste de inventario.
              </p>
            </div>
          </div>
        )}

        {/* Listado de ítems para verificar */}
        <div className="space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
            Ítems de la Orden ({itemsState.length})
          </span>

          <div className="space-y-3 max-h-[45vh] overflow-y-auto pr-1">
            {itemsState.map((item, index) => {
              const diff = item.cantidad_recibida - item.cantidad_solicitada;
              const hasItemDiff = diff !== 0;

              return (
                <div
                  key={item.producto_id || index}
                  data-testid={`reception-item-row-${item.producto_id}`}
                  className={`rounded-xl border p-3 text-xs transition-colors ${
                    hasItemDiff
                      ? "border-amber-500/40 bg-amber-500/5"
                      : "border-border bg-card/60"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="font-semibold text-foreground text-sm">
                      {item.producto_nombre}
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-muted-foreground block text-[11px]">
                        Solicitado: <strong className="text-foreground">{item.cantidad_solicitada}</strong>
                      </span>
                      {hasItemDiff && (
                        <span
                          className={`text-[10px] font-bold ${
                            diff > 0 ? "text-blue-500" : "text-amber-600 dark:text-amber-400"
                          }`}
                        >
                          {diff > 0 ? `+${diff}` : `${diff}`} unidades
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Inputs en Grid Responsivo */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                    {/* Cantidad Recibida */}
                    <div>
                      <label className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">
                        Cant. Recibida
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        required
                        data-testid={`input-cantidad-recibida-${item.producto_id}`}
                        value={item.cantidad_recibida}
                        onChange={(e) =>
                          updateItem(index, "cantidad_recibida", parseFloat(e.target.value) || 0)
                        }
                        className="touch-target w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-bold text-foreground focus:border-primary focus:outline-none min-h-[44px]"
                      />
                    </div>

                    {/* Código de Lote */}
                    <div>
                      <label className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">
                        Código de Lote
                      </label>
                      <div className="relative">
                        <Tag className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="LOTE-2026..."
                          data-testid={`input-lote-${item.producto_id}`}
                          value={item.lote_codigo}
                          onChange={(e) => updateItem(index, "lote_codigo", e.target.value)}
                          className="touch-target w-full rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none min-h-[44px]"
                        />
                      </div>
                    </div>

                    {/* Fecha de Vencimiento */}
                    <div>
                      <label className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">
                        Vencimiento
                      </label>
                      <div className="relative">
                        <Calendar className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                        <input
                          type="date"
                          data-testid={`input-vencimiento-${item.producto_id}`}
                          value={item.fecha_vencimiento}
                          onChange={(e) => updateItem(index, "fecha_vencimiento", e.target.value)}
                          className="touch-target w-full rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none min-h-[44px]"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Observaciones de Recepción */}
        <div>
          <label className="text-xs font-bold text-muted-foreground uppercase block mb-1">
            Observaciones / Notas de Andén
          </label>
          <textarea
            rows={2}
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            placeholder="Ej: Embalaje en perfecto estado, temperatura de cadena de frío verificada..."
            className="w-full rounded-xl border border-border bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Botones de acción (touch targets >= 44px) */}
        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="touch-target inline-flex min-h-[44px] min-w-[80px] items-center justify-center rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            data-testid="reception-confirm-btn"
            className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-2 text-xs font-bold text-white shadow-md hover:bg-emerald-700 active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <PackageCheck className="h-4 w-4" />
            <span>{isSubmitting ? "Registrando..." : "Confirmar Recepción"}</span>
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
