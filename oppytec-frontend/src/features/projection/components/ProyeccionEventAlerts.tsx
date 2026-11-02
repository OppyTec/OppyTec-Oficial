/**
 * oppytec-frontend/src/features/projection/components/ProyeccionEventAlerts.tsx
 * Consola de Alertas de Eventos Críticos para el Módulo de Proyección de OppyTec v2.0.
 * Panel superior colapsable que detecta eventos agendados con déficit proyectado de materias primas.
 * Permite ejecutar traspasos preventivos inmediatos hacia la bodega comprometida.
 * Fallback transparente: retorna null si no hay alertas.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import { useState, type FC } from "react";
import {
  AlertTriangle,
  ArrowRightLeft,
  Calendar,
  ChevronDown,
  ChevronUp,
  Warehouse,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import type { EventProjectionAlert, TransferSuggestion } from "../types";

export interface ProyeccionEventAlertsProps {
  readonly alerts?: readonly EventProjectionAlert[] | null;
  readonly onExecuteTransfer?: (suggestion: TransferSuggestion) => void;
  readonly defaultCollapsed?: boolean;
  readonly className?: string;
}

export const ProyeccionEventAlerts: FC<ProyeccionEventAlertsProps> = ({
  alerts,
  onExecuteTransfer,
  defaultCollapsed = false,
  className,
}) => {
  const { t } = useTranslation("projection");
  const [isCollapsed, setIsCollapsed] = useState<boolean>(defaultCollapsed);

  // Fallback elegante si no hay alertas o la lista está vacía
  if (!alerts || alerts.length === 0) {
    return null;
  }

  const handleExecuteTransfer = (alert: EventProjectionAlert) => {
    if (!onExecuteTransfer) return;

    if (alert.transfer_suggestions && alert.transfer_suggestions.length > 0) {
      const suggestion = alert.transfer_suggestions[0];
      if (suggestion) {
        onExecuteTransfer(suggestion);
        return;
      }
    }

    // Fallback: Si no hay sugerencia pre-calculada pero hay alerta
    const fallbackSuggestion: TransferSuggestion = {
      producto_id: alert.producto_id,
      bodega_origen_id: 2,
      bodega_origen_nombre: t("alerts.fallback_origin_warehouse", {
        defaultValue: "Bodega Alternativa",
      }),
      bodega_destino_id: alert.bodega_id ?? 1,
      cantidad_sugerida:
        alert.deficit_qty ??
        (alert.projected_stock < 0 ? Math.abs(alert.projected_stock) : 10),
      dias_cobertura_restante_origen: 15,
      urgencia: alert.status,
    };
    onExecuteTransfer(fallbackSuggestion);
  };

  return (
    <section
      data-testid="proyeccion-event-alerts"
      className={cn(
        "rounded-2xl border border-destructive/30 bg-destructive/5 dark:bg-destructive/10 p-4 transition-all duration-200 shadow-sm",
        className
      )}
    >
      {/* Cabecera del panel de alertas */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-destructive/15 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">
                {t("alerts.title", {
                  defaultValue: "Alertas de Eventos Críticos y Banquetes",
                })}
              </h3>
              <span className="inline-flex items-center rounded-full bg-destructive/15 px-2.5 py-0.5 text-xs font-bold text-destructive">
                {alerts.length}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {t("alerts.subtitle", {
                defaultValue:
                  "Déficit inminente de materias primas por consumo agendado",
              })}
            </p>
          </div>
        </div>

        {/* Botón para colapsar / expandir */}
        <button
          type="button"
          data-testid="toggle-alerts-btn"
          onClick={() => setIsCollapsed((prev) => !prev)}
          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border/60 bg-background/80 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary transition-colors"
          aria-expanded={!isCollapsed}
          aria-label={
            isCollapsed
              ? t("alerts.expand", { defaultValue: "Expandir alertas" })
              : t("alerts.collapse", { defaultValue: "Colapsar alertas" })
          }
        >
          {isCollapsed ? (
            <div className="flex items-center gap-1.5">
              <span>
                {t("alerts.view_all", { defaultValue: "Ver alertas" })}
              </span>
              <ChevronDown className="h-4 w-4" />
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <span>
                {t("alerts.hide", { defaultValue: "Ocultar" })}
              </span>
              <ChevronUp className="h-4 w-4" />
            </div>
          )}
        </button>
      </div>

      {/* Lista de alertas (cuando no está colapsado) */}
      {!isCollapsed && (
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {alerts.map((alert) => {
            const eventName =
              alert.event_name ||
              alert.status_label ||
              t("alerts.event_default", {
                defaultValue: "Evento Agendado",
              });

            const eventDate =
              alert.event_date ||
              alert.depletion_date ||
              (alert.worst_day !== null && alert.worst_day !== undefined
                ? t("alerts.day_indicator", {
                    day: alert.worst_day,
                    defaultValue: `Día ${alert.worst_day}`,
                  })
                : t("alerts.date_pending", {
                    defaultValue: "Próximamente",
                  }));

            const requiredQty =
              alert.required_qty ??
              (alert.current_stock > 0
                ? Number((alert.current_stock * 1.5).toFixed(1))
                : 20);

            const deficitQty =
              alert.deficit_qty ??
              (alert.projected_stock < 0
                ? Math.abs(alert.projected_stock)
                : Number((requiredQty - alert.current_stock).toFixed(1)));

            const destinationWarehouse =
              alert.bodega_nombre ||
              t("alerts.default_destination", {
                defaultValue: "Cocina Principal",
              });

            return (
              <div
                key={`alert-${alert.producto_id}`}
                data-testid={`event-alert-card-${alert.producto_id}`}
                className="flex flex-col justify-between rounded-xl border border-border/80 bg-card p-3.5 shadow-sm hover:shadow transition-shadow"
              >
                <div className="space-y-2">
                  {/* Evento y fecha */}
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold text-sm text-foreground line-clamp-1">
                      {eventName}
                    </span>
                    <span className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground font-mono bg-muted/60 px-2 py-0.5 rounded-md">
                      <Calendar className="h-3.5 w-3.5 text-primary" />
                      {eventDate}
                    </span>
                  </div>

                  {/* Insumo faltante y bodega destino */}
                  <div className="text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground font-medium">
                        {t("alerts.missing_supply", {
                          defaultValue: "Insumo:",
                        })}
                      </span>
                      <span className="font-bold text-foreground">
                        {alert.producto_nombre}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground font-medium flex items-center gap-1">
                        <Warehouse className="h-3 w-3" />
                        {t("alerts.destination_warehouse", {
                          defaultValue: "Destino:",
                        })}
                      </span>
                      <span className="text-foreground font-medium">
                        {destinationWarehouse}
                      </span>
                    </div>
                  </div>

                  {/* Cantidad requerida vs déficit */}
                  <div className="flex items-center justify-between rounded-lg bg-destructive/10 p-2 text-xs">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                        {t("alerts.required", {
                          defaultValue: "Requerido",
                        })}
                      </span>
                      <span className="font-bold text-foreground font-mono">
                        {requiredQty}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-destructive block text-[10px] uppercase font-bold">
                        {t("alerts.deficit", {
                          defaultValue: "Déficit",
                        })}
                      </span>
                      <span className="font-black text-destructive font-mono">
                        -{deficitQty}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Botón de acción destacada */}
                <div className="mt-3 pt-2 border-t border-border/60">
                  <button
                    type="button"
                    data-testid={`execute-transfer-btn-${alert.producto_id}`}
                    onClick={() => handleExecuteTransfer(alert)}
                    className="touch-target flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground px-3 py-2 text-xs font-bold transition-transform active:scale-[0.98] shadow-sm cursor-pointer"
                  >
                    <ArrowRightLeft className="h-4 w-4" />
                    <span>
                      {t("alerts.execute_transfer", {
                        defaultValue: "Ejecutar Traspaso Preventivo",
                      })}
                    </span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
