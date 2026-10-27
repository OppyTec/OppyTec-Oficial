/**
 * oppytec-frontend/src/features/oppyfy/components/OppyfyCanvasPanel.tsx
 * Split-View Canvas Analítico de OppyFy (v2.0):
 * - Tablas comparativas interactivas (FEFO, demoras de proveedores, etc.)
 * - Gráficos interactivos con Recharts (barras de costos teóricos vs reales, tendencias)
 * - Action Cards interactivas (ej. "Generar Borrador de Pedido")
 * - Soporte a los 3 temas (light, dark, ocean-blue)
 * - Regla inmutable "Pollo King" para nombres propios comerciales
 */

import React, { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  Table as TableIcon,
  BarChart3,
  CheckCircle,
  FileCheck2,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";
import type { CanvasArtifact, CanvasTableColumn } from "../types";

export interface OppyfyCanvasPanelProps {
  readonly artifact: CanvasArtifact | null;
  readonly onExecuteAction?: (actionId?: string) => Promise<void> | void;
  readonly className?: string;
}

export const OppyfyCanvasPanel: React.FC<OppyfyCanvasPanelProps> = ({
  artifact,
  onExecuteAction,
  className = "",
}) => {
  const [actionSuccess, setActionSuccess] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  const handleAction = async (): Promise<void> => {
    setIsExecuting(true);
    try {
      if (onExecuteAction) {
        await onExecuteAction(artifact?.actionId);
      }
      setActionSuccess(true);
      setTimeout(() => setActionSuccess(false), 4000);
    } finally {
      setIsExecuting(false);
    }
  };

  if (!artifact) {
    return (
      <aside
        data-testid="oppyfy-split-canvas"
        className={`flex h-full flex-col items-center justify-center rounded-xl border border-border bg-card/40 p-6 text-center text-xs shadow-sm ${className}`}
      >
        <div
          data-testid="canvas-empty-state"
          className="flex flex-col items-center max-w-sm space-y-2 text-muted-foreground"
        >
          <div className="rounded-full bg-secondary p-3 text-primary">
            <Sparkles className="h-6 w-6" />
          </div>
          <h3 className="font-bold text-foreground text-sm">
            {translateKey("oppyfy", "canvas.empty_title")}
          </h3>
          <p className="leading-relaxed">
            {translateKey("oppyfy", "canvas.empty_desc")}
          </p>
        </div>
      </aside>
    );
  }

  return (
    <aside
      data-testid="oppyfy-split-canvas"
      className={`flex h-full flex-col space-y-3 rounded-xl border border-border bg-card/70 p-4 shadow-sm overflow-y-auto ${className}`}
    >
      {/* Cabecera del artefacto */}
      <div className="flex items-center justify-between border-b border-border pb-2.5">
        <div className="flex items-center gap-2">
          {artifact.type === "table" && (
            <TableIcon className="h-4 w-4 text-primary" />
          )}
          {artifact.type === "chart" && (
            <BarChart3 className="h-4 w-4 text-primary" />
          )}
          {artifact.type === "action_card" && (
            <FileCheck2 className="h-4 w-4 text-primary" />
          )}
          <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">
            {artifact.title}
          </h2>
        </div>
        <span className="font-mono text-[10px] text-muted-foreground uppercase">
          {artifact.type}
        </span>
      </div>

      {artifact.summary && (
        <p className="text-xs text-muted-foreground leading-relaxed">
          {artifact.summary}
        </p>
      )}

      {/* Renderizado condicional según tipo de artefacto */}
      {artifact.type === "table" && renderTableArtifact(artifact)}
      {artifact.type === "chart" && renderChartArtifact(artifact)}
      {artifact.type === "action_card" && (
        <div
          data-testid="canvas-action-card-artifact"
          className="space-y-4 rounded-lg border border-border bg-secondary/30 p-4 text-xs"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="font-bold text-foreground text-sm">
                {artifact.title}
              </h4>
              <p className="mt-1 text-muted-foreground leading-relaxed">
                {artifact.summary ??
                  "Acción operativa vinculada a inventario y órdenes de compra."}
              </p>
            </div>
            <FileCheck2 className="h-5 w-5 text-primary shrink-0" />
          </div>

          {actionSuccess ? (
            <div className="flex items-center gap-2 rounded-md bg-emerald-500/15 p-2.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <CheckCircle className="h-4 w-4" />
              <span>{translateKey("oppyfy", "canvas.action_success")}</span>
            </div>
          ) : (
            <button
              type="button"
              data-testid="canvas-action-execute-btn"
              onClick={handleAction}
              disabled={isExecuting}
              className="touch-target inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow transition hover:opacity-95 disabled:opacity-50"
            >
              <span>{translateKey("oppyfy", "canvas.action_execute")}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
    </aside>
  );
};

// ============================================================================
// SUB-RENDERIZADORES
// ============================================================================

function renderTableArtifact(artifact: CanvasArtifact) {
  const rawData = artifact.data;
  const rows: Array<Record<string, unknown>> = Array.isArray(rawData)
    ? (rawData as Array<Record<string, unknown>>)
    : [];

  const columns: CanvasTableColumn[] = (artifact.columns ?? []).map((col) => {
    if (typeof col === "string") {
      return { key: col, label: col };
    }
    return col;
  });

  const firstRow = rows[0];
  const resolvedColumns: CanvasTableColumn[] =
    columns.length > 0
      ? columns
      : firstRow
      ? Object.keys(firstRow).map((key) => ({ key, label: key }))
      : [];

  return (
    <div
      data-testid="canvas-table-artifact"
      className="overflow-x-auto rounded-lg border border-border bg-card"
    >
      <table className="w-full text-left text-xs">
        <thead className="border-b border-border bg-secondary/50 font-semibold text-muted-foreground uppercase text-[10px]">
          <tr>
            {resolvedColumns.map((c) => (
              <th key={c.key} className="px-3 py-2">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, rIdx) => (
            <tr
              key={`row-${rIdx}`}
              data-testid={`canvas-table-row-${rIdx}`}
              className="hover:bg-secondary/20 transition-colors"
            >
              {resolvedColumns.map((c) => {
                const val = row[c.key];
                return (
                  <td key={c.key} className="px-3 py-2 text-foreground font-mono">
                    {c.type === "currency" ||
                    (typeof val === "number" && c.key.toLowerCase().includes("cost")) ? (
                      <MoneyBadge amount={String(val)} baseCurrency="CLP" />
                    ) : (
                      String(val ?? "")
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderChartArtifact(artifact: CanvasArtifact) {
  const chartData = Array.isArray(artifact.data)
    ? (artifact.data as Array<Record<string, unknown>>)
    : [];

  const isLine = artifact.chartType === "line";

  return (
    <div
      data-testid="canvas-chart-artifact"
      className="rounded-lg border border-border bg-card p-3"
    >
      <div className="h-64 w-full" style={{ minHeight: "240px", minWidth: "100px" }}>
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={100}
          minHeight={200}
          initialDimension={{ width: 400, height: 240 }}
        >
          {isLine ? (
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  borderColor: "hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "11px",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px" }} />
              <Line
                type="monotone"
                dataKey="teorico"
                name={translateKey("oppyfy", "canvas.cost_theoretical")}
                stroke="#10b981"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="real"
                name={translateKey("oppyfy", "canvas.cost_real")}
                stroke="#ef4444"
                strokeWidth={2}
              />
            </LineChart>
          ) : (
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  borderColor: "hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "11px",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px" }} />
              <Bar
                dataKey="teorico"
                name={translateKey("oppyfy", "canvas.cost_theoretical")}
                fill="#10b981"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="real"
                name={translateKey("oppyfy", "canvas.cost_real")}
                fill="#ef4444"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
