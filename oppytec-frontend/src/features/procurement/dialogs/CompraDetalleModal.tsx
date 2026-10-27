/**
 * oppytec-frontend/src/features/procurement/dialogs/CompraDetalleModal.tsx
 * Modal de Inspección Integral de Órdenes de Compra, Ítems e Incidencias Registradas.
 * Visualización de metadata operativa, trazabilidad de recepciones y desglose fiscal.
 */

import { useState } from "react";
import { Building2, Calendar, Warehouse, Package, AlertTriangle, ShieldCheck, CheckCircle2 } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { useCurrencyFormatter } from "@/shared/currency";
import type { CompraOrder } from "../types";
import { getEstadoBadgeConfig, formatDateSafe } from "../components/CompraTable";

export interface CompraDetalleModalProps {
  readonly open: boolean;
  readonly order: CompraOrder | null;
  readonly onClose: () => void;
}

export function CompraDetalleModal({
  open,
  order,
  onClose,
}: CompraDetalleModalProps) {
  const isMobile = useIsMobile();
  const { format } = useCurrencyFormatter();
  const [activeTab, setActiveTab] = useState<"items" | "incidencias">("items");

  if (!order) return null;

  const badge = getEstadoBadgeConfig(order.estado);
  const incidencias = order.incidencias ?? [];

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={`Orden de Compra: ${order.numero_orden || order.po_number}`}
      description="Inspección detallada de materias primas, recepción e historial de disputas"
      isMobile={isMobile}
      maxWidth="max-w-3xl"
    >
      <div data-testid="compra-detalle-modal" className="space-y-4 pt-2 text-xs">
        {/* Cabecera y Metadata */}
        <div className="rounded-2xl border border-border bg-card/60 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">
                Proveedor
              </span>
              <div className="flex items-center gap-1.5 text-base font-bold text-foreground">
                <Building2 className="h-4 w-4 text-primary shrink-0" />
                <span>{order.proveedor_nombre || order.supplier_name}</span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-0.5">
                Estado Actual
              </span>
              <span
                data-testid={`detalle-status-badge-${order.estado}`}
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${badge.className}`}
              >
                {badge.label}
              </span>
            </div>
          </div>

          {/* Grid de Atributos */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-muted-foreground">
            <div>
              <span className="text-[10px] font-bold uppercase block text-muted-foreground">
                Bodega Destino
              </span>
              <div className="flex items-center gap-1 text-foreground font-semibold mt-0.5">
                <Warehouse className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{order.bodega_nombre || "Bodega Central"}</span>
              </div>
            </div>

            <div>
              <span className="text-[10px] font-bold uppercase block text-muted-foreground">
                Fecha Emisión
              </span>
              <div className="flex items-center gap-1 text-foreground font-semibold mt-0.5">
                <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{formatDateSafe(order.fecha_emision)}</span>
              </div>
            </div>

            <div>
              <span className="text-[10px] font-bold uppercase block text-muted-foreground">
                Fecha Entrega Comprometida
              </span>
              <div className="flex items-center gap-1 text-foreground font-semibold mt-0.5">
                <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{formatDateSafe(order.fecha_entrega_comprometida || order.fecha_entrega_estimada)}</span>
              </div>
            </div>
          </div>

          {order.fecha_recepcion_real && (
            <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 px-3 py-1.5 text-emerald-700 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-4 w-4" />
              <span>Recepcionada en bodega el: {formatDateSafe(order.fecha_recepcion_real)}</span>
            </div>
          )}

          {order.notas && (
            <div className="rounded-xl border border-border bg-background p-2.5 text-muted-foreground">
              <strong className="text-foreground">Notas:</strong> {order.notas}
            </div>
          )}
        </div>

        {/* Pestañas de Navegación Interna */}
        <div className="flex items-center gap-2 border-b border-border pb-2">
          <button
            type="button"
            onClick={() => setActiveTab("items")}
            data-testid="detalle-tab-items"
            className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition-all cursor-pointer ${
              activeTab === "items"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary text-secondary-foreground hover:bg-muted"
            }`}
          >
            <Package className="h-4 w-4" />
            <span>Ítems ({order.items?.length ?? 0})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("incidencias")}
            data-testid="detalle-tab-incidencias"
            className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition-all cursor-pointer ${
              activeTab === "incidencias"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary text-secondary-foreground hover:bg-muted"
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            <span>Incidencias ({incidencias.length})</span>
          </button>
        </div>

        {/* Vista Ítems */}
        {activeTab === "items" && (
          <div className="space-y-3">
            <div className="overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-muted/40 uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-3.5 py-2.5 font-semibold">Insumo</th>
                    <th className="px-3.5 py-2.5 font-semibold">SKU / Lote</th>
                    <th className="px-3.5 py-2.5 text-center font-semibold">Solicitado</th>
                    <th className="px-3.5 py-2.5 text-center font-semibold">Recibido</th>
                    <th className="px-3.5 py-2.5 text-right font-semibold">Costo Neto</th>
                    <th className="px-3.5 py-2.5 text-right font-semibold">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {order.items?.map((item, idx) => (
                    <tr key={item.id ?? idx} className="hover:bg-muted/20">
                      <td className="px-3.5 py-2.5 font-semibold text-foreground">
                        {item.producto_nombre}
                      </td>
                      <td className="px-3.5 py-2.5 font-mono text-[11px] text-muted-foreground">
                        <div>{item.producto_sku || "—"}</div>
                        {item.lote_codigo && (
                          <div className="text-[10px] text-primary">Lote: {item.lote_codigo}</div>
                        )}
                      </td>
                      <td className="px-3.5 py-2.5 text-center font-bold text-foreground">
                        {item.cantidad_solicitada}
                      </td>
                      <td className="px-3.5 py-2.5 text-center font-bold text-emerald-600 dark:text-emerald-400">
                        {item.cantidad_recibida}
                      </td>
                      <td className="px-3.5 py-2.5 text-right font-mono text-muted-foreground">
                        {format(item.costo_unitario_neto)}
                      </td>
                      <td className="px-3.5 py-2.5 text-right font-mono font-bold text-foreground">
                        {format(item.subtotal_linea)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Resumen Financiero */}
            <div className="flex justify-end">
              <div className="w-full sm:w-64 space-y-1.5 rounded-xl border border-border bg-secondary/20 p-3 text-xs">
                <div className="flex justify-between text-muted-foreground">
                  <span>Monto Neto:</span>
                  <span className="font-bold text-foreground">{format(order.monto_neto)}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>IVA (19%):</span>
                  <span className="font-bold text-foreground">{format(order.monto_impuestos)}</span>
                </div>
                <div className="flex justify-between border-t border-border pt-1.5 text-sm font-black text-foreground">
                  <span>Total Orden:</span>
                  <span className="text-primary">{format(order.monto_total)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Vista Incidencias */}
        {activeTab === "incidencias" && (
          <div className="space-y-3">
            {incidencias.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-6 text-center text-muted-foreground">
                <ShieldCheck className="h-8 w-8 text-emerald-500 mb-2" />
                <p className="font-semibold text-foreground">Sin incidencias registradas</p>
                <p className="text-[11px] mt-0.5">
                  Esta orden no presenta discrepancias ni disputas de entrega.
                </p>
              </div>
            ) : (
              incidencias.map((inc) => (
                <div
                  key={inc.id}
                  data-testid={`incidencia-item-${inc.id}`}
                  className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-700 dark:text-amber-400">
                      {inc.tipo_incidencia}
                    </span>
                    <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-600 dark:text-amber-400">
                      Resolución: {inc.resolucion}
                    </span>
                  </div>
                  <p className="text-foreground">{inc.descripcion}</p>
                  <div className="flex items-center gap-4 text-[11px] text-muted-foreground border-t border-amber-500/20 pt-1.5">
                    <span>Cant. afectada: <strong>{inc.cantidad_afectada}</strong></span>
                    {inc.monto_disputa && (
                      <span>Monto en disputa: <strong>{format(inc.monto_disputa)}</strong></span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end border-t border-border pt-3">
          <button
            type="button"
            onClick={onClose}
            data-testid="compra-detalle-close-btn"
            className="touch-target inline-flex min-h-[44px] min-w-[80px] items-center justify-center rounded-xl bg-secondary px-4 py-2 text-xs font-semibold text-secondary-foreground hover:bg-muted active:scale-95 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
