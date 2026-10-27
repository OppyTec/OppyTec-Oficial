/**
 * oppytec-frontend/src/features/oppyfy/components/governance/GrantPermissionModal.tsx
 * Modal accesible para otorgar permisos temporales RBAC exclusivos de OppyFy.
 * Implementa estrictamente el Triple Control de Caducidad:
 * 1) Fecha/hora de vencimiento (expires_at)
 * 2) Límite de consultas (max_prompts)
 * 3) Tope de créditos temporales (temp_credit_ceiling)
 * Además de control granular para visualizar costos financieros (can_view_costs).
 */

import { useState } from "react";
import { X, ShieldAlert, KeyRound, Clock, Hash, Coins } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type {
  OppyfyGrantCreateRequest,
  OppyfyDomainTreeResponse,
  OppyfyWorkerWalletItem,
} from "../../types";

export interface GrantPermissionModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly domains: readonly OppyfyDomainTreeResponse[];
  readonly workers: readonly OppyfyWorkerWalletItem[];
  readonly onGrantPermission: (payload: OppyfyGrantCreateRequest) => Promise<unknown>;
  readonly isGranting?: boolean;
}

export function GrantPermissionModal({
  isOpen,
  onClose,
  domains,
  workers,
  onGrantPermission,
  isGranting = false,
}: GrantPermissionModalProps) {
  const [selectedUserId, setSelectedUserId] = useState<number>(workers[0]?.user_id ?? 1);
  const firstSub = domains[0]?.subdomains[0];
  const [selectedSubdomainKey, setSelectedSubdomainKey] = useState<string>(
    firstSub?.subdomain_key ?? "recipes_kitchen"
  );
  const [canViewCosts, setCanViewCosts] = useState<boolean>(false);

  // Triple control de caducidad
  const [expiresAt, setExpiresAt] = useState<string>("");
  const [maxPrompts, setMaxPrompts] = useState<string>("25");
  const [tempCreditCeiling, setTempCreditCeiling] = useState<string>("30.00");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  // Encontrar el subdomain_id a partir del key seleccionado
  let resolvedSubdomainId = 1;
  for (const d of domains) {
    const s = d.subdomains.find((sub) => sub.subdomain_key === selectedSubdomainKey);
    if (s) {
      resolvedSubdomainId = s.id;
      break;
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!selectedUserId) {
      setErrorMsg("Debe seleccionar un trabajador destinatario.");
      return;
    }

    if (!selectedSubdomainKey) {
      setErrorMsg("Debe seleccionar un subdominio de conocimiento.");
      return;
    }

    const parsedMaxPrompts = maxPrompts.trim() ? parseInt(maxPrompts.trim(), 10) : null;
    if (parsedMaxPrompts !== null && (isNaN(parsedMaxPrompts) || parsedMaxPrompts <= 0)) {
      setErrorMsg("El límite de consultas (max_prompts) debe ser un entero mayor a cero.");
      return;
    }

    const parsedCeiling = tempCreditCeiling.trim() ? parseFloat(tempCreditCeiling.trim()) : null;
    if (parsedCeiling !== null && (isNaN(parsedCeiling) || parsedCeiling < 0)) {
      setErrorMsg("El tope de créditos debe ser un número no negativo.");
      return;
    }

    let parsedIsoExpires: string | null = null;
    if (expiresAt.trim()) {
      const d = new Date(expiresAt);
      if (isNaN(d.getTime())) {
        setErrorMsg("La fecha y hora de vencimiento no es válida.");
        return;
      }
      parsedIsoExpires = d.toISOString();
    }

    // Regla: Se requiere al menos un control de caducidad
    if (!parsedIsoExpires && parsedMaxPrompts === null && parsedCeiling === null) {
      setErrorMsg("Debe configurar al menos uno de los 3 controles de caducidad temporal.");
      return;
    }

    const payload: OppyfyGrantCreateRequest = {
      user_id: selectedUserId,
      subdomain_id: resolvedSubdomainId,
      subdomain_slug: selectedSubdomainKey,
      can_query: true,
      can_view_costs: canViewCosts,
      expires_at: parsedIsoExpires,
      max_prompts: parsedMaxPrompts,
      temp_credit_ceiling: parsedCeiling !== null ? String(parsedCeiling) : null,
    };

    try {
      await onGrantPermission(payload);
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error al otorgar permiso.");
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="grant-permission-modal-title"
      data-testid="modal-grant-permission"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in"
    >
      <div className="glass-card relative flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-2xl">
        {/* Cabecera */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 text-amber-500">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="grant-permission-modal-title"
                className="text-base font-bold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.grant_modal.title")}
              </h2>
            </div>
          </div>
          <button
            type="button"
            data-testid="btn-close-grant-modal"
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Cerrar modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Error de validación */}
        {errorMsg && (
          <div
            role="alert"
            data-testid="grant-modal-error"
            className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive"
          >
            {errorMsg}
          </div>
        )}

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="flex-1 space-y-4 overflow-y-auto py-4">
          {/* Selector de Usuario */}
          <div>
            <label
              htmlFor="grant-user-select"
              className="mb-1 block text-xs font-semibold text-card-foreground"
            >
              {translateKey("oppyfy", "governance.grant_modal.user_select")}
            </label>
            <select
              id="grant-user-select"
              data-testid="select-grant-user"
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(Number(e.target.value))}
              className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {workers.map((w) => (
                <option key={w.user_id} value={w.user_id}>
                  {`${w.full_name} (${w.role_name}) - Pollo King`}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Subdominio */}
          <div>
            <label
              htmlFor="grant-subdomain-select"
              className="mb-1 block text-xs font-semibold text-card-foreground"
            >
              {translateKey("oppyfy", "governance.grant_modal.subdomain_select")}
            </label>
            <select
              id="grant-subdomain-select"
              data-testid="select-grant-subdomain"
              value={selectedSubdomainKey}
              onChange={(e) => setSelectedSubdomainKey(e.target.value)}
              className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {domains.map((d) => (
                <optgroup key={d.domain_key} label={d.name_es}>
                  {d.subdomains.map((s) => (
                    <option key={s.subdomain_key} value={s.subdomain_key}>
                      {`${s.name_es} (${s.subdomain_key})`}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Permiso de Costos Financieros */}
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                data-testid="check-grant-can-view-costs"
                checked={canViewCosts}
                onChange={(e) => setCanViewCosts(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary"
              />
              <div className="space-y-0.5">
                <span className="text-xs font-semibold text-card-foreground">
                  {translateKey("oppyfy", "governance.grant_modal.can_view_costs")}
                </span>
                <p className="text-[11px] text-muted-foreground">
                  Habilita la revelación de datos no enmascarados de costos reales, escandallos y márgenes en Pollo King.
                </p>
              </div>
            </label>
          </div>

          {/* Triple Control de Caducidad */}
          <div className="rounded-xl border border-border bg-secondary/15 p-4 space-y-3">
            <div className="flex items-center gap-2 text-primary">
              <ShieldAlert className="h-4 w-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">
                {translateKey("oppyfy", "governance.grant_modal.triple_control_title")}
              </h3>
            </div>
            <p className="text-[11px] text-muted-foreground">
              {translateKey("oppyfy", "governance.grant_modal.triple_control_desc")}
            </p>

            {/* 1. expires_at */}
            <div>
              <label
                htmlFor="grant-expires-at-input"
                className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-card-foreground"
              >
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                {translateKey("oppyfy", "governance.grant_modal.expires_at_label")}
              </label>
              <input
                id="grant-expires-at-input"
                type="datetime-local"
                data-testid="input-grant-expires-at"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* 2. max_prompts */}
            <div>
              <label
                htmlFor="grant-max-prompts-input"
                className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-card-foreground"
              >
                <Hash className="h-3.5 w-3.5 text-muted-foreground" />
                {translateKey("oppyfy", "governance.grant_modal.max_prompts_label")}
              </label>
              <input
                id="grant-max-prompts-input"
                type="number"
                min="1"
                data-testid="input-grant-max-prompts"
                value={maxPrompts}
                onChange={(e) => setMaxPrompts(e.target.value)}
                placeholder="ej. 20"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* 3. temp_credit_ceiling */}
            <div>
              <label
                htmlFor="grant-temp-credit-ceiling-input"
                className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-card-foreground"
              >
                <Coins className="h-3.5 w-3.5 text-muted-foreground" />
                {translateKey("oppyfy", "governance.grant_modal.temp_credit_ceiling_label")}
              </label>
              <input
                id="grant-temp-credit-ceiling-input"
                type="number"
                step="0.01"
                min="0"
                data-testid="input-grant-temp-ceiling"
                value={tempCreditCeiling}
                onChange={(e) => setTempCreditCeiling(e.target.value)}
                placeholder="ej. 30.00"
                className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          {/* Acciones */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              data-testid="btn-cancel-grant"
              onClick={onClose}
              disabled={isGranting}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-card-foreground transition-colors hover:bg-muted"
            >
              {translateKey("oppyfy", "governance.grant_modal.cancel")}
            </button>
            <button
              type="submit"
              data-testid="btn-submit-grant"
              disabled={isGranting}
              className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90 disabled:opacity-50"
            >
              <KeyRound className="h-4 w-4" />
              <span>
                {isGranting
                  ? "Concediendo..."
                  : translateKey("oppyfy", "governance.grant_modal.submit")}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
