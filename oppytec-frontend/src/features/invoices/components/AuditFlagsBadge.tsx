/**
 * oppytec-frontend/src/features/invoices/components/AuditFlagsBadge.tsx
 * Indicador visual compacto para la grilla de facturas cuando existen banderas de auditoría.
 */

import { useTranslation } from "react-i18next";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { cn } from "@/shared/lib";
import type { InvoiceAuditFlag } from "../types";

export interface AuditFlagsBadgeProps {
  flags: InvoiceAuditFlag[];
  className?: string;
}

export function AuditFlagsBadge({ flags, className }: AuditFlagsBadgeProps) {
  const { t } = useTranslation(["invoices"]);
  if (!flags || flags.length === 0) return null;

  const hasHigh = flags.some((f) => f.severity === "high");

  return (
    <span
      title={flags.map((f) => `• ${f.message}`).join("\n")}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold cursor-help",
        hasHigh
          ? "bg-rose-500/20 text-rose-500 border border-rose-500/30"
          : "bg-amber-500/20 text-amber-500 border border-amber-500/30",
        className
      )}
    >
      {hasHigh ? <ShieldAlert className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
      {flags.length}{" "}
      {flags.length === 1
        ? t("invoices:audit_badges.alert_singular", "alerta")
        : t("invoices:audit_badges.alert_plural", "alertas")}
    </span>
  );
}
