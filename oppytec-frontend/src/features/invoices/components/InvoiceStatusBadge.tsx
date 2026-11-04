/**
 * oppytec-frontend/src/features/invoices/components/InvoiceStatusBadge.tsx
 * Badge de estado de factura con ADN Visual Legacy (3 temas).
 */

import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { Clock, AlertTriangle, XCircle, Sparkles, Box } from "lucide-react";
import type { InvoiceStatus } from "../types";

export interface InvoiceStatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

export function InvoiceStatusBadge({ status, className }: InvoiceStatusBadgeProps) {
  const { t } = useTranslation(["invoices"]);

  switch (status) {
    case "UPLOADED":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20",
            className
          )}
        >
          <Clock className="h-3.5 w-3.5" />
          {t("invoices:status.uploaded", "Cargada")}
        </span>
      );

    case "ANALYZING":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/25 animate-pulse",
            className
          )}
        >
          <Sparkles className="h-3.5 w-3.5 animate-spin" />
          {t("invoices:status.analyzing", "Analizando IA...")}
        </span>
      );

    case "ANALYZED":
    case "READY_FOR_REVIEW":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-500 dark:text-amber-400 border border-amber-500/25",
            className
          )}
        >
          <Clock className="h-3.5 w-3.5" />
          {t("invoices:status.ready_for_review", "Por Revisar")}
        </span>
      );

    case "CONFIRMED_STOCK":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30",
            className
          )}
        >
          <Box className="h-3.5 w-3.5" />
          {t("invoices:status.confirmed_stock", "En Bodega")}
        </span>
      );

    case "REJECTED":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-500 dark:text-rose-400 border border-rose-500/25",
            className
          )}
        >
          <XCircle className="h-3.5 w-3.5" />
          {t("invoices:status.rejected", "Rechazada")}
        </span>
      );

    case "ERROR":
    default:
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/15 text-red-500 dark:text-red-400 border border-red-500/25",
            className
          )}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          {t("invoices:status.error", "Error OCR")}
        </span>
      );
  }
}
