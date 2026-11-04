/**
 * oppytec-frontend/src/features/invoices/components/FacturaReviewGrid.tsx
 * Grilla interactiva de 13 columnas para revisión de empaque mayorista,
 * conversión a stock real de cocina, radar de price drift y memorización de aliases.
 * Cumple con ADN Visual Legacy, sticky headers y soporte responsive Mobile-First.
 */

import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Sparkles,
  CheckCircle2,
  HelpCircle,
  Search,
  Package,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react";
import { formatMoney, formatUnitCost, cn } from "@/shared/lib";
import { UnidadMedidaCombobox } from "./UnidadMedidaCombobox";
import {
  MOCK_CATEGORIES,
  MOCK_WAREHOUSES,
  MOCK_CATALOG_PRODUCTS,
} from "../mockData";
import type {
  CategoryOption,
  InvoiceLineItem,
  ProductCatalogOption,
  WarehouseOption,
} from "../types";

export interface FacturaReviewGridProps {
  items: InvoiceLineItem[];
  onChangeItems: (items: InvoiceLineItem[]) => void;
  categories?: CategoryOption[];
  warehouses?: WarehouseOption[];
  catalogProducts?: ProductCatalogOption[];
  className?: string;
}

export function FacturaReviewGrid({
  items,
  onChangeItems,
  categories = MOCK_CATEGORIES,
  warehouses = MOCK_WAREHOUSES,
  catalogProducts = MOCK_CATALOG_PRODUCTS,
  className,
}: FacturaReviewGridProps) {
  const { t } = useTranslation(["invoices"]);
  const [filterText, setFilterText] = useState("");

  const handleRowChange = (index: number, updates: Partial<InvoiceLineItem>) => {
    const updated = [...items];
    const prevRow = updated[index];
    if (!prevRow) return;

    const row: InvoiceLineItem = { ...prevRow, ...updates };

    const cantidad = Math.max(0.001, Number(row.quantity) || 1);
    const unitPriceNet = Math.max(0, Number(row.unit_price_net) || 0);

    // Si cambió cantidad o precio neto, recalcular total neto
    if ("quantity" in updates || "unit_price_net" in updates) {
      row.total_net = Math.round(cantidad * unitPriceNet);
    }

    const currentTotalNet = row.total_net ?? Math.round(cantidad * unitPriceNet);

    // Recálculo según campo editado:
    if ("total_stock_fisico" in updates) {
      // Ajuste directo de balanza física
      const stock = Math.max(0.001, Number(updates.total_stock_fisico) || 0.001);
      row.total_stock_fisico = stock;
      row.factor_empaque = Math.round((stock / cantidad) * 1000) / 1000;
      row.costo_unitario_inventario = Math.round((currentTotalNet / stock) * 100) / 100;
    } else if (
      "factor_empaque" in updates ||
      "quantity" in updates ||
      "unit_price_net" in updates
    ) {
      const factor = Math.max(0.001, Number(row.factor_empaque) || 1);
      row.factor_empaque = factor;
      const stock = Math.round(cantidad * factor * 1000) / 1000;
      row.total_stock_fisico = stock;
      row.costo_unitario_inventario =
        stock > 0 ? Math.round((currentTotalNet / stock) * 100) / 100 : unitPriceNet;
    }

    // Si cambió producto asignado desde el catálogo
    if ("matched_product_id" in updates && updates.matched_product_id) {
      const prod = catalogProducts.find((p) => p.id === updates.matched_product_id);
      if (prod) {
        row.matched_product_name = prod.nombre;
        row.matched_product_sku = prod.sku;
        row.nombre_negocio = prod.nombre;
        row.categoria_id = prod.categoria_id;
        row.kitchen_base_unit = prod.unidad_inventario;
        row.ultimo_costo_referencia = prod.costo_unitario_ultimo;
        row.product_action = "use_existing";
        row.match_status = "exact_alias";

        // Calcular drift si existía costo previo
        const currentInventoryCost = row.costo_unitario_inventario ?? 0;
        if (prod.costo_unitario_ultimo > 0) {
          const varPct =
            ((currentInventoryCost - prod.costo_unitario_ultimo) /
              prod.costo_unitario_ultimo) *
            100;
          row.variacion_pct = Math.round(varPct * 10) / 10;
          row.drift_status =
            Math.abs(varPct) >= 20 ? "critical" : Math.abs(varPct) >= 10 ? "warning" : "normal";
        }
      }
    }

    updated[index] = row;
    onChangeItems(updated);
  };

  const filteredItemsWithIndex = useMemo(() => {
    return items
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => {
        if (!filterText) return true;
        const q = filterText.toLowerCase();
        return (
          item.raw_description.toLowerCase().includes(q) ||
          item.nombre_negocio.toLowerCase().includes(q) ||
          (item.matched_product_sku && item.matched_product_sku.toLowerCase().includes(q))
        );
      });
  }, [items, filterText]);

  const totals = useMemo(() => {
    return items.reduce(
      (acc, it) => {
        acc.net += it.total_net || 0;
        acc.stock += it.total_stock_fisico || 0;
        return acc;
      },
      { net: 0, stock: 0 }
    );
  }, [items]);

  return (
    <div
      data-testid="factura-review-grid"
      className={cn("glass-card rounded-2xl border border-border shadow-sm flex flex-col", className)}
    >
      {/* Barra superior de filtrado y resumen de líneas */}
      <div className="p-4 border-b border-border flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder={t("invoices:review_grid.filter_placeholder", "Filtrar líneas por descripción o producto...")}
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <span className="text-xs text-muted-foreground whitespace-nowrap hidden sm:inline">
            {filteredItemsWithIndex.length} de {items.length} ítems
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-xl bg-muted text-muted-foreground font-medium">
            {t("invoices:review_grid.total_lines_net", "Total Líneas Neto:")}{" "}
            <strong className="text-foreground">{formatMoney(totals.net)}</strong>
          </span>
        </div>
      </div>

      {/* Grilla con scroll horizontal y sticky headers */}
      <div className="overflow-x-auto overflow-y-auto max-h-[600px] relative">
        <table className="w-full text-left text-xs border-collapse min-w-[1250px]">
          <thead className="bg-muted/80 backdrop-blur sticky top-0 z-20 border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground select-none">
            <tr>
              <th className="py-2.5 px-2 text-center w-10">#</th>
              <th className="py-2.5 px-3 w-64 sticky left-0 z-30 bg-muted/95 backdrop-blur">
                {t("invoices:review_grid.col_invoice_item", "1. Ítem Factura / Empaque")}
              </th>
              <th className="py-2.5 px-2 text-center w-28">
                {t("invoices:review_grid.col_match", "2. Match")}
              </th>
              <th className="py-2.5 px-3 w-56">
                {t("invoices:review_grid.col_catalog_product", "3. Producto Negocio / Catálogo")}
              </th>
              <th className="py-2.5 px-2 w-36">
                {t("invoices:review_grid.col_category", "4. Categoría")}
              </th>
              <th className="py-2.5 px-2 w-36">
                {t("invoices:review_grid.col_warehouse", "5. Bodega Destino")}
              </th>
              <th className="py-2.5 px-2 text-right w-20">
                {t("invoices:review_grid.col_invoice_qty", "6. Cant. Factura")}
              </th>
              <th className="py-2.5 px-2 text-right w-24">
                {t("invoices:review_grid.col_net_price", "7. Precio Neto")}
              </th>
              <th className="py-2.5 px-2 text-right w-24">
                {t("invoices:review_grid.col_total_net", "8. Total Neto")}
              </th>
              <th className="py-2.5 px-2 text-right w-24">
                {t("invoices:review_grid.col_real_stock", "9. Stock Real")}
              </th>
              <th className="py-2.5 px-2 w-28">
                {t("invoices:review_grid.col_unit", "10. Unidad")}
              </th>
              <th className="py-2.5 px-2 text-right w-28">
                {t("invoices:review_grid.col_real_unit_cost", "11. Costo Unit. Real")}
              </th>
              <th className="py-2.5 px-2 text-center w-24">
                {t("invoices:review_grid.col_remember", "12. Recordar")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {filteredItemsWithIndex.map(({ item, index }) => {
              const rowNum = index + 1;

              return (
                <tr
                  key={item.id || `line-${index}`}
                  className="hover:bg-muted/30 transition-colors group"
                >
                  {/* 1. Contador # */}
                  <td className="py-3 px-2 text-center font-mono text-muted-foreground text-[11px]">
                    {rowNum}
                  </td>

                  {/* 2. Ítem Factura / Proveedor (Sticky Left) */}
                  <td className="py-3 px-3 sticky left-0 z-10 bg-background group-hover:bg-muted/30 transition-colors border-r border-border/40">
                    <p className="font-bold text-foreground leading-snug line-clamp-2">
                      {item.raw_description}
                    </p>
                    {item.packaging_description && (
                      <span className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded text-[10px] bg-primary/10 text-primary font-medium">
                        <Package className="h-2.5 w-2.5 shrink-0" />
                        {item.packaging_description}
                      </span>
                    )}
                    <span className="text-[10px] text-muted-foreground block mt-0.5">
                      {t("invoices:review_grid.doc_prefix", "Doc:")} {item.quantity} {item.unit_name}{" "}
                      {t("invoices:review_grid.vat_suffix", {
                        rate: Math.round(item.tax_rate * 100),
                        defaultValue: `• IVA ${Math.round(item.tax_rate * 100)}%`,
                      })}
                    </span>
                  </td>

                  {/* 3. Match Status */}
                  <td className="py-3 px-2 text-center">
                    {item.match_status === "exact_alias" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3" />
                        {t("invoices:review_grid.match_exact", "Alias Exacto")}
                      </span>
                    )}
                    {item.match_status === "suggested" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                        <Sparkles className="h-3 w-3" />
                        {t("invoices:review_grid.match_suggested", "Sugerido")}
                      </span>
                    )}
                    {item.match_status === "unmatched" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                        <HelpCircle className="h-3 w-3" />
                        {t("invoices:review_grid.match_new", "Nuevo")}
                      </span>
                    )}
                  </td>

                  {/* 4. Producto Negocio / Catálogo */}
                  <td className="py-3 px-3 space-y-1">
                    <div className="flex items-center gap-1">
                      <select
                        value={item.matched_product_id || ""}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === "create_new") {
                            handleRowChange(index, {
                              product_action: "create_new",
                              matched_product_id: null,
                              match_status: "unmatched",
                            });
                          } else {
                            handleRowChange(index, {
                              matched_product_id: val,
                            });
                          }
                        }}
                        className="w-full text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        <option value="">{t("invoices:review_grid.select_from_catalog", "-- Seleccionar de Catálogo --")}</option>
                        {catalogProducts.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.nombre} ({p.sku})
                          </option>
                        ))}
                        <option value="create_new">
                          {t("invoices:review_grid.create_new_product", "➕ Dar de alta nuevo producto")}
                        </option>
                      </select>
                    </div>
                    <input
                      type="text"
                      placeholder={t("invoices:review_grid.business_name_placeholder", "Nombre en negocio...")}
                      value={item.nombre_negocio}
                      onChange={(e) =>
                        handleRowChange(index, { nombre_negocio: e.target.value })
                      }
                      className="w-full text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </td>

                  {/* 5. Categoría */}
                  <td className="py-3 px-2">
                    <select
                      value={item.categoria_id}
                      onChange={(e) =>
                        handleRowChange(index, { categoria_id: e.target.value })
                      }
                      className="w-full text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* 6. Bodega Destino */}
                  <td className="py-3 px-2">
                    <select
                      value={item.bodega_id}
                      onChange={(e) =>
                        handleRowChange(index, { bodega_id: e.target.value })
                      }
                      className="w-full text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-medium"
                    >
                      {warehouses.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.nombre}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* 7. Cantidad Facturada */}
                  <td className="py-3 px-2 text-right">
                    <input
                      type="number"
                      step="any"
                      min="0.01"
                      value={item.quantity}
                      onChange={(e) =>
                        handleRowChange(index, {
                          quantity: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-16 text-right text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                    />
                  </td>

                  {/* 8. Precio Factura (Neto) */}
                  <td className="py-3 px-2 text-right">
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={item.unit_price_net}
                      onChange={(e) =>
                        handleRowChange(index, {
                          unit_price_net: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-20 text-right text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                    />
                  </td>

                  {/* 9. Total Neto */}
                  <td className="py-3 px-2 text-right font-mono font-semibold text-foreground">
                    {formatMoney(item.total_net)}
                  </td>

                  {/* 10. Stock Real Bodega */}
                  <td className="py-3 px-2 text-right">
                    <input
                      type="number"
                      step="any"
                      min="0.01"
                      title={t(
                        "invoices:review_grid.stock_title",
                        "Stock físico real a ingresar a inventario (modificable para ajuste de balanza)"
                      )}
                      value={item.total_stock_fisico}
                      onChange={(e) =>
                        handleRowChange(index, {
                          total_stock_fisico: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-20 text-right text-xs py-1 px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-mono font-bold text-primary"
                    />
                  </td>

                  {/* 11. Unidad Inventario */}
                  <td className="py-3 px-2">
                    <UnidadMedidaCombobox
                      value={item.kitchen_base_unit}
                      onChange={(unit) =>
                        handleRowChange(index, { kitchen_base_unit: unit })
                      }
                    />
                  </td>

                  {/* 12. Costo Real / Unid. con Price Drift Radar */}
                  <td className="py-3 px-2 text-right">
                    <div className="inline-flex flex-col items-end">
                      <span className="font-mono font-bold text-xs px-2 py-0.5 rounded-lg bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                        {formatUnitCost(item.costo_unitario_inventario)}
                      </span>
                      {item.variacion_pct !== undefined && item.variacion_pct !== null && (
                        <span
                          className={cn(
                            "inline-flex items-center gap-0.5 text-[10px] font-semibold mt-0.5",
                            item.variacion_pct > 0
                              ? item.variacion_pct >= 10
                                ? "text-rose-500"
                                : "text-amber-500"
                              : item.variacion_pct < 0
                              ? "text-emerald-500"
                              : "text-muted-foreground"
                          )}
                        >
                          {item.variacion_pct > 0 ? (
                            <ArrowUpRight className="h-2.5 w-2.5" />
                          ) : item.variacion_pct < 0 ? (
                            <ArrowDownRight className="h-2.5 w-2.5" />
                          ) : (
                            <Minus className="h-2.5 w-2.5" />
                          )}
                          {item.variacion_pct > 0 ? `+${item.variacion_pct}%` : `${item.variacion_pct}%`}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* 13. Recordar Alias */}
                  <td className="py-3 px-2 text-center">
                    <input
                      type="checkbox"
                      checked={item.remember_alias}
                      onChange={(e) =>
                        handleRowChange(index, { remember_alias: e.target.checked })
                      }
                      title={t(
                        "invoices:review_grid.remember_title",
                        "Memorizar alias de proveedor para próximas compras"
                      )}
                      className="h-4 w-4 rounded text-primary focus:ring-primary border-border cursor-pointer"
                    />
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
