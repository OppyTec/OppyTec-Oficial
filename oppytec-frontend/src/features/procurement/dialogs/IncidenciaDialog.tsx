/**
 * oppytec-frontend/src/features/procurement/dialogs/IncidenciaDialog.tsx
 * Modal de Registro y Tipificación de Discrepancias en Compras / Recepción.
 * Tipos: DIFERENCIA_CANTIDAD, PRODUCTO_DANADO, FECHA_CADUCADA, PRODUCTO_EQUIVOCADO, OTRO.
 */

import { useState } from "react";
import { AlertTriangle, DollarSign, ShieldAlert } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type { CompraOrder, RegisterIncidencePayload } from "../types";

export interface IncidenciaDialogProps {
  readonly open: boolean;
  readonly order: CompraOrder | null;
  readonly onClose: () => void;
  readonly onConfirm: (payload: RegisterIncidencePayload) => Promise<void> | void;
  readonly isSubmitting?: boolean;
}

export const TIPOS_INCIDENCIA = [
  { value: "DIFERENCIA_CANTIDAD", label: "Diferencia de Cantidad / Faltante" },
  { value: "PRODUCTO_DANADO", label: "Producto Dañado o Roto" },
  { value: "FECHA_CADUCADA", label: "Fecha Caducada o Próxima a Vencer" },
  { value: "PRODUCTO_EQUIVOCADO", label: "Producto Equivocado / No Coincide" },
  { value: "OTRO", label: "Otro / Incumplimiento Contractual" },
] as const;

export const RESOLUCIONES_SOLICITADAS = [
  { value: "REEMPLAZO", label: "Solicitud de Reemplazo Físico" },
  { value: "NOTA_CREDITO", label: "Emisión de Nota de Crédito" },
  { value: "REEMBOLSO", label: "Reembolso Directo de Fondos" },
  { value: "DESCUENTO", label: "Descuento en Siguiente Pedido" },
  { value: "OTRO", label: "Acuerdo Personalizado" },
] as const;

export function IncidenciaDialog({
  open,
  order,
  onClose,
  onConfirm,
  isSubmitting = false,
}: IncidenciaDialogProps) {
  const isMobile = useIsMobile();
  const [tipoIncidencia, setTipoIncidencia] = useState<string>("DIFERENCIA_CANTIDAD");
  const [selectedItemId, setSelectedItemId] = useState<string>("all");
  const [cantidadAfectada, setCantidadAfectada] = useState<number>(1);
  const [montoDisputa, setMontoDisputa] = useState<number>(0);
  const [resolucion, setResolucion] = useState<string>("REEMPLAZO");
  const [descripcion, setDescripcion] = useState<string>("");

  if (!order) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order.id) return;

    const itemIdNumber = selectedItemId === "all" ? null : Number(selectedItemId);

    const payload: RegisterIncidencePayload = {
      order_id: order.id,
      compra_item_id: itemIdNumber,
      tipo_incidencia: tipoIncidencia,
      cantidad_afectada: cantidadAfectada,
      monto_disputa: montoDisputa > 0 ? montoDisputa : undefined,
      resolucion,
      descripcion: descripcion.trim(),
    };

    await onConfirm(payload);
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title="Registrar Incidencia de Compra"
      description={`Orden: ${order.numero_orden || order.po_number} · Proveedor: ${order.proveedor_nombre}`}
      isMobile={isMobile}
      maxWidth="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2 text-xs">
        {/* Banner de Información */}
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-700 dark:text-amber-400">
          <ShieldAlert className="h-5 w-5 shrink-0" />
          <span>
            Las incidencias alimentan el <strong>Scorecard 360°</strong> del proveedor y respaldan notas de crédito o disputas de facturación.
          </span>
        </div>

        {/* Tipo de Incidencia */}
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            Tipo de Incidencia *
          </label>
          <select
            data-testid="incidencia-tipo-select"
            value={tipoIncidencia}
            onChange={(e) => setTipoIncidencia(e.target.value)}
            className="touch-target w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
          >
            {TIPOS_INCIDENCIA.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* Ítem Afectado */}
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            Ítem Afectado
          </label>
          <select
            data-testid="incidencia-item-select"
            value={selectedItemId}
            onChange={(e) => setSelectedItemId(e.target.value)}
            className="touch-target w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
          >
            <option value="all">Orden Completa / No específico</option>
            {order.items?.map((item) => (
              <option key={item.id ?? item.producto_id} value={String(item.id ?? item.producto_id)}>
                {item.producto_nombre} (Sol: {item.cantidad_solicitada})
              </option>
            ))}
          </select>
        </div>

        {/* Cantidad y Monto en Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Cantidad Afectada *
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              data-testid="incidencia-cantidad-input"
              value={cantidadAfectada}
              onChange={(e) => setCantidadAfectada(parseFloat(e.target.value) || 0)}
              className="touch-target w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-foreground focus:border-primary focus:outline-none min-h-[44px]"
            />
          </div>

          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Monto en Disputa (Opcional)
            </label>
            <div className="relative">
              <DollarSign className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="number"
                step="1"
                min="0"
                data-testid="incidencia-monto-input"
                value={montoDisputa || ""}
                onChange={(e) => setMontoDisputa(parseFloat(e.target.value) || 0)}
                placeholder="0"
                className="touch-target w-full rounded-xl border border-border bg-background pl-8 pr-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none min-h-[44px]"
              />
            </div>
          </div>
        </div>

        {/* Resolución Solicitada */}
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            Resolución Solicitada *
          </label>
          <select
            data-testid="incidencia-resolucion-select"
            value={resolucion}
            onChange={(e) => setResolucion(e.target.value)}
            className="touch-target w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
          >
            {RESOLUCIONES_SOLICITADAS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {/* Descripción de la Incidencia */}
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            Descripción y Evidencia Detallada *
          </label>
          <textarea
            rows={3}
            required
            data-testid="incidencia-descripcion-input"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder="Describa el motivo de la discrepancia, condición del embalaje, número de lote o detalles acordados con el transportista..."
            className="w-full rounded-xl border border-border bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Botones de acción */}
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
            disabled={isSubmitting || !descripcion.trim()}
            data-testid="incidencia-submit-btn"
            className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-amber-600 px-5 py-2 text-xs font-bold text-white shadow-md hover:bg-amber-700 active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <AlertTriangle className="h-4 w-4" />
            <span>{isSubmitting ? "Registrando..." : "Registrar Incidencia"}</span>
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
