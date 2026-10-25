// oppytec-frontend/src/features/inventory/stock/dialogs/SolicitudesDialog.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  ShoppingBag,
  Plus,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import type { StockItem } from "../../types";

export interface SolicitudesDialogProps {
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
  readonly onRequestCreated?: (solicitud: unknown) => void;
}

export type SolicitudState = "pendientes" | "en_ruta" | "recibidas" | "canceladas";

interface SolicitudItem {
  id: number;
  codigo: string;
  producto_nombre: string;
  producto_id: number;
  bodega_origen_nombre: string;
  bodega_destino_nombre: string;
  cantidad: number;
  unidad: string;
  fecha: string;
  estado: SolicitudState;
  urgencia: "normal" | "alta" | "critica";
}

const INITIAL_MOCK_SOLICITUDES: SolicitudItem[] = [
  {
    id: 1,
    codigo: "SOL-2026-0012",
    producto_nombre: "Salmón Atlántico Fresco",
    producto_id: 2,
    bodega_origen_nombre: "Bodega Central / Proveedor",
    bodega_destino_nombre: "Cámara de Frío Principal",
    cantidad: 15,
    unidad: "kg",
    fecha: "2026-10-25",
    estado: "pendientes",
    urgencia: "critica",
  },
  {
    id: 2,
    codigo: "SOL-2026-0010",
    producto_nombre: "Vino Cabernet Sauvignon Reserva",
    producto_id: 5,
    bodega_origen_nombre: "Bodega Seca Central",
    bodega_destino_nombre: "Barra & Coctelería",
    cantidad: 24,
    unidad: "botellas",
    fecha: "2026-10-24",
    estado: "en_ruta",
    urgencia: "alta",
  },
  {
    id: 3,
    codigo: "SOL-2026-0008",
    producto_nombre: "Lomo Vetado Angus Premium",
    producto_id: 1,
    bodega_origen_nombre: "Cámara de Frío Principal",
    bodega_destino_nombre: "Cocina Caliente",
    cantidad: 10,
    unidad: "kg",
    fecha: "2026-10-23",
    estado: "recibidas",
    urgencia: "normal",
  },
  {
    id: 4,
    codigo: "SOL-2026-0005",
    producto_nombre: "Arroz Grano Largo Selección",
    producto_id: 4,
    bodega_origen_nombre: "Bodega Seca Central",
    bodega_destino_nombre: "Cocina Caliente",
    cantidad: 50,
    unidad: "kg",
    fecha: "2026-10-20",
    estado: "canceladas",
    urgencia: "normal",
  },
];

const TAB_BUTTONS: Array<{
  readonly key: SolicitudState;
  readonly defaultLabel: string;
  readonly activeClass: string;
}> = [
  {
    key: "pendientes",
    defaultLabel: "Pendientes",
    activeClass: "bg-purple-600 text-white border-purple-600 shadow-md shadow-purple-500/20",
  },
  {
    key: "en_ruta",
    defaultLabel: "En Ruta",
    activeClass: "bg-amber-500 text-black border-amber-500 shadow-md shadow-amber-500/20",
  },
  {
    key: "recibidas",
    defaultLabel: "Recibidas",
    activeClass: "bg-emerald-600 text-white border-emerald-600 shadow-md shadow-emerald-500/20",
  },
  {
    key: "canceladas",
    defaultLabel: "Canceladas",
    activeClass: "bg-red-600 text-white border-red-600 shadow-md shadow-red-500/20",
  },
];

export function SolicitudesDialog({
  open,
  onClose,
  stockItems,
  bodegas,
  initialProduct,
  onRequestCreated,
}: SolicitudesDialogProps) {
  const { t } = useTranslation("inventory");
  const [activeTab, setActiveTab] = useState<SolicitudState>("pendientes");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [solicitudes, setSolicitudes] = useState<SolicitudItem[]>(INITIAL_MOCK_SOLICITUDES);

  // Estados del Formulario de Nueva Solicitud
  const [newProductoId, setNewProductoId] = useState<number>(() => {
    return initialProduct?.producto_id ?? stockItems[0]?.producto_id ?? 1;
  });
  const [newBodegaDestinoId, setNewBodegaDestinoId] = useState<number>(() => {
    return initialProduct?.bodega_id ?? bodegas[0]?.id ?? 1;
  });
  const [newCantidad, setNewCantidad] = useState<number>(5);
  const [newUrgencia, setNewUrgencia] = useState<"normal" | "alta" | "critica">("alta");
  const [newNotas, setNewNotas] = useState<string>("");

  useEffect(() => {
    if (open) {
      if (initialProduct) {
        setNewProductoId(initialProduct.producto_id);
        setNewBodegaDestinoId(initialProduct.bodega_id);
        setShowCreateForm(true);
      } else {
        setShowCreateForm(false);
      }
    }
  }, [open, initialProduct]);

  const selectedProductObj = useMemo(() => {
    return stockItems.find((it) => it.producto_id === newProductoId);
  }, [stockItems, newProductoId]);

  const filteredSolicitudes = useMemo(() => {
    return solicitudes.filter((s) => s.estado === activeTab);
  }, [solicitudes, activeTab]);

  const handleCreateSolicitud = () => {
    if (newCantidad <= 0) {
      toast.error(t("modals.solicitudes.toast_invalid_qty", "Ingrese una cantidad válida"));
      return;
    }

    const prod = stockItems.find((it) => it.producto_id === newProductoId);
    const dest = bodegas.find((b) => b.id === newBodegaDestinoId);

    const newSol: SolicitudItem = {
      id: Date.now(),
      codigo: `SOL-2026-${String(Math.floor(Math.random() * 9000) + 1000)}`,
      producto_nombre: prod?.nombre ?? "Insumo",
      producto_id: newProductoId,
      bodega_origen_nombre: "Bodega Central / Proveedor",
      bodega_destino_nombre: dest?.nombre ?? "Bodega",
      cantidad: newCantidad,
      unidad: prod?.unidad_medida ?? "u",
      fecha: new Date().toISOString().split("T")[0] ?? "2026-10-25",
      estado: "pendientes",
      urgencia: newUrgencia,
    };

    setSolicitudes((prev) => [newSol, ...prev]);
    toast.success(t("modals.solicitudes.toast_success", { code: newSol.codigo, defaultValue: `Solicitud ${newSol.codigo} emitida exitosamente` }));
    onRequestCreated?.(newSol);
    setShowCreateForm(false);
    setActiveTab("pendientes");
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("modals.solicitudes.title", "Solicitudes de Reposición Interna")}
      description={t("modals.solicitudes.description", "Control y seguimiento de pedidos de abastecimiento inter-bodega y compras")}
      maxWidth="max-w-2xl"
    >
      <div data-testid="dialog-solicitudes-container" className="space-y-4 py-2">
        {/* Barra Superior con Pestañas y Botón Nueva Solicitud */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 border-b border-border pb-3">
          {/* Pestañas de estado idénticas a Legacy */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 flex-1">
            {TAB_BUTTONS.map((btn) => {
              const count = solicitudes.filter((s) => s.estado === btn.key).length;
              const isActive = activeTab === btn.key && !showCreateForm;
              return (
                <button
                  key={btn.key}
                  type="button"
                  data-testid={`solicitudes-tab-${btn.key}`}
                  onClick={() => {
                    setActiveTab(btn.key);
                    setShowCreateForm(false);
                  }}
                  className={cn(
                    "touch-target px-2.5 py-1.5 text-[11px] font-black uppercase tracking-wider rounded-xl border transition-all cursor-pointer flex items-center justify-center gap-1.5",
                    isActive
                      ? btn.activeClass
                      : "bg-background text-muted-foreground border-border hover:bg-muted/60"
                  )}
                >
                  <span>{t(`modals.solicitudes.tabs.${btn.key}`, btn.defaultLabel)}</span>
                  <span className="font-mono text-[10px] px-1 rounded-full bg-black/10 dark:bg-white/10">
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Botón Nueva Solicitud */}
          <button
            type="button"
            data-testid="btn-toggle-nueva-solicitud"
            onClick={() => setShowCreateForm((prev) => !prev)}
            className={cn(
              "touch-target px-3.5 py-2 rounded-xl text-xs font-black uppercase tracking-wider cursor-pointer transition-all flex items-center justify-center gap-1.5 shrink-0",
              showCreateForm
                ? "bg-secondary text-secondary-foreground border border-border"
                : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs shadow-primary/20"
            )}
          >
            <Plus className="h-4 w-4" />
            <span>{showCreateForm ? t("modals.solicitudes.btn_view_list", "Ver Listado") : t("modals.solicitudes.btn_new_request", "+ Nueva Solicitud")}</span>
          </button>
        </div>

        {/* VISTA 1: FORMULARIO DE NUEVA SOLICITUD */}
        {showCreateForm ? (
          <div
            data-testid="form-nueva-solicitud"
            className="p-4 rounded-2xl border border-primary/20 bg-primary/5 space-y-3"
          >
            <h4 className="text-xs font-black uppercase tracking-wider text-primary flex items-center gap-1.5">
              <ShoppingBag className="h-4 w-4" />
              <span>{t("modals.solicitudes.form_title", "Emitir Requerimiento de Abastecimiento")}</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.solicitudes.replenish_item", "Insumo a Reponer")}
                </label>
                <select
                  data-testid="solicitud-product-select"
                  aria-label={t("modals.solicitudes.replenish_item", "Insumo a Reponer")}
                  value={newProductoId}
                  onChange={(e) => setNewProductoId(Number(e.target.value))}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {stockItems.map((it) => (
                    <option key={`sol-p-${it.producto_id}`} value={it.producto_id}>
                      {it.nombre} ({it.sku})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.solicitudes.requesting_warehouse", "Bodega Solicitante (Destino)")}
                </label>
                <select
                  data-testid="solicitud-bodega-select"
                  aria-label={t("modals.solicitudes.requesting_warehouse", "Bodega Solicitante (Destino)")}
                  value={newBodegaDestinoId}
                  onChange={(e) => setNewBodegaDestinoId(Number(e.target.value))}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {bodegas.map((b) => (
                    <option key={`sol-wh-${b.id}`} value={b.id}>
                      {b.nombre}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.solicitudes.required_qty", "Cantidad Requerida")}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    data-testid="solicitud-quantity-input"
                    aria-label={t("modals.solicitudes.required_qty", "Cantidad Requerida")}
                    step="any"
                    min="0.1"
                    value={newCantidad || ""}
                    onChange={(e) => setNewCantidad(Number(e.target.value))}
                    className="w-full h-10 px-3 rounded-xl border border-border bg-card text-sm font-mono font-bold outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground">
                    {selectedProductObj?.unidad_medida ?? "u"}
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  {t("modals.solicitudes.urgency_level", "Nivel de Urgencia")}
                </label>
                <select
                  data-testid="solicitud-urgency-select"
                  aria-label={t("modals.solicitudes.urgency_level", "Nivel de Urgencia")}
                  value={newUrgencia}
                  onChange={(e) => setNewUrgencia(e.target.value as "normal" | "alta" | "critica")}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold cursor-pointer outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="normal">{t("modals.solicitudes.urgency_normal", "Normal (Ciclo habitual)")}</option>
                  <option value="alta">{t("modals.solicitudes.urgency_high", "Alta (Stock bajo mínimo)")}</option>
                  <option value="critica">{t("modals.solicitudes.urgency_critical", "Crítica (Quiebre inmediato)")}</option>
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                {t("modals.solicitudes.notes_label", "Observaciones / Motivo del pedido")}
              </label>
              <input
                type="text"
                data-testid="solicitud-notes-input"
                aria-label={t("modals.solicitudes.notes_label", "Observaciones / Motivo del pedido")}
                value={newNotas}
                onChange={(e) => setNewNotas(e.target.value)}
                placeholder={t("modals.solicitudes.notes_placeholder", "Ej: Evento de fin de semana requiere stock de contingencia...")}
                className="w-full h-10 px-3 rounded-xl border border-border bg-card text-xs outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="touch-target px-4 py-2 rounded-xl border border-border text-xs font-bold text-foreground hover:bg-secondary cursor-pointer"
              >
                {t("modals.solicitudes.cancel", "Cancelar")}
              </button>
              <button
                type="button"
                data-testid="btn-submit-solicitud"
                onClick={handleCreateSolicitud}
                className="touch-target px-5 py-2 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-black uppercase tracking-wider cursor-pointer shadow-md shadow-primary/20"
              >
                {t("modals.solicitudes.submit", "Emitir Pedido")}
              </button>
            </div>
          </div>
        ) : (
          /* VISTA 2: LISTADO DE SOLICITUDES POR ESTADO */
          <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
            {filteredSolicitudes.length === 0 ? (
              <div
                data-testid="solicitudes-empty-state"
                className="py-12 text-center text-muted-foreground border-2 border-dashed border-border rounded-2xl bg-muted/10 space-y-2"
              >
                <ShoppingBag className="h-8 w-8 mx-auto text-muted-foreground/60" />
                <p className="text-xs font-bold">{t("modals.solicitudes.empty_state", "No hay solicitudes en este estado")}</p>
                <p className="text-[11px] text-muted-foreground">
                  {t("modals.solicitudes.empty_hint", "Utiliza el botón \"+ Nueva Solicitud\" para emitir un requerimiento")}
                </p>
              </div>
            ) : (
              filteredSolicitudes.map((item) => (
                <div
                  key={item.id}
                  data-testid={`solicitud-item-${item.id}`}
                  className="p-3.5 rounded-xl border border-border bg-card hover:border-primary/40 transition-all space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">
                        {item.producto_nombre}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-muted font-bold text-muted-foreground">
                        {item.codigo}
                      </span>
                    </div>

                    {item.urgencia === "critica" && (
                      <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-destructive/15 text-destructive border border-destructive/20 animate-pulse">
                        {t("modals.solicitudes.urgency_critical_badge", "Urgencia Crítica")}
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center justify-between text-xs text-muted-foreground gap-2">
                    <div className="flex items-center gap-2">
                      <span>{item.bodega_origen_nombre}</span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      <strong className="text-foreground">{item.bodega_destino_nombre}</strong>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-foreground">
                        {item.cantidad} {item.unidad}
                      </span>
                      <span>•</span>
                      <span>{item.fecha}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Pie de modal */}
        <div className="flex justify-end pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="touch-target px-4 py-2 rounded-xl bg-secondary text-secondary-foreground text-xs font-bold hover:bg-secondary/80 cursor-pointer"
          >
            {t("modals.solicitudes.close", "Cerrar")}
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}

export default SolicitudesDialog;
