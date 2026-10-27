import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

/**
 * Las 13 Sub-Vistas Oficiales del Centro de Observabilidad SuperUser (Estrategia Observabilidad 4-Pilares).
 */
export const OBSERVABILITY_13_SUBVIEWS = [
  "01-health-overview",
  "02-otel-distributed-traces",
  "03-loki-structured-logs",
  "04-prometheus-red-use-metrics",
  "05-sentry-exceptions-pii-scrubbed",
  "06-umami-privacy-analytics",
  "07-postgres-tenant-schemas",
  "08-redis-streams-websockets",
  "09-celery-workers-queues",
  "10-r2-storage-quotas",
  "11-fx-central-bank-sync",
  "12-backups-4layer-age-zst",
  "13-finops-llm-request-logs",
] as const;

export type ObservabilitySubviewId = (typeof OBSERVABILITY_13_SUBVIEWS)[number];

export const CANONICAL_ENVIRONMENTS = [
  "local",
  "preview",
  "ci",
  "staging",
  "production",
] as const;

export type CanonicalEnvFilter = (typeof CANONICAL_ENVIRONMENTS)[number];

export function PlatformAdminFeatureView() {
  const [selectedEnv, setSelectedEnv] =
    useState<CanonicalEnvFilter>("production");
  const [activeSubview, setActiveSubview] = useState<ObservabilitySubviewId>(
    "01-health-overview"
  );
  const [finopsViewMode, setFinopsViewMode] = useState<
    "by-tenant" | "by-model"
  >("by-tenant");
  const [backupRestored, setBackupRestored] = useState<boolean>(false);

  return (
    <section
      data-testid="feature-platform-admin"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("platform_admin", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("platform_admin", "tenants.provisioning", {
              schema: "tenant_rest_central",
            })}
          </p>
        </div>

        {/* Filtro de los 5 Entornos Oficiales (local, preview, ci, staging, production) */}
        <div
          data-testid="platform-admin-env-filter"
          className="flex flex-wrap gap-1"
        >
          {CANONICAL_ENVIRONMENTS.map((envName) => (
            <button
              key={envName}
              type="button"
              data-testid={`obs-env-filter-${envName}`}
              onClick={() => setSelectedEnv(envName)}
              className={`touch-target inline-flex min-h-[44px] items-center rounded-md px-2.5 py-1 font-mono text-xs font-semibold ${
                selectedEnv === envName
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {envName}
            </button>
          ))}
        </div>
      </div>

      {/* Holdings, 1:1 Legal Entities, FX Console & 4-Layer Backups */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div
          data-testid="platform-admin-holdings-card"
          className="space-y-1.5 rounded-xl border border-border bg-secondary/20 p-3 text-xs"
        >
          <h3 className="font-bold uppercase text-muted-foreground">
            Holdings & Razón Social 1:1
          </h3>
          <p className="font-semibold text-foreground">
            Holding Gastronómico Sur SpA
          </p>
          <p className="font-mono text-[11px] text-muted-foreground">
            RUT 76.543.210-K · Plan Enterprise (25 cupos)
          </p>
        </div>

        <div
          data-testid="platform-admin-fx-card"
          className="space-y-1.5 rounded-xl border border-border bg-secondary/20 p-3 text-xs"
        >
          <h3 className="font-bold uppercase text-muted-foreground">
            Consola FX (BCCh & BCE Frankfurter)
          </h3>
          <p className="text-muted-foreground">
            {translateKey("platform_admin", "fx_admin.manual_override", {
              pair: "USD/CLP",
              rate: "960.00000000",
              reason: "Sincronización BCCh 08:30",
            })}
          </p>
          <MoneyBadge amount="960" baseCurrency="CLP" />
        </div>

        <div
          data-testid="platform-admin-backups-card"
          className="space-y-1.5 rounded-xl border border-border bg-secondary/20 p-3 text-xs"
        >
          <h3 className="font-bold uppercase text-muted-foreground">
            Backups 4-Capas (.sql.zst.age)
          </h3>
          <p className="text-muted-foreground">
            {translateKey("platform_admin", "tenants.backup_restore", {
              tenantId: "tenant_rest_central",
            })}
          </p>
          <Can perform="platform_admin.backups.restore">
            <button
              type="button"
              data-testid="platform-admin-restore-btn"
              onClick={() => setBackupRestored(true)}
              className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground"
            >
              {backupRestored
                ? "Shadow Schema Validado OK"
                : "Dry-Run Restauración Quirúrgica"}
            </button>
          </Can>
        </div>
      </div>

      {/* 2 Vistas FinOps llm_request_logs */}
      <div
        data-testid="platform-admin-finops-views"
        className="rounded-xl border border-border bg-secondary/20 p-3"
      >
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            FinOps `llm_request_logs` (2 Vistas: Por Tenant / Por Modelo & Agente)
          </h3>
          <div className="flex gap-1.5">
            <button
              type="button"
              data-testid="finops-view-by-tenant"
              onClick={() => setFinopsViewMode("by-tenant")}
              className={`touch-target inline-flex min-h-[44px] items-center rounded-md px-2.5 py-1 text-xs font-semibold ${
                finopsViewMode === "by-tenant"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-foreground"
              }`}
            >
              Vista 1: Consumo por Tenant
            </button>
            <button
              type="button"
              data-testid="finops-view-by-model"
              onClick={() => setFinopsViewMode("by-model")}
              className={`touch-target inline-flex min-h-[44px] items-center rounded-md px-2.5 py-1 text-xs font-semibold ${
                finopsViewMode === "by-model"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-foreground"
              }`}
            >
              Vista 2: Latencia & Costo por Modelo
            </button>
          </div>
        </div>
        <p className="font-mono text-xs text-foreground">
          {finopsViewMode === "by-tenant"
            ? `Modo Activo [by-tenant] (${selectedEnv}): tenant_rest_central · 14,280 tokens · JEV Hit Rate 78.4%`
            : `Modo Activo [by-model] (${selectedEnv}): gemini-3.8-flash (p95=310ms) · jev-system1 (p95=3ms)`}
        </p>
      </div>

      {/* Centro de Observabilidad de 13 Sub-Vistas */}
      <div
        data-testid="observability-13-center"
        className="space-y-3 rounded-xl border border-border bg-secondary/20 p-3"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            Centro de Observabilidad 4-Pilares (13 Sub-Vistas · Filtro Environment)
          </h3>
          <span
            data-testid="observability-active-indicator"
            className="font-mono text-xs font-bold text-primary"
          >
            {`${selectedEnv} :: ${activeSubview}`}
          </span>
        </div>
        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
          {OBSERVABILITY_13_SUBVIEWS.map((sub) => (
            <button
              key={sub}
              type="button"
              data-testid={`obs-subview-${sub}`}
              onClick={() => setActiveSubview(sub)}
              className={`touch-target flex min-h-[44px] items-center justify-between rounded-lg border px-2.5 py-1.5 text-left font-mono text-[11px] ${
                activeSubview === sub
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-foreground"
              }`}
            >
              <span>{sub}</span>
              <span>{selectedEnv}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

export { AdminDashboard } from "./AdminDashboard";
export { AdminLayout } from "./AdminLayout";
export {
  AdminBusinessTypesView,
  AdminClientUsersView,
  AdminGlobalUsersView,
  AdminHoldingsView,
  AdminLegalEntitiesView,
  AdminModulesView,
  AdminPlansView,
  AdminTenantsView,
  HoldingsManagementView,
  PlansManagementView,
  TenantsManagementView,
  PLAN_BASICO_10_MODULE_SLUGS,
  SAAS_MODULE_TREE,
} from "./AdminManagementViews";
export { AdminSidebar } from "./AdminSidebar";
export type { AdminSidebarProps, MenuItem } from "./AdminSidebar";
export type { DashboardCounts } from "./AdminDashboard";
export type { TenantOptionItem } from "./AdminLayout";
export * from "./types";
export * from "./hooks";
export * from "./plans";
export * from "./tokens";

