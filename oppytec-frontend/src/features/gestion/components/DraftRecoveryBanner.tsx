import { useState, useEffect, useCallback } from "react";
import { Sparkles, Trash2, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/shared/lib";

export const DRAFT_STORAGE_KEY = "oppytec_producto_draft";

export interface DraftProductData {
  nombre?: string;
  currentStep?: number;
  categoriaId?: string;
  sku?: string;
  [key: string]: unknown;
}

export interface DraftRecoveryBannerProps {
  readonly onRecoverDraft?: (draft: DraftProductData) => void;
  readonly onDismiss?: () => void;
  readonly className?: string;
  readonly storageKey?: string;
}

export function DraftRecoveryBanner({
  onRecoverDraft,
  onDismiss,
  className,
  storageKey = DRAFT_STORAGE_KEY,
}: DraftRecoveryBannerProps) {
  const [draft, setDraft] = useState<DraftProductData | null>(null);

  const checkDraft = useCallback(() => {
    try {
      if (typeof window === "undefined" || !window.localStorage) {
        return;
      }
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) {
        setDraft(null);
        return;
      }
      const parsed = JSON.parse(raw) as DraftProductData;
      if (parsed && typeof parsed === "object") {
        setDraft(parsed);
      } else {
        setDraft(null);
      }
    } catch {
      setDraft(null);
    }
  }, [storageKey]);

  useEffect(() => {
    checkDraft();
    const handleStorage = (event: StorageEvent) => {
      if (event.key === storageKey) {
        checkDraft();
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [checkDraft, storageKey]);

  const handleDiscard = () => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(storageKey);
      }
    } catch {
      // safe fallback
    }
    setDraft(null);
    onDismiss?.();
  };

  const handleRecover = () => {
    if (!draft) return;
    onRecoverDraft?.(draft);
  };

  return (
    <AnimatePresence>
      {draft && (
        <motion.div
          layout
          data-testid="draft-recovery-banner"
          initial={{ opacity: 0, y: -12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -12, scale: 0.98 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className={cn(
            "relative w-full rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3.5 md:px-5 md:py-3 text-foreground shadow-sm mb-4 backdrop-blur-sm",
            className
          )}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            {/* Info Section */}
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-500 border border-amber-500/30 shadow-inner">
                <Sparkles className="h-5 w-5 animate-pulse" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[11px] font-black uppercase tracking-wider text-amber-600 dark:text-amber-400">
                    Borrador pendiente
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                    Paso {draft.currentStep ?? 1} de 4
                  </span>
                </div>
                <p className="text-xs font-semibold text-foreground truncate mt-0.5">
                  {draft.nombre?.trim() || "Producto sin nombre"}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 self-end sm:self-center shrink-0 w-full sm:w-auto">
              <button
                type="button"
                onClick={handleDiscard}
                data-testid="btn-discard-draft"
                className="flex-1 sm:flex-none inline-flex min-h-[44px] sm:min-h-[36px] items-center justify-center gap-1.5 rounded-xl border border-border bg-card px-3 py-2 text-xs font-bold text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-colors cursor-pointer select-none"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Descartar</span>
              </button>

              <button
                type="button"
                onClick={handleRecover}
                data-testid="btn-recover-draft"
                className="flex-1 sm:flex-none inline-flex min-h-[44px] sm:min-h-[36px] items-center justify-center gap-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-black px-4 py-2 text-xs font-black uppercase tracking-wider shadow-md shadow-amber-500/20 transition-all active:scale-95 cursor-pointer select-none"
              >
                <span>Recuperar Borrador</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default DraftRecoveryBanner;
