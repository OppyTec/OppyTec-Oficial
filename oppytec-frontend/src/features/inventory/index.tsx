import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Can } from "@/shared/auth/Can";
import { NumericInput } from "@/shared/components/ui/NumericInput";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

export * from "./types";
export * from "./hooks";
export * from "./mockData";
export * from "./stock/StockRegistroPage";
export * from "./stock/components";
export * from "./conteo";
export * from "./recuentos";

const INVENTORY_TABS = [
  "StockRegistro",
  "ContarInventario",
  "RecuentoInventario",
  "GestionarMerma",
] as const;

export type InventorySubTab = (typeof INVENTORY_TABS)[number];

export type UnifiedRecuentoSubView = "conteo-activo" | "historial-recuentos";

const DAYS_MAP = [
  { key: "mon", label: "Lun" },
  { key: "tue", label: "Mar" },
  { key: "wed", label: "Mié" },
  { key: "thu", label: "Jue" },
  { key: "fri", label: "Vie" },
  { key: "sat", label: "Sáb" },
  { key: "sun", label: "Dom" },
] as const;

export function InventoryFeatureView() {
  const { t } = useTranslation("inventory");
  const [activeTab, setActiveTab] = useState<InventorySubTab>("StockRegistro");
  const [unifiedRecuentoTab, setUnifiedRecuentoTab] =
    useState<UnifiedRecuentoSubView>("conteo-activo");
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
              {t("view.active_mode", { tab: activeTab, defaultValue: `Modo Activo: ${activeTab}` })}
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
            <span>{t("view.valuation_fefo", "Valorización Lote FEFO (PMP):")}</span>
            <MoneyBadge amount="185400" baseCurrency="CLP" />
          </div>

          {/* Vista Unificada de Recuento (Plan Básico: Conteo Físico Activo + Historial de Recuentos en 1 sola vista) */}
          <div
            data-testid="inventory-unified-recuento-card"
            className="mt-2 space-y-2 rounded-lg border border-primary/30 bg-card p-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-[11px] font-bold uppercase text-primary">
                {t("view.unified_card_title", "Módulo Recuento Unificado (Plan Básico)")}
              </span>
              <div className="flex gap-1">
                <button
                  type="button"
                  data-testid="recuento-subtab-activo"
                  onClick={() => {
                    setUnifiedRecuentoTab("conteo-activo");
                    setActiveTab("ContarInventario");
                  }}
                  className={`touch-target inline-flex min-h-[44px] items-center rounded-md px-2.5 py-1 text-[11px] font-semibold ${
                    unifiedRecuentoTab === "conteo-activo"
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  {t("view.tab1_active", "Tab 1: Recuento Físico Activo")}
                </button>
                <button
                  type="button"
                  data-testid="recuento-subtab-historial"
                  onClick={() => {
                    setUnifiedRecuentoTab("historial-recuentos");
                    setActiveTab("RecuentoInventario");
                  }}
                  className={`touch-target inline-flex min-h-[44px] items-center rounded-md px-2.5 py-1 text-[11px] font-semibold ${
                    unifiedRecuentoTab === "historial-recuentos"
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  {t("view.tab2_history", "Tab 2: Historial de Recuentos")}
                </button>
              </div>
            </div>
            <p
              data-testid="recuento-unified-status"
              className="font-mono text-xs text-muted-foreground"
            >
              {unifiedRecuentoTab === "conteo-activo"
                ? t("view.status_active", { qty: blindCountQty, defaultValue: `Conteo Físico Ciego Activo · Stock Capturado: ${blindCountQty} kg` })
                : t("view.status_history", "Historial de Recuentos Cerrados · Sesión #REC-2026-10 (Varianza: -0.50 kg auditada)")}
            </p>
          </div>
        </div>

        {/* Mapa de Calor 7x24 de Mermas & Aprobación por Umbral */}
        <div
          data-testid="inventory-merma-heatmap"
          className="space-y-3 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-muted-foreground">
              {t("view.merma_heatmap_title", "Mapa de Calor 7x24 Mermas & Umbral JEV")}
            </h3>
            <Can perform="inventory.mermas.approve">
              <button
                type="button"
                data-testid="inventory-approve-merma-btn"
                onClick={() => setMermaApproved(true)}
                className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground"
              >
                {mermaApproved ? t("view.merma_approved", "Merma Aprobada") : t("view.approve_merma_threshold", "Aprobar Merma > Umbral")}
              </button>
            </Can>
          </div>
          <p className="text-xs text-muted-foreground">
            {translateKey("inventory", "movements.waste", {
              reason: t("view.cold_chain_loss_reason", "Corte de cadena de frío turno noche (7 días x 24 horas)"),
            })}
          </p>
          <div className="grid grid-cols-7 gap-1 font-mono text-[10px]">
            {DAYS_MAP.map((day) => (
              <div
                key={day.key}
                className="rounded border border-border bg-card p-1.5 text-center"
              >
                <div className="font-bold">{t(`view.days.${day.key}`, day.label)}</div>
                <div className="text-primary">{t("view.ok_24h", "24h OK")}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
