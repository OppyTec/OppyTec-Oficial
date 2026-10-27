/**
 * oppytec-frontend/src/features/oppyfy/components/governance/OppyfyGovernancePanel.tsx
 * Panel Central de Gobernanza y RBAC Exclusivo de OppyFy (v2.0):
 * 1) Árbol de Dominios y Subdominios (OppyfyDomainTreeEditor)
 * 2) Permisos Temporales con triple control de caducidad (OppyfyTemporaryGrantsManager)
 * 3) Billetera de Créditos & Cupos por Trabajador (OppyfyWorkerWalletsManager)
 * 4) Visor de Auditoría de Prompts (OppyfyPromptAuditLogViewer)
 * - Mobile-first con touch targets >= 44px
 * - Soporte a 3 temas (light, dark, ocean-blue)
 * - Cero hardcoding vía i18n
 */

import { useState } from "react";
import {
  FolderTree,
  KeyRound,
  WalletCards,
  FileCheck2,
  ShieldCheck,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { OppyfyGovernanceTab } from "../../types";
import { useOppyfyGovernance } from "../../hooks";
import { OppyfyDomainTreeEditor } from "./OppyfyDomainTreeEditor";
import { OppyfyTemporaryGrantsManager } from "./OppyfyTemporaryGrantsManager";
import { OppyfyWorkerWalletsManager } from "./OppyfyWorkerWalletsManager";
import { OppyfyPromptAuditLogViewer } from "./OppyfyPromptAuditLogViewer";

export interface OppyfyGovernancePanelProps {
  readonly initialTab?: OppyfyGovernanceTab;
  readonly onTabChange?: (tab: OppyfyGovernanceTab) => void;
}

export function OppyfyGovernancePanel({
  initialTab = "domains",
  onTabChange,
}: OppyfyGovernancePanelProps = {}) {
  const [activeTab, setActiveTab] = useState<OppyfyGovernanceTab>(initialTab);

  const gov = useOppyfyGovernance();

  const handleSelectTab = (tab: OppyfyGovernanceTab) => {
    setActiveTab(tab);
    onTabChange?.(tab);
  };

  return (
    <div
      data-testid="oppyfy-governance-panel"
      className="flex flex-col space-y-6"
    >
      {/* Encabezado del Panel */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2 text-primary">
            <ShieldCheck className="h-6 w-6" />
            <h2 className="text-lg font-bold text-card-foreground">
              {translateKey("oppyfy", "governance.title")}
            </h2>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {translateKey("oppyfy", "governance.subtitle")}
          </p>
        </div>

        {/* Resumen Rápido de Estado */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="rounded-lg border border-border bg-secondary/30 px-3 py-1 text-xs">
            <span className="text-muted-foreground">Bolsa Global: </span>
            <span className="font-bold text-foreground">
              {gov.tenantCreditBag.remaining_pool_credits.toFixed(0)} cr.
            </span>
          </div>
          <div className="rounded-lg border border-border bg-secondary/30 px-3 py-1 text-xs">
            <span className="text-muted-foreground">Permisos Activos: </span>
            <span className="font-bold text-primary">
              {gov.grants.filter((g) => g.is_active).length}
            </span>
          </div>
        </div>
      </div>

      {/* Navegación por Pestañas Internas (Accessible Tabs) */}
      <div
        role="tablist"
        aria-label="Pestañas de Gobernanza OppyFy"
        className="flex flex-wrap gap-2 border-b border-border pb-2"
      >
        {/* Tab 1: Árbol de Dominios */}
        <button
          type="button"
          role="tab"
          id="gov-tab-domains"
          aria-selected={activeTab === "domains"}
          aria-controls="gov-panel-domains"
          data-testid="tab-gov-domains"
          onClick={() => handleSelectTab("domains")}
          className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
            activeTab === "domains"
              ? "border border-primary bg-primary/15 text-primary shadow-sm"
              : "border border-transparent bg-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
          }`}
        >
          <FolderTree className="h-4 w-4" />
          <span>{translateKey("oppyfy", "governance.tabs.domains")}</span>
        </button>

        {/* Tab 2: Permisos Temporales */}
        <button
          type="button"
          role="tab"
          id="gov-tab-grants"
          aria-selected={activeTab === "grants"}
          aria-controls="gov-panel-grants"
          data-testid="tab-gov-grants"
          onClick={() => handleSelectTab("grants")}
          className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
            activeTab === "grants"
              ? "border border-primary bg-primary/15 text-primary shadow-sm"
              : "border border-transparent bg-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
          }`}
        >
          <KeyRound className="h-4 w-4" />
          <span>{translateKey("oppyfy", "governance.tabs.grants")}</span>
        </button>

        {/* Tab 3: Billeteras & Cupos */}
        <button
          type="button"
          role="tab"
          id="gov-tab-wallets"
          aria-selected={activeTab === "wallets"}
          aria-controls="gov-panel-wallets"
          data-testid="tab-gov-wallets"
          onClick={() => handleSelectTab("wallets")}
          className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
            activeTab === "wallets"
              ? "border border-primary bg-primary/15 text-primary shadow-sm"
              : "border border-transparent bg-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
          }`}
        >
          <WalletCards className="h-4 w-4" />
          <span>{translateKey("oppyfy", "governance.tabs.wallets")}</span>
        </button>

        {/* Tab 4: Auditoría de Prompts */}
        <button
          type="button"
          role="tab"
          id="gov-tab-audit"
          aria-selected={activeTab === "audit"}
          aria-controls="gov-panel-audit"
          data-testid="tab-gov-audit"
          onClick={() => handleSelectTab("audit")}
          className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
            activeTab === "audit"
              ? "border border-primary bg-primary/15 text-primary shadow-sm"
              : "border border-transparent bg-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
          }`}
        >
          <FileCheck2 className="h-4 w-4" />
          <span>{translateKey("oppyfy", "governance.tabs.audit")}</span>
        </button>
      </div>

      {/* Contenido de la pestaña activa */}
      <div className="pt-2">
        {activeTab === "domains" && (
          <div
            id="gov-panel-domains"
            role="tabpanel"
            aria-labelledby="gov-tab-domains"
          >
            <OppyfyDomainTreeEditor
              domains={gov.domains}
              onCreateDomain={gov.createDomain}
              onToggleSubdomainActive={gov.toggleSubdomainActive}
              onToggleSubdomainCanViewCosts={gov.toggleSubdomainCanViewCosts}
              isCreatingDomain={gov.isCreatingDomain}
            />
          </div>
        )}

        {activeTab === "grants" && (
          <div
            id="gov-panel-grants"
            role="tabpanel"
            aria-labelledby="gov-tab-grants"
          >
            <OppyfyTemporaryGrantsManager
              grants={gov.grants}
              domains={gov.domains}
              workers={gov.workers}
              onGrantPermission={gov.createGrant}
              onRevokeGrant={gov.revokeGrant}
              isGranting={gov.isCreatingGrant}
            />
          </div>
        )}

        {activeTab === "wallets" && (
          <div
            id="gov-panel-wallets"
            role="tabpanel"
            aria-labelledby="gov-tab-wallets"
          >
            <OppyfyWorkerWalletsManager
              workers={gov.workers}
              tenantCreditBag={gov.tenantCreditBag}
              aiPacks={gov.aiPacks}
              onUpdateWorkerWallet={gov.updateWorkerWallet}
              onQuotePack={gov.quotePack}
            />
          </div>
        )}

        {activeTab === "audit" && (
          <div
            id="gov-panel-audit"
            role="tabpanel"
            aria-labelledby="gov-tab-audit"
          >
            <OppyfyPromptAuditLogViewer auditLogs={gov.auditLogs} />
          </div>
        )}
      </div>
    </div>
  );
}
