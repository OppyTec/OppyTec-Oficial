/**
 * oppytec-frontend/src/features/invoices/components/InvoiceTable.tsx
 * Grilla interactiva de facturas electrónicas con selección múltiple y ADN Visual Legacy.
 * Mobile-First, touch targets >= 44px y badges semafóricos.
 */

import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  FileText,
  Play,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { formatMoney, cn } from "@/shared/lib";
import { InvoiceStatusBadge } from "./InvoiceStatusBadge";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { AuditFlagsBadge } from "./AuditFlagsBadge";
import type { Invoice } from "../types";

export interface InvoiceTableProps {
  invoices: Invoice[];
  isLoading: boolean;
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onReprocess: (id: string) => void;
  onDelete: (id: string) => void;
}

export function InvoiceTable({
  invoices,
  isLoading,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onReprocess,
  onDelete,
}: InvoiceTableProps) {
  const { t } = useTranslation(["invoices"]);
  const navigate = useNavigate();

  const isAllSelected = invoices.length > 0 && selectedIds.length === invoices.length;

  if (isLoading) {
    return (
      <div className="glass-card rounded-2xl border border-border p-6 shadow-sm">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-1/4 rounded bg-muted" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-14 w-full rounded-xl bg-muted/60" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (invoices.length === 0) {
    return (
      <div
        data-testid="invoices-table-empty"
        className="glass-card flex min-h-[300px] flex-col items-center justify-center rounded-2xl border border-dashed border-border p-8 text-center"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <FileText className="h-7 w-7" />
        </div>
        <h4 className="mt-4 text-base font-bold text-foreground">
          {t("invoices:table.empty_title", "No se encontraron facturas")}
        </h4>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          {t(
            "invoices:table.empty_desc",
            "No hay documentos que coincidan con los filtros aplicados o aún no has cargado facturas electrónicas."
          )}
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="invoices-table"
      className="glass-card rounded-2xl border border-border shadow-sm overflow-hidden"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-muted/60 border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground select-none">
            <tr>
              <th className="py-3 px-3 w-10 text-center">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  onChange={onToggleSelectAll}
                  aria-label={t("invoices:table.select_all", "Seleccionar todas las facturas")}
                  className="h-4 w-4 rounded text-primary focus:ring-primary border-border cursor-pointer"
                />
              </th>
              <th className="py-3 px-3">{t("invoices:table.col_folio_dte", "Folio / Tipo DTE")}</th>
              <th className="py-3 px-3">{t("invoices:table.col_supplier", "Proveedor / Emisor")}</th>
              <th className="py-3 px-3">{t("invoices:table.col_date", "Fecha Emisión")}</th>
              <th className="py-3 px-3 text-right">{t("invoices:table.col_net", "Neto")}</th>
              <th className="py-3 px-3 text-right">{t("invoices:table.col_tax", "IVA")}</th>
              <th className="py-3 px-3 text-right">{t("invoices:table.col_total", "Total")}</th>
              <th className="py-3 px-3 text-center">{t("invoices:table.col_confidence", "Confianza IA")}</th>
              <th className="py-3 px-3 text-center">{t("invoices:table.col_status", "Estado")}</th>
              <th className="py-3 px-3 text-center">{t("invoices:table.col_audit", "Auditoría")}</th>
              <th className="py-3 px-3 text-right">{t("invoices:table.col_actions", "Acciones")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {invoices.map((inv) => {
              const isSelected = selectedIds.includes(inv.id);

              return (
                <tr
                  key={inv.id}
                  className={cn(
                    "hover:bg-muted/40 transition-colors cursor-pointer group",
                    isSelected && "bg-primary/5"
                  )}
                  onClick={() => navigate(`/contabilidad/facturas/${inv.id}`)}
                >
                  {/* Checkbox */}
                  <td
                    className="py-3.5 px-3 text-center"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleSelect(inv.id);
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(inv.id)}
                      className="h-4 w-4 rounded text-primary focus:ring-primary border-border cursor-pointer"
                    />
                  </td>

                  {/* Folio / Tipo DTE */}
                  <td className="py-3.5 px-3">
                    <div className="font-bold text-foreground text-sm font-mono">
                      #{inv.invoice_number || "S/F"}
                    </div>
                    <span className="text-[10px] text-muted-foreground block truncate max-w-[140px]">
                      {inv.dte_type.replace(/_/g, " ")}
                    </span>
                  </td>

                  {/* Proveedor */}
                  <td className="py-3.5 px-3">
                    <div className="font-semibold text-foreground truncate max-w-[200px]">
                      {inv.vendor_name || t("invoices:table.supplier_not_detected", "Proveedor no detectado")}
                    </div>
                    <span className="text-[10px] text-muted-foreground font-mono block">
                      RUT: {inv.vendor_tax_id || "—"}
                    </span>
                  </td>

                  {/* Fecha */}
                  <td className="py-3.5 px-3 text-muted-foreground whitespace-nowrap">
                    {inv.invoice_date || "—"}
                  </td>

                  {/* Neto */}
                  <td className="py-3.5 px-3 text-right font-mono font-medium text-foreground">
                    {formatMoney(inv.net_amount, (inv.currency as any) || "CLP")}
                  </td>

                  {/* IVA */}
                  <td className="py-3.5 px-3 text-right font-mono text-muted-foreground">
                    {formatMoney(inv.tax_amount, (inv.currency as any) || "CLP")}
                  </td>

                  {/* Total */}
                  <td className="py-3.5 px-3 text-right font-mono font-extrabold text-foreground text-sm">
                    {formatMoney(inv.total_amount, (inv.currency as any) || "CLP")}
                  </td>

                  {/* Confianza */}
                  <td className="py-3.5 px-3 text-center">
                    <ConfidenceBadge score={inv.confidence_score} />
                  </td>

                  {/* Estado */}
                  <td className="py-3.5 px-3 text-center">
                    <InvoiceStatusBadge status={inv.status} />
                  </td>

                  {/* Flags de auditoría */}
                  <td className="py-3.5 px-3 text-center">
                    <AuditFlagsBadge flags={inv.audit_flags} />
                  </td>

                  {/* Acciones */}
                  <td
                    className="py-3.5 px-3 text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => navigate(`/contabilidad/facturas/${inv.id}`)}
                        title={t("invoices:table.view_detail", "Ver / Editar en Inspector Dual")}
                        className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </button>

                      <button
                        type="button"
                        onClick={() => onReprocess(inv.id)}
                        title={t("invoices:table.reprocess", "Re-analizar con IA Gemini")}
                        className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-primary transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                      >
                        <Play className="h-4 w-4" />
                      </button>

                      {!inv.is_confirmed_to_inventory && (
                        <button
                          type="button"
                          onClick={() => {
                            if (confirm(t("invoices:table.delete_confirm", "¿Estás seguro de eliminar esta factura?"))) {
                              onDelete(inv.id);
                            }
                          }}
                          title={t("invoices:table.delete", "Eliminar Factura")}
                          className="p-2 rounded-xl hover:bg-rose-500/10 text-muted-foreground hover:text-rose-500 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
