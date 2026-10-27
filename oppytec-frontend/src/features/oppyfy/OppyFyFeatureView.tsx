/**
 * oppytec-frontend/src/features/oppyfy/OppyFyFeatureView.tsx
 * Espacio de Trabajo Unificado OppyFy (v2.0):
 * - Chat Inteligente con citaciones RAG de 3 capas
 * - Medidor semafórico de contexto y bloqueo anti-alucinación
 * - Split-View Canvas con tablas, gráficos Recharts y Action Cards
 * - Rollover asistido a hilo fresco al 5.00%
 * - Panel Exclusivo de Gobernanza & RBAC (Árbol de dominios, permisos temporales, billeteras y auditoría)
 * - Protección declarativa RBAC con <Can perform="oppyfy.governance.manage">
 * - Sincronización bidireccional con parámetro de URL ?tab=workspace vs ?tab=governance
 * - Soporte a 3 temas visuales (light, dark, ocean-blue)
 * - Mobile-first con touch targets >= 44px
 * - Regla inmutable "Pollo King"
 */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { MessageSquare, Layout, Sparkles, ShieldCheck } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import { Can } from "@/shared/auth/Can";
import { usePermissions } from "@/shared/auth/usePermissions";
import type { CanvasArtifact, ChatMessage } from "./types";
import {
  useOppyfyChat,
  useOppyfyCredits,
} from "./hooks";
import {
  OppyfyHeader,
  OppyfyChatPane,
  OppyfyCanvasPanel,
  OppyfyRolloverModal,
  OppyfyGovernancePanel,
} from "./components";

export type OppyFyMainTab = "workspace" | "governance";

export interface OppyFyRbacDomainConfig {
  readonly domain: string;
  readonly subdomain: string;
  readonly enabledForRole: boolean;
}

const DEFAULT_RBAC_DOMAINS: readonly OppyFyRbacDomainConfig[] = [
  { domain: "inventory", subdomain: "kardex_valuation", enabledForRole: true },
  { domain: "recipes", subdomain: "escandallo_margins", enabledForRole: true },
  { domain: "procurement", subdomain: "supplier_dte_prices", enabledForRole: true },
  { domain: "finance", subdomain: "holding_ebitda", enabledForRole: false },
];

export interface OppyFyFeatureViewProps {
  readonly initialCanvasArtifact?: CanvasArtifact | null;
  readonly initialContextPct?: number;
  readonly initialRemainingCredits?: number;
  readonly initialThreadId?: string;
  readonly defaultSubdomainSlug?: string;
  readonly initialTab?: OppyFyMainTab;
}

/**
 * Hook seguro para sincronizar query params incluso cuando se ejecuta fuera
 * de un componente <Router> de React Router (por ejemplo, en tests unitarios aislados).
 */
function useSafeSearchParams(): [URLSearchParams, (paramName: string, paramValue: string) => void] {
  try {
    const [searchParams, setSearchParams] = useSearchParams();
    const setParam = (name: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set(name, value);
        return next;
      });
    };
    return [searchParams, setParam];
  } catch {
    const localMemoryParams = new URLSearchParams();
    const setParam = (name: string, value: string) => {
      localMemoryParams.set(name, value);
    };
    return [localMemoryParams, setParam];
  }
}

export function OppyFyFeatureView({
  initialCanvasArtifact = null,
  initialContextPct,
  initialRemainingCredits,
  initialThreadId,
  defaultSubdomainSlug,
  initialTab,
}: OppyFyFeatureViewProps = {}) {
  // 1. Sincronización de Pestaña Principal (?tab=workspace vs ?tab=governance)
  const [searchParams, setSearchParam] = useSafeSearchParams();
  const urlTab = searchParams.get("tab");
  const defaultTab: OppyFyMainTab =
    initialTab ??
    (urlTab === "governance" ? "governance" : "workspace");

  const [activeMainTab, setActiveMainTab] = useState<OppyFyMainTab>(defaultTab);

  useEffect(() => {
    if (urlTab === "governance" || urlTab === "workspace") {
      setActiveMainTab(urlTab as OppyFyMainTab);
    }
  }, [urlTab]);

  const handleSwitchMainTab = (tab: OppyFyMainTab) => {
    setActiveMainTab(tab);
    setSearchParam("tab", tab);
  };

  // Permisos RBAC
  const { can, policy } = usePermissions();
  const hasGovernanceAccess =
    can("oppyfy.governance.manage") ||
    can("oppyfy.rbac.configure") ||
    Boolean(policy.isSuperUser);

  // 2. Hooks Reactivos de OppyFy Workspace
  const chat = useOppyfyChat({
    initialContextPct,
    initialRemainingCredits,
    initialThreadId,
    defaultSubdomainSlug,
  });

  const credits = useOppyfyCredits();

  // 3. Estados locales de UI
  const [isRolloverModalOpen, setIsRolloverModalOpen] = useState<boolean>(false);
  const [mobileView, setMobileView] = useState<"chat" | "canvas">("chat");
  const [domains, setDomains] = useState<readonly OppyFyRbacDomainConfig[]>(
    DEFAULT_RBAC_DOMAINS
  );

  // Inicializar artefacto si se recibe por props
  useEffect(() => {
    if (initialCanvasArtifact && !chat.activeCanvasArtifact) {
      chat.setActiveCanvasArtifact(initialCanvasArtifact);
    }
  }, [initialCanvasArtifact, chat]);

  // Si el medidor de contexto pasa a rojo, sugerir rollover modal
  const handleOpenRolloverModal = (): void => {
    setIsRolloverModalOpen(true);
  };

  const handleCloseRolloverModal = (): void => {
    setIsRolloverModalOpen(false);
  };

  const handleConfirmRollover = async (summaryNotes?: string): Promise<void> => {
    await chat.rolloverToFreshThread(summaryNotes);
    setIsRolloverModalOpen(false);
  };

  const handleSelectArtifactFromMessage = (msg: ChatMessage): void => {
    if (msg.canvasPayload) {
      chat.setActiveCanvasArtifact(msg.canvasPayload);
      setMobileView("canvas");
    }
  };

  const handleNewThread = (): void => {
    chat.clearMessages();
  };

  const toggleDomain = (index: number): void => {
    setDomains((prev) =>
      prev.map((item, idx) =>
        idx === index
          ? { ...item, enabledForRole: !item.enabledForRole }
          : item
      )
    );
  };

  // Saldo de créditos efectivo (del backend o local del chat)
  const remainingCredits =
    credits.wallet !== null
      ? credits.remainingCredits
      : chat.remainingCredits;

  return (
    <section
      data-testid="feature-oppyfy"
      className="glass-card flex flex-col space-y-4 rounded-xl p-4 md:p-6"
    >
      {/* Navegación Superior: Workspace IA vs Gobernanza & RBAC */}
      <div
        role="tablist"
        aria-label="Pestañas Principales de OppyFy"
        className="flex items-center gap-2 border-b border-border pb-3"
      >
        <button
          type="button"
          role="tab"
          id="oppyfy-main-tab-workspace"
          aria-selected={activeMainTab === "workspace"}
          aria-controls="oppyfy-main-panel-workspace"
          data-testid="tab-main-workspace"
          onClick={() => handleSwitchMainTab("workspace")}
          className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
            activeMainTab === "workspace"
              ? "border border-primary bg-primary/15 text-primary shadow-sm"
              : "border border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <Sparkles className="h-4 w-4" />
          <span>{translateKey("oppyfy", "view_tabs.workspace")}</span>
        </button>

        <button
          type="button"
          role="tab"
          id="oppyfy-main-tab-governance"
          aria-selected={activeMainTab === "governance"}
          aria-controls="oppyfy-main-panel-governance"
          data-testid="tab-main-governance"
          onClick={() => handleSwitchMainTab("governance")}
          className={`touch-target inline-flex min-h-[44px] items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
            activeMainTab === "governance"
              ? "border border-primary bg-primary/15 text-primary shadow-sm"
              : "border border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          <span>{translateKey("oppyfy", "view_tabs.governance")}</span>
        </button>
      </div>

      {/* RENDERIZADO CONDICIONAL POR PESTAÑA */}
      {activeMainTab === "workspace" ? (
        <div
          id="oppyfy-main-panel-workspace"
          role="tabpanel"
          aria-labelledby="oppyfy-main-tab-workspace"
          className="flex flex-col space-y-4"
        >
          {/* Encabezado OppyFy con Selector de Hilos, Créditos y Medidor de Contexto */}
          <OppyfyHeader
            threads={chat.threads}
            currentThreadId={chat.currentThreadId}
            remainingCredits={remainingCredits}
            contextHealth={chat.contextHealth}
            onSwitchThread={chat.switchThread}
            onNewThread={handleNewThread}
            onOpenRolloverModal={handleOpenRolloverModal}
          />

          {/* Controles de Vista Móvil (Chat / Canvas) */}
          <div className="flex lg:hidden items-center justify-center gap-2 border-b border-border pb-2">
            <button
              type="button"
              data-testid="mobile-toggle-chat"
              onClick={() => setMobileView("chat")}
              className={`touch-target inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-lg border text-xs font-semibold ${
                mobileView === "chat"
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border bg-card text-muted-foreground"
              }`}
            >
              <MessageSquare className="h-4 w-4" />
              <span>{translateKey("oppyfy", "canvas.toggle_chat")}</span>
            </button>
            <button
              type="button"
              data-testid="mobile-toggle-canvas"
              onClick={() => setMobileView("canvas")}
              className={`touch-target inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-lg border text-xs font-semibold ${
                mobileView === "canvas"
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border bg-card text-muted-foreground"
              }`}
            >
              <Layout className="h-4 w-4" />
              <span>{translateKey("oppyfy", "canvas.toggle_canvas")}</span>
            </button>
          </div>

          {/* Workspace Principal Split-View (Chat + Canvas) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 min-h-[520px]">
            {/* Panel Izquierdo: Chat Conversacional */}
            <div
              className={`lg:col-span-6 xl:col-span-6 h-full ${
                mobileView === "chat" ? "block" : "hidden lg:block"
              }`}
            >
              <OppyfyChatPane
                messages={chat.messages}
                draftPrompt={chat.draftPrompt}
                onChangeDraftPrompt={chat.setDraftPrompt}
                onSendMessage={chat.sendMessage}
                isSending={chat.isSending}
                contextHealth={chat.contextHealth}
                onOpenRolloverModal={handleOpenRolloverModal}
                onSelectArtifact={handleSelectArtifactFromMessage}
              />
            </div>

            {/* Panel Derecho: Split-View Canvas Analítico */}
            <div
              className={`lg:col-span-6 xl:col-span-6 h-full ${
                mobileView === "canvas" ? "block" : "hidden lg:block"
              }`}
            >
              <OppyfyCanvasPanel
                artifact={chat.activeCanvasArtifact}
                onExecuteAction={async () => {
                  await new Promise((res) => setTimeout(res, 200));
                }}
              />
            </div>
          </div>

          {/* Matriz RBAC Propia y Editable de OppyFy */}
          <div
            data-testid="oppyfy-rbac-domains"
            className="rounded-xl border border-border bg-secondary/20 p-3"
          >
            <h3 className="mb-2 text-xs font-bold uppercase text-muted-foreground">
              RBAC Propio Editable de OppyFy (Dominios & Subdominios Autorizados)
            </h3>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-4">
              {domains.map((d, idx) => (
                <button
                  key={`${d.domain}.${d.subdomain}`}
                  type="button"
                  data-testid={`oppyfy-domain-toggle-${d.domain}-${d.subdomain}`}
                  onClick={() => toggleDomain(idx)}
                  className={`touch-target flex min-h-[44px] items-center justify-between rounded-lg border px-3 py-2 text-xs font-mono transition-colors ${
                    d.enabledForRole
                      ? "border-primary bg-primary/15 text-primary"
                      : "border-border bg-card text-muted-foreground"
                  }`}
                >
                  <span>{`${d.domain}.${d.subdomain}`}</span>
                  <span>{d.enabledForRole ? "ON" : "OFF"}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Modal de Rollover Asistido (Traspaso a Hilo Fresco) */}
          <OppyfyRolloverModal
            isOpen={isRolloverModalOpen}
            onClose={handleCloseRolloverModal}
            onConfirm={handleConfirmRollover}
            isProcessing={chat.isSending}
          />
        </div>
      ) : (
        <div
          id="oppyfy-main-panel-governance"
          role="tabpanel"
          aria-labelledby="oppyfy-main-tab-governance"
        >
          <Can
            perform="oppyfy.governance.manage"
            fallback={
              hasGovernanceAccess ? (
                <OppyfyGovernancePanel />
              ) : (
                <div
                  role="status"
                  data-testid="governance-access-denied"
                  className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-center text-xs font-semibold text-destructive"
                >
                  {translateKey("oppyfy", "view_tabs.governance_denied")}
                </div>
              )
            }
          >
            <OppyfyGovernancePanel />
          </Can>
        </div>
      )}
    </section>
  );
}
