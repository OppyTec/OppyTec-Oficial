/**
 * oppytec-frontend/src/features/oppyfy/components/governance/OppyfyTemporaryGrantsManager.tsx
 * Gestor de Permisos Temporales Exclusivos de OppyFy.
 * - Lista de concesiones temporales activas con triple control de caducidad
 * - Apertura y gestión del modal de otorgamiento de permisos
 * - Mobile-first con touch targets >= 44px
 */

import { useState } from "react";
import { KeyRound, Plus, Ban, CheckCircle2 } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type {
  OppyfyTemporaryGrantItem,
  OppyfyGrantCreateRequest,
  OppyfyDomainTreeResponse,
  OppyfyWorkerWalletItem,
} from "../../types";
import { GrantPermissionModal } from "./GrantPermissionModal";

export interface OppyfyTemporaryGrantsManagerProps {
  readonly grants: readonly OppyfyTemporaryGrantItem[];
  readonly domains: readonly OppyfyDomainTreeResponse[];
  readonly workers: readonly OppyfyWorkerWalletItem[];
  readonly onGrantPermission: (payload: OppyfyGrantCreateRequest) => Promise<unknown>;
  readonly onRevokeGrant: (grantId: string) => void;
  readonly isGranting?: boolean;
}

export function OppyfyTemporaryGrantsManager({
  grants,
  domains,
  workers,
  onGrantPermission,
  onRevokeGrant,
  isGranting = false,
}: OppyfyTemporaryGrantsManagerProps) {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  return (
    <div
      data-testid="oppyfy-temporary-grants-manager"
      className="flex flex-col space-y-4"
    >
      {/* Barra superior de acciones */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-bold text-card-foreground">
            {translateKey("oppyfy", "governance.tabs.grants")}
          </h3>
          <p className="text-xs text-muted-foreground">
            Concede acceso temporal con triple control de caducidad (fecha, prompts y créditos).
          </p>
        </div>
        <button
          type="button"
          data-testid="btn-open-grant-modal"
          onClick={() => setIsModalOpen(true)}
          className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          <span>{translateKey("oppyfy", "governance.grants.grant_btn")}</span>
        </button>
      </div>

      {/* Tabla de Concesiones */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary/20 text-muted-foreground">
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_user")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_subdomain")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_view_costs")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_expires_at")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_max_prompts")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_temp_credit_ceiling")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.grants.th_status")}
              </th>
              <th className="px-4 py-3 font-semibold text-right">
                {translateKey("oppyfy", "governance.grants.th_actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {grants.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="px-4 py-8 text-center text-xs text-muted-foreground"
                >
                  {translateKey("oppyfy", "governance.grants.empty")}
                </td>
              </tr>
            ) : (
              grants.map((grant) => (
                <tr
                  key={grant.grant_id}
                  data-testid={`grant-row-${grant.grant_id}`}
                  className="hover:bg-secondary/10 transition-colors"
                >
                  {/* Trabajador */}
                  <td className="px-4 py-3 font-medium text-card-foreground">
                    <div className="flex items-center gap-2">
                      <KeyRound className="h-4 w-4 text-primary" />
                      <span>{grant.user_name || `Usuario #${grant.user_id}`}</span>
                    </div>
                  </td>

                  {/* Subdominio */}
                  <td className="px-4 py-3 font-mono text-xs text-foreground">
                    <span>{grant.subdomain_name || grant.subdomain_slug}</span>
                  </td>

                  {/* Ver Costos */}
                  <td className="px-4 py-3">
                    <span
                      data-testid={`grant-cost-badge-${grant.grant_id}`}
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                        grant.can_view_costs
                          ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {grant.can_view_costs ? "Desbloqueado" : "Enmascarado"}
                    </span>
                  </td>

                  {/* Fecha de vencimiento */}
                  <td className="px-4 py-3 font-mono text-muted-foreground">
                    {grant.expires_at
                      ? new Date(grant.expires_at).toLocaleString("es-CL")
                      : translateKey("oppyfy", "governance.grants.unlimited")}
                  </td>

                  {/* Límite de Prompts */}
                  <td className="px-4 py-3 font-mono text-card-foreground">
                    {grant.max_prompts !== null
                      ? `${grant.max_prompts} consultas`
                      : translateKey("oppyfy", "governance.grants.unlimited")}
                  </td>

                  {/* Tope de Créditos */}
                  <td className="px-4 py-3 font-mono text-card-foreground">
                    {grant.temp_credit_ceiling !== null
                      ? `${grant.temp_credit_ceiling} cr.`
                      : translateKey("oppyfy", "governance.grants.unlimited")}
                  </td>

                  {/* Estado */}
                  <td className="px-4 py-3">
                    <span
                      data-testid={`grant-status-${grant.grant_id}`}
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        grant.is_active
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                          : "bg-destructive/15 text-destructive"
                      }`}
                    >
                      {grant.is_active ? (
                        <>
                          <CheckCircle2 className="h-3 w-3" />
                          <span>{translateKey("oppyfy", "governance.grants.active_badge")}</span>
                        </>
                      ) : (
                        <>
                          <Ban className="h-3 w-3" />
                          <span>{translateKey("oppyfy", "governance.grants.revoked_badge")}</span>
                        </>
                      )}
                    </span>
                  </td>

                  {/* Acciones */}
                  <td className="px-4 py-3 text-right">
                    {grant.is_active && (
                      <button
                        type="button"
                        data-testid={`btn-revoke-grant-${grant.grant_id}`}
                        onClick={() => onRevokeGrant(grant.grant_id)}
                        className="touch-target inline-flex min-h-[44px] items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold text-destructive transition-colors hover:bg-destructive/10"
                      >
                        <Ban className="h-3.5 w-3.5" />
                        <span>{translateKey("oppyfy", "governance.grants.revoke_btn")}</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal de Concesión */}
      <GrantPermissionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        domains={domains}
        workers={workers}
        onGrantPermission={onGrantPermission}
        isGranting={isGranting}
      />
    </div>
  );
}
