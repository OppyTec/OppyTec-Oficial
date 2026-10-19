import type { ReactNode } from "react";
import { translateKey } from "@/shared/i18n";

export interface AdaptiveColumn<TRow> {
  readonly key: string;
  readonly header: string;
  readonly render: (row: TRow) => ReactNode;
}

export interface AdaptiveDataViewProps<TRow> {
  readonly rows: readonly TRow[];
  readonly columns: readonly AdaptiveColumn<TRow>[];
  readonly getRowKey: (row: TRow) => string;
  readonly isMobile?: boolean;
  readonly testId?: string;
}

/**
 * Mobile-First Adaptive Data View: Renders stacked touch cards on mobile viewports
 * and a dense scrollable table on desktop viewports.
 */
export function AdaptiveDataView<TRow>({
  rows,
  columns,
  getRowKey,
  isMobile = false,
  testId = "adaptive-data-view",
}: AdaptiveDataViewProps<TRow>) {
  if (rows.length === 0) {
    return (
      <div
        data-testid={`${testId}-empty`}
        className="rounded-xl border border-border bg-secondary/20 p-4 text-center text-xs text-muted-foreground"
      >
        {translateKey("common", "status.empty")}
      </div>
    );
  }

  if (isMobile) {
    return (
      <div data-testid={testId} data-mode="mobile-cards" className="space-y-2.5">
        {rows.map((row) => (
          <div
            key={getRowKey(row)}
            className="glass-card rounded-xl border border-border p-3"
          >
            {columns.map((col) => (
              <div
                key={col.key}
                className="flex items-center justify-between gap-2 py-1 text-xs"
              >
                <span className="font-medium text-muted-foreground">
                  {col.header}
                </span>
                <span className="font-semibold text-foreground">
                  {col.render(row)}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      data-testid={testId}
      data-mode="desktop-table"
      className="custom-table-scrollbar overflow-x-auto rounded-xl border border-border"
    >
      <table className="w-full border-collapse text-left text-xs">
        <thead className="bg-secondary/60 text-muted-foreground">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-3 py-2.5 font-semibold">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr key={getRowKey(row)} className="hover:bg-secondary/30">
              {columns.map((col) => (
                <td key={col.key} className="px-3 py-2 text-foreground">
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
