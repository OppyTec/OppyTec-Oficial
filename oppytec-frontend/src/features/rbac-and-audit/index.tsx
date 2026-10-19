import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { usePermissions } from "@/shared/auth/usePermissions";
import { AdaptiveDataView } from "@/shared/components/ui/AdaptiveDataView";
import { translateKey } from "@/shared/i18n";

interface ForensicAuditRow {
  readonly id: string;
  readonly action: string;
  readonly actor: string;
  readonly traceId: string;
  readonly diffSummary: string;
}

const INITIAL_AUDIT_LOGS: readonly ForensicAuditRow[] = [
  {
    id: "AUD-9001",
    action: "inventory.mermas.approve",
    actor: "chef.ejecutivo@oppytec.cl",
    traceId: "4bf92f3577b34da6a3ce929d0e0e4736",
    diffSummary: "old_status=PENDING -> new_status=APPROVED (12.5000 kg)",
  },
  {
    id: "AUD-9002",
    action: "rbac_audit.roles.manage",
    actor: "admin.holding@oppytec.cl",
    traceId: "8a12cc9011ab49d1b900112233445566",
    diffSummary: "grant_temp=inventory.mermas.override_threshold (TTL 4h)",
  },
];

export function RbacAndAuditFeatureView() {
  const { policy } = usePermissions();
  const [usedSeats, setUsedSeats] = useState<number>(18);
  const limitSeats = 25;

  const handleSoftDeleteReleaseSeat = (): void => {
    setUsedSeats((prev) => (prev > 1 ? prev - 1 : prev));
  };

  return (
    <section
      data-testid="feature-rbac-and-audit"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("rbac_audit", "rbac.title")}
          </h2>
          <p className="font-mono text-xs text-muted-foreground">
            {`Fórmula: M_Plan ∩ ((P_Role ∪ P_Temp) - P_Deny) · Rol activo: ${policy.roleName}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            data-testid="rbac-seat-quota-badge"
            className="rounded-lg border border-border bg-secondary px-3 py-1.5 font-mono text-xs font-semibold text-foreground"
          >
            {translateKey("rbac_audit", "rbac.seat_quota_usage", {
              used: usedSeats,
              limit: limitSeats,
            })}
          </span>
          <Can perform="rbac_audit.roles.manage">
            <button
              type="button"
              data-testid="rbac-release-seat-btn"
              onClick={handleSoftDeleteReleaseSeat}
              className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground"
            >
              Soft-Delete Usuario (Liberar Cupo)
            </button>
          </Can>
        </div>
      </div>

      {/* Matriz de 3 Niveles (<modulo>.<submodulo>.<funcion>) & JIT Grants */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div
          data-testid="rbac-three-level-matrix"
          className="rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="mb-2 text-xs font-bold uppercase text-muted-foreground">
            Matriz 3 Niveles (Módulo · Submódulo · Función)
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {policy.rolePermissions.slice(0, 10).map((perm) => (
              <span
                key={perm}
                className="rounded border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary"
              >
                {perm}
              </span>
            ))}
          </div>
        </div>

        <div
          data-testid="rbac-jit-grants"
          className="rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="mb-2 text-xs font-bold uppercase text-muted-foreground">
            JIT Temporary Grants (`user_temporary_grants`)
          </h3>
          {policy.temporaryGrants.map((grant) => (
            <div
              key={grant.permission}
              className="rounded-lg border border-border bg-card p-2 text-xs"
            >
              <div className="font-mono font-bold text-primary">
                {grant.permission}
              </div>
              <div className="text-muted-foreground">{grant.reason}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Forensic Audit Viewer */}
      <div className="space-y-2">
        <h3 className="text-sm font-bold text-foreground">
          {translateKey("rbac_audit", "audit.title")}
        </h3>
        <AdaptiveDataView
          testId="forensic-audit-table"
          rows={INITIAL_AUDIT_LOGS}
          getRowKey={(r) => r.id}
          columns={[
            {
              key: "event",
              header: "Evento",
              render: (r) =>
                translateKey("rbac_audit", "audit.event_recorded", {
                  action: r.action,
                  actor: r.actor,
                  traceId: r.traceId.slice(0, 12),
                }),
            },
            {
              key: "diff",
              header: "JSON Diff Inmutable",
              render: (r) => (
                <span className="font-mono text-[11px]">{r.diffSummary}</span>
              ),
            },
          ]}
        />
      </div>
    </section>
  );
}
