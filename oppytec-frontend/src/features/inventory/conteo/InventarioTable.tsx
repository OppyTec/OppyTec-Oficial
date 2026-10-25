// oppytec-frontend/src/features/inventory/conteo/InventarioTable.tsx
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Trash2,
  PackageCheck,
} from "lucide-react";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import type { ConteoItemDraft } from "../types";

export interface CatalogProduct {
  id: number;
  nombre: string;
  sku?: string;
  categoria?: string;
  categoria_color?: string;
  categoria_icono?: string;
  unidad_medida?: string;
  costo_unitario_ppp?: number;
  no_perecible?: boolean;
}

export interface InventarioTableProps {
  readonly items: ConteoItemDraft[];
  readonly productos: CatalogProduct[];
  readonly onUpdate: (localId: string, field: keyof ConteoItemDraft, value: any) => void;
  readonly onRemove: (localId: string) => void;
}

export function InventarioTable({
  items,
  productos,
  onUpdate,
  onRemove,
}: InventarioTableProps) {
  const { t } = useTranslation("inventory");
  const [isMobile, setIsMobile] = useState<boolean>(false);

  useEffect(() => {
    const checkMobile = () => {
      const hasTouch =
        typeof window !== "undefined" && typeof window.matchMedia === "function"
          ? window.matchMedia("(pointer: coarse)").matches
          : false;
      const isSmall = typeof window !== "undefined" ? window.innerWidth < 768 : false;
      setIsMobile(hasTouch || isSmall);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const handleQuickAdd = (localId: string, currentVal: number, delta: number) => {
    const next = Math.max(0, Number((currentVal + delta).toFixed(2)));
    onUpdate(localId, "stock_fisico_contado", next);
  };

  const findProduct = (productoId: number): CatalogProduct | undefined => {
    return productos.find((p) => p.id === productoId);
  };

  return (
    <div
      data-testid="inventario-table-wrapper"
      className="border border-border/80 rounded-2xl overflow-hidden bg-card/60 backdrop-blur-md shadow-xl"
    >
      {/* =========================================================================
          DESKTOP TABLE VIEW (>= 768px)
          ========================================================================= */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead className="bg-muted/50 border-b border-border">
            <tr className="text-[10px] font-black uppercase tracking-wider text-muted-foreground select-none">
              <th className="p-3.5 pl-5 text-left min-w-[220px]">
                {t("conteo.table.col_product", "Producto / Insumo")}
              </th>
              <th className="p-3.5 text-center w-28">
                {t("conteo.table.col_unit", "Unidad")}
              </th>
              <th className="p-3.5 text-center min-w-[280px]">
                {t("conteo.table.col_counted", "Cantidad Contada")}
              </th>
              <th className="p-3.5 text-center min-w-[200px]">
                {t("conteo.table.col_lot_expiry", "Lote & Vencimiento")}
              </th>
              <th className="p-3.5 w-14 text-center">
                {t("conteo.table.col_action", "Acción")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {items.map((item) => {
              const prod = findProduct(item.producto_id);
              const isNoPerecible = prod?.no_perecible === true;
              const unit = item.unidad_medida || prod?.unidad_medida || "unidades";

              return (
                <tr
                  key={item.localId}
                  data-testid={`conteo-row-${item.producto_id}`}
                  className="hover:bg-accent/40 transition-colors group"
                >
                  {/* Columna 1: Producto con icono gastronómico y SKU */}
                  <td className="p-3.5 pl-5 font-medium text-foreground">
                    <div className="flex items-center gap-3">
                      <div
                        className="h-9 w-9 rounded-xl flex items-center justify-center shrink-0 border border-border/60 shadow-xs"
                        style={{
                          backgroundColor: prod?.categoria_color
                            ? `${prod.categoria_color}20`
                            : "var(--primary-10, rgba(16, 185, 129, 0.1))",
                          color: prod?.categoria_color || "#10b981",
                        }}
                      >
                        <CategoryIcon
                          name={prod?.categoria_icono || "package"}
                          className="h-4 w-4"
                        />
                      </div>
                      <div className="min-w-0">
                        <div className="font-bold text-sm text-foreground truncate">
                          {item.producto_nombre || prod?.nombre || `Producto #${item.producto_id}`}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          {prod?.sku && (
                            <span className="font-mono text-[10px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/40">
                              {prod.sku}
                            </span>
                          )}
                          {prod?.categoria && (
                            <span className="text-[10px] font-semibold text-muted-foreground truncate">
                              {prod.categoria}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Columna 2: Unidad de Medida */}
                  <td className="p-3.5 text-center">
                    <span className="inline-flex items-center px-2 py-1 rounded-lg bg-secondary text-secondary-foreground font-mono font-bold text-xs uppercase">
                      {unit}
                    </span>
                  </td>

                  {/* Columna 3: Cantidad Contada con Botones de Incremento Rápido */}
                  <td className="p-3.5 text-center">
                    <div className="flex flex-col items-center justify-center gap-1.5">
                      <div className="flex items-center justify-center gap-1">
                        <input
                          type="number"
                          step="any"
                          min="0"
                          aria-label={t("conteo.table.aria_qty_for", {
                            name: item.producto_nombre,
                            defaultValue: `Cantidad para ${item.producto_nombre}`,
                          })}
                          data-testid={`conteo-qty-${item.producto_id}`}
                          value={item.stock_fisico_contado}
                          onChange={(e) => {
                            const val = e.target.value === "" ? 0 : Number(e.target.value);
                            onUpdate(item.localId, "stock_fisico_contado", Math.max(0, val));
                          }}
                          onFocus={(e) => e.target.select()}
                          className="touch-target h-10 w-28 text-center bg-background border border-border rounded-xl font-mono text-base font-black text-foreground shadow-inner focus:outline-none focus:ring-2 focus:ring-primary/40"
                        />
                      </div>

                      {/* Botones de incremento rápido (+1, +5, +10) */}
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 1)}
                          className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-secondary hover:bg-secondary/80 text-secondary-foreground border border-border transition-colors cursor-pointer"
                          title={t("conteo.table.quick_add_1", "Sumar 1 unidad")}
                          aria-label={t("conteo.table.quick_add_1", "Sumar 1 unidad")}
                        >
                          +1
                        </button>
                        <button
                          type="button"
                          onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 5)}
                          className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-secondary hover:bg-secondary/80 text-secondary-foreground border border-border transition-colors cursor-pointer"
                          title={t("conteo.table.quick_add_5", "Sumar 5 unidades")}
                          aria-label={t("conteo.table.quick_add_5", "Sumar 5 unidades")}
                        >
                          +5
                        </button>
                        <button
                          type="button"
                          onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 10)}
                          className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-secondary hover:bg-secondary/80 text-secondary-foreground border border-border transition-colors cursor-pointer"
                          title={t("conteo.table.quick_add_10", "Sumar 10 unidades")}
                          aria-label={t("conteo.table.quick_add_10", "Sumar 10 unidades")}
                        >
                          +10
                        </button>
                      </div>
                    </div>
                  </td>

                  {/* Columna 4: Lote y Fecha de Vencimiento */}
                  <td className="p-3.5 text-center">
                    {isNoPerecible ? (
                      <span className="text-muted-foreground font-extrabold text-xs block py-1">
                        {t("conteo.table.non_perishable", "— No perecible —")}
                      </span>
                    ) : (
                      <div className="flex flex-col gap-1.5 max-w-[190px] mx-auto">
                        <input
                          type="text"
                          aria-label={t("conteo.table.lot_placeholder", "Lote (opcional)")}
                          placeholder={t("conteo.table.lot_placeholder", "Lote (opcional)")}
                          value={item.lote_codigo ?? ""}
                          onChange={(e) =>
                            onUpdate(item.localId, "lote_codigo", e.target.value || null)
                          }
                          className="h-8 px-2 text-center rounded-lg border border-border bg-background text-xs font-mono placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                        <div className="relative">
                          <input
                            type="date"
                            aria-label={t("conteo.table.expiry_label", "Vencimiento")}
                            value={item.fecha_vencimiento ?? ""}
                            readOnly={isMobile}
                            onChange={(e) =>
                              onUpdate(item.localId, "fecha_vencimiento", e.target.value || null)
                            }
                            onClick={(e) => {
                              try {
                                e.currentTarget.showPicker();
                              } catch {
                                // fallback en navegadores antiguos
                              }
                            }}
                            className="h-8 w-full rounded-lg border border-border bg-background text-xs text-center cursor-pointer text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>
                    )}
                  </td>

                  {/* Columna 5: Botón Eliminar */}
                  <td className="p-3.5 text-center">
                    <button
                      type="button"
                      aria-label={t("conteo.table.aria_delete_for", {
                        name: item.producto_nombre,
                        defaultValue: `Eliminar ${item.producto_nombre}`,
                      })}
                      data-testid={`conteo-delete-${item.producto_id}`}
                      onClick={() => onRemove(item.localId)}
                      className="touch-target inline-flex items-center justify-center h-9 w-9 text-destructive hover:bg-destructive/10 rounded-xl transition-colors cursor-pointer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              );
            })}

            {items.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="p-8 text-center text-muted-foreground italic font-medium"
                >
                  <div className="flex flex-col items-center justify-center gap-2">
                    <PackageCheck className="h-8 w-8 text-muted-foreground/50" />
                    <p>{t("conteo.table.empty_table", "No hay productos en la lista de recuento.")}</p>
                    <p className="text-xs text-muted-foreground/80">
                      {t("conteo.table.empty_hint", "Usa el buscador o escanea un código de barras para comenzar.")}
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* =========================================================================
          MOBILE-FIRST CARDS (< 768px)
          ========================================================================= */}
      <div className="md:hidden divide-y divide-border/60">
        {items.map((item) => {
          const prod = findProduct(item.producto_id);
          const isNoPerecible = prod?.no_perecible === true;
          const unit = item.unidad_medida || prod?.unidad_medida || "unidades";

          return (
            <div
              key={item.localId}
              data-testid={`conteo-card-${item.producto_id}`}
              className="p-4 space-y-3 bg-card/40"
            >
              {/* Cabecera de la tarjeta: Nombre, Icono y Botón Eliminar */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0 border border-border/60"
                    style={{
                      backgroundColor: prod?.categoria_color
                        ? `${prod.categoria_color}20`
                        : "rgba(16, 185, 129, 0.1)",
                      color: prod?.categoria_color || "#10b981",
                    }}
                  >
                    <CategoryIcon
                      name={prod?.categoria_icono || "package"}
                      className="h-5 w-5"
                    />
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-sm text-foreground truncate">
                      {item.producto_nombre || prod?.nombre || `Producto #${item.producto_id}`}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {prod?.sku && (
                        <span className="font-mono text-[10px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/40">
                          {prod.sku}
                        </span>
                      )}
                      <span className="text-[10px] font-bold text-primary uppercase">
                        {unit}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  aria-label={t("conteo.table.aria_delete_for", {
                    name: item.producto_nombre,
                    defaultValue: `Eliminar ${item.producto_nombre}`,
                  })}
                  onClick={() => onRemove(item.localId)}
                  className="touch-target h-10 w-10 inline-flex items-center justify-center text-destructive hover:bg-destructive/10 rounded-xl transition-colors shrink-0"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              {/* Controles de Conteo Numérico Táctil */}
              <div className="bg-background/80 p-3 rounded-xl border border-border/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    {t("conteo.table.col_counted", "Cantidad Contada")}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      aria-label="Restar 1"
                      onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, -1)}
                      className="touch-target h-9 w-9 inline-flex items-center justify-center rounded-lg bg-secondary text-secondary-foreground font-black text-sm border border-border"
                    >
                      -
                    </button>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      aria-label={t("conteo.table.aria_qty_for", {
                        name: item.producto_nombre,
                        defaultValue: `Cantidad para ${item.producto_nombre}`,
                      })}
                      value={item.stock_fisico_contado}
                      onChange={(e) => {
                        const val = e.target.value === "" ? 0 : Number(e.target.value);
                        onUpdate(item.localId, "stock_fisico_contado", Math.max(0, val));
                      }}
                      className="touch-target h-9 w-20 text-center bg-card border border-border rounded-lg font-mono text-base font-black text-foreground shadow-inner focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      type="button"
                      aria-label="Sumar 1"
                      onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 1)}
                      className="touch-target h-9 w-9 inline-flex items-center justify-center rounded-lg bg-secondary text-secondary-foreground font-black text-sm border border-border"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Acciones de Incremento Rápido Táctiles */}
                <div className="flex items-center justify-end gap-1.5 pt-1 border-t border-border/40">
                  <span className="text-[10px] text-muted-foreground mr-auto font-medium">
                    {t("conteo.table.quick_shortcuts", "Atajos rápidos:")}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 1)}
                    className="touch-target min-h-[36px] px-2.5 rounded-lg bg-secondary text-xs font-bold text-secondary-foreground border border-border"
                  >
                    +1
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 5)}
                    className="touch-target min-h-[36px] px-2.5 rounded-lg bg-secondary text-xs font-bold text-secondary-foreground border border-border"
                  >
                    +5
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickAdd(item.localId, item.stock_fisico_contado, 10)}
                    className="touch-target min-h-[36px] px-2.5 rounded-lg bg-secondary text-xs font-bold text-secondary-foreground border border-border"
                  >
                    +10
                  </button>
                </div>
              </div>

              {/* Lote y Vencimiento */}
              {!isNoPerecible && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="text-[10px] font-bold text-muted-foreground block mb-1">
                      {t("conteo.table.lot_label", "Lote (opcional)")}
                    </label>
                    <input
                      type="text"
                      aria-label={t("conteo.table.lot_label", "Lote (opcional)")}
                      placeholder={t("conteo.table.lot_mobile_placeholder", "Lote #")}
                      value={item.lote_codigo ?? ""}
                      onChange={(e) =>
                        onUpdate(item.localId, "lote_codigo", e.target.value || null)
                      }
                      className="touch-target h-9 w-full px-2 rounded-lg border border-border bg-background text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-muted-foreground block mb-1">
                      {t("conteo.table.expiry_label", "Vencimiento")}
                    </label>
                    <input
                      type="date"
                      aria-label={t("conteo.table.expiry_label", "Vencimiento")}
                      value={item.fecha_vencimiento ?? ""}
                      onChange={(e) =>
                        onUpdate(item.localId, "fecha_vencimiento", e.target.value || null)
                      }
                      className="touch-target h-9 w-full px-2 rounded-lg border border-border bg-background text-xs"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {items.length === 0 && (
          <div className="p-8 text-center text-muted-foreground italic font-medium space-y-2">
            <PackageCheck className="h-8 w-8 mx-auto text-muted-foreground/50" />
            <p>{t("conteo.table.empty_table", "No hay productos en la lista de recuento.")}</p>
            <p className="text-xs text-muted-foreground/80">
              {t("conteo.table.mobile_add_hint", "Añade un producto desde el buscador superior.")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
