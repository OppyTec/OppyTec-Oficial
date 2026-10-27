/**
 * oppytec-frontend/src/features/procurement/mermas/MermaDateRangePicker.tsx
 * Selector reactivo de rango de fechas para Gestión Analítica de Mermas (Fase 6.2).
 * Presets: "hoy", "7d", "30d", "mes_actual", "mes_anterior", "personalizado".
 * Touch targets >= 44px y refresco instantáneo sin recargar la página.
 */

import { useState, useEffect } from "react";
import { Calendar, Check, RotateCcw } from "lucide-react";
import type { DateRangePreset } from "../types";

export interface MermaDateRangePickerProps {
  readonly preset: DateRangePreset;
  readonly dateFrom: string | null;
  readonly dateTo: string | null;
  readonly onPresetChange: (preset: DateRangePreset) => void;
  readonly onCustomRangeChange: (dateFrom: string, dateTo: string) => void;
  readonly onReset?: () => void;
}

const PRESET_OPTIONS: ReadonlyArray<{
  readonly value: DateRangePreset;
  readonly label: string;
  readonly shortLabel: string;
}> = [
  { value: "hoy", label: "Hoy", shortLabel: "Hoy" },
  { value: "7d", label: "Últimos 7 días", shortLabel: "7D" },
  { value: "30d", label: "Últimos 30 días", shortLabel: "30D" },
  { value: "mes_actual", label: "Este Mes", shortLabel: "Mes Actual" },
  { value: "mes_anterior", label: "Mes Anterior", shortLabel: "Mes Ant." },
  { value: "personalizado", label: "Personalizado", shortLabel: "Fechas" },
];

export function MermaDateRangePicker({
  preset,
  dateFrom,
  dateTo,
  onPresetChange,
  onCustomRangeChange,
  onReset,
}: MermaDateRangePickerProps) {
  const [localFrom, setLocalFrom] = useState<string>(dateFrom ?? "");
  const [localTo, setLocalTo] = useState<string>(dateTo ?? "");

  useEffect(() => {
    setLocalFrom(dateFrom ?? "");
    setLocalTo(dateTo ?? "");
  }, [dateFrom, dateTo]);

  const handlePresetClick = (nextPreset: DateRangePreset) => {
    if (nextPreset === "personalizado") {
      const fallbackFrom = localFrom || dateFrom || "2026-10-01";
      const fallbackTo = localTo || dateTo || "2026-10-26";
      setLocalFrom(fallbackFrom);
      setLocalTo(fallbackTo);
      onCustomRangeChange(fallbackFrom, fallbackTo);
      return;
    }
    onPresetChange(nextPreset);
  };

  const handleFromChange = (val: string) => {
    setLocalFrom(val);
    if (val && localTo) {
      onCustomRangeChange(val, localTo);
    }
  };

  const handleToChange = (val: string) => {
    setLocalTo(val);
    if (localFrom && val) {
      onCustomRangeChange(localFrom, val);
    }
  };

  const handleApplyCustom = () => {
    if (localFrom && localTo) {
      onCustomRangeChange(localFrom, localTo);
    }
  };

  return (
    <div
      data-testid="merma-date-range-picker"
      className="glass-card rounded-2xl border border-border bg-card p-3.5 shadow-sm space-y-3"
    >
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        {/* Etiqueta e indicador de rango activo */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs font-black uppercase tracking-wider text-foreground">
              Período de Análisis
            </div>
            <div
              data-testid="merma-active-date-range-label"
              className="text-[11px] font-mono font-semibold text-muted-foreground"
            >
              {dateFrom && dateTo
                ? `${dateFrom} → ${dateTo}`
                : "Rango completo"}
            </div>
          </div>
        </div>

        {/* Botones de Presets Rápidos (Touch targets >= 44px) */}
        <div
          role="group"
          aria-label="Presets de rango de fechas"
          className="flex flex-wrap items-center gap-1.5"
        >
          {PRESET_OPTIONS.map((opt) => {
            const isActive = preset === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                data-testid={`preset-btn-${opt.value}`}
                aria-pressed={isActive}
                onClick={() => handlePresetClick(opt.value)}
                className={`touch-target min-h-[44px] px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer select-none ${
                  isActive
                    ? "bg-rose-600 text-white shadow-sm shadow-rose-600/20"
                    : "bg-secondary/60 text-muted-foreground hover:text-foreground hover:bg-secondary border border-border/60"
                }`}
              >
                <span>{opt.label}</span>
              </button>
            );
          })}

          {onReset && preset !== "30d" && (
            <button
              type="button"
              data-testid="btn-reset-date-range"
              onClick={onReset}
              title="Restablecer a 30 días"
              className="touch-target min-h-[44px] min-w-[44px] inline-flex items-center justify-center rounded-xl border border-border bg-background text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Controles de Rango Personalizado */}
      {preset === "personalizado" && (
        <div
          data-testid="custom-date-range-controls"
          className="flex flex-col sm:flex-row sm:items-end gap-3 pt-3 border-t border-border/70 animate-in fade-in duration-200"
        >
          <div className="flex-1 space-y-1">
            <label
              htmlFor="merma-date-from"
              className="block text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400"
            >
              Fecha Desde
            </label>
            <input
              id="merma-date-from"
              type="date"
              data-testid="input-date-from"
              min="2020-01-01"
              max="2099-12-31"
              value={localFrom}
              onChange={(e) => handleFromChange(e.target.value)}
              className="w-full min-h-[44px] rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono font-bold text-foreground focus:border-primary focus:outline-none"
            />
          </div>

          <div className="flex-1 space-y-1">
            <label
              htmlFor="merma-date-to"
              className="block text-[11px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400"
            >
              Fecha Hasta
            </label>
            <input
              id="merma-date-to"
              type="date"
              data-testid="input-date-to"
              min="2020-01-01"
              max="2099-12-31"
              value={localTo}
              onChange={(e) => handleToChange(e.target.value)}
              className="w-full min-h-[44px] rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono font-bold text-foreground focus:border-primary focus:outline-none"
            />
          </div>

          <button
            type="button"
            data-testid="btn-apply-custom-range"
            onClick={handleApplyCustom}
            className="touch-target min-h-[44px] inline-flex items-center justify-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-95 transition-all cursor-pointer"
          >
            <Check className="h-4 w-4" />
            <span>Aplicar Rango</span>
          </button>
        </div>
      )}
    </div>
  );
}

export default MermaDateRangePicker;
