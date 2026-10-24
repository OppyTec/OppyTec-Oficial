import { useState } from "react";
import { ChevronDown, Layers } from "lucide-react";
import * as LucideIcons from "lucide-react";
import { cn } from "@/shared/lib";

export interface AreaOperativa {
  readonly id: string;
  readonly nombre: string;
  readonly icono?: string;
  readonly bodegas_ids?: string[];
}

export const OFFICIAL_AREAS: readonly AreaOperativa[] = [
  { id: "all", nombre: "Todas las Áreas", icono: "Layers" },
  { id: "cocina-caliente", nombre: "Cocina Caliente", icono: "Flame" },
  { id: "barra-salon", nombre: "Barra & Salón", icono: "Wine" },
  { id: "pasteleria", nombre: "Pastelería & Postres", icono: "Cake" },
  { id: "bodega-central", nombre: "Bodega Central", icono: "Warehouse" },
];

export interface AreaSelectorProps {
  readonly className?: string;
  readonly buttonClassName?: string;
  readonly allowAll?: boolean;
  readonly selectedAreaId?: string;
  readonly onSelectArea?: (areaId: string) => void;
}

export function AreaSelector({
  className,
  buttonClassName,
  allowAll = true,
  selectedAreaId: propSelectedAreaId,
  onSelectArea,
}: AreaSelectorProps) {
  const [internalSelectedId, setInternalSelectedId] = useState<string>("all");
  const [open, setOpen] = useState(false);

  const selectedAreaId = propSelectedAreaId ?? internalSelectedId;

  const handleSelect = (id: string) => {
    setInternalSelectedId(id);
    onSelectArea?.(id);
    setOpen(false);
  };

  const getAreaIcon = (iconName?: string) => {
    if (iconName && (LucideIcons as Record<string, any>)[iconName]) {
      return (LucideIcons as Record<string, any>)[iconName];
    }
    return Layers;
  };

  const isAllSelected = allowAll && (selectedAreaId === "all" || !selectedAreaId);
  const currentArea = OFFICIAL_AREAS.find((a) => a.id === selectedAreaId);
  const SelectedIcon = isAllSelected ? Layers : getAreaIcon(currentArea?.icono);
  const selectedLabel = isAllSelected ? "Todas las Áreas" : (currentArea?.nombre ?? "Área Operativa");

  return (
    <div className={cn("relative inline-block", className)} data-testid="area-selector">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "flex items-center gap-2 rounded-2xl border text-[10px] font-black uppercase tracking-widest transition-all hover:bg-secondary/80 h-8 min-h-[32px] px-3 bg-card text-foreground cursor-pointer select-none border-border shadow-sm",
          buttonClassName
        )}
      >
        <SelectedIcon className="h-3.5 w-3.5 text-primary shrink-0" />
        <span className="truncate max-w-[140px]">{selectedLabel}</span>
        <ChevronDown className={cn("h-3 w-3 opacity-50 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className="absolute left-0 top-full mt-1.5 w-64 rounded-2xl p-2 shadow-2xl z-50 bg-card border border-border"
          >
            {allowAll && (
              <button
                type="button"
                onClick={() => handleSelect("all")}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors mb-1 cursor-pointer",
                  isAllSelected
                    ? "bg-primary/15 text-primary font-black"
                    : "hover:bg-secondary text-foreground"
                )}
              >
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Layers size={12} strokeWidth={2.5} />
                </div>
                <span className="flex-1 text-left truncate">Todas las Áreas</span>
                {isAllSelected && <div className="h-1.5 w-1.5 rounded-full bg-primary" />}
              </button>
            )}

            <div className="max-h-52 overflow-y-auto space-y-0.5 custom-scrollbar">
              {OFFICIAL_AREAS.filter((a) => a.id !== "all").map((area) => {
                const AreaIcon = getAreaIcon(area.icono);
                const isSelected = selectedAreaId === area.id;
                return (
                  <button
                    key={area.id}
                    type="button"
                    onClick={() => handleSelect(area.id)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors text-left cursor-pointer",
                      isSelected
                        ? "bg-primary/15 text-primary font-black"
                        : "hover:bg-secondary text-foreground"
                    )}
                  >
                    <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                      <AreaIcon size={12} strokeWidth={2.5} />
                    </div>
                    <span className="flex-1 truncate">{area.nombre}</span>
                    {isSelected && <div className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />}
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

export default AreaSelector;
