/**
 * oppytec-frontend/src/features/invoices/components/UnidadMedidaCombobox.tsx
 * Selector rápido y searchable de unidades de inventario canónicas de cocina.
 */

import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/shared/lib";

export const GASTRONOMIC_UNIT_KEYS = [
  { value: "kg", key: "kg", defaultLabel: "Kilogramos (kg)" },
  { value: "g", key: "g", defaultLabel: "Gramos (g)" },
  { value: "L", key: "L", defaultLabel: "Litros (L)" },
  { value: "ml", key: "ml", defaultLabel: "Mililitros (ml)" },
  { value: "unidad", key: "unidad", defaultLabel: "Unidades (un)" },
  { value: "docena", key: "docena", defaultLabel: "Docena (12 un)" },
  { value: "porcion", key: "porcion", defaultLabel: "Porción" },
  { value: "atado", key: "atado", defaultLabel: "Atado / Paquete" },
  { value: "botella", key: "botella", defaultLabel: "Botella" },
  { value: "lata", key: "lata", defaultLabel: "Lata" },
];

export interface UnidadMedidaComboboxProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  disabled?: boolean;
}

export function UnidadMedidaCombobox({
  value,
  onChange,
  className,
  disabled = false,
}: UnidadMedidaComboboxProps) {
  const { t } = useTranslation(["invoices"]);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const gastronomicUnits = useMemo(() => {
    return GASTRONOMIC_UNIT_KEYS.map((u) => ({
      value: u.value,
      label: t(`invoices:combobox.units.${u.key}`, u.defaultLabel),
    }));
  }, [t]);

  const filtered = gastronomicUnits.filter(
    (u) =>
      u.label.toLowerCase().includes(search.toLowerCase()) ||
      u.value.toLowerCase().includes(search.toLowerCase())
  );

  const currentLabel =
    gastronomicUnits.find((u) => u.value.toLowerCase() === value.toLowerCase())?.label ||
    value ||
    t("invoices:combobox.default_unit", "Unidad");

  return (
    <div className={cn("relative inline-block w-full", className)}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "w-full flex items-center justify-between px-2.5 py-1.5 text-xs font-medium rounded-xl border border-border bg-background hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <span className="truncate">{currentLabel}</span>
        <ChevronDown className="h-3.5 w-3.5 opacity-60 shrink-0 ml-1" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => {
              setOpen(false);
              setSearch("");
            }}
          />
          <div className="absolute left-0 top-full mt-1 w-48 rounded-xl border border-border bg-popover p-1 shadow-xl z-50 animate-in fade-in-0 zoom-in-95">
            <input
              type="text"
              placeholder={t("invoices:combobox.search_unit", "Buscar unidad...")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-2 py-1 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary mb-1"
              autoFocus
            />
            <div className="max-h-44 overflow-y-auto space-y-0.5">
              {filtered.map((u) => {
                const isSelected = u.value.toLowerCase() === value.toLowerCase();
                return (
                  <button
                    key={u.value}
                    type="button"
                    onClick={() => {
                      onChange(u.value);
                      setOpen(false);
                      setSearch("");
                    }}
                    className={cn(
                      "w-full flex items-center justify-between px-2 py-1.5 text-xs rounded-lg transition-colors text-left",
                      isSelected
                        ? "bg-primary/10 text-primary font-semibold"
                        : "hover:bg-muted text-foreground"
                    )}
                  >
                    <span className="truncate">{u.label}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
