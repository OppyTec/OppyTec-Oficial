/**
 * oppytec-frontend/src/features/oppyfy/components/governance/BuyCreditPackModal.tsx
 * Modal para cotizar y comprar paquetes de créditos IA Add-On para la bolsa global del Tenant.
 * - Sin caducidad, 100% acumulables (Rollover)
 * - Muestra descuentos por Plan SaaS (Pro / Enterprise)
 * - Touch targets >= 44px
 */

import { useState } from "react";
import { X, Sparkles, Check, ShoppingCart, Tag } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import { formatCurrencyAmount } from "@/shared/currency/useCurrencyFormatter";
import type { AiCreditPackResponse, AiCreditPackQuoteResponse } from "../../types";

export interface BuyCreditPackModalProps {
  readonly isOpen: boolean;
  readonly packs: readonly AiCreditPackResponse[];
  readonly onClose: () => void;
  readonly onQuotePack: (packId: number, planTier?: string) => Promise<AiCreditPackQuoteResponse>;
  readonly onConfirmPurchase?: (packId: number) => Promise<void>;
}

export function BuyCreditPackModal({
  isOpen,
  packs,
  onClose,
  onQuotePack,
  onConfirmPurchase,
}: BuyCreditPackModalProps) {
  const [selectedPackId, setSelectedPackId] = useState<number | null>(packs[0]?.id ?? 1);
  const [activeQuote, setActiveQuote] = useState<AiCreditPackQuoteResponse | null>(null);
  const [isQuoting, setIsQuoting] = useState<boolean>(false);
  const [isPurchasing, setIsPurchasing] = useState<boolean>(false);
  const [purchaseSuccess, setPurchaseSuccess] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSelectAndQuote = async (packId: number) => {
    setSelectedPackId(packId);
    setIsQuoting(true);
    setPurchaseSuccess(false);
    try {
      const quote = await onQuotePack(packId, "pro");
      setActiveQuote(quote);
    } catch {
      setActiveQuote(null);
    } finally {
      setIsQuoting(false);
    }
  };

  const handleConfirm = async () => {
    if (!selectedPackId) return;
    setIsPurchasing(true);
    try {
      if (onConfirmPurchase) {
        await onConfirmPurchase(selectedPackId);
      } else {
        await new Promise((res) => setTimeout(res, 300));
      }
      setPurchaseSuccess(true);
    } finally {
      setIsPurchasing(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="buy-credit-pack-title"
      data-testid="modal-buy-credit-pack"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in"
    >
      <div className="glass-card relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-2xl">
        {/* Cabecera */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="buy-credit-pack-title"
                className="text-base font-bold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.buy_pack_modal.title")}
              </h2>
            </div>
          </div>
          <button
            type="button"
            data-testid="btn-close-buy-pack"
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label={translateKey("oppyfy", "governance.buy_pack_modal.close_aria")}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Notificación de compra exitosa */}
        {purchaseSuccess && (
          <div
            role="status"
            data-testid="buy-pack-success"
            className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs font-semibold text-emerald-600 dark:text-emerald-400"
          >
            <Check className="h-4 w-4" />
            <span>{translateKey("oppyfy", "governance.buy_pack_modal.success_message")}</span>
          </div>
        )}

        {/* Contenido con cuadrícula de paquetes */}
        <div className="flex-1 space-y-4 overflow-y-auto py-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {packs.map((pack) => {
              const isSelected = selectedPackId === pack.id;
              return (
                <div
                  key={pack.id}
                  data-testid={`credit-pack-card-${pack.id}`}
                  onClick={() => handleSelectAndQuote(pack.id)}
                  className={`relative flex flex-col justify-between rounded-xl border p-4 cursor-pointer transition-all ${
                    isSelected
                      ? "border-primary bg-primary/10 shadow-sm"
                      : "border-border bg-card hover:border-primary/50"
                  }`}
                >
                  {pack.is_popular && (
                    <span className="absolute -top-2.5 right-3 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-primary-foreground shadow-sm">
                      {translateKey("oppyfy", "governance.buy_pack_modal.popular_badge")}
                    </span>
                  )}
                  <div>
                    <h3 className="text-xs font-bold text-card-foreground">
                      {pack.pack_name}
                    </h3>
                    <div className="mt-2 text-2xl font-extrabold text-primary">
                      {pack.credits_amount}
                    </div>
                    <div className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                      {translateKey("oppyfy", "governance.buy_pack_modal.bonus_credits", {
                        bonus: pack.bonus_credits,
                      })}
                    </div>
                    <div className="mt-1 text-[11px] text-muted-foreground">
                      {translateKey("oppyfy", "governance.buy_pack_modal.total_credits", {
                        total: pack.total_credits,
                      })}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border flex items-baseline justify-between">
                    <span
                      data-testid={`credit-pack-price-clp-${pack.id}`}
                      className="text-xs font-bold text-foreground"
                    >
                      {formatCurrencyAmount(pack.price_clp, "CLP")} CLP
                    </span>
                    <span
                      data-testid={`credit-pack-price-usd-${pack.id}`}
                      className="text-[11px] font-mono text-muted-foreground"
                    >
                      {formatCurrencyAmount(pack.price_usd, "USD")}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Vista de Cotización Seleccionada */}
          {activeQuote && (
            <div
              data-testid="active-quote-box"
              className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                  <Tag className="h-3.5 w-3.5" />
                  {translateKey("oppyfy", "governance.buy_pack_modal.quote_title")}
                </span>
                <span className="rounded-md bg-emerald-500/20 px-2 py-0.5 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                  {translateKey("oppyfy", "governance.buy_pack_modal.discount_applied", {
                    pct: activeQuote.discount_pct,
                  })}
                </span>
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <span className="text-xs text-muted-foreground">
                  {translateKey("oppyfy", "governance.buy_pack_modal.final_price_label")}
                </span>
                <div className="text-right">
                  <span
                    data-testid="quote-final-clp"
                    className="text-lg font-extrabold text-foreground"
                  >
                    {formatCurrencyAmount(activeQuote.final_price_clp, "CLP")} CLP
                  </span>
                  <span
                    data-testid="quote-final-usd"
                    className="ml-2 text-xs font-mono text-muted-foreground"
                  >
                    ({formatCurrencyAmount(activeQuote.final_price_usd, "USD")})
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Botones de acción */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
          <button
            type="button"
            data-testid="btn-close-pack-modal"
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-card-foreground transition-colors hover:bg-muted"
          >
            {translateKey("oppyfy", "governance.buy_pack_modal.close")}
          </button>
          <button
            type="button"
            data-testid="btn-confirm-buy-pack"
            onClick={handleConfirm}
            disabled={isPurchasing || isQuoting || !selectedPackId}
            className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            <span>
              {isPurchasing
                ? translateKey("oppyfy", "governance.buy_pack_modal.processing")
                : translateKey("oppyfy", "governance.buy_pack_modal.confirm_btn")}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
