import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { NumericInput } from "@/shared/components/ui/NumericInput";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

const INVENTORY_TABS = [
  "StockRegistro",
  "ContarInventario",
  "RecuentoInventario",
  "GestionarMerma",
] as const;

export type InventorySubTab = (typeof INVENTORY_TABS)[number];

export function InventoryFeatureView() {
  const [activeTab, setActiveTab] = useState<InventorySubTab>("StockRegistro");
  const [blindCountQty, setBlindCountQty] = useState<string>("24.50");
  const [mermaApproved, setMermaApproved] = useState<boolean>(false);

  return (
    <section
      data-testid="feature-inventory"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("inventory", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("inventory", "warehouse.stock_level", {
              quantity: blindCountQty,
              unit: "kg",
            })}
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {INVENTORY_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              data-testid={`inventory-tab-${tab}`}
              onClick={() => setActiveTab(tab)}
              className={`touch-target inline-flex min-h-[44px] items-center rounded-lg px-3 py-1.5 text-xs font-semibold ${
                activeTab === tab
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid={`inventory-panel-${activeTab}`}
          className="space-y-3 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-primary">
              {`Modo Activo: ${activeTab}`}
            </span>
            <span className="animate-blink-critical rounded-md border border-destructive px-2 py-0.5 text-[11px] font-bold text-destructive">
              {translateKey("inventory", "warehouse.critical_alert", {
                item: "Pollo King",
                minStock: 15,
              })}
            </span>
          </div>

          <NumericInput
            label={translateKey("operations", "counts.blind_inventory")}
            value={blindCountQty}
            onChange={setBlindCountQty}
            step="0.50"
            unitLabel="kg"
            testId="inventory-blind-count-input"
          />

          <div className="flex items-center justify-between border-t border-border pt-2 text-xs">
            <span>Valorización Lote FEFO (PMP):</span>
            <MoneyBadge amount="185400" baseCurrency="CLP" />
          </div>
        </div>

        {/* Mapa de Calor 7x24 de Mermas & Aprobación por Umbral */}
        <div
          data-testid="inventory-merma-heatmap"
          className="space-y-3 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-muted-foreground">
              Mapa de Calor 7x24 Mermas & Umbral JEV
            </h3>
            <Can perform="inventory.mermas.approve">
              <button
                type="button"
                data-testid="inventory-approve-merma-btn"
                onClick={() => setMermaApproved(true)}
                className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground"
              >
                {mermaApproved ? "Merma Aprobada" : "Aprobar Merma > Umbral"}
              </button>
            </Can>
          </div>
          <p className="text-xs text-muted-foreground">
            {translateKey("inventory", "movements.waste", {
              reason: "Corte de cadena de frío turno noche (7 días x 24 horas)",
            })}
          </p>
          <div className="grid grid-cols-7 gap-1 font-mono text-[10px]">
            {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map((day) => (
              <div
                key={day}
                className="rounded border border-border bg-card p-1.5 text-center"
              >
                <div className="font-bold">{day}</div>
                <div className="text-primary">24h OK</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
