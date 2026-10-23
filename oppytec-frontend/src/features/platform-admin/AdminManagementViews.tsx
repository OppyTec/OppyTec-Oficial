import {
  Archive,
  ArrowLeft,
  Check,
  CheckSquare,
  ExternalLink,
  Layers,
  Sparkles,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiRequest, setHttpRequestContext } from "@/shared/api/httpClient";
import { Can } from "@/shared/auth/Can";
import {
  DynamicAdminForm,
  DynamicAdminTable,
  type FormFieldDef,
} from "@/shared/components/admin";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

function useSafeNavigate(): (path: string) => void {
  try {
    return useNavigate();
  } catch {
    return (path: string) => {
      if (typeof window !== "undefined") {
        window.location.hash = path;
      }
    };
  }
}

function useSafeSearchParams(): [URLSearchParams, (params: URLSearchParams) => void] {
  try {
    return useSearchParams();
  } catch {
    return [new URLSearchParams(), () => {}];
  }
}

export interface PlanCatalogItem {
  readonly slug: string;
  readonly name: string;
  readonly max_active_users: number;
  readonly max_products: number;
  readonly max_suppliers: number;
  readonly max_recipes: number;
  readonly max_combos: number;
  readonly max_storage_mb: number;
  readonly included_modules: readonly string[];
  readonly price_clp: string;
  readonly price_usd: string;
  readonly price_eur: string;
  readonly price_brl: string;
}

export interface HoldingRecordItem {
  readonly holding_id: string;
  readonly name: string;
  readonly plan_slug: string;
  readonly max_active_users: number;
  readonly max_storage_mb: number;
  readonly custom_max_products_override?: number | null;
  readonly custom_max_suppliers_override?: number | null;
  readonly is_active?: boolean;
}

export interface LegalEntityRecordItem {
  readonly entity_id: string;
  readonly holding_id: string;
  readonly tax_id: string;
  readonly legal_name: string;
  readonly legal_address?: string | null;
  readonly is_active?: boolean;
  readonly tenants_count?: number;
}

export interface TenantRecordItem {
  readonly tenant_id: string;
  readonly holding_id: string;
  readonly legal_entity_id?: string | null;
  readonly schema_name: string;
  readonly display_name: string;
  readonly base_currency: string;
  readonly enabled_modules: readonly string[];
  readonly custom_max_users_override?: number | null;
  readonly custom_max_products_override?: number | null;
  readonly custom_max_suppliers_override?: number | null;
  readonly custom_max_recipes_override?: number | null;
  readonly custom_max_combos_override?: number | null;
  readonly custom_storage_mb_override?: number | null;
  readonly is_active?: boolean;
  readonly business_type?: string;
}

export interface ClientUserRecordItem {
  readonly user_id: number;
  readonly holding_id: string;
  readonly tenant_id: string;
  readonly username: string;
  readonly email: string;
  readonly first_name: string;
  readonly last_name: string;
  readonly phone?: string;
  readonly role_slug: string;
  readonly hierarchy_rank: number;
  readonly is_holding_owner: boolean;
  readonly is_deleted: boolean;
}

export interface GlobalUserRecordItem {
  readonly id: number;
  readonly username: string;
  readonly first_name: string;
  readonly last_name: string;
  readonly email: string;
  readonly phone?: string;
  readonly role: string;
  readonly is_superuser: boolean;
  readonly is_active: boolean;
}

/**
 * Los 10 Módulos y Submódulos Oficiales del Plan Básico ("Núcleo Base de Control").
 */
export const PLAN_BASICO_10_MODULE_SLUGS = [
  "inicio",
  "operations.consumption_log",
  "inventory.stock",
  "catalog.products",
  "inventory.mermas",
  "inventory.counts",
  "notifications",
  "alerts",
  "audit.history",
  "identity.users",
] as const;

export const SAAS_MODULE_TREE = [
  {
    slug: "inicio",
    label: "1. Inicio (Dashboard Operativo Adaptativo)",
    isBasicPlanCore: true,
    children: [],
  },
  {
    slug: "operations",
    label: "2. Consumo y Operaciones",
    isBasicPlanCore: false,
    children: [
      {
        slug: "operations.consumption_log",
        label: "Registro de Consumo (Táctil / Plan Básico)",
        isBasicPlanCore: true,
      },
      {
        slug: "operations.voice_handsfree",
        label: "Manos Libres (Voz)",
        isBasicPlanCore: false,
      },
      {
        slug: "operations.buffet",
        label: "Buffet Inteligente",
        isBasicPlanCore: false,
      },
      {
        slug: "operations.pos",
        label: "Punto de Venta (Ventas Comerciales)",
        isBasicPlanCore: false,
      },
    ],
  },
  {
    slug: "inventory",
    label: "3. Inventario, Recuento y Mermas",
    isBasicPlanCore: false,
    children: [
      {
        slug: "inventory.stock",
        label: "Registro de Stock (Entradas Directas)",
        isBasicPlanCore: true,
      },
      {
        slug: "inventory.mermas",
        label: "Gestión de Mermas (Merma Operativa)",
        isBasicPlanCore: true,
      },
      {
        slug: "inventory.counts",
        label: "Recuentos Físicos e Historial (Plan Básico)",
        isBasicPlanCore: true,
      },
      {
        slug: "inventory.multiwarehouse",
        label: "Multi-Bodega Avanzado",
        isBasicPlanCore: false,
      },
    ],
  },
  {
    slug: "catalog",
    label: "4. Catálogo y Productos",
    isBasicPlanCore: false,
    children: [
      {
        slug: "catalog.products",
        label: "Gestión de Productos (3 Capas)",
        isBasicPlanCore: true,
      },
      {
        slug: "catalog.categories",
        label: "Categorías y Familias",
        isBasicPlanCore: false,
      },
      {
        slug: "catalog.import_ai",
        label: "Importador Excel Inteligente",
        isBasicPlanCore: false,
      },
    ],
  },
  {
    slug: "recipes",
    label: "5. Recetas y Escandallos",
    isBasicPlanCore: false,
    children: [
      {
        slug: "recipes.standard",
        label: "Fichas Técnicas y Sub-Recetas",
        isBasicPlanCore: false,
      },
      {
        slug: "recipes.combos",
        label: "Combos y Menús Degustación",
        isBasicPlanCore: false,
      },
    ],
  },
  {
    slug: "procurement",
    label: "6. Compras y Proveedores",
    isBasicPlanCore: false,
    children: [
      {
        slug: "procurement.suppliers",
        label: "Gestión de Proveedores",
        isBasicPlanCore: false,
      },
      {
        slug: "procurement.invoices_ocr",
        label: "Recepción Facturas DTE + AI OCR",
        isBasicPlanCore: false,
      },
    ],
  },
  {
    slug: "platform_core",
    label: "7. Notificaciones, Alertas y Auditoría",
    isBasicPlanCore: false,
    children: [
      {
        slug: "notifications",
        label: "Notificaciones Operativas",
        isBasicPlanCore: true,
      },
      {
        slug: "alerts",
        label: "Alertas de Desviación y Stock Mínimo",
        isBasicPlanCore: true,
      },
      {
        slug: "audit.history",
        label: "Historial de Movimientos y Auditoría",
        isBasicPlanCore: true,
      },
    ],
  },
  {
    slug: "identity",
    label: "8. Usuarios y Control de Acceso",
    isBasicPlanCore: false,
    children: [
      {
        slug: "identity.users",
        label: "Gestión de Usuarios del Local",
        isBasicPlanCore: true,
      },
      {
        slug: "identity.rbac_matrix",
        label: "Matriz RBAC y Permisos Temporales JIT",
        isBasicPlanCore: false,
      },
    ],
  },
] as const;

const INITIAL_PLANS_FALLBACK: readonly PlanCatalogItem[] = [
  {
    slug: "basic",
    name: "Plan Básico (Control de Inventario)",
    max_active_users: 5,
    max_products: 500,
    max_suppliers: 20,
    max_recipes: 0,
    max_combos: 0,
    max_storage_mb: 512,
    included_modules: [...PLAN_BASICO_10_MODULE_SLUGS],
    price_clp: "34990.00",
    price_usd: "39.00",
    price_eur: "35.00",
    price_brl: "195.00",
  },
  {
    slug: "starter",
    name: "Plan Esencial Gastronómico",
    max_active_users: 10,
    max_products: 1500,
    max_suppliers: 50,
    max_recipes: 100,
    max_combos: 30,
    max_storage_mb: 2048,
    included_modules: [
      ...PLAN_BASICO_10_MODULE_SLUGS,
      "recipes.standard",
      "procurement.suppliers",
    ],
    price_clp: "69990.00",
    price_usd: "79.00",
    price_eur: "72.00",
    price_brl: "390.00",
  },
  {
    slug: "enterprise",
    name: "Plan Corporativo / Multi-Cadena",
    max_active_users: 50,
    max_products: 10000,
    max_suppliers: 300,
    max_recipes: 2000,
    max_combos: 500,
    max_storage_mb: 10240,
    included_modules: [
      ...PLAN_BASICO_10_MODULE_SLUGS,
      "recipes.standard",
      "recipes.combos",
      "procurement.suppliers",
      "procurement.invoices_ocr",
      "inventory.multiwarehouse",
      "oppy_ai",
    ],
    price_clp: "149990.00",
    price_usd: "165.00",
    price_eur: "150.00",
    price_brl: "850.00",
  },
];

/* =========================================================================
 * 1. VISTA: GRUPOS (HOLDINGS) — DynamicAdminTable + DynamicAdminForm Modal
 * ========================================================================= */
export function AdminHoldingsView() {
  const navigate = useSafeNavigate();
  const [holdings, setHoldings] = useState<readonly HoldingRecordItem[]>(() => [
    {
      holding_id: "holding_genesis",
      name: "Holding Principal Génesis",
      plan_slug: "basic",
      max_active_users: 5,
      max_storage_mb: 512,
      is_active: true,
    },
    {
      holding_id: "holding_pacifico",
      name: "Grupo Gastronómico Pacífico SpA",
      plan_slug: "starter",
      max_active_users: 10,
      max_storage_mb: 2048,
      is_active: true,
    },
  ]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingHolding, setEditingHolding] = useState<HoldingRecordItem | null>(null);

  const fetchHoldings = () => {
    apiRequest<HoldingRecordItem[]>("/tenancy/holdings", {
      fallbackData: [
        {
          holding_id: "holding_genesis",
          name: "Holding Principal Génesis",
          plan_slug: "basic",
          max_active_users: 5,
          max_storage_mb: 512,
          is_active: true,
        },
        {
          holding_id: "holding_pacifico",
          name: "Grupo Gastronómico Pacífico SpA",
          plan_slug: "starter",
          max_active_users: 10,
          max_storage_mb: 2048,
          is_active: true,
        },
      ],
    })
      .then((res) => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setHoldings(res.data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchHoldings();
  }, []);

  const handleCreate = () => {
    setEditingHolding(null);
    setIsModalOpen(true);
  };

  const handleEdit = (holding: HoldingRecordItem) => {
    setEditingHolding(holding);
    setIsModalOpen(true);
  };

  const handleDelete = async (holding: HoldingRecordItem) => {
    if (
      confirm(
        translateKey("platform_admin", "holdings.confirm_delete", {
          name: holding.name,
          defaultValue: `¿Estás seguro de eliminar el holding "${holding.name}"?`,
        })
      )
    ) {
      setHoldings((prev) => prev.filter((h) => h.holding_id !== holding.holding_id));
    }
  };

  const handleModalSubmit = async (formData: Record<string, unknown>) => {
    const isEdit = Boolean(editingHolding);
    const apiPayload = {
      name: String(formData.name ?? "").trim(),
      plan_slug: String(formData.plan_slug ?? "basic"),
      max_active_users: Number(formData.max_active_users ?? 5),
      max_storage_mb: Number(formData.max_storage_mb ?? 512),
      custom_max_products_override: formData.custom_max_products_override
        ? Number(formData.custom_max_products_override)
        : null,
    };

    if (isEdit && editingHolding) {
      const updated: HoldingRecordItem = {
        ...editingHolding,
        ...apiPayload,
        is_active: formData.is_active !== false,
      };
      setHoldings((prev) =>
        prev.map((h) => (h.holding_id === editingHolding.holding_id ? updated : h))
      );
    } else {
      const newItem: HoldingRecordItem = {
        holding_id: `holding_${Date.now()}`,
        ...apiPayload,
        is_active: formData.is_active !== false,
      };
      await apiRequest<HoldingRecordItem>("/tenancy/holdings", {
        method: "POST",
        body: apiPayload,
        fallbackData: newItem,
      });
      setHoldings((prev) => [...prev, newItem]);
    }
    return true;
  };

  const columns = [
    {
      key: "holding_id",
      label: translateKey("platform_admin", "holdings.col_id", { defaultValue: "ID" }),
      render: (row: HoldingRecordItem) => (
        <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-[10px] text-muted-foreground">
          {row.holding_id}
        </code>
      ),
    },
    {
      key: "name",
      label: translateKey("platform_admin", "holdings.col_name", { defaultValue: "Nombre Comercial" }),
      render: (row: HoldingRecordItem) => (
        <span className="font-semibold text-foreground">{row.name}</span>
      ),
    },
    {
      key: "plan_slug",
      label: translateKey("platform_admin", "holdings.col_plan", { defaultValue: "Plan SaaS" }),
      render: (row: HoldingRecordItem) => (
        <span className="rounded bg-primary/15 px-2 py-0.5 font-mono text-[10px] font-bold text-primary">
          {row.plan_slug}
        </span>
      ),
    },
    {
      key: "max_active_users",
      label: translateKey("platform_admin", "holdings.col_users", { defaultValue: "Cupo Usuarios" }),
      render: (row: HoldingRecordItem) => (
        <span className="font-mono text-xs">{row.max_active_users}</span>
      ),
    },
    {
      key: "max_storage_mb",
      label: translateKey("platform_admin", "holdings.col_storage", { defaultValue: "R2 Disco (MB)" }),
      render: (row: HoldingRecordItem) => (
        <span className="font-mono text-xs">{row.max_storage_mb} MB</span>
      ),
    },
    {
      key: "is_active",
      label: translateKey("platform_admin", "holdings.col_status", { defaultValue: "Estado" }),
      render: (row: HoldingRecordItem) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            row.is_active !== false
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-destructive/20 text-destructive"
          }`}
        >
          {row.is_active !== false
            ? translateKey("platform_admin", "holdings.status_active", { defaultValue: "Activo" })
            : translateKey("platform_admin", "holdings.status_inactive", { defaultValue: "Inactivo" })}
        </span>
      ),
    },
    {
      key: "actions_view",
      label: translateKey("platform_admin", "holdings.col_view", { defaultValue: "Ver" }),
      render: (row: HoldingRecordItem) => (
        <button
          type="button"
          onClick={() => navigate(`/admin/tenants?holding_id=${row.holding_id}`)}
          className="rounded border border-border bg-card px-2.5 py-1 text-[11px] font-semibold text-foreground hover:bg-secondary transition-colors"
        >
          {translateKey("platform_admin", "holdings.view_tenants_btn", { defaultValue: "Ver Tenants" })}
        </button>
      ),
    },
  ];

  const formFields: FormFieldDef[] = [
    {
      name: "name",
      label: translateKey("platform_admin", "holdings.field_name", {
        defaultValue: "Nombre Comercial del Holding",
      }),
      type: "text",
      required: true,
      placeholder: translateKey("platform_admin", "holdings.field_name_placeholder", {
        defaultValue: "Ej: Grupo Gastronómico Pacífico SpA",
      }),
    },
    {
      name: "plan_slug",
      label: translateKey("platform_admin", "holdings.field_plan", {
        defaultValue: "Plan Comercial Base",
      }),
      type: "select",
      required: true,
      options: [
        { label: "Plan Básico (10 Módulos de Control)", value: "basic" },
        { label: "Plan Esencial Gastronómico", value: "starter" },
        { label: "Plan Corporativo / Multi-Cadena", value: "enterprise" },
      ],
    },
    {
      name: "max_active_users",
      label: translateKey("platform_admin", "holdings.field_users", {
        defaultValue: "Cupo de Usuarios Activos",
      }),
      type: "number",
      required: true,
    },
    {
      name: "max_storage_mb",
      label: translateKey("platform_admin", "holdings.field_storage", {
        defaultValue: "Cuota de Almacenamiento R2 (MB)",
      }),
      type: "number",
      required: true,
    },
    {
      name: "custom_max_products_override",
      label: translateKey("platform_admin", "holdings.field_products_override", {
        defaultValue: "Override Máx. Productos (Opcional)",
      }),
      type: "number",
      description: translateKey("platform_admin", "holdings.field_products_override_desc", {
        defaultValue: "Dejar en 0 para heredar del Plan",
      }),
    },
    {
      name: "is_active",
      label: translateKey("platform_admin", "holdings.field_is_active", {
        defaultValue: "Estado de la Cuenta",
      }),
      type: "boolean",
    },
  ];

  return (
    <div data-testid="admin-holdings-view" className="p-6 md:p-8 space-y-6">
      <DynamicAdminTable<HoldingRecordItem>
        title={translateKey("platform_admin", "holdings.title", { defaultValue: "Grupos (Holdings)" })}
        description={translateKey("platform_admin", "holdings.description", {
          defaultValue: "Gestión de grupos empresariales principales y asignación de planes comerciales.",
        })}
        data={holdings}
        columns={columns}
        loading={loading}
        onCreate={handleCreate}
        createButtonLabel={translateKey("platform_admin", "holdings.create_btn", { defaultValue: "Nuevo Holding" })}
        createPermission="platform_admin.holdings.manage"
        onEdit={handleEdit}
        editPermission="platform_admin.holdings.manage"
        onDelete={handleDelete}
        deletePermission="platform_admin.holdings.manage"
        primaryKey="holding_id"
        testId="holdings-table"
      />

      <DynamicAdminForm
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        title={
          editingHolding
            ? translateKey("platform_admin", "holdings.edit_title", { defaultValue: "Editar Holding" })
            : translateKey("platform_admin", "holdings.new_title", { defaultValue: "Nuevo Holding" })
        }
        description={translateKey("platform_admin", "holdings.form_description", {
          defaultValue: "Configura la razón matriz y los techos de cuotas corporativas.",
        })}
        fields={formFields}
        initialData={
          editingHolding
            ? {
                name: editingHolding.name,
                plan_slug: editingHolding.plan_slug,
                max_active_users: editingHolding.max_active_users,
                max_storage_mb: editingHolding.max_storage_mb,
                custom_max_products_override:
                  editingHolding.custom_max_products_override ?? 0,
                is_active: editingHolding.is_active !== false,
              }
            : null
        }
        onSubmit={handleModalSubmit}
        testId="admin-create-holding-form"
      />
    </div>
  );
}

/* =========================================================================
 * 2. VISTA: ENTIDADES LEGALES (RUT 1:1) — DynamicAdminTable + DynamicAdminForm
 * ========================================================================= */
export function AdminLegalEntitiesView() {
  const [entities, setEntities] = useState<readonly LegalEntityRecordItem[]>(() => [
    {
      entity_id: "le_genesis",
      holding_id: "holding_genesis",
      tax_id: "76.000.000-1",
      legal_name: "OppyTec SaaS SpA",
      legal_address: "Av. Providencia 1200, Santiago",
      is_active: true,
      tenants_count: 1,
    },
    {
      entity_id: "le_pacifico",
      holding_id: "holding_pacifico",
      tax_id: "77.123.456-K",
      legal_name: "Inversiones Gastronómicas Pacífico SpA",
      legal_address: "Costanera Center 2400, Santiago",
      is_active: true,
      tenants_count: 1,
    },
  ]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingEntity, setEditingEntity] = useState<LegalEntityRecordItem | null>(null);

  const fetchEntities = () => {
    apiRequest<LegalEntityRecordItem[]>("/tenancy/legal-entities", {
      fallbackData: [
        {
          entity_id: "le_genesis",
          holding_id: "holding_genesis",
          tax_id: "76.000.000-1",
          legal_name: "OppyTec SaaS SpA",
          legal_address: "Av. Providencia 1200, Santiago",
          is_active: true,
          tenants_count: 1,
        },
        {
          entity_id: "le_pacifico",
          holding_id: "holding_pacifico",
          tax_id: "77.123.456-K",
          legal_name: "Inversiones Gastronómicas Pacífico SpA",
          legal_address: "Costanera Center 2400, Santiago",
          is_active: true,
          tenants_count: 1,
        },
      ],
    })
      .then((res) => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setEntities(res.data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchEntities();
  }, []);

  const handleCreate = () => {
    setEditingEntity(null);
    setIsModalOpen(true);
  };

  const handleEdit = (entity: LegalEntityRecordItem) => {
    setEditingEntity(entity);
    setIsModalOpen(true);
  };

  const handleDelete = (entity: LegalEntityRecordItem) => {
    if (
      confirm(
        translateKey("platform_admin", "legal_entities.confirm_delete", {
          name: entity.legal_name,
          defaultValue: `¿Eliminar la entidad legal ${entity.legal_name}?`,
        })
      )
    ) {
      setEntities((prev) => prev.filter((e) => e.entity_id !== entity.entity_id));
    }
  };

  const handleModalSubmit = async (formData: Record<string, unknown>) => {
    const apiPayload = {
      holding_id: String(formData.holding_id ?? "holding_genesis"),
      tax_id: String(formData.tax_id ?? "").trim(),
      legal_name: String(formData.legal_name ?? "").trim(),
      legal_address: String(formData.legal_address ?? "").trim() || null,
    };

    if (editingEntity) {
      const updated: LegalEntityRecordItem = {
        ...editingEntity,
        ...apiPayload,
        is_active: formData.is_active !== false,
      };
      setEntities((prev) =>
        prev.map((e) => (e.entity_id === editingEntity.entity_id ? updated : e))
      );
    } else {
      const newItem: LegalEntityRecordItem = {
        entity_id: `le_${Date.now()}`,
        ...apiPayload,
        is_active: formData.is_active !== false,
        tenants_count: 0,
      };
      await apiRequest<LegalEntityRecordItem>("/tenancy/legal-entities", {
        method: "POST",
        body: apiPayload,
        fallbackData: newItem,
      });
      setEntities((prev) => [...prev, newItem]);
    }
    return true;
  };

  const columns = [
    {
      key: "tax_id",
      label: translateKey("platform_admin", "legal_entities.col_tax_id", { defaultValue: "RUT / Tax ID" }),
      render: (row: LegalEntityRecordItem) => (
        <span className="font-mono font-bold text-primary">{row.tax_id}</span>
      ),
    },
    {
      key: "legal_name",
      label: translateKey("platform_admin", "legal_entities.col_legal_name", { defaultValue: "Razón Social" }),
      render: (row: LegalEntityRecordItem) => (
        <span className="font-semibold text-foreground">{row.legal_name}</span>
      ),
    },
    {
      key: "holding_id",
      label: translateKey("platform_admin", "legal_entities.col_holding", { defaultValue: "Holding Perteneciente" }),
      render: (row: LegalEntityRecordItem) => (
        <span className="font-mono text-xs text-muted-foreground">{row.holding_id}</span>
      ),
    },
    {
      key: "legal_address",
      label: translateKey("platform_admin", "legal_entities.col_address", { defaultValue: "Dirección Tributaria" }),
      render: (row: LegalEntityRecordItem) => (
        <span className="text-xs text-muted-foreground truncate max-w-[200px] block">
          {row.legal_address || "—"}
        </span>
      ),
    },
    {
      key: "tenants_count",
      label: translateKey("platform_admin", "legal_entities.col_tenants_count", { defaultValue: "Tenants Asociados" }),
      render: (row: LegalEntityRecordItem) => (
        <span className="rounded bg-secondary px-2 py-0.5 font-mono text-[10px] font-bold text-foreground">
          {row.tenants_count ?? 1}
        </span>
      ),
    },
    {
      key: "is_active",
      label: translateKey("platform_admin", "legal_entities.col_status", { defaultValue: "Estado" }),
      render: (row: LegalEntityRecordItem) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            row.is_active !== false
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-destructive/20 text-destructive"
          }`}
        >
          {row.is_active !== false
            ? translateKey("platform_admin", "legal_entities.status_active", { defaultValue: "Activo" })
            : translateKey("platform_admin", "legal_entities.status_inactive", { defaultValue: "Inactivo" })}
        </span>
      ),
    },
  ];

  const formFields: FormFieldDef[] = [
    {
      name: "tax_id",
      label: translateKey("platform_admin", "legal_entities.field_tax_id", {
        defaultValue: "RUT / Tax ID Tributario",
      }),
      type: "text",
      required: true,
      placeholder: translateKey("platform_admin", "legal_entities.field_tax_id_placeholder", {
        defaultValue: "Ej: 76.543.210-K",
      }),
    },
    {
      name: "legal_name",
      label: translateKey("platform_admin", "legal_entities.field_legal_name", {
        defaultValue: "Razón Social",
      }),
      type: "text",
      required: true,
      placeholder: translateKey("platform_admin", "legal_entities.field_legal_name_placeholder", {
        defaultValue: "Ej: Inversiones Gastronómicas SpA",
      }),
    },
    {
      name: "holding_id",
      label: translateKey("platform_admin", "legal_entities.field_holding", {
        defaultValue: "Holding Perteneciente",
      }),
      type: "select",
      required: true,
      options: [
        { label: "Holding Principal Génesis", value: "holding_genesis" },
        { label: "Grupo Gastronómico Pacífico SpA", value: "holding_pacifico" },
      ],
    },
    {
      name: "legal_address",
      label: translateKey("platform_admin", "legal_entities.field_address", {
        defaultValue: "Dirección Tributaria",
      }),
      type: "text",
      placeholder: translateKey("platform_admin", "legal_entities.field_address_placeholder", {
        defaultValue: "Av. Providencia 1200, Santiago",
      }),
    },
    {
      name: "is_active",
      label: translateKey("platform_admin", "legal_entities.field_is_active", {
        defaultValue: "Estado de la Sociedad",
      }),
      type: "boolean",
    },
  ];

  return (
    <div data-testid="admin-legal-entities-view" className="p-6 md:p-8 space-y-6">
      <DynamicAdminTable<LegalEntityRecordItem>
        title={translateKey("platform_admin", "legal_entities.title", { defaultValue: "Entidades Legales" })}
        description={translateKey("platform_admin", "legal_entities.description", {
          defaultValue: "Gestión de empresas facturadoras y razones sociales (RUT 1:1 con locales).",
        })}
        data={entities}
        columns={columns}
        loading={loading}
        onCreate={handleCreate}
        createButtonLabel={translateKey("platform_admin", "legal_entities.create_btn", {
          defaultValue: "Nueva Entidad Legal",
        })}
        createPermission="platform_admin.legal_entities.manage"
        onEdit={handleEdit}
        editPermission="platform_admin.legal_entities.manage"
        onDelete={handleDelete}
        deletePermission="platform_admin.legal_entities.manage"
        primaryKey="entity_id"
        testId="legal-entities-table"
      />

      <DynamicAdminForm
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        title={
          editingEntity
            ? translateKey("platform_admin", "legal_entities.edit_title", { defaultValue: "Editar Entidad Legal" })
            : translateKey("platform_admin", "legal_entities.new_title", { defaultValue: "Nueva Entidad Legal" })
        }
        description={translateKey("platform_admin", "legal_entities.form_description", {
          defaultValue: "Ingresa los datos tributarios según facturación legal.",
        })}
        fields={formFields}
        initialData={
          editingEntity
            ? {
                tax_id: editingEntity.tax_id,
                legal_name: editingEntity.legal_name,
                holding_id: editingEntity.holding_id,
                legal_address: editingEntity.legal_address ?? "",
                is_active: editingEntity.is_active !== false,
              }
            : null
        }
        onSubmit={handleModalSubmit}
        testId="admin-create-legal-entity-form"
      />
    </div>
  );
}

/* =========================================================================
 * 3. VISTA: INQUILINOS (TENANTS) — DynamicAdminTable + Árbol Modal Legacy
 * ========================================================================= */
export function AdminTenantsView() {
  const navigate = useSafeNavigate();
  const [searchParams] = useSafeSearchParams();
  const holdingFilter = searchParams.get("holding_id");

  const [tenants, setTenants] = useState<readonly TenantRecordItem[]>(() => [
    {
      tenant_id: "tenant_genesis",
      holding_id: "holding_genesis",
      legal_entity_id: "le_genesis",
      schema_name: "tenant_genesis",
      display_name: "Local Central Génesis",
      base_currency: "CLP",
      enabled_modules: [...PLAN_BASICO_10_MODULE_SLUGS],
      business_type: "Restaurante a la Carta",
      is_active: true,
    },
    {
      tenant_id: "tenant_pacifico_centro",
      holding_id: "holding_pacifico",
      legal_entity_id: "le_pacifico",
      schema_name: "tenant_pacifico_centro",
      display_name: "Sucursal Pacífico Centro",
      base_currency: "CLP",
      enabled_modules: [...PLAN_BASICO_10_MODULE_SLUGS],
      business_type: "Restaurante a la Carta",
      is_active: true,
    },
  ]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingTenant, setEditingTenant] = useState<TenantRecordItem | null>(null);

  // Campos específicos del Modal
  const [schemaInput, setSchemaInput] = useState<string>("");
  const [slugInput, setSlugInput] = useState<string>("");
  const [nameInput, setNameInput] = useState<string>("");
  const [holdingIdInput, setHoldingIdInput] = useState<string>("holding_genesis");
  const [legalEntityIdInput, setLegalEntityIdInput] = useState<string>("le_genesis");
  const [currencyInput, setCurrencyInput] = useState<string>("CLP");
  const [enabledModules, setEnabledModules] = useState<readonly string[]>(
    PLAN_BASICO_10_MODULE_SLUGS
  );
  const [prodOverride, setProdOverride] = useState<string>("");
  const [suppOverride, setSuppOverride] = useState<string>("");
  const [impersonateNotice, setImpersonateNotice] = useState<string | null>(null);

  const fetchTenants = () => {
    apiRequest<TenantRecordItem[]>("/tenancy/tenants", {
      fallbackData: [
        {
          tenant_id: "tenant_genesis",
          holding_id: "holding_genesis",
          legal_entity_id: "le_genesis",
          schema_name: "tenant_genesis",
          display_name: "Local Central Génesis",
          base_currency: "CLP",
          enabled_modules: [...PLAN_BASICO_10_MODULE_SLUGS],
          business_type: "Restaurante a la Carta",
          is_active: true,
        },
        {
          tenant_id: "tenant_pacifico_centro",
          holding_id: "holding_pacifico",
          legal_entity_id: "le_pacifico",
          schema_name: "tenant_pacifico_centro",
          display_name: "Sucursal Pacífico Centro",
          base_currency: "CLP",
          enabled_modules: [...PLAN_BASICO_10_MODULE_SLUGS],
          business_type: "Restaurante a la Carta",
          is_active: true,
        },
      ],
    })
      .then((res) => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setTenants(res.data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTenants();
  }, []);

  const displayTenants = useMemo(() => {
    if (!holdingFilter) return tenants;
    return tenants.filter((t) => t.holding_id === holdingFilter);
  }, [tenants, holdingFilter]);

  const handleCreate = () => {
    setEditingTenant(null);
    setSchemaInput("");
    setSlugInput("");
    setNameInput("");
    setHoldingIdInput(holdingFilter || "holding_genesis");
    setLegalEntityIdInput("le_genesis");
    setCurrencyInput("CLP");
    setEnabledModules(PLAN_BASICO_10_MODULE_SLUGS);
    setProdOverride("");
    setSuppOverride("");
    setIsModalOpen(true);
  };

  const handleEdit = (tenant: TenantRecordItem) => {
    setEditingTenant(tenant);
    setSchemaInput(tenant.schema_name);
    setSlugInput(tenant.schema_name.replace(/^tenant_/, ""));
    setNameInput(tenant.display_name);
    setHoldingIdInput(tenant.holding_id);
    setLegalEntityIdInput(tenant.legal_entity_id || "le_genesis");
    setCurrencyInput(tenant.base_currency);
    setEnabledModules(tenant.enabled_modules);
    setProdOverride(
      tenant.custom_max_products_override
        ? String(tenant.custom_max_products_override)
        : ""
    );
    setSuppOverride(
      tenant.custom_max_suppliers_override
        ? String(tenant.custom_max_suppliers_override)
        : ""
    );
    setIsModalOpen(true);
  };

  const handleDelete = (tenant: TenantRecordItem) => {
    if (
      confirm(
        translateKey("platform_admin", "tenants_view.confirm_delete", {
          name: tenant.display_name,
          defaultValue: `¿Eliminar la sucursal ${tenant.display_name}?`,
        })
      )
    ) {
      setTenants((prev) => prev.filter((t) => t.tenant_id !== tenant.tenant_id));
    }
  };

  const handleImpersonate = async (tenant: TenantRecordItem) => {
    const res = await apiRequest<{
      readonly access_token: string;
      readonly tenant_id: string;
      readonly holding_id: string;
      readonly schema_name: string;
    }>("/tenancy/admin/impersonate", {
      method: "POST",
      body: {
        tenant_id: tenant.tenant_id,
        reason: `Soporte administrativo en ${tenant.display_name}`,
      },
      fallbackData: {
        access_token: "impersonated-support-token",
        tenant_id: tenant.tenant_id,
        holding_id: tenant.holding_id,
        schema_name: tenant.schema_name,
      },
    });

    setHttpRequestContext({
      tenantId: res.data.tenant_id,
      holdingId: res.data.holding_id,
      accessToken: res.data.access_token,
    });
    setImpersonateNotice(
      translateKey("platform_admin", "tenants_view.impersonate_notice", {
        name: tenant.display_name,
        schema: res.data.schema_name,
        defaultValue: `Entrando en modo soporte auditado a "${tenant.display_name}" (${res.data.schema_name})`,
      })
    );
  };

  const toggleModule = (modSlug: string) => {
    setEnabledModules((prev) =>
      prev.includes(modSlug)
        ? prev.filter((m) => m !== modSlug)
        : [...prev, modSlug]
    );
  };

  const handleSaveModal = async (e: FormEvent) => {
    e.preventDefault();
    if (!nameInput.trim()) return;

    const cleanSlug = (slugInput || nameInput)
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_]+/g, "_");
    const schema = cleanSlug.startsWith("tenant_") ? cleanSlug : `tenant_${cleanSlug}`;

    const apiPayload = {
      holding_id: holdingIdInput,
      legal_entity_id: legalEntityIdInput,
      slug: cleanSlug,
      display_name: nameInput.trim(),
      base_currency: currencyInput,
      enabled_modules: [...enabledModules],
      custom_max_products_override: prodOverride ? Number(prodOverride) : null,
      custom_max_suppliers_override: suppOverride ? Number(suppOverride) : null,
    };

    if (editingTenant) {
      const updated: TenantRecordItem = {
        ...editingTenant,
        ...apiPayload,
        is_active: true,
      };
      setTenants((prev) =>
        prev.map((t) => (t.tenant_id === editingTenant.tenant_id ? updated : t))
      );
    } else {
      const newItem: TenantRecordItem = {
        tenant_id: `t_${Date.now()}`,
        schema_name: schema,
        ...apiPayload,
        is_active: true,
      };
      await apiRequest<TenantRecordItem>("/tenancy/tenants", {
        method: "POST",
        body: apiPayload,
        fallbackData: newItem,
      });
      setTenants((prev) => [...prev, newItem]);
    }

    setIsModalOpen(false);
  };

  const columns = [
    {
      key: "schema_name",
      label: translateKey("platform_admin", "tenants_view.col_schema", { defaultValue: "Esquema (DB)" }),
      render: (row: TenantRecordItem) => (
        <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-[10px] text-primary">
          {row.schema_name}
        </code>
      ),
    },
    {
      key: "display_name",
      label: translateKey("platform_admin", "tenants_view.col_name", { defaultValue: "Nombre Comercial" }),
      render: (row: TenantRecordItem) => (
        <span className="font-semibold text-foreground">{row.display_name}</span>
      ),
    },
    {
      key: "business_type",
      label: translateKey("platform_admin", "tenants_view.col_business_type", { defaultValue: "Tipo Negocio" }),
      render: (row: TenantRecordItem) => (
        <span className="text-xs text-muted-foreground">
          {row.business_type || "Restaurante a la Carta"}
        </span>
      ),
    },
    {
      key: "holding_id",
      label: translateKey("platform_admin", "tenants_view.col_holding", { defaultValue: "Holding" }),
      render: (row: TenantRecordItem) => (
        <span className="font-mono text-xs text-muted-foreground">{row.holding_id}</span>
      ),
    },
    {
      key: "enabled_modules",
      label: translateKey("platform_admin", "tenants_view.col_modules", { defaultValue: "Módulos" }),
      render: (row: TenantRecordItem) => (
        <span className="rounded bg-secondary px-2 py-0.5 font-mono text-[10px] font-medium text-foreground">
          {translateKey("platform_admin", "tenants_view.modules_active_count", {
            count: row.enabled_modules.length,
            defaultValue: `${row.enabled_modules.length} activos`,
          })}
        </span>
      ),
    },
    {
      key: "is_active",
      label: translateKey("platform_admin", "tenants_view.col_status", { defaultValue: "Estado" }),
      render: (row: TenantRecordItem) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            row.is_active !== false
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-destructive/20 text-destructive"
          }`}
        >
          {row.is_active !== false
            ? translateKey("platform_admin", "tenants_view.status_active", { defaultValue: "Activo" })
            : translateKey("platform_admin", "tenants_view.status_inactive", { defaultValue: "Inactivo" })}
        </span>
      ),
    },
    {
      key: "manage",
      label: translateKey("platform_admin", "tenants_view.col_manage", { defaultValue: "Administrar" }),
      render: (row: TenantRecordItem) => (
        <Can perform="platform_admin.tenants.provision">
          <button
            type="button"
            data-testid={`impersonate-btn-${row.tenant_id}`}
            onClick={() => void handleImpersonate(row)}
            className="touch-target inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/15 text-emerald-400 px-3 py-1.5 text-xs font-semibold hover:bg-emerald-500/25 transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>{translateKey("platform_admin", "tenants_view.enter_btn", { defaultValue: "Entrar" })}</span>
          </button>
        </Can>
      ),
    },
  ];

  return (
    <div data-testid="admin-tenants-view" className="p-6 md:p-8 space-y-6">
      {holdingFilter && (
        <button
          type="button"
          onClick={() => navigate("/admin/holdings")}
          className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>
            {translateKey("platform_admin", "tenants_view.back_to_holdings", {
              defaultValue: "Volver a Grupos (Holdings)",
            })}
          </span>
        </button>
      )}

      {impersonateNotice && (
        <div
          data-testid="admin-impersonate-active-banner"
          className="rounded-xl border border-primary/40 bg-primary/10 p-4 text-xs font-semibold text-primary flex items-center justify-between"
        >
          <span>{impersonateNotice}</span>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded bg-primary text-primary-foreground px-3 py-1 text-xs"
          >
            {translateKey("platform_admin", "tenants_view.go_to_store", {
              defaultValue: "Ir al Local",
            })}
          </button>
        </div>
      )}

      <DynamicAdminTable<TenantRecordItem>
        title={
          holdingFilter
            ? translateKey("platform_admin", "tenants_view.title_filtered", {
                holdingId: holdingFilter,
                defaultValue: `Restaurantes (Tenants) del Holding "${holdingFilter}"`,
              })
            : translateKey("platform_admin", "tenants_view.title", {
                defaultValue: "Restaurantes (Tenants)",
              })
        }
        description={translateKey("platform_admin", "tenants_view.description", {
          defaultValue: "Gestión de instancias individuales operativas (Esquemas de Base de Datos PostgreSQL).",
        })}
        data={displayTenants}
        columns={columns}
        loading={loading}
        onCreate={handleCreate}
        createButtonLabel={translateKey("platform_admin", "tenants_view.create_btn", {
          defaultValue: "Nuevo Tenant",
        })}
        createPermission="platform_admin.tenants.provision"
        onEdit={handleEdit}
        editPermission="platform_admin.tenants.provision"
        onDelete={handleDelete}
        deletePermission="platform_admin.tenants.provision"
        primaryKey="tenant_id"
        testId="tenants-table"
      />

      {/* Árbol Jerárquico de Módulos (Plan Básico 10 Módulos) */}
      <div
        data-testid="tenant-module-tree"
        className="rounded-xl border border-border bg-card p-5 space-y-3"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
          <div>
            <h4 className="text-sm font-bold text-foreground">
              {translateKey("platform_admin", "tenants_view.module_tree_title", {
                defaultValue: "Árbol Oficial de Módulos y Submódulos (Plan Básico 10 Módulos)",
              })}
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              {translateKey("platform_admin", "tenants_view.module_tree_desc", {
                defaultValue: "Visualiza y selecciona los módulos base y avanzados disponibles para los locales gastronómicos.",
              })}
            </p>
          </div>
          <button
            type="button"
            data-testid="tenant-apply-plan-basico-btn"
            onClick={() => setEnabledModules(PLAN_BASICO_10_MODULE_SLUGS)}
            className="touch-target inline-flex items-center gap-1.5 rounded-lg bg-primary/15 text-primary px-3 py-1.5 text-xs font-semibold hover:bg-primary/25 transition-colors"
          >
            <CheckSquare className="h-3.5 w-3.5" />
            <span>
              {translateKey("platform_admin", "tenants_view.preset_basic_btn", {
                defaultValue: "Preset Plan Básico (10 Módulos)",
              })}
            </span>
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 pt-1">
          {SAAS_MODULE_TREE.map((root) => (
            <div
              key={root.slug}
              className="rounded-lg border border-border bg-secondary/10 p-3 space-y-1.5 text-xs"
            >
              <label className="flex items-center gap-2 font-bold text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={enabledModules.includes(root.slug)}
                  onChange={() => toggleModule(root.slug)}
                />
                <span>{root.label}</span>
              </label>

              {root.children.length > 0 && (
                <div className="pl-4 space-y-1 border-l border-border/60">
                  {root.children.map((child) => (
                    <label
                      key={child.slug}
                      className="flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        data-testid={`mod-check-${child.slug}`}
                        checked={enabledModules.includes(child.slug)}
                        onChange={() => toggleModule(child.slug)}
                      />
                      <span>└─ {child.label}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Modal Dialog para Aprovisionar / Editar Tenant y Árbol de Módulos */}
      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
        >
          <div className="glass-card w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col rounded-2xl border border-border p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3 shrink-0">
              <div>
                <h3 className="text-lg font-bold text-foreground">
                  {editingTenant
                    ? translateKey("platform_admin", "tenants_view.edit_title", { defaultValue: "Editar Tenant" })
                    : translateKey("platform_admin", "tenants_view.new_title", {
                        defaultValue: "Nuevo Tenant (Aprovisionar Local)",
                      })}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {translateKey("platform_admin", "tenants_view.description", {
                    defaultValue: "Configura esquema, moneda base y asignación de módulos y cuotas.",
                  })}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg bg-secondary p-1 text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => void handleSaveModal(e)}
              data-testid="admin-create-tenant-form"
              className="flex-1 overflow-y-auto space-y-4 py-4 pr-1 text-xs"
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1">
                  <span className="font-semibold text-foreground">Nombre Comercial</span>
                  <input
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    placeholder="Ej: Sucursal Costanera"
                    required
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                  />
                </label>
                <label className="space-y-1">
                  <span className="font-semibold text-foreground">Slug URL / Esquema</span>
                  <input
                    value={slugInput}
                    disabled={Boolean(editingTenant)}
                    onChange={(e) => setSlugInput(e.target.value)}
                    placeholder="costanera_centro"
                    required
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                  />
                  {editingTenant && schemaInput && (
                    <span className="text-[10px] text-primary font-mono block">
                      Esquema DB: {schemaInput}
                    </span>
                  )}
                </label>
                <label className="space-y-1">
                  <span className="font-semibold text-foreground">Holding Asociado</span>
                  <select
                    value={holdingIdInput}
                    onChange={(e) => setHoldingIdInput(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                  >
                    <option value="holding_genesis">Holding Principal Génesis</option>
                    <option value="holding_pacifico">Grupo Gastronómico Pacífico SpA</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="font-semibold text-foreground">Entidad Legal (RUT 1:1)</span>
                  <select
                    value={legalEntityIdInput}
                    onChange={(e) => setLegalEntityIdInput(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                  >
                    <option value="le_genesis">76.000.000-1 — OppyTec SaaS SpA</option>
                    <option value="le_pacifico">
                      77.123.456-K — Inversiones Gastronómicas Pacífico
                    </option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="font-semibold text-foreground">Moneda Base Operativa</span>
                  <select
                    value={currencyInput}
                    onChange={(e) => setCurrencyInput(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                  >
                    <option value="CLP">CLP ($) — Peso Chileno</option>
                    <option value="USD">USD ($) — Dólar Estadounidense</option>
                    <option value="EUR">EUR (€) — Euro</option>
                    <option value="BRL">BRL (R$) — Real Brasileño</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="font-semibold text-foreground">
                    Override Máx. Productos (Opcional)
                  </span>
                  <input
                    type="number"
                    value={prodOverride}
                    onChange={(e) => setProdOverride(e.target.value)}
                    placeholder="Hereda del Plan"
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                  />
                </label>
              </div>

              {/* Árbol Jerárquico de Módulos (Plan Básico 10 Módulos) */}
              <div
                data-testid="tenant-module-tree"
                className="space-y-2 pt-2 border-t border-border"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-foreground">
                    Árbol de Módulos y Submódulos Habilitados
                  </span>
                  <button
                    type="button"
                    data-testid="tenant-apply-plan-basico-btn"
                    onClick={() => setEnabledModules(PLAN_BASICO_10_MODULE_SLUGS)}
                    className="inline-flex items-center gap-1.5 rounded bg-primary/15 text-primary px-2.5 py-1 text-[11px] font-semibold hover:bg-primary/25 transition-colors"
                  >
                    <CheckSquare className="h-3.5 w-3.5" />
                    <span>Preset Plan Básico (10 Módulos)</span>
                  </button>
                </div>

                <div className="max-h-56 overflow-y-auto rounded-xl border border-border bg-secondary/15 p-3 space-y-2">
                  {SAAS_MODULE_TREE.map((root) => (
                    <div key={root.slug} className="space-y-1">
                      <label className="flex items-center gap-2 font-semibold text-foreground cursor-pointer">
                        <input
                          type="checkbox"
                          checked={enabledModules.includes(root.slug)}
                          onChange={() => toggleModule(root.slug)}
                        />
                        <span>{root.label}</span>
                        {root.isBasicPlanCore && (
                          <span className="ml-auto rounded bg-primary/15 text-primary px-1.5 py-0.5 font-mono text-[9px]">
                            Plan Básico
                          </span>
                        )}
                      </label>

                      {root.children.length > 0 && (
                        <div className="pl-5 space-y-1 border-l border-border/60">
                          {root.children.map((child) => (
                            <label
                              key={child.slug}
                              className="flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer"
                            >
                              <input
                                type="checkbox"
                                data-testid={`mod-check-${child.slug}`}
                                checked={enabledModules.includes(child.slug)}
                                onChange={() => toggleModule(child.slug)}
                              />
                              <span>└─ {child.label}</span>
                              {child.isBasicPlanCore && (
                                <span className="ml-auto rounded bg-primary/15 text-primary px-1.5 py-0.5 font-mono text-[9px]">
                                  Plan Básico
                                </span>
                              )}
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-secondary"
                >
                  {translateKey("platform_admin", "table_common.cancel", { defaultValue: "Cancelar" })}
                </button>
                <button
                  type="submit"
                  data-testid="tenant-provision-submit-btn"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-xs font-semibold shadow-sm hover:bg-primary/90"
                >
                  <Check className="h-4 w-4" />
                  <span>
                    {translateKey("platform_admin", "tenants_view.save_tenant_btn", {
                      defaultValue: "Guardar Sucursal",
                    })}
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/* =========================================================================
 * 4. VISTA: USUARIOS CLIENTES — DynamicAdminTable + DynamicAdminForm Modal
 * ========================================================================= */
export function AdminClientUsersView() {
  const [users, setUsers] = useState<readonly ClientUserRecordItem[]>(() => [
    {
      user_id: 101,
      holding_id: "holding_genesis",
      tenant_id: "tenant_genesis",
      username: "admin.local",
      email: "admin.local@restaurant.cl",
      first_name: "Administrador",
      last_name: "Sucursal",
      role_slug: "admin",
      hierarchy_rank: 10,
      is_holding_owner: false,
      is_deleted: false,
    },
    {
      user_id: 102,
      holding_id: "holding_pacifico",
      tenant_id: "tenant_pacifico_centro",
      username: "cocinero.jefe",
      email: "chef@pacifico.cl",
      first_name: "Mario",
      last_name: "Gómez",
      role_slug: "supervisor",
      hierarchy_rank: 20,
      is_holding_owner: false,
      is_deleted: false,
    },
  ]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<ClientUserRecordItem | null>(null);

  const fetchUsers = () => {
    apiRequest<ClientUserRecordItem[]>("/tenancy/client-users", {
      fallbackData: [
        {
          user_id: 101,
          holding_id: "holding_genesis",
          tenant_id: "tenant_genesis",
          username: "admin.local",
          email: "admin.local@restaurant.cl",
          first_name: "Administrador",
          last_name: "Sucursal",
          role_slug: "admin",
          hierarchy_rank: 10,
          is_holding_owner: false,
          is_deleted: false,
        },
        {
          user_id: 102,
          holding_id: "holding_pacifico",
          tenant_id: "tenant_pacifico_centro",
          username: "cocinero.jefe",
          email: "chef@pacifico.cl",
          first_name: "Mario",
          last_name: "Gómez",
          role_slug: "supervisor",
          hierarchy_rank: 20,
          is_holding_owner: false,
          is_deleted: false,
        },
      ],
    })
      .then((res) => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setUsers(res.data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreate = () => {
    setEditingUser(null);
    setIsModalOpen(true);
  };

  const handleEdit = (user: ClientUserRecordItem) => {
    setEditingUser(user);
    setIsModalOpen(true);
  };

  const handleSoftDelete = async (userId: number) => {
    await apiRequest(`/tenancy/client-users/${userId}`, {
      method: "DELETE",
      fallbackData: { success: true },
    });
    setUsers((prev) =>
      prev.map((u) => (u.user_id === userId ? { ...u, is_deleted: true } : u))
    );
  };

  const handleModalSubmit = async (formData: Record<string, unknown>) => {
    const rawRole = String(formData.role_slug ?? "admin");
    const validRoles = ["propietario", "superuser", "admin", "supervisor", "cajero"] as const;
    const resolvedRole = (validRoles.includes(rawRole as (typeof validRoles)[number])
      ? rawRole
      : "admin") as (typeof validRoles)[number];

    const apiPayload = {
      holding_id: String(formData.holding_id ?? "holding_genesis"),
      tenant_id: String(formData.tenant_id ?? "tenant_genesis"),
      username: String(formData.username ?? "").trim(),
      email: String(formData.email ?? "").trim(),
      password: String(formData.password ?? "OppyTec#2026"),
      first_name: String(formData.first_name ?? "").trim() || "Operador",
      last_name: String(formData.last_name ?? "").trim() || "Cliente",
      role_slug: resolvedRole,
      is_holding_owner: Boolean(formData.is_holding_owner),
    };

    if (editingUser) {
      const updated: ClientUserRecordItem = {
        ...editingUser,
        ...apiPayload,
        phone: String(formData.phone ?? "").trim() || undefined,
      };
      setUsers((prev) =>
        prev.map((u) => (u.user_id === editingUser.user_id ? updated : u))
      );
    } else {
      const newItem: ClientUserRecordItem = {
        user_id: Date.now(),
        hierarchy_rank: resolvedRole === "propietario" ? 5 : resolvedRole === "admin" ? 10 : 20,
        ...apiPayload,
        phone: String(formData.phone ?? "").trim() || undefined,
        is_deleted: false,
      };
      await apiRequest<ClientUserRecordItem>("/tenancy/client-users", {
        method: "POST",
        body: apiPayload,
        fallbackData: newItem,
      });
      setUsers((prev) => [...prev, newItem]);
    }
    return true;
  };

  const columns = [
    {
      key: "username",
      label: translateKey("platform_admin", "client_users.col_username", { defaultValue: "Usuario" }),
      render: (row: ClientUserRecordItem) => (
        <span className="font-semibold text-foreground">{row.username}</span>
      ),
    },
    {
      key: "full_name",
      label: translateKey("platform_admin", "client_users.col_full_name", { defaultValue: "Nombre Completo" }),
      render: (row: ClientUserRecordItem) => (
        <span>{`${row.first_name} ${row.last_name}`}</span>
      ),
    },
    {
      key: "email",
      label: translateKey("platform_admin", "client_users.col_email", { defaultValue: "Email" }),
      render: (row: ClientUserRecordItem) => (
        <span className="font-mono text-xs text-muted-foreground">{row.email}</span>
      ),
    },
    {
      key: "role_slug",
      label: translateKey("platform_admin", "client_users.col_role", { defaultValue: "Rol" }),
      render: (row: ClientUserRecordItem) => (
        <span className="rounded bg-primary/15 px-2 py-0.5 font-mono text-[10px] font-bold text-primary">
          {row.role_slug}
        </span>
      ),
    },
    {
      key: "tenant_id",
      label: translateKey("platform_admin", "client_users.col_tenant", { defaultValue: "Local (Tenant)" }),
      render: (row: ClientUserRecordItem) => (
        <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-[10px] text-muted-foreground">
          {row.tenant_id}
        </code>
      ),
    },
    {
      key: "is_deleted",
      label: translateKey("platform_admin", "client_users.col_status", { defaultValue: "Estado" }),
      render: (row: ClientUserRecordItem) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            !row.is_deleted
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-amber-500/20 text-amber-400"
          }`}
        >
          {!row.is_deleted
            ? translateKey("platform_admin", "client_users.status_active", { defaultValue: "Activo" })
            : translateKey("platform_admin", "client_users.status_archived", { defaultValue: "Archivado (Cupo Liberado)" })}
        </span>
      ),
    },
    {
      key: "quota_action",
      label: translateKey("platform_admin", "client_users.col_quotas", { defaultValue: "Cupos" }),
      render: (row: ClientUserRecordItem) =>
        !row.is_deleted ? (
          <Can perform="platform_admin.client_users.manage">
            <button
              type="button"
              data-testid={`soft-delete-cu-btn-${row.user_id}`}
              onClick={() => void handleSoftDelete(row.user_id)}
              className="inline-flex items-center gap-1 rounded border border-destructive/40 bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold text-destructive hover:bg-destructive/20"
            >
              <Archive className="h-3 w-3" />
              <span>{translateKey("platform_admin", "client_users.archive_btn", { defaultValue: "Archivar" })}</span>
            </button>
          </Can>
        ) : (
          <span className="text-[10px] text-muted-foreground italic">
            {translateKey("platform_admin", "client_users.released_badge", { defaultValue: "Liberado" })}
          </span>
        ),
    },
  ];

  const formFields: FormFieldDef[] = [
    {
      name: "username",
      label: translateKey("platform_admin", "client_users.field_username", { defaultValue: "Nombre de Usuario" }),
      type: "text",
      required: true,
      placeholder: "usuario.local",
    },
    {
      name: "first_name",
      label: translateKey("platform_admin", "client_users.field_first_name", { defaultValue: "Nombre" }),
      type: "text",
      required: true,
      placeholder: "Carlos",
    },
    {
      name: "last_name",
      label: translateKey("platform_admin", "client_users.field_last_name", { defaultValue: "Apellido" }),
      type: "text",
      required: true,
      placeholder: "Muñoz",
    },
    {
      name: "email",
      label: translateKey("platform_admin", "client_users.field_email", { defaultValue: "Correo Electrónico" }),
      type: "text",
      required: true,
      placeholder: "usuario@restaurante.cl",
    },
    {
      name: "phone",
      label: translateKey("platform_admin", "client_users.field_phone", { defaultValue: "Teléfono" }),
      type: "text",
      placeholder: "+56 9 1234 5678",
    },
    {
      name: "password",
      label: translateKey("platform_admin", "client_users.field_password", { defaultValue: "Contraseña de Acceso" }),
      type: "password",
      placeholder: "••••••••",
    },
    {
      name: "holding_id",
      label: translateKey("platform_admin", "client_users.field_holding", { defaultValue: "Holding Asociado" }),
      type: "select",
      required: true,
      options: [
        { label: "Holding Principal Génesis", value: "holding_genesis" },
        { label: "Grupo Gastronómico Pacífico SpA", value: "holding_pacifico" },
      ],
    },
    {
      name: "tenant_id",
      label: translateKey("platform_admin", "client_users.field_tenant", { defaultValue: "Sucursal / Local Asignado" }),
      type: "select",
      required: true,
      options: [
        { label: "Local Central Génesis", value: "tenant_genesis" },
        { label: "Sucursal Pacífico Centro", value: "tenant_pacifico_centro" },
      ],
    },
    {
      name: "role_slug",
      label: translateKey("platform_admin", "client_users.field_role", { defaultValue: "Rol y Nivel Operativo" }),
      type: "select",
      required: true,
      options: [
        { label: "Administrador de Sucursal (admin)", value: "admin" },
        { label: "Supervisor de Turno / Jefe Cocina (supervisor)", value: "supervisor" },
        { label: "Cajero / Operador de Turno (cajero)", value: "cajero" },
        { label: "Propietario de Local (propietario)", value: "propietario" },
      ],
    },
  ];

  return (
    <div data-testid="admin-client-users-view" className="p-6 md:p-8 space-y-6">
      <DynamicAdminTable<ClientUserRecordItem>
        title={translateKey("platform_admin", "client_users.title", { defaultValue: "Usuarios Clientes" })}
        description={translateKey("platform_admin", "client_users.description", {
          defaultValue: "Gestión de cuentas en locales gastronómicos con control de cupos y soft-delete.",
        })}
        data={users}
        columns={columns}
        loading={loading}
        onCreate={handleCreate}
        createButtonLabel={translateKey("platform_admin", "client_users.create_btn", {
          defaultValue: "Nuevo Usuario Cliente",
        })}
        createPermission="platform_admin.client_users.manage"
        onEdit={handleEdit}
        editPermission="platform_admin.client_users.manage"
        primaryKey="user_id"
        testId="client-users-table"
      />

      <DynamicAdminForm
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        title={
          editingUser
            ? translateKey("platform_admin", "client_users.edit_title", { defaultValue: "Editar Usuario Cliente" })
            : translateKey("platform_admin", "client_users.new_title", { defaultValue: "Nuevo Usuario Cliente" })
        }
        description={translateKey("platform_admin", "client_users.form_description", {
          defaultValue: "Asigna la cuenta al holding y local correspondiente.",
        })}
        fields={formFields}
        initialData={
          editingUser
            ? {
                username: editingUser.username,
                first_name: editingUser.first_name,
                last_name: editingUser.last_name,
                email: editingUser.email,
                phone: editingUser.phone ?? "",
                password: "",
                holding_id: editingUser.holding_id,
                tenant_id: editingUser.tenant_id,
                role_slug: editingUser.role_slug,
              }
            : null
        }
        onSubmit={handleModalSubmit}
        testId="admin-create-client-user-form"
      />
    </div>
  );
}

/* =========================================================================
 * 5. VISTA: USUARIOS GLOBALES (STAFF / SUPERADMIN) — DynamicAdminTable + Form
 * ========================================================================= */
export function AdminGlobalUsersView() {
  const [users, setUsers] = useState<readonly GlobalUserRecordItem[]>([
    {
      id: 1,
      username: "oppytec.admin",
      first_name: "SuperUser",
      last_name: "OppyTec",
      email: "oppytec.admin@gmail.com",
      phone: "+56 9 9999 8888",
      role: "propietario",
      is_superuser: true,
      is_active: true,
    },
    {
      id: 2,
      username: "soporte.staff",
      first_name: "Agente",
      last_name: "Soporte",
      email: "soporte@oppytec.com",
      phone: "+56 9 8888 7777",
      role: "admin",
      is_superuser: false,
      is_active: true,
    },
  ]);
  const [loading] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<GlobalUserRecordItem | null>(null);

  const handleCreate = () => {
    setEditingUser(null);
    setIsModalOpen(true);
  };

  const handleEdit = (user: GlobalUserRecordItem) => {
    setEditingUser(user);
    setIsModalOpen(true);
  };

  const handleDelete = (user: GlobalUserRecordItem) => {
    if (
      confirm(
        translateKey("platform_admin", "global_users.confirm_delete", {
          username: user.username,
        })
      )
    ) {
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    }
  };

  const handleModalSubmit = (formData: Record<string, unknown>) => {
    const payload = {
      username: String(formData.username ?? "").trim(),
      first_name: String(formData.first_name ?? "").trim(),
      last_name: String(formData.last_name ?? "").trim(),
      email: String(formData.email ?? "").trim(),
      phone: String(formData.phone ?? "").trim() || undefined,
      role: String(formData.role ?? "admin"),
      is_superuser: Boolean(formData.is_superuser),
      is_active: formData.is_active !== false,
    };

    if (editingUser) {
      setUsers((prev) =>
        prev.map((u) => (u.id === editingUser.id ? { ...editingUser, ...payload } : u))
      );
    } else {
      const newItem: GlobalUserRecordItem = {
        id: Date.now(),
        ...payload,
      };
      setUsers((prev) => [...prev, newItem]);
    }
    return true;
  };

  const columns = [
    {
      key: "username",
      label: translateKey("platform_admin", "global_users.col_username"),
      render: (row: GlobalUserRecordItem) => (
        <span className="font-semibold text-foreground">{row.username}</span>
      ),
    },
    {
      key: "full_name",
      label: translateKey("platform_admin", "global_users.col_full_name"),
      render: (row: GlobalUserRecordItem) => (
        <span>{`${row.first_name} ${row.last_name}`}</span>
      ),
    },
    {
      key: "email",
      label: translateKey("platform_admin", "global_users.col_email"),
      render: (row: GlobalUserRecordItem) => (
        <span className="font-mono text-xs text-muted-foreground">{row.email}</span>
      ),
    },
    {
      key: "role",
      label: translateKey("platform_admin", "global_users.col_role"),
      render: (row: GlobalUserRecordItem) => (
        <span className="rounded bg-secondary px-2 py-0.5 font-mono text-[10px] font-semibold text-foreground">
          {row.role}
        </span>
      ),
    },
    {
      key: "is_superuser",
      label: translateKey("platform_admin", "global_users.col_superuser"),
      render: (row: GlobalUserRecordItem) => (
        <span
          className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
            row.is_superuser
              ? "bg-purple-500/20 text-purple-400"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {row.is_superuser
            ? translateKey("platform_admin", "global_users.yes")
            : translateKey("platform_admin", "global_users.no")}
        </span>
      ),
    },
    {
      key: "is_active",
      label: translateKey("platform_admin", "global_users.col_status"),
      render: (row: GlobalUserRecordItem) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            row.is_active
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-destructive/20 text-destructive"
          }`}
        >
          {row.is_active
            ? translateKey("platform_admin", "global_users.status_active")
            : translateKey("platform_admin", "global_users.status_inactive")}
        </span>
      ),
    },
  ];

  const formFields: FormFieldDef[] = [
    {
      name: "username",
      label: translateKey("platform_admin", "global_users.field_username"),
      type: "text",
      required: true,
      placeholder: "staff.oppytec",
    },
    {
      name: "first_name",
      label: translateKey("platform_admin", "global_users.field_first_name"),
      type: "text",
      required: true,
    },
    {
      name: "last_name",
      label: translateKey("platform_admin", "global_users.field_last_name"),
      type: "text",
      required: true,
    },
    {
      name: "email",
      label: translateKey("platform_admin", "global_users.field_email"),
      type: "text",
      required: true,
      placeholder: "staff@oppytec.com",
    },
    {
      name: "phone",
      label: translateKey("platform_admin", "global_users.field_phone"),
      type: "text",
    },
    {
      name: "password",
      label: translateKey("platform_admin", "global_users.field_password"),
      type: "password",
    },
    {
      name: "role",
      label: translateKey("platform_admin", "global_users.field_role"),
      type: "select",
      required: true,
      options: [
        {
          label: translateKey("platform_admin", "global_users.role_propietario"),
          value: "propietario",
        },
        {
          label: translateKey("platform_admin", "global_users.role_admin"),
          value: "admin",
        },
        {
          label: translateKey("platform_admin", "global_users.role_supervisor"),
          value: "supervisor",
        },
        {
          label: translateKey("platform_admin", "global_users.role_staff"),
          value: "user",
        },
      ],
    },
    {
      name: "is_superuser",
      label: translateKey("platform_admin", "global_users.field_is_superuser"),
      type: "boolean",
    },
    {
      name: "is_active",
      label: translateKey("platform_admin", "global_users.field_is_active"),
      type: "boolean",
    },
  ];

  return (
    <div data-testid="admin-global-users-view" className="p-6 md:p-8 space-y-6">
      <DynamicAdminTable<GlobalUserRecordItem>
        title={translateKey("platform_admin", "global_users.title")}
        description={translateKey("platform_admin", "global_users.description")}
        data={users}
        columns={columns}
        loading={loading}
        onCreate={handleCreate}
        createButtonLabel={translateKey("platform_admin", "global_users.create_btn")}
        onEdit={handleEdit}
        onDelete={handleDelete}
        primaryKey="id"
        testId="global-users-table"
      />

      <DynamicAdminForm
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        title={
          editingUser
            ? translateKey("platform_admin", "global_users.edit_title")
            : translateKey("platform_admin", "global_users.new_title")
        }
        description={translateKey("platform_admin", "global_users.form_description")}
        fields={formFields}
        initialData={
          editingUser
            ? {
                username: editingUser.username,
                first_name: editingUser.first_name,
                last_name: editingUser.last_name,
                email: editingUser.email,
                phone: editingUser.phone ?? "",
                role: editingUser.role,
                is_superuser: editingUser.is_superuser,
                is_active: editingUser.is_active,
              }
            : null
        }
        onSubmit={handleModalSubmit}
        testId="admin-create-global-user-form"
      />
    </div>
  );
}

/* =========================================================================
 * 6. VISTA: TIPOS DE NEGOCIO — DynamicAdminTable + DynamicAdminForm Modal
 * ========================================================================= */
export interface BusinessTypeItem {
  readonly id: string;
  readonly name: string;
  readonly vertical: string;
  readonly enabled_modules: readonly string[];
  readonly is_active: boolean;
}

const DEFAULT_BUSINESS_TYPES: readonly BusinessTypeItem[] = [
  {
    id: "bt_restaurante",
    name: "Restaurante a la Carta",
    vertical: "Gastronomía",
    enabled_modules: ["catalog.products", "inventory.stock", "recipes", "operations.pos"],
    is_active: true,
  },
  {
    id: "bt_cafeteria",
    name: "Cafetería & Pastelería",
    vertical: "Gastronomía",
    enabled_modules: ["catalog.products", "inventory.stock", "recipes"],
    is_active: true,
  },
  {
    id: "bt_bar",
    name: "Bar & Coctelería",
    vertical: "Entretenimiento",
    enabled_modules: ["catalog.products", "inventory.stock", "recipes", "operations.pos"],
    is_active: true,
  },
  {
    id: "bt_dark_kitchen",
    name: "Dark Kitchen / Delivery",
    vertical: "Delivery",
    enabled_modules: ["catalog.products", "inventory.stock", "recipes", "procurement"],
    is_active: true,
  },
  {
    id: "bt_fast_food",
    name: "Comida Rápida (QSR)",
    vertical: "Gastronomía",
    enabled_modules: ["catalog.products", "inventory.stock", "recipes.combos", "operations.pos"],
    is_active: true,
  },
];

export function AdminBusinessTypesView() {
  const [types, setTypes] = useState<readonly BusinessTypeItem[]>(DEFAULT_BUSINESS_TYPES);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingType, setEditingType] = useState<BusinessTypeItem | null>(null);

  const handleCreate = () => {
    setEditingType(null);
    setIsModalOpen(true);
  };

  const handleEdit = (type: BusinessTypeItem) => {
    setEditingType(type);
    setIsModalOpen(true);
  };

  const handleDelete = (type: BusinessTypeItem) => {
    if (
      confirm(
        translateKey("platform_admin", "business_types.confirm_delete", {
          name: type.name,
        })
      )
    ) {
      setTypes((prev) => prev.filter((t) => t.id !== type.id));
    }
  };

  const handleModalSubmit = (formData: Record<string, unknown>) => {
    const payload = {
      name: String(formData.name ?? "").trim(),
      vertical: String(formData.vertical ?? "Gastronomía"),
      enabled_modules: ["catalog.products", "inventory.stock"],
      is_active: formData.is_active !== false,
    };

    if (editingType) {
      setTypes((prev) =>
        prev.map((t) => (t.id === editingType.id ? { ...editingType, ...payload } : t))
      );
    } else {
      const newItem: BusinessTypeItem = {
        id: `bt_${Date.now()}`,
        ...payload,
      };
      setTypes((prev) => [...prev, newItem]);
    }
    return true;
  };

  const columns = [
    {
      key: "vertical",
      label: translateKey("platform_admin", "business_types.col_vertical"),
      render: (row: BusinessTypeItem) => (
        <span className="rounded bg-primary/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-primary">
          {row.vertical}
        </span>
      ),
    },
    {
      key: "name",
      label: translateKey("platform_admin", "business_types.col_name"),
      render: (row: BusinessTypeItem) => (
        <span className="font-semibold text-foreground">{row.name}</span>
      ),
    },
    {
      key: "enabled_modules",
      label: translateKey("platform_admin", "business_types.col_modules"),
      render: (row: BusinessTypeItem) => (
        <span className="font-mono text-[11px] text-muted-foreground">
          {row.enabled_modules.join(", ")}
        </span>
      ),
    },
    {
      key: "is_active",
      label: translateKey("platform_admin", "business_types.col_status"),
      render: (row: BusinessTypeItem) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            row.is_active
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-destructive/20 text-destructive"
          }`}
        >
          {row.is_active
            ? translateKey("platform_admin", "business_types.status_active")
            : translateKey("platform_admin", "business_types.status_inactive")}
        </span>
      ),
    },
  ];

  const formFields: FormFieldDef[] = [
    {
      name: "name",
      label: translateKey("platform_admin", "business_types.field_name"),
      type: "text",
      required: true,
      placeholder: translateKey(
        "platform_admin",
        "business_types.field_name_placeholder"
      ),
    },
    {
      name: "vertical",
      label: translateKey("platform_admin", "business_types.field_vertical"),
      type: "select",
      required: true,
      options: [
        {
          label: translateKey(
            "platform_admin",
            "business_types.vertical_gastronomy"
          ),
          value: "Gastronomía",
        },
        {
          label: translateKey(
            "platform_admin",
            "business_types.vertical_entertainment"
          ),
          value: "Entretenimiento",
        },
        {
          label: translateKey(
            "platform_admin",
            "business_types.vertical_delivery"
          ),
          value: "Delivery",
        },
        {
          label: translateKey(
            "platform_admin",
            "business_types.vertical_hospitality"
          ),
          value: "Hotelería",
        },
      ],
    },
    {
      name: "is_active",
      label: translateKey("platform_admin", "business_types.field_is_active"),
      type: "boolean",
    },
  ];

  return (
    <div data-testid="admin-business-types-view" className="p-6 md:p-8 space-y-6">
      <DynamicAdminTable<BusinessTypeItem>
        title={translateKey("platform_admin", "business_types.title")}
        description={translateKey("platform_admin", "business_types.description")}
        data={types}
        columns={columns}
        onCreate={handleCreate}
        createButtonLabel={translateKey(
          "platform_admin",
          "business_types.create_btn"
        )}
        onEdit={handleEdit}
        onDelete={handleDelete}
        primaryKey="id"
        testId="business-types-table"
      />

      <DynamicAdminForm
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        title={
          editingType
            ? translateKey("platform_admin", "business_types.edit_title")
            : translateKey("platform_admin", "business_types.new_title")
        }
        description={translateKey(
          "platform_admin",
          "business_types.form_description"
        )}
        fields={formFields}
        initialData={
          editingType
            ? {
                name: editingType.name,
                vertical: editingType.vertical,
                is_active: editingType.is_active,
              }
            : null
        }
        onSubmit={handleModalSubmit}
        testId="admin-create-business-type-form"
      />
    </div>
  );
}

/* =========================================================================
 * 7. VISTA: MÓDULOS (SAAS) — DynamicAdminTable + Jerarquía Oficial
 * ========================================================================= */
interface ModuleRow {
  readonly slug: string;
  readonly label: string;
  readonly hierarchy: "Principal" | "Submódulo";
  readonly is_core: boolean;
}

export function AdminModulesView() {
  const moduleRows: ModuleRow[] = useMemo(() => {
    const list: ModuleRow[] = [];
    SAAS_MODULE_TREE.forEach((m) => {
      list.push({
        slug: m.slug,
        label: m.label,
        hierarchy: "Principal",
        is_core: m.isBasicPlanCore,
      });
      m.children.forEach((c) => {
        list.push({
          slug: c.slug,
          label: `└─ ${c.label}`,
          hierarchy: "Submódulo",
          is_core: c.isBasicPlanCore,
        });
      });
    });
    return list;
  }, []);

  const columns = [
    {
      key: "slug",
      label: translateKey("platform_admin", "modules_view.col_slug"),
      render: (row: ModuleRow) => (
        <code className="bg-primary/10 text-primary px-2 py-0.5 rounded font-mono text-[10px] font-bold">
          {row.slug}
        </code>
      ),
    },
    {
      key: "label",
      label: translateKey("platform_admin", "modules_view.col_name"),
      render: (row: ModuleRow) => (
        <span
          className={`text-xs ${
            row.hierarchy === "Principal"
              ? "font-bold text-foreground"
              : "text-muted-foreground pl-2"
          }`}
        >
          {row.label}
        </span>
      ),
    },
    {
      key: "hierarchy",
      label: translateKey("platform_admin", "modules_view.col_hierarchy"),
      render: (row: ModuleRow) => (
        <span
          className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
            row.hierarchy === "Principal"
              ? "bg-secondary text-foreground"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {row.hierarchy === "Principal"
            ? translateKey("platform_admin", "modules_view.level_root")
            : translateKey("platform_admin", "modules_view.level_sub")}
        </span>
      ),
    },
    {
      key: "is_core",
      label: translateKey("platform_admin", "modules_view.col_basic_plan"),
      render: (row: ModuleRow) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
            row.is_core
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-secondary text-muted-foreground"
          }`}
        >
          {row.is_core
            ? translateKey("platform_admin", "modules_view.status_included")
            : translateKey("platform_admin", "modules_view.status_optional")}
        </span>
      ),
    },
  ];

  return (
    <div data-testid="admin-modules-view" className="p-6 md:p-8 space-y-6">
      <DynamicAdminTable<ModuleRow>
        title={translateKey("platform_admin", "modules_view.title")}
        description={translateKey("platform_admin", "modules_view.description")}
        data={moduleRows}
        columns={columns}
        primaryKey="slug"
        testId="modules-table"
      />
    </div>
  );
}

/* =========================================================================
 * 8. VISTA: PLANES (SAAS) — Catálogo de Planes y Editor de Cuotas
 * ========================================================================= */
export function AdminPlansView() {
  const [plans, setPlans] = useState<readonly PlanCatalogItem[]>(
    INITIAL_PLANS_FALLBACK
  );
  const [slug, setSlug] = useState<string>("basic");
  const [name, setName] = useState<string>(
    "Plan Básico (Control de Inventario)"
  );
  const [maxUsers, setMaxUsers] = useState<number>(5);
  const [maxProducts, setMaxProducts] = useState<number>(500);
  const [maxSuppliers, setMaxSuppliers] = useState<number>(20);
  const [maxRecipes, setMaxRecipes] = useState<number>(0);
  const [maxCombos, setMaxCombos] = useState<number>(0);
  const [maxStorageMb, setMaxStorageMb] = useState<number>(512);
  const [priceClp, setPriceClp] = useState<string>("34990.00");
  const [priceUsd, setPriceUsd] = useState<string>("39.00");
  const [selectedModules, setSelectedModules] = useState<readonly string[]>(
    PLAN_BASICO_10_MODULE_SLUGS
  );
  const [savedBanner, setSavedBanner] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    apiRequest<PlanCatalogItem[]>("/tenancy/plans", {
      fallbackData: [...INITIAL_PLANS_FALLBACK],
    })
      .then((res) => {
        if (mounted && Array.isArray(res.data) && res.data.length > 0) {
          setPlans(res.data);
        }
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  const handleLoadPlanPreset = (plan: PlanCatalogItem) => {
    setSlug(plan.slug);
    setName(plan.name);
    setMaxUsers(plan.max_active_users);
    setMaxProducts(plan.max_products);
    setMaxSuppliers(plan.max_suppliers);
    setMaxRecipes(plan.max_recipes);
    setMaxCombos(plan.max_combos);
    setMaxStorageMb(plan.max_storage_mb);
    setPriceClp(String(plan.price_clp));
    setPriceUsd(String(plan.price_usd));
    setSelectedModules(plan.included_modules);
  };

  const handleSavePlan = async (e: FormEvent) => {
    e.preventDefault();
    const newPlan: PlanCatalogItem = {
      slug: slug.trim().toLowerCase(),
      name: name.trim(),
      max_active_users: maxUsers,
      max_products: maxProducts,
      max_suppliers: maxSuppliers,
      max_recipes: maxRecipes,
      max_combos: maxCombos,
      max_storage_mb: maxStorageMb,
      included_modules: selectedModules,
      price_clp: priceClp,
      price_usd: priceUsd,
      price_eur: "35.00",
      price_brl: "195.00",
    };

    const res = await apiRequest<PlanCatalogItem>("/tenancy/plans", {
      method: "POST",
      body: newPlan,
      fallbackData: newPlan,
    });
    const saved = res.data;
    setPlans((prev) => {
      const idx = prev.findIndex((p) => p.slug === saved.slug);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = saved;
        return copy;
      }
      return [...prev, saved];
    });
    setSavedBanner(
      translateKey("platform_admin", "plans.saved_success", {
        name: saved.name,
        slug: saved.slug,
      })
    );
  };

  return (
    <div
      data-testid="admin-plans-view"
      className="p-6 md:p-8 space-y-6 animate-in fade-in duration-300"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Layers className="h-6 w-6 text-primary" />
            <span>{translateKey("platform_admin", "plans.title")}</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            {translateKey("platform_admin", "plans.description")}
          </p>
        </div>
        <button
          type="button"
          data-testid="btn-preset-plan-basico"
          onClick={() => {
            const basic =
              plans.find((p) => p.slug === "basic") ?? INITIAL_PLANS_FALLBACK[0];
            if (basic) handleLoadPlanPreset(basic);
          }}
          className="touch-target inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-primary/15 px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/25"
        >
          <Sparkles className="h-4 w-4" />
          <span>{translateKey("platform_admin", "plans.preset_basic_btn")}</span>
        </button>
      </div>

      {savedBanner && (
        <div
          data-testid="admin-plan-saved-banner"
          className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2.5 text-xs font-semibold text-emerald-400"
        >
          {savedBanner}
        </div>
      )}

      {/* Tarjetas de Planes Existentes */}
      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((p) => (
          <div
            key={p.slug}
            data-testid={`plan-card-${p.slug}`}
            className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-sm hover:border-primary/50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="font-mono text-[10px] uppercase font-bold text-primary">
                  {p.slug}
                </span>
                <h3 className="text-sm font-bold text-foreground">{p.name}</h3>
              </div>
              <MoneyBadge amount={String(p.price_clp)} baseCurrency="CLP" />
            </div>

            <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px] text-muted-foreground">
              <span>
                {translateKey("platform_admin", "plans.quotas.users", {
                  count: p.max_active_users,
                })}
              </span>
              <span>
                {translateKey("platform_admin", "plans.quotas.products", {
                  count: p.max_products,
                })}
              </span>
              <span>
                {translateKey("platform_admin", "plans.quotas.suppliers", {
                  count: p.max_suppliers,
                })}
              </span>
              <span>
                {translateKey("platform_admin", "plans.quotas.recipes", {
                  count: p.max_recipes,
                })}
              </span>
              <span>
                {translateKey("platform_admin", "plans.quotas.combos", {
                  count: p.max_combos,
                })}
              </span>
              <span>
                {translateKey("platform_admin", "plans.quotas.storage_mb", {
                  count: p.max_storage_mb,
                })}
              </span>
            </div>

            <button
              type="button"
              data-testid={`edit-plan-btn-${p.slug}`}
              onClick={() => handleLoadPlanPreset(p)}
              className="touch-target w-full rounded-lg border border-border bg-secondary/60 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary"
            >
              {translateKey("platform_admin", "plans.edit_plan_btn")}
            </button>
          </div>
        ))}
      </div>

      {/* Formulario Paramétrico de las 6 Cuotas */}
      <form
        onSubmit={(e) => void handleSavePlan(e)}
        data-testid="admin-plan-editor-form"
        className="rounded-xl border border-border bg-card p-5 space-y-4"
      >
        <h3 className="text-sm font-bold uppercase text-muted-foreground">
          {translateKey("platform_admin", "plans.editor_title")}
        </h3>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.slug")}
            </span>
            <input
              data-testid="plan-input-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.name")}
            </span>
            <input
              data-testid="plan-input-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.price_clp")}
            </span>
            <input
              data-testid="plan-input-price-clp"
              value={priceClp}
              onChange={(e) => setPriceClp(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.price_usd")}
            </span>
            <input
              data-testid="plan-input-price-usd"
              value={priceUsd}
              onChange={(e) => setPriceUsd(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.max_users")}
            </span>
            <input
              type="number"
              min={1}
              data-testid="plan-quota-users"
              value={maxUsers}
              onChange={(e) => setMaxUsers(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.max_products")}
            </span>
            <input
              type="number"
              min={0}
              data-testid="plan-quota-products"
              value={maxProducts}
              onChange={(e) => setMaxProducts(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.max_suppliers")}
            </span>
            <input
              type="number"
              min={0}
              data-testid="plan-quota-suppliers"
              value={maxSuppliers}
              onChange={(e) => setMaxSuppliers(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.max_recipes")}
            </span>
            <input
              type="number"
              min={0}
              data-testid="plan-quota-recipes"
              value={maxRecipes}
              onChange={(e) => setMaxRecipes(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.max_combos")}
            </span>
            <input
              type="number"
              min={0}
              data-testid="plan-quota-combos"
              value={maxCombos}
              onChange={(e) => setMaxCombos(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>

          <label className="space-y-1 text-xs">
            <span className="font-semibold text-foreground">
              {translateKey("platform_admin", "plans.fields.max_storage_mb")}
            </span>
            <input
              type="number"
              min={64}
              data-testid="plan-quota-storage-mb"
              value={maxStorageMb}
              onChange={(e) => setMaxStorageMb(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
            />
          </label>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            data-testid="save-plan-submit-btn"
            className="touch-target inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground"
          >
            <Check className="h-4 w-4" />
            <span>{translateKey("platform_admin", "plans.save_btn")}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

// Canonical Aliases for Admin Management Views
export const PlansManagementView = AdminPlansView;
export const HoldingsManagementView = AdminHoldingsView;
export const TenantsManagementView = AdminTenantsView;

