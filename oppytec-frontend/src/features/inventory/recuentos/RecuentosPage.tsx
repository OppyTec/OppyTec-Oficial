// oppytec-frontend/src/features/inventory/recuentos/RecuentosPage.tsx
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ClipboardCheck,
  Plus,
  Warehouse,
  Filter,
  Search,
  RefreshCw,
  Inbox,
  AlertCircle,
  BarChart3,
  CheckCircle,
} from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { useAuth } from "@/shared/auth/usePermissions";
import { useCurrencyFormatter } from "@/shared/currency";
import { useRecuentos } from "../hooks/useRecuentos";
import { MOCK_BODEGAS } from "../mockData";
import { RecuentoCard } from "./RecuentoCard";
import { RecuentoDetalleModal } from "./RecuentoDetalleModal";
import type { PhysicalCountSession, PhysicalCountState } from "../types";

const ESTADOS_FILTRO: Array<{ key: string; defaultLabel: string; value: PhysicalCountState | "ALL" }> = [
  { key: "all", defaultLabel: "Todos los Estados", value: "ALL" },
  { key: "in_progress", defaultLabel: "En Progreso", value: "EN_PROGRESO" },
  { key: "pending_approval", defaultLabel: "Pendientes de Aprobación", value: "PENDIENTE_APROBACION" },
  { key: "approved", defaultLabel: "Aprobados y Conciliados", value: "APROBADO" },
  { key: "rejected", defaultLabel: "Rechazados", value: "RECHAZADO" },
];

export function RecuentosPage() {
  const { t } = useTranslation("inventory");
  const navigate = useNavigate();
  const { user } = useAuth();
  const { convertAndFormat } = useCurrencyFormatter();
  const isPropietario =
    user?.role?.toLowerCase() === "propietario" ||
    user?.role?.toLowerCase() === "admin" ||
    user?.isSuperuser === true ||
    user?.isGlobalAdmin === true;

  const {
    sessions,
    isLoading,
    isError,
    refetch,
    bodegaFilter,
    setBodegaFilter,
    statusFilter,
    setStatusFilter,
    search,
    setSearch,
    approveSession,
    rejectSession,
    deleteSession,
  } = useRecuentos();

  const [expandedSessionId, setExpandedSessionId] = useState<number | null>(null);
  const [modalSession, setModalSession] = useState<PhysicalCountSession | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | "delete" | null>(null);

  const handleToggleExpand = (id: number) => {
    setExpandedSessionId((prev) => (prev === id ? null : id));
  };

  const handleOpenDetailModal = (session: PhysicalCountSession) => {
    setModalSession(session);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setModalSession(null);
  };

  const handleApprove = async (sessionId: number) => {
    setActionLoadingId(sessionId);
    setActionType("approve");
    try {
      await approveSession(sessionId);
      if (modalSession?.id === sessionId) {
        setIsModalOpen(false);
        setModalSession(null);
      }
    } finally {
      setActionLoadingId(null);
      setActionType(null);
    }
  };

  const handleReject = async (sessionId: number) => {
    setActionLoadingId(sessionId);
    setActionType("reject");
    try {
      await rejectSession(sessionId);
    } finally {
      setActionLoadingId(null);
      setActionType(null);
    }
  };

  const handleDelete = async (sessionId: number) => {
    setActionLoadingId(sessionId);
    setActionType("delete");
    try {
      await deleteSession(sessionId);
      if (expandedSessionId === sessionId) {
        setExpandedSessionId(null);
      }
    } finally {
      setActionLoadingId(null);
      setActionType(null);
    }
  };

  // KPIs de la vista
  const metrics = useMemo(() => {
    const total = sessions.length;
    const pendientes = sessions.filter((s) => s.estado === "PENDIENTE_APROBACION").length;
    const aprobados = sessions.filter((s) => s.estado === "APROBADO").length;
    const impactoNeto = sessions.reduce(
      (acc, s) => acc + (s.total_valorizacion_discrepancia || 0),
      0
    );

    return { total, pendientes, aprobados, impactoNeto };
  }, [sessions]);

  return (
    <div
      data-testid="recuentos-page"
      className="container mx-auto px-2 sm:px-4 py-4 md:py-6 max-w-7xl space-y-6 animate-fade-in pb-16"
    >
      {/* 1. Header Centrado con ADN OppyTec */}
      <SectionHeader
        title={t("recuentos.title", "Historial de Recuentos")}
        subtitle={t("recuentos.subtitle", "Consulta y gestiona las sesiones de conteo físico y auditoría de inventario")}
        icon={ClipboardCheck}
        color="#8b5cf6"
        center={true}
      />

      {/* 2. Métricas y KPIs de Auditoría */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-card p-3 sm:p-4 rounded-2xl border border-border flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400 shrink-0">
            <ClipboardCheck className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              {t("recuentos.kpi_total_records", "Total Actas")}
            </span>
            <span className="text-lg font-black text-foreground">{metrics.total}</span>
          </div>
        </div>

        <div className="glass-card p-3 sm:p-4 rounded-2xl border border-border flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 shrink-0">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              {t("recuentos.kpi_to_approve", "Por Aprobar")}
            </span>
            <span className="text-lg font-black text-amber-400">{metrics.pendientes}</span>
          </div>
        </div>

        <div className="glass-card p-3 sm:p-4 rounded-2xl border border-border flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 shrink-0">
            <CheckCircle className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              {t("recuentos.kpi_reconciled", "Conciliados")}
            </span>
            <span className="text-lg font-black text-emerald-400">{metrics.aprobados}</span>
          </div>
        </div>

        <div className="glass-card p-3 sm:p-4 rounded-2xl border border-border flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 shrink-0">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              {t("recuentos.kpi_total_impact", "Impacto Total PPP")}
            </span>
            <span
              className={`text-base font-black truncate block ${
                metrics.impactoNeto >= 0 ? "text-emerald-500" : "text-rose-500"
              }`}
            >
              {metrics.impactoNeto >= 0 ? "+" : ""}
              {convertAndFormat(metrics.impactoNeto, "CLP")}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Toolbar de Control y Filtros */}
      <div className="glass-card p-3 sm:p-4 rounded-2xl border border-border/80 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Controles de Búsqueda y Filtros */}
        <div className="flex flex-1 flex-wrap items-center gap-2.5">
          {/* Buscador */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              aria-label={t("recuentos.search_aria", "Buscar sesiones o insumos")}
              placeholder={t("recuentos.search_placeholder", "Buscar por bodega, responsable, insumo o notas...")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="touch-target h-10 w-full rounded-xl border border-input bg-card pl-9 pr-3 text-xs font-medium text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
          </div>

          {/* Selector de Bodega */}
          <div className="inline-flex items-center gap-1.5 rounded-xl border border-input bg-card px-3 py-1">
            <Warehouse className="h-4 w-4 text-purple-400 shrink-0" />
            <select
              aria-label={t("recuentos.filter_warehouse_aria", "Filtrar por bodega")}
              value={bodegaFilter}
              onChange={(e) =>
                setBodegaFilter(e.target.value === "all" ? "all" : Number(e.target.value))
              }
              className="touch-target min-h-[38px] bg-transparent text-xs font-semibold text-foreground focus:outline-none"
            >
              <option value="all">{t("recuentos.all_warehouses", "Todas las Bodegas")}</option>
              {MOCK_BODEGAS.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Estado */}
          <div className="inline-flex items-center gap-1.5 rounded-xl border border-input bg-card px-3 py-1">
            <Filter className="h-4 w-4 text-purple-400 shrink-0" />
            <select
              aria-label={t("recuentos.filter_status_aria", "Filtrar por estado")}
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as PhysicalCountState | "ALL")
              }
              className="touch-target min-h-[38px] bg-transparent text-xs font-semibold text-foreground focus:outline-none"
            >
              {ESTADOS_FILTRO.map((est) => (
                <option key={est.value} value={est.value}>
                  {t(`recuentos.filter_states.${est.key}`, est.defaultLabel)}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="touch-target inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground hover:text-foreground transition-colors"
            title={t("recuentos.refresh_title", "Recargar sesiones")}
            aria-label={t("recuentos.refresh_aria", "Recargar recuentos")}
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>

        {/* Botón Primario + Nuevo Recuento */}
        <div className="flex items-center justify-end">
          <button
            type="button"
            data-testid="btn-nuevo-recuento"
            onClick={() => navigate("/contar-inventario")}
            className="touch-target inline-flex min-h-[44px] w-full md:w-auto items-center justify-center gap-2 rounded-xl bg-purple-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-purple-600/25 hover:bg-purple-700 transition-all active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            {t("recuentos.new_count", "+ Nuevo Recuento")}
          </button>
        </div>
      </div>

      {/* 4. Lista de Actas / Tarjetas Expandibles */}
      {isLoading ? (
        <div className="text-center py-20 text-muted-foreground font-semibold">
          <div className="h-10 w-10 animate-spin rounded-2xl border-4 border-purple-500 border-t-transparent mx-auto mb-4" />
          {t("recuentos.loading", "Cargando historial de recuentos...")}
        </div>
      ) : isError ? (
        <div className="p-8 text-center rounded-2xl border border-destructive/20 bg-destructive/5 text-destructive">
          <AlertCircle className="h-10 w-10 mx-auto mb-2 opacity-80" />
          <h4 className="font-bold text-sm">{t("recuentos.error_title", "Error al cargar recuentos")}</h4>
          <p className="text-xs text-muted-foreground mt-1">
            {t("recuentos.error_desc", "No se pudo sincronizar la lista de actas con el servidor.")}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-destructive px-4 py-2 text-xs font-bold text-white"
          >
            {t("recuentos.retry", "Reintentar")}
          </button>
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-16 border border-dashed rounded-[2rem] border-border bg-card/20 backdrop-blur-sm">
          <Inbox className="h-12 w-12 mx-auto text-muted-foreground opacity-30 mb-3" />
          <p className="text-sm text-muted-foreground font-bold uppercase tracking-wider">
            {t("recuentos.empty_title", "Historial de recuentos vacío")}
          </p>
          <p className="text-xs text-muted-foreground/70 mt-1 max-w-sm mx-auto">
            {t("recuentos.empty_desc", "No se encontraron sesiones de conteo para los filtros seleccionados.")}
          </p>
          <button
            type="button"
            onClick={() => navigate("/contar-inventario")}
            className="mt-4 touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t("recuentos.start_new_count", "Comenzar Nuevo Conteo")}
          </button>
        </div>
      ) : (
        <div className="space-y-4" data-testid="recuentos-list">
          {sessions.map((session) => (
            <RecuentoCard
              key={session.id}
              session={session}
              isExpanded={expandedSessionId === session.id}
              onToggleExpand={() => handleToggleExpand(session.id)}
              onOpenDetailModal={() => handleOpenDetailModal(session)}
              onApprove={handleApprove}
              onReject={handleReject}
              onDelete={handleDelete}
              isApproving={actionLoadingId === session.id && actionType === "approve"}
              isRejecting={actionLoadingId === session.id && actionType === "reject"}
              isDeleting={actionLoadingId === session.id && actionType === "delete"}
              isPropietario={isPropietario}
            />
          ))}
        </div>
      )}

      {/* 5. Modal de Detalle y Edición Rápida */}
      <RecuentoDetalleModal
        open={isModalOpen}
        onClose={handleCloseModal}
        session={modalSession}
        isPropietario={isPropietario}
        onSaveSessionItems={async () => {}}
        onApprove={handleApprove}
        isApproving={actionLoadingId === modalSession?.id && actionType === "approve"}
      />
    </div>
  );
}

export default RecuentosPage;
