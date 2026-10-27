/**
 * oppytec-frontend/src/features/procurement/dialogs/ProveedorProductosDialog.tsx
 * Modal de Gestión de Catálogo Pactado y Precios Acordados por Proveedor.
 * Respeto estricto a la Regla "Pollo King" y Formateo FX con precisión Decimal.
 */

import { useEffect, useState } from "react";
import { Plus, Save, Star, Trash2, Building2, Package, Clock } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useCurrencyFormatter } from "@/shared/currency";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { useProveedores } from "../hooks/useProveedores";
import type { ProductoProveedor, Proveedor, SupplierCatalogItemPayload } from "../types";

export interface ProveedorProductosDialogProps {
  readonly open: boolean;
  readonly proveedor: Proveedor | null;
  readonly onClose: () => void;
  readonly onSaved?: () => void;
}

export function ProveedorProductosDialog({
  open,
  proveedor,
  onClose,
  onSaved,
}: ProveedorProductosDialogProps) {
  const isMobile = useIsMobile();
  const { format } = useCurrencyFormatter();

  const {
    catalog,
    isLoadingCatalog,
    updateCatalog,
    isUpdatingCatalog,
  } = useProveedores(undefined, open && proveedor ? proveedor.id : null);

  // Estado local editable de la lista de productos
  const [items, setItems] = useState<ProductoProveedor[]>([]);

  // Formulario para añadir un nuevo insumo al catálogo
  const [newProductoNombre, setNewProductoNombre] = useState("");
  const [newCodigoProveedor, setNewCodigoProveedor] = useState("");
  const [newPrecioPactado, setNewPrecioPactado] = useState<string>("1000");
  const [newLeadTime, setNewLeadTime] = useState<number>(proveedor?.lead_time_dias ?? 2);
  const [newEsPrincipal, setNewEsPrincipal] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  // Sincronizar catálogo cuando se abre el modal o cambia el catálogo del proveedor activo
  useEffect(() => {
    if (!open || !proveedor) return;
    if (catalog && catalog.length > 0) {
      setItems([...catalog]);
    } else {
      setItems([]);
    }
    setShowAddForm(false);
  }, [catalog, open, proveedor]);

  if (!proveedor) return null;

  // Actualizar un campo individual de una fila
  const handleUpdateItem = <K extends keyof ProductoProveedor>(
    index: number,
    field: K,
    value: ProductoProveedor[K]
  ) => {
    setItems((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value } as ProductoProveedor;
      return copy;
    });
  };

  // Eliminar un producto del catálogo local
  const handleRemoveItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  // Añadir un nuevo producto a la lista local
  const handleAddProduct = () => {
    const trimmed = newProductoNombre.trim();
    if (!trimmed) return;

    const generatedId = Math.floor(Date.now() % 100000);
    const newItem: ProductoProveedor = {
      id: null,
      producto_id: generatedId,
      producto_nombre: trimmed,
      producto_sku: `INS-${trimmed.substring(0, 4).toUpperCase()}-${Math.floor(Math.random() * 900 + 100)}`,
      proveedor_id: proveedor.id,
      codigo_proveedor: newCodigoProveedor.trim() || null,
      codigo_producto_proveedor: newCodigoProveedor.trim() || null,
      ultimo_costo_neto: newPrecioPactado,
      precio_pactado: newPrecioPactado,
      tiempo_entrega_dias: Number(newLeadTime),
      es_proveedor_principal: newEsPrincipal,
    };

    setItems((prev) => [...prev, newItem]);
    setNewProductoNombre("");
    setNewCodigoProveedor("");
    setNewPrecioPactado("1000");
    setNewEsPrincipal(false);
    setShowAddForm(false);
  };

  // Guardar catálogo en backend
  const handleSaveCatalog = async () => {
    const payloadItems: SupplierCatalogItemPayload[] = items.map((it) => ({
      producto_id: it.producto_id,
      precio_pactado: it.precio_pactado ?? "0",
      codigo_producto_proveedor: it.codigo_producto_proveedor ?? it.codigo_proveedor ?? null,
      tiempo_entrega_dias: it.tiempo_entrega_dias,
      es_proveedor_principal: it.es_proveedor_principal,
    }));

    await updateCatalog({
      supplier_id: proveedor.id,
      items: payloadItems,
    });

    onSaved?.();
    onClose();
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      isMobile={isMobile}
      maxWidth="max-w-4xl"
      title={`Catálogo Pactado: ${proveedor.razon_social}`}
      description="Gestiona la lista de insumos pactados, precios acordados y condiciones de suministro."
    >
      <div className="flex flex-col gap-4 pt-2">
        {/* Cabecera resumen de proveedor */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-muted/40 p-3 text-xs">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" />
            <span className="font-semibold text-foreground">{proveedor.razon_social}</span>
            <span className="font-mono text-muted-foreground">({proveedor.rut_tax_id})</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Lead time estándar:</span>
            <span className="font-bold text-foreground">{proveedor.lead_time_dias} días</span>
          </div>
        </div>

        {/* Barra superior de catálogo */}
        <div className="flex items-center justify-between gap-2">
          <div className="text-xs font-semibold text-foreground">
            Insumos Registrados ({items.length})
          </div>
          <button
            type="button"
            onClick={() => setShowAddForm(!showAddForm)}
            data-testid="btn-add-product-toggle"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary/20 active:scale-95"
          >
            <Plus className="h-4 w-4" />
            <span>{showAddForm ? "Cancelar Nuevo" : "+ Agregar Insumo"}</span>
          </button>
        </div>

        {/* Formulario desplegable para agregar insumo */}
        {showAddForm && (
          <div
            data-testid="form-add-product"
            className="rounded-xl border border-primary/30 bg-primary/5 p-3.5 space-y-3"
          >
            <div className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <Package className="h-4 w-4 text-primary" />
              <span>Nuevo Insumo al Catálogo Pactado</span>
            </div>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-4">
              <div>
                <label className="mb-1 block text-[11px] font-semibold text-foreground">
                  Nombre del Insumo / Producto <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  data-testid="input-new-producto-nombre"
                  placeholder="ej. Pollo King o Harina Selecta"
                  value={newProductoNombre}
                  onChange={(e) => setNewProductoNombre(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold text-foreground">
                  Código Insumo (Proveedor)
                </label>
                <input
                  type="text"
                  data-testid="input-new-codigo-proveedor"
                  placeholder="ej. AF-POL-01"
                  value={newCodigoProveedor}
                  onChange={(e) => setNewCodigoProveedor(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold text-foreground">
                  Precio Pactado Neto ($)
                </label>
                <input
                  type="number"
                  data-testid="input-new-precio-pactado"
                  min="0"
                  step="0.01"
                  value={newPrecioPactado}
                  onChange={(e) => setNewPrecioPactado(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold text-foreground">
                  Lead Time (Días)
                </label>
                <input
                  type="number"
                  data-testid="input-new-lead-time"
                  min="0"
                  max="90"
                  value={newLeadTime}
                  onChange={(e) => setNewLeadTime(Number(e.target.value))}
                  className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-primary/20">
              <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer select-none">
                <input
                  type="checkbox"
                  data-testid="checkbox-new-es-principal"
                  checked={newEsPrincipal}
                  onChange={(e) => setNewEsPrincipal(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                />
                <span>Marcar como Proveedor Principal para este insumo</span>
              </label>

              <button
                type="button"
                onClick={handleAddProduct}
                data-testid="btn-confirm-add-product"
                className="min-h-[38px] rounded-xl bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground transition-all hover:bg-primary/90 active:scale-95"
              >
                Insertar en Lista
              </button>
            </div>
          </div>
        )}

        {/* Tabla o Lista de Insumos */}
        {isLoadingCatalog ? (
          <div className="space-y-2 py-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 w-full animate-pulse rounded-xl bg-muted" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div
            data-testid="catalog-empty-state"
            className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground"
          >
            No hay productos registrados en el catálogo de este proveedor. Haz clic en <strong>+ Agregar Insumo</strong> para empezar.
          </div>
        ) : (
          <div
            data-testid="catalog-items-table"
            className="overflow-x-auto rounded-xl border border-border max-h-[350px] overflow-y-auto"
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase sticky top-0 bg-background/95 backdrop-blur-sm z-10">
                  <th className="py-2.5 px-3">Insumo</th>
                  <th className="py-2.5 px-3">Cód. Prov.</th>
                  <th className="py-2.5 px-3">Último Costo</th>
                  <th className="py-2.5 px-3">Precio Pactado ($)</th>
                  <th className="py-2.5 px-3 text-center">Lead Time</th>
                  <th className="py-2.5 px-3 text-center">Principal</th>
                  <th className="py-2.5 px-3 text-right">Quitar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 font-medium">
                {items.map((it, idx) => (
                  <tr
                    key={it.id ?? `item-${it.producto_id}-${idx}`}
                    data-testid={`catalog-row-${idx}`}
                    className="hover:bg-muted/20"
                  >
                    {/* Insumo */}
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-foreground">
                        {it.producto_nombre || `Producto #${it.producto_id}`}
                      </div>
                      {it.producto_sku && (
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {it.producto_sku}
                        </div>
                      )}
                    </td>

                    {/* Cód Prov */}
                    <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">
                      {it.codigo_producto_proveedor ?? it.codigo_proveedor ?? "—"}
                    </td>

                    {/* Último Costo */}
                    <td className="py-2.5 px-3 text-muted-foreground">
                      {it.ultimo_costo_neto ? format(it.ultimo_costo_neto) : "—"}
                    </td>

                    {/* Precio Pactado (Editable) */}
                    <td className="py-2.5 px-3">
                      <input
                        type="number"
                        data-testid={`input-precio-pactado-${idx}`}
                        value={it.precio_pactado ?? ""}
                        onChange={(e) => handleUpdateItem(idx, "precio_pactado", e.target.value)}
                        className="w-24 rounded-lg border border-border bg-background px-2 py-1 text-xs text-foreground focus:border-primary focus:outline-none"
                      />
                    </td>

                    {/* Lead Time */}
                    <td className="py-2.5 px-3 text-center">
                      <div className="inline-flex items-center gap-1 text-[11px] text-foreground font-semibold">
                        <Clock className="h-3 w-3 text-primary" />
                        <span>{it.tiempo_entrega_dias ?? proveedor.lead_time_dias}d</span>
                      </div>
                    </td>

                    {/* Es Principal */}
                    <td className="py-2.5 px-3 text-center">
                      <button
                        type="button"
                        onClick={() => handleUpdateItem(idx, "es_proveedor_principal", !it.es_proveedor_principal)}
                        data-testid={`btn-toggle-principal-${idx}`}
                        title={it.es_proveedor_principal ? "Proveedor principal" : "Marcar como principal"}
                        className={`flex h-8 w-8 mx-auto items-center justify-center rounded-lg border transition-all ${
                          it.es_proveedor_principal
                            ? "border-amber-500/50 bg-amber-500/10 text-amber-500"
                            : "border-border text-muted-foreground/40 hover:text-muted-foreground"
                        }`}
                      >
                        <Star className="h-4 w-4 fill-current" />
                      </button>
                    </td>

                    {/* Eliminar */}
                    <td className="py-2.5 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        data-testid={`btn-remove-catalog-item-${idx}`}
                        title="Eliminar de catálogo pactado"
                        className="flex h-8 w-8 ml-auto items-center justify-center rounded-lg text-muted-foreground hover:bg-rose-500/10 hover:text-rose-500 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer con acciones */}
        <div className="mt-2 flex items-center justify-between border-t border-border/70 pt-3">
          <div className="text-[11px] text-muted-foreground">
            Los cambios se aplicarán automáticamente a las futuras órdenes de compra.
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isUpdatingCatalog}
              className="min-h-[44px] rounded-xl border border-border px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted transition-colors"
            >
              Cerrar
            </button>
            <button
              type="button"
              onClick={handleSaveCatalog}
              disabled={isUpdatingCatalog || items.length === 0}
              data-testid="btn-save-catalog"
              className="min-h-[44px] flex items-center gap-2 rounded-xl bg-primary px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              <span>{isUpdatingCatalog ? "Guardando Catálogo..." : "Guardar Catálogo Pactado"}</span>
            </button>
          </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
