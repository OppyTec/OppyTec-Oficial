import { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Coins,
  Cpu,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type {
  HoldingBriefingResponse,
  HoldingHubSummary,
  HoldingTabId,
  SafetyStatus,
} from "./types";

export interface HoldingAiBriefingCardProps {
  readonly briefing?: HoldingBriefingResponse | null;
  readonly holdingData: HoldingHubSummary;
  readonly onRefresh?: () => void;
  readonly onNavigateTab?: (tab: HoldingTabId) => void;
  readonly isRefreshing?: boolean;
}

export function HoldingAiBriefingCard({
  briefing,
  holdingData,
  onRefresh,
  onNavigateTab,
  isRefreshing = false,
}: HoldingAiBriefingCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  // Fallback briefing from holdingData if direct briefing prop is not supplied
  const effectiveBriefing: HoldingBriefingResponse | null =
    briefing ?? holdingData.ai_briefing ?? null;

  if (!effectiveBriefing) {
    return null;
  }

  const safetyStatus: SafetyStatus =
    effectiveBriefing.safety_cap_prediction?.status || holdingData.safety_status;

  const getSafetyBadgeConfig = (status: SafetyStatus) => {
    switch (status) {
      case "CRITICAL":
        return {
          label: translateKey("holding_hub", "briefing.status_critical", {
            defaultValue: "Riesgo Crítico",
          }),
          color: "text-rose-500",
          bgColor: "bg-rose-500/10",
          borderColor: "border-rose-500/30",
          dotColor: "bg-rose-500",
          icon: ShieldAlert,
        };
      case "WARNING":
        return {
          label: translateKey("holding_hub", "briefing.status_warning", {
            defaultValue: "Atención Requerida",
          }),
          color: "text-amber-500",
          bgColor: "bg-amber-500/10",
          borderColor: "border-amber-500/30",
          dotColor: "bg-amber-500",
          icon: AlertTriangle,
        };
      case "NORMAL":
      default:
        return {
          label: translateKey("holding_hub", "briefing.status_healthy", {
            defaultValue: "Salud Operativa Óptima",
          }),
          color: "text-emerald-500",
          bgColor: "bg-emerald-500/10",
          borderColor: "border-emerald-500/30",
          dotColor: "bg-emerald-500",
          icon: ShieldCheck,
        };
    }
  };

  const badgeConfig = getSafetyBadgeConfig(safetyStatus);
  const SafetyIcon = badgeConfig.icon;

  return (
    <section
      data-testid="holding-ai-briefing-card"
      className="relative overflow-hidden rounded-2xl border border-primary/25 bg-gradient-to-br from-card/90 via-card/75 to-primary/5 p-5 md:p-6 backdrop-blur-2xl shadow-xl transition-all duration-300 hover:border-primary/40 group"
      aria-label={translateKey("holding_hub", "briefing.executive_title", {
        defaultValue: "Oppy Daily Holding Briefing",
      })}
    >
      {/* Ambient background glow */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-primary/10 blur-3xl transition-opacity duration-500 group-hover:opacity-80" />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary border border-primary/25 shadow-xs">
            <Sparkles className="h-5 w-5 animate-pulse" />
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-lg md:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                {translateKey("holding_hub", "briefing.executive_title", {
                  defaultValue: "Oppy Daily Holding Briefing",
                })}
              </h2>
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider text-primary border border-primary/20">
                <Bot className="h-3 w-3" />
                {translateKey("holding_hub", "briefing.executive_badge", {
                  defaultValue: "OPPYFY IA EXECUTIVE",
                })}
              </span>
              <span className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-0.5 text-[10px] font-mono font-medium text-muted-foreground border border-border/50">
                <Cpu className="h-2.5 w-2.5" />
                {effectiveBriefing.model_name}
              </span>
            </div>

            <p className="text-xs text-muted-foreground mt-0.5">
              {translateKey("holding_hub", "briefing.subtitle", {
                defaultValue: "Diagnóstico corporativo multi-sucursal en tiempo real",
              })}
            </p>
          </div>
        </div>

        {/* Right action controls & Safety badge */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          {/* Safety Cap Status Badge */}
          <div
            data-testid="holding-ai-briefing-safety-badge"
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${badgeConfig.bgColor} ${badgeConfig.color} ${badgeConfig.borderColor} shadow-xs`}
          >
            <span
              className={`h-2 w-2 rounded-full ${badgeConfig.dotColor} animate-ping opacity-75`}
            />
            <SafetyIcon className="h-3.5 w-3.5" />
            <span>{badgeConfig.label}</span>
          </div>

          {/* Quick Refresh Button */}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={isRefreshing}
              data-testid="holding-ai-briefing-refresh-btn"
              title={translateKey("holding_hub", "briefing.action_refresh", {
                defaultValue: "Actualizar Briefing",
              })}
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-border/70 bg-background/60 text-muted-foreground hover:text-foreground hover:bg-background transition-colors disabled:opacity-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
              />
            </button>
          )}

          {/* Toggle Expand/Collapse Button */}
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            data-testid="holding-ai-briefing-toggle"
            className="flex items-center gap-1.5 rounded-xl border border-border/70 bg-background/60 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-background hover:border-primary/40 transition-colors shadow-xs"
          >
            {isExpanded ? (
              <>
                <span>
                  {translateKey("holding_hub", "briefing.toggle_collapse", {
                    defaultValue: "Colapsar análisis",
                  })}
                </span>
                <ChevronUp className="h-3.5 w-3.5" />
              </>
            ) : (
              <>
                <span>
                  {translateKey("holding_hub", "briefing.toggle_expand", {
                    defaultValue: "Ver análisis completo",
                  })}
                </span>
                <ChevronDown className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Collapsed Teaser View */}
      {!isExpanded && (
        <div className="mt-3 pt-3 border-t border-border/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-muted-foreground">
          <p className="line-clamp-1 italic font-serif">
            &ldquo;{effectiveBriefing.summary_paragraphs[0]}&rdquo;
          </p>
          <span className="text-[11px] font-mono shrink-0 text-primary">
            {translateKey("holding_hub", "briefing.tokens_label", {
              tokens: effectiveBriefing.tokens_used,
            })}{" "}
            •{" "}
            {translateKey("holding_hub", "briefing.credits_label", {
              credits: effectiveBriefing.credits_deducted,
            })}
          </span>
        </div>
      )}

      {/* Expanded Comprehensive Briefing View */}
      {isExpanded && (
        <div
          data-testid="holding-ai-briefing-content"
          className="mt-5 space-y-6 animate-in fade-in slide-in-from-top-2 duration-300"
        >
          {/* Two Structured Executive Paragraphs */}
          <div className="space-y-3.5 rounded-xl border border-border/60 bg-background/50 p-4 md:p-5 shadow-xs">
            <div
              data-testid="holding-ai-briefing-paragraph-0"
              className="text-xs md:text-sm leading-relaxed text-foreground/90 text-justify"
            >
              <span className="font-semibold text-primary mr-1">
                [{translateKey("holding_hub", "briefing.category_sales_waste")}]:
              </span>
              {effectiveBriefing.summary_paragraphs[0]}
            </div>

            <div
              data-testid="holding-ai-briefing-paragraph-1"
              className="text-xs md:text-sm leading-relaxed text-foreground/90 text-justify pt-2 border-t border-border/40"
            >
              <span className="font-semibold text-primary mr-1">
                [{translateKey("holding_hub", "briefing.category_credits_safety")}]:
              </span>
              {effectiveBriefing.summary_paragraphs[1]}
            </div>
          </div>

          {/* Highlights & Cost Alerts Dual Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Key Achievements Column */}
            <div
              data-testid="holding-ai-briefing-achievements"
              className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-2.5"
            >
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                <span>
                  {translateKey(
                    "holding_hub",
                    "briefing.achievements_title",
                    {
                      defaultValue: "Aciertos y Fortalezas Operativas",
                    }
                  )}
                </span>
              </div>
              <ul className="space-y-2 text-xs text-foreground/80">
                {effectiveBriefing.key_achievements.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-500 font-bold shrink-0 mt-0.5">
                      ✓
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Cost & Waste Alerts Column */}
            <div
              data-testid="holding-ai-briefing-alerts"
              className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-2.5"
            >
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                <span>
                  {translateKey("holding_hub", "briefing.alerts_title", {
                    defaultValue: "Alertas de Merma y Costos",
                  })}
                </span>
              </div>
              <ul className="space-y-2 text-xs text-foreground/80">
                {effectiveBriefing.cost_alerts.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-500 font-bold shrink-0 mt-0.5">
                      ⚠
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Safety Cap Predictive Box */}
          <div className="rounded-xl border border-border/80 bg-gradient-to-r from-card/90 via-card/70 to-primary/10 p-4 md:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
            <div className="space-y-1.5 max-w-2xl">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-primary" />
                  {translateKey(
                    "holding_hub",
                    "briefing.safety_cap_title",
                    {
                      defaultValue: "Proyección Predictiva Safety Cap",
                    }
                  )}
                </span>
                <span className="text-xs font-mono font-semibold text-primary">
                  {effectiveBriefing.safety_cap_prediction.estimated_days_remaining !== null
                    ? translateKey("holding_hub", "briefing.autonomy_days", {
                        days: effectiveBriefing.safety_cap_prediction.estimated_days_remaining,
                        defaultValue: `~${effectiveBriefing.safety_cap_prediction.estimated_days_remaining} días restantes`,
                      })
                    : translateKey("holding_hub", "briefing.autonomy_indefinite", {
                        defaultValue: "Autonomía indefinida",
                      })}
                </span>
              </div>
              <p className="text-xs md:text-sm text-foreground/90 font-medium">
                {effectiveBriefing.safety_cap_prediction.recommendation}
              </p>
              <div className="flex items-center gap-4 text-[11px] font-mono text-muted-foreground pt-1">
                <span>
                  {translateKey("holding_hub", "briefing.burn_rate_label", {
                    defaultValue: "Burn Rate",
                  })}:{" "}
                  <strong className="text-foreground font-semibold">
                    {effectiveBriefing.safety_cap_prediction.burn_rate_daily}
                  </strong>{" "}
                  {translateKey("holding_hub", "briefing.credits_per_day", {
                    defaultValue: "créditos/día",
                  })}
                </span>
                <span>•</span>
                <span>
                  {translateKey("holding_hub", "briefing.pool_available", {
                    defaultValue: "Bolsa disponible",
                  })}:{" "}
                  <strong className="text-foreground font-semibold">
                    {holdingData.credit_balance.toLocaleString()}
                  </strong>
                </span>
              </div>
            </div>

            {/* Quick Action Navigation Buttons */}
            {onNavigateTab && (
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => onNavigateTab("creditos")}
                  data-testid="holding-briefing-manage-credits-btn"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-sm group"
                >
                  <Coins className="h-3.5 w-3.5" />
                  <span>
                    {translateKey(
                      "holding_hub",
                      "briefing.action_manage_credits",
                      { defaultValue: "Gestionar Cuotas de IA" }
                    )}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </button>
              </div>
            )}
          </div>

          {/* Footer Metadata */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/40 text-[11px] font-mono text-muted-foreground">
            <div className="flex items-center gap-3">
              <span>
                {translateKey("holding_hub", "briefing.tokens_label", {
                  tokens: effectiveBriefing.tokens_used,
                  defaultValue: `${effectiveBriefing.tokens_used} tokens LLM`,
                })}
              </span>
              <span>•</span>
              <span>
                {translateKey("holding_hub", "briefing.credits_label", {
                  credits: effectiveBriefing.credits_deducted,
                  defaultValue: `${effectiveBriefing.credits_deducted} crédito deducido`,
                })}
              </span>
            </div>
            <span>
              {translateKey("holding_hub", "briefing.generated_at", {
                defaultValue: "Generado",
              })}:{" "}
              {new Date(effectiveBriefing.generated_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
