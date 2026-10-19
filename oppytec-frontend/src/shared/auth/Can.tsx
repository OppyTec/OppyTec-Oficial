import type { ReactNode } from "react";
import { translateKey } from "@/shared/i18n";
import {
  type ThreeLevelPermission,
  usePermissions,
} from "./usePermissions";

export interface CanProps {
  readonly perform: ThreeLevelPermission;
  readonly children: ReactNode;
  readonly fallback?: ReactNode;
  readonly showDeniedBadge?: boolean;
}

/**
 * Declarative 3-level RBAC guard (`<Can perform="module.submodule.function">`).
 * Evaluates `M_Plan ∩ ((P_Role ∪ P_Temp) \ P_Deny)` without hardcoded role strings.
 */
export function Can({
  perform,
  children,
  fallback = null,
  showDeniedBadge = false,
}: CanProps) {
  const { can } = usePermissions();
  const allowed = can(perform);

  if (allowed) {
    return (
      <span data-testid={`rbac-allowed-${perform}`} className="contents">
        {children}
      </span>
    );
  }

  if (fallback !== null) {
    return <>{fallback}</>;
  }

  if (showDeniedBadge) {
    return (
      <span
        role="status"
        data-testid={`rbac-denied-${perform}`}
        className="inline-flex items-center rounded-md border border-destructive/30 bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive"
      >
        {translateKey("rbac_audit", "rbac.permission_denied", {
          permission: perform,
        })}
      </span>
    );
  }

  return null;
}
