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
    mermasAnalytics: (tenantId: string, params?: Record<string, unknown>) =>
      ["oppytec", "inventory", "mermas", "analytics", tenantId, params ?? {}] as const,
    mermasHistory: (tenantId: string, params?: Record<string, unknown>) =>
      ["oppytec", "inventory", "mermas", "history", tenantId, params ?? {}] as const,
    alerts: (params?: {
      holdingId?: string;
      tenantId?: string;
      bodegaIds?: string;
      areaOperativaId?: string;
      filterType?: string;
      upcomingDays?: number;
    }) =>
      [
        "oppytec",
        "inventory",
        "alerts",
        params?.holdingId ?? "default",
        params?.tenantId ?? "default",
        params?.bodegaIds ?? "all",
        params?.areaOperativaId ?? "all",
        params?.filterType ?? "all",
        String(params?.upcomingDays ?? 30),
      ] as const,
    alertsBadge: (params?: {
      holdingId?: string;
      tenantId?: string;
      bodegaIds?: string;
      areaOperativaId?: string;
    }) =>
      [
        "oppytec",
        "inventory",
        "alerts",
        "badge",
        params?.holdingId ?? "default",
        params?.tenantId ?? "default",
        params?.bodegaIds ?? "all",
        params?.areaOperativaId ?? "all",
      ] as const,
    history: (params?: Record<string, unknown>) =>
      ["inventory", "history", params ?? {}] as const,
  },
  recipes: {
    all: (tenantId: string) => ["oppytec", "recipes", "all", tenantId] as const,
    list: (tenantId: string, params?: Record<string, unknown>) =>
      ["oppytec", "recipes", "list", tenantId, params ?? {}] as const,
    detail: (tenantId: string, id: string | number) =>
      ["oppytec", "recipes", "detail", tenantId, String(id)] as const,
    categories: (tenantId: string) =>
      ["oppytec", "recipes", "categories", tenantId] as const,
    optionGroups: (tenantId: string) =>
      ["oppytec", "recipes", "optionGroups", tenantId] as const,
    optionGroupDetail: (tenantId: string, id: string | number) =>
      ["oppytec", "recipes", "optionGroupDetail", tenantId, String(id)] as const,
    combos: (tenantId: string, params?: Record<string, unknown>) =>
      ["oppytec", "recipes", "combos", tenantId, params ?? {}] as const,
    comboDetail: (tenantId: string, id: string | number) =>
      ["oppytec", "recipes", "comboDetail", tenantId, String(id)] as const,
    comboCategories: (tenantId: string) =>
      ["oppytec", "recipes", "comboCategories", tenantId] as const,
    simulation: (tenantId: string, recipeId: string | number) =>
      ["oppytec", "recipes", "simulation", tenantId, String(recipeId)] as const,
    allergens: (tenantId: string, id: string | number) =>
      ["oppytec", "recipes", "allergens", tenantId, String(id)] as const,
    kitchenSheet: (tenantId: string, id: string | number, servings?: number) =>
      ["oppytec", "recipes", "kitchenSheet", tenantId, String(id), servings ?? "default"] as const,
    escandallos: (tenantId: string) =>
      ["oppytec", "recipes", "escandallos", tenantId] as const,
  },
  procurement: {
    purchaseOrders: (tenantId: string, params?: Record<string, unknown>) =>
      ["oppytec", "procurement", "purchaseOrders", tenantId, params ?? {}] as const,
    dashboard: (tenantId: string) =>
      ["oppytec", "procurement", "dashboard", tenantId] as const,
    suppliers: (tenantId: string, params?: Record<string, unknown>) =>
      ["oppytec", "procurement", "suppliers", tenantId, params ?? {}] as const,
    supplierCatalog: (tenantId: string, supplierId: number) =>
      ["oppytec", "procurement", "supplierCatalog", tenantId, supplierId] as const,
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
    buffetSessions: (
      tenantId: string,
      bodegaId?: number | string | null,
      estado?: string | null
    ) =>
      [
        "oppytec",
        "operations",
        "buffet",
        "sessions",
        tenantId,
        String(bodegaId ?? "all"),
        estado ?? "all",
      ] as const,
    buffetSessionDetail: (tenantId: string, id: number | string) =>
      ["oppytec", "operations", "buffet", "detail", tenantId, String(id)] as const,
    buffetTemplates: (tenantId: string) =>
      ["oppytec", "operations", "buffet", "templates", tenantId] as const,
    consumption: {
      all: (tenantId: string) =>
        ["oppytec", "operations", "consumption", tenantId] as const,
      history: (tenantId: string, params?: Record<string, unknown>) =>
        [
          "oppytec",
          "operations",
          "consumption",
          "history",
          tenantId,
          JSON.stringify(params ?? {}),
        ] as const,
      detail: (tenantId: string, id: number | string) =>
        [
          "oppytec",
          "operations",
          "consumption",
          "detail",
          tenantId,
          String(id),
        ] as const,
      templates: (tenantId: string) =>
        [
          "oppytec",
          "operations",
          "consumption",
          "templates",
          tenantId,
        ] as const,
    },
    voice: {
      all: (tenantId: string) =>
        ["oppytec", "operations", "voice", tenantId] as const,
      stations: (tenantId: string, areaOperativaId?: number | null) =>
        [
          "oppytec",
          "operations",
          "voice",
          "stations",
          tenantId,
          String(areaOperativaId ?? "all"),
        ] as const,
      orders: (tenantId: string) =>
        ["oppytec", "operations", "voice", "orders", tenantId] as const,
    },
    activities: (tenantId: string) =>
      ["oppytec", "operations", "activities", tenantId] as const,
    alerts: (tenantId: string) =>
      ["oppytec", "operations", "alerts", tenantId] as const,
    notifications: (tenantId: string) =>
      ["oppytec", "operations", "notifications", tenantId] as const,
    approvals: (params?: {
      tenantId?: string;
      estado?: string;
      categoria?: string;
      areaId?: string;
      bodegaId?: number;
      search?: string;
      page?: number;
    }) =>
      [
        "oppytec",
        "operations",
        "approvals",
        params?.tenantId ?? "default",
        params?.estado ?? "all",
        params?.categoria ?? "all",
        params?.areaId ?? "all",
        params?.bodegaId !== undefined ? String(params.bodegaId) : "all",
        params?.search ?? "",
        String(params?.page ?? 1),
      ] as const,
    pendingCount: (params?: { tenantId?: string; areaId?: string }) =>
      [
        "oppytec",
        "operations",
        "pendingCount",
        params?.tenantId ?? "default",
        params?.areaId ?? "all",
      ] as const,
    notificationMatrix: (tenantId?: string) =>
      [
        "oppytec",
        "operations",
        "notificationMatrix",
        tenantId ?? "default",
      ] as const,
  },
  approvals: {
    all: () => ["oppytec", "approvals"] as const,
    list: (params?: {
      tenantId?: string;
      estado?: string;
      categoria?: string;
      areaId?: string;
      bodegaId?: number;
      search?: string;
      page?: number;
    }) =>
      [
        "oppytec",
        "approvals",
        "list",
        params?.tenantId ?? "default",
        params?.estado ?? "all",
        params?.categoria ?? "all",
        params?.areaId ?? "all",
        params?.bodegaId !== undefined ? String(params.bodegaId) : "all",
        params?.search ?? "",
        String(params?.page ?? 1),
      ] as const,
    detail: (id: string) => ["oppytec", "approvals", "detail", id] as const,
    pendingCount: (params?: { tenantId?: string; areaId?: string }) =>
      [
        "oppytec",
        "approvals",
        "pendingCount",
        params?.tenantId ?? "default",
        params?.areaId ?? "all",
      ] as const,
    matrix: (tenantId?: string) =>
      ["oppytec", "approvals", "matrix", tenantId ?? "default"] as const,
    buffetDetail: (solicitudId: string) =>
      ["oppytec", "approvals", "buffetDetail", solicitudId] as const,
  },
  pendingCount: (params?: { tenantId?: string; areaId?: string }) =>
    [
      "oppytec",
      "approvals",
      "pendingCount",
      params?.tenantId ?? "default",
      params?.areaId ?? "all",
    ] as const,
  notificationMatrix: (tenantId?: string) =>
    ["oppytec", "approvals", "matrix", tenantId ?? "default"] as const,
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
    wallet: (tenantId: string) =>
      ["oppytec", "oppyfy", "wallet", tenantId] as const,
    workerWallets: (tenantId: string) =>
      ["oppytec", "oppyfy", "workerWallets", tenantId] as const,
    rbacDomains: (tenantId: string) =>
      ["oppytec", "oppyfy", "rbacDomains", tenantId] as const,
    rbacGrants: (tenantId: string) =>
      ["oppytec", "oppyfy", "rbacGrants", tenantId] as const,
    promptAuditLogs: (tenantId: string, status?: string) =>
      ["oppytec", "oppyfy", "promptAuditLogs", tenantId, status ?? "all"] as const,
    aiPacks: (isActiveOnly?: boolean) =>
      ["oppytec", "oppyfy", "aiPacks", String(isActiveOnly ?? false)] as const,
    packQuote: (packId: number, planTier?: string) =>
      ["oppytec", "oppyfy", "packQuote", String(packId), planTier ?? "none"] as const,
    telemetryLogs: () =>
      ["oppytec", "oppyfy", "telemetryLogs"] as const,
  },
  platformAdmin: {
    holdings: () => ["oppytec", "platformAdmin", "holdings"] as const,
    plans: () => ["oppytec", "platformAdmin", "plans"] as const,
    aiPacks: (isActiveOnly?: boolean) =>
      ["oppytec", "platformAdmin", "aiPacks", String(isActiveOnly ?? false)] as const,
    saasPolicy: () => ["oppytec", "platformAdmin", "saasPolicy"] as const,
    tokenConsumption: (filters?: Record<string, unknown>) =>
      ["oppytec", "platformAdmin", "tokenConsumption", filters ?? {}] as const,
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
