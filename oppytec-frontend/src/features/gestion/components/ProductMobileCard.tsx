import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Package, ChevronDown, Pencil, Trash2, BarChart3 } from "lucide-react";
import { BodegaBadge } from "@/shared/components/layout/BodegaBadge";
import { Can } from "@/shared/auth/Can";
import {
  cn,
  formatMoney,
  formatUnitCost,
  formatEquivalenciaText,
  formatProductSubtitle,
  getImageUrl,
} from "@/shared/lib";
import type { Producto } from "../types";

export interface BodegaInfo {
  id: string;
  nombre: string;
  color?: string;
  icono?: string;
}

export interface ProductMobileCardProps {
  product: Producto;
  bodegas?: readonly BodegaInfo[];
  bodegaMap?: Record<string, BodegaInfo>;
  selectedWarehouseId?: string;
  visibleCols?: ReadonlySet<string> | Set<string>;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onEdit?: (product: Producto) => void;
  onDelete?: (product: Producto) => void;
  onViewDetail?: (product: Producto) => void;
  className?: string;
}

export const ProductMobileCard: React.FC<ProductMobileCardProps> = ({
  product,
  bodegas = [],
  bodegaMap = {},
  selectedWarehouseId = "all",
  visibleCols,
  isExpanded = false,
  onToggleExpand,
  onEdit,
  onDelete,
  onViewDetail,
  className,
}) => {
  const p = product;
  const isAll = selectedWarehouseId === "all" || !selectedWarehouseId;

  // Bodegas relevantes filtradas
  const relevantBodegas = useMemo(() => {
    return (p.bodegas_config || [])
      .filter((bc) => {
        const b = bodegaMap[bc.bodega_id];
        if (!b) return false;
        return isAll ? true : bc.bodega_id === selectedWarehouseId;
      })
      .sort((a, b) => {
        const idxA = bodegas.findIndex((bd) => bd.id === a.bodega_id);
        const idxB = bodegas.findIndex((bd) => bd.id === b.bodega_id);
        return idxA - idxB;
      });
  }, [p.bodegas_config, bodegaMap, isAll, selectedWarehouseId, bodegas]);

  // Contenido y unidades
  const isGranel = (p.tipo_envase_rel?.nombre || p.unidad_envase || "")
    .toLowerCase()
    .includes("granel");
  const envaseUnitLabel = isGranel
    ? p.unidad || "un"
    : p.tipo_envase_rel?.nombre || p.unidad_envase || "un";
  const contNeto = isGranel
    ? 1
    : p.contenido_envase && Number(p.contenido_envase) > 0
    ? Number(p.contenido_envase)
    : 1;
  const baseUnitStr = isGranel
    ? p.unidad || "kg"
    : p.contenido_envase && Number(p.contenido_envase) > 0
    ? p.unidad_envase || p.unidad || "un"
    : p.unidad || p.unidad_envase || "un";

  // Stocks
  const stockVigenteTotal = useMemo(() => {
    return (relevantBodegas || []).reduce(
      (sum, bc) => sum + (bc.stock_actual ?? 0),
      0
    );
  }, [relevantBodegas]);

  const stockMinimoTotal = useMemo(() => {
    return (relevantBodegas || []).reduce(
      (sum, bc) => sum + (bc.stock_minimo ?? 0),
      0
    );
  }, [relevantBodegas]);

  // Multiplicador IVA
  const pct = p.iva_porcentaje ?? 19;
  const mult = 1 + pct / 100;

  // Presentación primaria
  const primaryPres =
    p.presentaciones_compra?.find(
      (pres) =>
        (pres.ultimo_costo && Number(pres.ultimo_costo) > 0) ||
        (pres.cantidad && pres.cantidad > 1)
    ) || p.presentaciones_compra?.[0];

  const presEquiv =
    primaryPres?.equivalencia && Number(primaryPres.equivalencia) > 0
      ? Number(primaryPres.equivalencia)
      : contNeto;
  const presCantEnvases =
    primaryPres?.cantidad && Number(primaryPres.cantidad) > 0
      ? Number(primaryPres.cantidad)
      : contNeto > 0 && presEquiv > 0
      ? presEquiv / contNeto
      : presEquiv;

  // 1. Último Costo
  const costoUltimoUnidadNeto =
    primaryPres && primaryPres.ultimo_costo && presCantEnvases > 0
      ? Number(primaryPres.ultimo_costo) / presCantEnvases
      : p.costo_unitario_ultimo ?? (p.ultimo_costo ? Number(p.ultimo_costo) : p.costo_unitario ?? 0);
  const costoUltimoUnidadBruto = costoUltimoUnidadNeto
    ? costoUltimoUnidadNeto * mult
    : 0;
  const costoUltimoEmbalajeNeto = primaryPres?.ultimo_costo
    ? Number(primaryPres.ultimo_costo)
    : p.ultimo_costo
    ? Number(p.ultimo_costo)
    : costoUltimoUnidadNeto * presCantEnvases;
  const costoUltimoEmbalajeBruto = primaryPres?.costo_bruto
    ? Number(primaryPres.costo_bruto)
    : costoUltimoEmbalajeNeto
    ? Math.round(costoUltimoEmbalajeNeto * mult)
    : 0;

  // 2. Penúltimo Costo
  const costoPenultimoUnidadNeto =
    primaryPres && primaryPres.penultimo_costo && presCantEnvases > 0
      ? Number(primaryPres.penultimo_costo) / presCantEnvases
      : p.costo_unitario_penultimo ?? p.costo_penultimo ?? p.penultimo_costo ?? null;
  const costoPenultimoUnidadBruto =
    costoPenultimoUnidadNeto !== null ? costoPenultimoUnidadNeto * mult : null;
  const costoPenultimoEmbalajeNeto = primaryPres?.penultimo_costo
    ? Number(primaryPres.penultimo_costo)
    : costoPenultimoUnidadNeto !== null
    ? costoPenultimoUnidadNeto * presCantEnvases
    : null;
  const costoPenultimoEmbalajeBruto =
    costoPenultimoEmbalajeNeto !== null
      ? Math.round(costoPenultimoEmbalajeNeto * mult)
      : null;

  // 3. Costo Promedio Inventario (PPP)
  const costoPromInvUnidadNeto =
    p.costo_unitario_ppp && p.costo_unitario_ppp > 0
      ? p.costo_unitario_ppp
      : p.costo_promedio_inventario && p.costo_promedio_inventario > 0
      ? p.costo_promedio_inventario
      : p.costo_promedio && Number(p.costo_promedio) > 0
      ? Number(p.costo_promedio)
      : costoUltimoUnidadNeto;
  const costoPromInvUnidadBruto = costoPromInvUnidadNeto
    ? costoPromInvUnidadNeto * mult
    : 0;

  // 4. Costo Promedio Histórico (10 compras)
  const costoPromHistUnidadNeto =
    p.costo_unitario_promedio_10 && p.costo_unitario_promedio_10 > 0
      ? p.costo_unitario_promedio_10
      : p.costo_promedio_historico && p.costo_promedio_historico > 0
      ? p.costo_promedio_historico
      : costoUltimoUnidadNeto;
  const costoPromHistUnidadBruto = costoPromHistUnidadNeto
    ? costoPromHistUnidadNeto * mult
    : 0;

  // 5. Precios de Venta & Márgenes
  const pvBruto = p.precio_venta ? Number(p.precio_venta) : null;
  const pvNeto = pvBruto ? pvBruto / mult : null;
  const margenBrutoVal =
    pvBruto && pvBruto > 0 && costoPromInvUnidadBruto > 0
      ? ((pvBruto - costoPromInvUnidadBruto) / pvBruto) * 100
      : null;
  const margenNetoVal =
    pvNeto && pvNeto > 0 && costoPromInvUnidadNeto > 0
      ? ((pvNeto - costoPromInvUnidadNeto) / pvNeto) * 100
      : null;

  // 6. Variación Inflacionaria
  let varPercent: number | null = null;
  if (
    costoUltimoUnidadNeto > 0 &&
    costoPenultimoUnidadNeto !== null &&
    costoPenultimoUnidadNeto > 0
  ) {
    varPercent =
      ((costoUltimoUnidadNeto - costoPenultimoUnidadNeto) /
        costoPenultimoUnidadNeto) *
      100;
  }

  // 7. Valor Inventario
  const valorInvTotalNeto =
    p.valor_inventario ?? Math.round(stockVigenteTotal * costoPromInvUnidadNeto);
  const valorInvTotalBruto = Math.round(valorInvTotalNeto * mult);

  // 8. Cobertura & Rotación
  const dailyCons = p.consumo_diario_promedio
    ? Number(p.consumo_diario_promedio)
    : 0;
  const daysCov =
    dailyCons > 0
      ? Math.round(stockVigenteTotal / dailyCons)
      : stockVigenteTotal > 0
      ? 30
      : 0;
  const soldUnits = p.unidades_vendidas_mes ? Number(p.unidades_vendidas_mes) : 0;
  const invAvg = stockVigenteTotal > 0 ? stockVigenteTotal : 1;
  const rotIndex = soldUnits / invAvg;

  // Construcción de métricas activas
  const metricsList = useMemo(() => {
    const list: {
      label: string;
      value: string;
      highlight?: "primary" | "emerald" | "amber" | "red";
    }[] = [];

    const isColVisible = (key: string) => !visibleCols || visibleCols.has(key);

    if (isColVisible("precio_venta_bruto")) {
      list.push({
        label: "P. Venta Bruto",
        value: pvBruto ? formatUnitCost(pvBruto) : "—",
        highlight: "primary",
      });
    }
    if (isColVisible("precio_venta_neto")) {
      list.push({
        label: "P. Venta Neto",
        value: pvNeto ? formatUnitCost(pvNeto) : "—",
        highlight: "primary",
      });
    }
    if (isColVisible("ultimo_costo_unidad_neto")) {
      list.push({
        label: "Últ. Costo Neto",
        value: costoUltimoUnidadNeto
          ? `${formatUnitCost(costoUltimoUnidadNeto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("ultimo_costo_unidad_bruto")) {
      list.push({
        label: "Últ. Costo Bruto",
        value: costoUltimoUnidadBruto
          ? `${formatUnitCost(costoUltimoUnidadBruto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("ultimo_costo_embalaje_neto")) {
      list.push({
        label: "Últ. Emb. Neto",
        value: costoUltimoEmbalajeNeto
          ? formatMoney(Math.round(costoUltimoEmbalajeNeto))
          : "—",
      });
    }
    if (isColVisible("ultimo_costo_embalaje_bruto")) {
      list.push({
        label: "Últ. Emb. Bruto",
        value: costoUltimoEmbalajeBruto
          ? formatMoney(Math.round(costoUltimoEmbalajeBruto))
          : "—",
      });
    }
    if (isColVisible("penultimo_costo_unidad_neto")) {
      list.push({
        label: "Penúlt. Costo Neto",
        value: costoPenultimoUnidadNeto
          ? `${formatUnitCost(costoPenultimoUnidadNeto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("penultimo_costo_unidad_bruto")) {
      list.push({
        label: "Penúlt. Costo Bruto",
        value: costoPenultimoUnidadBruto
          ? `${formatUnitCost(costoPenultimoUnidadBruto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("penultimo_costo_embalaje_neto")) {
      list.push({
        label: "Penúlt. Emb. Neto",
        value: costoPenultimoEmbalajeNeto
          ? formatMoney(Math.round(costoPenultimoEmbalajeNeto))
          : "—",
      });
    }
    if (isColVisible("penultimo_costo_embalaje_bruto")) {
      list.push({
        label: "Penúlt. Emb. Bruto",
        value: costoPenultimoEmbalajeBruto
          ? formatMoney(Math.round(costoPenultimoEmbalajeBruto))
          : "—",
      });
    }
    if (isColVisible("variacion_costo")) {
      list.push({
        label: "Var. Inflacionaria",
        value:
          varPercent !== null
            ? `${varPercent > 0 ? "🔴 +" : varPercent < 0 ? "🟢 " : ""}${varPercent.toFixed(1)}%`
            : "—",
        highlight:
          varPercent !== null
            ? varPercent > 0
              ? "red"
              : varPercent < 0
              ? "emerald"
              : undefined
            : undefined,
      });
    }
    if (isColVisible("costo_prom_inv_unidad_neto")) {
      list.push({
        label: "PPP Unit. Neto",
        value: costoPromInvUnidadNeto
          ? `${formatUnitCost(costoPromInvUnidadNeto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("costo_prom_inv_unidad_bruto")) {
      list.push({
        label: "PPP Unit. Bruto",
        value: costoPromInvUnidadBruto
          ? `${formatUnitCost(costoPromInvUnidadBruto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("costo_prom_hist_unidad_neto")) {
      list.push({
        label: "Hist. Unit. Neto",
        value: costoPromHistUnidadNeto
          ? `${formatUnitCost(costoPromHistUnidadNeto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("costo_prom_hist_unidad_bruto")) {
      list.push({
        label: "Hist. Unit. Bruto",
        value: costoPromHistUnidadBruto
          ? `${formatUnitCost(costoPromHistUnidadBruto)} / ${envaseUnitLabel}`
          : "—",
      });
    }
    if (isColVisible("margen_bruto")) {
      list.push({
        label: "Margen Bruto",
        value: margenBrutoVal !== null ? `${margenBrutoVal.toFixed(1)}%` : "—",
        highlight:
          margenBrutoVal !== null
            ? margenBrutoVal >= 40
              ? "emerald"
              : margenBrutoVal >= 20
              ? "amber"
              : "red"
            : undefined,
      });
    }
    if (isColVisible("margen_neto")) {
      list.push({
        label: "Margen Neto",
        value: margenNetoVal !== null ? `${margenNetoVal.toFixed(1)}%` : "—",
        highlight:
          margenNetoVal !== null
            ? margenNetoVal >= 40
              ? "emerald"
              : margenNetoVal >= 20
              ? "amber"
              : "red"
            : undefined,
      });
    }
    if (isColVisible("valor_inventario_neto")) {
      list.push({
        label: "Valor Inv. Neto",
        value: valorInvTotalNeto > 0 ? formatMoney(valorInvTotalNeto) : "$0",
      });
    }
    if (isColVisible("valor_inventario_bruto")) {
      list.push({
        label: "Valor Inv. Bruto",
        value: valorInvTotalBruto > 0 ? formatMoney(valorInvTotalBruto) : "$0",
      });
    }
    if (isColVisible("dias_cobertura")) {
      list.push({
        label: "Días Cobertura",
        value: `${daysCov} días`,
        highlight: daysCov >= 15 ? "emerald" : daysCov >= 7 ? "amber" : "red",
      });
    }
    if (isColVisible("indice_rotacion")) {
      list.push({
        label: "Índice Rotación",
        value: rotIndex > 0 ? `${rotIndex.toFixed(1)}x / mes` : "0x / mes",
      });
    }

    return list;
  }, [
    visibleCols,
    pvBruto,
    pvNeto,
    costoUltimoUnidadNeto,
    envaseUnitLabel,
    costoUltimoUnidadBruto,
    costoUltimoEmbalajeNeto,
    costoUltimoEmbalajeBruto,
    costoPenultimoUnidadNeto,
    varPercent,
    costoPromInvUnidadNeto,
    costoPromHistUnidadNeto,
    margenBrutoVal,
    valorInvTotalNeto,
    daysCov,
    rotIndex,
  ]);

  const isZero = stockVigenteTotal === 0;
  const isLow = stockVigenteTotal < stockMinimoTotal && stockMinimoTotal > 0;

  return (
    <div
      data-testid={`product-mobile-card-${p.id}`}
      className={cn(
        "rounded-2xl bg-card border border-input shadow-xs transition-all duration-200 overflow-hidden",
        isExpanded ? "ring-2 ring-primary/40 shadow-md border-primary/30" : "hover:border-input/80",
        className
      )}
    >
      {/* ─── CABECERA COLAPSADA (Touch Target >= 44px) ─── */}
      <button
        type="button"
        data-testid={`product-mobile-header-${p.id}`}
        onClick={onToggleExpand}
        className="w-full min-h-[52px] p-3 flex items-center gap-3 text-left cursor-pointer select-none active:scale-[0.99] transition-transform"
      >
        {/* IMAGEN O ICONO */}
        {p.imagen_url ? (
          <img
            src={getImageUrl(p.imagen_url)}
            alt={p.nombre}
            className="h-11 w-11 rounded-xl object-cover shrink-0 border border-border/50"
          />
        ) : (
          <div className="h-11 w-11 rounded-xl bg-secondary/60 border border-border/50 flex items-center justify-center shrink-0">
            <Package className="h-5 w-5 text-muted-foreground/60" />
          </div>
        )}

        {/* NOMBRE, SUBTÍTULO Y BADGE */}
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <div className="flex items-center gap-1.5 flex-wrap">
            <h3 className="font-bold text-sm text-foreground truncate">{p.nombre}</h3>
            {p.estado === "borrador_incompleto" && (
              <span className="px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[9px] font-bold shrink-0">
                📝 Borrador Incompleto
              </span>
            )}
          </div>
          <span className="text-[10px] text-muted-foreground truncate">
            {formatProductSubtitle(p)}
          </span>
          {/* Primer badge de bodega en resumen */}
          {relevantBodegas.length > 0 && (
            <div className="flex items-center gap-1 mt-1 flex-wrap">
              {relevantBodegas.slice(0, 2).map((bc) => {
                const b = bodegaMap[bc.bodega_id];
                if (!b) return null;
                return (
                  <BodegaBadge
                    key={bc.bodega_id}
                    nombre={b.nombre}
                    color={b.color}
                    icono={b.icono}
                    className="py-0.5 px-1.5 text-[8px]"
                  />
                );
              })}
              {relevantBodegas.length > 2 && (
                <span className="text-[9px] text-muted-foreground font-semibold">
                  +{relevantBodegas.length - 2}
                </span>
              )}
            </div>
          )}
        </div>

        {/* STOCK ACTUAL RESUMIDO */}
        <div className="shrink-0 flex flex-col items-end pr-1">
          <span
            className={cn(
              "text-xs font-black tabular-nums leading-none",
              isZero ? "text-red-500" : isLow ? "text-amber-500" : "text-emerald-600 dark:text-emerald-400"
            )}
          >
            {stockVigenteTotal}
            <span className="text-[9px] font-bold text-muted-foreground ml-0.5">
              {envaseUnitLabel}
            </span>
          </span>
          {stockMinimoTotal > 0 && (
            <span className="text-[9px] text-muted-foreground">
              mín: {stockMinimoTotal}
            </span>
          )}
        </div>

        {/* CHEVRON ANIMADO */}
        <div className="shrink-0 text-muted-foreground/60">
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform duration-300",
              isExpanded && "rotate-180 text-primary"
            )}
          />
        </div>
      </button>

      {/* ─── CONTENIDO EXPANDIBLE ─── */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            key={`mobile-expanded-${p.id}`}
            data-testid={`product-mobile-content-${p.id}`}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-1 border-t border-input/40 space-y-3">
              {/* SECCIÓN DE BODEGAS Y STOCKS */}
              <div className="space-y-1.5 pt-1">
                <span className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">
                  Desglose por Bodega
                </span>
                {relevantBodegas.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground italic">
                    Sin stock configurado en bodegas activas
                  </p>
                ) : (
                  relevantBodegas.map((bc) => {
                    const b = bodegaMap[bc.bodega_id];
                    if (!b) return null;

                    const bStock = bc.stock_actual ?? 0;
                    const bMin = bc.stock_minimo ?? 0;
                    const bIsZero = bStock === 0;
                    const bIsLow = bStock < bMin && bMin > 0;
                    const bPercent = Math.min(
                      100,
                      Math.max(0, (bStock / (bMin ? bMin * 2 : 100)) * 100)
                    );
                    const coord = `${bc.coordenada_letra ?? ""}${bc.coordenada_numero ?? ""}`;

                    return (
                      <div
                        key={bc.bodega_id}
                        data-testid={`mobile-bodega-row-${bc.bodega_id}`}
                        className="flex items-center gap-2.5 p-2 rounded-xl bg-secondary/30 border border-border/30"
                      >
                        {/* Bodega Badge */}
                        <div className="w-[90px] shrink-0">
                          <BodegaBadge nombre={b.nombre} color={b.color} icono={b.icono} />
                        </div>

                        {/* Stock & Progress Bar */}
                        <div className="flex-1 flex flex-col justify-center min-w-0">
                          <span
                            className={cn(
                              "text-xs font-black tabular-nums leading-none mb-1",
                              bIsZero ? "text-red-500" : bIsLow ? "text-amber-500" : "text-foreground"
                            )}
                          >
                            {bStock}
                            <span className="text-[9px] text-muted-foreground font-bold ml-1">
                              / {bMin} {envaseUnitLabel}
                            </span>
                          </span>
                          <div className="w-full max-w-[90px] h-1.5 bg-secondary/80 rounded-full overflow-hidden">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all duration-300",
                                bIsZero
                                  ? "bg-red-500"
                                  : bIsLow
                                  ? "bg-amber-500"
                                  : "bg-emerald-500"
                              )}
                              style={{ width: `${bPercent}%` }}
                            />
                          </div>
                        </div>

                        {/* Ubicación */}
                        {coord && (
                          <div className="shrink-0 flex flex-col items-center border-l border-border/40 pl-2">
                            <span className="text-[7px] font-black uppercase tracking-widest text-muted-foreground/60">
                              Ubic
                            </span>
                            <span className="text-[10px] font-bold text-foreground">
                              {coord}
                            </span>
                          </div>
                        )}

                        {/* Contenido Equivalente */}
                        <div className="shrink-0 flex flex-col items-end border-l border-border/40 pl-2">
                          <span className="text-[7px] font-black uppercase tracking-widest text-muted-foreground/60">
                            Total
                          </span>
                          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                            {formatEquivalenciaText(bStock * contNeto, baseUnitStr)}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* GRILLA DE MÉTRICAS */}
              {metricsList.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">
                    Costos, Precios y Rentabilidad
                  </span>
                  <div className="grid grid-cols-2 gap-2 pt-0.5">
                    {metricsList.map((m, mIdx) => (
                      <div
                        key={mIdx}
                        className="flex flex-col p-2 rounded-xl bg-secondary/20 border border-border/30 justify-center"
                      >
                        <span className="text-[8px] font-black uppercase tracking-wider text-muted-foreground/80 truncate">
                          {m.label}
                        </span>
                        <span
                          className={cn(
                            "text-xs font-black tabular-nums truncate mt-0.5",
                            m.highlight === "primary" && "text-primary",
                            m.highlight === "emerald" && "text-emerald-500",
                            m.highlight === "amber" && "text-amber-500",
                            m.highlight === "red" && "text-red-500",
                            !m.highlight && "text-foreground"
                          )}
                        >
                          {m.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ACCIONES TOUCH TARGET >= 44px */}
              <div className="flex items-center justify-between pt-2 border-t border-input/30 gap-2">
                {onViewDetail && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewDetail(p);
                    }}
                    className="min-h-[44px] px-3 gap-1.5 rounded-xl border border-border bg-secondary/50 text-[11px] font-bold text-foreground hover:bg-secondary transition-colors inline-flex items-center justify-center cursor-pointer active:scale-95"
                  >
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <span>Ficha / Kardex</span>
                  </button>
                )}

                <div className="flex items-center gap-1.5 ml-auto">
                  {onEdit && (
                    <Can perform="catalog.products.edit">
                      <button
                        type="button"
                        data-testid={`mobile-edit-btn-${p.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onEdit(p);
                        }}
                        className="min-h-[44px] min-w-[44px] px-3 gap-1.5 rounded-xl border border-yellow-500/20 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 font-bold text-[11px] hover:bg-yellow-500/20 transition-colors inline-flex items-center justify-center cursor-pointer active:scale-95"
                      >
                        <Pencil className="h-4 w-4" />
                        <span>Editar</span>
                      </button>
                    </Can>
                  )}

                  {onDelete && (
                    <Can perform="catalog.products.delete">
                      <button
                        type="button"
                        data-testid={`mobile-delete-btn-${p.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(p);
                        }}
                        className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-red-500/20 bg-red-500/10 text-red-500 font-bold hover:bg-red-500/20 transition-colors inline-flex items-center justify-center cursor-pointer active:scale-95"
                        aria-label="Eliminar producto"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </Can>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ProductMobileCard;
