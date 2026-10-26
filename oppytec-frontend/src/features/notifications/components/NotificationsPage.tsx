import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Inbox,
  RefreshCw,
} from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { TablePagination } from "@/shared/components/ui/TablePagination";
import { usePersistentSearch } from "@/shared/hooks/usePersistentSearch";
import { useApprovals, usePendingCount } from "../hooks";
import {
  type CategoryType,
  type MainViewType,
  type Solicitud,
} from "../types";
import { BuffetApprovalModal } from "./BuffetApprovalModal";
import { CategoryTabs } from "./CategoryTabs";
import { ConteoRequestDetails } from "./ConteoRequestDetails";
import { NotificationsCompactTable } from "./NotificationsCompactTable";
import { NotificationsToolbar } from "./NotificationsToolbar";
import { RechazoModal } from "./RechazoModal";
import { SolicitudCard } from "./SolicitudCard";
import { NotificationMatrixView } from "./NotificationMatrixView";

export function NotificationsPage() {
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight");

  // Selectores de Área Operativa y Bodega
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [selectedBodegaId, setSelectedBodegaId] = useState<string>("all");

  // Vista Principal: 'bandeja' | 'historial' | 'configuracion'
  const [mainView, setMainView] = useState<MainViewType>("bandeja");

  // Categoría Operativa activa
  const [activeCategory, setActiveCategory] = useState<CategoryType | "all">(
    "all"
  );

  // Layout de visualización: 'cards' | 'compact'
  const [viewLayout, setViewLayout] = useState<"cards" | "compact">(() => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const saved = window.localStorage.getItem("notifications_view_layout");
        if (saved === "cards" || saved === "compact") return saved;
      }
    } catch {
      // Ignorar fallos de entorno
    }
    return "cards";
  });

  const handleSetViewLayout = useCallback((layout: "cards" | "compact") => {
    setViewLayout(layout);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem("notifications_view_layout", layout);
      }
    } catch {
      // Ignorar
    }
  }, []);

  // Búsqueda persistente
  const [searchTerm, setSearchTerm, clearSearchTerm] = usePersistentSearch(
    "notificaciones",
    ""
  );

  // Paginación
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Modales de Inspección y Rechazo
  const [inspectedBuffetSolicitud, setInspectedBuffetSolicitud] =
    useState<Solicitud | null>(null);
  const [inspectedConteoSolicitud, setInspectedConteoSolicitud] =
    useState<Solicitud | null>(null);
  const [rejectTargetSolicitud, setRejectTargetSolicitud] =
    useState<Solicitud | null>(null);

  // Reiniciar a página 1 ante cambio de filtros o vista
  useEffect(() => {
    setCurrentPage(1);
  }, [mainView, activeCategory, selectedAreaId, selectedBodegaId, searchTerm]);

  // Hook reactivo de solicitudes de aprobación
  const {
    solicitudes,
    total,
    isLoading,
    isError,
    refetch,
    approveRequest,
    rejectRequest,
    isApproving,
    isRejecting,
  } = useApprovals({
    mainView,
    activeCategory,
    selectedAreaId: selectedAreaId === "all" ? undefined : selectedAreaId,
    selectedBodegaId: selectedBodegaId === "all" ? undefined : selectedBodegaId,
    searchTerm,
    page: currentPage,
    pageSize,
  });

  // Hook reactivo ligero de conteo de pendientes
  const { counts, total: totalPending } = usePendingCount({
    areaId: selectedAreaId === "all" ? undefined : selectedAreaId,
  });

  // Autoscroll suave y enfoque cuando existe query param ?highlight=<id>
  useEffect(() => {
    if (highlightId && solicitudes.length > 0) {
      const timer = setTimeout(() => {
        const el =
          document.getElementById(`notif-${highlightId}`) ||
          document.getElementById(`notif-compact-${highlightId}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [highlightId, solicitudes]);

  // Manejo de Aprobación
  const handleApprove = useCallback(
    async (id: string, customDetails?: Record<string, any>) => {
      await approveRequest(id, customDetails);
    },
    [approveRequest]
  );

  // Manejo de Rechazo
  const handleReject = useCallback(
    async (id: string, reason: string) => {
      await rejectRequest(id, reason);
    },
    [rejectRequest]
  );

  // Manejo de Inspección
  const handleInspect = useCallback((solicitud: Solicitud) => {
    if (solicitud.tipo === "consumo_buffet") {
      setInspectedBuffetSolicitud(solicitud);
    } else if (solicitud.tipo === "conteo") {
      setInspectedConteoSolicitud(solicitud);
    } else if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("inspect_approval_request", { detail: solicitud })
      );
    }
  }, []);

  return (
    <div
      data-testid="notifications-page"
      className="container mx-auto px-2 sm:px-4 py-4 sm:py-6 space-y-4 max-w-7xl animate-in fade-in duration-300"
    >
      {/* 1. Cabecera Visual Centrada (SectionHeader #fbbf24) */}
      <SectionHeader
        title="Centro de Notificaciones y Aprobaciones"
        subtitle="Gobernanza operativa, control jerárquico de mermas, conteos y auditorías"
        icon={Bell}
        color="#fbbf24"
        center
      />

      {/* 2. Barra de Herramientas y Filtros Contextuales */}
      <NotificationsToolbar
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        onClearSearch={clearSearchTerm}
        selectedAreaId={selectedAreaId}
        onSelectArea={setSelectedAreaId}
        selectedBodegaId={selectedBodegaId}
        onSelectWarehouse={setSelectedBodegaId}
        viewLayout={viewLayout}
        onViewLayoutChange={handleSetViewLayout}
        mainView={mainView}
        onMainViewChange={setMainView}
        pendingCount={totalPending}
        historyCount={mainView === "historial" ? total : undefined}
      />

      {/* 3. Renderizado Condicional según Vista Principal */}
      {mainView === "configuracion" ? (
        /* Panel de Gobernanza y Configuración de Alertas (Fase 6) */
        <NotificationMatrixView onBack={() => setMainView("bandeja")} />
      ) : (
        /* Bandeja de Entrada o Historial */
        <div className="space-y-4">
          {/* Pestañas Operativas por Categoría */}
          <CategoryTabs
            activeCategory={activeCategory}
            onSelectCategory={setActiveCategory}
            counts={counts}
          />

          {/* Estado de Carga Elegante (Zero Blank Screens) */}
          {isLoading && solicitudes.length === 0 ? (
            <div
              data-testid="notifications-loading"
              className="grid grid-cols-1 md:grid-cols-2 gap-4 py-8"
            >
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-48 rounded-3xl bg-card/40 border border-input/40 animate-pulse p-4 flex flex-col justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-2xl bg-muted/60" />
                    <div className="space-y-1.5 flex-1">
                      <div className="h-4 w-32 bg-muted/60 rounded" />
                      <div className="h-3 w-20 bg-muted/40 rounded" />
                    </div>
                  </div>
                  <div className="h-16 bg-muted/30 rounded-2xl" />
                  <div className="flex justify-end gap-2">
                    <div className="h-8 w-20 bg-muted/40 rounded-xl" />
                    <div className="h-8 w-20 bg-muted/60 rounded-xl" />
                  </div>
                </div>
              ))}
            </div>
          ) : isError && solicitudes.length === 0 ? (
            /* Estado de Error con Resiliencia */
            <div
              data-testid="notifications-error"
              className="p-8 rounded-3xl border border-destructive/20 bg-destructive/5 text-center space-y-3"
            >
              <AlertTriangle className="h-8 w-8 text-destructive mx-auto" />
              <div className="space-y-1">
                <h3 className="font-bold text-foreground">
                  No se pudieron sincronizar las solicitudes
                </h3>
                <p className="text-xs text-muted-foreground">
                  Verifica tu conexión a internet o el estado del servicio central.
                </p>
              </div>
              <button
                type="button"
                onClick={() => refetch()}
                className="px-4 py-2 rounded-xl bg-destructive text-destructive-foreground text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Reintentar
              </button>
            </div>
          ) : solicitudes.length === 0 ? (
            /* Estado Vacío Ilustrado y Contextual */
            <div
              data-testid="notifications-empty-state"
              className="rounded-3xl border border-input/60 bg-card/30 backdrop-blur-sm p-12 text-center space-y-3 shadow-inner"
            >
              <div className="h-14 w-14 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center mx-auto shadow-sm">
                {mainView === "bandeja" ? (
                  <CheckCircle2 className="h-7 w-7 text-emerald-500" />
                ) : (
                  <Inbox className="h-7 w-7 text-amber-500" />
                )}
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-black text-foreground">
                  {mainView === "bandeja"
                    ? "Bandeja al día"
                    : "Historial sin registros"}
                </h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  {mainView === "bandeja"
                    ? activeCategory !== "all"
                      ? `No hay solicitudes pendientes en la categoría ${activeCategory}.`
                      : "Excelente trabajo. Todas las mermas, consumos y auditorías han sido resueltas."
                    : "No hay registros históricos que coincidan con los filtros aplicados."}
                </p>
              </div>
            </div>
          ) : viewLayout === "cards" ? (
            /* Modo 1: Tarjetas Expandidas */
            <div
              data-testid="notifications-cards-grid"
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              {solicitudes.map((solicitud) => (
                <SolicitudCard
                  key={solicitud.id}
                  solicitud={solicitud}
                  isHighlighted={highlightId === solicitud.id}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onInspect={handleInspect}
                  isApproving={isApproving}
                  isRejecting={isRejecting}
                />
              ))}
            </div>
          ) : (
            /* Modo 2: Tabla Compacta de Alta Productividad */
            <NotificationsCompactTable
              solicitudes={solicitudes}
              highlightId={highlightId}
              onApprove={handleApprove}
              onReject={handleReject}
              onInspect={handleInspect}
              onRequestReject={(s) => setRejectTargetSolicitud(s)}
              isApproving={isApproving}
              isRejecting={isRejecting}
            />
          )}

          {/* Paginación */}
          {total > 0 && (
            <TablePagination
              currentPage={currentPage}
              totalItems={total}
              pageSize={pageSize}
              pageSizeOptions={[10, 20, 50]}
              onPageChange={setCurrentPage}
              onPageSizeChange={setPageSize}
              itemLabel="solicitudes"
            />
          )}
        </div>
      )}

      {/* MODAL 1: Auditoría de Buffet Legacy (50/50 y Sobrantes) */}
      <BuffetApprovalModal
        open={!!inspectedBuffetSolicitud}
        solicitudId={inspectedBuffetSolicitud?.id || null}
        solicitud={inspectedBuffetSolicitud}
        onClose={() => setInspectedBuffetSolicitud(null)}
        onResolved={() => {
          setInspectedBuffetSolicitud(null);
          void refetch();
        }}
      />

      {/* MODAL 2: Inspector de Conteo Físico Multidimensional */}
      <ConteoRequestDetails
        open={!!inspectedConteoSolicitud}
        solicitud={inspectedConteoSolicitud}
        onClose={() => setInspectedConteoSolicitud(null)}
        onApprove={handleApprove}
        onReject={handleReject}
        isApproving={isApproving}
        isRejecting={isRejecting}
      />

      {/* MODAL 3: Rechazo Supervisado con Justificación */}
      <RechazoModal
        open={!!rejectTargetSolicitud}
        solicitud={rejectTargetSolicitud}
        onClose={() => setRejectTargetSolicitud(null)}
        onConfirmReject={async (id, reason) => {
          await handleReject(id, reason);
          setRejectTargetSolicitud(null);
        }}
        isRejecting={isRejecting}
      />
    </div>
  );
}

export default NotificationsPage;
