/**
 * oppytec-frontend/src/features/procurement/components/CompraTable.tsx
 * Tabla Multidimensional de Órdenes de Compra con ADN Visual Legacy.
 * Badges temáticos exactos, formateo FX con precisión Decimal y acciones táctiles.
 */

import { Eye, PackageCheck, AlertTriangle, XCircle, FileQuestion, Calendar, Building2 } from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { CompraEstado, CompraOrder } from "../types";

export interface CompraTableProps {
  readonly orders: CompraOrder[];
  readonly isLoading?: boolean;
  readonly onView: (order: CompraOrder) => void;
  readonly onReceive: (order: CompraOrder) => void;
  readonly onIncidence: (order: CompraOrder) => void;
  readonly onCancel: (order: CompraOrder) => void;
}

export function getEstadoBadgeConfig(estado: CompraEstado): {
  label: string;
  className: string;
} {
  switch (estado) {
    case "BORRADOR":
      return {
        label: "Borrador",
        className: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/30",
      };
    case "SOLICITADA":
      return {
        label: "Solicitada",
        className: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
      };
    case "EN_CAMINO":
      return {
        label: "En Camino",
        className: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
      };
    case "RECIBIDA_PARCIAL":
      return {
        label: "Recibida Parcial",
        className: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30",
      };
    case "RECIBIDA_TOTAL":
      return {
        label: "Recibida Conforme",
        className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
      };
    case "CANCELADA":
      return {
        label: "Cancelada",
        className: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30",
      };
    default:
      return {
        label: estado,
        className: "bg-muted text-muted-foreground border-border",
      };
  }
}

export function formatDateSafe(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleDateString("es-CL", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return isoString;
  }
}

export function CompraTable({
  orders,
  isLoading = false,
  onView,
  onReceive,
  onIncidence,
  onCancel,
}: CompraTableProps) {
  const { format } = useCurrencyFormatter();

  if (isLoading) {
    return (
      <div className="flex min-h-[250px] items-center justify-center rounded-2xl border border-border bg-card p-6">
        <div className="flex flex-col items-center gap-2">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-xs text-muted-foreground">Cargando órdenes de compra...</p>
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div
        data-testid="compras-table-empty"
        className="flex min-h-[280px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-8 text-center"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <FileQuestion className="h-7 w-7" />
        </div>
        <h3 className="mt-3 text-sm font-bold text-foreground">No se encontraron órdenes de compra</h3>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          No hay órdenes registradas que coincidan con los filtros aplicados.
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="compra-table"
      className="glass-card overflow-hidden rounded-2xl border border-border shadow-sm"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-foreground">
          <thead className="border-b border-border bg-muted/40 uppercase tracking-wider text-muted-foreground">
            <tr>
              <th scope="col" className="px-4 py-3.5 font-semibold">
                N° Orden
              </th>
              <th scope="col" className="px-4 py-3.5 font-semibold">
                Proveedor
              </th>
              <th scope="col" className="px-4 py-3.5 font-semibold">
                Fecha Emisión
              </th>
              <th scope="col" className="px-4 py-3.5 font-semibold">
                Entrega Comprometida
              </th>
              <th scope="col" className="px-4 py-3.5 font-semibold">
                Estado
              </th>
              <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                Total Neto + IVA
              </th>
              <th scope="col" className="px-4 py-3.5 text-center font-semibold">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
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
                <tr
                  key={orderId}
                  data-testid={`compra-row-${order.numero_orden}`}
                  className="transition-colors hover:bg-muted/30"
                >
                  {/* N° Orden */}
                  <td className="whitespace-nowrap px-4 py-3 font-mono font-bold text-foreground">
                    {order.numero_orden || order.po_number || "—"}
                  </td>

                  {/* Proveedor */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <Building2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="font-semibold text-foreground truncate max-w-[220px]" title={order.proveedor_nombre}>
                        {order.proveedor_nombre || order.supplier_name}
                      </span>
                    </div>
                    {order.bodega_nombre && (
                      <span className="text-[11px] text-muted-foreground block truncate max-w-[200px]">
                        Destino: {order.bodega_nombre}
                      </span>
                    )}
                  </td>

                  {/* Fecha Emisión */}
                  <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5 shrink-0" />
                      <span>{formatDateSafe(order.fecha_emision)}</span>
                    </div>
                  </td>

                  {/* Fecha Entrega */}
                  <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5 shrink-0" />
                      <span>{formatDateSafe(order.fecha_entrega_comprometida || order.fecha_entrega_estimada)}</span>
                    </div>
                  </td>

                  {/* Estado Badge */}
                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      data-testid={`status-badge-${order.estado}`}
                      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                  </td>

                  {/* Total FX */}
                  <td className="whitespace-nowrap px-4 py-3 text-right font-black text-foreground">
                    {format(order.monto_total)}
                  </td>

                  {/* Acciones */}
                  <td className="whitespace-nowrap px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      {/* Ver */}
                      <button
                        type="button"
                        onClick={() => onView(order)}
                        title="Ver detalle"
                        data-testid={`compra-view-btn-${order.numero_orden}`}
                        className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-muted hover:text-foreground active:scale-95 cursor-pointer"
                      >
                        <Eye className="h-4 w-4" />
                      </button>

                      {/* Recepcionar */}
                      {canReceive && (
                        <button
                          type="button"
                          onClick={() => onReceive(order)}
                          title="Recepcionar mercadería"
                          data-testid={`compra-receive-btn-${order.numero_orden}`}
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-emerald-600 transition-all hover:bg-emerald-500/10 dark:text-emerald-400 active:scale-95 cursor-pointer"
                        >
                          <PackageCheck className="h-4 w-4" />
                        </button>
                      )}

                      {/* Incidencia */}
                      <button
                        type="button"
                        onClick={() => onIncidence(order)}
                        title="Registrar incidencia"
                        data-testid={`compra-incidence-btn-${order.numero_orden}`}
                        className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-amber-600 transition-all hover:bg-amber-500/10 dark:text-amber-400 active:scale-95 cursor-pointer"
                      >
                        <AlertTriangle className="h-4 w-4" />
                      </button>

                      {/* Cancelar */}
                      {canCancel && (
                        <button
                          type="button"
                          onClick={() => onCancel(order)}
                          title="Cancelar orden"
                          data-testid={`compra-cancel-btn-${order.numero_orden}`}
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-rose-600 transition-all hover:bg-rose-500/10 dark:text-rose-400 active:scale-95 cursor-pointer"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
