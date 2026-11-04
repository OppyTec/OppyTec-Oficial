/**
 * oppytec-frontend/src/features/invoices/components/FacturaSupplierBanner.tsx
 * Banner de Proveedor y Encabezado del Documento con ADN Visual Legacy.
 */

import { useTranslation } from "react-i18next";
import { Building2, UserPlus, CheckCircle2, AlertCircle } from "lucide-react";
import { formatMoney } from "@/shared/lib";
import { InvoiceStatusBadge } from "./InvoiceStatusBadge";
import { ConfidenceBadge } from "./ConfidenceBadge";
import type { Invoice } from "../types";

export interface FacturaSupplierBannerProps {
  invoice: Invoice;
  onLinkSupplier?: () => void;
}

export function FacturaSupplierBanner({ invoice, onLinkSupplier }: FacturaSupplierBannerProps) {
  const { t } = useTranslation(["invoices"]);
  const isRegistered = !invoice.audit_flags?.some((f) => f.code === "UNKNOWN_SUPPLIER");

  const dteLabelMap: Record<string, string> = {
    FACTURA_ELECTRONICA_33: t("invoices:dte.factura_electronica_33", "Factura Electrónica (DTE 33)"),
    FACTURA_EXENTA_34: t("invoices:dte.factura_exenta_34", "Factura Exenta (DTE 34)"),
    GUIA_DESPACHO_52: t("invoices:dte.guia_despacho_52", "Guía de Despacho (DTE 52)"),
    BOLETA_ELECTRONICA_39: t("invoices:dte.boleta_electronica_39", "Boleta Electrónica (DTE 39)"),
    NOTA_CREDITO_61: t("invoices:dte.nota_credito_61", "Nota de Crédito (DTE 61)"),
    NOTA_DEBITO_56: t("invoices:dte.nota_debito_56", "Nota de Débito (DTE 56)"),
  };

  return (
    <div
      data-testid="factura-supplier-banner"
      className="glass-card rounded-2xl border border-border p-5 shadow-sm space-y-4"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Información del Proveedor */}
        <div className="flex items-start gap-3.5">
          <div className="h-11 w-11 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
            <Building2 className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-bold text-foreground">
                {invoice.vendor_name || t("invoices:supplier_banner.unknown_vendor", "Proveedor sin Razón Social detectada")}
              </h2>
              {isRegistered ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  <CheckCircle2 className="h-3 w-3" />
                  {t("invoices:supplier_banner.registered", "Registrado en Catálogo")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                  <AlertCircle className="h-3 w-3" />
                  {t("invoices:supplier_banner.new_vendor", "Nuevo Proveedor")}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
              <span>
                <strong>{t("invoices:supplier_banner.rut_label", "RUT:")}</strong> {invoice.vendor_tax_id || t("invoices:supplier_banner.not_detected", "No detectado")}
              </span>
              {invoice.vendor_fiscal_address && (
                <span className="truncate max-w-xs" title={invoice.vendor_fiscal_address}>
                  • {invoice.vendor_fiscal_address}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Badges de Estado y Confianza */}
        <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
          <InvoiceStatusBadge status={invoice.status} />
          <ConfidenceBadge score={invoice.confidence_score} />
          {!isRegistered && onLinkSupplier && (
            <button
              type="button"
              onClick={onLinkSupplier}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-primary/15 text-primary hover:bg-primary/25 border border-primary/30 transition-colors"
            >
              <UserPlus className="h-3.5 w-3.5" />
              {t("invoices:supplier_banner.quick_add_supplier", "Alta Rápida Proveedor")}
            </button>
          )}
        </div>
      </div>

      {/* Franja de Datos Clave DTE */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-3 border-t border-border/60 text-xs">
        <div>
          <span className="text-muted-foreground block text-[11px]">{t("invoices:supplier_banner.dte_type_label", "Tipo DTE")}</span>
          <span className="font-semibold text-foreground truncate block">
            {dteLabelMap[invoice.dte_type] || invoice.dte_type}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">{t("invoices:supplier_banner.folio_label", "Folio Documento")}</span>
          <span className="font-bold font-mono text-foreground">
            #{invoice.invoice_number || "S/F"}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">{t("invoices:supplier_banner.issue_date_label", "Fecha Emisión")}</span>
          <span className="font-medium text-foreground">
            {invoice.invoice_date || "—"}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">{t("invoices:supplier_banner.net_amount_label", "Monto Neto")}</span>
          <span className="font-medium text-foreground">
            {formatMoney(invoice.net_amount, (invoice.currency as any) || "CLP")}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">{t("invoices:supplier_banner.tax_amount_label", "IVA (19%)")}</span>
          <span className="font-medium text-muted-foreground">
            {formatMoney(invoice.tax_amount, (invoice.currency as any) || "CLP")}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">{t("invoices:supplier_banner.total_amount_label", "Total Factura")}</span>
          <span className="font-extrabold text-foreground text-sm font-mono text-emerald-600 dark:text-emerald-400">
            {formatMoney(invoice.total_amount, (invoice.currency as any) || "CLP")}
          </span>
        </div>
      </div>
    </div>
  );
}
