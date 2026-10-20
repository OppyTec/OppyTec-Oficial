import { Briefcase, Building, Store, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { apiRequest } from "@/shared/api/httpClient";

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

export function AdminDashboard() {
  const [counts, setCounts] = useState<DashboardCounts>({
    holdings: 0,
    legalEntities: 0,
    tenants: 0,
    users: 1, // SuperUser Génesis inicial
  });

  useEffect(() => {
    let isMounted = true;
    apiRequest<SummaryApiResponse>("/tenancy/dashboard/summary")
      .then((res) => {
        if (isMounted && res.data) {
          setCounts({
            holdings: Number(res.data.holdings ?? 0),
            legalEntities: Number(res.data.legal_entities ?? 0),
            tenants: Number(res.data.tenants ?? 0),
            users: Number(res.data.users ?? 1),
          });
        }
      })
      .catch(() => {
        // En caso de modo offline o prueba unitaria, mantiene el estado base seguro
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div
      data-testid="admin-dashboard-view"
      className="p-6 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500"
    >
      <div className="space-y-2">
        <h2 className="text-3xl font-bold tracking-tight text-foreground">
          Panel de Control Global
        </h2>
        <p className="text-muted-foreground">
          Gestión de Holdings, Entidades Legales (RUTs) e Inquilinos de la plataforma OppyTec.
        </p>
      </div>

      <div
        data-testid="admin-kpi-grid"
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        {/* Grupos Empresariales */}
        <div
          data-testid="kpi-holdings"
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-primary/50 transition-colors"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground">
              Grupos Empresariales
            </span>
            <Building className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.holdings}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Total de holdings registrados
            </p>
          </div>
        </div>

        {/* Entidades Legales */}
        <div
          data-testid="kpi-legal-entities"
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-primary/50 transition-colors"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground">
              Entidades Legales
            </span>
            <Briefcase className="h-4 w-4 text-orange-500" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.legalEntities}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Empresas facturadoras (RUTs)
            </p>
          </div>
        </div>

        {/* Tenants */}
        <div
          data-testid="kpi-tenants"
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-primary/50 transition-colors"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground">Tenants</span>
            <Store className="h-4 w-4 text-emerald-500" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.tenants}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Instancias activas (Locales)
            </p>
          </div>
        </div>

        {/* Usuarios Globales */}
        <div
          data-testid="kpi-users"
          className="rounded-xl border border-border bg-card p-6 shadow-sm hover:border-primary/50 transition-colors"
        >
          <div className="flex flex-row items-center justify-between pb-2">
            <span className="text-sm font-medium text-foreground">
              Usuarios Globales
            </span>
            <Users className="h-4 w-4 text-pink-500" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground">
              {counts.users}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Cuentas creadas</p>
          </div>
        </div>
      </div>

      <div className="mt-8 border rounded-xl bg-card p-12 text-center text-muted-foreground border-dashed">
        Aquí irá el componente DynamicDataTable para visualizar los tenants más recientes.
      </div>
    </div>
  );
}
