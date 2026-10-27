/**
 * oppytec-frontend/src/features/procurement/components/CatalogoPrecios.tsx
 * Catálogo Comparativo de Precios Pactados e Insumos con Proveedores.
 * Formateo Decimal FX, búsqueda en tiempo real y respeto estricto de la regla comercial ("Pollo King").
 */

import { useState, useMemo } from "react";
import { Search, Tag, CheckCircle2, Clock, Filter, Building2 } from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { ProductoProveedor, Proveedor } from "../types";
import { MOCK_PRODUCTOS_PROVEEDOR, MOCK_PROVEEDORES } from "../mockData";

export interface CatalogoPreciosProps {
  readonly proveedores?: Proveedor[];
  readonly items?: ProductoProveedor[];
  readonly onSelectProducto?: (item: ProductoProveedor) => void;
}

export function CatalogoPrecios({
  proveedores = MOCK_PROVEEDORES,
  items,
  onSelectProducto,
}: CatalogoPreciosProps) {
  const { format } = useCurrencyFormatter();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSupplierId, setSelectedSupplierId] = useState<number | "ALL">("ALL");

  // Si no se pasaron items, agregamos los de todos los proveedores conocidos
  const allItems: ProductoProveedor[] = useMemo(() => {
    if (items && items.length > 0) return items;
    const aggregated: ProductoProveedor[] = [];
    Object.values(MOCK_PRODUCTOS_PROVEEDOR).forEach((arr) => {
      aggregated.push(...arr);
    });
    return aggregated;
  }, [items]);

  // Mapa de nombres de proveedores
  const supplierNameMap = useMemo(() => {
    const map = new Map<number, string>();
    proveedores.forEach((p) => {
      map.set(p.id, p.nombre_fantasia || p.razon_social);
    });
    return map;
  }, [proveedores]);

  // Filtrado reactivo
  const filteredItems = useMemo(() => {
    return allItems.filter((item) => {
      const matchSupplier =
        selectedSupplierId === "ALL" || item.proveedor_id === selectedSupplierId;

      const term = searchTerm.toLowerCase().trim();
      const matchSearch =
        !term ||
        (item.producto_nombre && item.producto_nombre.toLowerCase().includes(term)) ||
        (item.producto_sku && item.producto_sku.toLowerCase().includes(term)) ||
        (item.codigo_producto_proveedor &&
          item.codigo_producto_proveedor.toLowerCase().includes(term));

      return matchSupplier && matchSearch;
    });
  }, [allItems, selectedSupplierId, searchTerm]);

  return (
    <div data-testid="catalogo-precios" className="space-y-4">
      {/* Barra de Filtros y Búsqueda */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            data-testid="catalogo-search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar insumo por nombre, SKU o código de proveedor..."
            className="touch-target w-full rounded-xl border border-border bg-card py-2.5 pl-9 pr-4 text-xs text-foreground placeholder:text-muted-foreground shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary min-h-[44px]"
          />
        </div>

        {/* Filtro por Proveedor */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
          <select
            data-testid="catalogo-supplier-filter"
            value={selectedSupplierId}
            onChange={(e) =>
              setSelectedSupplierId(
                e.target.value === "ALL" ? "ALL" : Number(e.target.value)
              )
            }
            className="touch-target rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground shadow-sm focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
          >
            <option value="ALL">Todos los Proveedores</option>
            {proveedores.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre_fantasia || p.razon_social}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabla de Insumos y Precios */}
      <div className="glass-card overflow-hidden rounded-2xl border border-border shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-foreground">
            <thead className="border-b border-border bg-muted/40 uppercase tracking-wider text-muted-foreground">
              <tr>
                <th scope="col" className="px-4 py-3.5 font-semibold">
                  Insumo / Producto
                </th>
                <th scope="col" className="px-4 py-3.5 font-semibold">
                  SKU / Cód. Proveedor
                </th>
                <th scope="col" className="px-4 py-3.5 font-semibold">
                  Proveedor Asignado
                </th>
                <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                  Último Costo Neto
                </th>
                <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                  Precio Pactado
                </th>
                <th scope="col" className="px-4 py-3.5 text-center font-semibold">
                  Lead Time
                </th>
                <th scope="col" className="px-4 py-3.5 text-center font-semibold">
                  Estado Contrato
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-muted-foreground">
                    No se encontraron insumos que coincidan con la búsqueda.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item, idx) => {
                  const supplierName =
                    supplierNameMap.get(item.proveedor_id) || `Proveedor #${item.proveedor_id}`;
                  const key = item.id ? `cat-item-${item.id}` : `cat-item-${idx}`;

                  return (
                    <tr
                      key={key}
                      data-testid={`catalogo-row-${item.producto_nombre?.replace(/\s+/g, "-").toLowerCase()}`}
                      onClick={() => onSelectProducto?.(item)}
                      className={`transition-colors hover:bg-muted/30 ${
                        onSelectProducto ? "cursor-pointer" : ""
                      }`}
                    >
                      {/* Nombre Insumo */}
                      <td className="px-4 py-3 font-semibold text-foreground">
                        <div className="flex items-center gap-2">
                          <Tag className="h-3.5 w-3.5 text-primary shrink-0" />
                          <span className="truncate max-w-[220px]" title={item.producto_nombre || ""}>
                            {item.producto_nombre}
                          </span>
                        </div>
                      </td>

                      {/* SKU / Código */}
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted-foreground">
                        <div>{item.producto_sku || "—"}</div>
                        {item.codigo_producto_proveedor && (
                          <div className="text-[10px] text-primary/80">
                            Cód: {item.codigo_producto_proveedor}
                          </div>
                        )}
                      </td>

                      {/* Proveedor */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <Building2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <span className="font-medium text-foreground truncate max-w-[180px]" title={supplierName}>
                            {supplierName}
                          </span>
                        </div>
                      </td>

                      {/* Último Costo Neto */}
                      <td className="whitespace-nowrap px-4 py-3 text-right font-medium text-muted-foreground">
                        {item.ultimo_costo_neto ? format(item.ultimo_costo_neto) : "—"}
                      </td>

                      {/* Precio Pactado */}
                      <td className="whitespace-nowrap px-4 py-3 text-right font-bold text-foreground">
                        {item.precio_pactado ? format(item.precio_pactado) : "—"}
                      </td>

                      {/* Lead Time */}
                      <td className="whitespace-nowrap px-4 py-3 text-center text-muted-foreground">
                        <div className="flex items-center justify-center gap-1">
                          <Clock className="h-3.5 w-3.5 shrink-0" />
                          <span>{item.tiempo_entrega_dias ?? "—"} d</span>
                        </div>
                      </td>

                      {/* Principal Badge */}
                      <td className="whitespace-nowrap px-4 py-3 text-center">
                        {item.es_proveedor_principal ? (
                          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="h-3 w-3" />
                            Principal
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                            Alternativo
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
