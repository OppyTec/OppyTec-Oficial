import { useState } from "react";
import { Check, Sparkles, Star, Zap } from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";
import { SAAS_PLANS } from "./constants";
import type { HoldingHubSummary, SaaSPlanTier } from "./types";

export interface HoldingPlansSectionProps {
  readonly holdingData: HoldingHubSummary;
  readonly onChangePlan: (
    newPlanSlug: string,
    immediate: boolean,
    reason?: string
  ) => Promise<boolean>;
}

export function HoldingPlansSection({
  holdingData,
  onChangePlan,
}: HoldingPlansSectionProps) {
  const { currency, convertAndFormat } = useCurrencyFormatter();
  const [selectedPlanForModal, setSelectedPlanForModal] =
    useState<SaaSPlanTier | null>(null);
  const [immediate, setImmediate] = useState<boolean>(true);
  const [reason, setReason] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleConfirmPlanChange = async () => {
    if (!selectedPlanForModal) return;
    setIsSubmitting(true);
    try {
      const ok = await onChangePlan(
        selectedPlanForModal.slug,
        immediate,
        reason.trim() || undefined
      );
      if (ok) {
        setSuccessMessage(
          translateKey("holding_hub", "plans.change_success", {
            plan: translateKey("holding_hub", selectedPlanForModal.nameKey),
          })
        );
        setSelectedPlanForModal(null);
        setReason("");
        setTimeout(() => setSuccessMessage(null), 5000);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      data-testid="holding-plans-section"
      className="space-y-8 animate-in fade-in duration-300"
    >
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
          {translateKey("holding_hub", "plans.header_title")}
        </h2>
        <p className="text-xs md:text-sm text-muted-foreground">
          {translateKey("holding_hub", "plans.header_subtitle")}
        </p>
      </div>

      {/* Success banner */}
      {successMessage && (
        <div
          data-testid="plan-change-success-banner"
          className="mx-auto max-w-2xl rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-center text-sm font-semibold text-emerald-500 animate-in fade-in zoom-in-95"
        >
          {successMessage}
        </div>
      )}

      {/* Plans Catalog Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 max-w-6xl mx-auto items-stretch">
        {SAAS_PLANS.map((plan) => {
          const isActive = holdingData.active_plan_slug === plan.slug;
          const isRecommended = Boolean(plan.recommended);

          return (
            <div
              key={plan.slug}
              data-testid={`saas-plan-card-${plan.slug}`}
              className={`relative flex flex-col justify-between rounded-3xl border p-6 md:p-8 backdrop-blur-xl transition-all duration-300 shadow-xl ${
                isActive
                  ? "border-primary bg-card/80 ring-2 ring-primary/40 shadow-primary/10"
                  : isRecommended
                  ? "border-cyan-500/50 bg-card/70 hover:border-cyan-400"
                  : "border-border/70 bg-card/50 hover:border-border"
              }`}
            >
              {/* Badges Header */}
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 flex items-center gap-2">
                {isRecommended && (
                  <span
                    data-testid={`recommended-plan-badge-${plan.slug}`}
                    className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 px-3.5 py-1 text-xs font-bold text-white shadow-md shadow-cyan-500/25 uppercase tracking-wider"
                  >
                    <Star className="h-3.5 w-3.5 fill-white" />
                    {translateKey("holding_hub", "plans.recommended")}
                  </span>
                )}
                {isActive && (
                  <span
                    data-testid={`active-plan-badge-${plan.slug}`}
                    className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-1 text-xs font-bold text-primary-foreground shadow-md shadow-primary/30 uppercase tracking-wider"
                  >
                    <Check className="h-3.5 w-3.5" />
                    {translateKey("holding_hub", "plans.active_badge")}
                  </span>
                )}
              </div>

              <div>
                {/* Plan Name & Description */}
                <div className="mt-2 text-center">
                  <h3 className="text-xl font-bold text-foreground">
                    {translateKey("holding_hub", plan.nameKey)}
                  </h3>
                  <p className="mt-2 text-xs text-muted-foreground min-h-[36px]">
                    {translateKey("holding_hub", plan.descKey)}
                  </p>
                </div>

                {/* Dual Pricing Display */}
                <div className="mt-6 text-center border-y border-border/60 py-4 bg-muted/20 rounded-2xl">
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="text-3xl font-extrabold tracking-tight text-foreground font-mono">
                      {convertAndFormat(plan.priceClp, "CLP", currency)}
                    </span>
                    <span className="text-xs text-muted-foreground font-medium">
                      {translateKey("holding_hub", "plans.per_month")}
                    </span>
                  </div>
                  <div className="mt-1 text-xs font-mono font-semibold text-muted-foreground">
                    {currency === "CLP"
                      ? `≈ ${convertAndFormat(plan.priceClp, "CLP", "USD")} USD ${translateKey("holding_hub", "plans.per_month")}`
                      : `≈ ${convertAndFormat(plan.priceClp, "CLP", "CLP")} CLP ${translateKey("holding_hub", "plans.per_month")}`}
                  </div>
                </div>

                {/* Monthly AI Credits Highlight */}
                <div className="mt-5 rounded-2xl border border-primary/20 bg-primary/5 p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-primary" />
                    <span className="text-xs font-medium text-foreground">
                      {translateKey("holding_hub", "plans.monthly_ai_credits")}
                    </span>
                  </div>
                  <span className="font-mono text-xs font-bold text-primary">
                    {plan.monthlyCredits.toLocaleString()}
                  </span>
                </div>

                {/* Modules & Perks List */}
                <div className="mt-6 space-y-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                    {translateKey("holding_hub", "plans.features_included")}
                  </span>
                  <ul className="space-y-2.5 text-xs text-foreground/90">
                    {plan.perks.map((perk) => (
                      <li key={perk} className="flex items-center gap-2.5">
                        <div className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-500 shrink-0">
                          <Check className="h-2.5 w-2.5" />
                        </div>
                        <span className="font-semibold">{perk}</span>
                      </li>
                    ))}
                    {plan.modules.map((mod) => (
                      <li key={mod} className="flex items-center gap-2.5 text-muted-foreground">
                        <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                        <span>{mod}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Button */}
              <div className="mt-8 pt-4 border-t border-border/60">
                {isActive ? (
                  <button
                    type="button"
                    disabled
                    data-testid={`plan-action-active-${plan.slug}`}
                    className="w-full rounded-xl border border-primary/40 bg-primary/10 py-3 text-xs font-bold text-primary cursor-default"
                  >
                    {translateKey("holding_hub", "plans.current_plan_action")}
                  </button>
                ) : (
                  <button
                    type="button"
                    data-testid={`plan-action-subscribe-${plan.slug}`}
                    onClick={() => {
                      setSelectedPlanForModal(plan);
                      setImmediate(true);
                      setReason("");
                    }}
                    className={`w-full rounded-xl py-3 text-xs font-bold transition shadow-md focus:outline-none ${
                      isRecommended
                        ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:opacity-95 shadow-cyan-500/20"
                        : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-primary/20"
                    }`}
                  >
                    {translateKey("holding_hub", "plans.subscribe_action")}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Confirmation Modal */}
      {selectedPlanForModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={translateKey("holding_hub", "plans.modal_confirm_title")}
          data-testid="plan-change-modal"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setSelectedPlanForModal(null)}
        >
          <div
            className="relative w-full max-w-lg rounded-3xl border border-border bg-card p-6 md:p-8 shadow-2xl backdrop-blur-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/20 text-primary">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">
                  {translateKey("holding_hub", "plans.modal_confirm_title")}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {translateKey("holding_hub", selectedPlanForModal.nameKey)}
                </p>
              </div>
            </div>

            <p className="mt-4 text-xs md:text-sm text-foreground/80 leading-relaxed">
              {translateKey("holding_hub", "plans.modal_confirm_desc", {
                plan: translateKey("holding_hub", selectedPlanForModal.nameKey),
              })}
            </p>

            {/* Effective Option Radios */}
            <div className="mt-5 space-y-2.5">
              <label
                className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition ${
                  immediate
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border bg-muted/30 text-muted-foreground"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <input
                    type="radio"
                    name="effective_mode"
                    data-testid="plan-effective-immediate"
                    checked={immediate}
                    onChange={() => setImmediate(true)}
                    className="accent-primary"
                  />
                  <span className="text-xs font-semibold">
                    {translateKey("holding_hub", "plans.effective_immediately")}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-primary font-bold">
                  {translateKey("holding_hub", "plans.radio_today")}
                </span>
              </label>

              <label
                className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition ${
                  !immediate
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border bg-muted/30 text-muted-foreground"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <input
                    type="radio"
                    name="effective_mode"
                    data-testid="plan-effective-next-cycle"
                    checked={!immediate}
                    onChange={() => setImmediate(false)}
                    className="accent-primary"
                  />
                  <span className="text-xs font-semibold">
                    {translateKey("holding_hub", "plans.effective_next_cycle")}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-muted-foreground">
                  {translateKey("holding_hub", "plans.radio_cycle_end")}
                </span>
              </label>
            </div>

            {/* Reason Textarea */}
            <div className="mt-4">
              <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
                {translateKey("holding_hub", "plans.reason_label")}
              </label>
              <textarea
                rows={3}
                data-testid="plan-change-reason-input"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={translateKey("holding_hub", "plans.reason_placeholder")}
                className="w-full rounded-xl border border-border bg-background/50 p-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
              />
            </div>

            {/* Actions */}
            <div className="mt-6 flex items-center justify-end gap-3 border-t border-border/60 pt-4">
              <button
                type="button"
                onClick={() => setSelectedPlanForModal(null)}
                disabled={isSubmitting}
                className="rounded-xl border border-border px-4 py-2.5 text-xs font-semibold text-foreground hover:bg-muted/70 transition"
              >
                {translateKey("holding_hub", "plans.cancel_button")}
              </button>
              <button
                type="button"
                data-testid="plan-change-confirm-btn"
                disabled={isSubmitting}
                onClick={handleConfirmPlanChange}
                className="rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground shadow-md shadow-primary/20 hover:bg-primary/90 transition disabled:opacity-50"
              >
                {isSubmitting
                  ? translateKey("common", "status.loading")
                  : translateKey("holding_hub", "plans.confirm_button")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
