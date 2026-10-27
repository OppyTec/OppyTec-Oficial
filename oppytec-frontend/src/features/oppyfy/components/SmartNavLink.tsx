import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Compass, ExternalLink, ArrowRight, X } from "lucide-react";

export interface SmartNavLinkProps {
  readonly href?: string;
  readonly children?: React.ReactNode;
}

export function SmartNavLink({ href, children }: SmartNavLinkProps) {
  const [navDialogOpen, setNavDialogOpen] = useState(false);
  const navigate = useNavigate();

  if (!href) {
    return <span className="font-semibold text-primary">{children}</span>;
  }

  const isExternal = href.startsWith("http://") || href.startsWith("https://");

  const handleOpenNewTab = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.open(href, "_blank", "noopener,noreferrer");
    setNavDialogOpen(false);
  };

  const handleNavigateCurrentTab = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isExternal) {
      window.location.href = href;
    } else {
      navigate(href);
    }
    setNavDialogOpen(false);
  };

  return (
    <>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setNavDialogOpen(true);
        }}
        type="button"
        data-testid="smart-nav-link"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 my-0.5 rounded-lg bg-primary/15 hover:bg-primary/25 border border-primary/30 text-primary font-medium text-xs transition-all duration-150 cursor-pointer shadow-xs hover:scale-[1.02] active:scale-[0.98]"
        title="Opciones de navegación a esta vista"
      >
        <Compass className="w-3.5 h-3.5 text-primary shrink-0" />
        <span className="underline decoration-primary/40 underline-offset-2 font-semibold">
          {children}
        </span>
        <ExternalLink className="w-3 h-3 text-primary/70 shrink-0 ml-0.5" />
      </button>

      {navDialogOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Opciones de Navegación Inteligente"
          data-testid="smart-nav-dialog"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150"
          onClick={() => setNavDialogOpen(false)}
        >
          <div
            className="glass-card w-full max-w-md rounded-2xl border border-border p-5 shadow-2xl relative bg-card text-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border pb-3 mb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <Compass className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    Navegación: <span className="text-primary">{children}</span>
                  </h3>
                  <p className="text-[11px] text-muted-foreground">
                    ¿Cómo prefieres abrir esta vista del sistema OppyTec?
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setNavDialogOpen(false)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                aria-label="Cerrar modal de navegación"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-3 py-2">
              <button
                type="button"
                data-testid="smart-nav-new-tab"
                onClick={handleOpenNewTab}
                className="flex items-start gap-3 p-3.5 rounded-xl border border-primary/40 bg-primary/10 hover:bg-primary/20 text-left transition-all cursor-pointer group"
              >
                <div className="p-2 rounded-lg bg-primary/20 text-primary group-hover:scale-110 transition-transform">
                  <ExternalLink className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                    Abrir en pestaña nueva
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary font-mono font-bold">
                      Recomendado
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Mantiene activa tu conversación con Oppy sin perder el contexto actual.
                  </div>
                </div>
              </button>

              <button
                type="button"
                data-testid="smart-nav-current-tab"
                onClick={handleNavigateCurrentTab}
                className="flex items-start gap-3 p-3.5 rounded-xl border border-border bg-secondary/40 hover:bg-secondary/70 text-left transition-all cursor-pointer group"
              >
                <div className="p-2 rounded-lg bg-secondary text-muted-foreground group-hover:text-foreground group-hover:scale-110 transition-transform">
                  <ArrowRight className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground">
                    Navegar en ventana actual
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Redirige la ventana actual directamente a la sección en OppyTec.
                  </div>
                </div>
              </button>
            </div>

            <div className="pt-3 border-t border-border flex justify-end">
              <button
                type="button"
                onClick={() => setNavDialogOpen(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default SmartNavLink;
