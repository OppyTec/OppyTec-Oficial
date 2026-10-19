import { Building2 } from "lucide-react";
import { setHttpRequestContext } from "@/shared/api/httpClient";
import { translateKey } from "@/shared/i18n";

export interface TenantOption {
  readonly holdingId: string;
  readonly holdingName: string;
  readonly tenantId: string;
  readonly tenantName: string;
  readonly rut: string;
}

export const OFFICIAL_TENANT_OPTIONS: readonly TenantOption[] = [
  {
    holdingId: "holding-gastro-sur",
    holdingName: "Holding Gastronómico Sur SpA",
    tenantId: "tenant_rest_central",
    tenantName: "Restaurante Central Santiago",
    rut: "76.543.210-K",
  },
  {
    holdingId: "holding-gastro-sur",
    holdingName: "Holding Gastronómico Sur SpA",
    tenantId: "tenant_hotel_costanera",
    tenantName: "Hotel & Buffet Costanera",
    rut: "76.889.112-4",
  },
  {
    holdingId: "holding-pacifico-food",
    holdingName: "Pacífico Food Service S.A.",
    tenantId: "tenant_dark_kitchen_norte",
    tenantName: "Comisariato & Dark Kitchen Norte",
    rut: "77.120.990-1",
  },
] as const;

export interface HoldingTenantSwitcherProps {
  readonly activeTenantId: string;
  readonly onSelectTenant: (option: TenantOption) => void;
}

export function HoldingTenantSwitcher({
  activeTenantId,
  onSelectTenant,
}: HoldingTenantSwitcherProps) {
  const current =
    OFFICIAL_TENANT_OPTIONS.find((t) => t.tenantId === activeTenantId) ??
    OFFICIAL_TENANT_OPTIONS[0];

  const handleChange = (nextTenantId: string): void => {
    const found = OFFICIAL_TENANT_OPTIONS.find(
      (item) => item.tenantId === nextTenantId
    );
    if (!found) {
      return;
    }
    setHttpRequestContext({
      holdingId: found.holdingId,
      tenantId: found.tenantId,
    });
    onSelectTenant(found);
  };

  return (
    <div
      data-testid="holding-tenant-switcher"
      className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary/50 px-2.5 py-1.5"
    >
      <Building2 className="h-4 w-4 text-primary" aria-hidden="true" />
      <select
        aria-label={translateKey("auth", "session.tenant_switch", {
          tenant: current?.tenantName ?? activeTenantId,
        })}
        data-testid="holding-tenant-select"
        value={activeTenantId}
        onChange={(e) => handleChange(e.target.value)}
        className="touch-target min-h-[44px] rounded-md bg-transparent font-mono text-xs font-semibold text-foreground focus:outline-none"
      >
        {OFFICIAL_TENANT_OPTIONS.map((opt) => (
          <option key={opt.tenantId} value={opt.tenantId}>
            {`${opt.holdingName} — ${opt.tenantName} (${opt.rut})`}
          </option>
        ))}
      </select>
    </div>
  );
}
