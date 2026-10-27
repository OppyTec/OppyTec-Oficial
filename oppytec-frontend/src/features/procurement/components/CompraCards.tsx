/**
 * oppytec-frontend/src/features/procurement/components/CompraCards.tsx
 * Vista Alternativa Mobile-First en Tarjetas Táctiles (Touch targets >= 44px).
 * ADN Visual Legacy y Adaptabilidad para Pantallas Móviles y Tablets.
 */

import { Eye, PackageCheck, AlertTriangle, XCircle, Calendar, Building2, Package, FileQuestion } from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { CompraOrder } from "../types";
import { getEstadoBadgeConfig, formatDateSafe } from "./CompraTable";

export interface CompraCardsProps {
  readonly orders: CompraOrder[];
  readonly isLoading?: boolean;
  readonly onView: (order: CompraOrder) => void;
  readonly onReceive: (order: CompraOrder) => void;
  readonly onIncidence: (order: CompraOrder) => void;
  readonly onCancel: (order: CompraOrder) => void;
}

export function CompraCards({
  orders,
  isLoading = false,
  onView,
  onReceive,
  onIncidence,
  onCancel,
}: CompraCardsProps) {
  const { format } = useCurrencyFormatter();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[1, 2, 3, 4].map((idx) => (
          <div
            key={idx}
            className="glass-card flex min-h-[180px] animate-pulse flex-col justify-between rounded-2xl border border-border p-4"
          >
            <div className="h-4 w-1/3 rounded bg-muted" />
            <div className="h-6 w-2/3 rounded bg-muted" />
            <div className="h-4 w-1/2 rounded bg-muted" />
          </div>
        ))}
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div
        data-testid="compras-cards-empty"
        className="flex min-h-[250px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-6 text-center"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          <FileQuestion className="h-6 w-6" />
        </div>
        <h3 className="mt-3 text-sm font-bold text-foreground">No hay órdenes para mostrar</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Intente ajustar los filtros de búsqueda o registre una nueva orden.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="compra-cards-grid" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {orders.map((order) => {
        const badge = getEstadoBadgeConfig(order.estado);
        const orderId = order.id ?? order.numero_orden;
        const canReceive =
          order.estado === "SOLICITADA" ||
          order.estado === "EN_CAMINO" ||
          order.estado === "RECIBIDA_PARCIAL";
        const canCancel =
          order.estado !== "CANCELADA" && order.estado !== "RECIBIDA_TOTAL";

        return (
          <div
            key={orderId}
            data-testid={`compra-card-${order.numero_orden}`}
            className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm transition-all hover:border-primary/40"
          >
            {/* Header: N° Orden y Badge de Estado */}
            <div className="flex items-start justify-between gap-2 border-b border-border pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Orden de Compra
                </span>
                <h4 className="font-mono text-base font-black text-foreground">
                  {order.numero_orden || order.po_number}
                </h4>
              </div>
              <span
                data-testid={`card-status-badge-${order.estado}`}
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${badge.className}`}
              >
                {badge.label}
              </span>
            </div>

            {/* Contenido / Metadata */}
            <div className="my-3 space-y-2 text-xs">
              <div className="flex items-center gap-1.5 text-foreground font-semibold">
                <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate" title={order.proveedor_nombre}>
                  {order.proveedor_nombre || order.supplier_name}
                </span>
              </div>

              {order.bodega_nombre && (
                <div className="text-[11px] text-muted-foreground pl-5 truncate">
                  Destino: {order.bodega_nombre}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 pt-1 text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 shrink-0" />
                  <span>Emisión: {formatDateSafe(order.fecha_emision)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 shrink-0" />
                  <span>Entrega: {formatDateSafe(order.fecha_entrega_comprometida || order.fecha_entrega_estimada)}</span>
                </div>
              </div>

              {/* Items y Monto Total */}
              <div className="flex items-center justify-between rounded-xl bg-secondary/30 px-3 py-2 text-xs">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Package className="h-3.5 w-3.5" />
                  <span>{order.items_count ?? order.items?.length ?? 0} ítems</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase text-muted-foreground block">Total Neto + IVA</span>
                  <span className="text-sm font-black text-foreground">
                    {format(order.monto_total)}
                  </span>
                </div>
              </div>
            </div>

            {/* Botones de acción táctiles (touch targets >= 44px) */}
            <div className="grid grid-cols-2 gap-2 border-t border-border pt-3">
              <button
                type="button"
                onClick={() => onView(order)}
                data-testid={`card-view-btn-${order.numero_orden}`}
                className="touch-target inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground transition-all hover:bg-muted active:scale-95 cursor-pointer"
              >
                <Eye className="h-4 w-4" />
                <span>Ver Detalle</span>
              </button>

              {canReceive ? (
                <button
                  type="button"
                  onClick={() => onReceive(order)}
                  data-testid={`card-receive-btn-${order.numero_orden}`}
                  className="touch-target inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-emerald-700 active:scale-95 cursor-pointer"
                >
                  <PackageCheck className="h-4 w-4" />
                  <span>Recepcionar</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => onIncidence(order)}
                  data-testid={`card-incidence-btn-${order.numero_orden}`}
                  className="touch-target inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-600 dark:text-amber-400 transition-all hover:bg-amber-500/20 active:scale-95 cursor-pointer"
                >
                  <AlertTriangle className="h-4 w-4" />
                  <span>Incidencia</span>
                </button>
              )}

              {canReceive && (
                <button
                  type="button"
                  onClick={() => onIncidence(order)}
                  data-testid={`card-secondary-incidence-btn-${order.numero_orden}`}
                  className="touch-target col-span-1 inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-600 dark:text-amber-400 transition-all hover:bg-amber-500/20 active:scale-95 cursor-pointer"
                >
                  <AlertTriangle className="h-4 w-4" />
                  <span>Incidencia</span>
                </button>
              )}

              {canCancel && (
                <button
                  type="button"
                  onClick={() => onCancel(order)}
                  data-testid={`card-cancel-btn-${order.numero_orden}`}
                  className={`touch-target inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-600 dark:text-rose-400 transition-all hover:bg-rose-500/20 active:scale-95 cursor-pointer ${
                    !canReceive ? "col-span-2" : "col-span-1"
                  }`}
                >
                  <XCircle className="h-4 w-4" />
                  <span>Cancelar</span>
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
