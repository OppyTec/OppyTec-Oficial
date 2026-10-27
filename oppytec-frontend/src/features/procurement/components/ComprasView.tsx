/**
 * oppytec-frontend/src/features/procurement/components/ComprasView.tsx
 * Vista Integradora de Abastecimiento, Compras y Proveedores con ADN Visual Legacy.
 * SubTabs: Dashboard (BarChart3), Listado (FileText), Proveedores (Truck), Catálogo (Tag).
 * Selector Dual Lista / Tarjetas, Banner de Borrador y Mobile-First (Touch targets >= 44px).
 */

import { useState, useCallback } from "react";
import {
  BarChart3,
  FileText,
  Truck,
  Tag,
  Plus,
  Search,
  LayoutGrid,
  List,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useCompras } from "../hooks/useCompras";
import { useProveedores } from "../hooks/useProveedores";
import { ComprasDashboard } from "./ComprasDashboard";
import { CompraTable } from "./CompraTable";
import { CompraCards } from "./CompraCards";
import { CatalogoPrecios } from "./CatalogoPrecios";
import { CompraDialog } from "../dialogs/CompraDialog";
import { MercaderiaReceptionDialog } from "../dialogs/MercaderiaReceptionDialog";
import { IncidenciaDialog } from "../dialogs/IncidenciaDialog";
import { CompraDetalleModal } from "../dialogs/CompraDetalleModal";
import { ProveedoresPage } from "../ProveedoresPage";
import type {
  CompraEstado,
  CompraOrder,
  CreateOrderPayload,
  ReceiveGoodsPayload,
  RegisterIncidencePayload,
} from "../types";

export type ComprasSubTab = "dashboard" | "listado" | "proveedores" | "catalogo";
export type ComprasViewMode = "table" | "cards";

const VIEW_MODE_STORAGE_KEY = "oppytec_compras_view_mode";

const STATUS_FILTERS: (CompraEstado | "TODOS")[] = [
  "TODOS",
  "BORRADOR",
  "SOLICITADA",
  "EN_CAMINO",
  "RECIBIDA_PARCIAL",
  "RECIBIDA_TOTAL",
  "CANCELADA",
];

export function ComprasView() {
  const [activeSubTab, setActiveSubTab] = useState<ComprasSubTab>("listado");

  // Hook de Compras
  const {
    orders,
    dashboard,
    isLoadingOrders,
    isLoadingDashboard,
    refetchDashboard,
    filters,
    setFilter,
    draftData,
    hasDraft,
    saveDraft,
    clearDraft,
    createOrder,
    isCreatingOrder,
    receiveGoods,
    isReceivingGoods,
    registerIncidence,
    isRegisteringIncidence,
    cancelOrder,
  } = useCompras();

  // Hook de Proveedores
  const {
    proveedores: suppliers = [],
    catalog = [],
  } = useProveedores();

  // Persistencia de Vista Dual (Tabla / Tarjetas)
  const [viewMode, setViewModeState] = useState<ComprasViewMode>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      const saved = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
      if (saved === "table" || saved === "cards") {
        return saved;
      }
    }
    return "table";
  });

  const setViewMode = useCallback((mode: ComprasViewMode) => {
    setViewModeState(mode);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
      } catch {
        // Safe fallback
      }
    }
  }, []);

  // Modales
  const [isCompraDialogOpen, setIsCompraDialogOpen] = useState(false);
  const [activeDraftToLoad, setActiveDraftToLoad] = useState<typeof draftData>(null);

  const [selectedOrderForDetail, setSelectedOrderForDetail] = useState<CompraOrder | null>(null);
  const [selectedOrderForReception, setSelectedOrderForReception] = useState<CompraOrder | null>(null);
  const [selectedOrderForIncidence, setSelectedOrderForIncidence] = useState<CompraOrder | null>(null);

  // Manejadores
  const handleOpenNewCompra = () => {
    setActiveDraftToLoad(null);
    setIsCompraDialogOpen(true);
  };

  const handleRecoverDraft = () => {
    setActiveDraftToLoad(draftData);
    setIsCompraDialogOpen(true);
  };

  const handleCreateOrderSubmit = async (payload: CreateOrderPayload) => {
    try {
      await createOrder(payload);
      setIsCompraDialogOpen(false);
    } catch {
      // Error manejado en hook useCompras
    }
  };

  const handleReceiveGoodsSubmit = async (payload: ReceiveGoodsPayload) => {
    try {
      await receiveGoods(payload);
      setSelectedOrderForReception(null);
    } catch {
      // Error manejado en hook useCompras
    }
  };

  const handleRegisterIncidenceSubmit = async (payload: RegisterIncidencePayload) => {
    try {
      await registerIncidence(payload);
      setSelectedOrderForIncidence(null);
    } catch {
      // Error manejado en hook useCompras
    }
  };

  const handleCancelOrder = async (order: CompraOrder) => {
    if (!order.id) return;
    const confirmPrompt = window.confirm(
      `¿Está seguro de que desea cancelar la orden ${order.numero_orden || order.po_number}?`
    );
    if (confirmPrompt) {
      await cancelOrder({ order_id: order.id, motivo: "Cancelación solicitada por usuario" });
    }
  };

  return (
    <div data-testid="compras-view" className="space-y-6">
      {/* Banner Interactivo de Borrador Persistente */}
      {hasDraft && (
        <div
          data-testid="compras-draft-banner"
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3.5 md:px-5 md:py-3 text-foreground shadow-sm backdrop-blur-sm"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30">
              <Sparkles className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <p className="text-xs font-bold text-foreground md:text-sm">
                Borrador de orden de compra sin guardar
              </p>
              <p className="text-[11px] text-muted-foreground">
                Se detectó una orden en progreso con {draftData?.items?.length ?? 0} ítems.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 self-end sm:self-center">
            <button
              type="button"
              onClick={clearDraft}
              data-testid="discard-draft-btn"
              className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-rose-500 active:scale-95 cursor-pointer"
            >
              <Trash2 className="h-4 w-4" />
              <span>Descartar</span>
            </button>
            <button
              type="button"
              onClick={handleRecoverDraft}
              data-testid="recover-draft-btn"
              className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-amber-700 active:scale-95 cursor-pointer"
            >
              <span>Recuperar Borrador</span>
            </button>
          </div>
        </div>
      )}

      {/* SubTabs de Navegación Legacy */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {/* SubTab: Dashboard */}
          <button
            type="button"
            onClick={() => setActiveSubTab("dashboard")}
            data-testid="compras-subtab-dashboard"
            className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all cursor-pointer ${
              activeSubTab === "dashboard"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            <span>Dashboard</span>
          </button>

          {/* SubTab: Listado */}
          <button
            type="button"
            onClick={() => setActiveSubTab("listado")}
            data-testid="compras-subtab-listado"
            className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all cursor-pointer ${
              activeSubTab === "listado"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
            }`}
          >
            <FileText className="h-4 w-4" />
            <span>Listado de Órdenes</span>
          </button>

          {/* SubTab: Proveedores */}
          <button
            type="button"
            onClick={() => setActiveSubTab("proveedores")}
            data-testid="compras-subtab-proveedores"
            className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all cursor-pointer ${
              activeSubTab === "proveedores"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
            }`}
          >
            <Truck className="h-4 w-4" />
            <span>Proveedores</span>
          </button>

          {/* SubTab: Catálogo */}
          <button
            type="button"
            onClick={() => setActiveSubTab("catalogo")}
            data-testid="compras-subtab-catalogo"
            className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all cursor-pointer ${
              activeSubTab === "catalogo"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
            }`}
          >
            <Tag className="h-4 w-4" />
            <span>Catálogo Pactado</span>
          </button>
        </div>

        {/* Botón Primario: + Nueva Compra */}
        <button
          type="button"
          onClick={handleOpenNewCompra}
          data-testid="nueva-compra-btn"
          className="touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-md hover:bg-primary/90 active:scale-95 cursor-pointer ml-auto"
        >
          <Plus className="h-4 w-4" />
          <span>+ Nueva Compra</span>
        </button>
      </div>

      {/* RENDERIZADO CONDICIONAL POR SUBTAB */}

      {/* 1. DASHBOARD */}
      {activeSubTab === "dashboard" && (
        <ComprasDashboard
          dashboard={dashboard}
          isLoading={isLoadingDashboard}
          onRefresh={refetchDashboard}
        />
      )}

      {/* 2. LISTADO DE ÓRDENES */}
      {activeSubTab === "listado" && (
        <div className="space-y-4">
          {/* Barra de Búsqueda, Filtros y Switcher Dual */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            {/* Buscador en tiempo real */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                data-testid="compras-search-input"
                placeholder="Buscar por N° Orden o Proveedor..."
                value={filters.search ?? ""}
                onChange={(e) => setFilter("search", e.target.value)}
                className="touch-target w-full rounded-xl border border-border bg-card py-2.5 pl-10 pr-4 text-xs text-foreground placeholder:text-muted-foreground shadow-sm focus:border-primary focus:outline-none min-h-[44px]"
              />
            </div>

            {/* Switcher de Vista Dual: Lista / Tarjetas */}
            <div className="flex items-center gap-1.5 self-end sm:self-center">
              <button
                type="button"
                onClick={() => setViewMode("table")}
                data-testid="view-mode-table-btn"
                title="Vista de Tabla"
                className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border transition-all cursor-pointer ${
                  viewMode === "table"
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground hover:bg-muted"
                }`}
              >
                <List className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={() => setViewMode("cards")}
                data-testid="view-mode-cards-btn"
                title="Vista de Tarjetas Mobile-First"
                className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border transition-all cursor-pointer ${
                  viewMode === "cards"
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground hover:bg-muted"
                }`}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Filtros por Estado (Pills Horizontales) */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {STATUS_FILTERS.map((st) => {
              const isSelected = (filters.status ?? "TODOS") === st;
              return (
                <button
                  key={st}
                  type="button"
                  onClick={() => setFilter("status", st)}
                  data-testid={`filter-status-${st}`}
                  className={`touch-target inline-flex min-h-[44px] shrink-0 items-center rounded-full border px-3 py-1.5 text-[11px] font-bold transition-all cursor-pointer ${
                    isSelected
                      ? "border-primary bg-primary text-primary-foreground shadow-sm"
                      : "border-border bg-card text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {st === "TODOS" ? "Todos los Estados" : st.replace("_", " ")}
                </button>
              );
            })}
          </div>

          {/* Vista Tabla o Tarjetas */}
          {viewMode === "table" ? (
            <CompraTable
              orders={orders}
              isLoading={isLoadingOrders}
              onView={(order) => setSelectedOrderForDetail(order)}
              onReceive={(order) => setSelectedOrderForReception(order)}
              onIncidence={(order) => setSelectedOrderForIncidence(order)}
              onCancel={handleCancelOrder}
            />
          ) : (
            <CompraCards
              orders={orders}
              isLoading={isLoadingOrders}
              onView={(order) => setSelectedOrderForDetail(order)}
              onReceive={(order) => setSelectedOrderForReception(order)}
              onIncidence={(order) => setSelectedOrderForIncidence(order)}
              onCancel={handleCancelOrder}
            />
          )}
        </div>
      )}

      {/* 3. PROVEEDORES */}
      {activeSubTab === "proveedores" && (
        <div data-testid="proveedores-tab-content">
          <ProveedoresPage isSubTab={true} />
        </div>
      )}

      {/* 4. CATÁLOGO PACTADO */}
      {activeSubTab === "catalogo" && (
        <CatalogoPrecios
          proveedores={suppliers}
          items={catalog}
          onSelectProducto={(prod) => {
            saveDraft({
              proveedor_id: prod.proveedor_id,
              items: [
                {
                  producto_id: prod.producto_id,
                  producto_nombre: prod.producto_nombre || "",
                  cantidad_solicitada: 10,
                  costo_unitario_neto: Number(prod.precio_pactado ?? prod.ultimo_costo_neto ?? 0),
                  subtotal_linea: Number(prod.precio_pactado ?? prod.ultimo_costo_neto ?? 0) * 10,
                },
              ],
            });
            handleRecoverDraft();
          }}
        />
      )}

      {/* MODAL 1: Nueva / Editar Compra */}
      <CompraDialog
        open={isCompraDialogOpen}
        onClose={() => setIsCompraDialogOpen(false)}
        onSave={handleCreateOrderSubmit}
        initialDraft={activeDraftToLoad}
        onSaveDraft={saveDraft}
        proveedores={suppliers}
        isSubmitting={isCreatingOrder}
      />

      {/* MODAL 2: Recepción de Mercadería */}
      <MercaderiaReceptionDialog
        open={Boolean(selectedOrderForReception)}
        order={selectedOrderForReception}
        onClose={() => setSelectedOrderForReception(null)}
        onConfirm={handleReceiveGoodsSubmit}
        isSubmitting={isReceivingGoods}
      />

      {/* MODAL 3: Registro de Incidencias */}
      <IncidenciaDialog
        open={Boolean(selectedOrderForIncidence)}
        order={selectedOrderForIncidence}
        onClose={() => setSelectedOrderForIncidence(null)}
        onConfirm={handleRegisterIncidenceSubmit}
        isSubmitting={isRegisteringIncidence}
      />

      {/* MODAL 4: Inspección de Detalle */}
      <CompraDetalleModal
        open={Boolean(selectedOrderForDetail)}
        order={selectedOrderForDetail}
        onClose={() => setSelectedOrderForDetail(null)}
      />
    </div>
  );
}
