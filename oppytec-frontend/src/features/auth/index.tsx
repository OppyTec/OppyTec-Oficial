import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { OFFICIAL_TENANT_OPTIONS } from "@/shared/components/layout/HoldingTenantSwitcher";
import { translateKey } from "@/shared/i18n";

export interface ImpersonationBannerProps {
  readonly impersonatedTenant: string;
  readonly reason: string;
  readonly expiresInMinutes: number;
  readonly onExitImpersonation: () => void;
}

export function ImpersonationBanner({
  impersonatedTenant,
  reason,
  expiresInMinutes,
  onExitImpersonation,
}: ImpersonationBannerProps) {
  return (
    <div
      role="status"
      data-testid="auth-impersonation-banner"
      className="animate-blink-orange mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-warning bg-warning/15 px-3 py-2 text-xs text-foreground"
    >
      <div>
        <span className="font-bold">Impersonación Auditada: </span>
        <span className="font-mono">{impersonatedTenant}</span>
        <span className="ml-2 text-muted-foreground">{`(${reason} · TTL ${String(expiresInMinutes)}m)`}</span>
      </div>
      <button
        type="button"
        data-testid="auth-exit-impersonation"
        onClick={onExitImpersonation}
        className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-secondary px-3 py-1 font-semibold text-secondary-foreground"
      >
        {translateKey("auth", "session.logout")}
      </button>
    </div>
  );
}

export function AuthFeatureView() {
  const [email, setEmail] = useState<string>("chef.ejecutivo@oppytec.cl");
  const [mfaCode, setMfaCode] = useState<string>("482910");
  const [selectedTenantId, setSelectedTenantId] = useState<string>(
    OFFICIAL_TENANT_OPTIONS[0]?.tenantId ?? "tenant_rest_central"
  );
  const [impersonating, setImpersonating] = useState<boolean>(true);

  return (
    <section
      data-testid="feature-auth"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("auth", "login.title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("auth", "login.mfa_prompt", { email })}
          </p>
        </div>
        <Can perform="auth.session.manage" showDeniedBadge>
          <span className="rounded-full bg-primary/15 px-2.5 py-1 font-mono text-xs font-semibold text-primary">
            JWT Dual RS256 + MFA Activo
          </span>
        </Can>
      </div>

      {impersonating && (
        <ImpersonationBanner
          impersonatedTenant={selectedTenantId}
          reason="Soporte Nivel 3 — Cuadratura de Kardex"
          expiresInMinutes={15}
          onExitImpersonation={() => setImpersonating(false)}
        />
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3">
          <label className="block text-xs font-semibold text-muted-foreground">
            {translateKey("auth", "login.email_label")}
          </label>
          <input
            type="email"
            aria-label={translateKey("auth", "login.email_label")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="touch-target min-h-[44px] w-full rounded-md border border-border bg-card px-3 text-xs text-foreground"
          />
          <label className="block text-xs font-semibold text-muted-foreground">
            MFA TOTP (6 dígitos)
          </label>
          <input
            type="text"
            inputMode="numeric"
            aria-label="MFA TOTP"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
            className="touch-target min-h-[44px] w-full rounded-md border border-border bg-card px-3 font-mono text-xs text-foreground"
          />
        </div>

        <div
          data-testid="auth-select-tenant"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            SelectTenant (Multi-Holding)
          </h3>
          {OFFICIAL_TENANT_OPTIONS.map((t) => (
            <button
              key={t.tenantId}
              type="button"
              onClick={() => setSelectedTenantId(t.tenantId)}
              className={`touch-target flex min-h-[44px] w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-xs ${
                selectedTenantId === t.tenantId
                  ? "border-primary bg-primary/15 font-bold text-primary"
                  : "border-border bg-card text-foreground"
              }`}
            >
              <span>{t.tenantName}</span>
              <span className="font-mono text-[11px]">{t.rut}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
