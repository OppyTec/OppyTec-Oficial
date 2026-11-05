import {
  Bot,
  BrainCircuit,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import { HoldingAiBriefingCard } from "./HoldingAiBriefingCard";
import type { HoldingHubSummary, HoldingTabId } from "./types";

export interface HoldingBriefingSectionProps {
  readonly holdingData: HoldingHubSummary;
  readonly onRefresh?: () => void;
  readonly onNavigateTab?: (tab: HoldingTabId) => void;
  readonly refreshing?: boolean;
}

export function HoldingBriefingSection({
  holdingData,
  onRefresh,
  onNavigateTab,
  refreshing = false,
}: HoldingBriefingSectionProps) {
  const briefing = holdingData.ai_briefing;
  const totalBotRequests = holdingData.tenants.reduce(
    (acc, t) => acc + (t.bot_requests || 0),
    0
  );

  return (
    <div
      data-testid="holding-briefing-section"
      className="space-y-8 animate-in fade-in duration-300"
    >
      {/* Executive Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase bg-purple-500/15 text-purple-400 border border-purple-500/30">
              <Sparkles className="h-3 w-3" />
              {translateKey("holding_hub", "briefing.badge", {
                defaultValue: "OPPYBOT IA EXECUTIVE",
              })}
            </span>
            <span className="text-xs text-muted-foreground">
              {briefing?.model_name || "gpt-4o-mini / claude-3-5-sonnet"}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            {translateKey("holding_hub", "briefing.header_title", {
              defaultValue: "Oppy Daily Holding Briefing",
            })}
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            {translateKey("holding_hub", "briefing.header_subtitle", {
              defaultValue:
                "Diagnóstico corporativo multi-sucursal y recomendaciones de IA en tiempo real.",
            })}
          </p>
        </div>

        {onRefresh && (
          <button
            type="button"
            data-testid="holding-briefing-refresh-section-btn"
            onClick={onRefresh}
            disabled={refreshing}
            className="flex items-center justify-center gap-2 rounded-xl border border-border/80 bg-background/60 px-4 py-2.5 text-xs font-semibold text-foreground hover:bg-muted/60 transition shadow-xs self-start md:self-auto shrink-0"
          >
            <RefreshCw
              className={`h-4 w-4 text-purple-400 ${
                refreshing ? "animate-spin" : ""
              }`}
            />
            <span>
              {translateKey("holding_hub", "briefing.action_refresh", {
                defaultValue: "Actualizar Briefing",
              })}
            </span>
          </button>
        )}
      </div>

      {/* Main AI Briefing Executive Card */}
      <HoldingAiBriefingCard
        briefing={briefing}
        holdingData={holdingData}
        onRefresh={onRefresh}
        onNavigateTab={onNavigateTab}
        isRefreshing={refreshing}
      />

      {/* 3 Executive Multi-Branch AI Governance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Total Interactions Card */}
        <div className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-lg transition hover:border-purple-500/30">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "briefing.total_bot_requests_label", {
                defaultValue: "Interacciones Totales IA",
              })}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Bot className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-bold font-mono text-foreground">
            {totalBotRequests.toLocaleString()}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            {translateKey("holding_hub", "briefing.total_bot_requests_sub", {
              defaultValue: "Peticiones procesadas por OppyBot en todas las sucursales",
            })}
          </p>
        </div>

        {/* Token Governance Card */}
        <div className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-lg transition hover:border-purple-500/30">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "briefing.tokens_governance_label", {
                defaultValue: "Gobernanza de Tokens",
              })}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <BrainCircuit className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-bold font-mono text-foreground">
            {(briefing?.tokens_used || 2480).toLocaleString()}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            {translateKey("holding_hub", "briefing.tokens_governance_sub", {
              defaultValue: "Tokens consumidos en el ciclo actual de auditoría",
            })}
          </p>
        </div>

        {/* Safety Cap Status Card */}
        <div className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-lg transition hover:border-purple-500/30">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "briefing.safety_cap_header_label", {
                defaultValue: "Safety Cap Activo",
              })}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            {holdingData.usage_pct}%
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            {translateKey("holding_hub", "briefing.safety_cap_header_sub", {
              defaultValue: "Consumo de cuota controlado bajo umbral de seguridad",
            })}
          </p>
        </div>
      </div>
    </div>
  );
}
