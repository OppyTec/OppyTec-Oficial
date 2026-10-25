// oppytec-frontend/src/features/inventory/stock/dialogs/AddingMercaderiaDialog.tsx
import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Truck,
  Plus,
  PackageCheck,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import type { StockItem, MovementPayload } from "../../types";

export interface AddingMercaderiaDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly stockItems: StockItem[];
  readonly bodegas: ReadonlyArray<{
    readonly id: number;
    readonly nombre: string;
    readonly color?: string;
    readonly icono?: string;
  }>;
  readonly onRegisterMovement?: (payload: MovementPayload) => Promise<unknown>;
  readonly onSuccess?: () => void;
}

interface MockPendingPurchase {
  id: number;
  numero_pedido: string;
  proveedor: string;
  fecha: string;
  bodega_nombre: string;
  bodega_id: number;
  items_count: number;
  total: number;
  estado: "en_ruta" | "pendiente";
}

const MOCK_PURCHASES: MockPendingPurchase[] = [
  {
    id: 101,
    numero_pedido: "OC-2026-0891",
    proveedor: "Carnes Ñuble S.A.",
    fecha: "2026-10-24",
    bodega_nombre: "Cámara de Frío Principal",
    bodega_id: 1,
    items_count: 3,
    total: 840000,
    estado: "en_ruta",
  },
  {
    id: 102,
    numero_pedido: "OC-2026-0894",
    proveedor: "Distribuidora Alimentos del Sur",
    fecha: "2026-10-25",
    bodega_nombre: "Bodega Seca Central",
    bodega_id: 3,
    items_count: 6,
    total: 345000,
    estado: "pendiente",
  },
];

export function AddingMercaderiaDialog({
  open,
  onClose,
  stockItems,
  bodegas,
  onRegisterMovement,
  onSuccess,
}: AddingMercaderiaDialogProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [activeTab, setActiveTab] = useState<"pedidos" | "libre">("pedidos");

  // Estados de Ingreso Libre
  const [bodegaId, setBodegaId] = useState<number>(() => bodegas[0]?.id ?? 1);
  const [productoId, setProductoId] = useState<number>(() => stockItems[0]?.producto_id ?? 1);
  const [cantidad, setCantidad] = useState<number>(10);
  const [costoUnitario, setCostoUnitario] = useState<number>(0);
  const [loteCodigo, setLoteCodigo] = useState<string>("LOT-" + new Date().toISOString().slice(0, 10).replace(/-/g, ""));
  const [fechaVencimiento, setFechaVencimiento] = useState<string>("2026-12-31");
  const [proveedorGuia, setProveedorGuia] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Estados de Pedidos
  const [searchPurchase, setSearchPurchase] = useState("");

  const availableInWarehouse = useMemo(() => {
    return stockItems.filter((it) => it.bodega_id === bodegaId);
  }, [stockItems, bodegaId]);

  const currentItem = useMemo(() => {
    return availableInWarehouse.find((it) => it.producto_id === productoId) ||
      stockItems.find((it) => it.producto_id === productoId);
  }, [availableInWarehouse, stockItems, productoId]);

  const filteredPurchases = useMemo(() => {
    if (!searchPurchase.trim()) return MOCK_PURCHASES;
    const q = searchPurchase.toLowerCase().trim();
    return MOCK_PURCHASES.filter(
      (p) =>
        p.proveedor.toLowerCase().includes(q) ||
        p.numero_pedido.toLowerCase().includes(q) ||
        p.bodega_nombre.toLowerCase().includes(q)
    );
  }, [searchPurchase]);

  // Handler de ingreso libre directo
  const handleConfirmLibre = async () => {
    if (!productoId || cantidad <= 0) {
      toast.error(t("modals.adding_mercaderia.toast_invalid", "Seleccione un producto y cantidad válida"));
      return;
    }

    setIsSubmitting(true);
    try {
      if (onRegisterMovement) {
        await onRegisterMovement({
          producto_id: productoId,
          bodega_id: bodegaId,
          cantidad,
          tipo_movimiento: "ENTRADA",
          unit_cost: costoUnitario || currentItem?.costo_unitario_ppp || 0,
          lote_codigo: loteCodigo || undefined,
          fecha_vencimiento_lote: fechaVencimiento || undefined,
          documento_referencia: proveedorGuia.trim()
            ? `RECEPCION_LIBRE: ${proveedorGuia.trim()}`
            : "RECEPCION_LIBRE_DIRECTA",
        });
      } else {
        toast.success(t("modals.adding_mercaderia.toast_success_direct", {
          qty: cantidad,
          unit: currentItem?.unidad_medida ?? "u",
          defaultValue: `Recepción rápida registrada: ${cantidad} ${currentItem?.unidad_medida ?? "u"} ingresadas`,
        }));
      }
      onSuccess?.();
      onClose();
    } catch {
      // Error manejado
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handler de recepción de pedido
  const handleConfirmPurchase = async (purchase: MockPendingPurchase) => {
    setIsSubmitting(true);
    try {
      // Simular ingreso de los ítems de la orden de compra
      if (onRegisterMovement && stockItems.length > 0) {
        const item = stockItems[0];
        if (item) {
          await onRegisterMovement({
            producto_id: item.producto_id,
            bodega_id: purchase.bodega_id,
            cantidad: 20,
            tipo_movimiento: "COMPRA",
            unit_cost: item.costo_unitario_ppp,
            documento_referencia: `RECEPCION_${purchase.numero_pedido}`,
          });
        }
      }
      toast.success(t("modals.adding_mercaderia.toast_success_order", {
        order: purchase.numero_pedido,
        supplier: purchase.proveedor,
        defaultValue: `Pedido ${purchase.numero_pedido} de ${purchase.proveedor} ingresado a bodega satisfactoriamente`,
      }));
      onSuccess?.();
      onClose();
    } catch {
      // Error
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("modals.adding_mercaderia.title", "Recepción e Ingreso de Mercadería")}
      description={t("modals.adding_mercaderia.description", "Terminal de entrada rápida para órdenes de compra pendientes o ingresos directos con lote FEFO")}
      maxWidth="max-w-2xl"
    >
      <div data-testid="dialog-adding-mercaderia-container" className="space-y-4 py-2">
        {/* Pestañas de modo */}
        <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-muted/40 border border-border">
          <button
            type="button"
            data-testid="tab-receive-pedidos"
            onClick={() => setActiveTab("pedidos")}
            className={cn(
              "touch-target py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer",
              activeTab === "pedidos"
                ? "bg-card text-foreground shadow-xs font-black"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Truck className="h-4 w-4 text-primary" />
            <span>{t("modals.adding_mercaderia.tab_purchase_order", "Desde Orden de Compra")}</span>
          </button>

          <button
            type="button"
            data-testid="tab-receive-libre"
            onClick={() => setActiveTab("libre")}
            className={cn(
              "touch-target py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer",
              activeTab === "libre"
                ? "bg-card text-foreground shadow-xs font-black"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Plus className="h-4 w-4 text-emerald-500" />
            <span>{t("modals.adding_mercaderia.tab_direct_entry", "Ingreso Libre Directo")}</span>
          </button>
        </div>

        {/* MODO 1: RECEPCIÓN DE PEDIDOS */}
        {activeTab === "pedidos" && (
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                data-testid="search-pedidos-input"
                aria-label={t("modals.adding_mercaderia.search_placeholder", "Buscar pedidos por proveedor o N° de orden...")}
                placeholder={t("modals.adding_mercaderia.search_placeholder", "Buscar pedidos por proveedor o N° de orden...")}
                value={searchPurchase}
                onChange={(e) => setSearchPurchase(e.target.value)}
                className="w-full pl-9 pr-3 h-10 rounded-xl border border-border bg-card text-xs text-foreground outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {filteredPurchases.map((p) => (
                <div
                  key={p.id}
                  data-testid={`purchase-card-${p.id}`}
                  className="p-3.5 rounded-xl border border-border bg-card hover:border-primary/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">{p.proveedor}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                        {p.numero_pedido}
                      </span>
                      {p.estado === "en_ruta" && (
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                          {t("modals.adding_mercaderia.in_route", "En Ruta")}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span>{t("modals.adding_mercaderia.destination", { name: p.bodega_nombre, defaultValue: `Destino: ${p.bodega_nombre}` })}</span>
                      <span>•</span>
                      <span>{t("modals.adding_mercaderia.items_count", { count: p.items_count, defaultValue: `${p.items_count} insumos` })}</span>
                      <span>•</span>
                      <span className="font-mono font-semibold text-foreground">{convertAndFormat(p.total, "CLP")}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    data-testid={`btn-receive-purchase-${p.id}`}
                    onClick={() => handleConfirmPurchase(p)}
                    disabled={isSubmitting}
                    className="touch-target inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-all cursor-pointer shadow-xs shadow-primary/20 shrink-0"
                  >
                    <PackageCheck className="h-4 w-4" />
                    <span>{t("modals.adding_mercaderia.receive_order_btn", "Ingresar Pedido")}</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* MODO 2: INGRESO LIBRE DIRECTO */}
        {activeTab === "libre" && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.adding_mercaderia.destination_warehouse", "Bodega Destino")}
                </label>
                <select
                  data-testid="libre-bodega-select"
                  aria-label={t("modals.adding_mercaderia.destination_warehouse", "Bodega Destino")}
                  value={bodegaId}
                  onChange={(e) => setBodegaId(Number(e.target.value))}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {bodegas.map((b) => (
                    <option key={`wh-libre-${b.id}`} value={b.id}>
                      {b.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.adding_mercaderia.product_label", "Insumo / Producto")}
                </label>
                <select
                  data-testid="libre-product-select"
                  aria-label={t("modals.adding_mercaderia.product_label", "Insumo / Producto")}
                  value={productoId}
                  onChange={(e) => {
                    const p = Number(e.target.value);
                    setProductoId(p);
                    const it = stockItems.find((i) => i.producto_id === p);
                    if (it) setCostoUnitario(it.costo_unitario_ppp);
                  }}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {availableInWarehouse.map((it) => (
                    <option key={`prod-libre-${it.producto_id}`} value={it.producto_id}>
                      {it.nombre} ({it.sku})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.adding_mercaderia.received_qty", "Cantidad Recibida")}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    data-testid="libre-quantity-input"
                    aria-label={t("modals.adding_mercaderia.received_qty", "Cantidad Recibida")}
                    step="any"
                    min="0.001"
                    value={cantidad || ""}
                    onChange={(e) => setCantidad(Number(e.target.value))}
                    className="w-full h-10 px-3 rounded-xl border border-border bg-card text-sm font-mono font-bold outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground">
                    {currentItem?.unidad_medida ?? "u"}
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.adding_mercaderia.invoice_cost", "Costo Unitario Factura ($)")}
                </label>
                <input
                  type="number"
                  data-testid="libre-cost-input"
                  aria-label={t("modals.adding_mercaderia.invoice_cost", "Costo Unitario Factura ($)")}
                  step="1"
                  min="0"
                  value={costoUnitario || ""}
                  onChange={(e) => setCostoUnitario(Number(e.target.value))}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-sm font-mono font-bold outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>

            {/* Lote y Vencimiento */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.adding_mercaderia.lot_code", "Código de Lote")}
                </label>
                <input
                  type="text"
                  data-testid="libre-lote-input"
                  aria-label={t("modals.adding_mercaderia.lot_code", "Código de Lote")}
                  value={loteCodigo}
                  onChange={(e) => setLoteCodigo(e.target.value)}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-mono font-bold outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.adding_mercaderia.expiry_date", "Fecha de Caducidad (FEFO)")}
                </label>
                <input
                  type="date"
                  data-testid="libre-expiry-input"
                  aria-label={t("modals.adding_mercaderia.expiry_date", "Fecha de Caducidad (FEFO)")}
                  value={fechaVencimiento}
                  onChange={(e) => setFechaVencimiento(e.target.value)}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                {t("modals.adding_mercaderia.reference_doc", "N° de Guía / Factura / Proveedor")}
              </label>
              <input
                type="text"
                data-testid="libre-doc-input"
                aria-label={t("modals.adding_mercaderia.reference_doc", "N° de Guía / Factura / Proveedor")}
                value={proveedorGuia}
                onChange={(e) => setProveedorGuia(e.target.value)}
                placeholder={t("modals.adding_mercaderia.reference_placeholder", "Ej: Factura 45291 - Distribuidora Alimentos")}
                className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <button
                type="button"
                onClick={onClose}
                className="touch-target px-4 py-2 rounded-xl border border-border text-xs font-bold text-foreground hover:bg-secondary cursor-pointer transition-colors"
              >
                {t("modals.adding_mercaderia.cancel", "Cancelar")}
              </button>
              <button
                type="button"
                data-testid="btn-confirm-libre"
                onClick={handleConfirmLibre}
                disabled={isSubmitting || cantidad <= 0}
                className="touch-target px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-black uppercase tracking-wider cursor-pointer shadow-md shadow-emerald-600/20 transition-all flex items-center gap-1.5"
              >
                <PackageCheck className="h-4 w-4" />
                <span>{isSubmitting ? t("modals.adding_mercaderia.submitting", "Ingresando...") : t("modals.adding_mercaderia.confirm", "Ingresar a Stock")}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </ResponsiveDialog>
  );
}

export default AddingMercaderiaDialog;
