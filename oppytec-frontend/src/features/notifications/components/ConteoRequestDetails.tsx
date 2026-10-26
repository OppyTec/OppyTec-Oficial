import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { cn, formatMoney } from "@/shared/lib/utils";
import type { Solicitud } from "../types";

export interface ConteoItemDetail {
  id: string | number;
  producto_id: number;
  producto_nombre: string;
  codigo_barra?: string;
  unidad?: string;
  lote_codigo?: string;
  vencimiento?: string | null;
  stock_teorico: number;
  stock_fisico: number;
  costo_unitario_ppp: number;
  observaciones?: string | null;
}

export interface ConteoRequestDetailsProps {
  readonly open?: boolean;
  readonly onClose?: () => void;
  readonly solicitud: Solicitud | null;
  readonly onApprove?: (id: string) => void | Promise<any>;
  readonly onReject?: (id: string, reason: string) => void | Promise<any>;
  readonly isApproving?: boolean;
  readonly isRejecting?: boolean;
  readonly embedded?: boolean;
}

export function formatDeltaMoney(delta: number): string {
  if (delta === 0) return "$0";
  const sign = delta > 0 ? "+" : "-";
  return `${sign}${formatMoney(Math.abs(delta))}`;
}

export function ConteoRequestDetails({
  open = true,
  onClose,
  solicitud,
  onApprove,
  onReject,
  isApproving = false,
  isRejecting = false,
  embedded = false,
}: ConteoRequestDetailsProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [items, setItems] = useState<ConteoItemDetail[]>([]);
  const [toleranceThresholdClp] = useState<number>(5000); // Umbral de tolerancia de discrepancia financiera
  const [showRejectInput, setShowRejectInput] = useState<boolean>(false);
  const [rejectReason, setRejectReason] = useState<string>("");

  useEffect(() => {
    if (!solicitud) {
      setItems([]);
      return;
    }

    const actaId =
      solicitud.detalles?.acta_conteo_id ||
      solicitud.detalles?.acta_id ||
      solicitud.id;

    void loadConteoDetail(actaId);
  }, [solicitud]);

  const loadConteoDetail = async (actaId: string | number) => {
    setLoading(true);

    const mockFallbackItems: ConteoItemDetail[] = [
      {
        id: "item-cnt-1",
        producto_id: 201,
        producto_nombre: "Carne Vacuno Lomo Vetado",
        codigo_barra: "780123456001",
        unidad: "kg",
        lote_codigo: "LOTE-2026-A1",
        vencimiento: "2026-11-15",
        stock_teorico: 15.0,
        stock_fisico: 13.5,
        costo_unitario_ppp: 14500,
        observaciones: "Diferencia detectada en cámara frigorífica",
      },
      {
        id: "item-cnt-2",
        producto_id: 202,
        producto_nombre: "Salmón Atlántico Fresco",
        codigo_barra: "780123456002",
        unidad: "kg",
        lote_codigo: "LOTE-2026-S2",
        vencimiento: "2026-11-05",
        stock_teorico: 8.0,
        stock_fisico: 8.0,
        costo_unitario_ppp: 12000,
        observaciones: "Stock cuadrado con Kardex",
      },
      {
        id: "item-cnt-3",
        producto_id: 203,
        producto_nombre: "Aceite de Oliva Extra Virgen 5L",
        codigo_barra: "780123456003",
        unidad: "bidon",
        lote_codigo: "LOTE-2026-O3",
        vencimiento: "2027-02-28",
        stock_teorico: 6.0,
        stock_fisico: 7.0,
        costo_unitario_ppp: 28000,
        observaciones: "Un bidón extra encontrado en pasillo B",
      },
      {
        id: "item-cnt-4",
        producto_id: 204,
        producto_nombre: "Pechuga de Pollo Deshuesada",
        codigo_barra: "780123456004",
        unidad: "kg",
        lote_codigo: "LOTE-2026-P4",
        vencimiento: "2026-10-31",
        stock_teorico: 20.0,
        stock_fisico: 20.0,
        costo_unitario_ppp: 4500,
        observaciones: "Stock exacto",
      },
    ];

    try {
      const res = await apiRequest<any>(`/api/v1/inventory/counts/${actaId}`, {
        method: "GET",
        fallbackData: { items: mockFallbackItems },
      });

      const loadedItems = res.data?.items || res.data?.detalles?.items;
      if (Array.isArray(loadedItems) && loadedItems.length > 0) {
        setItems(
          loadedItems.map((it: any) => ({
            id: it.id || Math.random().toString(),
            producto_id: it.producto_id || 0,
            producto_nombre: it.producto_nombre || it.nombre || "Insumo",
            codigo_barra: it.codigo_barra,
            unidad: it.unidad || "un",
            lote_codigo: it.lote_codigo,
            vencimiento: it.vencimiento,
            stock_teorico: Number(it.stock_teorico ?? it.teorico ?? 0),
            stock_fisico: Number(it.stock_fisico ?? it.fisico ?? 0),
            costo_unitario_ppp: Number(it.costo_unitario_ppp ?? it.costo_unitario ?? it.ppp ?? 0),
            observaciones: it.observaciones,
          }))
        );
      } else {
        setItems(mockFallbackItems);
      }
    } catch {
      setItems(mockFallbackItems);
    } finally {
      setLoading(false);
    }
  };

  // Cálculos de discrepancias globales
  const summary = useMemo(() => {
    let totalItems = items.length;
    let itemsWithDiscrepancy = 0;
    let totalDeltaUnits = 0;
    let totalDeltaMonetario = 0;
    let maxAbsoluteDiscrepancyClp = 0;

    items.forEach((it) => {
      const deltaQty = it.stock_fisico - it.stock_teorico;
      const deltaClp = deltaQty * it.costo_unitario_ppp;
      if (Math.abs(deltaQty) > 0.001) {
        itemsWithDiscrepancy += 1;
      }
      totalDeltaUnits += deltaQty;
      totalDeltaMonetario += deltaClp;
      if (Math.abs(deltaClp) > maxAbsoluteDiscrepancyClp) {
        maxAbsoluteDiscrepancyClp = Math.abs(deltaClp);
      }
    });

    // Severidad:
    // Verde: itemsWithDiscrepancy === 0
    // Ámbar: discrepancias menores (<= toleranceThresholdClp)
    // Rojo: supera tolerancia (> toleranceThresholdClp)
    let severity: "green" | "amber" | "red" = "green";
    if (itemsWithDiscrepancy > 0) {
      if (
        Math.abs(totalDeltaMonetario) > toleranceThresholdClp ||
        maxAbsoluteDiscrepancyClp > toleranceThresholdClp
      ) {
        severity = "red";
      } else {
        severity = "amber";
      }
    }

    return {
      totalItems,
      itemsWithDiscrepancy,
      totalDeltaUnits,
      totalDeltaMonetario,
      severity,
    };
  }, [items, toleranceThresholdClp]);

  const handleConfirmReject = async () => {
    if (!solicitud) return;
    if (!rejectReason.trim() || rejectReason.trim().length < 5) {
      toast.error("El motivo de rechazo debe tener al menos 5 caracteres");
      return;
    }
    await onReject?.(solicitud.id, rejectReason.trim());
    setShowRejectInput(false);
    onClose?.();
  };

  const handleConfirmApprove = async () => {
    if (!solicitud) return;
    await onApprove?.(solicitud.id);
    onClose?.();
  };

  if (!open && !embedded) return null;

  const content = (
    <div
      data-testid="conteo-request-details"
      className={cn(
        "space-y-4 text-foreground",
        embedded ? "p-3 rounded-2xl bg-card border border-border/80" : ""
      )}
    >
      {/* Cabecera y Badges de Severidad */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/60">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
            <ClipboardCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-black text-foreground">
                Auditoría de Conteo Físico #{solicitud?.detalles?.acta_conteo_id || solicitud?.id}
              </h3>
              {summary.severity === "green" && (
                <span
                  data-testid="badge-severity-green"
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 inline-flex items-center gap-1"
                >
                  <CheckCircle2 className="w-3 h-3" /> Sin Discrepancias
                </span>
              )}
              {summary.severity === "amber" && (
                <span
                  data-testid="badge-severity-amber"
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-500 border border-amber-500/30 inline-flex items-center gap-1"
                >
                  <AlertCircle className="w-3 h-3" /> Discrepancia Menor
                </span>
              )}
              {summary.severity === "red" && (
                <span
                  data-testid="badge-severity-red"
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/15 text-rose-500 border border-rose-500/30 inline-flex items-center gap-1 animate-pulse"
                >
                  <AlertTriangle className="w-3 h-3" /> Supera Tolerancia
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Comparativa del Kardex teórico al momento del corte vs el stock contado por el operador.
            </p>
          </div>
        </div>

        {/* Resumen KPI */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="px-3 py-1.5 rounded-xl bg-muted/60 border border-border/60 text-right">
            <span className="text-[10px] uppercase font-bold text-muted-foreground block">
              Diferencia Financiera
            </span>
            <span
              data-testid="delta-monetario-total"
              className={cn(
                "text-xs font-mono font-black",
                summary.totalDeltaMonetario > 0
                  ? "text-emerald-500"
                  : summary.totalDeltaMonetario < 0
                    ? "text-rose-500"
                    : "text-foreground"
              )}
            >
              {formatDeltaMoney(summary.totalDeltaMonetario)}
            </span>
          </div>
        </div>
      </div>

      {/* Tabla Comparativa Multidimensional */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
          <span className="text-xs text-muted-foreground">Cargando ítems del conteo...</span>
        </div>
      ) : (
        <div className="border border-border/60 rounded-2xl overflow-hidden shadow-xs">
          <table className="w-full text-xs" data-testid="conteo-table">
            <thead className="bg-muted/50 border-b border-border/50 text-[10px] font-black uppercase text-muted-foreground select-none">
              <tr>
                <th className="py-2.5 px-3 text-left">Insumo / Lote</th>
                <th className="py-2.5 px-2 text-center">Stock Kardex (Teórico)</th>
                <th className="py-2.5 px-2 text-center">Stock Físico (Contado)</th>
                <th className="py-2.5 px-2 text-center">Discrepancia (Δ)</th>
                <th className="py-2.5 px-2 text-center">Costo PPP</th>
                <th className="py-2.5 px-3 text-right">Impacto Financiero (Δ × PPP)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {items.map((it, idx) => {
                const deltaQty = it.stock_fisico - it.stock_teorico;
                const deltaMoney = deltaQty * it.costo_unitario_ppp;
                const hasDiff = Math.abs(deltaQty) > 0.001;

                return (
                  <tr
                    key={it.id || idx}
                    data-testid={`conteo-row-${idx}`}
                    className={cn(
                      "hover:bg-muted/20 transition-colors",
                      hasDiff
                        ? deltaMoney < 0
                          ? "bg-rose-500/5"
                          : "bg-emerald-500/5"
                        : ""
                    )}
                  >
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-foreground">{it.producto_nombre}</div>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-0.5">
                        {it.lote_codigo && (
                          <span className="font-mono bg-muted px-1.5 py-0.2 rounded">
                            Lote: {it.lote_codigo}
                          </span>
                        )}
                        {it.vencimiento && <span>Vence: {it.vencimiento}</span>}
                      </div>
                    </td>

                    {/* Stock Teórico */}
                    <td className="py-2.5 px-2 text-center font-mono font-medium text-muted-foreground">
                      {it.stock_teorico} {it.unidad}
                    </td>

                    {/* Stock Físico */}
                    <td className="py-2.5 px-2 text-center font-mono font-bold text-foreground">
                      {it.stock_fisico} {it.unidad}
                    </td>

                    {/* Discrepancia en Unidades */}
                    <td className="py-2.5 px-2 text-center font-mono">
                      <span
                        data-testid={`delta-units-${idx}`}
                        className={cn(
                          "px-2 py-0.5 rounded-lg text-xs font-black inline-flex items-center gap-1",
                          deltaQty === 0
                            ? "bg-muted text-muted-foreground"
                            : deltaQty > 0
                              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                              : "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                        )}
                      >
                        {deltaQty > 0 ? "+" : ""}
                        {deltaQty} {it.unidad}
                      </span>
                    </td>

                    {/* Costo PPP */}
                    <td className="py-2.5 px-2 text-center font-mono text-[11px] text-muted-foreground">
                      {formatMoney(it.costo_unitario_ppp)}
                    </td>

                    {/* Impacto Financiero Delta */}
                    <td className="py-2.5 px-3 text-right font-mono">
                      <span
                        data-testid={`delta-clp-${idx}`}
                        className={cn(
                          "font-black text-xs",
                          deltaMoney === 0
                            ? "text-muted-foreground"
                            : deltaMoney > 0
                              ? "text-emerald-500"
                              : "text-rose-500"
                        )}
                      >
                        {formatDeltaMoney(deltaMoney)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Observaciones de solicitud */}
      {solicitud?.detalles?.observaciones && (
        <div className="p-3 rounded-xl bg-muted/40 border border-border/50 text-xs">
          <strong className="text-foreground">Observaciones del emisor:</strong>{" "}
          <span className="text-muted-foreground">{solicitud.detalles.observaciones}</span>
        </div>
      )}

      {/* Subpanel de Rechazo */}
      {showRejectInput && (
        <div
          data-testid="conteo-reject-panel"
          className="p-3 rounded-2xl bg-destructive/10 border border-destructive/20 space-y-2 animate-in fade-in"
        >
          <div className="flex items-center justify-between text-xs font-black uppercase text-destructive tracking-wider">
            <span className="flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" /> Motivo del Rechazo del Acta
            </span>
            <button
              type="button"
              onClick={() => setShowRejectInput(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <textarea
            rows={2}
            data-testid="conteo-reject-reason-input"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Ingresa la justificación (mínimo 5 caracteres)..."
            className="w-full p-2 rounded-xl bg-background border border-destructive/30 text-xs font-medium text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-destructive"
          />
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowRejectInput(false)}
              className="px-3 py-1.5 rounded-xl border border-input text-xs font-bold text-muted-foreground"
            >
              Cancelar
            </button>
            <button
              type="button"
              data-testid="conteo-confirm-reject-btn"
              onClick={handleConfirmReject}
              disabled={isRejecting}
              className="px-3.5 py-1.5 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground text-xs font-black uppercase tracking-wider"
            >
              {isRejecting ? "Rechazando..." : "Confirmar Rechazo"}
            </button>
          </div>
        </div>
      )}

      {/* Botones de Acción */}
      {!embedded && (
        <div className="pt-3 border-t border-border/60 flex items-center justify-between gap-3">
          <button
            type="button"
            data-testid="conteo-close-btn"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-input bg-background hover:bg-muted text-xs font-bold text-muted-foreground cursor-pointer"
          >
            Cerrar
          </button>

          {!showRejectInput && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="conteo-open-reject-btn"
                onClick={() => setShowRejectInput(true)}
                disabled={isRejecting || isApproving}
                className="px-3.5 py-2 rounded-xl border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 text-xs font-black uppercase tracking-wider inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <XCircle className="w-4 h-4" />
                <span>Rechazar Acta</span>
              </button>

              <button
                type="button"
                data-testid="conteo-approve-btn"
                onClick={handleConfirmApprove}
                disabled={isApproving || isRejecting}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-black uppercase tracking-widest inline-flex items-center gap-1.5 shadow-md shadow-emerald-950/20 cursor-pointer disabled:opacity-50 active:scale-95 transition-all"
              >
                {isApproving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4" />
                )}
                <span>Aprobar y Ajustar Kardex</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );

  if (embedded) {
    return content;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Inspector de Conteo Físico"
      data-testid="conteo-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-2 sm:p-4 overflow-y-auto"
    >
      <div className="glass-card w-full max-w-4xl rounded-3xl border border-border/80 bg-background/95 p-4 sm:p-6 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden my-auto animate-in fade-in zoom-in-95">
        <div className="flex-1 overflow-y-auto min-h-0 pr-1">{content}</div>
      </div>
    </div>
  );
}

export default ConteoRequestDetails;
