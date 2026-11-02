// oppytec-frontend/src/features/events/components/EventoCard.tsx
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Play,
  Pencil,
  Ban,
  Trash2,
  RotateCcw,
  Eye,
  Calendar,
  Clock,
  Users,
  Building2,
  Package,
  ChefHat,
  Layers,
  AlertTriangle,
} from "lucide-react";
import { cn, formatMoney } from "@/shared/lib";
import type { Evento, EventoListItem } from "../types";
import { formatDateES, formatTimeShort } from "../utils/dateUtils";
import { getEventEstimatedCost } from "../hooks/useEvents";
import { useEventAlerts } from "../hooks/useEventAlerts";

export type EventoCardItemType = Evento | EventoListItem;

export interface EventoCardProps {
  readonly evento: EventoCardItemType;
  readonly isAdmin?: boolean;
  readonly isExecuting?: boolean;
  readonly onExecute?: (evento: EventoCardItemType) => void;
  readonly onCancel?: (evento: EventoCardItemType) => void;
  readonly onReactivate?: (evento: EventoCardItemType) => void;
  readonly onEdit?: (evento: EventoCardItemType) => void;
  readonly onDelete?: (evento: EventoCardItemType) => void;
  readonly onDetail?: (evento: EventoCardItemType) => void;
}

export function EventoCard({
  evento,
  isAdmin = true,
  isExecuting = false,
  onExecute,
  onCancel,
  onReactivate,
  onEdit,
  onDelete,
  onDetail,
}: EventoCardProps) {
  const { t } = useTranslation("events");
  const isAgendado = !evento.cancelado && !evento.ejecutado;
  const isFinalizado = evento.ejecutado && !evento.cancelado;
  const isCancelado = evento.cancelado;

  const { eventAlerts } = useEventAlerts();
  const eventAlert = useMemo(
    () => (isAgendado ? eventAlerts.find((a) => a.evento_id === evento.id) : undefined),
    [isAgendado, eventAlerts, evento.id]
  );

  const estimatedCost = useMemo(() => getEventEstimatedCost(evento), [evento]);

  const itemsCount = "items" in evento && evento.items ? evento.items.length : evento.items_count ?? 0;
  const recetasCount = "recetas" in evento && evento.recetas ? evento.recetas.length : evento.recetas_count ?? 0;
  const combosCount = "combos" in evento && evento.combos ? evento.combos.length : evento.combos_count ?? 0;
  const invitadosCount = "cantidad_invitados" in evento && evento.cantidad_invitados
    ? evento.cantidad_invitados
    : evento.cantidad_personas ?? 0;

  const cardColor = evento.color || "#ec4899";
  const salonColor = ("salon" in evento && evento.salon?.color) || cardColor;
  const salonNombre = ("salon" in evento && evento.salon?.nombre) || evento.salon_nombre || ("lugar" in evento ? evento.lugar : null);

  return (
    <div
      role="article"
      data-testid={`evento-card-${evento.id}`}
      tabIndex={0}
      onClick={() => onDetail?.(evento)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onDetail?.(evento);
        }
      }}
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-2xl border bg-card p-5 text-card-foreground shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-pointer",
        "border-border/70 hover:border-border"
      )}
      style={{
        borderLeftWidth: "6px",
        borderLeftColor: cardColor,
      }}
    >
      {/* Cabecera superior con título y badges */}
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3
              title={evento.nombre}
              className="text-base font-bold tracking-tight text-foreground truncate group-hover:text-primary transition-colors"
            >
              {evento.nombre}
            </h3>
            {evento.titular && (
              <p className="text-xs text-muted-foreground truncate">
                {t("card.titular")}: <span className="font-medium text-foreground">{evento.titular}</span>
              </p>
            )}
          </div>

          {/* Badge de Estado reactivo */}
          <div className="shrink-0 flex items-center gap-1.5">
            {eventAlert && (
              eventAlert.severidad === "CRITICAL" ? (
                <span
                  data-testid={`alert-critical-${evento.id}`}
                  title={eventAlert.mensaje}
                  className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold text-rose-600 dark:text-rose-400 animate-pulse"
                >
                  <AlertTriangle className="h-3 w-3 shrink-0" />
                  <span>{t("card.badge_critical")}</span>
                </span>
              ) : (
                <span
                  data-testid={`alert-warning-${evento.id}`}
                  title={eventAlert.mensaje}
                  className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-600 dark:text-amber-400"
                >
                  <AlertTriangle className="h-3 w-3 shrink-0" />
                  <span>{t("card.badge_warning")}</span>
                </span>
              )
            )}

            {isAgendado && (
              <span
                data-testid="badge-estado-agendado"
                className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2.5 py-0.5 text-xs font-semibold text-sky-600 dark:text-sky-400 border border-sky-500/20"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-sky-500 animate-pulse" />
                {t("card.badge_agendado")}
              </span>
            )}
            {isFinalizado && (
              <span
                data-testid="badge-estado-finalizado"
                className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {t("card.badge_finalizado")}
              </span>
            )}
            {isCancelado && (
              <span
                data-testid="badge-estado-cancelado"
                className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-600 dark:text-rose-400 border border-rose-500/20"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                {t("card.badge_cancelado")}
              </span>
            )}
          </div>
        </div>

        {/* Metadatos: Fecha y Rango Horario */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5 font-medium">
            <Calendar className="h-3.5 w-3.5 text-primary/70 shrink-0" />
            <span>{formatDateES(evento.fecha)}</span>
          </div>

          {(evento.hora_inicio || evento.hora_fin) && (
            <div className="flex items-center gap-1.5 font-medium">
              <Clock className="h-3.5 w-3.5 text-muted-foreground/80 shrink-0" />
              <span>
                {formatTimeShort(evento.hora_inicio) || t("card.sin_hora")}
                {evento.hora_fin ? ` - ${formatTimeShort(evento.hora_fin)}` : ""}
              </span>
            </div>
          )}
        </div>

        {/* Salón asignado y comensales */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          {salonNombre && (
            <span
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 font-medium border"
              style={{
                backgroundColor: `${salonColor}12`,
                borderColor: `${salonColor}35`,
                color: salonColor,
              }}
            >
              <Building2 className="h-3 w-3 shrink-0" />
              <span className="truncate max-w-[150px]">{salonNombre}</span>
            </span>
          )}

          {invitadosCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-lg bg-secondary/70 px-2 py-1 text-secondary-foreground font-medium border border-border/50">
              <Users className="h-3 w-3 shrink-0 text-muted-foreground" />
              <span>{t("card.comensales", { count: invitadosCount })}</span>
            </span>
          )}
        </div>

        {/* Desglose de Insumos, Recetas y Combos */}
        <div className="rounded-xl bg-secondary/30 p-2.5 border border-border/50 space-y-1.5 text-xs">
          <div className="flex items-center justify-between font-semibold text-muted-foreground">
            <span>{t("card.supplies_scheduled")}</span>
            {estimatedCost > 0 && (
              <span className="font-bold text-foreground font-mono">
                {formatMoney(estimatedCost)}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              title="Insumos directos de inventario"
              className="inline-flex items-center gap-1 rounded-md bg-background px-2 py-0.5 text-[11px] font-medium border border-border/60 text-muted-foreground"
            >
              <Package className="h-3 w-3 text-sky-500" />
              <span>{t("card.items_count", { count: itemsCount })}</span>
            </span>
            <span
              title="Recetas y preparaciones"
              className="inline-flex items-center gap-1 rounded-md bg-background px-2 py-0.5 text-[11px] font-medium border border-border/60 text-muted-foreground"
            >
              <ChefHat className="h-3 w-3 text-amber-500" />
              <span>{t("card.recetas_count", { count: recetasCount })}</span>
            </span>
            <span
              title="Combos gastronómicos"
              className="inline-flex items-center gap-1 rounded-md bg-background px-2 py-0.5 text-[11px] font-medium border border-border/60 text-muted-foreground"
            >
              <Layers className="h-3 w-3 text-purple-500" />
              <span>{t("card.combos_count", { count: combosCount })}</span>
            </span>
            {eventAlert && (
              <span
                data-testid={`stock-comprometido-indicator-${evento.id}`}
                title={t("card.committed_stock_tooltip", { count: eventAlert.total_insumos_deficit })}
                className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold border border-amber-500/30 text-amber-600 dark:text-amber-400"
              >
                <AlertTriangle className="h-3 w-3" />
                <span>{t("card.committed_stock_indicator")}</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Botones de acción según estado */}
      <div
        className="mt-4 flex flex-wrap items-center gap-2 border-t border-border/50 pt-3"
        onClick={(e) => e.stopPropagation()}
      >
        {isAgendado && (
          <>
            <button
              type="button"
              data-testid="btn-ejecutar-kardex"
              disabled={isExecuting}
              onClick={() => onExecute?.(evento)}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white shadow hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-50 cursor-pointer"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>{isExecuting ? t("card.btn_executing") : t("card.btn_execute")}</span>
            </button>

            <button
              type="button"
              data-testid="btn-editar-evento"
              title={t("card.btn_edit")}
              onClick={() => onEdit?.(evento)}
              className="inline-flex items-center justify-center rounded-xl border border-border bg-card px-2.5 py-2 text-xs font-semibold text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>

            <button
              type="button"
              data-testid="btn-cancelar-evento"
              title={t("card.btn_cancel")}
              onClick={() => onCancel?.(evento)}
              className="inline-flex items-center justify-center rounded-xl border border-rose-500/20 bg-rose-500/5 px-2.5 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-500/15 active:scale-95 transition-all cursor-pointer"
            >
              <Ban className="h-3.5 w-3.5" />
            </button>

            {isAdmin && (
              <button
                type="button"
                data-testid="btn-eliminar-evento"
                title={t("card.btn_delete")}
                onClick={() => onDelete?.(evento)}
                className="inline-flex items-center justify-center rounded-xl border border-border/50 bg-card px-2.5 py-2 text-xs font-semibold text-destructive hover:bg-destructive/10 active:scale-95 transition-all cursor-pointer"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </>
        )}

        {isCancelado && (
          <>
            <button
              type="button"
              data-testid="btn-reactivar-evento"
              onClick={() => onReactivate?.(evento)}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-xs font-bold text-sky-600 hover:bg-sky-500/20 active:scale-95 transition-all cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>{t("card.btn_reactivate")}</span>
            </button>

            {isAdmin && (
              <button
                type="button"
                data-testid="btn-eliminar-evento"
                title={t("card.btn_delete")}
                onClick={() => onDelete?.(evento)}
                className="inline-flex items-center justify-center rounded-xl border border-destructive/20 bg-destructive/10 px-2.5 py-2 text-xs font-semibold text-destructive hover:bg-destructive/20 active:scale-95 transition-all cursor-pointer"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </>
        )}

        {isFinalizado && (
          <button
            type="button"
            data-testid="btn-ver-detalle-finalizado"
            onClick={() => onDetail?.(evento)}
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-secondary/80 px-3 py-2 text-xs font-bold text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
          >
            <Eye className="h-3.5 w-3.5" />
            <span>{t("card.btn_view_detail")}</span>
          </button>
        )}
      </div>
    </div>
  );
}
