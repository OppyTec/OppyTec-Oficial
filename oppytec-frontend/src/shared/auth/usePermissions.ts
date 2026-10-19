import {
  createContext,
  createElement,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

export type ThreeLevelPermission = `${string}.${string}.${string}`;

const THREE_LEVEL_REGEX = /^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$/;

export function isValidThreeLevelPermission(
  permission: string
): permission is ThreeLevelPermission {
  return THREE_LEVEL_REGEX.test(permission);
}

export interface TemporaryGrantDescriptor {
  readonly permission: ThreeLevelPermission;
  readonly expiresAtIso: string;
  readonly reason: string;
  readonly grantedBy: string;
}

export interface RbacPolicyState {
  readonly roleName: string;
  readonly planModules: readonly string[];
  readonly rolePermissions: readonly ThreeLevelPermission[];
  readonly temporaryGrants: readonly TemporaryGrantDescriptor[];
  readonly deniedPermissions: readonly ThreeLevelPermission[];
  readonly isSuperUser?: boolean;
}

/**
 * Evaluates the canonical 3-level RBAC intersection formula (Rule 07):
 * Effective = M_Plan ∩ ((P_Role ∪ P_Temp_Active) \ P_Deny)
 */
export function evaluateEffectivePermissions(
  state: RbacPolicyState,
  nowIso: string = new Date().toISOString()
): ReadonlySet<ThreeLevelPermission> {
  const deniedSet = new Set<string>(state.deniedPermissions);
  const planSet = new Set<string>(state.planModules);
  const effective = new Set<ThreeLevelPermission>();

  const candidates = new Set<ThreeLevelPermission>(state.rolePermissions);
  for (const grant of state.temporaryGrants) {
    if (grant.expiresAtIso > nowIso) {
      candidates.add(grant.permission);
    }
  }

  for (const perm of candidates) {
    if (!isValidThreeLevelPermission(perm)) {
      continue;
    }
    if (deniedSet.has(perm)) {
      continue;
    }
    const modulePrefix = perm.split(".")[0] ?? "";
    if (planSet.has("*") || planSet.has(modulePrefix) || planSet.has(perm)) {
      effective.add(perm);
    }
  }
  return effective;
}

export const DEFAULT_RBAC_POLICY_STATE: RbacPolicyState = {
  roleName: "Gerente Operaciones",
  isSuperUser: true,
  planModules: [
    "auth",
    "rbac_audit",
    "catalog",
    "inventory",
    "recipes",
    "procurement",
    "operations",
    "analytics",
    "oppyfy",
    "platform_admin",
  ],
  rolePermissions: [
    "auth.session.manage",
    "rbac_audit.roles.manage",
    "rbac_audit.audit.read",
    "catalog.products.create",
    "catalog.products.edit",
    "catalog.importer.execute",
    "inventory.stock.read",
    "inventory.counts.execute",
    "inventory.mermas.approve",
    "recipes.escandallos.edit",
    "recipes.simulator.execute",
    "procurement.orders.create",
    "procurement.orders.approve",
    "procurement.invoices.ocr",
    "operations.pos.consume",
    "operations.events.manage",
    "operations.activities.manage",
    "analytics.kpis.read",
    "analytics.reports.export",
    "oppyfy.workspace.query",
    "oppyfy.rbac.configure",
    "platform_admin.holdings.manage",
    "platform_admin.observability.read",
    "platform_admin.backups.restore",
  ],
  temporaryGrants: [
    {
      permission: "inventory.mermas.override_threshold",
      expiresAtIso: "2099-12-31T23:59:59Z",
      reason: "Cierre mensual de auditoría de bodega fría",
      grantedBy: "director.operaciones@oppytec.cl",
    },
  ],
  deniedPermissions: [],
};

export interface PermissionsContextValue {
  readonly policy: RbacPolicyState;
  readonly effectivePermissions: ReadonlySet<ThreeLevelPermission>;
  readonly can: (permission: ThreeLevelPermission) => boolean;
  readonly updatePolicy: (next: Partial<RbacPolicyState>) => void;
}

const PermissionsContext = createContext<PermissionsContextValue | undefined>(
  undefined
);

export interface PermissionsProviderProps {
  readonly children: ReactNode;
  readonly initialPolicy?: RbacPolicyState;
}

export function PermissionsProvider({
  children,
  initialPolicy = DEFAULT_RBAC_POLICY_STATE,
}: PermissionsProviderProps) {
  const [policy, setPolicy] = useState<RbacPolicyState>(initialPolicy);

  const effectivePermissions = useMemo(
    () => evaluateEffectivePermissions(policy),
    [policy]
  );

  const can = useCallback(
    (permission: ThreeLevelPermission): boolean => {
      if (!isValidThreeLevelPermission(permission)) {
        return false;
      }
      return effectivePermissions.has(permission);
    },
    [effectivePermissions]
  );

  const updatePolicy = useCallback((next: Partial<RbacPolicyState>): void => {
    setPolicy((prev) => ({
      ...prev,
      ...next,
    }));
  }, []);

  const value = useMemo<PermissionsContextValue>(
    () => ({
      policy,
      effectivePermissions,
      can,
      updatePolicy,
    }),
    [policy, effectivePermissions, can, updatePolicy]
  );

  return createElement(PermissionsContext.Provider, { value }, children);
}

export function usePermissions(): PermissionsContextValue {
  const ctx = useContext(PermissionsContext);
  if (!ctx) {
    const fallbackSet = evaluateEffectivePermissions(DEFAULT_RBAC_POLICY_STATE);
    return {
      policy: DEFAULT_RBAC_POLICY_STATE,
      effectivePermissions: fallbackSet,
      can: (perm: ThreeLevelPermission) => fallbackSet.has(perm),
      updatePolicy: () => undefined,
    };
  }
  return ctx;
}
