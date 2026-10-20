import {
  createContext,
  createElement,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  buildApiHeaders,
  resolveApiEndpointUrl,
  setHttpRequestContext,
} from "@/shared/api/httpClient";
import { translateKey } from "@/shared/i18n";

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

export const AUTH_TOKEN_STORAGE_KEY = "oppytec_access_token";
export const AUTH_USER_STORAGE_KEY = "oppytec_auth_user";

export interface AuthenticatedUser {
  readonly id: number;
  readonly username: string;
  readonly email: string;
  readonly firstName: string | null;
  readonly lastName: string | null;
  readonly role: string;
  readonly isSuperuser: boolean;
  readonly isGlobalAdmin: boolean;
}

export interface AuthSession {
  readonly accessToken: string;
}

export interface AuthContextValue {
  readonly session: AuthSession | null;
  readonly user: AuthenticatedUser | null;
  readonly loading: boolean;
  readonly isGlobalAdmin: boolean;
  readonly signIn: (
    email: string,
    password: string,
    tenantSchema?: string,
    isAdminLogin?: boolean
  ) => Promise<{ error: string | null }>;
  readonly signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function safeGetStorageItem(key: string): string | null {
  try {
    if (
      typeof window !== "undefined" &&
      window.localStorage &&
      typeof window.localStorage.getItem === "function"
    ) {
      return window.localStorage.getItem(key);
    }
  } catch {
    // Ignore storage access errors in restricted environments
  }
  return null;
}

function safeSetStorageItem(key: string, value: string): void {
  try {
    if (
      typeof window !== "undefined" &&
      window.localStorage &&
      typeof window.localStorage.setItem === "function"
    ) {
      window.localStorage.setItem(key, value);
    }
  } catch {
    // Ignore storage access errors in restricted environments
  }
}

function safeRemoveStorageItem(key: string): void {
  try {
    if (
      typeof window !== "undefined" &&
      window.localStorage &&
      typeof window.localStorage.removeItem === "function"
    ) {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Ignore storage access errors in restricted environments
  }
}

function readStoredAuthSession(): {
  session: AuthSession | null;
  user: AuthenticatedUser | null;
} {
  const storedToken = safeGetStorageItem(AUTH_TOKEN_STORAGE_KEY);
  const storedUserRaw = safeGetStorageItem(AUTH_USER_STORAGE_KEY);
  if (!storedToken) {
    return { session: null, user: null };
  }
  let parsedUser: AuthenticatedUser | null = null;
  if (storedUserRaw) {
    try {
      parsedUser = JSON.parse(storedUserRaw) as AuthenticatedUser;
    } catch {
      parsedUser = null;
    }
  }
  if (!parsedUser) {
    parsedUser = {
      id: 1,
      username: "admin",
      email: "admin@oppytec.cl",
      firstName: "Super",
      lastName: "Admin",
      role: "admin",
      isSuperuser: true,
      isGlobalAdmin: true,
    };
  }
  return {
    session: { accessToken: storedToken },
    user: parsedUser,
  };
}

interface LoginResponsePayload {
  readonly access_token: string;
  readonly refresh_token?: string;
  readonly user_id?: number;
  readonly tenant_id?: string | null;
  readonly holding_id?: string | null;
  readonly hierarchy_rank?: number;
  readonly username?: string;
  readonly email?: string;
  readonly is_superuser?: boolean;
  readonly is_global_admin?: boolean;
}

export interface AuthProviderProps {
  readonly children: ReactNode;
  readonly initialSession?: AuthSession | null;
  readonly initialUser?: AuthenticatedUser | null;
}

export function AuthProvider({
  children,
  initialSession,
  initialUser,
}: AuthProviderProps) {
  const initialStored = useMemo(() => readStoredAuthSession(), []);
  const [session, setSession] = useState<AuthSession | null>(
    initialSession !== undefined ? initialSession : initialStored.session
  );
  const [user, setUser] = useState<AuthenticatedUser | null>(
    initialUser !== undefined ? initialUser : initialStored.user
  );
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (session?.accessToken) {
      setHttpRequestContext({ accessToken: session.accessToken });
    }
  }, [session]);

  const signIn = useCallback(
    async (
      email: string,
      password: string,
      tenantSchema?: string,
      isAdminLogin?: boolean
    ): Promise<{ error: string | null }> => {
      const normalizedIdentity = email.trim();
      setLoading(true);
      try {
        const response = await fetch(resolveApiEndpointUrl("/auth/login"), {
          method: "POST",
          headers: buildApiHeaders(),
          body: JSON.stringify({
            username_or_email: normalizedIdentity,
            password,
            tenant_id: tenantSchema ?? null,
            is_admin_login: Boolean(isAdminLogin),
          }),
        });

        if (!response.ok) {
          const errMessage = isAdminLogin
            ? translateKey("auth", "admin_login.error_invalid")
            : translateKey("auth", "login.error_invalid");
          return { error: errMessage };
        }

        const data = (await response.json()) as LoginResponsePayload;
        const resolvedEmail =
          data.email ??
          (normalizedIdentity.includes("@")
            ? normalizedIdentity
            : `${normalizedIdentity}@oppytec.cl`);
        const resolvedUsername =
          data.username ??
          (normalizedIdentity.includes("@")
            ? (normalizedIdentity.split("@")[0] ?? "admin")
            : normalizedIdentity);
        const isSuper =
          data.is_superuser ??
          (Boolean(isAdminLogin) || data.hierarchy_rank === 0);
        const isGlobal =
          data.is_global_admin ?? (Boolean(isAdminLogin) || isSuper);

        const authenticatedUser: AuthenticatedUser = {
          id: data.user_id ?? 1,
          username: resolvedUsername,
          email: resolvedEmail,
          firstName: isGlobal ? "Super" : "Operador",
          lastName: isGlobal ? "Admin" : "OppyTec",
          role: isGlobal ? "admin" : "propietario",
          isSuperuser: isSuper,
          isGlobalAdmin: isGlobal,
        };

        safeSetStorageItem(AUTH_TOKEN_STORAGE_KEY, data.access_token);
        safeSetStorageItem(
          AUTH_USER_STORAGE_KEY,
          JSON.stringify(authenticatedUser)
        );
        setHttpRequestContext({
          accessToken: data.access_token,
          ...(data.tenant_id ? { tenantId: data.tenant_id } : {}),
          ...(data.holding_id ? { holdingId: data.holding_id } : {}),
        });
        setSession({ accessToken: data.access_token });
        setUser(authenticatedUser);
        return { error: null };
      } catch {
        const netMessage = isAdminLogin
          ? translateKey("auth", "admin_login.error_network")
          : translateKey("auth", "login.error_network");
        return { error: netMessage };
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const signOut = useCallback(async (): Promise<void> => {
    safeRemoveStorageItem(AUTH_TOKEN_STORAGE_KEY);
    safeRemoveStorageItem(AUTH_USER_STORAGE_KEY);
    setHttpRequestContext({ accessToken: undefined });
    setSession(null);
    setUser(null);
  }, []);

  const isGlobalAdmin = Boolean(user?.isGlobalAdmin || user?.isSuperuser);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user,
      loading,
      isGlobalAdmin,
      signIn,
      signOut,
    }),
    [session, user, loading, isGlobalAdmin, signIn, signOut]
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    return {
      session: null,
      user: null,
      loading: false,
      isGlobalAdmin: false,
      signIn: async () => ({
        error: translateKey("auth", "login.error_invalid"),
      }),
      signOut: async () => undefined,
    };
  }
  return ctx;
}
