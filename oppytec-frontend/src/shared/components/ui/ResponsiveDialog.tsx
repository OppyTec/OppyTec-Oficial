import type { ReactNode } from "react";
import { translateKey } from "@/shared/i18n";

export interface ResponsiveDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly title: string;
  readonly description?: string;
  readonly isMobile?: boolean;
  readonly children: ReactNode;
}

/**
 * Adaptive Dialog (Rule 21): Renders as a Bottom Sheet Drawer on mobile (`< 768px`)
 * and a centered Glassmorphic Modal on desktop (`CLS = 0`).
 */
export function ResponsiveDialog({
  open,
  onClose,
  title,
  description,
  isMobile = false,
  children,
}: ResponsiveDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      data-testid="responsive-dialog"
      data-layout-mode={isMobile ? "mobile-drawer" : "desktop-modal"}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-2 backdrop-blur-sm md:items-center md:p-4"
    >
      <div
        className={`glass-card w-full max-w-lg rounded-2xl border border-border p-4 shadow-2xl ${
          isMobile ? "rounded-b-none" : ""
        }`}
      >
        <div className="mb-3 flex items-center justify-between border-b border-border pb-2">
          <div>
            <h3 className="text-base font-bold text-foreground">{title}</h3>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="responsive-dialog-close"
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-secondary px-3 py-1.5 text-xs font-semibold text-secondary-foreground"
          >
            {translateKey("common", "actions.cancel")}
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
