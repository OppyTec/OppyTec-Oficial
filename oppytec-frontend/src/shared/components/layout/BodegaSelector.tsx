import { Warehouse } from "lucide-react";
import { setHttpRequestContext } from "@/shared/api/httpClient";
import { translateKey } from "@/shared/i18n";

export interface WarehouseOption {
  readonly id: string;
  readonly label: string;
}

export const OFFICIAL_WAREHOUSES: readonly WarehouseOption[] = [
  { id: "bod-cocina-central", label: "Bodega Cocina Central" },
  { id: "bod-camara-fria", label: "Cámara Fría -18°C" },
  { id: "bod-barra-cava", label: "Barra & Cava" },
] as const;

export interface BodegaSelectorProps {
  readonly activeWarehouseId: string;
  readonly onSelectWarehouse: (warehouseId: string) => void;
}

export function BodegaSelector({
  activeWarehouseId,
  onSelectWarehouse,
}: BodegaSelectorProps) {
  const handleSelect = (warehouseId: string): void => {
    setHttpRequestContext({ warehouseId });
    onSelectWarehouse(warehouseId);
  };

  return (
    <div
      data-testid="bodega-selector"
      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1"
    >
      <Warehouse className="h-4 w-4 text-primary" aria-hidden="true" />
      <select
        aria-label={translateKey("inventory", "warehouse.select", {
          warehouse: activeWarehouseId,
        })}
        data-testid="bodega-select"
        value={activeWarehouseId}
        onChange={(e) => handleSelect(e.target.value)}
        className="touch-target min-h-[44px] rounded bg-transparent text-xs font-semibold text-foreground focus:outline-none"
      >
        {OFFICIAL_WAREHOUSES.map((wh) => (
          <option key={wh.id} value={wh.id}>
            {wh.label}
          </option>
        ))}
      </select>
    </div>
  );
}
