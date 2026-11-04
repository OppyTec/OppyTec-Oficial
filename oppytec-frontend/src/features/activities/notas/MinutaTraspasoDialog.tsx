import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Sparkles,
  Copy,
  Check,
  BookmarkPlus,
  AlertTriangle,
  Package,
  Clock,
  Users,
  Calendar,
  Layers,
  RefreshCw,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { apiRequest } from "@/shared/api/httpClient";
import { toast } from "sonner";
import { cn } from "@/shared/lib";
import { OFFICIAL_AREAS } from "@/shared/components/layout/AreaSelector";
import type { MinutaTraspasoResponse } from "../types";
import { MOCK_MINUTA_TRASPASO } from "../mockData";

export interface MinutaTraspasoDialogProps {
  readonly open: boolean;
  readonly areaId?: string;
  readonly onClose: () => void;
  readonly onSaveAsNota?: (data: {
    titulo: string;
    contenido: string;
    area_id?: string | null;
    categoria: string;
  }) => Promise<void>;
}

export function MinutaTraspasoDialog({
  open,
  areaId,
  onClose,
  onSaveAsNota,
}: MinutaTraspasoDialogProps) {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();

  const todayStr = new Date().toISOString().split("T")[0] ?? "";
  const [fecha, setFecha] = useState<string>(todayStr);
  const [selectedArea, setSelectedArea] = useState<string>(areaId && areaId !== "all" ? areaId : "all");
  const [isLoading, setIsLoading] = useState(false);
  const [minuta, setMinuta] = useState<MinutaTraspasoResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [isSavingNota, setIsSavingNota] = useState(false);

  useEffect(() => {
    if (open) {
      if (areaId && areaId !== "all") {
        setSelectedArea(areaId);
      }
      setFecha(todayStr);
      // Cargar automáticamente minuta al abrir
      void handleGenerarMinuta();
    } else {
      setMinuta(null);
      setCopied(false);
    }
  }, [open, areaId]);

  const handleGenerarMinuta = async () => {
    setIsLoading(true);
    try {
      const payload = {
        fecha: fecha || undefined,
        area_id: selectedArea !== "all" ? selectedArea : undefined,
      };
      const res = await apiRequest<MinutaTraspasoResponse>(
        "/api/v1/actividades/minuta-traspaso",
        {
          method: "POST",
          body: payload,
          fallbackData: MOCK_MINUTA_TRASPASO,
        }
      );
      setMinuta(res.data);
    } catch {
      toast.error(
        t("activities.minuta.error_fetch", {
          defaultValue: "Error al generar la minuta con OppyFy",
        })
      );
      setMinuta(MOCK_MINUTA_TRASPASO);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyClipboard = async () => {
    if (!minuta) return;
    try {
      await navigator.clipboard.writeText(minuta.resumen_ejecutivo);
      setCopied(true);
      toast.success(
        t("activities.minuta.copied_success", {
          defaultValue: "Minuta copiada al portapapeles",
        })
      );
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error(
        t("activities.minuta.error_copy", {
          defaultValue: "Error al copiar texto al portapapeles",
        })
      );
    }
  };

  const handleGuardarComoNota = async () => {
    if (!minuta || !onSaveAsNota) return;
    setIsSavingNota(true);
    try {
      const defaultPrefix = t("activities.minuta.note_title_prefix", { defaultValue: "📋 Minuta de Traspaso" });
      const generalArea = t("activities.notas.categories.general", { defaultValue: "General" });
      await onSaveAsNota({
        titulo: `${defaultPrefix} — ${minuta.fecha} (${minuta.area_id || generalArea})`,
        contenido: minuta.resumen_ejecutivo,
        area_id: minuta.area_id,
        categoria: "general",
      });
      toast.success(
        t("activities.minuta.saved_as_note", {
          defaultValue: "Minuta guardada como Nota de Equipo destacada",
        })
      );
      onClose();
    } catch {
      toast.error(
        t("activities.minuta.error_save_as_note", {
          defaultValue: "Error al guardar la minuta como nota",
        })
      );
    } finally {
      setIsSavingNota(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      isMobile={isMobile}
      maxWidth="max-w-3xl"
      title={t("activities.minuta.dialog_title", {
        defaultValue: "🤖 Resumen de Traspaso (OppyFy AI)",
      })}
      description={t("activities.minuta.dialog_desc", {
        defaultValue:
          "Síntesis ejecutiva del turno para el Chef y Gerente a partir de notas, tareas y dotación.",
      })}
    >
      <div className="flex flex-col gap-4 max-h-[75vh] overflow-y-auto pr-1">
        {/* Barra superior de filtros: Fecha, Área y Botón Regenerar */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5 items-end rounded-xl border border-border bg-secondary/30 p-2.5">
          <div className="sm:col-span-5 flex flex-col gap-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{t("activities.minuta.date_label", { defaultValue: "Fecha del Turno" })}</span>
            </label>
            <input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="sm:col-span-4 flex flex-col gap-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              <Layers className="h-3 w-3" />
              <span>{t("activities.minuta.area_label", { defaultValue: "Área Operativa" })}</span>
            </label>
            <select
              value={selectedArea}
              onChange={(e) => setSelectedArea(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">{t("activities.common.all_areas", { defaultValue: "Todas las áreas" })}</option>
              {OFFICIAL_AREAS.filter((a) => a.id !== "all").map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="sm:col-span-3">
            <button
              type="button"
              disabled={isLoading}
              onClick={() => void handleGenerarMinuta()}
              className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-black uppercase tracking-wider text-white hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50 cursor-pointer shadow-md shadow-blue-500/20"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
              <span>{t("activities.minuta.refresh", { defaultValue: "Actualizar" })}</span>
            </button>
          </div>
        </div>

        {/* Estado de Carga */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center p-8 gap-3 text-center">
            <div className="relative">
              <Sparkles className="h-10 w-10 text-blue-500 animate-pulse" />
              <div className="absolute inset-0 blur-md bg-blue-500/30 -z-10 rounded-full" />
            </div>
            <div className="text-sm font-bold text-foreground">
              {t("activities.minuta.generating", {
                defaultValue: "OppyFy está consolidando la bitácora del turno...",
              })}
            </div>
            <p className="text-xs text-muted-foreground max-w-sm">
              {t("activities.minuta.generating_desc", {
                defaultValue: "Analizando incidentes de bitácora, avance de checklists y horas laborales de colaboradores.",
              })}
            </p>
          </div>
        )}

        {/* Contenido de la Minuta */}
        {!isLoading && minuta && (
          <div className="flex flex-col gap-4 animate-in fade-in-50 duration-200">
            {/* Badges de Métricas de Cierre */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="rounded-xl border border-border bg-card p-2.5 flex items-center gap-2.5 shadow-sm">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500 shrink-0">
                  <AlertTriangle className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-semibold">
                    {t("activities.minuta.metrics.incidents", { defaultValue: "Incidentes" })}
                  </div>
                  <div className="text-sm font-black text-foreground">
                    {minuta.puntos_clave.incidentes.length > 0 &&
                    !minuta.puntos_clave.incidentes[0]?.includes("Sin incidentes")
                      ? minuta.puntos_clave.incidentes.length
                      : 0}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-2.5 flex items-center gap-2.5 shadow-sm">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500 shrink-0">
                  <Package className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-semibold">
                    {t("activities.minuta.metrics.production", { defaultValue: "Producción" })}
                  </div>
                  <div className="text-sm font-black text-foreground">
                    {minuta.puntos_clave.produccion.length}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-2.5 flex items-center gap-2.5 shadow-sm">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-500/10 text-rose-500 shrink-0">
                  <Clock className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-semibold">
                    {t("activities.minuta.metrics.pending", { defaultValue: "Pendientes" })}
                  </div>
                  <div className="text-sm font-black text-foreground">
                    {minuta.estadisticas.tareas_incompletas}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-2.5 flex items-center gap-2.5 shadow-sm">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500 shrink-0">
                  <Users className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-semibold">
                    {t("activities.minuta.metrics.collaborators", { defaultValue: "Colaboradores" })}
                  </div>
                  <div className="text-sm font-black text-foreground">
                    {minuta.puntos_clave.dotacion.total_colaboradores}
                  </div>
                </div>
              </div>
            </div>

            {/* Los 4 Puntos Clave Estructurados */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* 1. Incidentes */}
              <div className="rounded-xl border border-border bg-card p-3 shadow-sm flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-amber-500">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>{t("activities.minuta.sections.incidents", { defaultValue: "1. Incidentes y Novedades Críticas" })}</span>
                </div>
                <ul className="text-xs text-foreground/90 space-y-1.5 pl-1">
                  {minuta.puntos_clave.incidentes.map((inc, i) => (
                    <li key={i} className="leading-relaxed">
                      {inc}
                    </li>
                  ))}
                </ul>
              </div>

              {/* 2. Producción */}
              <div className="rounded-xl border border-border bg-card p-3 shadow-sm flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-emerald-500">
                  <Package className="h-3.5 w-3.5" />
                  <span>{t("activities.minuta.sections.production", { defaultValue: "2. Producción y Stock" })}</span>
                </div>
                <ul className="text-xs text-foreground/90 space-y-1.5 pl-1">
                  {minuta.puntos_clave.produccion.map((prod, i) => (
                    <li key={i} className="leading-relaxed">
                      {prod}
                    </li>
                  ))}
                </ul>
              </div>

              {/* 3. Tareas Pendientes */}
              <div className="rounded-xl border border-border bg-card p-3 shadow-sm flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-rose-500">
                  <Clock className="h-3.5 w-3.5" />
                  <span>{t("activities.minuta.sections.pending_tasks", { defaultValue: "3. Tareas Pendientes y Relevo" })}</span>
                </div>
                {minuta.puntos_clave.tareas_pendientes.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    {t("activities.minuta.no_pending_tasks", { defaultValue: "✅ 100% de tareas completadas. Turno listo sin pendientes." })}
                  </p>
                ) : (
                  <ul className="text-xs text-foreground/90 space-y-2 pl-1">
                    {minuta.puntos_clave.tareas_pendientes.map((tp) => (
                      <li key={tp.id} className="border-l-2 border-rose-500/60 pl-2">
                        <span className="font-bold text-foreground">{tp.titulo}</span>
                        <div className="text-[11px] text-muted-foreground">
                          {t("activities.minuta.justification", { defaultValue: "Justificación:" })} {tp.nota_incompleta}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 4. Dotación */}
              <div className="rounded-xl border border-border bg-card p-3 shadow-sm flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-blue-500">
                  <Users className="h-3.5 w-3.5" />
                  <span>{t("activities.minuta.sections.staff", { defaultValue: "4. Dotación y Asistencia" })}</span>
                </div>
                <div className="text-xs text-foreground/90">
                  <p className="font-semibold mb-1">
                    {t("activities.minuta.collaborators_registered", {
                      count: minuta.puntos_clave.dotacion.total_colaboradores,
                      defaultValue: `${minuta.puntos_clave.dotacion.total_colaboradores} colaboradores registrados en turno.`,
                    })}
                  </p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {minuta.puntos_clave.dotacion.turnos.map((tur) => (
                      <span
                        key={tur.id}
                        className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground"
                      >
                        {t("activities.minuta.collaborator_shift", {
                          id: tur.user_id,
                          start: tur.hora_inicio || "--",
                          end: tur.hora_fin || "--",
                          defaultValue: `Colaborador #${tur.user_id} (${tur.hora_inicio || "--"} - ${tur.hora_fin || "--"})`,
                        })}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Vista Previa en Markdown Texto Completo */}
            <div className="rounded-xl border border-border bg-background p-3 flex flex-col gap-1.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                {t("activities.minuta.markdown_preview", { defaultValue: "Vista Markdown Copiable" })}
              </div>
              <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap max-h-40 overflow-y-auto bg-secondary/40 p-2.5 rounded-lg border border-border custom-scrollbar">
                {minuta.resumen_ejecutivo}
              </pre>
            </div>
          </div>
        )}

        {/* Barra de Acciones Final */}
        <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-border shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border px-4 py-2 text-xs font-bold text-muted-foreground hover:bg-secondary transition-all cursor-pointer"
          >
            {t("activities.common.close", { defaultValue: "Cerrar" })}
          </button>

          {minuta && (
            <>
              <button
                type="button"
                onClick={() => void handleCopyClipboard()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-secondary/80 px-4 py-2 text-xs font-bold text-foreground hover:bg-secondary transition-all cursor-pointer shadow-sm active:scale-95"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    <span className="text-emerald-500">{t("activities.minuta.copied", { defaultValue: "Copiado" })}</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>{t("activities.minuta.copy_btn", { defaultValue: "Copiar Minuta" })}</span>
                  </>
                )}
              </button>

              {onSaveAsNota && (
                <button
                  type="button"
                  disabled={isSavingNota}
                  onClick={() => void handleGuardarComoNota()}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-black uppercase tracking-wider text-white hover:bg-blue-700 active:scale-95 transition-all cursor-pointer shadow-md shadow-blue-500/20 disabled:opacity-50"
                >
                  <BookmarkPlus className="h-3.5 w-3.5" />
                  <span>{t("activities.minuta.save_as_note_btn", { defaultValue: "Guardar como Nota" })}</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </ResponsiveDialog>
  );
}
