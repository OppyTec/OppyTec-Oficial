// oppytec-frontend/src/features/events/components/EventosCalendar.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/shared/lib";
import type { Evento, EventoListItem, Salon, CalendarViewMode } from "../types";
import {
  MONTH_NAMES,
  formatDateISO,
  getMondayOfWeek,
  isSameDay,
  formatTimeShort,
  areIntervalsColliding,
} from "../utils/dateUtils";

export type EventoCalendarItem = Evento | EventoListItem;

export interface EventosCalendarProps {
  readonly eventos: EventoCalendarItem[];
  readonly salones?: Salon[];
  readonly onSelectDate?: (dateStr: string, salonId?: string) => void;
  readonly onSelectEvento?: (evento: EventoCalendarItem) => void;
  readonly onNewEvento?: (dateStr?: string) => void;
}

const STORAGE_VIEW_KEY = "oppytec_eventos_calendar_view";

const MONTH_KEYS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
] as const;

const DAY_SHORT_KEYS = [
  "lun",
  "mar",
  "mie",
  "jue",
  "vie",
  "sab",
  "dom",
] as const;

export function EventosCalendar({
  eventos,
  onSelectDate,
  onSelectEvento,
  onNewEvento,
}: EventosCalendarProps) {
  const { t } = useTranslation("events");
  const [currentDate, setCurrentDate] = useState<Date>(() => new Date());
  const [viewMode, setViewMode] = useState<CalendarViewMode>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_VIEW_KEY);
      if (saved && ["month", "week", "3days", "day"].includes(saved)) {
        return saved as CalendarViewMode;
      }
    } catch {
      // Fallback
    }
    return "month";
  });

  const dayNamesShort = useMemo(
    () => DAY_SHORT_KEYS.map((k) => t(`calendar.days_short.${k}`)),
    [t]
  );

  const getMonthName = (mIndex: number): string => {
    const key = MONTH_KEYS[mIndex];
    return key ? t(`calendar.months.${key}`) : MONTH_NAMES[mIndex] || "";
  };

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_VIEW_KEY, viewMode);
    } catch {
      // Ignore
    }
  }, [viewMode]);

  // Navegación de periodos
  const handlePrev = () => {
    setCurrentDate((prev) => {
      const next = new Date(prev);
      if (viewMode === "month") {
        next.setMonth(next.getMonth() - 1);
      } else if (viewMode === "week") {
        next.setDate(next.getDate() - 7);
      } else if (viewMode === "3days") {
        next.setDate(next.getDate() - 3);
      } else {
        next.setDate(next.getDate() - 1);
      }
      return next;
    });
  };

  const handleNext = () => {
    setCurrentDate((prev) => {
      const next = new Date(prev);
      if (viewMode === "month") {
        next.setMonth(next.getMonth() + 1);
      } else if (viewMode === "week") {
        next.setDate(next.getDate() + 7);
      } else if (viewMode === "3days") {
        next.setDate(next.getDate() + 3);
      } else {
        next.setDate(next.getDate() + 1);
      }
      return next;
    });
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  // Cálculo de detección de colisiones entre eventos en el mismo salón y día
  const collidingEventIds = useMemo(() => {
    const colliding = new Set<string>();
    const groupedByDateAndSalon = new Map<string, EventoCalendarItem[]>();

    eventos.forEach((ev) => {
      if (ev.cancelado) return;
      const salonKey =
        ev.salon_id ||
        ("salon" in ev && ev.salon?.nombre) ||
        ev.salon_nombre ||
        ("lugar" in ev ? ev.lugar : null) ||
        "sin-salon";

      if (salonKey === "sin-salon") return;
      const key = `${ev.fecha}_${salonKey}`;
      const group = groupedByDateAndSalon.get(key) ?? [];
      group.push(ev);
      groupedByDateAndSalon.set(key, group);
    });

    groupedByDateAndSalon.forEach((list) => {
      if (list.length < 2) return;
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const a = list[i]!;
          const b = list[j]!;
          if (areIntervalsColliding(a.hora_inicio, a.hora_fin, b.hora_inicio, b.hora_fin)) {
            colliding.add(a.id);
            colliding.add(b.id);
          }
        }
      }
    });

    return colliding;
  }, [eventos]);

  // Generación de fechas según vista
  const daysToRender = useMemo(() => {
    if (viewMode === "month") {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();

      // Primer día del mes
      const firstDay = new Date(year, month, 1);
      const startingMonday = getMondayOfWeek(firstDay);

      const days: Date[] = [];
      const curr = new Date(startingMonday);

      // Renderizar 35 o 42 días (5 o 6 semanas completas de Lunes a Domingo)
      for (let i = 0; i < 42; i++) {
        days.push(new Date(curr));
        curr.setDate(curr.getDate() + 1);
        if (i >= 34 && curr.getMonth() !== month && curr.getDay() === 1) {
          break; // Si ya cubrimos el mes y el siguiente es Lunes
        }
      }
      return days;
    }

    if (viewMode === "week") {
      const monday = getMondayOfWeek(currentDate);
      const days: Date[] = [];
      const curr = new Date(monday);
      for (let i = 0; i < 7; i++) {
        days.push(new Date(curr));
        curr.setDate(curr.getDate() + 1);
      }
      return days;
    }

    if (viewMode === "3days") {
      const days: Date[] = [];
      const curr = new Date(currentDate);
      for (let i = 0; i < 3; i++) {
        days.push(new Date(curr));
        curr.setDate(curr.getDate() + 1);
      }
      return days;
    }

    // Single day
    return [new Date(currentDate)];
  }, [currentDate, viewMode]);

  // Título del periodo actual
  const periodTitle = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = getMonthName(currentDate.getMonth());
    if (viewMode === "month") {
      return `${month} ${year}`;
    }
    if (viewMode === "day") {
      return `${currentDate.getDate()} ${month}, ${year}`;
    }
    if (daysToRender.length > 0) {
      const first = daysToRender[0]!;
      const last = daysToRender[daysToRender.length - 1]!;
      return `${first.getDate()} ${getMonthName(first.getMonth()).slice(0, 3)} - ${last.getDate()} ${getMonthName(last.getMonth()).slice(0, 3)} ${year}`;
    }
    return `${month} ${year}`;
  }, [currentDate, viewMode, daysToRender, t]);

  // Indexar eventos por fecha ISO
  const eventsByDate = useMemo(() => {
    const map = new Map<string, EventoCalendarItem[]>();
    eventos.forEach((ev) => {
      const dateKey = ev.fecha;
      const list = map.get(dateKey) ?? [];
      list.push(ev);
      map.set(dateKey, list);
    });
    return map;
  }, [eventos]);

  return (
    <div
      data-testid="eventos-calendar"
      className="flex flex-col rounded-2xl border border-border bg-card p-4 shadow-sm space-y-4"
    >
      {/* Barra de control superior del calendario */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        {/* Navegación y Hoy */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            data-testid="calendar-prev"
            aria-label={t("calendar.prev")}
            onClick={handlePrev}
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-background text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          <button
            type="button"
            data-testid="calendar-today"
            onClick={handleToday}
            className="inline-flex h-9 items-center justify-center rounded-xl border border-border bg-background px-3 text-xs font-bold text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
          >
            {t("calendar.today")}
          </button>

          <button
            type="button"
            data-testid="calendar-next"
            aria-label={t("calendar.next")}
            onClick={handleNext}
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-background text-foreground hover:bg-secondary active:scale-95 transition-all cursor-pointer"
          >
            <ChevronRight className="h-4 w-4" />
          </button>

          <h2 className="ml-2 text-base font-bold text-foreground tracking-tight capitalize">
            {periodTitle}
          </h2>
        </div>

        {/* Selector de vistas */}
        <div className="flex items-center gap-1 rounded-xl bg-secondary/70 p-1 border border-border/50">
          {(
            [
              { id: "month", label: t("calendar.view_month") },
              { id: "week", label: t("calendar.view_week") },
              { id: "3days", label: t("calendar.view_3days") },
              { id: "day", label: t("calendar.view_day") },
            ] as const
          ).map((v) => (
            <button
              key={v.id}
              type="button"
              data-testid={`calendar-view-${v.id}`}
              onClick={() => setViewMode(v.id)}
              className={cn(
                "rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer",
                viewMode === v.id
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cabecera de días de la semana (Lunes a Domingo) */}
      {viewMode === "month" && (
        <div className="grid grid-cols-7 gap-1 text-center text-xs font-bold text-muted-foreground uppercase tracking-wider py-1 border-b border-border/40">
          {dayNamesShort.map((d) => (
            <div key={d}>{d}</div>
          ))}
        </div>
      )}

      {/* Grilla principal del calendario */}
      <div
        className={cn(
          "grid gap-2",
          viewMode === "month" && "grid-cols-7",
          viewMode === "week" && "grid-cols-1 md:grid-cols-7",
          viewMode === "3days" && "grid-cols-1 md:grid-cols-3",
          viewMode === "day" && "grid-cols-1"
        )}
      >
        {daysToRender.map((dayDate) => {
          const dateISO = formatDateISO(dayDate);
          const isCurrentMonth = dayDate.getMonth() === currentDate.getMonth();
          const isToday = isSameDay(dayDate, new Date());
          const dayEvents = eventsByDate.get(dateISO) ?? [];

          return (
            <div
              key={dateISO}
              data-testid={`calendar-day-${dateISO}`}
              onClick={() => {
                onSelectDate?.(dateISO);
              }}
              className={cn(
                "group relative flex flex-col min-h-[110px] rounded-xl border p-2 transition-all cursor-pointer",
                isToday
                  ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                  : isCurrentMonth || viewMode !== "month"
                  ? "border-border/60 bg-background/50 hover:bg-secondary/40"
                  : "border-border/30 bg-muted/20 opacity-50 hover:opacity-100",
                viewMode !== "month" && "min-h-[220px]"
              )}
            >
              {/* Encabezado del día */}
              <div className="flex items-center justify-between mb-1.5">
                <span
                  className={cn(
                    "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold",
                    isToday
                      ? "bg-primary text-primary-foreground font-black shadow-sm"
                      : "text-foreground group-hover:text-primary"
                  )}
                >
                  {dayDate.getDate()}
                </span>

                {viewMode !== "month" && (
                  <span className="text-xs font-semibold text-muted-foreground">
                    {dayNamesShort[(dayDate.getDay() + 6) % 7]}
                  </span>
                )}

                {/* Botón rápido para agregar evento en este día */}
                <button
                  type="button"
                  title={t("calendar.quick_add_title", { date: dateISO })}
                  data-testid={`btn-quick-add-${dateISO}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onNewEvento?.(dateISO);
                  }}
                  className="opacity-0 group-hover:opacity-100 inline-flex h-5 w-5 items-center justify-center rounded-md bg-secondary text-secondary-foreground hover:bg-primary hover:text-primary-foreground transition-all cursor-pointer"
                >
                  <Plus className="h-3 w-3" />
                </button>
              </div>

              {/* Lista de eventos del día */}
              <div className="flex-1 space-y-1 overflow-y-auto max-h-[160px] pr-0.5">
                {dayEvents.map((ev) => {
                  const hasCollision = collidingEventIds.has(ev.id);
                  const evColor = ev.color || "#ec4899";
                  const salonLabel =
                    ("salon" in ev && ev.salon?.nombre) ||
                    ev.salon_nombre ||
                    ("lugar" in ev ? ev.lugar : null);

                  return (
                    <div
                      key={ev.id}
                      data-testid={`calendar-event-${ev.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectEvento?.(ev);
                      }}
                      className={cn(
                        "relative flex flex-col gap-0.5 rounded-lg p-1.5 text-[11px] font-medium transition-all hover:scale-[1.02] hover:shadow cursor-pointer border",
                        ev.cancelado ? "opacity-60 line-through" : ""
                      )}
                      style={{
                        backgroundColor: `${evColor}18`,
                        borderColor: hasCollision ? "#ef4444" : `${evColor}40`,
                        color: evColor,
                      }}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-bold truncate text-foreground flex-1">
                          {ev.nombre}
                        </span>
                        {hasCollision && (
                          <span
                            title={t("calendar.collision_alert")}
                            className="inline-flex items-center text-rose-500 animate-bounce"
                          >
                            <AlertTriangle className="h-3 w-3" />
                          </span>
                        )}
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        {ev.hora_inicio && (
                          <span className="flex items-center gap-0.5">
                            <Clock className="h-2.5 w-2.5" />
                            {formatTimeShort(ev.hora_inicio)}
                          </span>
                        )}
                        {salonLabel && (
                          <span className="truncate max-w-[80px]">{salonLabel}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
