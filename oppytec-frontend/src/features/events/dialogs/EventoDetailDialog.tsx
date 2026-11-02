// oppytec-frontend/src/features/events/dialogs/EventoDetailDialog.tsx
import { useTranslation } from "react-i18next";
import {
  Calendar,
  Clock,
  Package,
  ChefHat,
  Layers,
  Play,
  Pencil,
  Ban,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { formatMoney } from "@/shared/lib";
import type { Evento } from "../types";
import { formatDateES, formatTimeShort } from "../utils/dateUtils";
import { getEventEstimatedCost } from "../hooks/useEvents";

export interface EventoDetailDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly evento?: Evento | null;
  readonly onEdit?: (evento: Evento) => void;
  readonly onExecute?: (evento: Evento) => void;
  readonly onCancel?: (evento: Evento) => void;
}

export function EventoDetailDialog({
  open,
  onClose,
  evento,
  onEdit,
  onExecute,
  onCancel,
}: EventoDetailDialogProps) {
  const { t } = useTranslation("events");
  if (!evento) return null;

  const isAgendado = !evento.cancelado && !evento.ejecutado;
  const isFinalizado = evento.ejecutado && !evento.cancelado;
  const isCancelado = evento.cancelado;

  const estimatedCost = getEventEstimatedCost(evento);
  const cardColor = evento.color || "#ec4899";

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={evento.nombre}
      description={
        evento.titular
          ? t("detail_dialog.description_titular", { titular: evento.titular })
          : t("detail_dialog.description_default")
      }
      maxWidth="max-w-2xl"
    >
      <div data-testid="evento-detail-dialog-content" className="space-y-4 py-2 text-xs">
        {/* Banner de Estado y Fecha */}
        <div
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl p-3 border"
          style={{
            backgroundColor: `${cardColor}10`,
            borderColor: `${cardColor}30`,
          }}
        >
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-foreground">
              <Calendar className="h-4 w-4 text-primary" />
              <span>{formatDateES(evento.fecha)}</span>
            </div>
            {(evento.hora_inicio || evento.hora_fin) && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>
                  {formatTimeShort(evento.hora_inicio)}
                  {evento.hora_fin ? ` - ${formatTimeShort(evento.hora_fin)}` : ""}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isAgendado && (
              <span className="rounded-full bg-sky-500/10 px-3 py-1 font-bold text-sky-600 border border-sky-500/20">
                {t("detail_dialog.status_agendado")}
              </span>
            )}
            {isFinalizado && (
              <span className="rounded-full bg-emerald-500/10 px-3 py-1 font-bold text-emerald-600 border border-emerald-500/20">
                {t("detail_dialog.status_finalizado")}
              </span>
            )}
            {isCancelado && (
              <span className="rounded-full bg-rose-500/10 px-3 py-1 font-bold text-rose-600 border border-rose-500/20">
                {t("detail_dialog.status_cancelado")}
              </span>
            )}
          </div>
        </div>

        {/* Información de Salón y Capacidad */}
        <div className="grid grid-cols-2 gap-3 rounded-xl border border-border bg-card p-3">
          <div className="space-y-0.5">
            <span className="text-[11px] font-semibold text-muted-foreground">
              {t("detail_dialog.salon_label")}
            </span>
            <p className="font-bold text-foreground">
              {evento.salon?.nombre ||
                evento.salon_nombre ||
                evento.lugar ||
                t("detail_dialog.no_salon")}
            </p>
          </div>
          <div className="space-y-0.5">
            <span className="text-[11px] font-semibold text-muted-foreground">
              {t("detail_dialog.guests_label")}
            </span>
            <p className="font-bold text-foreground">
              {t("detail_dialog.guests_unit", {
                count: evento.cantidad_invitados ?? evento.cantidad_personas ?? 0,
              })}
            </p>
          </div>
        </div>

        {/* Suministros Programados */}
        <div className="space-y-2">
          <h4 className="font-bold uppercase tracking-wider text-muted-foreground text-[11px] flex items-center justify-between">
            <span>{t("detail_dialog.supplies_title")}</span>
            {estimatedCost > 0 && (
              <span className="font-mono text-foreground font-bold">
                {t("detail_dialog.estimated_cost_label", { cost: formatMoney(estimatedCost) })}
              </span>
            )}
          </h4>

          {/* Insumos */}
          {evento.items && evento.items.length > 0 && (
            <div className="rounded-xl border border-border overflow-hidden">
              <div className="bg-secondary/60 px-3 py-1.5 font-bold text-[11px] text-foreground flex items-center gap-1.5">
                <Package className="h-3.5 w-3.5 text-sky-500" />
                <span>
                  {t("detail_dialog.items_header", { count: evento.items.length })}
                </span>
              </div>
              <div className="divide-y divide-border/50 max-h-36 overflow-y-auto">
                {evento.items.map((it, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-1.5">
                    <span className="truncate flex-1">
                      {it.producto_nombre || `Producto #${it.producto_id}`}
                    </span>
                    <span className="font-mono text-muted-foreground">
                      {it.cantidad} {it.unidad_medida || "u."}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recetas */}
          {evento.recetas && evento.recetas.length > 0 && (
            <div className="rounded-xl border border-border overflow-hidden">
              <div className="bg-secondary/60 px-3 py-1.5 font-bold text-[11px] text-foreground flex items-center gap-1.5">
                <ChefHat className="h-3.5 w-3.5 text-amber-500" />
                <span>
                  {t("detail_dialog.recipes_header", { count: evento.recetas.length })}
                </span>
              </div>
              <div className="divide-y divide-border/50 max-h-36 overflow-y-auto">
                {evento.recetas.map((rc, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-1.5">
                    <span className="truncate flex-1">{rc.receta_nombre}</span>
                    <span className="font-mono text-muted-foreground">
                      {t("dialog.portions_unit", { count: rc.porciones })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Combos */}
          {evento.combos && evento.combos.length > 0 && (
            <div className="rounded-xl border border-border overflow-hidden">
              <div className="bg-secondary/60 px-3 py-1.5 font-bold text-[11px] text-foreground flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-purple-500" />
                <span>
                  {t("detail_dialog.combos_header", { count: evento.combos.length })}
                </span>
              </div>
              <div className="divide-y divide-border/50 max-h-36 overflow-y-auto">
                {evento.combos.map((cb, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-1.5">
                    <span className="truncate flex-1">{cb.combo_nombre}</span>
                    <span className="font-mono text-muted-foreground">
                      {t("dialog.packages_unit", { count: cb.cantidad })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Notas */}
        {evento.notas && (
          <div className="rounded-xl border border-border bg-card p-3 space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground">
              {t("detail_dialog.notes_label")}
            </span>
            <p className="text-foreground whitespace-pre-wrap">{evento.notas}</p>
          </div>
        )}

        {/* Botones de acción */}
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border/50 pt-3">
          {isAgendado && (
            <>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onCancel?.(evento);
                }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-500/20 active:scale-95 transition-all cursor-pointer"
              >
                <Ban className="h-3.5 w-3.5" />
                <span>{t("detail_dialog.btn_cancel")}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  onClose();
                  onEdit?.(evento);
                }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
              >
                <Pencil className="h-3.5 w-3.5" />
                <span>{t("detail_dialog.btn_edit")}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  onClose();
                  onExecute?.(evento);
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-emerald-700 active:scale-95 transition-all cursor-pointer"
              >
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>{t("detail_dialog.btn_execute")}</span>
              </button>
            </>
          )}

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer"
          >
            {t("detail_dialog.btn_close")}
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
