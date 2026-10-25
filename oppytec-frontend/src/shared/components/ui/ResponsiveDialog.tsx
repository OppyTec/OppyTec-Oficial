import type { ReactNode } from "react";
import { translateKey } from "@/shared/i18n";
import { cn } from "@/shared/lib/utils";

export interface ResponsiveDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly title: string;
  readonly description?: string;
  readonly isMobile?: boolean;
  readonly maxWidth?: string;
  readonly className?: string;
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
  maxWidth = "max-w-lg",
  className,
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
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-2 backdrop-blur-sm md:items-center md:p-4 overflow-y-auto"
    >
      <div
        className={cn(
          "glass-card w-full rounded-2xl border border-border p-4 shadow-2xl max-h-[90vh] flex flex-col my-auto",
          maxWidth,
          isMobile ? "rounded-b-none" : "",
          className
        )}
      >
        <div className="mb-3 flex items-center justify-between border-b border-border pb-2 shrink-0">
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
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-secondary px-3 py-1.5 text-xs font-semibold text-secondary-foreground cursor-pointer select-none"
          >
            {translateKey("common", "actions.cancel")}
          </button>
        </div>
        <div className="flex-1 overflow-y-auto min-h-0">{children}</div>
      </div>
    </div>
  );
}
