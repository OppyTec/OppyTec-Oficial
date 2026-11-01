/**
 * oppytec-frontend/src/features/platform-admin/types.ts
 * Contratos TypeScript estrictos (0 `any`, `readonly` properties) para:
 * - Catálogo de Planes Comerciales & Tiers (`/api/v1/platform-admin/plans`)
 * - Política Global SaaS de Conversión Tokens/Créditos (`/api/v1/platform-admin/ai-credits/policy`)
 * - Consola FinOps de Consumo de Tokens & Créditos (`/api/v1/platform-admin/token-consumption`)
 * - Ajuste de Cupos de Créditos IA por Holding y Tenant
 */

// ============================================================================
// 1. CONTRATOS DE PLANES COMERCIALES
// ============================================================================

export interface SystemPlan {
  readonly slug: string;
  readonly name: string;
  readonly tier: number;
  readonly monthly_ai_credits: number;
  readonly description: string;
  readonly is_popular: boolean;
  readonly is_active: boolean;
  readonly max_active_users: number;
  readonly max_products: number;
  readonly max_suppliers: number;
  readonly max_recipes: number;
  readonly max_combos: number;
  readonly max_storage_mb: number;
  readonly included_modules: readonly string[];
  readonly anchor_currency: string;
  readonly price_clp: number;
  readonly price_usd: number;
  readonly price_eur: number;
  readonly price_brl: number;
  readonly auto_convert_fx: boolean;
  readonly active_clients_count: number;
}

export interface SystemPlanCreateRequest {
  readonly slug?: string;
  readonly name: string;
  readonly tier: number;
  readonly monthly_ai_credits: number;
  readonly description: string;
  readonly is_popular: boolean;
  readonly is_active: boolean;
  readonly max_active_users: number;
  readonly max_products: number;
  readonly max_suppliers: number;
  readonly max_recipes: number;
  readonly max_combos: number;
  readonly max_storage_mb: number;
  readonly included_modules: readonly string[];
  readonly anchor_currency: string;
  readonly price_clp: number;
  readonly price_usd: number;
  readonly price_eur?: number;
  readonly price_brl?: number;
  readonly auto_convert_fx: boolean;
}

export type SystemPlanUpdateRequest = Partial<SystemPlanCreateRequest>;

// ============================================================================
// 2. CONTRATOS DE POLÍTICA GLOBAL SAAS (CONVERSIÓN DE CRÉDITOS & PRECIOS EXTRA)
// ============================================================================

export interface SaaSAIPolicy {
  readonly tokens_per_credit: number;
  readonly default_monthly_credits: number;
  readonly credit_price_clp: number;
  readonly credit_price_usd: number;
  readonly updated_at: string | null;
  readonly updated_by: string | null;
}

export interface SaaSAIPolicyUpdateRequest {
  readonly tokens_per_credit?: number;
  readonly default_monthly_credits?: number;
  readonly credit_price_clp?: number;
  readonly credit_price_usd?: number;
}

// ============================================================================
// 3. CONTRATOS FINOPS DE CONSUMO DE TOKENS & CRÉDITOS
// ============================================================================

export interface TokenLogItem {
  readonly id: string;
  readonly created_at: string;
  readonly holding_id: string | null;
  readonly holding_name: string;
  readonly tenant_id: string | null;
  readonly tenant_name: string;
  readonly user_id: string | null;
  readonly user_name: string;
  readonly caller_feature: string;
  readonly model_name: string;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly total_tokens: number;
  readonly estimated_cost_usd: number;
  readonly estimated_cost_clp: number;
  readonly credits_deducted: number;
  readonly request_duration_ms: number;
  readonly api_success: boolean;
  readonly error_message: string | null;
}

export interface TenantGroup {
  readonly tenant_id: string;
  readonly tenant_name: string;
  readonly total_requests: number;
  readonly total_tokens: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly estimated_cost_usd: number;
  readonly estimated_cost_clp: number;
  readonly monthly_credit_limit: number;
  readonly credits_used: number;
  readonly credits_remaining: number;
  readonly credit_usage_pct: number;
  readonly logs: readonly TokenLogItem[];
}

export interface HoldingGroup {
  readonly holding_id: string;
  readonly holding_name: string;
  readonly total_requests: number;
  readonly total_tokens: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly estimated_cost_usd: number;
  readonly estimated_cost_clp: number;
  readonly monthly_credit_limit: number;
  readonly credit_distribution_mode: string;
  readonly credits_used: number;
  readonly credits_remaining: number;
  readonly credit_usage_pct: number;
  readonly tenants: readonly TenantGroup[];
}

export interface TokenConsumptionResponse {
  readonly holdings: readonly HoldingGroup[];
  readonly logs: readonly TokenLogItem[];
  readonly total_records: number;
  readonly total_tokens_all: number;
  readonly total_cost_usd_all: number;
  readonly total_cost_clp_all: number;
  readonly total_credits_used_all: number;
  readonly tokens_per_credit: number;
  readonly page: number;
  readonly page_size: number;
}

export interface CreditQuotaAdjustmentResponse {
  readonly target_type: "holding" | "tenant";
  readonly target_id: string;
  readonly monthly_credit_limit: number;
  readonly monthly_credits?: number;
  readonly credit_distribution_mode: string | null;
  readonly updated_at: string;
  readonly updated_by: string;
  readonly message?: string;
}

export interface HoldingCreditsUpdatePayload {
  readonly monthly_credits: number;
  readonly distribution_mode?: "shared" | "per_tenant";
}

export interface TenantCreditsUpdatePayload {
  readonly monthly_credits: number;
}

// ============================================================================
// 4. CATÁLOGO DEL SISTEMA DE MÓDULOS DE NEGOCIO
// ============================================================================

export interface SystemModuleCatalogItem {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly iconName: string;
  readonly category: "Core" | "Operaciones" | "Inventario" | "Finanzas" | "Gobernanza" | "IA" | "Comercial";
}

export const SYSTEM_MODULE_CATALOG: readonly SystemModuleCatalogItem[] = [
  {
    id: "core",
    label: "Core Platform",
    description: "Configuración base del tenant, usuarios, sucursales y permisos.",
    iconName: "LayoutDashboard",
    category: "Core",
  },
  {
    id: "pos",
    label: "Punto de Venta (POS)",
    description: "Gestión de boletas, comandas, mesas y terminales de cobro rápido.",
    iconName: "ShoppingBag",
    category: "Operaciones",
  },
  {
    id: "inventory",
    label: "Inventario & Kardex",
    description: "Gestión de existencias, recuentos físicos y auditoría FIFO / PPP.",
    iconName: "ClipboardList",
    category: "Inventario",
  },
  {
    id: "kitchen",
    label: "Cocina & KDS",
    description: "Pantalla de comandas para cocineros y estaciones gastronómicas.",
    iconName: "Flame",
    category: "Operaciones",
  },
  {
    id: "delivery",
    label: "Delivery & Despachos",
    description: "Integración con repartidores y seguimiento de pedidos para despacho.",
    iconName: "Truck",
    category: "Operaciones",
  },
  {
    id: "ai_oppyfy",
    label: "Copiloto IA OppyFy",
    description: "Asistente cognitivo, chat contextual y optimización de recetas con LLM.",
    iconName: "Sparkles",
    category: "IA",
  },
  {
    id: "reports",
    label: "Reportes & Analítica BI",
    description: "Métricas ejecutivas de ventas, mermas consolidadas y márgenes.",
    iconName: "TrendingUp",
    category: "Finanzas",
  },
  {
    id: "loyalty",
    label: "Fidelización & Clientes",
    description: "Campañas de fidelización, acumulación de puntos y base de comensales.",
    iconName: "HeartHandshake",
    category: "Comercial",
  },
  {
    id: "inicio",
    label: "Dashboard General",
    description: "Indicadores clave, métricas de ventas y accesos rápidos.",
    iconName: "LayoutDashboard",
    category: "Core",
  },
  {
    id: "consumo",
    label: "Registro de Consumo & Buffet",
    description: "Registro de consumo de personal, cocina y control de bandejas gastronorm.",
    iconName: "UtensilsCrossed",
    category: "Operaciones",
  },
  {
    id: "ventas",
    label: "Ventas & Facturación",
    description: "Gestión de boletas, comandas, mesas y terminales de venta.",
    iconName: "ShoppingBag",
    category: "Operaciones",
  },
  {
    id: "gestion",
    label: "Catálogo & Escandallos",
    description: "Productos, insumos a granel, recetas técnicas y combos de menú.",
    iconName: "Boxes",
    category: "Inventario",
  },
  {
    id: "notificaciones",
    label: "Notificaciones & Aprobaciones",
    description: "Centro jerárquico de gobernanza, aprobación de mermas y auditorías.",
    iconName: "Bell",
    category: "Gobernanza",
  },
  {
    id: "alertas",
    label: "Alertas de Stock & Vencimiento",
    description: "Alertas inteligentes de stock crítico y control FEFO de caducidad.",
    iconName: "AlertTriangle",
    category: "Inventario",
  },
  {
    id: "eventos",
    label: "Eventos & Banquetes",
    description: "Calendario de eventos, reservas especiales y cotizaciones gastronómicas.",
    iconName: "CalendarDays",
    category: "Operaciones",
  },
  {
    id: "proyeccion",
    label: "Proyección de Demanda",
    description: "Analítica predictiva de demanda y planificación de compras sugeridas.",
    iconName: "TrendingUp",
    category: "Finanzas",
  },
  {
    id: "historial",
    label: "Historial de Movimientos",
    description: "Trazabilidad completa de movimientos, transferencias y mermas operacionales.",
    iconName: "History",
    category: "Gobernanza",
  },
  {
    id: "contabilidad",
    label: "Contabilidad & Facturas DTE",
    description: "Recepción de pedidos, lectura OCR de facturas y control de proveedores.",
    iconName: "Calculator",
    category: "Finanzas",
  },
  {
    id: "oppyfy",
    label: "Copiloto IA OppyFy Context",
    description: "Asistente cognitivo, chat contextual y análisis de datos en lenguaje natural.",
    iconName: "Sparkles",
    category: "IA",
  },
  {
    id: "platform-admin",
    label: "SuperAdmin & Observabilidad",
    description: "Panel de administración SaaS, gestión de planes y monitoreo FinOps de IA.",
    iconName: "ShieldAlert",
    category: "Gobernanza",
  },
] as const;

// ============================================================================
// 5. MOCK DATA RESILIENTE (CERO PANTALLAS EN BLANCO)
// ============================================================================

export const MOCK_SYSTEM_PLANS: readonly SystemPlan[] = [
  {
    slug: "plan-basico",
    name: "Plan Básico",
    tier: 1,
    monthly_ai_credits: 500,
    description: "Ideal para cafeterías, food trucks o locales individuales en fase inicial.",
    is_popular: false,
    is_active: true,
    max_active_users: 3,
    max_products: 150,
    max_suppliers: 10,
    max_recipes: 25,
    max_combos: 10,
    max_storage_mb: 512,
    included_modules: ["inicio", "consumo", "inventario", "notificaciones", "alertas"],
    anchor_currency: "CLP",
    price_clp: 29990,
    price_usd: 35,
    price_eur: 32,
    price_brl: 175,
    auto_convert_fx: true,
    active_clients_count: 8,
  },
  {
    slug: "plan-pro",
    name: "Plan Pro Gastronómico",
    tier: 2,
    monthly_ai_credits: 2000,
    description: "Para restaurantes consolidados que requieren costeo estricto y escandallos.",
    is_popular: true,
    is_active: true,
    max_active_users: 10,
    max_products: 1000,
    max_suppliers: 50,
    max_recipes: 200,
    max_combos: 50,
    max_storage_mb: 2048,
    included_modules: [
      "inicio",
      "consumo",
      "ventas",
      "inventario",
      "gestion",
      "notificaciones",
      "alertas",
      "historial",
      "oppyfy",
    ],
    anchor_currency: "CLP",
    price_clp: 69990,
    price_usd: 79,
    price_eur: 73,
    price_brl: 410,
    auto_convert_fx: true,
    active_clients_count: 24,
  },
  {
    slug: "plan-enterprise",
    name: "Plan Enterprise Holding",
    tier: 3,
    monthly_ai_credits: 10000,
    description: "Para cadenas de restaurantes, hoteles con buffet y comisariatos multi-sucursal.",
    is_popular: false,
    is_active: true,
    max_active_users: 999,
    max_products: 10000,
    max_suppliers: 500,
    max_recipes: 2000,
    max_combos: 500,
    max_storage_mb: 20480,
    included_modules: [
      "inicio",
      "consumo",
      "ventas",
      "inventario",
      "gestion",
      "notificaciones",
      "alertas",
      "eventos",
      "proyeccion",
      "historial",
      "contabilidad",
      "oppyfy",
      "platform-admin",
    ],
    anchor_currency: "CLP",
    price_clp: 189990,
    price_usd: 215,
    price_eur: 198,
    price_brl: 1120,
    auto_convert_fx: true,
    active_clients_count: 6,
  },
];

export const MOCK_SAAS_POLICY: SaaSAIPolicy = {
  tokens_per_credit: 1000,
  default_monthly_credits: 2000,
  credit_price_clp: 15.0,
  credit_price_usd: 0.015,
  updated_at: new Date().toISOString(),
  updated_by: "Sistema",
};

export const MOCK_TOKEN_LOGS: readonly TokenLogItem[] = [
  {
    id: "log-001",
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronómico Sur SpA",
    tenant_id: "tenant_rest_central",
    tenant_name: "Restaurante Central Santiago",
    user_id: "usr-001",
    user_name: "Chef Ejecutivo",
    caller_feature: "escandallo_generator",
    model_name: "gemini-1.5-flash",
    input_tokens: 1200,
    output_tokens: 450,
    total_tokens: 1650,
    estimated_cost_usd: 0.0003,
    estimated_cost_clp: 0.28,
    credits_deducted: 1.65,
    request_duration_ms: 820,
    api_success: true,
    error_message: null,
  },
  {
    id: "log-002",
    created_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronómico Sur SpA",
    tenant_id: "tenant_hotel_costanera",
    tenant_name: "Hotel & Buffet Costanera",
    user_id: "usr-002",
    user_name: "Auditor Buffet",
    caller_feature: "buffet_anomaly_detector",
    model_name: "gemini-1.5-pro",
    input_tokens: 3500,
    output_tokens: 890,
    total_tokens: 4390,
    estimated_cost_usd: 0.0125,
    estimated_cost_clp: 11.87,
    credits_deducted: 4.39,
    request_duration_ms: 1940,
    api_success: true,
    error_message: null,
  },
  {
    id: "log-003",
    created_at: new Date(Date.now() - 50 * 60 * 1000).toISOString(),
    holding_id: "holding-pacifico-food",
    holding_name: "Pacífico Food Service S.A.",
    tenant_id: "tenant_dark_kitchen_norte",
    tenant_name: "Comisariato & Dark Kitchen Norte",
    user_id: "usr-003",
    user_name: "Jefe de Compras",
    caller_feature: "ocr_invoice_extraction",
    model_name: "gemini-1.5-flash",
    input_tokens: 2800,
    output_tokens: 600,
    total_tokens: 3400,
    estimated_cost_usd: 0.0007,
    estimated_cost_clp: 0.66,
    credits_deducted: 3.4,
    request_duration_ms: 1150,
    api_success: true,
    error_message: null,
  },
];

export const MOCK_TENANTS_GROUPS: readonly TenantGroup[] = [
  {
    tenant_id: "tenant_rest_central",
    tenant_name: "Restaurante Central Santiago",
    total_requests: 48,
    total_tokens: 95400,
    input_tokens: 72000,
    output_tokens: 23400,
    estimated_cost_usd: 0.028,
    estimated_cost_clp: 26.6,
    monthly_credit_limit: 2000,
    credits_used: 95,
    credits_remaining: 1905,
    credit_usage_pct: 4.75,
    logs: [MOCK_TOKEN_LOGS[0]!],
  },
  {
    tenant_id: "tenant_hotel_costanera",
    tenant_name: "Hotel & Buffet Costanera",
    total_requests: 112,
    total_tokens: 420000,
    input_tokens: 310000,
    output_tokens: 110000,
    estimated_cost_usd: 0.45,
    estimated_cost_clp: 427.5,
    monthly_credit_limit: 5000,
    credits_used: 420,
    credits_remaining: 4580,
    credit_usage_pct: 8.4,
    logs: [MOCK_TOKEN_LOGS[1]!],
  },
];

export const MOCK_HOLDINGS_GROUPS: readonly HoldingGroup[] = [
  {
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronómico Sur SpA",
    total_requests: 160,
    total_tokens: 515400,
    input_tokens: 382000,
    output_tokens: 133400,
    estimated_cost_usd: 0.478,
    estimated_cost_clp: 454.1,
    monthly_credit_limit: 10000,
    credit_distribution_mode: "shared",
    credits_used: 515,
    credits_remaining: 9485,
    credit_usage_pct: 5.15,
    tenants: MOCK_TENANTS_GROUPS,
  },
  {
    holding_id: "holding-pacifico-food",
    holding_name: "Pacífico Food Service S.A.",
    total_requests: 42,
    total_tokens: 128000,
    input_tokens: 94000,
    output_tokens: 34000,
    estimated_cost_usd: 0.035,
    estimated_cost_clp: 33.25,
    monthly_credit_limit: 4000,
    credit_distribution_mode: "per_tenant",
    credits_used: 128,
    credits_remaining: 3872,
    credit_usage_pct: 3.2,
    tenants: [
      {
        tenant_id: "tenant_dark_kitchen_norte",
        tenant_name: "Comisariato & Dark Kitchen Norte",
        total_requests: 42,
        total_tokens: 128000,
        input_tokens: 94000,
        output_tokens: 34000,
        estimated_cost_usd: 0.035,
        estimated_cost_clp: 33.25,
        monthly_credit_limit: 4000,
        credits_used: 128,
        credits_remaining: 3872,
        credit_usage_pct: 3.2,
        logs: [MOCK_TOKEN_LOGS[2]!],
      },
    ],
  },
];

export const MOCK_TOKEN_CONSUMPTION: TokenConsumptionResponse = {
  holdings: MOCK_HOLDINGS_GROUPS,
  logs: MOCK_TOKEN_LOGS,
  total_records: 3,
  total_tokens_all: 643400,
  total_cost_usd_all: 0.513,
  total_cost_clp_all: 487.35,
  total_credits_used_all: 643,
  tokens_per_credit: 1000,
  page: 1,
  page_size: 50,
};

// ============================================================================
// 6. PAQUETES DE CRÉDITOS IA INDEPENDIENTES (ADD-ONS QUE HACEN JUEGO CON PLANES BASE)
// ============================================================================

export interface AiCreditPackItem {
  readonly id: number;
  readonly pack_name: string;
  readonly credits_amount: number | string;
  readonly bonus_credits: number | string;
  readonly total_credits: number | string;
  readonly price_clp: number | string;
  readonly price_usd: number | string;
  readonly is_popular: boolean;
  readonly is_active: boolean;
  readonly sort_order: number;
  readonly plan_tier_discounts: Record<string, number | string>;
}

export interface AiCreditPackCreatePayload {
  readonly pack_name: string;
  readonly credits_amount: number;
  readonly price_clp: number;
  readonly price_usd: number;
  readonly bonus_credits?: number;
  readonly is_popular?: boolean;
  readonly is_active?: boolean;
  readonly sort_order?: number;
  readonly plan_tier_discounts?: Record<string, number>;
}

export const MOCK_AI_CREDIT_PACKS: readonly AiCreditPackItem[] = [
  {
    id: 1,
    pack_name: "Starter Boost (1.000 Créditos)",
    credits_amount: 1000,
    bonus_credits: 0,
    total_credits: 1000,
    price_clp: 9990,
    price_usd: 11,
    is_popular: false,
    is_active: true,
    sort_order: 1,
    plan_tier_discounts: {
      plan_basico: 0,
      plan_pro: 10,
      plan_enterprise: 20,
    },
  },
  {
    id: 2,
    pack_name: "Growth Pack (5.000 Créditos)",
    credits_amount: 5000,
    bonus_credits: 250,
    total_credits: 5250,
    price_clp: 44990,
    price_usd: 49,
    is_popular: true,
    is_active: true,
    sort_order: 2,
    plan_tier_discounts: {
      plan_basico: 0,
      plan_pro: 10,
      plan_enterprise: 20,
    },
  },
  {
    id: 3,
    pack_name: "Enterprise Scale Pollo King (10.000 Créditos)",
    credits_amount: 10000,
    bonus_credits: 1000,
    total_credits: 11000,
    price_clp: 79990,
    price_usd: 88,
    is_popular: false,
    is_active: true,
    sort_order: 3,
    plan_tier_discounts: {
      plan_basico: 0,
      plan_pro: 15,
      plan_enterprise: 25,
    },
  },
];

// ============================================================================
// 6. CONTRATOS FINOPS DE CONSUMO DE DECISIONES JEV (SUB-SIMBÓLICO / DETERMINISTA)
// ============================================================================

export interface JevLogItem {
  readonly id: string;
  readonly created_at: string;
  readonly holding_id: string;
  readonly holding_name: string;
  readonly tenant_id: string;
  readonly tenant_name: string;
  readonly tenant_schema: string;
  readonly user_id?: number | null;
  readonly trace_id?: string | null;
  readonly caller_feature: string;
  readonly decision_id: string;
  readonly decision_primitive: string;
  readonly input_summary: string;
  readonly result_value: string;
  readonly confidence_score: number;
  readonly calibrated_action: string;
  readonly model_name: string;
  readonly estimated_tokens: number;
  readonly provider_cost_usd: number;
  readonly provider_cost_clp: number;
  readonly credits_deducted: number;
  readonly latency_ms: number;
  readonly is_success: boolean;
  readonly error_message?: string | null;
}

export interface JevTenantGroup {
  readonly tenant_id: string;
  readonly tenant_name: string;
  readonly tenant_schema: string;
  readonly holding_id: string;
  readonly total_decisions: number;
  readonly total_cost_usd: number;
  readonly total_cost_clp: number;
  readonly total_credits_deducted: number;
  readonly avg_latency_ms: number;
  readonly auto_accepted_count: number;
  readonly flagged_warning_count: number;
  readonly fallback_llm_count: number;
  readonly logs: readonly JevLogItem[];
}

export interface JevHoldingGroup {
  readonly holding_id: string;
  readonly holding_name: string;
  readonly total_decisions: number;
  readonly total_cost_usd: number;
  readonly total_cost_clp: number;
  readonly total_credits_deducted: number;
  readonly avg_latency_ms: number;
  readonly tenants: readonly JevTenantGroup[];
}

export interface JevConsumptionSummaryResponse {
  readonly total_decisions_all: number;
  readonly total_cost_usd_all: number;
  readonly total_cost_clp_all: number;
  readonly total_credits_deducted_all: number;
  readonly avg_latency_ms_all: number;
  readonly total_auto_accepted_all: number;
  readonly total_flagged_warning_all: number;
  readonly total_fallback_llm_all: number;
  readonly estimated_savings_usd_all: number;
  readonly estimated_savings_clp_all: number;
  readonly holdings: readonly JevHoldingGroup[];
  readonly tenants: readonly JevTenantGroup[];
  readonly all_logs: readonly JevLogItem[];
  readonly page: number;
  readonly page_size: number;
  readonly total_logs_count: number;
}

export const MOCK_JEV_LOGS: readonly JevLogItem[] = [
  {
    id: "jev-log-001",
    created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronomía del Sur",
    tenant_id: "tenant_rest_central",
    tenant_name: "Restaurante Central Providencia",
    tenant_schema: "tenant_rest_central",
    user_id: 1,
    trace_id: "trace-jev-001-abc",
    caller_feature: "mermas_detection",
    decision_id: "dec-merm-9812",
    decision_primitive: "anomaly_score",
    input_summary: "Desviación merma carne lomo vacuno 2.8%",
    result_value: "Aceptada sin anomalía (Riesgo Bajo)",
    confidence_score: 0.98,
    calibrated_action: "AUTO_ACCEPTED",
    model_name: "jev-rules-engine-v2",
    estimated_tokens: 150,
    provider_cost_usd: 0.00008,
    provider_cost_clp: 0.076,
    credits_deducted: 1,
    latency_ms: 12,
    is_success: true,
    error_message: null,
  },
  {
    id: "jev-log-002",
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronomía del Sur",
    tenant_id: "tenant_rest_central",
    tenant_name: "Restaurante Central Providencia",
    tenant_schema: "tenant_rest_central",
    user_id: 2,
    trace_id: "trace-jev-002-def",
    caller_feature: "demand_prediction",
    decision_id: "dec-dem-4521",
    decision_primitive: "bayesian_filter",
    input_summary: "Previsión demanda fin de semana lluvia",
    result_value: "Incremento sugerido +14.5% stock masas",
    confidence_score: 0.93,
    calibrated_action: "AUTO_ACCEPTED",
    model_name: "jev-fast-heuristic",
    estimated_tokens: 220,
    provider_cost_usd: 0.00012,
    provider_cost_clp: 0.114,
    credits_deducted: 1,
    latency_ms: 16,
    is_success: true,
    error_message: null,
  },
  {
    id: "jev-log-003",
    created_at: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronomía del Sur",
    tenant_id: "tenant_rest_mall_plaza",
    tenant_name: "Sucursal Mall Plaza El Trébol",
    tenant_schema: "tenant_rest_mall_plaza",
    user_id: 3,
    trace_id: "trace-jev-003-ghi",
    caller_feature: "recipe_costing",
    decision_id: "dec-rec-1104",
    decision_primitive: "cost_optimality",
    input_summary: "Actualización costo insumo Queso Gouda importado",
    result_value: "Margen operativo en riesgo (38.2%)",
    confidence_score: 0.74,
    calibrated_action: "FLAGGED_WARNING",
    model_name: "jev-rules-engine-v2",
    estimated_tokens: 180,
    provider_cost_usd: 0.00009,
    provider_cost_clp: 0.086,
    credits_deducted: 1,
    latency_ms: 19,
    is_success: true,
    error_message: null,
  },
  {
    id: "jev-log-004",
    created_at: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
    holding_id: "holding-andes",
    holding_name: "Grupo Restaurantero Andes",
    tenant_id: "tenant_andes_las_condes",
    tenant_name: "Bistro Andes Las Condes",
    tenant_schema: "tenant_andes_las_condes",
    user_id: 4,
    trace_id: "trace-jev-004-jkl",
    caller_feature: "order_anomaly",
    decision_id: "dec-ord-8831",
    decision_primitive: "threshold_gate",
    input_summary: "OC irregular 200kg Salmón Premium",
    result_value: "Desviación > 3 sigma. Derivado a Gemini 2.5",
    confidence_score: 0.58,
    calibrated_action: "FALLBACK_LLM",
    model_name: "gemini-2.5-flash-fallback",
    estimated_tokens: 850,
    provider_cost_usd: 0.0018,
    provider_cost_clp: 1.71,
    credits_deducted: 3,
    latency_ms: 420,
    is_success: true,
    error_message: null,
  },
  {
    id: "jev-log-005",
    created_at: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    holding_id: "holding-andes",
    holding_name: "Grupo Restaurantero Andes",
    tenant_id: "tenant_andes_las_condes",
    tenant_name: "Bistro Andes Las Condes",
    tenant_schema: "tenant_andes_las_condes",
    user_id: 5,
    trace_id: "trace-jev-005-mno",
    caller_feature: "inventory_replenishment",
    decision_id: "dec-inv-3329",
    decision_primitive: "exact_match",
    input_summary: "Reabastecimiento automático stock Vino Reserva",
    result_value: "Punto de reorden alcanzado (8 botellas)",
    confidence_score: 0.99,
    calibrated_action: "AUTO_ACCEPTED",
    model_name: "jev-rules-engine-v2",
    estimated_tokens: 110,
    provider_cost_usd: 0.00006,
    provider_cost_clp: 0.057,
    credits_deducted: 1,
    latency_ms: 11,
    is_success: true,
    error_message: null,
  },
];

export const MOCK_JEV_TENANTS: readonly JevTenantGroup[] = [
  {
    tenant_id: "tenant_rest_central",
    tenant_name: "Restaurante Central Providencia",
    tenant_schema: "tenant_rest_central",
    holding_id: "holding-gastro-sur",
    total_decisions: 6850,
    total_cost_usd: 0.92,
    total_cost_clp: 874,
    total_credits_deducted: 6900,
    avg_latency_ms: 14.8,
    auto_accepted_count: 6240,
    flagged_warning_count: 490,
    fallback_llm_count: 120,
    logs: MOCK_JEV_LOGS.filter((l) => l.tenant_id === "tenant_rest_central"),
  },
  {
    tenant_id: "tenant_rest_mall_plaza",
    tenant_name: "Sucursal Mall Plaza El Trébol",
    tenant_schema: "tenant_rest_mall_plaza",
    holding_id: "holding-gastro-sur",
    total_decisions: 3420,
    total_cost_usd: 0.48,
    total_cost_clp: 456,
    total_credits_deducted: 3450,
    avg_latency_ms: 18.2,
    auto_accepted_count: 3100,
    flagged_warning_count: 260,
    fallback_llm_count: 60,
    logs: MOCK_JEV_LOGS.filter((l) => l.tenant_id === "tenant_rest_mall_plaza"),
  },
  {
    tenant_id: "tenant_andes_las_condes",
    tenant_name: "Bistro Andes Las Condes",
    tenant_schema: "tenant_andes_las_condes",
    holding_id: "holding-andes",
    total_decisions: 2210,
    total_cost_usd: 0.445,
    total_cost_clp: 422.75,
    total_credits_deducted: 2150,
    avg_latency_ms: 22.5,
    auto_accepted_count: 1910,
    flagged_warning_count: 230,
    fallback_llm_count: 70,
    logs: MOCK_JEV_LOGS.filter((l) => l.tenant_id === "tenant_andes_las_condes"),
  },
];

export const MOCK_JEV_HOLDINGS: readonly JevHoldingGroup[] = [
  {
    holding_id: "holding-gastro-sur",
    holding_name: "Holding Gastronomía del Sur",
    total_decisions: 10270,
    total_cost_usd: 1.40,
    total_cost_clp: 1330,
    total_credits_deducted: 10350,
    avg_latency_ms: 16.5,
    tenants: MOCK_JEV_TENANTS.filter((t) => t.holding_id === "holding-gastro-sur"),
  },
  {
    holding_id: "holding-andes",
    holding_name: "Grupo Restaurantero Andes",
    total_decisions: 2210,
    total_cost_usd: 0.445,
    total_cost_clp: 422.75,
    total_credits_deducted: 2150,
    avg_latency_ms: 22.5,
    tenants: MOCK_JEV_TENANTS.filter((t) => t.holding_id === "holding-andes"),
  },
];

export const MOCK_JEV_CONSUMPTION: JevConsumptionSummaryResponse = {
  total_decisions_all: 12480,
  total_cost_usd_all: 1.845,
  total_cost_clp_all: 1752.75,
  total_credits_deducted_all: 12500,
  avg_latency_ms_all: 18.4,
  total_auto_accepted_all: 11250,
  total_flagged_warning_all: 980,
  total_fallback_llm_all: 250,
  estimated_savings_usd_all: 485.60,
  estimated_savings_clp_all: 461320,
  holdings: MOCK_JEV_HOLDINGS,
  tenants: MOCK_JEV_TENANTS,
  all_logs: MOCK_JEV_LOGS,
  page: 1,
  page_size: 50,
  total_logs_count: 12480,
};


