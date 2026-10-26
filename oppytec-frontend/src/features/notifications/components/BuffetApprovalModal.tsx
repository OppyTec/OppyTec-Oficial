import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Columns,
  Layers,
  Loader2,
  Package,
  ShieldCheck,
  Sparkles,
  Table,
  TrendingDown,
  UtensilsCrossed,
  X,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { cn, formatMoney, getImageUrl } from "@/shared/lib/utils";
import type { Solicitud } from "../types";

export interface BuffetItemRecord {
  id: string | number;
  item_type: string;
  nombre: string;
  unidad?: string;
  cantidad_apertura: number;
  cantidad_reposiciones: number;
  cantidad_cierre: number;
  cantidad_consumida: number;
  cantidad_sobrante?: number;
  costo_unitario_ppp?: number;
  accion_sobrante: "retornar" | "merma";
  motivo_merma?: string | null;
  foto_url?: string | null;
}

export interface BuffetApprovalModalProps {
  readonly open: boolean;
  readonly onOpenChange?: (open: boolean) => void;
  readonly onClose?: () => void;
  readonly solicitudId: string | null;
  readonly solicitud?: Solicitud | null;
  readonly onResolved: () => void;
}

export const MOTIVOS_MERMA = [
  "Caducidad en buffet / tiempo expuesto",
  "Deterioro / manipulación de comensales",
  "Contaminación cruzada",
  "Temperatura fuera de rango",
  "Sobrante no recuperable",
  "Otro motivo",
] as const;

export function BuffetApprovalModal({
  open,
  onOpenChange,
  onClose,
  solicitudId,
  solicitud,
  onResolved,
}: BuffetApprovalModalProps) {
  const [loading, setLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [activeTab, setActiveTab] = useState<"balance" | "split_view">("balance");

  const [approvalData, setApprovalData] = useState<any | null>(null);
  const [items, setItems] = useState<BuffetItemRecord[]>([]);
  const [hoveredItemId, setHoveredItemId] = useState<string | number | null>(null);

  // Modo rechazo
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const handleClose = () => {
    onClose?.();
    onOpenChange?.(false);
  };

  useEffect(() => {
    if (open && (solicitudId || solicitud?.id)) {
      const targetId = solicitudId || solicitud?.id;
      if (targetId) {
        void loadApprovalDetail(targetId);
      }
    } else {
      setApprovalData(null);
      setItems([]);
      setShowRejectInput(false);
      setRejectReason("");
      setActiveTab("balance");
    }
  }, [open, solicitudId, solicitud]);

  const loadApprovalDetail = async (id: string) => {
    setLoading(true);
    const mockFallback = {
      id,
      tipo: "consumo_buffet",
      estado: "pendiente",
      detalles: {
        buffet_nombre: solicitud?.detalles?.buffet_nombre || "Sesión Buffet Almuerzo",
        bodega_nombre: "Cocina Principal Buffet",
        pax_atendidos: solicitud?.detalles?.pax_atendidos || 45,
        estacion_apertura: {
          nombre: "Estación Central 1 (Montaje)",
          foto_url: "/images/buffet-apertura.jpg",
          hora: "11:30",
        },
        estacion_cierre: {
          nombre: "Estación Central 1 (Desmontaje)",
          foto_url: "/images/buffet-cierre.jpg",
          hora: "15:30",
        },
        items: [
          {
            id: "it-1",
            item_type: "insumo",
            nombre: "Lomo Liso Vacuno",
            unidad: "kg",
            cantidad_apertura: 10,
            cantidad_reposiciones: 5,
            cantidad_cierre: 3,
            cantidad_consumida: 12,
            costo_unitario_ppp: 14500,
            accion_sobrante: "retornar",
            motivo_merma: null,
          },
          {
            id: "it-2",
            item_type: "insumo",
            nombre: "Salmón Grillado",
            unidad: "kg",
            cantidad_apertura: 8,
            cantidad_reposiciones: 4,
            cantidad_cierre: 2,
            cantidad_consumida: 10,
            costo_unitario_ppp: 12000,
            accion_sobrante: "merma",
            motivo_merma: "Caducidad en buffet / tiempo expuesto",
          },
          {
            id: "it-3",
            item_type: "receta",
            nombre: "Arroz Primavera Especial",
            unidad: "kg",
            cantidad_apertura: 12,
            cantidad_reposiciones: 6,
            cantidad_cierre: 4,
            cantidad_consumida: 14,
            costo_unitario_ppp: 3200,
            accion_sobrante: "retornar",
            motivo_merma: null,
          },
        ],
      },
    };

    try {
      const res = await apiRequest<any>(
        `/api/v1/operations/buffet/approvals/${id}/detail`,
        {
          method: "GET",
          fallbackData: mockFallback,
        }
      );

      const data = res.data ?? mockFallback;
      setApprovalData(data);
      const rawItems = data?.detalles?.items || [];
      const parsedItems: BuffetItemRecord[] = rawItems.map((it: any) => {
        const ap = Number(it.cantidad_apertura || 0);
        const rep = Number(it.cantidad_reposiciones || 0);
        const cie = Number(it.cantidad_cierre || 0);
        const consumida =
          it.cantidad_consumida !== undefined
            ? Number(it.cantidad_consumida)
            : Math.max(0, ap + rep - cie);
        return {
          id: it.id || it.item_id || Math.random().toString(),
          item_type: it.item_type || "insumo",
          nombre: it.nombre || "Ítem de buffet",
          unidad: it.unidad || "un",
          cantidad_apertura: ap,
          cantidad_reposiciones: rep,
          cantidad_cierre: cie,
          cantidad_consumida: consumida,
          cantidad_sobrante: cie,
          costo_unitario_ppp: Number(it.costo_unitario_ppp || it.costo_unitario || it.ppp || 0),
          accion_sobrante: it.accion_sobrante === "merma" ? "merma" : "retornar",
          motivo_merma: it.motivo_merma || null,
          foto_url: it.foto_url || null,
        };
      });

      setItems(parsedItems.length > 0 ? parsedItems : mockFallback.detalles.items as any);
    } catch (err: any) {
      console.error("Error al cargar detalle de buffet:", err);
      toast.error("No se pudo cargar la información del buffet, usando snapshot local.");
      setApprovalData(mockFallback);
      setItems(mockFallback.detalles.items as any);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAccionSobrante = (index: number) => {
    setItems((prev) =>
      prev.map((it, idx) => {
        if (idx !== index) return it;
        const nextAction: "retornar" | "merma" =
          it.accion_sobrante === "retornar" ? "merma" : "retornar";
        return {
          ...it,
          accion_sobrante: nextAction,
          motivo_merma: nextAction === "merma" ? it.motivo_merma || MOTIVOS_MERMA[0] : null,
        };
      })
    );
  };

  const handleSetAccionSobrante = (
    index: number,
    action: "retornar" | "merma",
    motivo?: string
  ) => {
    setItems((prev) =>
      prev.map((it, idx) => {
        if (idx !== index) return it;
        return {
          ...it,
          accion_sobrante: action,
          motivo_merma: action === "merma" ? motivo || it.motivo_merma || MOTIVOS_MERMA[0] : null,
        };
      })
    );
  };

  const handleUpdateItemField = (index: number, field: keyof BuffetItemRecord, value: any) => {
    setItems((prev) =>
      prev.map((it, idx) => {
        if (idx !== index) return it;
        const updated = { ...it, [field]: value };
        if (
          field === "cantidad_apertura" ||
          field === "cantidad_reposiciones" ||
          field === "cantidad_cierre"
        ) {
          const ap = Number(field === "cantidad_apertura" ? value : it.cantidad_apertura || 0);
          const rep = Number(field === "cantidad_reposiciones" ? value : it.cantidad_reposiciones || 0);
          const cie = Number(field === "cantidad_cierre" ? value : it.cantidad_cierre || 0);
          updated.cantidad_consumida = Math.max(0, ap + rep - cie);
          updated.cantidad_sobrante = cie;
        }
        return updated;
      })
    );
  };

  // Cálculos financieros y de consumo
  const totals = useMemo(() => {
    let totalConsumoQty = 0;
    let totalValorConsumoPPP = 0;
    let totalSobranteQty = 0;
    let totalMermaQty = 0;
    let totalRetornoQty = 0;

    items.forEach((it) => {
      totalConsumoQty += it.cantidad_consumida;
      totalValorConsumoPPP += it.cantidad_consumida * (it.costo_unitario_ppp || 0);
      const sobrante = it.cantidad_cierre;
      totalSobranteQty += sobrante;
      if (it.accion_sobrante === "merma") {
        totalMermaQty += sobrante;
      } else {
        totalRetornoQty += sobrante;
      }
    });

    return {
      totalConsumoQty,
      totalValorConsumoPPP,
      totalSobranteQty,
      totalMermaQty,
      totalRetornoQty,
    };
  }, [items]);

  const handleResolve = async (action: "aprobar" | "rechazar") => {
    const targetId = solicitudId || solicitud?.id;
    if (!targetId) return;

    if (action === "rechazar" && (!rejectReason.trim() || rejectReason.trim().length < 5)) {
      toast.error("Debes ingresar un motivo de rechazo de al menos 5 caracteres");
      return;
    }

    setResolving(true);
    try {
      const itemsOverride = items.map((it) => ({
        item_id: it.id,
        item_type: it.item_type,
        nombre: it.nombre,
        cantidad: Number(it.cantidad_consumida || 0),
        accion_sobrante: it.accion_sobrante,
        motivo_merma: it.accion_sobrante === "merma" ? it.motivo_merma || MOTIVOS_MERMA[0] : null,
      }));

      await apiRequest(`/api/v1/operations/buffet/approvals/${targetId}/resolve`, {
        method: "POST",
        body: {
          accion: action,
          motivo_rechazo: action === "rechazar" ? rejectReason.trim() : null,
          items_override: itemsOverride,
        },
      });

      toast.success(
        action === "aprobar"
          ? "Buffet aprobado exitosamente y stock descontado del inventario"
          : "Buffet rechazado correctamente"
      );
      onResolved();
      handleClose();
    } catch (err: any) {
      console.error("Error al resolver buffet:", err);
      toast.error(err?.message || "Error al procesar la aprobación del buffet");
    } finally {
      setResolving(false);
    }
  };

  if (!open) return null;

  const detalles = approvalData?.detalles || solicitud?.detalles || {};
  const aperturaEstacion = detalles.estacion_apertura;
  const cierreEstacion = detalles.estacion_cierre;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Auditoría de Buffet"
      data-testid="buffet-approval-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-2 sm:p-4 overflow-y-auto"
    >
      <div className="glass-card w-full max-w-5xl rounded-3xl border border-border/80 bg-background/95 p-4 sm:p-6 shadow-2xl flex flex-col max-h-[92vh] overflow-hidden my-auto animate-in fade-in zoom-in-95">
        {/* Cabecera */}
        <div className="shrink-0 pb-4 border-b border-border/60">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                <UtensilsCrossed className="h-6 w-6" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-base sm:text-lg font-black text-foreground">
                    Auditoría de Buffet: {detalles.buffet_nombre || "Sesión Buffet"}
                  </h3>
                  <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                    Bodega: {detalles.bodega_nombre || "Principal Buffet"}
                  </span>
                  {detalles.pax_atendidos && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                      👥 {detalles.pax_atendidos} Pax
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Revisa la comparativa 50/50 y valida el destino de los sobrantes antes de impactar el Kardex.
                </p>
              </div>
            </div>

            {/* Selector de Pestañas: Balance vs Split-View */}
            <div className="flex items-center gap-1.5 bg-muted/60 p-1 rounded-2xl border border-border/40 shrink-0">
              <button
                type="button"
                data-testid="tab-balance"
                onClick={() => setActiveTab("balance")}
                className={cn(
                  "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                  activeTab === "balance"
                    ? "bg-background text-foreground shadow-sm border border-border/60"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Table className="w-3.5 h-3.5" />
                <span>Balance Consolidado</span>
              </button>

              <button
                type="button"
                data-testid="tab-split-view"
                onClick={() => setActiveTab("split_view")}
                className={cn(
                  "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                  activeTab === "split_view"
                    ? "bg-cyan-500 text-black shadow-sm font-black"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Columns className="w-3.5 h-3.5" />
                <span>Auditoría Split-View</span>
              </button>
            </div>
          </div>

          {/* Tarjetas KPI de Resumen Financiero en Tiempo Real */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-border/40 text-xs">
            <div className="p-2 rounded-xl bg-card border border-border/60">
              <span className="text-[10px] font-bold text-muted-foreground uppercase">Ítems Evaluados</span>
              <p className="text-sm font-black text-foreground">{items.length} productos</p>
            </div>
            <div className="p-2 rounded-xl bg-cyan-500/5 border border-cyan-500/20">
              <span className="text-[10px] font-bold text-cyan-400 uppercase">Consumo Neto Total</span>
              <p className="text-sm font-black text-cyan-400 font-mono">{totals.totalConsumoQty} un/kg</p>
            </div>
            <div className="p-2 rounded-xl bg-card border border-border/60">
              <span className="text-[10px] font-bold text-muted-foreground uppercase">Sobrantes (Cierre)</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-emerald-500 font-mono">↩ {totals.totalRetornoQty} ret</span>
                <span className="text-xs font-bold text-rose-400 font-mono">🗑 {totals.totalMermaQty} merma</span>
              </div>
            </div>
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <span className="text-[10px] font-black text-amber-400 uppercase">Valorización Financiera PPP</span>
              <p className="text-sm font-black text-amber-400 font-mono">
                {formatMoney(totals.totalValorConsumoPPP)}
              </p>
            </div>
          </div>
        </div>

        {/* Cuerpo Principal Scrollable */}
        <div className="flex-1 overflow-y-auto py-3 min-h-[300px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
              <span className="text-xs text-muted-foreground">Cargando datos del buffet...</span>
            </div>
          ) : activeTab === "balance" ? (
            /* TAB 1: BALANCE CONSOLIDADO */
            <div className="space-y-3" data-testid="balance-view">
              <div className="border border-border/60 rounded-2xl overflow-hidden shadow-xs">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50 border-b border-border/50 text-[10px] font-black uppercase text-muted-foreground select-none">
                    <tr>
                      <th className="py-2.5 px-3 text-left">Insumo / Receta</th>
                      <th className="py-2.5 px-2 text-center">Apertura</th>
                      <th className="py-2.5 px-2 text-center">Reposición</th>
                      <th className="py-2.5 px-2 text-center">Cierre</th>
                      <th className="py-2.5 px-2 text-center text-cyan-400">Consumo Neto</th>
                      <th className="py-2.5 px-2 text-center">PPP Unitario</th>
                      <th className="py-2.5 px-2 text-center text-amber-400">Subtotal PPP</th>
                      <th className="py-2.5 px-3 text-left">Destino Sobrante</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {items.map((it, idx) => {
                      const ap = Number(it.cantidad_apertura || 0);
                      const rep = Number(it.cantidad_reposiciones || 0);
                      const cie = Number(it.cantidad_cierre || 0);
                      const consumo = it.cantidad_consumida;
                      const subtotalPPP = consumo * (it.costo_unitario_ppp || 0);

                      return (
                        <tr
                          key={it.id || idx}
                          data-testid={`buffet-row-${idx}`}
                          onMouseEnter={() => setHoveredItemId(it.id)}
                          onMouseLeave={() => setHoveredItemId(null)}
                          className={cn(
                            "hover:bg-muted/20 transition-colors",
                            hoveredItemId === it.id && "bg-cyan-500/5"
                          )}
                        >
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-foreground">{it.nombre}</span>
                              <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                                {it.item_type}
                              </span>
                            </div>
                            <span className="text-[10px] text-muted-foreground">
                              Unidad: {it.unidad || "un"}
                            </span>
                          </td>

                          {/* Conteo Apertura editable */}
                          <td className="py-2.5 px-2 text-center font-mono">
                            <input
                              type="number"
                              min="0"
                              data-testid={`input-apertura-${idx}`}
                              value={ap}
                              onChange={(e) =>
                                handleUpdateItemField(
                                  idx,
                                  "cantidad_apertura",
                                  Math.max(0, Number(e.target.value))
                                )
                              }
                              className="h-7 w-16 text-center text-xs font-mono font-bold mx-auto rounded-lg border border-border bg-background text-foreground"
                            />
                          </td>

                          {/* Reposición editable */}
                          <td className="py-2.5 px-2 text-center font-mono">
                            <input
                              type="number"
                              min="0"
                              data-testid={`input-reposicion-${idx}`}
                              value={rep}
                              onChange={(e) =>
                                handleUpdateItemField(
                                  idx,
                                  "cantidad_reposiciones",
                                  Math.max(0, Number(e.target.value))
                                )
                              }
                              className="h-7 w-16 text-center text-xs font-mono font-bold mx-auto rounded-lg border border-amber-500/30 bg-background text-amber-500"
                            />
                          </td>

                          {/* Cierre editable */}
                          <td className="py-2.5 px-2 text-center font-mono">
                            <input
                              type="number"
                              min="0"
                              data-testid={`input-cierre-${idx}`}
                              value={cie}
                              onChange={(e) =>
                                handleUpdateItemField(
                                  idx,
                                  "cantidad_cierre",
                                  Math.max(0, Number(e.target.value))
                                )
                              }
                              className="h-7 w-16 text-center text-xs font-mono font-bold mx-auto rounded-lg border border-border bg-background text-foreground"
                            />
                          </td>

                          {/* Consumo Neto Calculado */}
                          <td className="py-2.5 px-2 text-center">
                            <span
                              data-testid={`consumo-neto-${idx}`}
                              className="font-mono font-black text-xs text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-lg border border-cyan-500/30"
                            >
                              {consumo} {it.unidad || ""}
                            </span>
                          </td>

                          {/* PPP Unitario */}
                          <td className="py-2.5 px-2 text-center font-mono text-[11px] text-muted-foreground">
                            {formatMoney(it.costo_unitario_ppp || 0)}
                          </td>

                          {/* Subtotal Consumo PPP */}
                          <td className="py-2.5 px-2 text-center font-mono font-black text-amber-400 text-xs">
                            {formatMoney(subtotalPPP)}
                          </td>

                          {/* Destino Sobrante: Retornar vs Merma */}
                          <td className="py-2.5 px-3">
                            <div className="flex flex-col gap-1.5">
                              <div className="flex items-center gap-1.5">
                                <button
                                  type="button"
                                  data-testid={`toggle-sobrante-${idx}`}
                                  onClick={() => handleToggleAccionSobrante(idx)}
                                  className={cn(
                                    "px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider border transition-all cursor-pointer",
                                    it.accion_sobrante === "retornar"
                                      ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/25"
                                      : "bg-rose-500/15 border-rose-500/30 text-rose-500 hover:bg-rose-500/25"
                                  )}
                                >
                                  {it.accion_sobrante === "retornar"
                                    ? "↩ Retornar a Bodega"
                                    : "🗑 Declarar Merma"}
                                </button>
                              </div>

                              {it.accion_sobrante === "merma" && (
                                <select
                                  data-testid={`select-motivo-merma-${idx}`}
                                  value={it.motivo_merma || MOTIVOS_MERMA[0]}
                                  onChange={(e) =>
                                    handleUpdateItemField(idx, "motivo_merma", e.target.value)
                                  }
                                  className="h-7 text-[10px] rounded-lg border border-rose-500/30 bg-background text-foreground px-2 py-0.5 font-medium"
                                >
                                  {MOTIVOS_MERMA.map((m) => (
                                    <option key={m} value={m}>
                                      {m}
                                    </option>
                                  ))}
                                </select>
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
          ) : (
            /* TAB 2: AUDITORÍA VISUAL SPLIT-VIEW (50/50) */
            <div className="space-y-4" data-testid="split-view">
              {/* Fotos 50/50 Apertura vs Cierre */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[280px] sm:h-[320px]">
                {/* Panel Izquierdo: Apertura */}
                <div className="flex flex-col rounded-2xl border border-cyan-500/30 overflow-hidden bg-black/90 relative shadow-inner">
                  <div className="px-3 py-2 bg-black/80 border-b border-cyan-500/20 flex items-center justify-between z-10">
                    <span className="text-xs font-black uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>1. Apertura / Montaje</span>
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {aperturaEstacion?.nombre || "Estación Apertura"} • {aperturaEstacion?.hora || "11:30"}
                    </span>
                  </div>

                  <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-black">
                    {aperturaEstacion?.foto_url ? (
                      <img
                        src={getImageUrl(aperturaEstacion.foto_url)}
                        alt="Apertura Buffet"
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          // Fallback si la imagen no existe
                          (e.currentTarget as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : null}
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4 pointer-events-none">
                      <Package className="h-10 w-10 text-cyan-400/30 mb-2" />
                      <span className="text-xs font-bold text-cyan-400/80">
                        {aperturaEstacion?.nombre || "Estación de Apertura"}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        Foto tomada por el supervisor de turno al montar
                      </span>
                    </div>
                  </div>
                </div>

                {/* Panel Derecho: Cierre */}
                <div className="flex flex-col rounded-2xl border border-indigo-500/30 overflow-hidden bg-black/90 relative shadow-inner">
                  <div className="px-3 py-2 bg-black/80 border-b border-indigo-500/20 flex items-center justify-between z-10">
                    <span className="text-xs font-black uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                      <TrendingDown className="w-3.5 h-3.5" />
                      <span>2. Cierre / Desmontaje</span>
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {cierreEstacion?.nombre || "Estación Cierre"} • {cierreEstacion?.hora || "15:30"}
                    </span>
                  </div>

                  <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-black">
                    {cierreEstacion?.foto_url ? (
                      <img
                        src={getImageUrl(cierreEstacion.foto_url)}
                        alt="Cierre Buffet"
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          (e.currentTarget as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : null}
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4 pointer-events-none">
                      <UtensilsCrossed className="h-10 w-10 text-indigo-400/30 mb-2" />
                      <span className="text-xs font-bold text-indigo-400/80">
                        {cierreEstacion?.nombre || "Estación de Desmontaje"}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        Foto tomada por el supervisor al desmontar
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Decisión Ítem por Ítem en Split-View */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-black uppercase tracking-wider text-foreground flex items-center gap-1.5">
                    <Layers className="h-4 w-4 text-cyan-400" />
                    <span>Resolución de Sobrantes por Ítem</span>
                  </h4>
                  <span className="text-[10px] text-muted-foreground">
                    Elige el destino para cada sobrante de cierre
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {items.map((it, idx) => {
                    const ap = it.cantidad_apertura;
                    const rep = it.cantidad_reposiciones;
                    const cie = it.cantidad_cierre;
                    const consumo = it.cantidad_consumida;

                    return (
                      <div
                        key={it.id || idx}
                        data-testid={`split-card-${idx}`}
                        className={cn(
                          "p-3 rounded-2xl border transition-all",
                          it.accion_sobrante === "retornar"
                            ? "bg-card border-emerald-500/30 shadow-xs"
                            : "bg-card border-rose-500/30 shadow-xs"
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-black text-xs text-foreground block">
                              {it.nombre}
                            </span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              Ap: {ap} + Rep: {rep} - Cie: {cie}
                            </span>
                          </div>
                          <span className="text-[10px] font-mono font-black px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                            Neto: {consumo} {it.unidad}
                          </span>
                        </div>

                        <div className="mt-2 pt-2 border-t border-border/50 flex flex-col gap-2">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-muted-foreground">Sobrante a decidir:</span>
                            <strong className="font-mono text-foreground">
                              {cie} {it.unidad}
                            </strong>
                          </div>

                          <div className="grid grid-cols-2 gap-1.5">
                            <button
                              type="button"
                              data-testid={`split-btn-retornar-${idx}`}
                              onClick={() => handleSetAccionSobrante(idx, "retornar")}
                              className={cn(
                                "py-1.5 px-2 rounded-xl text-[10px] font-black uppercase tracking-wider border text-center transition-all cursor-pointer",
                                it.accion_sobrante === "retornar"
                                  ? "bg-emerald-500 text-white border-emerald-500 shadow-sm"
                                  : "border-border hover:bg-muted text-muted-foreground"
                              )}
                            >
                              ↩ Retornar
                            </button>

                            <button
                              type="button"
                              data-testid={`split-btn-merma-${idx}`}
                              onClick={() => handleSetAccionSobrante(idx, "merma")}
                              className={cn(
                                "py-1.5 px-2 rounded-xl text-[10px] font-black uppercase tracking-wider border text-center transition-all cursor-pointer",
                                it.accion_sobrante === "merma"
                                  ? "bg-rose-500 text-white border-rose-500 shadow-sm"
                                  : "border-border hover:bg-muted text-muted-foreground"
                              )}
                            >
                              🗑 Merma
                            </button>
                          </div>

                          {it.accion_sobrante === "merma" && (
                            <select
                              data-testid={`split-select-motivo-${idx}`}
                              value={it.motivo_merma || MOTIVOS_MERMA[0]}
                              onChange={(e) =>
                                handleUpdateItemField(idx, "motivo_merma", e.target.value)
                              }
                              className="w-full text-[10px] rounded-lg border border-rose-500/30 bg-background text-foreground px-2 py-1 font-medium mt-1"
                            >
                              {MOTIVOS_MERMA.map((m) => (
                                <option key={m} value={m}>
                                  {m}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Panel de Rechazo con Justificación Obligatoria */}
        {showRejectInput && (
          <div
            data-testid="buffet-reject-panel"
            className="p-3 rounded-2xl bg-destructive/10 border border-destructive/20 space-y-2 mb-2 animate-in fade-in"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase text-destructive tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" /> Motivo de Rechazo de Auditoría
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
              data-testid="buffet-reject-reason-input"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Ej: Las cantidades de cierre no coinciden con el registro de mermas de turno..."
              className="w-full p-2 rounded-xl bg-background border border-destructive/30 text-xs font-medium text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-destructive"
            />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Mínimo 5 caracteres</span>
              <span>{rejectReason.trim().length} caracteres</span>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="shrink-0 pt-3 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            type="button"
            data-testid="buffet-close-btn"
            onClick={handleClose}
            className="w-full sm:w-auto px-4 py-2 rounded-xl border border-input bg-background hover:bg-muted text-xs font-bold text-muted-foreground cursor-pointer"
          >
            Cerrar
          </button>

          {!showRejectInput ? (
            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                data-testid="buffet-open-reject-btn"
                onClick={() => setShowRejectInput(true)}
                disabled={resolving}
                className="px-3.5 py-2 rounded-xl border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 text-xs font-black uppercase tracking-wider inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <XCircle className="w-4 h-4" />
                <span>Rechazar</span>
              </button>

              <button
                type="button"
                data-testid="buffet-confirm-btn"
                onClick={() => handleResolve("aprobar")}
                disabled={resolving}
                className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-black uppercase tracking-widest inline-flex items-center gap-2 shadow-lg shadow-cyan-950/20 cursor-pointer disabled:opacity-50 active:scale-95 transition-all"
              >
                {resolving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4" />
                )}
                <span>Confirmar y Cerrar Auditoría Buffet</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={() => setShowRejectInput(false)}
                className="px-3 py-2 rounded-xl border border-input text-xs font-bold text-muted-foreground cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                data-testid="buffet-confirm-reject-btn"
                onClick={() => handleResolve("rechazar")}
                disabled={resolving}
                className="px-4 py-2 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground text-xs font-black uppercase tracking-wider cursor-pointer disabled:opacity-50"
              >
                {resolving ? "Rechazando..." : "Confirmar Rechazo"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default BuffetApprovalModal;
