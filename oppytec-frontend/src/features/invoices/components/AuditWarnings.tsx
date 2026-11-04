/**
 * oppytec-frontend/src/features/invoices/components/AuditWarnings.tsx
 * Lista expandida de banderas de auditoría tributaria y discrepancias de precios.
 */

import { useTranslation } from "react-i18next";
import { AlertTriangle, ShieldAlert, Info } from "lucide-react";
import { cn } from "@/shared/lib";
import type { InvoiceAuditFlag } from "../types";

export interface AuditWarningsProps {
  flags: InvoiceAuditFlag[];
  className?: string;
}

export function AuditWarnings({ flags, className }: AuditWarningsProps) {
  const { t } = useTranslation(["invoices"]);
  if (!flags || flags.length === 0) return null;

  return (
    <div className={cn("space-y-2", className)} data-testid="audit-warnings-container">
      {flags.map((flag, idx) => {
        const isHigh = flag.severity === "high";
        const isMedium = flag.severity === "medium";
        const translatedMessage = t(
          `invoices:audit_rules.${flag.code.toLowerCase()}`,
          flag.message
        );

        return (
          <div
            key={`${flag.code}-${idx}`}
            className={cn(
              "flex items-start gap-3 p-3 rounded-xl border text-xs transition-all",
              isHigh
                ? "bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400"
                : isMedium
                ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300"
                : "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400"
            )}
          >
            <div className="shrink-0 mt-0.5">
              {isHigh ? (
                <ShieldAlert className="h-4 w-4" />
              ) : isMedium ? (
                <AlertTriangle className="h-4 w-4" />
              ) : (
                <Info className="h-4 w-4" />
              )}
            </div>
            <div className="flex-1">
              <span className="font-bold uppercase tracking-wider text-[10px] block opacity-80">
                {flag.code.replace(/_/g, " ")}
              </span>
              <p className="mt-0.5 leading-relaxed">{translatedMessage}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
