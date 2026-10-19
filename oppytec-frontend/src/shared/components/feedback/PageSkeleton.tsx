import { translateKey } from "@/shared/i18n";

export interface PageSkeletonProps {
  readonly rows?: number;
}

export function PageSkeleton({ rows = 3 }: PageSkeletonProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="page-skeleton"
      className="space-y-3 rounded-xl border border-border bg-card/50 p-4"
    >
      <span className="text-xs font-medium text-muted-foreground">
        {translateKey("common", "status.loading")}
      </span>
      {Array.from({ length: rows }).map((_, idx) => (
        <div
          key={String(idx)}
          className="h-10 w-full animate-pulse rounded-lg bg-secondary/70"
        />
      ))}
    </div>
  );
}
