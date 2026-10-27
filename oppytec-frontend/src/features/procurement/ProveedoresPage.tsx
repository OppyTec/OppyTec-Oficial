/**
 * oppytec-frontend/src/features/procurement/ProveedoresPage.tsx
 * Página Principal del Directorio de Proveedores con ADN Visual Legacy y Mobile-First.
 * SectionHeader temático (#059669), Buscador predictivo, Filtro por estado,
 * Selector Dual Lista/Tarjetas persistente y modales 360° / Catálogo / Creación.
 */

import { useState, useCallback, useMemo } from "react";
import {
  Truck,
  Plus,
  Search,
  LayoutGrid,
  List,
  X,
  AlertTriangle,
} from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { useProveedores } from "./hooks/useProveedores";
import { ProveedoresTable } from "./components/ProveedoresTable";
import { ProveedoresCards } from "./components/ProveedoresCards";
import { ProveedorDialog } from "./dialogs/ProveedorDialog";
import { ProveedorProductosDialog } from "./dialogs/ProveedorProductosDialog";
import { ProveedorDashboardDialog } from "./dialogs/ProveedorDashboardDialog";
import type {
  CreateProveedorPayload,
  Proveedor,
  UpdateProveedorPayload,
} from "./types";

export type ProveedoresViewMode = "table" | "cards";

const VIEW_MODE_STORAGE_KEY = "oppytec_proveedores_view_mode";

export interface ProveedoresPageProps {
  readonly isSubTab?: boolean;
}

export function ProveedoresPage({ isSubTab = false }: ProveedoresPageProps) {
  const isMobile = useIsMobile();

  // Hook de Proveedores
  const {
    proveedores,
    isLoadingSuppliers,
    filters,
    setFilter,
    createProveedor,
    isCreatingProveedor,
    updateProveedor,
    isUpdatingProveedor,
    deleteProveedor,
    isDeletingProveedor,
  } = useProveedores();

  // Persistencia de Vista Dual (Tabla / Tarjetas)
  const [viewMode, setViewModeState] = useState<ProveedoresViewMode>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      const saved = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
      if (saved === "table" || saved === "cards") {
        return saved;
      }
    }
    return "table";
  });

  const setViewMode = useCallback((mode: ProveedoresViewMode) => {
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
  const [isCreateOrEditDialogOpen, setIsCreateOrEditDialogOpen] = useState(false);
  const [proveedorToEdit, setProveedorToEdit] = useState<Proveedor | null>(null);

  const [catalogDialogOpen, setCatalogDialogOpen] = useState(false);
  const [selectedProveedorForCatalog, setSelectedProveedorForCatalog] = useState<Proveedor | null>(null);

  const [dashboardDialogOpen, setDashboardDialogOpen] = useState(false);
  const [selectedProveedorForDashboard, setSelectedProveedorForDashboard] = useState<Proveedor | null>(null);

  // Modal confirmación eliminar
  const [proveedorToDelete, setProveedorToDelete] = useState<Proveedor | null>(null);

  // Handlers de modales
  const handleOpenCreate = () => {
    setProveedorToEdit(null);
    setIsCreateOrEditDialogOpen(true);
  };

  const handleOpenEdit = (prov: Proveedor) => {
    setProveedorToEdit(prov);
    setIsCreateOrEditDialogOpen(true);
  };

  const handleOpenCatalog = (prov: Proveedor) => {
    setSelectedProveedorForCatalog(prov);
    setCatalogDialogOpen(true);
  };

  const handleOpenDashboard = (prov: Proveedor) => {
    setSelectedProveedorForDashboard(prov);
    setDashboardDialogOpen(true);
  };

  const handleSaveProveedor = async (
    payload: CreateProveedorPayload | UpdateProveedorPayload,
    id?: number
  ) => {
    if (id) {
      await updateProveedor({ id, payload: payload as UpdateProveedorPayload });
    } else {
      await createProveedor(payload as CreateProveedorPayload);
    }
  };

  const handleConfirmDelete = async () => {
    if (!proveedorToDelete) return;
    await deleteProveedor(proveedorToDelete.id);
    setProveedorToDelete(null);
  };

  // Conteo de proveedores activos
  const activeCount = useMemo(() => {
    return proveedores.filter((p) => p.estado === "ACTIVO").length;
  }, [proveedores]);

  return (
    <div
      data-testid="proveedores-page-root"
      className="space-y-6 animate-in fade-in duration-300 pb-12"
    >
      {/* 1. SECTION HEADER (Sólo si no se incrusta como sub-pestaña interna) */}
      {!isSubTab && (
        <div data-testid="proveedores-section-header">
          <SectionHeader
            title="Directorio de Proveedores"
            subtitle="Gestión de alianzas comerciales, tiempos de entrega y catálogo pactado"
            icon={Truck}
            color="#059669"
            center={true}
          />
        </div>
      )}

      {/* 2. BARRA DE CONTROL Y HERRAMIENTAS */}
      <div className="glass-card flex flex-col gap-3 rounded-2xl border border-border p-3.5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        {/* Buscador predictivo en tiempo real */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            data-testid="input-search-proveedores"
            value={filters.search}
            onChange={(e) => setFilter("search", e.target.value)}
            placeholder="Buscar por RUT, razón social, fantasía o contacto..."
            className="w-full rounded-xl border border-border bg-background py-2.5 pl-10 pr-9 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
          {filters.search && (
            <button
              type="button"
              onClick={() => setFilter("search", "")}
              data-testid="btn-clear-search-proveedores"
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground hover:bg-muted"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Filtros por estado y Selector dual */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Selector de filtros de estado */}
          <div className="inline-flex rounded-xl border border-border bg-muted/40 p-0.5 text-xs">
            {(["TODOS", "ACTIVO", "INACTIVO"] as const).map((est) => {
              const isActive = (filters.estado ?? "TODOS") === est;
              return (
                <button
                  key={est}
                  type="button"
                  data-testid={`filter-estado-${est.toLowerCase()}`}
                  onClick={() => setFilter("estado", est)}
                  className={`min-h-[36px] rounded-lg px-3 py-1 font-semibold transition-all ${
                    isActive
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {est === "TODOS" ? "Todos" : est === "ACTIVO" ? "Activos" : "Inactivos"}
                </button>
              );
            })}
          </div>

          {/* Selector de Vista: Lista / Tarjetas */}
          <div className="inline-flex rounded-xl border border-border bg-muted/40 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("table")}
              data-testid="btn-view-mode-table"
              title="Vista en Tabla"
              className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
                viewMode === "table"
                  ? "bg-background text-primary shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <List className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("cards")}
              data-testid="btn-view-mode-cards"
              title="Vista en Tarjetas Mobile-First"
              className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
                viewMode === "cards"
                  ? "bg-background text-primary shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>

          {/* Botón primario: Nuevo Proveedor */}
          <button
            type="button"
            onClick={handleOpenCreate}
            data-testid="btn-nuevo-proveedor"
            className="flex min-h-[44px] items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-emerald-700 active:scale-95 ml-auto sm:ml-0"
          >
            <Plus className="h-4 w-4" />
            <span>+ Nuevo Proveedor</span>
          </button>
        </div>
      </div>

      {/* 3. RESUMEN RÁPIDO DE CONTEO */}
      <div className="flex items-center justify-between px-1 text-xs text-muted-foreground">
        <div>
          Mostrando <strong className="text-foreground">{proveedores.length}</strong> proveedores
          {filters.estado !== "TODOS" && ` (filtro: ${filters.estado})`}
        </div>
        <div>
          <strong className="text-emerald-600 dark:text-emerald-400">{activeCount}</strong> activos
        </div>
      </div>

      {/* 4. CONTENIDO: TABLA O TARJETAS */}
      {viewMode === "table" ? (
        <ProveedoresTable
          proveedores={proveedores}
          isLoading={isLoadingSuppliers}
          onOpenDashboard={handleOpenDashboard}
          onOpenCatalog={handleOpenCatalog}
          onEdit={handleOpenEdit}
          onDelete={(prov) => setProveedorToDelete(prov)}
        />
      ) : (
        <ProveedoresCards
          proveedores={proveedores}
          isLoading={isLoadingSuppliers}
          onOpenDashboard={handleOpenDashboard}
          onOpenCatalog={handleOpenCatalog}
          onEdit={handleOpenEdit}
          onDelete={(prov) => setProveedorToDelete(prov)}
        />
      )}

      {/* 5. MODAL: ALTA Y EDICIÓN DE PROVEEDOR */}
      <ProveedorDialog
        open={isCreateOrEditDialogOpen}
        proveedor={proveedorToEdit}
        onClose={() => setIsCreateOrEditDialogOpen(false)}
        onSave={handleSaveProveedor}
        isSubmitting={isCreatingProveedor || isUpdatingProveedor}
      />

      {/* 6. MODAL: CATÁLOGO PACTADO */}
      <ProveedorProductosDialog
        open={catalogDialogOpen}
        proveedor={selectedProveedorForCatalog}
        onClose={() => {
          setCatalogDialogOpen(false);
          setSelectedProveedorForCatalog(null);
        }}
      />

      {/* 7. MODAL: DASHBOARD 360° */}
      <ProveedorDashboardDialog
        open={dashboardDialogOpen}
        proveedor={selectedProveedorForDashboard}
        onClose={() => {
          setDashboardDialogOpen(false);
          setSelectedProveedorForDashboard(null);
        }}
      />

      {/* 8. MODAL: CONFIRMACIÓN DE ELIMINACIÓN */}
      {proveedorToDelete && (
        <ResponsiveDialog
          open={Boolean(proveedorToDelete)}
          onClose={() => setProveedorToDelete(null)}
          isMobile={isMobile}
          maxWidth="max-w-md"
          title="Desactivar Proveedor"
          description={`¿Estás seguro de que deseas desactivar al proveedor "${proveedorToDelete.razon_social}"?`}
        >
          <div className="flex flex-col gap-4 pt-2">
            <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <span>
                El proveedor quedará en estado <strong>INACTIVO</strong> y no podrá ser seleccionado para nuevas órdenes de compra hasta reactivarse.
              </span>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-border/70 pt-3">
              <button
                type="button"
                onClick={() => setProveedorToDelete(null)}
                className="min-h-[44px] rounded-xl border border-border px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeletingProveedor}
                data-testid="btn-confirm-delete-proveedor"
                className="min-h-[44px] flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-rose-700 active:scale-95 disabled:opacity-50"
              >
                <span>{isDeletingProveedor ? "Desactivando..." : "Sí, Desactivar"}</span>
              </button>
            </div>
          </div>
        </ResponsiveDialog>
      )}
    </div>
  );
}
