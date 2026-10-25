// oppytec-frontend/src/features/gestion/components/FacturaImportModal/UnidadMedidaCombobox.tsx
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Scale, ChevronDown, Check } from "lucide-react";
import { cn } from "@/shared/lib/utils";

export interface MeasurementUnit {
  readonly id: string;
  readonly label: string;
  readonly symbol: string;
  readonly defaultFactor: number;
}

export const COMMON_MEASUREMENT_UNITS: readonly MeasurementUnit[] = [
  { id: "kg", label: "Kilogramos", symbol: "kg", defaultFactor: 1 },
  { id: "g", label: "Gramos", symbol: "g", defaultFactor: 0.001 },
  { id: "l", label: "Litros", symbol: "L", defaultFactor: 1 },
  { id: "ml", label: "Mililitros", symbol: "mL", defaultFactor: 0.001 },
  { id: "un", label: "Unidades", symbol: "un", defaultFactor: 1 },
  { id: "pack", label: "Pack", symbol: "pack", defaultFactor: 6 },
  { id: "caja", label: "Caja", symbol: "caja", defaultFactor: 12 },
  { id: "botella", label: "Botella", symbol: "bot", defaultFactor: 1 },
  { id: "lata", label: "Lata", symbol: "lata", defaultFactor: 1 },
  { id: "saco", label: "Saco", symbol: "saco", defaultFactor: 25 },
];

export interface UnidadMedidaComboboxProps {
  readonly value: string;
  readonly factor?: number;
  readonly onChange: (unit: string, factor: number) => void;
  readonly className?: string;
  readonly disabled?: boolean;
}

export const UnidadMedidaCombobox: React.FC<UnidadMedidaComboboxProps> = ({
  value,
  factor = 1,
  onChange,
  className,
  disabled = false,
}) => {
  const { t } = useTranslation(["factura_import"]);
  const [isOpen, setIsOpen] = useState(false);
  const [customFactor, setCustomFactor] = useState<number>(factor);

  const selectedUnit = COMMON_MEASUREMENT_UNITS.find(
    (u) => u.id === value.toLowerCase() || u.symbol.toLowerCase() === value.toLowerCase()
  ) || {
    id: value || "un",
    label: value || "Unidad",
    symbol: value || "un",
    defaultFactor: 1,
  };

  const handleSelectUnit = (unit: MeasurementUnit) => {
    setIsOpen(false);
    const newFactor = unit.defaultFactor;
    setCustomFactor(newFactor);
    onChange(unit.symbol, newFactor);
  };

  const handleFactorChange = (newFactor: number) => {
    setCustomFactor(newFactor);
    onChange(selectedUnit.symbol, newFactor);
  };

  return (
    <div className={cn("relative flex items-center gap-1.5", className)} data-testid="unidad-medida-combobox">
      {/* Unit Selector Trigger */}
      <div className="relative">
        <button
          type="button"
          disabled={disabled}
          onClick={() => setIsOpen(!isOpen)}
          data-testid="unidad-combobox-trigger"
          className="touch-target inline-flex min-h-[38px] px-2.5 items-center justify-between gap-1.5 rounded-lg border border-input bg-background text-xs font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer disabled:opacity-50"
        >
          <Scale className="h-3.5 w-3.5 text-primary shrink-0" />
          <span className="truncate max-w-[80px]">{selectedUnit.symbol}</span>
          <ChevronDown className="h-3 w-3 opacity-60" />
        </button>

        {isOpen && (
          <div
            data-testid="unidad-combobox-dropdown"
            className="absolute left-0 top-full mt-1 z-50 w-44 rounded-xl border border-border bg-card p-1 shadow-xl max-h-48 overflow-y-auto custom-scrollbar"
          >
            {COMMON_MEASUREMENT_UNITS.map((u) => {
              const isSelected = u.symbol.toLowerCase() === selectedUnit.symbol.toLowerCase();
              return (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => handleSelectUnit(u)}
                  data-testid={`unit-opt-${u.id}`}
                  className={cn(
                    "w-full text-left flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors",
                    isSelected
                      ? "bg-primary text-primary-foreground font-bold"
                      : "hover:bg-secondary text-foreground"
                  )}
                >
                  <span>
                    {t(`units.labels.${u.id}`, u.label)} ({u.symbol})
                  </span>
                  {isSelected && <Check className="h-3.5 w-3.5" />}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Factor multiplier input (e.g., 1 caja = 12 unidades) */}
      {(selectedUnit.id === "caja" || selectedUnit.id === "pack" || selectedUnit.id === "saco") && (
        <div className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground shrink-0">
          <span>x</span>
          <input
            type="number"
            min="1"
            step="any"
            value={customFactor}
            onChange={(e) => handleFactorChange(Number(e.target.value) || 1)}
            data-testid="input-unit-factor"
            title={t("units.factor_tooltip", "Factor de conversión a unidad base")}
            className="w-14 h-9 px-1.5 rounded-lg bg-background border border-input text-xs font-mono font-bold text-center text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      )}
    </div>
  );
};
