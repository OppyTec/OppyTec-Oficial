/**
 * oppytec-frontend/src/features/oppyfy/components/governance/CreateDomainModal.tsx
 * Modal accesible para crear nuevos dominios y subdominios personalizados en OppyFy.
 * - Mobile-first con touch targets >= 44px
 * - Soporte de temas (light, dark, ocean-blue)
 * - Cero hardcoding vía i18n
 */

import { useState } from "react";
import { X, Plus, Sparkles } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { OppyfyDomainCreateRequest } from "../../types";

export interface CreateDomainModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onCreateDomain: (payload: OppyfyDomainCreateRequest) => Promise<unknown>;
  readonly isCreating?: boolean;
}

export function CreateDomainModal({
  isOpen,
  onClose,
  onCreateDomain,
  isCreating = false,
}: CreateDomainModalProps) {
  const [domainKey, setDomainKey] = useState("");
  const [nameEs, setNameEs] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [icon, setIcon] = useState("BrainCircuit");
  const [subdomainKey, setSubdomainKey] = useState("");
  const [subdomainName, setSubdomainName] = useState("");
  const [toolsStr, setToolsStr] = useState("query_recipe_costs");
  const [canViewCostsDefault, setCanViewCostsDefault] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedKey = domainKey.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");
    const trimmedNameEs = nameEs.trim();
    const trimmedSubKey = subdomainKey.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");
    const trimmedSubName = subdomainName.trim();

    if (!trimmedKey || !trimmedNameEs) {
      setValidationError("La clave del dominio y el nombre en español son obligatorios.");
      return;
    }

    if (!trimmedSubKey || !trimmedSubName) {
      setValidationError("Debe ingresar la clave y el nombre del subdominio inicial.");
      return;
    }

    const toolFunctions = toolsStr
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const payload: OppyfyDomainCreateRequest = {
      domain_key: trimmedKey,
      name_es: trimmedNameEs,
      name_en: nameEn.trim() || trimmedNameEs,
      icon: icon.trim() || "BrainCircuit",
      is_active: true,
      subdomains: [
        {
          subdomain_key: trimmedSubKey,
          name_es: trimmedSubName,
          name_en: trimmedSubName,
          allowed_tool_functions: toolFunctions,
          can_view_costs_default: canViewCostsDefault,
          is_active: true,
        },
      ],
    };

    try {
      await onCreateDomain(payload);
      onClose();
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : "Error al crear el dominio.");
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-domain-modal-title"
      data-testid="modal-create-domain"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in"
    >
      <div className="glass-card relative flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-2xl">
        {/* Cabecera del Modal */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="create-domain-modal-title"
                className="text-base font-bold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.create_domain_modal.title")}
              </h2>
            </div>
          </div>
          <button
            type="button"
            data-testid="btn-close-create-domain"
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Cerrar modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Mensaje de validación */}
        {validationError && (
          <div
            role="alert"
            data-testid="create-domain-error"
            className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive"
          >
            {validationError}
          </div>
        )}

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="flex-1 space-y-4 overflow-y-auto py-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="domain-key-input"
                className="mb-1 block text-xs font-semibold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.create_domain_modal.domain_key")}
              </label>
              <input
                id="domain-key-input"
                type="text"
                data-testid="input-domain-key"
                value={domainKey}
                onChange={(e) => setDomainKey(e.target.value)}
                placeholder="ej. produccion_eventos"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                required
              />
            </div>
            <div>
              <label
                htmlFor="domain-icon-input"
                className="mb-1 block text-xs font-semibold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.create_domain_modal.icon")}
              </label>
              <input
                id="domain-icon-input"
                type="text"
                data-testid="input-domain-icon"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="Calendar, Award, Truck, ChefHat"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="name-es-input"
                className="mb-1 block text-xs font-semibold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.create_domain_modal.name_es")}
              </label>
              <input
                id="name-es-input"
                type="text"
                data-testid="input-domain-name-es"
                value={nameEs}
                onChange={(e) => setNameEs(e.target.value)}
                placeholder="ej. Producción y Banquetes"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                required
              />
            </div>
            <div>
              <label
                htmlFor="name-en-input"
                className="mb-1 block text-xs font-semibold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.create_domain_modal.name_en")}
              </label>
              <input
                id="name-en-input"
                type="text"
                data-testid="input-domain-name-en"
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                placeholder="ej. Production & Banquets"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="rounded-xl border border-border bg-secondary/15 p-3.5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wide text-primary">
              Subdominio Inicial
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="subdomain-key-input"
                  className="mb-1 block text-xs font-semibold text-card-foreground"
                >
                  {translateKey("oppyfy", "governance.create_domain_modal.subdomain_key")}
                </label>
                <input
                  id="subdomain-key-input"
                  type="text"
                  data-testid="input-subdomain-key"
                  value={subdomainKey}
                  onChange={(e) => setSubdomainKey(e.target.value)}
                  placeholder="ej. banquet_feasibility"
                  className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="subdomain-name-input"
                  className="mb-1 block text-xs font-semibold text-card-foreground"
                >
                  {translateKey("oppyfy", "governance.create_domain_modal.subdomain_name")}
                </label>
                <input
                  id="subdomain-name-input"
                  type="text"
                  data-testid="input-subdomain-name"
                  value={subdomainName}
                  onChange={(e) => setSubdomainName(e.target.value)}
                  placeholder="ej. Factibilidad de Banquetes"
                  className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="tools-str-input"
                className="mb-1 block text-xs font-semibold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.create_domain_modal.tools_label")}
              </label>
              <input
                id="tools-str-input"
                type="text"
                data-testid="input-domain-tools"
                value={toolsStr}
                onChange={(e) => setToolsStr(e.target.value)}
                placeholder="analyze_event_supply_feasibility, query_recipe_costs"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <label className="flex items-center gap-3 pt-1 cursor-pointer">
              <input
                type="checkbox"
                data-testid="check-can-view-costs-default"
                checked={canViewCostsDefault}
                onChange={(e) => setCanViewCostsDefault(e.target.checked)}
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
              />
              <span className="text-xs font-medium text-card-foreground">
                {translateKey("oppyfy", "governance.create_domain_modal.can_view_costs_default")}
              </span>
            </label>
          </div>

          {/* Botones de acción */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              data-testid="btn-cancel-create-domain"
              onClick={onClose}
              disabled={isCreating}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-card-foreground transition-colors hover:bg-muted"
            >
              {translateKey("oppyfy", "governance.create_domain_modal.cancel")}
            </button>
            <button
              type="submit"
              data-testid="btn-submit-create-domain"
              disabled={isCreating}
              className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90 disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              <span>
                {isCreating
                  ? "Creando..."
                  : translateKey("oppyfy", "governance.create_domain_modal.submit")}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
