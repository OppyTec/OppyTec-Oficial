import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

const PROCUREMENT_SECTIONS = ["Compras", "Proveedores", "Facturas"] as const;
export type ProcurementSection = (typeof PROCUREMENT_SECTIONS)[number];

export function ProcurementFeatureView() {
  const [section, setSection] = useState<ProcurementSection>("Facturas");
  const [ocrVerified, setOcrVerified] = useState<boolean>(false);

  return (
    <section
      data-testid="feature-procurement"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("procurement", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("procurement", "purchase_order.number", {
              poNumber: "OC-2026-0842",
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {PROCUREMENT_SECTIONS.map((sec) => (
            <button
              key={sec}
              type="button"
              data-testid={`procurement-tab-${sec}`}
              onClick={() => setSection(sec)}
              className={`touch-target inline-flex min-h-[44px] items-center rounded-lg px-3 py-1.5 text-xs font-semibold ${
                section === sec
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {sec}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid={`procurement-panel-${section}`}
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            {`${section} · ${translateKey("procurement", "purchase_order.supplier", {
              supplierName: "Distribuidora Austral Food SpA (76.321.400-8)",
            })}`}
          </h3>
          <p className="text-xs text-foreground">
            {translateKey("procurement", "purchase_order.status_approved", {
              approver: "gerencia.compras@oppytec.cl",
            })}
          </p>
          <div className="flex items-center justify-between border-t border-border pt-2 text-xs">
            <span>
              {translateKey("procurement", "purchase_order.total_amount", {
                amount: "1.450.000 CLP",
              })}
            </span>
            <MoneyBadge amount="1450000" baseCurrency="CLP" />
          </div>
        </div>

        <div
          data-testid="procurement-ocr-dte"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-muted-foreground">
              {translateKey("procurement", "dte.reception_title")}
            </h3>
            <Can perform="procurement.invoices.ocr">
              <button
                type="button"
                data-testid="procurement-ocr-btn"
                onClick={() => setOcrVerified(true)}
                className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground"
              >
                {ocrVerified ? "3-Way Match OK" : "Ejecutar AI OCR DTE"}
              </button>
            </Can>
          </div>
          <p className="rounded-lg border border-warning/40 bg-warning/10 p-2 text-xs text-foreground">
            {translateKey("procurement", "dte.price_variance_alert", {
              variancePct: "4.2",
              item: "Pollo King",
            })}
          </p>
        </div>
      </div>
    </section>
  );
}
