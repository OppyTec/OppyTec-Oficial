import type { ReactNode } from "react";
import { translateKey } from "@/shared/i18n";

export interface EmptyStateProps {
  readonly title?: string;
  readonly actionSlot?: ReactNode;
}

export function EmptyState({ title, actionSlot }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-secondary/20 p-6 text-center"
    >
      <p className="text-sm font-medium text-muted-foreground">
        {title ?? translateKey("common", "status.empty")}
      </p>
      {actionSlot}
    </div>
  );
}
