import React, { useState, useMemo, useRef, useCallback } from "react";
import {
  ChevronDown,
  ChevronRight,
  Pencil,
  Trash2,
  Package,
} from "lucide-react";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { BodegaBadge } from "@/shared/components/layout/BodegaBadge";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { Can } from "@/shared/auth/Can";
import {
  cn,
  formatMoney,
  formatUnitCost,
  formatEquivalenciaText,
  formatProductSubtitle,
  getImageUrl,
} from "@/shared/lib";
import { CategoryTableWrapper } from "./CategoryTableWrapper";
import {
  type Producto,
  type Categoria,
  type ColumnKey,
  ALL_COLUMNS,
  COLUMN_WIDTHS,
  getColWidthPx,
  DEFAULT_COLUMNS,
} from "../types";
import type { BodegaInfo } from "./ProductMobileCard";

export interface ProductTableProps {
  productos: Producto[];
  categorias?: readonly Categoria[];
  bodegas?: readonly BodegaInfo[];
  bodegaMap?: Record<string, BodegaInfo>;
  selectedWarehouseId?: string;
  activeCols?: readonly ColumnKey[];
  viewMode?: "grouped" | "simple" | "agrupado";
  collapsedCategoryIds?: ReadonlySet<string> | Set<string>;
  onToggleCategoryCollapse?: (categoryId: string) => void;
  onEdit?: (product: Producto) => void;
  onDelete?: (product: Producto) => void;
  onSelectProduct?: (product: Producto) => void;
  className?: string;
}

export const ProductTable: React.FC<ProductTableProps> = ({
  productos,
  categorias = [],
  bodegas = [],
  bodegaMap = {},
  selectedWarehouseId = "all",
  activeCols = DEFAULT_COLUMNS,
  viewMode = "grouped",
  collapsedCategoryIds,
  onToggleCategoryCollapse,
  onEdit,
  onDelete,
  onSelectProduct,
  className,
}) => {
  // Estado local para categorías colapsadas si no viene por props
  const [localCollapsed, setLocalCollapsed] = useState<Set<string>>(new Set());
  const effectiveCollapsed = collapsedCategoryIds ?? localCollapsed;

  const handleToggleCat = useCallback(
    (catId: string) => {
      if (onToggleCategoryCollapse) {
        onToggleCategoryCollapse(catId);
      } else {
        setLocalCollapsed((prev) => {
          const next = new Set(prev);
          if (next.has(catId)) next.delete(catId);
          else next.add(catId);
          return next;
        });
      }
    },
    [onToggleCategoryCollapse]
  );

  // Estado para modal de confirmación de eliminación
  const [productToDelete, setProductToDelete] = useState<Producto | null>(null);

  // Sincronización de scroll horizontal entre tablas de categorías
  const tableContainersRef = useRef<Map<string, HTMLDivElement>>(new Map());
  const isSyncingScrollRef = useRef(false);

  const registerContainer = useCallback(
    (id: string, el: HTMLDivElement | null) => {
      if (el) {
        tableContainersRef.current.set(id, el);
      } else {
        tableContainersRef.current.delete(id);
      }
    },
    []
  );

  const handleHorizontalScroll = useCallback(
    (scrollLeft: number, sourceId: string) => {
      if (isSyncingScrollRef.current) return;
      isSyncingScrollRef.current = true;
      tableContainersRef.current.forEach((el, id) => {
        if (id !== sourceId && el && el.scrollLeft !== scrollLeft) {
          el.scrollLeft = scrollLeft;
        }
      });
      isSyncingScrollRef.current = false;
    },
    []
  );

  // Definición de columnas activas ordenadas
  const activeColDefs = useMemo(() => {
    return activeCols
      .map((k) => ALL_COLUMNS.find((c) => c.key === k))
      .filter((c): c is (typeof ALL_COLUMNS)[number] => Boolean(c));
  }, [activeCols]);

  const minTableWidth = useMemo(() => {
    const colsWidth = activeColDefs.reduce(
      (sum, col) => sum + getColWidthPx(col.key),
      0
    );
    // 240px (Producto) + 96px (Acciones) + colsWidth
    return 240 + 96 + colsWidth;
  }, [activeColDefs]);

  // Agrupación por categoría
  const isGrouped = viewMode === "grouped" || viewMode === "agrupado";

  const groupedCategories = useMemo(() => {
    if (!isGrouped) return [];

    const catMap = new Map<string, { categoria: Categoria; productos: Producto[] }>();
    const uncategorized: Producto[] = [];

    // Pre-poblar categorías registradas
    categorias.forEach((cat) => {
      catMap.set(cat.id, { categoria: cat, productos: [] });
    });

    productos.forEach((p) => {
      if (p.categoria_id && catMap.has(p.categoria_id)) {
        catMap.get(p.categoria_id)!.productos.push(p);
      } else {
        uncategorized.push(p);
      }
    });

    const result = Array.from(catMap.values()).filter(
      (group) => group.productos.length > 0
    );

    if (uncategorized.length > 0) {
      result.push({
        categoria: {
          id: "sin-categoria",
          nombre: "Sin Categoría",
          color: "#94a3b8",
          icono: "Folder",
        },
        productos: uncategorized,
      });
    }

    return result;
  }, [productos, categorias, isGrouped]);

  const isAllWarehouses = selectedWarehouseId === "all" || !selectedWarehouseId;

  // Renderizador de fila de producto
  const renderRow = (p: Producto, isChild = false) => {
    const relevantBodegas = (p.bodegas_config || [])
      .filter((bc) => {
        const b = bodegaMap[bc.bodega_id];
        if (!b) return false;
        return isAllWarehouses ? true : bc.bodega_id === selectedWarehouseId;
      })
      .sort((a, b) => {
        const indexA = bodegas.findIndex((bd) => bd.id === a.bodega_id);
        const indexB = bodegas.findIndex((bd) => bd.id === b.bodega_id);
        return indexA - indexB;
      });

    const tdClass =
      "px-3 py-3 border-y border-border/20 bg-card/70 bg-gradient-to-r from-card to-card/60 shadow-xs transition-colors group-hover:bg-accent/40";

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

    const pct = p.iva_porcentaje ?? 19;
    const mult = 1 + pct / 100;

    const primaryPres =
      p.presentaciones_compra?.find(
        (pres) =>
          (pres.ultimo_costo && Number(pres.ultimo_costo) > 0) ||
          (pres.cantidad && pres.cantidad > 1)
      ) || p.presentaciones_compra?.[0];
    const presName =
      primaryPres?.nombre ||
      (p.tipo_envase_rel?.nombre
        ? `Caja x1 ${p.tipo_envase_rel.nombre}`
        : "Embalaje");
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
        : p.costo_unitario_ultimo ??
          (p.ultimo_costo ? Number(p.ultimo_costo) : p.costo_unitario ?? 0);
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
      costoPenultimoUnidadNeto !== null
        ? costoPenultimoUnidadNeto * mult
        : null;
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
    const costoPromInvEmbalajeNeto =
      costoPromInvUnidadNeto * presCantEnvases;
    const costoPromInvEmbalajeBruto = costoPromInvEmbalajeNeto
      ? Math.round(costoPromInvEmbalajeNeto * mult)
      : 0;

    // 4. Costo Promedio Histórico
    const costoPromHistUnidadNeto =
      p.costo_unitario_promedio_10 && p.costo_unitario_promedio_10 > 0
        ? p.costo_unitario_promedio_10
        : p.costo_promedio_historico && p.costo_promedio_historico > 0
        ? p.costo_promedio_historico
        : costoUltimoUnidadNeto;
    const costoPromHistUnidadBruto = costoPromHistUnidadNeto
      ? costoPromHistUnidadNeto * mult
      : 0;
    const costoPromHistEmbalajeNeto =
      costoPromHistUnidadNeto * presCantEnvases;
    const costoPromHistEmbalajeBruto = costoPromHistEmbalajeNeto
      ? Math.round(costoPromHistEmbalajeNeto * mult)
      : 0;

    // 5. Stock & Valor Inventario
    const stockVigenteTotal = (relevantBodegas || []).reduce(
      (sum, bc) => sum + (bc.stock_actual ?? 0),
      0
    );
    const valorInvTotalNeto =
      p.valor_inventario ??
      Math.round(stockVigenteTotal * costoPromInvUnidadNeto);
    const valorInvTotalBruto = Math.round(valorInvTotalNeto * mult);

    // 6. Precios de Venta & Márgenes
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
    const foodCostVal =
      pvBruto && pvBruto > 0 && costoPromInvUnidadBruto > 0
        ? (costoPromInvUnidadBruto / pvBruto) * 100
        : null;

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

    // 7. Cobertura y Rotación
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

    return (
      <tr
        key={p.id}
        data-testid={`product-row-${p.id}`}
        onClick={() => onSelectProduct?.(p)}
        className="group cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-sm"
      >
        {/* Columna Fija: Producto */}
        <td
          className={cn(
            tdClass,
            "border-l rounded-l-xl",
            isChild && "pl-8 border-l-2 border-l-primary/40"
          )}
        >
          <div className="flex items-center gap-2">
            {isChild && (
              <ChevronRight className="h-3.5 w-3.5 text-primary/60 shrink-0" />
            )}
            {p.imagen_url ? (
              <img
                src={getImageUrl(p.imagen_url)}
                alt=""
                className="h-8 w-8 rounded-lg object-cover shrink-0 border border-border/40"
              />
            ) : (
              <div className="h-8 w-8 rounded-lg bg-secondary/60 flex items-center justify-center shrink-0 border border-border/40">
                <Package className="h-4 w-4 text-muted-foreground/60" />
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-semibold text-xs text-foreground truncate max-w-[150px]">
                  {p.nombre}
                </span>
                {p.estado === "borrador_incompleto" && (
                  <span className="px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[9px] font-bold shrink-0">
                    📝 Borrador
                  </span>
                )}
              </div>
              <div className="text-[10px] text-muted-foreground truncate max-w-[170px]">
                {formatProductSubtitle(p)}
              </div>
            </div>
          </div>
        </td>

        {/* Columnas Analíticas Dinámicas */}
        {activeColDefs.map((colObj) => {
          const col = colObj.key;

          // 📦 STOCK Y LOGÍSTICA
          if (col === "bodega") {
            return (
              <td key={col} className={tdClass}>
                <div className="flex flex-col gap-1.5 items-center">
                  {relevantBodegas.length === 0 ? (
                    <span className="text-[10px] text-muted-foreground">—</span>
                  ) : (
                    relevantBodegas.map((bc) => {
                      const b = bodegaMap[bc.bodega_id];
                      if (!b) return null;
                      return (
                        <div
                          key={bc.bodega_id}
                          className="flex items-center gap-1.5 h-7"
                        >
                          <BodegaBadge
                            nombre={b.nombre}
                            color={b.color}
                            icono={b.icono}
                          />
                        </div>
                      );
                    })
                  )}
                </div>
              </td>
            );
          }

          if (col === "stock_actual") {
            return (
              <td key={col} className={tdClass}>
                <div className="flex flex-col gap-2 items-center">
                  {relevantBodegas.length === 0 ? (
                    <span className="text-[10px] text-muted-foreground">—</span>
                  ) : (
                    relevantBodegas.map((bc) => {
                      const bStock = bc.stock_actual ?? 0;
                      const bMin = bc.stock_minimo ?? 0;
                      const isZero = bStock === 0;
                      const isLow = bStock < bMin && bMin > 0;
                      const percent = Math.min(
                        100,
                        Math.max(
                          0,
                          (bStock / (bMin ? bMin * 2 : 100)) * 100
                        )
                      );
                      return (
                        <div
                          key={bc.bodega_id}
                          className="w-full flex flex-col items-center gap-1"
                        >
                          <span
                            className={cn(
                              "text-sm font-black tabular-nums leading-none flex items-baseline gap-1",
                              isZero
                                ? "text-red-500"
                                : isLow
                                ? "text-amber-500"
                                : "text-foreground"
                            )}
                          >
                            <span>{bStock}</span>
                            <span className="text-[9px] text-muted-foreground font-bold">
                              {envaseUnitLabel}
                            </span>
                          </span>
                          <div className="w-16 h-1 bg-secondary/80 rounded-full overflow-hidden flex justify-start">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all duration-300",
                                isZero
                                  ? "bg-red-500"
                                  : isLow
                                  ? "bg-amber-500"
                                  : "bg-emerald-500"
                              )}
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </td>
            );
          }

          if (col === "stock_min") {
            return (
              <td key={col} className={tdClass}>
                <div className="flex flex-col gap-1.5 items-center">
                  {relevantBodegas.length === 0 ? (
                    <span className="text-[10px] text-muted-foreground">—</span>
                  ) : (
                    relevantBodegas.map((bc) => (
                      <span
                        key={bc.bodega_id}
                        className="text-xs font-black text-foreground/80 tabular-nums h-7 flex items-center justify-center gap-1"
                      >
                        <span>{bc.stock_minimo ?? 0}</span>
                        <span className="text-[9px] text-muted-foreground font-bold">
                          {envaseUnitLabel}
                        </span>
                      </span>
                    ))
                  )}
                </div>
              </td>
            );
          }

          if (col === "contenido_total") {
            const hasDrenado =
              p.contenido_drenado && Number(p.contenido_drenado) > 0;
            const drenadoVal = hasDrenado
              ? Number(p.contenido_drenado)
              : contNeto;
            return (
              <td key={col} className={tdClass}>
                <div className="flex flex-col gap-1 items-center">
                  {relevantBodegas.length === 0 ? (
                    <span className="text-[10px] text-muted-foreground">—</span>
                  ) : (
                    relevantBodegas.map((bc) => {
                      const bStock = bc.stock_actual ?? 0;
                      const totalEquiv = bStock * contNeto;
                      const totalDrenadoEquiv = bStock * drenadoVal;
                      const formattedContenido = formatEquivalenciaText(
                        totalEquiv,
                        baseUnitStr
                      );
                      const formattedDrenado = formatEquivalenciaText(
                        totalDrenadoEquiv,
                        baseUnitStr
                      );
                      return (
                        <div
                          key={bc.bodega_id}
                          className="h-7 flex flex-col items-center justify-center"
                        >
                          <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                            {formattedContenido}
                          </span>
                          {hasDrenado && (
                            <span className="text-[8px] font-bold text-emerald-700 dark:text-emerald-300">
                              💧 {formattedDrenado}
                            </span>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </td>
            );
          }

          if (col === "ubicacion") {
            return (
              <td key={col} className={tdClass}>
                <div className="flex flex-col gap-1.5 items-center">
                  {relevantBodegas.length === 0 ? (
                    <span className="text-[10px] text-muted-foreground">—</span>
                  ) : (
                    relevantBodegas.map((bc) => {
                      const coord = `${bc.coordenada_letra ?? ""}${bc.coordenada_numero ?? ""}`;
                      return (
                        <span
                          key={bc.bodega_id}
                          className="text-xs font-black text-foreground/80 uppercase h-7 flex items-center justify-center"
                        >
                          {coord || "—"}
                        </span>
                      );
                    })
                  )}
                </div>
              </td>
            );
          }

          // 💰 COSTOS DE COMPRA
          if (col === "ultimo_costo_unidad_neto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoUltimoUnidadNeto ? (
                  `${formatUnitCost(costoUltimoUnidadNeto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "ultimo_costo_unidad_bruto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoUltimoUnidadBruto ? (
                  `${formatUnitCost(costoUltimoUnidadBruto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "ultimo_costo_embalaje_neto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoUltimoEmbalajeNeto
                      ? formatMoney(Math.round(costoUltimoEmbalajeNeto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "ultimo_costo_embalaje_bruto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoUltimoEmbalajeBruto
                      ? formatMoney(Math.round(costoUltimoEmbalajeBruto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "penultimo_costo_unidad_neto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoPenultimoUnidadNeto ? (
                  `${formatUnitCost(costoPenultimoUnidadNeto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "penultimo_costo_unidad_bruto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoPenultimoUnidadBruto ? (
                  `${formatUnitCost(costoPenultimoUnidadBruto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "penultimo_costo_embalaje_neto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoPenultimoEmbalajeNeto
                      ? formatMoney(Math.round(costoPenultimoEmbalajeNeto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "penultimo_costo_embalaje_bruto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoPenultimoEmbalajeBruto
                      ? formatMoney(Math.round(costoPenultimoEmbalajeBruto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "variacion_costo") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                {varPercent !== null ? (
                  <span
                    data-testid={`inflation-badge-${p.id}`}
                    className={cn(
                      "text-[11px] font-black tabular-nums px-2 py-0.5 rounded-full inline-flex items-center gap-1",
                      varPercent > 0
                        ? "bg-red-500/10 text-red-500"
                        : varPercent < 0
                        ? "bg-emerald-500/10 text-emerald-500"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {varPercent > 0
                      ? `🔴 +${varPercent.toFixed(1)}%`
                      : varPercent < 0
                      ? `🟢 ${varPercent.toFixed(1)}%`
                      : "0%"}
                  </span>
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "costo_prom_inv_unidad_neto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoPromInvUnidadNeto ? (
                  `${formatUnitCost(costoPromInvUnidadNeto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "costo_prom_inv_unidad_bruto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoPromInvUnidadBruto ? (
                  `${formatUnitCost(costoPromInvUnidadBruto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "costo_prom_inv_embalaje_neto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoPromInvEmbalajeNeto
                      ? formatMoney(Math.round(costoPromInvEmbalajeNeto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "costo_prom_inv_embalaje_bruto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoPromInvEmbalajeBruto
                      ? formatMoney(Math.round(costoPromInvEmbalajeBruto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "costo_prom_hist_unidad_neto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoPromHistUnidadNeto ? (
                  `${formatUnitCost(costoPromHistUnidadNeto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "costo_prom_hist_unidad_bruto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-foreground/90"
                )}
              >
                {costoPromHistUnidadBruto ? (
                  `${formatUnitCost(costoPromHistUnidadBruto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "costo_prom_hist_embalaje_neto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoPromHistEmbalajeNeto
                      ? formatMoney(Math.round(costoPromHistEmbalajeNeto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          if (col === "costo_prom_hist_embalaje_bruto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <div className="flex flex-col items-center justify-center">
                  <span className="text-xs font-black tabular-nums text-foreground/90">
                    {costoPromHistEmbalajeBruto
                      ? formatMoney(Math.round(costoPromHistEmbalajeBruto))
                      : "—"}
                  </span>
                  <span className="text-[8px] font-bold text-muted-foreground truncate max-w-[120px]">
                    {presName}
                  </span>
                </div>
              </td>
            );
          }

          // 🏷️ VENTAS Y MÁRGENES
          if (col === "precio_venta_neto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-primary"
                )}
              >
                {pvNeto ? (
                  `${formatUnitCost(pvNeto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "precio_venta_bruto") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-black tabular-nums text-primary"
                )}
              >
                {pvBruto ? (
                  `${formatUnitCost(pvBruto)} / ${envaseUnitLabel}`
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "margen_bruto" || col === "margen_neto") {
            const mVal = col === "margen_bruto" ? margenBrutoVal : margenNetoVal;
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                {mVal !== null ? (
                  <div className="flex flex-col items-center justify-center gap-0.5">
                    <span
                      className={cn(
                        "text-[11px] font-black tabular-nums px-2 py-0.5 rounded-full",
                        mVal >= 40
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                          : mVal >= 20
                          ? "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400"
                          : "bg-red-500/15 text-red-500"
                      )}
                    >
                      {mVal.toFixed(1)}%
                    </span>
                    {foodCostVal !== null && (
                      <span className="text-[8px] font-bold text-muted-foreground/70">
                        FC: {foodCostVal.toFixed(1)}%
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="text-[10px] text-muted-foreground font-normal">
                    —
                  </span>
                )}
              </td>
            );
          }

          if (col === "valor_inventario_neto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                  {valorInvTotalNeto > 0 ? formatMoney(valorInvTotalNeto) : "$0"}
                </span>
              </td>
            );
          }

          if (col === "valor_inventario_bruto") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                  {valorInvTotalBruto > 0 ? formatMoney(valorInvTotalBruto) : "$0"}
                </span>
              </td>
            );
          }

          // ⏳ ROTACIÓN Y AUTONOMÍA
          if (col === "dias_cobertura") {
            return (
              <td key={col} className={cn(tdClass, "text-center")}>
                <span
                  className={cn(
                    "text-[10px] font-bold px-2 py-0.5 rounded-full inline-block",
                    daysCov >= 15
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : daysCov >= 7
                      ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
                      : "bg-red-500/10 text-red-500"
                  )}
                >
                  {daysCov} días
                </span>
              </td>
            );
          }

          if (col === "indice_rotacion") {
            return (
              <td
                key={col}
                className={cn(
                  tdClass,
                  "text-center text-xs font-bold text-foreground/80 tabular-nums"
                )}
              >
                {rotIndex > 0 ? `${rotIndex.toFixed(1)}x / mes` : "0x / mes"}
              </td>
            );
          }

          return null;
        })}

        {/* Columna Fija: Acciones */}
        <td className={cn(tdClass, "text-center border-r rounded-r-xl w-24")}>
          <div className="flex justify-center items-center gap-1">
            <Can perform="catalog.products.edit">
              <button
                type="button"
                data-testid={`edit-product-btn-${p.id}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit?.(p);
                }}
                className="rounded-lg p-1.5 hover:bg-yellow-500/10 text-muted-foreground hover:text-yellow-600 dark:hover:text-yellow-400 transition-colors cursor-pointer"
                aria-label={`Editar ${p.nombre}`}
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </Can>

            <Can perform="catalog.products.delete">
              <button
                type="button"
                data-testid={`delete-product-btn-${p.id}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setProductToDelete(p);
                }}
                className="rounded-lg p-1.5 hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors cursor-pointer"
                aria-label={`Eliminar ${p.nombre}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </Can>
          </div>
        </td>
      </tr>
    );
  };

  return (
    <div
      data-testid="product-table-root"
      className={cn("w-full space-y-4", className)}
    >
      {/* MODO AGRUPADO POR CATEGORÍAS */}
      {isGrouped ? (
        groupedCategories.map(({ categoria, productos: catProducts }) => {
          const isCollapsed = effectiveCollapsed.has(categoria.id);

          return (
            <div
              key={categoria.id}
              data-testid={`category-group-${categoria.id}`}
              className="space-y-1"
            >
              {/* Barra de Categoría Colapsable */}
              <div
                data-testid={`category-header-${categoria.id}`}
                onClick={() => handleToggleCat(categoria.id)}
                className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-card/40 hover:bg-secondary/40 border border-border/30 cursor-pointer select-none transition-all"
              >
                <ChevronDown
                  className={cn(
                    "h-4 w-4 text-muted-foreground transition-transform duration-200",
                    isCollapsed && "-rotate-90"
                  )}
                />
                <div
                  className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-bold"
                  style={{
                    backgroundColor: categoria.color
                      ? `${categoria.color}20`
                      : "transparent",
                    color: categoria.color || undefined,
                  }}
                >
                  <CategoryIcon
                    name={categoria.icono}
                    className="h-3.5 w-3.5 shrink-0"
                  />
                  <span>{categoria.nombre}</span>
                </div>
                <span
                  data-testid={`category-count-${categoria.id}`}
                  className="px-2 py-0.5 rounded-full bg-secondary text-muted-foreground text-[10px] font-extrabold"
                >
                  {catProducts.length} {catProducts.length === 1 ? "producto" : "productos"}
                </span>
                <div className="h-[1px] flex-1 bg-gradient-to-r from-border/50 to-transparent" />
              </div>

              {/* Tabla de Productos de la Categoría */}
              {!isCollapsed && (
                <CategoryTableWrapper
                  catId={categoria.id}
                  activeCols={activeColDefs}
                  minTableWidth={minTableWidth}
                  columnWidths={COLUMN_WIDTHS}
                  getColWidthPx={getColWidthPx}
                  onHorizontalScroll={handleHorizontalScroll}
                  registerContainer={registerContainer}
                >
                  {catProducts.map((p) => renderRow(p))}
                </CategoryTableWrapper>
              )}
            </div>
          );
        })
      ) : (
        /* MODO SIMPLE (Lista Continua Plana) */
        <div data-testid="product-table-simple">
          <CategoryTableWrapper
            catId="simple-all"
            activeCols={activeColDefs}
            minTableWidth={minTableWidth}
            columnWidths={COLUMN_WIDTHS}
            getColWidthPx={getColWidthPx}
            onHorizontalScroll={handleHorizontalScroll}
            registerContainer={registerContainer}
          >
            {productos.map((p) => renderRow(p))}
          </CategoryTableWrapper>
        </div>
      )}

      {/* ResponsiveDialog de Confirmación de Eliminación */}
      <ResponsiveDialog
        open={Boolean(productToDelete)}
        onClose={() => setProductToDelete(null)}
        title="Confirmar Eliminación"
        description="Esta acción eliminará el producto del catálogo."
      >
        <div className="space-y-4 pt-2">
          <p className="text-sm text-foreground">
            ¿Estás seguro de que deseas eliminar permanentemente el producto{" "}
            <span className="font-bold text-destructive">
              {productToDelete?.nombre}
            </span>
            ? Esta operación no se puede deshacer.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setProductToDelete(null)}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-semibold text-secondary-foreground hover:bg-secondary/80 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              data-testid="confirm-delete-btn"
              onClick={() => {
                if (productToDelete) {
                  onDelete?.(productToDelete);
                  setProductToDelete(null);
                }
              }}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-xl bg-destructive px-4 py-2 text-xs font-semibold text-destructive-foreground hover:bg-destructive/90 transition-colors"
            >
              Eliminar Producto
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
};

export default ProductTable;
