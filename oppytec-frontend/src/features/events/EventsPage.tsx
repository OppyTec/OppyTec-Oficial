// oppytec-frontend/src/features/events/EventsPage.tsx
import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  CalendarDays,
  Plus,
  LayoutGrid,
  Calendar as CalendarIcon,
  Building2,
  FileSpreadsheet,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { cn } from "@/shared/lib";
import { i18next } from "@/shared/i18n";
import { useEvents } from "./hooks/useEvents";
import { useSalones } from "./hooks/useSalones";
import { useEventAlerts } from "./hooks/useEventAlerts";
import type { Evento, EventoListItem } from "./types";
import { EventoCard, type EventoCardItemType } from "./components/EventoCard";
import { EventosCalendar } from "./components/EventosCalendar";
import { EventoDialog } from "./dialogs/EventoDialog";
import { SalonesDialog } from "./dialogs/SalonesDialog";
import { ResumenFaltantesDialog } from "./dialogs/ResumenFaltantesDialog";
import { EventoDetailDialog } from "./dialogs/EventoDetailDialog";
import { formatDateISO } from "./utils/dateUtils";

export function exportEventsToCSV(
  eventos: (Evento | EventoListItem)[],
  tFn?: (key: string, options?: Record<string, unknown>) => string
) {
  const t =
    tFn ??
    ((key: string, options?: Record<string, unknown>) =>
      String(i18next.t(key, { ns: "events", ...options })));

  if (!eventos || eventos.length === 0) {
    toast.error(t("export.no_events_to_export"));
    return;
  }

  const rows = [
    [
      t("export.headers.id"),
      t("export.headers.name"),
      t("export.headers.titular"),
      t("export.headers.date"),
      t("export.headers.start_time"),
      t("export.headers.end_time"),
      t("export.headers.salon"),
      t("export.headers.guests"),
      t("export.headers.status"),
      t("export.headers.items_qty"),
      t("export.headers.recipes_qty"),
      t("export.headers.combos_qty"),
    ],
  ];

  eventos.forEach((ev) => {
    const salonName =
      ("salon" in ev && ev.salon?.nombre) ||
      ev.salon_nombre ||
      ("lugar" in ev ? ev.lugar : null) ||
      "—";

    const comensales =
      ("cantidad_invitados" in ev && ev.cantidad_invitados
        ? ev.cantidad_invitados
        : ev.cantidad_personas) ?? 0;

    const itemsCnt = "items" in ev && ev.items ? ev.items.length : ev.items_count ?? 0;
    const recetasCnt = "recetas" in ev && ev.recetas ? ev.recetas.length : ev.recetas_count ?? 0;
    const combosCnt = "combos" in ev && ev.combos ? ev.combos.length : ev.combos_count ?? 0;

    rows.push([
      ev.id,
      ev.nombre,
      ev.titular || "—",
      ev.fecha,
      ev.hora_inicio || "—",
      ev.hora_fin || "—",
      salonName,
      String(comensales),
      ev.cancelado
        ? t("export.status_labels.cancelled")
        : ev.ejecutado
        ? t("export.status_labels.finished")
        : t("export.status_labels.scheduled"),
      String(itemsCnt),
      String(recetasCnt),
      String(combosCnt),
    ]);
  });

  const csvContent =
    "\uFEFF" + rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute(
    "download",
    `${t("export.filename_prefix")}_${formatDateISO(new Date())}.csv`
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  toast.success(t("export.export_success"));
}

export function EventsPage() {
  const { t } = useTranslation("events");
  const {
    events,
    counts,
    activeTab,
    setActiveTab,
    executeEvent,
    cancelEvent,
    reactivateEvent,
    deleteEvent,
    isExecuting,
    isLoading,
  } = useEvents();

  const { salones } = useSalones();
  const {
    hasShortages,
    totalFaltantes,
    items: faltantes,
    criticalAlertsCount,
    warningAlertsCount,
    hasCriticalAlerts,
    hasWarningAlerts,
  } = useEventAlerts();

  // Estados locales de interfaz
  const [viewMode, setViewMode] = useState<"grid" | "calendar">("grid");
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");

  // Modales operativos
  const [isEventoDialogOpen, setIsEventoDialogOpen] = useState(false);
  const [editingEvento, setEditingEvento] = useState<Evento | null>(null);
  const [initialDate, setInitialDate] = useState<string | null>(null);

  const [isSalonesDialogOpen, setIsSalonesDialogOpen] = useState(false);
  const [isFaltantesDialogOpen, setIsFaltantesDialogOpen] = useState(false);
  const [detailEvento, setDetailEvento] = useState<Evento | null>(null);

  // Filtrado reactivo por área operativa
  const filteredEventos = useMemo(() => {
    if (!selectedAreaId || selectedAreaId === "all") return events;

    const areaNum = Number(selectedAreaId);
    if (isNaN(areaNum)) return events;

    // Filtra eventos cuyo salón contenga el área o sin asignación estricta
    return events.filter((ev: EventoListItem) => {
      if (!ev.salon_id) return true;
      const salon = salones.find((s) => s.id === ev.salon_id);
      if (!salon) return true;
      return salon.areas_operativas_ids?.includes(areaNum);
    });
  }, [events, selectedAreaId, salones]);

  // Eventos particionados por pestaña
  const proximosEventos = useMemo(
    () => filteredEventos.filter((e: EventoListItem) => !e.cancelado && !e.ejecutado),
    [filteredEventos]
  );
  const finalizadosEventos = useMemo(
    () => filteredEventos.filter((e: EventoListItem) => e.ejecutado && !e.cancelado),
    [filteredEventos]
  );
  const canceladosEventos = useMemo(
    () => filteredEventos.filter((e: EventoListItem) => e.cancelado),
    [filteredEventos]
  );

  const currentTabEvents =
    activeTab === "proximos"
      ? proximosEventos
      : activeTab === "historial"
      ? finalizadosEventos
      : canceladosEventos;

  // Handlers para acciones
  const handleOpenNew = (dateStr?: string) => {
    setEditingEvento(null);
    setInitialDate(dateStr || formatDateISO(new Date()));
    setIsEventoDialogOpen(true);
  };

  const handleEdit = (ev: EventoCardItemType) => {
    setEditingEvento(ev as Evento);
    setIsEventoDialogOpen(true);
  };

  const handleExecute = async (ev: EventoCardItemType) => {
    if (window.confirm(t("card.confirm_execute", { name: ev.nombre }))) {
      await executeEvent(ev.id);
    }
  };

  const handleCancel = async (ev: EventoCardItemType) => {
    if (window.confirm(t("card.confirm_cancel", { name: ev.nombre }))) {
      await cancelEvent({ id: ev.id, motivo: t("card.cancel_reason_default") });
    }
  };

  const handleReactivate = async (ev: EventoCardItemType) => {
    await reactivateEvent(ev.id);
  };

  const handleDelete = async (ev: EventoCardItemType) => {
    if (window.confirm(t("card.confirm_delete", { name: ev.nombre }))) {
      await deleteEvent(ev.id);
    }
  };

  const handleExport = () => {
    exportEventsToCSV(filteredEventos, (k, opts) => t(k, opts));
  };

  return (
    <div
      data-testid="events-page-root"
      className="container mx-auto max-w-7xl px-4 py-6 md:px-6 md:py-8 space-y-6"
    >
      {/* 4.1 Cabecera Institucional Estandarizada */}
      <SectionHeader
        title={t("header.title")}
        subtitle={t("header.subtitle")}
        icon={CalendarDays}
        color="#ec4899"
        center={true}
      />

      {/* Banner de alerta de stock faltante y crítico (FASE 7) */}
      {(hasShortages || hasCriticalAlerts || hasWarningAlerts) && (
        <div
          data-testid="event-shortages-banner"
          data-severity={hasCriticalAlerts ? "CRITICAL" : "WARNING"}
          className={cn(
            "flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 p-4 shadow-sm transition-all",
            hasCriticalAlerts
              ? "border-rose-500/40 bg-rose-500/10 text-rose-800 dark:text-rose-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300"
          )}
        >
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                hasCriticalAlerts
                  ? "bg-rose-500/20 text-rose-600 animate-pulse"
                  : "bg-amber-500/20 text-amber-600"
              )}
            >
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                {hasCriticalAlerts ? (
                  <span className="rounded-md bg-rose-600 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-white">
                    {t("alerts_banner.badge_critical")}
                  </span>
                ) : (
                  warningAlertsCount > 0 && (
                    <span className="rounded-md bg-amber-600 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-white">
                      {t("alerts_banner.badge_warning")}
                    </span>
                  )
                )}
                <h4 className="text-sm font-bold">
                  {t("alerts_banner.title_prefix")} (
                  {hasCriticalAlerts
                    ? (criticalAlertsCount === 1
                        ? t("alerts_banner.critical_summary_single", { shortagesCount: totalFaltantes })
                        : t("alerts_banner.critical_summary", {
                            criticalCount: criticalAlertsCount,
                            shortagesCount: totalFaltantes,
                          }))
                    : t("alerts_banner.warning_summary", { shortagesCount: totalFaltantes })}
                  )
                </h4>
              </div>
              <p
                className={cn(
                  "text-xs mt-0.5",
                  hasCriticalAlerts
                    ? "text-rose-700 dark:text-rose-400"
                    : "text-amber-700 dark:text-amber-400"
                )}
              >
                {hasCriticalAlerts
                  ? `${t("alerts_banner.desc_critical")}${
                      warningAlertsCount > 0
                        ? t("alerts_banner.desc_critical_suffix", { count: warningAlertsCount })
                        : ""
                    }`
                  : t("alerts_banner.desc_warning")}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="btn-ver-resumen-faltantes"
            onClick={() => setIsFaltantesDialogOpen(true)}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold text-white shadow-sm active:scale-95 transition-all cursor-pointer",
              hasCriticalAlerts
                ? "bg-rose-600 hover:bg-rose-700"
                : "bg-amber-600 hover:bg-amber-700"
            )}
          >
            <span>{t("alerts_banner.btn_view_shortages")}</span>
          </button>
        </div>
      )}

      {/* 4.1 Toolbar Unificado */}
      <div
        data-testid="events-toolbar"
        className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-3 shadow-xs"
      >
        {/* Selector de Áreas Operativas */}
        <div className="flex items-center gap-2">
          <AreaSelector
            selectedAreaId={selectedAreaId}
            onSelectArea={(areaId) => setSelectedAreaId(areaId)}
          />
        </div>

        {/* Acciones principales del Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Botón Salones */}
          <button
            type="button"
            data-testid="btn-abrir-salones"
            onClick={() => setIsSalonesDialogOpen(true)}
            title={t("toolbar.salones_tooltip")}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-3.5 py-2 text-xs font-bold text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
          >
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <span>{t("toolbar.salones")}</span>
          </button>

          {/* Botón Exportar Minuta */}
          <button
            type="button"
            data-testid="btn-exportar-eventos"
            onClick={handleExport}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-3.5 py-2 text-xs font-bold text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
          >
            <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
            <span>{t("toolbar.exportar")}</span>
          </button>

          {/* Toggle de Vistas: Grilla vs Calendario */}
          <div className="flex items-center rounded-xl bg-secondary/80 p-1 border border-border/50">
            <button
              type="button"
              data-testid="btn-view-grid"
              title={t("toolbar.view_grid")}
              onClick={() => setViewMode("grid")}
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-lg transition-all cursor-pointer",
                viewMode === "grid"
                  ? "bg-card text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              type="button"
              data-testid="btn-view-calendar"
              title={t("toolbar.view_calendar")}
              onClick={() => setViewMode("calendar")}
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-lg transition-all cursor-pointer",
                viewMode === "calendar"
                  ? "bg-card text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <CalendarIcon className="h-4 w-4 text-[#ec4899]" />
            </button>
          </div>

          {/* Botón Primario: Nuevo Evento (#ec4899) */}
          <button
            type="button"
            data-testid="btn-nuevo-evento"
            onClick={() => handleOpenNew()}
            className="inline-flex items-center gap-2 rounded-xl bg-[#ec4899] px-4 py-2 text-xs font-bold text-white shadow-md hover:bg-[#db2777] active:scale-95 transition-all cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            <span>{t("toolbar.nuevo_evento")}</span>
          </button>
        </div>
      </div>

      {/* 4.2 Pestañas de Estado con Contadores Reactivos */}
      <div
        data-testid="events-tabs"
        className="flex items-center gap-2 border-b border-border/60 pb-2 text-xs font-bold"
      >
        <button
          type="button"
          data-testid="tab-proximos"
          onClick={() => setActiveTab("proximos")}
          className={cn(
            "flex items-center gap-2 rounded-xl px-4 py-2 transition-all cursor-pointer",
            activeTab === "proximos"
              ? "bg-[#ec4899]/10 text-[#ec4899] border border-[#ec4899]/30 shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          )}
        >
          <span>{t("tabs.proximos")}</span>
          <span
            data-testid="badge-count-proximos"
            className="rounded-full bg-[#ec4899] px-2 py-0.5 text-[10px] text-white"
          >
            {counts.proximos}
          </span>
        </button>

        <button
          type="button"
          data-testid="tab-historial"
          onClick={() => setActiveTab("historial")}
          className={cn(
            "flex items-center gap-2 rounded-xl px-4 py-2 transition-all cursor-pointer",
            activeTab === "historial"
              ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          )}
        >
          <span>{t("tabs.historial")}</span>
          <span
            data-testid="badge-count-historial"
            className="rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] text-white"
          >
            {counts.historial}
          </span>
        </button>

        <button
          type="button"
          data-testid="tab-cancelados"
          onClick={() => setActiveTab("cancelados")}
          className={cn(
            "flex items-center gap-2 rounded-xl px-4 py-2 transition-all cursor-pointer",
            activeTab === "cancelados"
              ? "bg-rose-500/10 text-rose-600 border border-rose-500/30 shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          )}
        >
          <span>{t("tabs.cancelados")}</span>
          <span
            data-testid="badge-count-cancelados"
            className="rounded-full bg-rose-600 px-2 py-0.5 text-[10px] text-white"
          >
            {counts.cancelados}
          </span>
        </button>
      </div>

      {/* Renderizado Condicional: Grilla de Tarjetas vs Calendario */}
      {viewMode === "grid" ? (
        <div data-testid="events-grid-view" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {currentTabEvents.map((ev: EventoListItem) => (
              <EventoCard
                key={ev.id}
                evento={ev}
                isExecuting={isExecuting}
                onExecute={handleExecute}
                onCancel={handleCancel}
                onReactivate={handleReactivate}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onDetail={(target) => setDetailEvento(target as Evento)}
              />
            ))}
          </div>

          {currentTabEvents.length === 0 && !isLoading && (
            <div
              data-testid="events-empty-state"
              className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 py-16 text-center space-y-3"
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#ec4899]/10 text-[#ec4899]">
                <CalendarDays className="h-7 w-7" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-foreground">
                  {t("empty_state.title")}
                </h3>
                <p className="text-xs text-muted-foreground max-w-sm">
                  {activeTab === "proximos"
                    ? t("empty_state.desc_proximos")
                    : activeTab === "historial"
                    ? t("empty_state.desc_historial")
                    : t("empty_state.desc_cancelados")}
                </p>
              </div>
              {activeTab === "proximos" && (
                <button
                  type="button"
                  data-testid="btn-empty-crear-evento"
                  onClick={() => handleOpenNew()}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-[#ec4899] px-4 py-2 text-xs font-bold text-white shadow hover:bg-[#db2777] active:scale-95 transition-all cursor-pointer"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>{t("empty_state.btn_create_first")}</span>
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div data-testid="events-calendar-view">
          <EventosCalendar
            eventos={filteredEventos}
            salones={salones}
            onSelectDate={(dateStr) => handleOpenNew(dateStr)}
            onNewEvento={(dateStr) => handleOpenNew(dateStr)}
            onSelectEvento={(ev) => setDetailEvento(ev as Evento)}
          />
        </div>
      )}

      {/* Diálogos Operativos */}
      <EventoDialog
        open={isEventoDialogOpen}
        onClose={() => setIsEventoDialogOpen(false)}
        editingEvento={editingEvento}
        initialDate={initialDate}
      />

      <SalonesDialog
        open={isSalonesDialogOpen}
        onClose={() => setIsSalonesDialogOpen(false)}
      />

      <ResumenFaltantesDialog
        open={isFaltantesDialogOpen}
        onClose={() => setIsFaltantesDialogOpen(false)}
        faltantesOverride={faltantes}
      />

      <EventoDetailDialog
        open={Boolean(detailEvento)}
        onClose={() => setDetailEvento(null)}
        evento={detailEvento}
        onEdit={(ev) => handleEdit(ev)}
        onExecute={(ev) => handleExecute(ev)}
        onCancel={(ev) => handleCancel(ev)}
      />
    </div>
  );
}

export default EventsPage;
