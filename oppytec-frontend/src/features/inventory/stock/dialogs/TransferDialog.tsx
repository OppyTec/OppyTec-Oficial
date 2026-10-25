// oppytec-frontend/src/features/inventory/stock/dialogs/TransferDialog.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  ArrowRightLeft,
  Search,
  Plus,
  Trash2,
  AlertTriangle,
  Package,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import type { StockItem, BulkTransferPayload } from "../../types";

export interface TransferDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly stockItems: StockItem[];
  readonly bodegas: ReadonlyArray<{
    readonly id: number;
    readonly nombre: string;
    readonly color?: string;
    readonly icono?: string;
  }>;
  readonly initialProduct?: StockItem | null;
  readonly onTransfer: (payload: BulkTransferPayload) => Promise<unknown>;
}

interface TransferRow {
  localId: string;
  producto_id: number;
  cantidad: number;
  lote_codigo?: string;
}

export function TransferDialog({
  open,
  onClose,
  stockItems,
  bodegas,
  initialProduct,
  onTransfer,
}: TransferDialogProps) {
  const { t } = useTranslation("inventory");

  // Bodegas de origen y destino
  const [origenId, setOrigenId] = useState<number>(() => {
    if (initialProduct) return initialProduct.bodega_id;
    return bodegas[0]?.id ?? 1;
  });

  const [destinoId, setDestinoId] = useState<number>(() => {
    const firstOther = bodegas.find((b) => b.id !== (initialProduct?.bodega_id ?? 1));
    return firstOther?.id ?? (bodegas[1]?.id ?? 2);
  });

  // Filas de insumos a transferir
  const [rows, setRows] = useState<TransferRow[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [productSearch, setProductSearch] = useState("");

  // Inicializar filas al abrir el modal o cambiar producto inicial
  useEffect(() => {
    if (open) {
      const orig = initialProduct ? initialProduct.bodega_id : bodegas[0]?.id ?? 1;
      setOrigenId(orig);

      const dest = bodegas.find((b) => b.id !== orig)?.id ?? (bodegas[1]?.id ?? 2);
      setDestinoId(dest);

      if (initialProduct) {
        setRows([
          {
            localId: `tr-${Date.now()}-0`,
            producto_id: initialProduct.producto_id,
            cantidad: 1,
            lote_codigo: initialProduct.lotes?.[0]?.lote_codigo,
          },
        ]);
      } else {
        const availableInOrig = stockItems.filter((i) => i.bodega_id === orig);
        const first = availableInOrig[0];
        setRows([
          {
            localId: `tr-${Date.now()}-0`,
            producto_id: first ? first.producto_id : 0,
            cantidad: 1,
            lote_codigo: first?.lotes?.[0]?.lote_codigo,
          },
        ]);
      }
      setProductSearch("");
      setIsSubmitting(false);
    }
  }, [open, initialProduct, bodegas, stockItems]);

  // Manejo de intercambio si origen y destino coinciden
  const handleOrigenChange = (newOrig: number) => {
    if (newOrig === destinoId) {
      setDestinoId(origenId);
    }
    setOrigenId(newOrig);
  };

  const handleDestinoChange = (newDest: number) => {
    if (newDest === origenId) {
      setOrigenId(destinoId);
    }
    setDestinoId(newDest);
  };

  // Insumos disponibles en la bodega de origen
  const itemsInOrigin = useMemo(() => {
    return stockItems.filter((it) => it.bodega_id === origenId);
  }, [stockItems, origenId]);

  // Búsqueda de productos en origen
  const filteredOriginItems = useMemo(() => {
    if (!productSearch.trim()) return itemsInOrigin;
    const q = productSearch.toLowerCase().trim();
    return itemsInOrigin.filter(
      (it) =>
        it.nombre.toLowerCase().includes(q) ||
        it.sku.toLowerCase().includes(q) ||
        it.categoria.toLowerCase().includes(q)
    );
  }, [itemsInOrigin, productSearch]);

  const handleAddRow = () => {
    const unusedItem = itemsInOrigin.find(
      (it) => !rows.some((r) => r.producto_id === it.producto_id)
    );
    const prodId = unusedItem ? unusedItem.producto_id : itemsInOrigin[0]?.producto_id ?? 0;
    setRows((prev) => [
      ...prev,
      {
        localId: `tr-${Date.now()}-${prev.length}`,
        producto_id: prodId,
        cantidad: 1,
        lote_codigo: unusedItem?.lotes?.[0]?.lote_codigo,
      },
    ]);
  };

  const handleRemoveRow = (localId: string) => {
    if (rows.length <= 1) {
      toast.info(t("modals.transfer.error_min_items", "Debe haber al menos un insumo en la transferencia"));
      return;
    }
    setRows((prev) => prev.filter((r) => r.localId !== localId));
  };

  const handleUpdateRow = (
    localId: string,
    field: keyof TransferRow,
    value: string | number
  ) => {
    setRows((prev) =>
      prev.map((r) => {
        if (r.localId !== localId) return r;
        if (field === "producto_id") {
          const item = itemsInOrigin.find((it) => it.producto_id === Number(value));
          return {
            ...r,
            producto_id: Number(value),
            lote_codigo: item?.lotes?.[0]?.lote_codigo,
          };
        }
        return { ...r, [field]: value };
      })
    );
  };

  // Validación de filas
  const validationErrors = useMemo(() => {
    const errors: Record<string, string> = {};
    if (origenId === destinoId) {
      errors.bodegas = t("modals.transfer.error_different_warehouses", "La bodega de origen y destino deben ser diferentes");
    }

    for (const r of rows) {
      if (!r.producto_id) {
        errors[r.localId] = t("modals.transfer.error_valid_product", "Seleccione un producto válido");
        continue;
      }
      const item = itemsInOrigin.find((it) => it.producto_id === r.producto_id);
      const stockDisp = item ? item.stock_actual : 0;
      if (r.cantidad <= 0) {
        errors[r.localId] = t("modals.transfer.error_qty_positive", "La cantidad debe ser mayor a 0");
      } else if (r.cantidad > stockDisp) {
        errors[r.localId] = t("modals.transfer.error_qty_exceeds", {
          qty: r.cantidad,
          available: stockDisp,
          defaultValue: `Cantidad (${r.cantidad}) supera el stock disponible (${stockDisp})`,
        });
      }
    }
    return errors;
  }, [rows, itemsInOrigin, origenId, destinoId, t]);

  const hasErrors = Object.keys(validationErrors).length > 0;

  // Confirmación
  const handleSubmit = async () => {
    if (hasErrors) {
      toast.error(t("modals.transfer.error_fix_errors", "Por favor corrija los errores antes de confirmar el traspaso"));
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: BulkTransferPayload = {
        bodega_origen_id: origenId,
        bodega_destino_id: destinoId,
        fecha_transferencia: new Date().toISOString().split("T")[0],
        items: rows.map((r) => {
          const item = itemsInOrigin.find((it) => it.producto_id === r.producto_id);
          return {
            producto_id: r.producto_id,
            cantidad: r.cantidad,
            producto_nombre: item?.nombre,
          };
        }),
      };

      await onTransfer(payload);
      onClose();
    } catch {
      // El toast ya fue mostrado por el hook o llamador
    } finally {
      setIsSubmitting(false);
    }
  };

  // Nombres de bodegas
  const origenBodega = bodegas.find((b) => b.id === origenId);
  const destinoBodega = bodegas.find((b) => b.id === destinoId);

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("modals.transfer.title", "Transferencia de Stock entre Bodegas")}
      description={t("modals.transfer.description", "Mueve existencias de forma atómica con balance en vivo y trazabilidad en Kardex")}
      maxWidth="max-w-3xl"
    >
      <div data-testid="dialog-transfer-container" className="space-y-4 py-2">
        {/* Selector de Bodegas Origen y Destino */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-2xl bg-muted/30 border border-border">
          <div className="space-y-1.5">
            <label className="text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              {t("modals.transfer.origin_warehouse", "Bodega Origen")}
            </label>
            <select
              data-testid="transfer-origen-select"
              aria-label={t("modals.transfer.origin_warehouse", "Bodega Origen")}
              value={origenId}
              onChange={(e) => handleOrigenChange(Number(e.target.value))}
              className="w-full h-11 px-3 rounded-xl border border-border bg-card text-xs font-bold text-foreground outline-none focus:ring-2 focus:ring-primary cursor-pointer"
            >
              {bodegas.map((b) => (
                <option key={`orig-${b.id}`} value={b.id}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              {t("modals.transfer.destination_warehouse", "Bodega Destino")}
            </label>
            <select
              data-testid="transfer-destino-select"
              aria-label={t("modals.transfer.destination_warehouse", "Bodega Destino")}
              value={destinoId}
              onChange={(e) => handleDestinoChange(Number(e.target.value))}
              className="w-full h-11 px-3 rounded-xl border border-border bg-card text-xs font-bold text-foreground outline-none focus:ring-2 focus:ring-primary cursor-pointer"
            >
              {bodegas.map((b) => (
                <option key={`dest-${b.id}`} value={b.id}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </div>

          {origenId === destinoId && (
            <div className="col-span-full text-xs font-bold text-destructive flex items-center gap-1.5 pt-1">
              <AlertTriangle className="h-4 w-4" />
              <span>{t("modals.transfer.same_warehouse_error", "Origen y destino no pueden ser la misma bodega")}</span>
            </div>
          )}
        </div>

        {/* Buscador de Insumos para agilizar selección */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            data-testid="transfer-search-input"
            aria-label={t("modals.transfer.search_placeholder", "Buscar insumos disponibles en bodega origen...")}
            placeholder={t("modals.transfer.search_placeholder", "Buscar insumos disponibles en bodega origen...")}
            value={productSearch}
            onChange={(e) => setProductSearch(e.target.value)}
            className="w-full pl-9 pr-3 h-10 rounded-xl border border-border bg-card text-xs text-foreground placeholder:text-muted-foreground outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Lista de Filas de Insumos */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-black uppercase tracking-wider text-foreground flex items-center gap-1.5">
              <Package className="h-4 w-4 text-primary" />
              {t("modals.transfer.items_to_move", { count: rows.length, defaultValue: `Insumos a Mover (${rows.length})` })}
            </label>
            <button
              type="button"
              data-testid="btn-add-transfer-row"
              onClick={handleAddRow}
              className="touch-target inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-secondary text-xs font-bold text-foreground cursor-pointer transition-colors"
            >
              <Plus className="h-3.5 w-3.5 text-primary" />
              <span>{t("modals.transfer.add_item", "Agregar otro insumo")}</span>
            </button>
          </div>

          <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
            {rows.map((row, idx) => {
              const currentItem = itemsInOrigin.find((it) => it.producto_id === row.producto_id);
              const targetItem = stockItems.find(
                (it) => it.producto_id === row.producto_id && it.bodega_id === destinoId
              );

              const stockOrigenAntes = currentItem ? currentItem.stock_actual : 0;
              const stockOrigenDespues = stockOrigenAntes - row.cantidad;
              const stockDestinoAntes = targetItem ? targetItem.stock_actual : 0;
              const stockDestinoDespues = stockDestinoAntes + row.cantidad;
              const rowError = validationErrors[row.localId];

              return (
                <div
                  key={row.localId}
                  data-testid={`transfer-row-${idx}`}
                  className={cn(
                    "p-3 rounded-xl border bg-card transition-all space-y-2",
                    rowError ? "border-destructive/60 bg-destructive/5" : "border-border"
                  )}
                >
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                    {/* Selector de Producto */}
                    <div className="sm:col-span-6 space-y-1">
                      <select
                        data-testid={`transfer-item-select-${idx}`}
                        value={row.producto_id}
                        onChange={(e) =>
                          handleUpdateRow(row.localId, "producto_id", Number(e.target.value))
                        }
                        className="w-full h-9 px-2.5 rounded-lg border border-border bg-background text-xs font-bold text-foreground outline-none cursor-pointer"
                      >
                        {filteredOriginItems.map((it) => (
                          <option key={`opt-${it.producto_id}`} value={it.producto_id}>
                            {t("modals.transfer.opt_item_format", {
                              name: it.nombre,
                              sku: it.sku,
                              stock: it.stock_actual,
                              unit: it.unidad_medida,
                              defaultValue: `${it.nombre} (${it.sku}) — Disp: ${it.stock_actual} ${it.unidad_medida}`,
                            })}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Cantidad Input */}
                    <div className="sm:col-span-3 space-y-1">
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          data-testid={`transfer-item-qty-${idx}`}
                          step="any"
                          min="0.001"
                          max={stockOrigenAntes}
                          value={row.cantidad || ""}
                          onChange={(e) =>
                            handleUpdateRow(row.localId, "cantidad", Number(e.target.value))
                          }
                          className="w-full h-9 px-2 rounded-lg border border-border bg-background text-xs font-mono font-bold text-center"
                          placeholder={t("modals.transfer.quantity_placeholder", "Cantidad")}
                        />
                        <span className="text-[11px] font-bold text-muted-foreground">
                          {currentItem?.unidad_medida ?? "u"}
                        </span>
                      </div>
                    </div>

                    {/* Lote / FEFO opcional */}
                    <div className="sm:col-span-2 space-y-1">
                      {currentItem?.lotes && currentItem.lotes.length > 0 ? (
                        <select
                          value={row.lote_codigo ?? ""}
                          onChange={(e) =>
                            handleUpdateRow(row.localId, "lote_codigo", e.target.value)
                          }
                          className="w-full h-9 px-2 rounded-lg border border-border bg-background text-[11px] font-mono cursor-pointer"
                        >
                          {currentItem.lotes.map((l) => (
                            <option key={l.lote_codigo} value={l.lote_codigo}>
                              {l.lote_codigo} ({l.cantidad})
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-[10px] text-muted-foreground italic block truncate text-center">
                          {t("modals.transfer.no_fefo_lot", "Sin lote FEFO")}
                        </span>
                      )}
                    </div>

                    {/* Eliminar Fila */}
                    <div className="sm:col-span-1 flex justify-end">
                      <button
                        type="button"
                        data-testid={`btn-remove-transfer-row-${idx}`}
                        onClick={() => handleRemoveRow(row.localId)}
                        className="p-2 rounded-lg text-destructive/80 hover:text-destructive hover:bg-destructive/10 cursor-pointer transition-colors"
                        title={t("modals.transfer.remove_item_title", "Eliminar insumo")}
                        aria-label={t("modals.transfer.remove_item_title", "Eliminar insumo")}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Cálculo en vivo de balance y error */}
                  <div className="flex flex-wrap items-center justify-between text-[11px] pt-1 border-t border-border/40 gap-2">
                    <div className="flex items-center gap-3 font-mono">
                      <span className="text-muted-foreground">
                        {t("modals.transfer.origin_balance", {
                          name: origenBodega?.nombre ?? "Origen",
                          defaultValue: `Origen (${origenBodega?.nombre ?? "Origen"}):`,
                        })}{" "}
                        <strong className="text-foreground">{stockOrigenAntes}</strong>{" "}
                        <ArrowRight className="inline h-3 w-3 text-muted-foreground" />{" "}
                        <strong
                          className={cn(
                            stockOrigenDespues < 0 ? "text-destructive" : "text-emerald-500"
                          )}
                        >
                          {stockOrigenDespues}
                        </strong>
                      </span>
                      <span className="text-muted-foreground">
                        {t("modals.transfer.destination_balance", {
                          name: destinoBodega?.nombre ?? "Destino",
                          defaultValue: `Destino (${destinoBodega?.nombre ?? "Destino"}):`,
                        })}{" "}
                        <strong className="text-foreground">{stockDestinoAntes}</strong>{" "}
                        <ArrowRight className="inline h-3 w-3 text-muted-foreground" />{" "}
                        <strong className="text-emerald-500">{stockDestinoDespues}</strong>
                      </span>
                    </div>

                    {rowError && (
                      <span className="text-destructive font-bold flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        {rowError}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Resumen Final de Transferencia */}
        <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 flex flex-wrap items-center justify-between text-xs font-bold gap-2">
          <div className="flex items-center gap-2 text-foreground">
            <ArrowRightLeft className="h-4 w-4 text-primary" />
            <span>
              {t("modals.transfer.total_summary", {
                qty: rows.reduce((acc, r) => acc + (Number(r.cantidad) || 0), 0),
                count: rows.length,
                defaultValue: `Total a transferir: ${rows.reduce((acc, r) => acc + (Number(r.cantidad) || 0), 0)} unidades en ${rows.length} insumo(s)`,
              })}
            </span>
          </div>
          <span className="text-[11px] text-muted-foreground font-normal">
            {t("modals.transfer.operation_date", {
              date: new Date().toLocaleDateString("es-CL"),
              defaultValue: `Fecha de operación: ${new Date().toLocaleDateString("es-CL")}`,
            })}
          </span>
        </div>

        {/* Botonera de Acción */}
        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="touch-target px-4 py-2 rounded-xl border border-border text-xs font-bold text-foreground hover:bg-secondary cursor-pointer transition-colors"
          >
            {t("modals.transfer.cancel", "Cancelar")}
          </button>
          <button
            type="button"
            data-testid="btn-confirm-transfer"
            onClick={handleSubmit}
            disabled={isSubmitting || hasErrors}
            className={cn(
              "touch-target px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider cursor-pointer shadow-md transition-all flex items-center gap-1.5",
              hasErrors || isSubmitting
                ? "bg-muted text-muted-foreground cursor-not-allowed opacity-60"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20"
            )}
          >
            <ArrowRightLeft className="h-3.5 w-3.5" />
            <span>{isSubmitting ? t("modals.transfer.submitting", "Transfiriendo...") : t("modals.transfer.confirm", "Confirmar Transferencia")}</span>
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}

export default TransferDialog;
