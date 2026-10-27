/**
 * oppytec-frontend/src/features/oppyfy/components/governance/OppyfyPromptAuditLogViewer.tsx
 * Visor de la Bitácora Inmutable de Auditoría de Prompts (oppyfy_prompt_audit_log).
 * - Registra cada intento de consulta de los trabajadores
 * - Muestra rechazos por falta de permisos (BLOCKED_UNAUTHORIZED_PROMPT)
 * - Filtro por estado (Todos, Solo Bloqueados, Solo Permitidos)
 * - Buscador en tiempo real de texto de prompt, trabajador o dominio
 * - Mobile-first con touch targets >= 44px
 */

import { useState, useMemo } from "react";
import {
  Search,
  CheckCircle2,
  ShieldBan,
  Wrench,
  Clock,
  Layers,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { OppyfyPromptAuditLogItem } from "../../types";

export interface OppyfyPromptAuditLogViewerProps {
  readonly auditLogs: readonly OppyfyPromptAuditLogItem[];
}

export type AuditStatusFilter = "all" | "blocked" | "allowed";

export function OppyfyPromptAuditLogViewer({
  auditLogs,
}: OppyfyPromptAuditLogViewerProps) {
  const [statusFilter, setStatusFilter] = useState<AuditStatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      // Filtro de estado
      if (statusFilter === "blocked" && log.status !== "BLOCKED_UNAUTHORIZED_PROMPT") {
        return false;
      }
      if (statusFilter === "allowed" && log.status !== "ALLOWED") {
        return false;
      }

      // Filtro de búsqueda textual
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesPrompt = log.prompt_text.toLowerCase().includes(q);
        const matchesUser = (log.user_name || String(log.user_id)).toLowerCase().includes(q);
        const matchesDomain = (log.resolved_domain || "").toLowerCase().includes(q);
        return matchesPrompt || matchesUser || matchesDomain;
      }

      return true;
    });
  }, [auditLogs, statusFilter, searchQuery]);

  return (
    <div
      data-testid="oppyfy-prompt-audit-log-viewer"
      className="flex flex-col space-y-4"
    >
      {/* Encabezado y Barra de Filtros */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-bold text-card-foreground">
            {translateKey("oppyfy", "governance.audit.title")}
          </h3>
          <p className="text-xs text-muted-foreground">
            Bitácora inmutable de consultas y validaciones de seguridad RBAC de OppyFy.
          </p>
        </div>

        {/* Contador de registros */}
        <div className="rounded-lg bg-secondary/50 px-3 py-1 font-mono text-xs text-muted-foreground">
          {filteredLogs.length} de {auditLogs.length} registros
        </div>
      </div>

      {/* Controles: Buscador + Filtros de Estado */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Input Buscador */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            data-testid="input-audit-search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={translateKey("oppyfy", "governance.audit.search_placeholder")}
            className="touch-target min-h-[44px] w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Botones de Estado */}
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filtro de estados de auditoría">
          <button
            type="button"
            data-testid="filter-audit-all"
            onClick={() => setStatusFilter("all")}
            className={`touch-target inline-flex min-h-[44px] items-center px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === "all"
                ? "border-primary bg-primary/15 text-primary"
                : "border-border bg-card text-muted-foreground hover:bg-muted"
            }`}
          >
            {translateKey("oppyfy", "governance.audit.filter_status_all")}
          </button>
          <button
            type="button"
            data-testid="filter-audit-blocked"
            onClick={() => setStatusFilter("blocked")}
            className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === "blocked"
                ? "border-destructive bg-destructive/15 text-destructive"
                : "border-border bg-card text-muted-foreground hover:bg-muted"
            }`}
          >
            <ShieldBan className="h-3.5 w-3.5" />
            <span>{translateKey("oppyfy", "governance.audit.filter_status_blocked")}</span>
          </button>
          <button
            type="button"
            data-testid="filter-audit-allowed"
            onClick={() => setStatusFilter("allowed")}
            className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === "allowed"
                ? "border-emerald-500 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                : "border-border bg-card text-muted-foreground hover:bg-muted"
            }`}
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>{translateKey("oppyfy", "governance.audit.filter_status_allowed")}</span>
          </button>
        </div>
      </div>

      {/* Tabla de Eventos de Auditoría */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary/20 text-muted-foreground">
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.audit.th_timestamp")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.audit.th_worker")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.audit.th_prompt")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.audit.th_status")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.audit.th_domain")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.audit.th_tools")}
              </th>
              <th className="px-4 py-3 font-semibold text-right">
                {translateKey("oppyfy", "governance.audit.th_credits")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredLogs.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-8 text-center text-xs text-muted-foreground"
                >
                  {translateKey("oppyfy", "governance.audit.empty")}
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => {
                const isBlocked = log.status === "BLOCKED_UNAUTHORIZED_PROMPT";
                return (
                  <tr
                    key={log.id}
                    data-testid={`audit-row-${log.id}`}
                    className={`hover:bg-secondary/10 transition-colors ${
                      isBlocked ? "bg-destructive/5" : ""
                    }`}
                  >
                    {/* Timestamp */}
                    <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        <span>{new Date(log.created_at).toLocaleString("es-CL")}</span>
                      </div>
                    </td>

                    {/* Trabajador */}
                    <td className="px-4 py-3 font-medium text-foreground whitespace-nowrap">
                      {log.user_name || `Usuario #${log.user_id}`}
                    </td>

                    {/* Texto del Prompt */}
                    <td className="px-4 py-3 max-w-xs font-serif text-xs text-card-foreground">
                      <p className="line-clamp-2" title={log.prompt_text}>
                        "{log.prompt_text}"
                      </p>
                    </td>

                    {/* Estado RBAC */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        data-testid={`audit-badge-status-${log.id}`}
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                          isBlocked
                            ? "bg-destructive/15 text-destructive border border-destructive/30"
                            : "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                        }`}
                      >
                        {isBlocked ? (
                          <>
                            <ShieldBan className="h-3 w-3" />
                            <span>BLOCKED</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="h-3 w-3" />
                            <span>ALLOWED</span>
                          </>
                        )}
                      </span>
                    </td>

                    {/* Dominio */}
                    <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Layers className="h-3 w-3" />
                        <span>{log.resolved_domain || "-"}</span>
                      </div>
                    </td>

                    {/* Herramientas */}
                    <td className="px-4 py-3">
                      {log.resolved_tools.length === 0 ? (
                        <span className="text-[11px] text-muted-foreground">-</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {log.resolved_tools.map((t) => (
                            <span
                              key={t}
                              className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground flex items-center gap-1"
                            >
                              <Wrench className="h-2.5 w-2.5" />
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>

                    {/* Créditos y Tokens */}
                    <td className="px-4 py-3 font-mono text-right whitespace-nowrap">
                      <div className="font-bold text-foreground">
                        {log.credits_deducted} cr.
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {log.tokens_spent} tokens
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
