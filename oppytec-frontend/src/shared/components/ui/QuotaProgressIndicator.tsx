import {
  type QuotaResourceKey,
  type QuotaSemaphoreStatus,
  resolveQuotaSemaphoreStatus,
} from "./designTokens";

export interface QuotaProgressIndicatorProps {
  readonly resourceKey: QuotaResourceKey;
  readonly label: string;
  readonly activeCount: number;
  readonly maxLimit: number;
  readonly unitSuffix?: string;
  readonly softDeletedCount?: number;
  readonly testId?: string;
}

export function QuotaProgressIndicator({
  resourceKey,
  label,
  activeCount,
  maxLimit,
  unitSuffix = "",
  softDeletedCount = 0,
  testId,
}: QuotaProgressIndicatorProps) {
  const { status, percentage } = resolveQuotaSemaphoreStatus(
    activeCount,
    maxLimit
  );

  const badgeStyles: Record<QuotaSemaphoreStatus, string> = {
    NORMAL: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    WARNING: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    CRITICAL:
      "border-destructive bg-destructive/15 text-destructive animate-pulse",
    OVER_QUOTA: "border-destructive bg-destructive text-destructive-foreground",
  };

  const barColors: Record<QuotaSemaphoreStatus, string> = {
    NORMAL: "bg-emerald-500",
    WARNING: "bg-amber-500",
    CRITICAL: "bg-destructive",
    OVER_QUOTA: "bg-destructive",
  };

  const statusLabels: Record<QuotaSemaphoreStatus, string> = {
    NORMAL: "Saludable",
    WARNING: "Preventivo ≥80%",
    CRITICAL: "Crítico ≥95%",
    OVER_QUOTA: maxLimit <= 0 ? "No incluido en Plan" : "Cupo Agotado (100%)",
  };

  const suffix = unitSuffix ? ` ${unitSuffix}` : "";

  return (
    <div
      data-testid={testId ?? `quota-indicator-${resourceKey}`}
      data-quota-status={status}
      className="rounded-xl border border-border bg-card/80 p-3 space-y-2 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-semibold text-foreground">{label}</span>
        <span
          className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-bold ${badgeStyles[status]}`}
        >
          {statusLabels[status]}
        </span>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={`h-full transition-all duration-300 ${barColors[status]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
        <span>
          {`${activeCount}${suffix} / ${maxLimit}${suffix} (${percentage}%)`}
        </span>
        {softDeletedCount > 0 && (
          <span className="text-[10px] text-primary">
            {`${softDeletedCount} archivados (no ocupan cupo)`}
          </span>
        )}
      </div>
    </div>
  );
}
