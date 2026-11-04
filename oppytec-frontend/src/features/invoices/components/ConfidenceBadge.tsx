/**
 * oppytec-frontend/src/features/invoices/components/ConfidenceBadge.tsx
 * Pill semafórico para nivel de confianza de extracción con IA (Gemini).
 */

import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { Sparkles, AlertCircle } from "lucide-react";

export interface ConfidenceBadgeProps {
  score: number;
  className?: string;
}

export function ConfidenceBadge({ score, className }: ConfidenceBadgeProps) {
  const { t } = useTranslation(["invoices"]);
  const pct = Math.round(score * 100);

  if (score >= 0.85) {
    return (
      <span
        title={t("invoices:audit_badges.high_confidence", {
          pct,
          defaultValue: `Extracción IA de alta precisión: ${pct}%`,
        })}
        className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30",
          className
        )}
      >
        <Sparkles className="h-3 w-3" />
        {pct}%
      </span>
    );
  }

  if (score >= 0.6) {
    return (
      <span
        title={t("invoices:audit_badges.medium_confidence", {
          pct,
          defaultValue: `Extracción con advertencia de precisión media: ${pct}%`,
        })}
        className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30",
          className
        )}
      >
        <Sparkles className="h-3 w-3" />
        {pct}%
      </span>
    );
  }

  return (
    <span
      title={t("invoices:audit_badges.low_confidence", {
        pct,
        defaultValue: `Baja confianza IA (${pct}%). Requiere revisión manual obligatoria.`,
      })}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 animate-pulse",
        className
      )}
    >
      <AlertCircle className="h-3 w-3" />
      {pct}%
    </span>
  );
}
