/**
 * oppytec-frontend/src/features/procurement/mermas/MermaHistory.tsx
 * Historial Detallado y Auditoría de Mermas (Fase 6.5).
 * Vista dual (Tabla Desktop + Tarjetas Mobile-First), filtro por motivo y buscador por producto/lote.
 * Respeta estrictamente la regla inmutable "Pollo King" y formateo FX con precisión Decimal.
 * Conecta con el botón rápido "+ Registrar Merma" para disparar MermaDialog.
 */

import { useState, useMemo } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  LayoutGrid,
  List,
  Plus,
  Search,
  UserCheck,
  Warehouse,
  X,
  XCircle,
} from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { MermaHistoryItem } from "../types";

export interface MermaHistoryProps {
  readonly items: MermaHistoryItem[];
  readonly isLoading?: boolean;
  readonly selectedMotivoFilter?: string | null;
  readonly onMotivoFilterChange?: (motivo: string | null) => void;
  readonly onOpenRegisterMerma: () => void;
}

export function formatMermaDateTime(isoString?: string | null): string {
  if (!isoString) return "—";
  try {
    const dt = new Date(isoString);
    if (isNaN(dt.getTime())) return isoString;
    const dd = String(dt.getUTCDate()).padStart(2, "0");
    const mm = String(dt.getUTCMonth() + 1).padStart(2, "0");
    const yyyy = dt.getUTCFullYear();
    const hh = String(dt.getUTCHours()).padStart(2, "0");
    const min = String(dt.getUTCMinutes()).padStart(2, "0");
    return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
  } catch {
    return isoString;
  }
}

export function getApprovalBadgeConfig(estado: string): {
  label: string;
  className: string;
  Icon: typeof CheckCircle2;
} {
  const normalized = (estado || "APROBADA").toUpperCase();
  if (normalized === "PENDIENTE") {
    return {
      label: "PENDIENTE",
      className:
        "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
      Icon: Clock,
    };
  }
  if (normalized === "RECHAZADA") {
    return {
      label: "RECHAZADA",
      className:
        "border-zinc-500/30 bg-zinc-500/10 text-zinc-500",
      Icon: XCircle,
    };
  }
  return {
    label: "APROBADA",
    className:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    Icon: CheckCircle2,
  };
}

export function MermaHistory({
  items,
  isLoading = false,
  selectedMotivoFilter,
  onMotivoFilterChange,
  onOpenRegisterMerma,
}: MermaHistoryProps) {
  const { format } = useCurrencyFormatter();
  const [searchQuery, setSearchQuery] = useState("");
  const [internalMotivo, setInternalMotivo] = useState<string>("TODOS");
  const [estadoFilter, setEstadoFilter] = useState<string>("TODOS");
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");

  const activeMotivo =
    selectedMotivoFilter !== undefined
      ? selectedMotivoFilter || "TODOS"
      : internalMotivo;

  const handleMotivoChange = (value: string) => {
    setInternalMotivo(value);
    onMotivoFilterChange?.(value === "TODOS" ? null : value);
  };

  // Lista única de motivos presentes + motivos estándar
  const availableMotivos = useMemo(() => {
    const set = new Set<string>([
      "Vencimiento",
      "Rotura / Daño Físico",
      "Cadena de Frío",
      "Cocción / Manipulación",
    ]);
    items.forEach((it) => {
      if (it.motivo) set.add(it.motivo);
    });
    return Array.from(set);
  }, [items]);

  // Filtrado reactivo por búsqueda de producto/SKU/lote, motivo y estado
  const filteredItems = useMemo(() => {
    return items.filter((it) => {
      const lotCode = `LOTE-${it.id}`;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesName = (it.producto_nombre || "").toLowerCase().includes(q);
        const matchesSku = (it.producto_sku || "").toLowerCase().includes(q);
        const matchesLot = lotCode.toLowerCase().includes(q);
        const matchesBodega = (it.bodega_nombre || "").toLowerCase().includes(q);
        if (!matchesName && !matchesSku && !matchesLot && !matchesBodega) {
          return false;
        }
      }

      if (activeMotivo !== "TODOS") {
        if (it.motivo.toLowerCase() !== activeMotivo.toLowerCase()) {
          return false;
        }
      }

      if (estadoFilter !== "TODOS") {
        if ((it.estado_aprobacion || "").toUpperCase() !== estadoFilter) {
          return false;
        }
      }

      return true;
    });
  }, [items, searchQuery, activeMotivo, estadoFilter]);

  const totalFilteredLoss = useMemo(() => {
    return filteredItems.reduce((acc, it) => acc + Number(it.costo_total || 0), 0);
  }, [filteredItems]);

  return (
    <div
      data-testid="merma-history-section"
      className="glass-card rounded-2xl border border-border bg-card shadow-sm overflow-hidden"
    >
      {/* 1. CABECERA Y CONTROLES DE FILTRADO + BOTÓN REGISTRAR MERMA */}
      <div className="p-4 border-b border-border/70 space-y-3 bg-muted/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
              Historial Detallado y Auditoría de Mermas
            </h3>
            <p className="text-xs text-muted-foreground">
              Mostrando <strong className="text-foreground">{filteredItems.length}</strong>{" "}
              registros · Pérdida acumulada en vista:{" "}
              <strong className="font-mono text-rose-600 dark:text-rose-400">
                {format(totalFilteredLoss)}
              </strong>
            </p>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            {/* Switcher Tabla / Tarjetas */}
            <div className="inline-flex rounded-xl border border-border bg-background p-0.5">
              <button
                type="button"
                data-testid="merma-history-view-table"
                onClick={() => setViewMode("table")}
                title="Vista de Tabla"
                className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all cursor-pointer ${
                  viewMode === "table"
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <List className="h-4 w-4" />
              </button>
              <button
                type="button"
                data-testid="merma-history-view-cards"
                onClick={() => setViewMode("cards")}
                title="Vista de Tarjetas Mobile-First"
                className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all cursor-pointer ${
                  viewMode === "cards"
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
            </div>

            {/* Botón rápido + Registrar Merma (Touch target >= 44px) */}
            <button
              type="button"
              data-testid="btn-registrar-merma"
              onClick={onOpenRegisterMerma}
              className="touch-target min-h-[44px] inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-xs font-black uppercase tracking-wider text-white shadow-md shadow-rose-600/20 hover:bg-rose-700 active:scale-95 transition-all cursor-pointer"
            >
              <Plus className="h-4 w-4" />
              <span>+ Registrar Merma</span>
            </button>
          </div>
        </div>

        {/* Barra de Búsqueda y Selectores de Motivo / Estado */}
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-12">
          {/* Buscador por Producto / SKU / Lote */}
          <div className="relative sm:col-span-6">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              data-testid="input-search-merma-history"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por producto (ej. Pollo King), SKU, lote o bodega..."
              className="w-full min-h-[44px] rounded-xl border border-border bg-background pl-10 pr-9 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                data-testid="btn-clear-merma-search"
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground hover:bg-muted cursor-pointer"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Selector de Motivo */}
          <div className="sm:col-span-3 flex items-center gap-1.5">
            <Filter className="h-4 w-4 text-muted-foreground shrink-0 hidden sm:block" />
            <select
              data-testid="select-filter-motivo"
              aria-label="Filtrar por motivo de merma"
              value={activeMotivo}
              onChange={(e) => handleMotivoChange(e.target.value)}
              className="w-full min-h-[44px] rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none cursor-pointer"
            >
              <option value="TODOS">Todos los motivos</option>
              {availableMotivos.map((mot) => (
                <option key={mot} value={mot}>
                  {mot}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Estado de Aprobación */}
          <div className="sm:col-span-3">
            <select
              data-testid="select-filter-estado"
              aria-label="Filtrar por estado de aprobación"
              value={estadoFilter}
              onChange={(e) => setEstadoFilter(e.target.value)}
              className="w-full min-h-[44px] rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none cursor-pointer"
            >
              <option value="TODOS">Todos los estados</option>
              <option value="APROBADA">Aprobada</option>
              <option value="PENDIENTE">Pendiente de Aprobación</option>
              <option value="RECHAZADA">Rechazada</option>
            </select>
          </div>
        </div>
      </div>

      {/* 2. CONTENIDO: TABLA O TARJETAS */}
      {isLoading ? (
        <div className="p-6 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 w-full animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div
          data-testid="merma-history-empty"
          className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground mb-3">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-bold text-foreground">
            No se encontraron registros de merma
          </h4>
          <p className="mt-1 max-w-sm text-xs text-muted-foreground">
            No hay eventos que coincidan con los filtros activos.
          </p>
        </div>
      ) : viewMode === "table" ? (
        <div data-testid="merma-history-table" className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border/80 bg-muted/40 text-[11px] font-black text-muted-foreground uppercase tracking-wider">
                <th className="py-3 px-4">Fecha / Hora</th>
                <th className="py-3 px-4">Producto / Insumo</th>
                <th className="py-3 px-4">Bodega & Lote</th>
                <th className="py-3 px-4">Motivo</th>
                <th className="py-3 px-4 text-right">Cantidad</th>
                <th className="py-3 px-4 text-right">Costo PPP Unit.</th>
                <th className="py-3 px-4 text-right">Pérdida Total</th>
                <th className="py-3 px-4 text-center">Operador</th>
                <th className="py-3 px-4 text-center">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 font-medium">
              {filteredItems.map((item) => {
                const qty = Math.max(0.0001, Number(item.cantidad || 0));
                const totalCost = Number(item.costo_total || 0);
                const unitCostPpp = totalCost / qty;
                const approval = getApprovalBadgeConfig(item.estado_aprobacion);
                const ApprovalIcon = approval.Icon;
                const lotCode = `LOTE-${item.id}`;

                return (
                  <tr
                    key={item.id}
                    data-testid={`merma-history-row-${item.id}`}
                    className="transition-colors hover:bg-muted/30"
                  >
                    {/* Fecha */}
                    <td className="py-3.5 px-4 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      {formatMermaDateTime(item.fecha_merma ?? item.created_at)}
                    </td>

                    {/* Producto (Regla Pollo King intacta) */}
                    <td className="py-3.5 px-4">
                      <div
                        data-testid={`merma-row-producto-${item.id}`}
                        className="font-bold text-foreground"
                      >
                        {item.producto_nombre || `Producto #${item.producto_id}`}
                      </div>
                      {item.producto_sku && (
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {item.producto_sku}
                        </div>
                      )}
                    </td>

                    {/* Bodega & Lote */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5 text-foreground font-semibold">
                        <Warehouse className="h-3.5 w-3.5 text-primary shrink-0" />
                        <span>{item.bodega_nombre || `Bodega #${item.bodega_id}`}</span>
                      </div>
                      <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
                        Lote: {lotCode}
                      </div>
                    </td>

                    {/* Motivo */}
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center rounded-lg bg-rose-500/10 border border-rose-500/20 px-2.5 py-0.5 text-[11px] font-bold text-rose-600 dark:text-rose-400">
                        {item.motivo}
                      </span>
                    </td>

                    {/* Cantidad */}
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-foreground whitespace-nowrap">
                      {Number(item.cantidad || 0).toFixed(2)} u.
                    </td>

                    {/* Costo PPP Unitario */}
                    <td className="py-3.5 px-4 text-right font-mono text-muted-foreground whitespace-nowrap">
                      {format(unitCostPpp)}
                    </td>

                    {/* Pérdida Total */}
                    <td
                      data-testid={`merma-row-costo-${item.id}`}
                      className="py-3.5 px-4 text-right font-mono font-black text-rose-600 dark:text-rose-400 whitespace-nowrap"
                    >
                      {format(totalCost)}
                    </td>

                    {/* Operador responsable */}
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                        <UserCheck className="h-3.5 w-3.5 text-primary" />
                        Op. #{item.reportado_por_user_id}
                      </span>
                    </td>

                    {/* Estado de Aprobación */}
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span
                        data-testid={`merma-row-estado-${item.id}`}
                        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase ${approval.className}`}
                      >
                        <ApprovalIcon className="h-3 w-3" />
                        <span>{approval.label}</span>
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* Vista en Tarjetas Mobile-First */
        <div
          data-testid="merma-history-cards"
          className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {filteredItems.map((item) => {
            const qty = Math.max(0.0001, Number(item.cantidad || 0));
            const totalCost = Number(item.costo_total || 0);
            const unitCostPpp = totalCost / qty;
            const approval = getApprovalBadgeConfig(item.estado_aprobacion);
            const lotCode = `LOTE-${item.id}`;

            return (
              <div
                key={item.id}
                data-testid={`merma-history-card-${item.id}`}
                className="rounded-2xl border border-border bg-background/60 p-4 space-y-3 shadow-sm"
              >
                <div className="flex items-start justify-between gap-2 border-b border-border/60 pb-2.5">
                  <div>
                    <h4 className="font-bold text-foreground text-sm">
                      {item.producto_nombre || `Producto #${item.producto_id}`}
                    </h4>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {item.producto_sku} · {lotCode}
                    </span>
                  </div>
                  <span
                    className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase ${approval.className}`}
                  >
                    {approval.label}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Motivo</span>
                    <span className="font-bold text-rose-600 dark:text-rose-400">
                      {item.motivo}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Bodega</span>
                    <span className="font-semibold text-foreground">
                      {item.bodega_nombre || `Bodega #${item.bodega_id}`}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">
                      Cantidad × PPP
                    </span>
                    <span className="font-mono font-semibold text-foreground">
                      {Number(item.cantidad || 0).toFixed(2)} u. × {format(unitCostPpp)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">
                      Pérdida Total
                    </span>
                    <span className="font-mono font-black text-rose-600 dark:text-rose-400">
                      {format(totalCost)}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
                  <span>{formatMermaDateTime(item.fecha_merma ?? item.created_at)}</span>
                  <span>Operador #{item.reportado_por_user_id}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MermaHistory;
