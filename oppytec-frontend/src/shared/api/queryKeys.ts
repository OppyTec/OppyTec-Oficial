export interface TenantScopeParams {
  readonly holdingId: string;
  readonly tenantId: string;
  readonly warehouseId?: string;
}

/**
 * Centralized TanStack Query v5 Key Factory for OppyTec SaaS v2.0.
 * Enforces deterministic cache invalidation from WebSocket push events (`useRealtimeSync`).
 */
export const queryKeys = {
  all: ["oppytec"] as const,
  auth: {
    session: () => ["oppytec", "auth", "session"] as const,
    tenants: (holdingId: string) =>
      ["oppytec", "auth", "tenants", holdingId] as const,
  },
  rbac: {
    roles: (tenantId: string) => ["oppytec", "rbac", "roles", tenantId] as const,
    matrix: (tenantId: string) =>
      ["oppytec", "rbac", "matrix", tenantId] as const,
    tempGrants: (tenantId: string) =>
      ["oppytec", "rbac", "tempGrants", tenantId] as const,
    seatQuota: (tenantId: string) =>
      ["oppytec", "rbac", "seatQuota", tenantId] as const,
  },
  audit: {
    forensicLogs: (tenantId: string, traceId?: string) =>
      ["oppytec", "audit", "forensicLogs", tenantId, traceId ?? "all"] as const,
  },
  catalog: {
    products: (tenantId: string) =>
      ["oppytec", "catalog", "products", tenantId] as const,
    categories: (tenantId: string) =>
      ["oppytec", "catalog", "categories", tenantId] as const,
    units: (tenantId: string) =>
      ["oppytec", "catalog", "units", tenantId] as const,
    r2Quota: (tenantId: string) =>
      ["oppytec", "catalog", "r2Quota", tenantId] as const,
  },
  inventory: {
    stock: (scope: TenantScopeParams) =>
      [
        "oppytec",
        "inventory",
        "stock",
        scope.holdingId,
        scope.tenantId,
        scope.warehouseId ?? "all",
      ] as const,
    counts: (tenantId: string) =>
      ["oppytec", "inventory", "counts", tenantId] as const,
    mermas: (tenantId: string) =>
      ["oppytec", "inventory", "mermas", tenantId] as const,
  },
  recipes: {
    escandallos: (tenantId: string) =>
      ["oppytec", "recipes", "escandallos", tenantId] as const,
    combos: (tenantId: string) =>
      ["oppytec", "recipes", "combos", tenantId] as const,
  },
  procurement: {
    purchaseOrders: (tenantId: string) =>
      ["oppytec", "procurement", "purchaseOrders", tenantId] as const,
    suppliers: (tenantId: string) =>
      ["oppytec", "procurement", "suppliers", tenantId] as const,
    invoices: (tenantId: string) =>
      ["oppytec", "procurement", "invoices", tenantId] as const,
  },
  operations: {
    posConsumption: (tenantId: string) =>
      ["oppytec", "operations", "posConsumption", tenantId] as const,
    events: (tenantId: string) =>
      ["oppytec", "operations", "events", tenantId] as const,
    buffet: (tenantId: string) =>
      ["oppytec", "operations", "buffet", tenantId] as const,
    activities: (tenantId: string) =>
      ["oppytec", "operations", "activities", tenantId] as const,
    alerts: (tenantId: string) =>
      ["oppytec", "operations", "alerts", tenantId] as const,
    notifications: (tenantId: string) =>
      ["oppytec", "operations", "notifications", tenantId] as const,
  },
  analytics: {
    kpis: (tenantId: string, period: string) =>
      ["oppytec", "analytics", "kpis", tenantId, period] as const,
    reports: (tenantId: string, reportType: string) =>
      ["oppytec", "analytics", "reports", tenantId, reportType] as const,
  },
  oppyfy: {
    workspace: (tenantId: string) =>
      ["oppytec", "oppyfy", "workspace", tenantId] as const,
    credits: (tenantId: string) =>
      ["oppytec", "oppyfy", "credits", tenantId] as const,
    rbacDomains: (tenantId: string) =>
      ["oppytec", "oppyfy", "rbacDomains", tenantId] as const,
  },
  platformAdmin: {
    holdings: () => ["oppytec", "platformAdmin", "holdings"] as const,
    finopsLogs: (envFilter: string) =>
      ["oppytec", "platformAdmin", "finopsLogs", envFilter] as const,
    observability: (subview: string, envFilter: string) =>
      [
        "oppytec",
        "platformAdmin",
        "observability",
        subview,
        envFilter,
      ] as const,
  },
} as const;
