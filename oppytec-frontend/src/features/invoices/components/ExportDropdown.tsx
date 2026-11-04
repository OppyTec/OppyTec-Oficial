/**
 * oppytec-frontend/src/features/invoices/components/ExportDropdown.tsx
 * Menú desplegable para exportar facturas a SII Chile y ERPs internacionales.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Download, ChevronDown, FileSpreadsheet, Building, FileText } from "lucide-react";
import { cn } from "@/shared/lib";
import type { ExportFormat } from "../types";

export interface ExportDropdownProps {
  onExport: (format: ExportFormat) => void;
  isExporting: boolean;
  className?: string;
  disabled?: boolean;
}

export function ExportDropdown({
  onExport,
  isExporting,
  className,
  disabled = false,
}: ExportDropdownProps) {
  const { t } = useTranslation(["invoices"]);
  const [open, setOpen] = useState(false);

  const options: Array<{ format: ExportFormat; label: string; desc: string; icon: any }> = [
    {
      format: "sii_compras",
      label: t("invoices:export.sii_compras_label", "SII Registro de Compras"),
      desc: t("invoices:export.sii_compras_desc", "Formato oficial CSV (punto y coma) para SII Chile"),
      icon: Building,
    },
    {
      format: "sii_ventas",
      label: t("invoices:export.sii_ventas_label", "SII Registro de Ventas"),
      desc: t("invoices:export.sii_ventas_desc", "Formato oficial CSV para SII Chile"),
      icon: Building,
    },
    {
      format: "excel",
      label: t("invoices:export.excel_label", "Excel (.xlsx)"),
      desc: t("invoices:export.excel_desc", "Planilla de cálculo con fórmulas y detalle de líneas"),
      icon: FileSpreadsheet,
    },
    {
      format: "csv",
      label: t("invoices:export.csv_label", "CSV Estándar"),
      desc: t("invoices:export.csv_desc", "Archivo separado por comas UTF-8"),
      icon: FileText,
    },
    {
      format: "quickbooks",
      label: t("invoices:export.quickbooks_label", "QuickBooks Bills"),
      desc: t("invoices:export.quickbooks_desc", "Mapeo para importador de gastos QuickBooks"),
      icon: FileText,
    },
    {
      format: "xero",
      label: t("invoices:export.xero_label", "Xero Invoices"),
      desc: t("invoices:export.xero_desc", "Formato compatible con Xero Accounting"),
      icon: FileText,
    },
    {
      format: "odoo",
      label: t("invoices:export.odoo_label", "Odoo ERP"),
      desc: t("invoices:export.odoo_desc", "Estructura contable para Odoo Account Move"),
      icon: FileText,
    },
  ];

  return (
    <div className={cn("relative inline-block", className)}>
      <button
        type="button"
        disabled={disabled || isExporting}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl border border-border bg-background hover:bg-muted/60 transition-colors shadow-sm disabled:opacity-50"
        )}
      >
        <Download className="h-4 w-4 text-primary" />
        <span>{isExporting ? t("invoices:export.exporting", "Exportando...") : t("invoices:export.export_invoices", "Exportar Facturas")}</span>
        <ChevronDown className="h-3.5 w-3.5 opacity-60" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1.5 w-72 rounded-2xl border border-border bg-popover p-1.5 shadow-xl z-50 animate-in fade-in-0 zoom-in-95">
            <div className="px-2 py-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border/60 mb-1">
              {t("invoices:export.select_format", "Seleccionar Formato de Exportación")}
            </div>
            <div className="space-y-0.5">
              {options.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.format}
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      onExport(opt.format);
                    }}
                    className="w-full flex items-start gap-2.5 p-2 rounded-xl hover:bg-muted transition-colors text-left group"
                  >
                    <Icon className="h-4 w-4 text-primary shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-foreground">{opt.label}</div>
                      <div className="text-[10px] text-muted-foreground leading-tight">
                        {opt.desc}
                      </div>
                    </div>
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
