/**
 * oppytec-frontend/src/features/oppyfy/components/governance/OppyfyWorkerWalletsManager.tsx
 * Gestor de la Billetera de Créditos del Tenant y Asignación de Cupos por Trabajador.
 * - Bolsa global de créditos (sin caducidad, 100% acumulables / Rollover)
 * - Matriz de trabajadores con activación individual y cupo asignado
 * - Modal para editar cupo de trabajador
 * - Modal para cotizar y comprar paquetes Add-On
 * - Mobile-first con touch targets >= 44px
 */

import { useState } from "react";
import {
  Wallet,
  Sparkles,
  Coins,
  TrendingDown,
  Edit2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type {
  OppyfyWorkerWalletItem,
  OppyfyTenantCreditBagSummary,
  OppyfyWalletPatchRequest,
  AiCreditPackResponse,
  AiCreditPackQuoteResponse,
} from "../../types";
import { EditWorkerWalletModal } from "./EditWorkerWalletModal";
import { BuyCreditPackModal } from "./BuyCreditPackModal";

export interface OppyfyWorkerWalletsManagerProps {
  readonly workers: readonly OppyfyWorkerWalletItem[];
  readonly tenantCreditBag: OppyfyTenantCreditBagSummary;
  readonly aiPacks: readonly AiCreditPackResponse[];
  readonly onUpdateWorkerWallet: (
    userId: number,
    patch: OppyfyWalletPatchRequest
  ) => Promise<void>;
  readonly onQuotePack: (packId: number, planTier?: string) => Promise<AiCreditPackQuoteResponse>;
}

export function OppyfyWorkerWalletsManager({
  workers,
  tenantCreditBag,
  aiPacks,
  onUpdateWorkerWallet,
  onQuotePack,
}: OppyfyWorkerWalletsManagerProps) {
  const [selectedWorkerForEdit, setSelectedWorkerForEdit] =
    useState<OppyfyWorkerWalletItem | null>(null);
  const [isBuyModalOpen, setIsBuyModalOpen] = useState<boolean>(false);

  const handleToggleWorkerEnabled = async (worker: OppyfyWorkerWalletItem) => {
    await onUpdateWorkerWallet(worker.user_id, {
      is_oppyfy_enabled: !worker.is_oppyfy_enabled,
    });
  };

  return (
    <div
      data-testid="oppyfy-worker-wallets-manager"
      className="flex flex-col space-y-4"
    >
      {/* Tarjeta: Bolsa Global de Créditos del Tenant */}
      <div
        data-testid="tenant-global-credit-bag"
        className="glass-card rounded-2xl border border-primary/30 bg-primary/5 p-5 shadow-sm"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-primary">
              <Wallet className="h-5 w-5" />
              <h3 className="text-sm font-bold uppercase tracking-wider">
                {translateKey("oppyfy", "governance.wallets.pool_title")}
              </h3>
            </div>
            <p className="text-xs text-muted-foreground">
              {translateKey("oppyfy", "governance.wallets.pool_desc")}
            </p>
          </div>

          <button
            type="button"
            data-testid="btn-open-buy-pack"
            onClick={() => setIsBuyModalOpen(true)}
            className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90"
          >
            <Sparkles className="h-4 w-4" />
            <span>{translateKey("oppyfy", "governance.wallets.buy_pack_btn")}</span>
          </button>
        </div>

        {/* Métricas de la bolsa global */}
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 pt-3 border-t border-primary/20">
          <div className="rounded-xl border border-border bg-card/70 p-3">
            <span className="text-[11px] font-medium text-muted-foreground">
              {translateKey("oppyfy", "governance.wallets.total_purchased")}
            </span>
            <div className="mt-1 text-lg font-extrabold text-foreground">
              {tenantCreditBag.total_purchased_credits.toFixed(2)} cr.
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card/70 p-3">
            <span className="text-[11px] font-medium text-muted-foreground">
              {translateKey("oppyfy", "governance.wallets.total_allocated")}
            </span>
            <div className="mt-1 text-lg font-extrabold text-primary">
              {tenantCreditBag.total_allocated_credits.toFixed(2)} cr.
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card/70 p-3">
            <span className="text-[11px] font-medium text-muted-foreground">
              {translateKey("oppyfy", "governance.wallets.total_consumed")}
            </span>
            <div className="mt-1 text-lg font-extrabold text-muted-foreground">
              {tenantCreditBag.total_consumed_credits.toFixed(2)} cr.
            </div>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
            <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
              {translateKey("oppyfy", "governance.wallets.remaining_pool")}
            </span>
            <div className="mt-1 text-lg font-extrabold text-emerald-600 dark:text-emerald-400">
              {tenantCreditBag.remaining_pool_credits.toFixed(2)} cr.
            </div>
          </div>
        </div>
      </div>

      {/* Tabla de Trabajadores y Cupos */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary/20 text-muted-foreground">
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.wallets.th_worker")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.wallets.th_status")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.wallets.th_ceiling")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.wallets.th_consumed")}
              </th>
              <th className="px-4 py-3 font-semibold">
                {translateKey("oppyfy", "governance.wallets.th_remaining")}
              </th>
              <th className="px-4 py-3 font-semibold text-right">
                {translateKey("oppyfy", "governance.wallets.th_actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {workers.map((worker) => (
              <tr
                key={worker.user_id}
                data-testid={`worker-wallet-row-${worker.user_id}`}
                className="hover:bg-secondary/10 transition-colors"
              >
                {/* Nombre y Cargo */}
                <td className="px-4 py-3 font-medium text-card-foreground">
                  <div>
                    <div className="font-bold text-foreground">{worker.full_name}</div>
                    <div className="text-[11px] text-muted-foreground font-mono">
                      {worker.role_name} • {worker.email}
                    </div>
                  </div>
                </td>

                {/* Switch Acceso OppyFy */}
                <td className="px-4 py-3">
                  <button
                    type="button"
                    data-testid={`toggle-worker-oppyfy-${worker.user_id}`}
                    onClick={() => handleToggleWorkerEnabled(worker)}
                    className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border px-3 py-1 text-xs font-semibold transition-colors ${
                      worker.is_oppyfy_enabled
                        ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                        : "border-border bg-card text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {worker.is_oppyfy_enabled ? (
                      <>
                        <CheckCircle className="h-3.5 w-3.5" />
                        <span>{translateKey("oppyfy", "governance.wallets.status_enabled")}</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3.5 w-3.5" />
                        <span>{translateKey("oppyfy", "governance.wallets.status_disabled")}</span>
                      </>
                    )}
                  </button>
                </td>

                {/* Cupo Asignado */}
                <td className="px-4 py-3 font-mono font-bold text-card-foreground">
                  <div className="flex items-center gap-1">
                    <Coins className="h-3.5 w-3.5 text-primary" />
                    <span>{worker.assigned_credit_ceiling} cr.</span>
                  </div>
                </td>

                {/* Consumido */}
                <td className="px-4 py-3 font-mono text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <TrendingDown className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{worker.consumed_credits_total} cr.</span>
                  </div>
                </td>

                {/* Saldo Restante */}
                <td className="px-4 py-3 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                  <span>{worker.remaining_credits} cr.</span>
                </td>

                {/* Acciones */}
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    data-testid={`btn-edit-worker-wallet-${worker.user_id}`}
                    onClick={() => setSelectedWorkerForEdit(worker)}
                    className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-card-foreground transition-colors hover:bg-muted"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                    <span>{translateKey("oppyfy", "governance.wallets.edit_ceiling_btn")}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal Editar Cupo */}
      <EditWorkerWalletModal
        isOpen={selectedWorkerForEdit !== null}
        worker={selectedWorkerForEdit}
        onClose={() => setSelectedWorkerForEdit(null)}
        onSave={onUpdateWorkerWallet}
      />

      {/* Modal Comprar Paquetes */}
      <BuyCreditPackModal
        isOpen={isBuyModalOpen}
        packs={aiPacks}
        onClose={() => setIsBuyModalOpen(false)}
        onQuotePack={onQuotePack}
      />
    </div>
  );
}
