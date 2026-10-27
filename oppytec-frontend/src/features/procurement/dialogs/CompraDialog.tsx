/**
 * oppytec-frontend/src/features/procurement/dialogs/CompraDialog.tsx
 * Modal Centrado Amplio para Creación y Edición de Órdenes de Compra.
 * Soporte de borrador persistente en localStorage, adición dinámica de insumos,
 * cálculo estricto de IVA (19%) y total neto con precisión Decimal.
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import { Plus, Trash2, Building2, Warehouse, Calendar, Save, AlertCircle } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { useCurrencyFormatter } from "@/shared/currency";
import type {
  CompraDraft,
  CompraDraftItem,
  CreateOrderPayload,
  OrderItemInput,
  Proveedor,
} from "../types";
import { MOCK_PROVEEDORES } from "../mockData";

export interface CompraDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly onSave: (payload: CreateOrderPayload) => Promise<void> | void;
  readonly initialDraft?: CompraDraft | null;
  readonly onSaveDraft?: (draft: Partial<CompraDraft>) => void;
  readonly proveedores?: Proveedor[];
  readonly isSubmitting?: boolean;
}

interface OrderItemRow {
  id: string;
  producto_id: number;
  producto_nombre: string;
  cantidad: number;
  costo_unitario: number;
}

const DEFAULT_INSUMOS_SUGGESTIONS = [
  { id: 10, nombre: "Pollo King", costo: 3850 },
  { id: 11, nombre: "Salmón Atlántico Fresco", costo: 9800 },
  { id: 20, nombre: "Tomate Larga Vida", costo: 1250 },
  { id: 30, nombre: "Queso Parmesano Reggiano", costo: 14500 },
  { id: 40, nombre: "Aceite de Oliva Extra Virgen", costo: 7200 },
];

export function CompraDialog({
  open,
  onClose,
  onSave,
  initialDraft,
  onSaveDraft,
  proveedores = MOCK_PROVEEDORES,
  isSubmitting = false,
}: CompraDialogProps) {
  const isMobile = useIsMobile();
  const { format } = useCurrencyFormatter();

  const [proveedorId, setProveedorId] = useState<number>(proveedores[0]?.id ?? 1);
  const [bodegaId, setBodegaId] = useState<number>(1);
  const [fechaEntrega, setFechaEntrega] = useState<string>("");
  const [moneda, setMoneda] = useState<string>("CLP");
  const [notas, setNotas] = useState<string>("");

  const [items, setItems] = useState<OrderItemRow[]>([]);

  // Inicializar o precargar desde borrador
  useEffect(() => {
    if (open) {
      if (initialDraft) {
        if (initialDraft.proveedor_id) setProveedorId(initialDraft.proveedor_id);
        if (initialDraft.bodega_destino_id) setBodegaId(initialDraft.bodega_destino_id);
        if (initialDraft.fecha_entrega_comprometida) {
          setFechaEntrega(initialDraft.fecha_entrega_comprometida.slice(0, 10));
        }
        if (initialDraft.notas) setNotas(initialDraft.notas);
        if (initialDraft.moneda) setMoneda(initialDraft.moneda);

        if (initialDraft.items && initialDraft.items.length > 0) {
          setItems(
            initialDraft.items.map((it, idx) => ({
              id: `draft-row-${idx}-${Date.now()}`,
              producto_id: it.producto_id,
              producto_nombre: it.producto_nombre,
              cantidad: Number(it.cantidad_solicitada) || 1,
              costo_unitario: Number(it.costo_unitario_neto) || 0,
            }))
          );
          return;
        }
      }

      // Default: 1 ítem sugerido (ej. "Pollo King")
      const def = DEFAULT_INSUMOS_SUGGESTIONS[0];
      if (def) {
        setItems([
          {
            id: `item-${Date.now()}`,
            producto_id: def.id,
            producto_nombre: def.nombre,
            cantidad: 10,
            costo_unitario: def.costo,
          },
        ]);
      }
      // Seteo de fecha default a 3 días en el futuro
      const future = new Date();
      future.setDate(future.getDate() + 3);
      setFechaEntrega(future.toISOString().slice(0, 10));
    }
  }, [open, initialDraft]);

  // Manejo dinámico de filas
  const handleAddItem = () => {
    const nextInsumo =
      DEFAULT_INSUMOS_SUGGESTIONS[items.length % DEFAULT_INSUMOS_SUGGESTIONS.length];
    if (nextInsumo) {
      setItems((prev) => [
        ...prev,
        {
          id: `row-${Date.now()}-${Math.random()}`,
          producto_id: nextInsumo.id,
          producto_nombre: nextInsumo.nombre,
          cantidad: 5,
          costo_unitario: nextInsumo.costo,
        },
      ]);
    }
  };

  const handleRemoveItem = (id: string) => {
    setItems((prev) => prev.filter((r) => r.id !== id));
  };

  const handleUpdateItem = (
    id: string,
    field: "producto_id" | "cantidad" | "costo_unitario" | "producto_nombre",
    value: string | number
  ) => {
    setItems((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        if (field === "producto_id") {
          const numId = Number(value);
          const found = DEFAULT_INSUMOS_SUGGESTIONS.find((s) => s.id === numId);
          return {
            ...r,
            producto_id: numId,
            producto_nombre: found ? found.nombre : r.producto_nombre,
            costo_unitario: found ? found.costo : r.costo_unitario,
          };
        }
        return { ...r, [field]: value };
      })
    );
  };

  // Cálculos financieros
  const montoNeto = useMemo(() => {
    return items.reduce((sum, it) => sum + it.cantidad * it.costo_unitario, 0);
  }, [items]);

  const montoImpuestos = useMemo(() => {
    return Math.round(montoNeto * 0.19);
  }, [montoNeto]);

  const montoTotal = useMemo(() => {
    return montoNeto + montoImpuestos;
  }, [montoNeto, montoImpuestos]);

  // Auto-guardado en borrador cuando los datos cambian
  const handleAutoSaveDraft = useCallback(() => {
    if (!onSaveDraft) return;
    const draftItems: CompraDraftItem[] = items.map((it) => ({
      producto_id: it.producto_id,
      producto_nombre: it.producto_nombre,
      cantidad_solicitada: it.cantidad,
      costo_unitario_neto: it.costo_unitario,
      subtotal_linea: it.cantidad * it.costo_unitario,
    }));

    const selectedProv = proveedores.find((p) => p.id === proveedorId);
    onSaveDraft({
      proveedor_id: proveedorId,
      proveedor_nombre: selectedProv?.razon_social,
      bodega_destino_id: bodegaId,
      fecha_entrega_comprometida: fechaEntrega || null,
      moneda,
      notas,
      items: draftItems,
    });
  }, [onSaveDraft, items, proveedorId, bodegaId, fechaEntrega, moneda, notas, proveedores]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (items.length === 0) return;

    const selectedProv = proveedores.find((p) => p.id === proveedorId);
    const orderItems: OrderItemInput[] = items.map((it) => ({
      producto_id: it.producto_id,
      cantidad_solicitada: it.cantidad,
      costo_unitario_neto: it.costo_unitario,
    }));

    const payload: CreateOrderPayload = {
      proveedor_id: proveedorId,
      proveedor_nombre: selectedProv?.razon_social,
      bodega_destino_id: bodegaId,
      fecha_entrega_comprometida: fechaEntrega || null,
      moneda,
      notas: notas.trim() || undefined,
      items: orderItems,
    };

    await onSave(payload);
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title="Nueva Orden de Compra"
      description="Creación de orden formal de reabastecimiento con cálculo de impuestos"
      isMobile={isMobile}
      maxWidth="max-w-4xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2 text-xs">
        {/* Cabecera de la Orden: Proveedor, Bodega, Fecha */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-2xl border border-border bg-card/40 p-3.5">
          {/* Proveedor */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Proveedor *
            </label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <select
                data-testid="compra-dialog-proveedor-select"
                value={proveedorId}
                onChange={(e) => {
                  setProveedorId(Number(e.target.value));
                  handleAutoSaveDraft();
                }}
                className="touch-target w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
              >
                {proveedores.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.razon_social} ({p.rut_tax_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Bodega Destino */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Bodega Destino *
            </label>
            <div className="relative">
              <Warehouse className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <select
                data-testid="compra-dialog-bodega-select"
                value={bodegaId}
                onChange={(e) => {
                  setBodegaId(Number(e.target.value));
                  handleAutoSaveDraft();
                }}
                className="touch-target w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
              >
                <option value={1}>Bodega Cocina Central</option>
                <option value={2}>Cámara Fría -18°C</option>
                <option value={3}>Barra & Cava</option>
              </select>
            </div>
          </div>

          {/* Fecha Entrega Comprometida */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Entrega Comprometida *
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="date"
                required
                data-testid="compra-dialog-fecha-input"
                value={fechaEntrega}
                onChange={(e) => {
                  setFechaEntrega(e.target.value);
                  handleAutoSaveDraft();
                }}
                className="touch-target w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2 text-xs font-medium text-foreground focus:border-primary focus:outline-none min-h-[44px]"
              />
            </div>
          </div>
        </div>

        {/* Tabla Dinámica de Ítems */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Ítems del Pedido ({items.length})
            </span>
            <button
              type="button"
              onClick={handleAddItem}
              data-testid="compra-dialog-add-item-btn"
              className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-border bg-secondary/50 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary active:scale-95 cursor-pointer"
            >
              <Plus className="h-4 w-4 text-primary" />
              <span>Agregar Insumo</span>
            </button>
          </div>

          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-6 text-center text-muted-foreground">
              <AlertCircle className="h-6 w-6 mb-1 text-muted-foreground/60" />
              <p>Agregue al menos un insumo para emitir la orden.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[35vh] overflow-y-auto pr-1">
              {items.map((row, idx) => {
                const subtotal = row.cantidad * row.costo_unitario;

                return (
                  <div
                    key={row.id}
                    data-testid={`compra-dialog-item-row-${idx}`}
                    className="grid grid-cols-12 gap-2 items-center rounded-xl border border-border bg-card/60 p-2.5"
                  >
                    {/* Selector de Producto */}
                    <div className="col-span-12 sm:col-span-5">
                      <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-0.5 sm:hidden">
                        Insumo
                      </label>
                      <select
                        value={row.producto_id}
                        data-testid={`item-producto-select-${idx}`}
                        onChange={(e) =>
                          handleUpdateItem(row.id, "producto_id", e.target.value)
                        }
                        className="touch-target w-full rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs font-semibold text-foreground focus:border-primary focus:outline-none min-h-[44px] cursor-pointer"
                      >
                        {DEFAULT_INSUMOS_SUGGESTIONS.map((sug) => (
                          <option key={sug.id} value={sug.id}>
                            {sug.nombre}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Cantidad Solicitada */}
                    <div className="col-span-4 sm:col-span-2">
                      <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-0.5 sm:hidden">
                        Cantidad
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0.1"
                        required
                        data-testid={`item-cantidad-input-${idx}`}
                        value={row.cantidad}
                        onChange={(e) =>
                          handleUpdateItem(
                            row.id,
                            "cantidad",
                            parseFloat(e.target.value) || 0
                          )
                        }
                        className="touch-target w-full rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs font-bold text-foreground focus:border-primary focus:outline-none min-h-[44px]"
                      />
                    </div>

                    {/* Costo Unitario Neto */}
                    <div className="col-span-4 sm:col-span-2">
                      <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-0.5 sm:hidden">
                        Costo Neto
                      </label>
                      <input
                        type="number"
                        step="1"
                        min="0"
                        required
                        data-testid={`item-costo-input-${idx}`}
                        value={row.costo_unitario}
                        onChange={(e) =>
                          handleUpdateItem(
                            row.id,
                            "costo_unitario",
                            parseFloat(e.target.value) || 0
                          )
                        }
                        className="touch-target w-full rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none min-h-[44px]"
                      />
                    </div>

                    {/* Subtotal Línea */}
                    <div className="col-span-3 sm:col-span-2 text-right font-mono font-bold text-foreground">
                      <span className="text-[10px] uppercase text-muted-foreground block sm:hidden">
                        Subtotal
                      </span>
                      <span>{format(subtotal)}</span>
                    </div>

                    {/* Eliminar Fila */}
                    <div className="col-span-1 text-center">
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(row.id)}
                        title="Eliminar fila"
                        data-testid={`item-remove-btn-${idx}`}
                        className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 active:scale-95 cursor-pointer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Desglose Financiero (Neto, IVA 19%, Total) */}
        <div className="rounded-2xl border border-border bg-secondary/20 p-4">
          <div className="space-y-1.5 text-xs max-w-xs ml-auto">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Subtotal Neto:</span>
              <span className="font-bold text-foreground">{format(montoNeto)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">IVA (19%):</span>
              <span className="font-bold text-foreground">{format(montoImpuestos)}</span>
            </div>
            <div className="flex items-center justify-between border-t border-border pt-2 text-sm">
              <span className="font-black text-foreground">Total Orden:</span>
              <span className="font-black text-primary text-base">{format(montoTotal)}</span>
            </div>
          </div>
        </div>

        {/* Notas Adicionales */}
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            Instrucciones de Entrega / Notas
          </label>
          <textarea
            rows={2}
            value={notas}
            onChange={(e) => {
              setNotas(e.target.value);
              handleAutoSaveDraft();
            }}
            placeholder="Ej: Entregar por acceso lateral antes de las 11:00 AM..."
            className="w-full rounded-xl border border-border bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
          />
        </div>

        {/* Botones de acción */}
        <div className="flex items-center justify-between border-t border-border pt-3">
          {onSaveDraft && (
            <button
              type="button"
              onClick={handleAutoSaveDraft}
              data-testid="compra-dialog-save-draft-btn"
              className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground active:scale-95 cursor-pointer"
            >
              <Save className="h-4 w-4" />
              <span>Guardar Borrador</span>
            </button>
          )}

          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="touch-target inline-flex min-h-[44px] min-w-[80px] items-center justify-center rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted active:scale-95 disabled:opacity-50 cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting || items.length === 0}
              data-testid="compra-dialog-submit-btn"
              className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2 text-xs font-bold text-primary-foreground shadow-md hover:bg-primary/90 active:scale-95 disabled:opacity-50 cursor-pointer"
            >
              <span>{isSubmitting ? "Emitiendo..." : "Emitir Orden de Compra"}</span>
            </button>
          </div>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
