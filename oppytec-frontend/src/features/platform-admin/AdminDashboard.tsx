import {
  ArrowRight,
  Briefcase,
  Building,
  Building2,
  ExternalLink,
  Layers,
  Plus,
  Search,
  Store,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, setHttpRequestContext } from "@/shared/api/httpClient";
import { translateKey } from "@/shared/i18n";

export interface DashboardCounts {
  readonly holdings: number;
  readonly legalEntities: number;
  readonly tenants: number;
  readonly users: number;
}

interface SummaryApiResponse {
  readonly holdings?: number;
  readonly legal_entities?: number;
  readonly tenants?: number;
  readonly users?: number;
}

interface QuickTenantItem {
  readonly tenant_id: string;
  readonly schema_name: string;
  readonly display_name: string;
  readonly holding_id: string;
  readonly enabled_modules: readonly string[];
}

const FALLBACK_DASHBOARD_TENANTS: readonly QuickTenantItem[] = [
  {
    tenant_id: "t_genesis",
    schema_name: "tenant_genesis",
    display_name: "Local Central Génesis",
    holding_id: "holding_genesis",
    enabled_modules: ["inicio", "catalog.products", "inventory.stock", "identity.users"],
  },
  {
    tenant_id: "t_pacifico_centro",
    schema_name: "tenant_pacifico_centro",
    display_name: "Sucursal Pacífico Centro",
    holding_id: "holding_pacifico",
    enabled_modules: ["inicio", "catalog.products", "inventory.stock", "inventory.mermas"],
  },
];

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

export function AdminDashboard() {
  const navigate = useSafeNavigate();
  const [counts, setCounts] = useState<DashboardCounts>({
    holdings: 1,
    legalEntities: 1,
    tenants: 2,
    users: 1, // SuperUser Génesis inicial
  });
  const [tenants, setTenants] = useState<readonly QuickTenantItem[]>(FALLBACK_DASHBOARD_TENANTS);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [impersonatedNotice, setImpersonatedNotice] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    apiRequest<SummaryApiResponse>("/tenancy/dashboard/summary")
      .then((res) => {
        if (isMounted && res.data) {
          setCounts({
            holdings: Number(res.data.holdings ?? 1),
            legalEntities: Number(res.data.legal_entities ?? 1),
            tenants: Number(res.data.tenants ?? 2),
            users: Number(res.data.users ?? 1),
          });
        }
      })
      .catch(() => undefined);

    apiRequest<QuickTenantItem[]>("/tenancy/tenants", {
      fallbackData: [...FALLBACK_DASHBOARD_TENANTS],
    })
      .then((res) => {
        if (isMounted && Array.isArray(res.data) && res.data.length > 0) {
          setTenants(res.data);
        }
      })
      .catch(() => undefined);

    return () => {
      isMounted = false;
    };
  }, []);

  const handleImpersonate = async (tenant: QuickTenantItem) => {
    const res = await apiRequest<{
      readonly access_token: string;
      readonly tenant_id: string;
      readonly holding_id: string;
      readonly schema_name: string;
    }>("/tenancy/admin/impersonate", {
      method: "POST",
      body: {
        tenant_id: tenant.tenant_id,
        reason: translateKey("platform_admin", "dashboard.support_reason", {
          name: tenant.display_name,
        }),
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
    setImpersonatedNotice(
      translateKey("platform_admin", "dashboard.impersonate_active", {
        name: tenant.display_name,
        schema: res.data.schema_name,
      })
    );
  };

  const filteredTenants = tenants.filter(
    (t) =>
      t.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.schema_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.holding_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div
      data-testid="admin-dashboard-view"
      className="p-6 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500"
    >
      {/* Encabezado y Barra de Acciones Rápidas */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1">
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Panel de Control Global
          </h2>
          <p className="text-muted-foreground text-sm">
            Gestión completa de Holdings, Entidades Legales (RUTs), Locales (Tenants) y Planes Comerciales.
          </p>
        </div>

        {/* Botones de Creación Directa */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="quick-btn-new-holding"
            onClick={() => navigate("/admin/holdings")}
            className="touch-target inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Nuevo Holding</span>
          </button>
          <button
            type="button"
            data-testid="quick-btn-new-legal-entity"
            onClick={() => navigate("/admin/legal-entities")}
            className="touch-target inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary transition-colors"
          >
            <Building2 className="h-4 w-4 text-orange-500" />
            <span>Nueva Entidad Legal</span>
          </button>
          <button
            type="button"
            data-testid="quick-btn-new-tenant"
            onClick={() => navigate("/admin/tenants")}
            className="touch-target inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary transition-colors"
          >
            <Store className="h-4 w-4 text-emerald-500" />
            <span>Aprovisionar Tenant</span>
          </button>
          <button
            type="button"
            data-testid="quick-btn-plans"
            onClick={() => navigate("/admin/plans")}
            className="touch-target inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary transition-colors"
          >
            <Layers className="h-4 w-4 text-purple-500" />
            <span>Planes SaaS</span>
          </button>
        </div>
      </div>

      {impersonatedNotice && (
        <div
          data-testid="admin-dashboard-impersonate-banner"
          className="rounded-xl border border-primary/40 bg-primary/10 p-4 text-xs font-semibold text-primary flex items-center justify-between"
        >
          <span>{impersonatedNotice}</span>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-primary-foreground px-3 py-1 text-xs"
          >
            <span>Ir al Workspace Local</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* KPI Cards Interactivas */}
      <div
        data-testid="admin-kpi-grid"
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        {/* Grupos Empresariales */}
        <div
          data-testid="kpi-holdings"
          onClick={() => navigate("/admin/holdings")}
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-primary/50 hover:bg-secondary/20 transition-all cursor-pointer group"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
              Grupos Empresariales
            </span>
            <Building className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.holdings}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <span>Total de holdings registrados</span>
              <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
            </p>
          </div>
        </div>

        {/* Entidades Legales */}
        <div
          data-testid="kpi-legal-entities"
          onClick={() => navigate("/admin/legal-entities")}
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-orange-500/50 hover:bg-secondary/20 transition-all cursor-pointer group"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground group-hover:text-orange-500 transition-colors">
              Entidades Legales
            </span>
            <Briefcase className="h-4 w-4 text-orange-500" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.legalEntities}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <span>Empresas facturadoras (RUTs)</span>
              <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-orange-500" />
            </p>
          </div>
        </div>

        {/* Tenants */}
        <div
          data-testid="kpi-tenants"
          onClick={() => navigate("/admin/tenants")}
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-emerald-500/50 hover:bg-secondary/20 transition-all cursor-pointer group"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground group-hover:text-emerald-500 transition-colors">
              Tenants
            </span>
            <Store className="h-4 w-4 text-emerald-500" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.tenants}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <span>Instancias activas (Locales)</span>
              <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-500" />
            </p>
          </div>
        </div>

        {/* Usuarios Clientes y Globales */}
        <div
          data-testid="kpi-users"
          onClick={() => navigate("/admin/client-users")}
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-pink-500/50 hover:bg-secondary/20 transition-all cursor-pointer group"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground group-hover:text-pink-500 transition-colors">
              Usuarios Clientes
            </span>
            <Users className="h-4 w-4 text-pink-500" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.users}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <span>Cuentas activas en sucursales</span>
              <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-pink-500" />
            </p>
          </div>
        </div>
      </div>

      {/* Tabla Dinámica de Locales / Tenants en Vivo */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 border-b border-border bg-secondary/10">
          <div>
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Store className="h-5 w-5 text-emerald-500" />
              <span>Instancias de Locales (Tenants Registrados)</span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Esquemas aislados en PostgreSQL, módulos asignados y acceso directo en modo soporte.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Buscar por local o esquema..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-56 rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <button
              type="button"
              onClick={() => navigate("/admin/tenants")}
              className="touch-target inline-flex items-center gap-1 rounded-lg bg-primary/10 text-primary px-3 py-1.5 text-xs font-semibold hover:bg-primary/20 transition-colors"
            >
              <span>Gestionar Todos</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-secondary/20 text-muted-foreground font-semibold">
              <tr>
                <th className="px-5 py-3">Nombre del Local</th>
                <th className="px-5 py-3">Esquema DB</th>
                <th className="px-5 py-3">Holding</th>
                <th className="px-5 py-3">Módulos Activos</th>
                <th className="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredTenants.map((t) => (
                <tr key={t.tenant_id} className="hover:bg-secondary/15 transition-colors">
                  <td className="px-5 py-3 font-semibold text-foreground">
                    {t.display_name}
                  </td>
                  <td className="px-5 py-3 font-mono text-[11px] text-primary">
                    {t.schema_name}
                  </td>
                  <td className="px-5 py-3 font-mono text-[11px] text-muted-foreground">
                    {t.holding_id}
                  </td>
                  <td className="px-5 py-3">
                    <span className="rounded bg-secondary px-2 py-0.5 text-[10px] font-medium text-foreground">
                      {t.enabled_modules.length} módulos
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => navigate("/admin/tenants")}
                        className="rounded border border-border bg-card px-2.5 py-1 text-[11px] font-semibold text-foreground hover:bg-secondary transition-colors"
                      >
                        Configurar
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleImpersonate(t)}
                        className="inline-flex items-center gap-1 rounded bg-emerald-500/15 text-emerald-400 px-2.5 py-1 text-[11px] font-semibold hover:bg-emerald-500/25 transition-colors"
                      >
                        <ExternalLink className="h-3 w-3" />
                        <span>Entrar</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
