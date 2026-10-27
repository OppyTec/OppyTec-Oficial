/**
 * oppytec-frontend/src/features/oppyfy/components/governance/OppyfyDomainTreeEditor.tsx
 * Editor jerárquico del Árbol de Dominios y Subdominios de OppyFy.
 * - Muestra badges de módulos SaaS contratados
 * - Interruptores para activar/desactivar subdominios y capacidades de consulta
 * - Modal para registrar dominios y subdominios personalizados
 * - Mobile-first con touch targets >= 44px
 */

import { useState } from "react";
import {
  ChefHat,
  Boxes,
  Truck,
  BadgePercent,
  Sparkles,
  Layers,
  Wrench,
  Eye,
  Plus,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { OppyfyDomainTreeResponse, OppyfyDomainCreateRequest } from "../../types";
import { CreateDomainModal } from "./CreateDomainModal";

export interface OppyfyDomainTreeEditorProps {
  readonly domains: readonly OppyfyDomainTreeResponse[];
  readonly onCreateDomain: (payload: OppyfyDomainCreateRequest) => Promise<unknown>;
  readonly onToggleSubdomainActive: (domainId: number, subdomainId: number) => void;
  readonly onToggleSubdomainCanViewCosts: (domainId: number, subdomainId: number) => void;
  readonly isCreatingDomain?: boolean;
}

export function OppyfyDomainTreeEditor({
  domains,
  onCreateDomain,
  onToggleSubdomainActive,
  onToggleSubdomainCanViewCosts,
  isCreatingDomain = false,
}: OppyfyDomainTreeEditorProps) {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  const getDomainIcon = (iconName: string) => {
    switch (iconName?.toLowerCase()) {
      case "chefhat":
        return <ChefHat className="h-5 w-5" />;
      case "boxes":
        return <Boxes className="h-5 w-5" />;
      case "truck":
        return <Truck className="h-5 w-5" />;
      case "badgepercent":
        return <BadgePercent className="h-5 w-5" />;
      default:
        return <Sparkles className="h-5 w-5" />;
    }
  };

  return (
    <div
      data-testid="oppyfy-domain-tree-editor"
      className="flex flex-col space-y-4"
    >
      {/* Barra superior de acciones */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-bold text-card-foreground">
            {translateKey("oppyfy", "governance.tabs.domains")}
          </h3>
          <p className="text-xs text-muted-foreground">
            Configura qué áreas de negocio e inventario pueden ser consultadas por OppyFy.
          </p>
        </div>
        <button
          type="button"
          data-testid="btn-open-create-domain"
          onClick={() => setIsCreateModalOpen(true)}
          className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          <span>{translateKey("oppyfy", "governance.domains.new_domain")}</span>
        </button>
      </div>

      {/* Árbol Jerárquico de Dominios */}
      <div className="space-y-4">
        {domains.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
            {translateKey("oppyfy", "governance.domains.empty")}
          </div>
        ) : (
          domains.map((domain) => (
            <div
              key={domain.id}
              data-testid={`domain-card-${domain.domain_key}`}
              className="rounded-xl border border-border bg-card shadow-sm transition-all overflow-hidden"
            >
              {/* Encabezado del Dominio */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-secondary/15 px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/20 text-primary">
                    {getDomainIcon(domain.icon)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-card-foreground">
                        {domain.name_es}
                      </h4>
                      <span className="rounded-md bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                        {domain.domain_key}
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {domain.name_en}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    data-testid={`domain-contracted-badge-${domain.domain_key}`}
                    className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary"
                  >
                    {translateKey("oppyfy", "governance.domains.contracted_badge", {
                      module: domain.domain_key,
                    })}
                  </span>
                  <span className="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground">
                    {translateKey("oppyfy", "governance.domains.subdomains_count", {
                      count: domain.subdomains.length,
                    })}
                  </span>
                </div>
              </div>

              {/* Lista de Subdominios */}
              <div className="divide-y divide-border">
                {domain.subdomains.map((subdomain) => (
                  <div
                    key={subdomain.id}
                    data-testid={`subdomain-row-${subdomain.subdomain_key}`}
                    className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between hover:bg-secondary/10 transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Layers className="h-4 w-4 text-muted-foreground" />
                        <span className="text-xs font-bold text-card-foreground">
                          {subdomain.name_es}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          ({subdomain.subdomain_key})
                        </span>
                      </div>

                      {/* Badges de Herramientas Operativas */}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Wrench className="h-3 w-3" />
                          Herramientas:
                        </span>
                        {subdomain.allowed_tool_functions.map((tool) => (
                          <span
                            key={tool}
                            className="rounded bg-muted/80 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                          >
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Controles e Interruptores del Subdominio */}
                    <div className="flex flex-wrap items-center gap-4 pt-2 sm:pt-0">
                      {/* Switch: Ver Costos Financieros */}
                      <button
                        type="button"
                        data-testid={`subdomain-toggle-costs-${subdomain.subdomain_key}`}
                        onClick={() =>
                          onToggleSubdomainCanViewCosts(domain.id, subdomain.id)
                        }
                        className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                          subdomain.can_view_costs_default
                            ? "border-amber-500/50 bg-amber-500/15 text-amber-600 dark:text-amber-400"
                            : "border-border bg-card text-muted-foreground hover:bg-muted"
                        }`}
                        title="Permitir ver costos financieros sin enmascarar"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>
                          {subdomain.can_view_costs_default
                            ? "Costos: Visibles"
                            : "Costos: Enmascarados"}
                        </span>
                      </button>

                      {/* Switch: Activar/Desactivar Subdominio */}
                      <button
                        type="button"
                        data-testid={`subdomain-toggle-active-${subdomain.subdomain_key}`}
                        onClick={() =>
                          onToggleSubdomainActive(domain.id, subdomain.id)
                        }
                        className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                          subdomain.is_active
                            ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                            : "border-border bg-card text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        <span
                          className={`h-2 w-2 rounded-full ${
                            subdomain.is_active
                              ? "bg-emerald-500"
                              : "bg-muted-foreground"
                          }`}
                        />
                        <span>{subdomain.is_active ? "Activo" : "Desactivado"}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal para Crear Dominio */}
      <CreateDomainModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreateDomain={onCreateDomain}
        isCreating={isCreatingDomain}
      />
    </div>
  );
}
