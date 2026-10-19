import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { getRuntimeEnv } from "@/shared/config/env";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

export interface OppyFyRbacDomainConfig {
  readonly domain: string;
  readonly subdomain: string;
  readonly enabledForRole: boolean;
}

const INITIAL_OPPYFY_DOMAINS: readonly OppyFyRbacDomainConfig[] = [
  { domain: "inventory", subdomain: "kardex_valuation", enabledForRole: true },
  { domain: "recipes", subdomain: "escandallo_margins", enabledForRole: true },
  { domain: "procurement", subdomain: "supplier_dte_prices", enabledForRole: true },
  { domain: "finance", subdomain: "holding_ebitda", enabledForRole: false },
];

export function OppyFyFeatureView() {
  const env = getRuntimeEnv();
  const [promptText, setPromptText] = useState<string>(
    "¿Cuál es la brecha de costo real vs teórico en Pollo King esta semana?"
  );
  const [contextUsagePct] = useState<number>(34);
  const [creditsRemaining, setCreditsRemaining] = useState<number>(1420);
  const [domains, setDomains] = useState<readonly OppyFyRbacDomainConfig[]>(
    INITIAL_OPPYFY_DOMAINS
  );

  const toggleDomain = (index: number): void => {
    setDomains((prev) =>
      prev.map((item, idx) =>
        idx === index
          ? { ...item, enabledForRole: !item.enabledForRole }
          : item
      )
    );
  };

  const handleExecuteQuery = (): void => {
    setCreditsRemaining((prev) => (prev > 0 ? prev - 1 : 0));
  };

  return (
    <section
      data-testid="feature-oppyfy"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("oppyfy", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("oppyfy", "chat.jev_fast_path", { ms: 4 })}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            data-testid="oppyfy-context-meter"
            className="rounded-lg border border-border bg-secondary px-2.5 py-1 font-mono text-xs font-semibold text-foreground"
          >
            {`Contexto RAG: ${String(contextUsagePct)}%`}
          </span>
          <span
            data-testid="oppyfy-credit-wallet"
            className="rounded-lg bg-primary/15 px-3 py-1 font-mono text-xs font-bold text-primary"
          >
            {translateKey("oppyfy", "chat.credits_remaining", {
              credits: creditsRemaining,
            })}
            {" (Sin vencimiento)"}
          </span>
        </div>
      </div>

      {/* Split-View Workspace: Chat + Canvas Analítico */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div
          data-testid="oppyfy-chat-pane"
          className="space-y-3 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <label className="block text-xs font-bold uppercase text-muted-foreground">
            {translateKey("oppyfy", "chat.placeholder", {
              brandName: env.VITE_AI_ASSISTANT_BRAND_NAME,
            })}
          </label>
          <input
            type="text"
            aria-label="Prompt OppyFy"
            data-testid="oppyfy-prompt-input"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            className="touch-target min-h-[44px] w-full rounded-md border border-border bg-card px-3 text-xs text-foreground"
          />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">
              {translateKey("oppyfy", "governance.rbac_filtered", {
                role: "Gerente Operaciones",
              })}
            </span>
            <Can perform="oppyfy.workspace.query">
              <button
                type="button"
                data-testid="oppyfy-send-btn"
                onClick={handleExecuteQuery}
                className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground"
              >
                Consultar OppyFy
              </button>
            </Can>
          </div>
        </div>

        <div
          data-testid="oppyfy-split-canvas"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-muted-foreground">
              Split-View Canvas (Tablas, Gráficos & Citaciones RAG 3-Capas)
            </h3>
            <span className="font-mono text-[11px] text-primary">
              {translateKey("oppyfy", "governance.citations_count", {
                count: 3,
              })}
            </span>
          </div>
          <div className="rounded-lg border border-border bg-card p-2.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold">Pollo King (Lote FEFO #882)</span>
              <MoneyBadge amount="4890" baseCurrency="CLP" />
            </div>
            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
              llm_request_logs: model=gemini-3.8-flash · tokens=412 · cost_usd=0.00042000
            </p>
          </div>
        </div>
      </div>

      {/* Matriz RBAC Propia y Editable de OppyFy */}
      <div
        data-testid="oppyfy-rbac-domains"
        className="rounded-xl border border-border bg-secondary/20 p-3"
      >
        <h3 className="mb-2 text-xs font-bold uppercase text-muted-foreground">
          RBAC Propio Editable de OppyFy (Dominios & Subdominios Autorizados)
        </h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-4">
          {domains.map((d, idx) => (
            <button
              key={`${d.domain}.${d.subdomain}`}
              type="button"
              data-testid={`oppyfy-domain-toggle-${d.domain}-${d.subdomain}`}
              onClick={() => toggleDomain(idx)}
              className={`touch-target flex min-h-[44px] items-center justify-between rounded-lg border px-3 py-2 text-xs font-mono ${
                d.enabledForRole
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border bg-card text-muted-foreground"
              }`}
            >
              <span>{`${d.domain}.${d.subdomain}`}</span>
              <span>{d.enabledForRole ? "ON" : "OFF"}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
